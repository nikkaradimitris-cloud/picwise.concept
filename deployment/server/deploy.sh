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
  "$SHARED/shops" "$SHARED/offers" "$SHARED/photos" "$SHARED/searches" "$SHARED/checks" "$SHARED/packages"
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
# One card per product (owner, 2026-11-19): the sets the site writes for picwise-families,
# and its answers, which the site reads.
install -d -o root -g picwise-assist -m 2750 "$ASSIST/families"
install -d -o picwise-assist -g picwise-assist -m 2750 "$ASSIST/families/answers"
install -d -o picwise-assist -g picwise-assist -m 700 "$ASSIST/families/spend"

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
  install -d -o picwise -g picwise-assist -m 2770 "$ASSIST/families/jobs"
  # The category of the products not asked yet (the checks' rules 5.5): the preparation
  # names them in shelves/jobs, picwise-shelves answers in shelves (its answers file).
  install -d -o picwise-assist -g picwise-assist -m 2750 "$ASSIST/shelves"
  install -d -o picwise -g picwise-assist -m 2770 "$ASSIST/shelves/jobs"
  # The question "is it the kind itself" (docs/PICWISE_KIND_ITSELF_RULES.md, 8.2): the
  # preparation names the questions in itself/jobs, picwise-itself answers in itself (its
  # answers file). While data/kind_itself_switch.json is false, nothing is named or read.
  install -d -o picwise-assist -g picwise-assist -m 2750 "$ASSIST/itself"
  install -d -o picwise -g picwise-assist -m 2770 "$ASSIST/itself/jobs"
  # The quality meter's verdicts and its day's note (the same rules, section 9).
  install -d -o picwise-assist -g picwise-assist -m 2750 "$ASSIST/meter"
  ASSIST_ON=yes
  echo "Anthropic key: set"
else
  rm -f /etc/picwise/assist.env
  rm -rf -- "${ASSIST:?}/jobs" "${ASSIST:?}/drafts" "${ASSIST:?}/families/jobs" "${ASSIST:?}/shelves/jobs" \
    "${ASSIST:?}/itself/jobs"
  ASSIST_ON=no
  echo "Anthropic key: not set; the site writes no job"
fi
if [ -n "$ASSIST_ENV_FILE" ]; then rm -f "$ASSIST_ENV_FILE"; fi

echo "== services"
for unit in picwise-web.service picwise-prepare.service picwise-prepare.timer picwise-shops.service \
  picwise-shops.timer picwise-photos.service picwise-photos.timer picwise-offers.service picwise-offers.timer; do
  install -m 644 "$RELEASE/deployment/server/$unit" /etc/systemd/system/
done
# The checks of every product on its shop's own site (docs/PICWISE_CHECKS_RULES.md).
for unit in picwise-checks.service picwise-checks.timer; do
  install -m 644 "$RELEASE/deployment/server/$unit" /etc/systemd/system/
done
# The checks' four clones and their night's recording (the checks' rules 22; owner, 2026-11-25:
# «μην αγνοείς τους 4 κλώνους»): installed always, enabled only with data/checks_clones.json
# "on" (his «ανέβασε»), in place of the bot alone.
for unit in picwise-checks@.service picwise-checks@.timer picwise-checks-record.service picwise-checks-record.timer; do
  install -m 644 "$RELEASE/deployment/server/$unit" /etc/systemd/system/
done
CLONES=$(python3 -c 'import json, sys; print(4 if json.load(open(sys.argv[1])).get("on") is True else 0)' \
  "$RELEASE/data/checks_clones.json" 2> /dev/null || echo 0)
# The AI layer's services, started below only with its key.
install -m 644 "$RELEASE/deployment/server/picwise-assist.service" /etc/systemd/system/
for unit in picwise-families.service picwise-family-jobs.service picwise-family-jobs.timer \
  picwise-shelves.service picwise-shelves.timer picwise-itself.service picwise-itself.timer \
  picwise-meter.service picwise-meter.timer; do
  install -m 644 "$RELEASE/deployment/server/$unit" /etc/systemd/system/
done
systemctl daemon-reload

PREVIOUS=$(readlink "$APP/current" 2> /dev/null || true)
ln -sfn "releases/$RELEASE_ID" "$APP/current.new"
mv -T "$APP/current.new" "$APP/current"

