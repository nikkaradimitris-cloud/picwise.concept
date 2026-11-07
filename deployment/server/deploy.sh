#!/usr/bin/env bash
# Put a release of the site on PicWise's server and start it (owner's «ναι», 2026-10-25).
#
#   deploy.sh <release-id> <release.tar.gz> <environment-file> [<assist-environment-file>]
#
# Run as root by .github/workflows/server-deploy.yml, which first copies to the server
# the release (`git archive` of the pushed commit), the environment files it built from
# GitHub's secrets (the site's, and the AI layer's key for picwise-assist alone), and this
# script. Safe to run again.
#
# Layout: /srv/picwise/releases/<id> (code, root's, read-only to the site),
# /srv/picwise/current (the release in use), /srv/picwise/venv (gunicorn),
# /srv/picwise/shared (what the site writes: the prepared catalogue, prepared.json, the
# feed's download cache), /etc/picwise/picwise.env (the secrets). The site listens on
# 127.0.0.1:8016 only, so nothing reaches it from the internet. The AI layer
# (docs/PICWISE_AI_LAYER_SPEC.md, 4.5): /srv/picwise/assist (the site's jobs and the
# service's answers, shared by the two and nothing else), /srv/picwise/venv-ai (the
# Anthropic SDK), /etc/picwise/assist.env (its key, root's alone, read by systemd for
# picwise-assist.service).
set -euo pipefail

RELEASE_ID=${1:?release id}
TARBALL=${2:?release archive}
ENV_FILE=${3:?environment file}
ASSIST_ENV_FILE=${4:-}
[[ $RELEASE_ID =~ ^[0-9A-Za-z-]+$ ]] || { echo "bad release id" >&2; exit 2; }

APP=/srv/picwise
RELEASE=$APP/releases/$RELEASE_ID
SHARED=$APP/shared
HEALTH_URL=http://127.0.0.1:8016/health
export DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=l

echo "== packages"
apt-get -q -y -o DPkg::Lock::Timeout=600 install python3-venv curl time > /dev/null

echo "== user and folders"
id picwise > /dev/null 2>&1 || useradd --system --user-group --home-dir "$APP" --no-create-home \
  --shell /usr/sbin/nologin picwise
install -d -o root -g root -m 755 "$APP" "$APP/releases" "$APP/venvs"
install -d -o picwise -g picwise -m 750 "$SHARED" "$SHARED/prepared" "$SHARED/public" "$SHARED/cache" \
  "$SHARED/shops" "$SHARED/offers" "$SHARED/photos" "$SHARED/searches"
install -d -o root -g picwise -m 750 /etc/picwise
# The AI layer's service, under a user of its own that never reads the site's files or
# secrets; the site joins its group to share /srv/picwise/assist with it. Its jobs/ folder
# is made below only when the service has its key.
id picwise-assist > /dev/null 2>&1 || useradd --system --user-group --home-dir "$APP" --no-create-home \
  --shell /usr/sbin/nologin picwise-assist
usermod -a -G picwise-assist picwise
ASSIST=$APP/assist
install -d -o root -g picwise-assist -m 2750 "$ASSIST"
install -d -o picwise-assist -g picwise-assist -m 2750 "$ASSIST/results"
install -d -o picwise -g picwise-assist -m 2750 "$ASSIST/served"
install -d -o picwise-assist -g picwise-assist -m 700 "$ASSIST/spend"

echo "== release $RELEASE_ID"
rm -rf "$RELEASE.partial"
mkdir -p "$RELEASE.partial"
tar -xzf "$TARBALL" -C "$RELEASE.partial" --no-same-owner
python3 -m compileall -q "$RELEASE.partial/api" "$RELEASE.partial/src" "$RELEASE.partial/tools" \
  "$RELEASE.partial/deployment/server" > /dev/null
chown -R root:root "$RELEASE.partial"
chmod -R u=rwX,go=rX "$RELEASE.partial"
rm -rf "$RELEASE"
mv "$RELEASE.partial" "$RELEASE"
rm -f "$TARBALL"

