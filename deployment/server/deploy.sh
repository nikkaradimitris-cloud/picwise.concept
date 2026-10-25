#!/usr/bin/env bash
# Put a release of the site on PicWise's server and start it (owner's «ναι», 2026-10-25).
#
#   deploy.sh <release-id> <release.tar.gz> <environment-file>
#
# Run as root by .github/workflows/server-deploy.yml, which first copies to the server
# the release (`git archive` of the pushed commit), the environment file it built from
# GitHub's secrets, and this script. Safe to run again.
#
# Layout: /srv/picwise/releases/<id> (code, root's, read-only to the site),
# /srv/picwise/current (the release in use), /srv/picwise/venv (gunicorn),
# /srv/picwise/shared (what the site writes: the prepared catalogue, prepared.json, the
# feed's download cache), /etc/picwise/picwise.env (the secrets). The site listens on
# 127.0.0.1:8016 only, so nothing reaches it from the internet.
set -euo pipefail

RELEASE_ID=${1:?release id}
TARBALL=${2:?release archive}
ENV_FILE=${3:?environment file}
[[ $RELEASE_ID =~ ^[0-9A-Za-z-]+$ ]] || { echo "bad release id" >&2; exit 2; }

APP=/srv/picwise
RELEASE=$APP/releases/$RELEASE_ID
SHARED=$APP/shared
HEALTH_URL=http://127.0.0.1:8016/health
export DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=l

echo "== packages"
apt-get -q -y -o DPkg::Lock::Timeout=600 install python3-venv curl > /dev/null

echo "== user and folders"
id picwise > /dev/null 2>&1 || useradd --system --user-group --home-dir "$APP" --no-create-home \
  --shell /usr/sbin/nologin picwise
install -d -o root -g root -m 755 "$APP" "$APP/releases" "$APP/venvs"
install -d -o picwise -g picwise -m 750 "$SHARED" "$SHARED/prepared" "$SHARED/public" "$SHARED/cache"
install -d -o root -g picwise -m 750 /etc/picwise

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

echo "== secrets"
install -o root -g picwise -m 640 "$ENV_FILE" /etc/picwise/picwise.env
rm -f "$ENV_FILE"
if grep -q '^AWIN_FEED_URL=' /etc/picwise/picwise.env; then echo "feed link: set"; else echo "feed link: not set"; fi

echo "== services"
for unit in picwise-web.service picwise-prepare.service picwise-prepare.timer; do
  install -m 644 "$RELEASE/deployment/server/$unit" /etc/systemd/system/
done
systemctl daemon-reload

PREVIOUS=$(readlink "$APP/current" 2> /dev/null || true)
ln -sfn "releases/$RELEASE_ID" "$APP/current.new"
mv -T "$APP/current.new" "$APP/current"

echo "== the catalogue, prepared as a Vercel build prepares it"
systemctl start picwise-prepare.service || echo "preparing failed; the site reads the feed itself"
journalctl -u picwise-prepare.service -n 3 -o cat --no-pager | grep 'prepare_catalogue' || true
systemctl enable --now picwise-prepare.timer

echo "== the site"
systemctl enable picwise-web.service
systemctl restart picwise-web.service
healthy=no
for _ in $(seq 1 30); do
  if curl -fsS -m 5 -o /dev/null "$HEALTH_URL"; then healthy=yes; break; fi
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

echo "== old releases (the one in use and the 4 newest others are kept)"
find "$APP/releases" -mindepth 1 -maxdepth 1 -type d ! -path "$RELEASE" -printf '%T@ %p\n' \
  | sort -rn | tail -n +5 | cut -d' ' -f2- | xargs -r rm -rf --
find "$APP/venvs" -mindepth 1 -maxdepth 1 -type d ! -path "$VENV" -exec rm -rf {} +
ls -1 "$APP/releases"
echo "== done"