echo "== the catalogue, prepared as a Vercel build prepares it, when this release needs it"
# Owner, 2026-11-20: «ότι αφορά τον κατάλογο okay από ποια αλλαγή δεν αφορά τον κατάλογο
# γιατί πρέπει να περιμένουμε μισή ώρα?» (a preparation takes 22 to 26 minutes with both
# Awin links). Prepared again only when the change concerns the catalogue: this release
# would not read the file in place (other code wrote it), the preparation's own script or
# service changed, or the file was prepared a day ago or more. Otherwise the site restarts
# on the file in place, and the night prepares it as every night.
PREPARE=yes
if [ -n "$PREVIOUS" ] && [ -d "$APP/$PREVIOUS" ] \
  && cmp -s "$APP/$PREVIOUS/tools/prepare_catalogue.py" "$RELEASE/tools/prepare_catalogue.py" \
  && cmp -s "$APP/$PREVIOUS/deployment/server/picwise-prepare.service" "$RELEASE/deployment/server/picwise-prepare.service"; then
  BEFORE=$(python3 "$RELEASE/deployment/server/prepared_state.py" --within-hours 24 \
    "$SHARED/prepared/catalogue.json.gz" 2>&1 | tail -n 1 || true)
  case "$BEFORE" in fresh*) PREPARE=no ;; esac
fi
if [ "$PREPARE" = yes ]; then
  # The checks' round (all day) stops while the catalogue is prepared, for the server's
  # memory; its answers are kept, and it goes on after the site restarts (below).
  systemctl stop picwise-checks.service 2> /dev/null || true
  systemctl stop 'picwise-checks@*.service' 2> /dev/null || true
  systemctl start picwise-prepare.service || echo "preparing failed; the site keeps the last prepared file (30 h)"
  # The summary line, the peak memory and length, and systemd's own line, of this run.
  journalctl -u picwise-prepare.service -n 20 -o cat --no-pager --since "-65min" \
    | grep -E 'prepare_catalogue|Consumed' | tail -n 3 || true
else
  echo "not prepared again: the change does not concern the catalogue; this release reads the one in place ($BEFORE)"
  # A round running goes on with the code it started with; when the bot's code changed it
  # is stopped here and started again below on this release's, going on from the answers
  # it kept (24/11: the mend of a round ended by an error would otherwise wait a day).
  if [ -n "$PREVIOUS" ] && [ -d "$APP/$PREVIOUS" ] \
    && ! { diff -rq "$APP/$PREVIOUS/deployment/bot" "$RELEASE/deployment/bot" > /dev/null 2>&1 \
      && diff -rq "$APP/$PREVIOUS/src/picwise_checks" "$RELEASE/src/picwise_checks" > /dev/null 2>&1; }; then
    echo "the checks' bot changed: its round is started again on this release, from the answers it kept"
    systemctl stop picwise-checks.service 2> /dev/null || true
    systemctl stop 'picwise-checks@*.service' 2> /dev/null || true
  fi
fi

echo "== the catalogue in place, as this release reads it"
# Owner, 2026-11-20 («κάνε μόνο το ένα», of three remedies): this release goes in only if it can read
# the catalogue in place. That day a deployment whose preparation was killed for memory
# restarted the site with code that refuses the file in place (a prepared file is read only
# by the code that wrote it), and the site showed no product for 80 minutes. Otherwise the
# site stays on the release it runs, not restarted, with that release's units, and the
# deployment fails, so that its run says so. Read without loading the catalogue.
STATE=$(python3 "$RELEASE/deployment/server/prepared_state.py" "$SHARED/prepared/catalogue.json.gz" 2>&1 \
  | tail -n 1 || true)
echo "${STATE:-unreadable}"
case "$STATE" in
  fresh*) ;;
  *)
    # The units the step "== services" put in place, each as the release the site runs has it.
    UNITS="picwise-web.service picwise-prepare.service picwise-prepare.timer picwise-shops.service
      picwise-shops.timer picwise-photos.service picwise-photos.timer picwise-offers.service picwise-offers.timer
      picwise-assist.service picwise-families.service picwise-family-jobs.service picwise-family-jobs.timer
      picwise-checks.service picwise-checks.timer picwise-checks@.service picwise-checks@.timer
      picwise-checks-record.service picwise-checks-record.timer picwise-shelves.service picwise-shelves.timer
      picwise-itself.service picwise-itself.timer picwise-meter.service picwise-meter.timer"
    if [ -n "$PREVIOUS" ] && [ -d "$APP/$PREVIOUS" ] && [ "$(readlink -f "$APP/$PREVIOUS")" != "$RELEASE" ]; then
      ln -sfn "$PREVIOUS" "$APP/current.new"
      mv -T "$APP/current.new" "$APP/current"
      for unit in $UNITS; do
        if [ -f "$APP/$PREVIOUS/deployment/server/$unit" ]; then
          install -m 644 "$APP/$PREVIOUS/deployment/server/$unit" /etc/systemd/system/
        fi
      done
      systemctl daemon-reload
      echo "this release cannot read the catalogue in place (${STATE:-unreadable}): the site stays on $PREVIOUS, not restarted" >&2
      exit 1
    fi
    echo "no release before this one to stay on: this one goes in"
    ;;