echo "== gunicorn"
# One virtual environment per requirements file: a script in it names its own path, so
# it is never moved; /srv/picwise/venv points to the one in use.
REQUIREMENTS=$RELEASE/deployment/server/requirements-server.txt
VENV=$APP/venvs/$(sha256sum "$REQUIREMENTS" | cut -c1-12)
if [ ! -x "$VENV/bin/gunicorn" ]; then
  rm -rf "$VENV"
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q --disable-pip-version-check --no-cache-dir --require-hashes \
    --only-binary=:all: -r "$REQUIREMENTS"
fi
ln -sfn "$VENV" "$APP/venv.new"
mv -T "$APP/venv.new" "$APP/venv"
"$APP/venv/bin/gunicorn" --version

echo "== the AI layer's library"
# The Anthropic SDK, every package checked against its hash, in an environment of its own:
# the site never imports it (docs/PICWISE_AI_LAYER_SPEC.md, 4.6).
AI_REQUIREMENTS=$RELEASE/deployment/server/requirements-ai.txt
AI_VENV=$APP/venvs/ai-$(sha256sum "$AI_REQUIREMENTS" | cut -c1-12)
if [ ! -x "$AI_VENV/bin/python" ] || ! "$AI_VENV/bin/python" -c "import anthropic" 2> /dev/null; then
  rm -rf "$AI_VENV"
  python3 -m venv "$AI_VENV"
  "$AI_VENV/bin/pip" install -q --disable-pip-version-check --no-cache-dir --require-hashes \
    -r "$AI_REQUIREMENTS"
fi
ln -sfn "$AI_VENV" "$APP/venv-ai.new"
mv -T "$APP/venv-ai.new" "$APP/venv-ai"
"$APP/venv-ai/bin/python" -c "import anthropic; print('anthropic', anthropic.__version__)"

echo "== secrets"
install -o root -g picwise -m 640 "$ENV_FILE" /etc/picwise/picwise.env
rm -f "$ENV_FILE"
if grep -q '^AWIN_FEED_URL=' /etc/picwise/picwise.env; then echo "feed link: set"; else echo "feed link: not set"; fi
if grep -q '^AWIN_API_TOKEN=' /etc/picwise/picwise.env; then echo "Awin token: set"; else echo "Awin token: not set"; fi
# The AI layer's key, for picwise-assist alone. Without it the jobs/ folder is not made, so
# the site writes no job and its pages are as before.
if [ -n "$ASSIST_ENV_FILE" ] && [ -s "$ASSIST_ENV_FILE" ] && grep -q '^ANTHROPIC_API_KEY=' "$ASSIST_ENV_FILE"; then
  install -o root -g root -m 600 "$ASSIST_ENV_FILE" /etc/picwise/assist.env
  # The site's drafts become jobs only when a page's script asks: no cost for a bot.
  install -d -o picwise -g picwise-assist -m 2750 "$ASSIST/drafts"
  install -d -o picwise -g picwise-assist -m 2770 "$ASSIST/jobs"
  ASSIST_ON=yes
  echo "Anthropic key: set"
else
  rm -f /etc/picwise/assist.env
  rm -rf -- "${ASSIST:?}/jobs" "${ASSIST:?}/drafts"
  ASSIST_ON=no
  echo "Anthropic key: not set; the site writes no job"
fi
if [ -n "$ASSIST_ENV_FILE" ]; then rm -f "$ASSIST_ENV_FILE"; fi

echo "== services"
for unit in picwise-web.service picwise-prepare.service picwise-prepare.timer picwise-shops.service \
  picwise-shops.timer picwise-photos.service picwise-photos.timer picwise-offers.service picwise-offers.timer; do
  install -m 644 "$RELEASE/deployment/server/$unit" /etc/systemd/system/