esac
systemctl enable --now picwise-prepare.timer
# The shops' catalogues each night before the preparation (owner, 2026-10-26); a
# deployment never asks them itself.
systemctl enable --now picwise-shops.timer
# The checks of every product on its shop's own site, all day (the checks' rules; owner,
# 2026-11-21 and 2026-11-22). What they decided is applied only behind data/checks_switch.json.
# With the clones on (22): the four clones' timers and the night's recording, never with the
# bot alone beside them; off, the bot alone, as before.
if [ "$CLONES" -gt 0 ]; then
  systemctl disable --now picwise-checks.timer 2> /dev/null || true
  systemctl stop picwise-checks.service 2> /dev/null || true
  for clone in $(seq 1 "$CLONES"); do systemctl enable --now "picwise-checks@$clone.timer"; done
  systemctl enable --now picwise-checks-record.timer
else
  for clone in 1 2 3 4; do systemctl disable --now "picwise-checks@$clone.timer" 2> /dev/null || true; done
  systemctl stop 'picwise-checks@*.service' 2> /dev/null || true
  systemctl disable --now picwise-checks-record.timer 2> /dev/null || true
  systemctl enable --now picwise-checks.timer
fi

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
# The checks' round goes on (it asks nothing between 03:05 and 05:30 UTC, nor on a night
# recorded already); started in the background, a round already running is left as it is.
if [ "$CLONES" -gt 0 ]; then
  for clone in $(seq 1 "$CLONES"); do
    systemctl start --no-block "picwise-checks@$clone.service" 2> /dev/null \
      || echo "the checks' clone $clone did not start; its timer starts the next"
  done
else
  systemctl start --no-block picwise-checks.service 2> /dev/null || echo "the checks' round did not start; the timer starts the next"
fi

echo "== the AI layer's service"
# Only with its key; at most one euro a day (owner, 2026-11-06), kept as $1.00. A service
# that does not start leaves the site as it is: its pages wait for no answer.
if [ "$ASSIST_ON" = yes ]; then
  systemctl enable picwise-assist.service
  systemctl restart picwise-assist.service || echo "assist did not start; the site is as it was"
  sleep 3
  echo "assist: $(systemctl is-active picwise-assist.service || true)"
  journalctl -u picwise-assist.service -n 3 -o cat --no-pager --since "-1min" || true
  # One card per product (owner, 2026-11-19: «δεν θα περιμένω τη νύχτα για να κάνει το
  # σκανάρισμα θα το κάνουμε τώρα»): the sets written now, from the catalogue just
  # prepared, and answered from now on; again after each night's preparation.
  systemctl enable picwise-families.service
  systemctl restart picwise-families.service || echo "families did not start; the site is as it was"
  systemctl start --no-block picwise-family-jobs.service || echo "the families' sets were not written now"
  systemctl enable --now picwise-family-jobs.timer
  echo "families: $(systemctl is-active picwise-families.service || true)"
  # The category of the products not asked yet, each morning after the preparation (the
  # checks' rules 5.5); never started by a deployment itself.
  systemctl enable --now picwise-shelves.timer
  # The question "is it the kind itself", each morning after the categories; it finds
  # nothing to ask while the preparation names nothing (its switch false).
  systemctl enable --now picwise-itself.timer
  # The quality meter, each morning after them: the first cards of fixed searches, judged
  # (at most $2 a day; its verdicts change nothing shown).
  systemctl enable --now picwise-meter.timer
else
  systemctl disable --now picwise-assist.service > /dev/null 2>&1 || true
  systemctl disable --now picwise-families.service picwise-family-jobs.timer picwise-shelves.timer \
    picwise-itself.timer picwise-meter.timer > /dev/null 2>&1 || true
  echo "assist: off, no key"
fi

echo "== old releases (the one in use and the 4 newest others are kept)"
find "$APP/releases" -mindepth 1 -maxdepth 1 -type d ! -path "$RELEASE" -printf '%T@ %p\n' \
  | sort -rn | tail -n +5 | cut -d' ' -f2- | xargs -r rm -rf --
find "$APP/venvs" -mindepth 1 -maxdepth 1 -type d ! -path "$VENV" ! -path "$AI_VENV" -exec rm -rf {} +
ls -1 "$APP/releases"
echo "== done"