done
# The AI layer's service, started below only with its key.
install -m 644 "$RELEASE/deployment/server/picwise-assist.service" /etc/systemd/system/
systemctl daemon-reload

PREVIOUS=$(readlink "$APP/current" 2> /dev/null || true)
ln -sfn "releases/$RELEASE_ID" "$APP/current.new"
mv -T "$APP/current.new" "$APP/current"

echo "== the catalogue, prepared as a Vercel build prepares it"
systemctl start picwise-prepare.service || echo "preparing failed; the site keeps the last prepared file (30 h)"
# The summary line, the peak memory and length, and systemd's own line, of this run.
journalctl -u picwise-prepare.service -n 20 -o cat --no-pager --since "-65min" \
  | grep -E 'prepare_catalogue|Consumed' | tail -n 3 || true
systemctl enable --now picwise-prepare.timer
# The shops' catalogues each night before the preparation (owner, 2026-10-26); a
# deployment never asks them itself.
systemctl enable --now picwise-shops.timer

echo "== the offers of PicWise's shops (Awin), fetched once now and every night"
# Owner, 2026-11-01: «Οκ να φέρνει τις προσφορές των δικών μας καταστημάτων». Served to no
# one yet; its counts only are printed.
systemctl start picwise-offers.service || echo "fetching the offers failed; the last file kept"
journalctl -u picwise-offers.service -o cat --no-pager --since "-31min" | grep '^offers:' | tail -n 1 || true
systemctl enable --now picwise-offers.timer

echo "== the products' photos, checked now in the background and every night"
# Owner, 2026-11-01: «Όταν το προϊόν δεν φέρνει φωτογραφία δεν πρέπει να εμφανίζεται». The
# first check asks every photo, at most an hour; the site leaves the gone ones out once
# the file is written, within a minute.
systemctl start --no-block picwise-photos.service || echo "the photo check did not start; the last file kept"
systemctl enable --now picwise-photos.timer

echo "== the site"
systemctl enable picwise-web.service
systemctl restart picwise-web.service
healthy=no
for _ in $(seq 1 30); do
  if curl -fs -m 5 -o /dev/null "$HEALTH_URL"; then healthy=yes; break; fi
  sleep 1
done
if [ "$healthy" != yes ]; then
  journalctl -u picwise-web.service -n 30 -o cat --no-pager || true
  if [ -n "$PREVIOUS" ] && [ -d "$APP/$PREVIOUS" ]; then
    ln -sfn "$PREVIOUS" "$APP/current.new"
    mv -T "$APP/current.new" "$APP/current"
    systemctl restart picwise-web.service
    echo "the new release did not answer; back to $PREVIOUS" >&2
  fi
  exit 1
fi
curl -fsS -m 5 "$HEALTH_URL"
echo

echo "== the AI layer's service"
# Only with its key; at most one euro a day (owner, 2026-11-06), kept as $1.00. A service
# that does not start leaves the site as it is: its pages wait for no answer.
if [ "$ASSIST_ON" = yes ]; then
  systemctl enable picwise-assist.service
  systemctl restart picwise-assist.service || echo "assist did not start; the site is as it was"
  sleep 3
  echo "assist: $(systemctl is-active picwise-assist.service || true)"
  journalctl -u picwise-assist.service -n 3 -o cat --no-pager --since "-1min" || true
else
  systemctl disable --now picwise-assist.service > /dev/null 2>&1 || true
  echo "assist: off, no key"
fi

echo "== old releases (the one in use and the 4 newest others are kept)"
find "$APP/releases" -mindepth 1 -maxdepth 1 -type d ! -path "$RELEASE" -printf '%T@ %p\n' \
  | sort -rn | tail -n +5 | cut -d' ' -f2- | xargs -r rm -rf --
find "$APP/venvs" -mindepth 1 -maxdepth 1 -type d ! -path "$VENV" ! -path "$AI_VENV" -exec rm -rf {} +
ls -1 "$APP/releases"
echo "== done"
