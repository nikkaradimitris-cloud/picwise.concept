#!/usr/bin/env bash
# PicWise's front door on its own server: Caddy, giving the site HTTPS on its domain
# (owner, 2026-10-30: «Θέλω να βλέπω live το site από το καινούργιο server»). The site
# itself is gunicorn on 127.0.0.1:8016, put there by deployment/server/deploy.sh.
#
#   web_setup.sh install [Caddyfile] Caddy from Ubuntu's own archive, so its security
#                                    updates come with the system's; kept stopped until
#                                    the domain points at the server; the file checked
#   web_setup.sh open <Caddyfile>    the file checked by Caddy, put in place, Caddy
#                                    started; it then takes its certificate by itself
#   web_setup.sh status              what answers on 80 and 443, and Caddy's words about
#                                    the certificate
#
# Run as root by .github/workflows/server-web.yml, which copies it and the Caddyfile to
# the server. Safe to run again.
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=l
CADDYFILE=/etc/caddy/Caddyfile

# Ours once open: the package's own file serves a welcome page.
ours_in_place() {
  grep -q "PicWise's front door" "$CADDYFILE" 2> /dev/null
}

install_caddy() {
  if ! dpkg-query -W -f='${Status}' caddy 2> /dev/null | grep -q 'install ok installed'; then
    apt-get -q -o DPkg::Lock::Timeout=600 update > /dev/null
    apt-get -q -y -o DPkg::Lock::Timeout=600 install caddy > /dev/null
  fi
  if ! ours_in_place; then
    # Until the domain points here nothing answers on 80 or 443: the package starts
    # Caddy with its welcome page, which is stopped at once.
    systemctl disable --now caddy.service 2> /dev/null || true
  fi
  echo "caddy $(caddy version | cut -d' ' -f1): $(systemctl is-active caddy.service || true)"
}

# The file beside the one in use, as $CADDYFILE.new, once Caddy has accepted it. Checked
# as the user Caddy runs as, so nothing is written to root's home.
check_file() {
  local new=${1:?the Caddyfile to check}
  install -o root -g root -m 644 "$new" "$CADDYFILE.new"
  if ! runuser -u caddy -- env HOME=/var/lib/caddy caddy validate --adapter caddyfile \
    --config "$CADDYFILE.new" > /tmp/picwise-caddy-validate.txt 2>&1; then
    tail -n 5 /tmp/picwise-caddy-validate.txt >&2
    rm -f "$CADDYFILE.new" /tmp/picwise-caddy-validate.txt
    echo "Caddy refused the file; nothing changed" >&2
    exit 1
  fi
  rm -f /tmp/picwise-caddy-validate.txt
  echo "the front door's file: accepted by Caddy"
}

open_site() {
  local new=${1:?the Caddyfile to put in place}
  install_caddy
  check_file "$new"
  mv -f "$CADDYFILE.new" "$CADDYFILE"
  systemctl enable caddy.service 2> /dev/null
  systemctl reload-or-restart caddy.service
  sleep 2
  echo "caddy: $(systemctl is-active caddy.service || true), with the site's file"
}

status() {
  local enabled
  enabled=$(systemctl is-enabled caddy.service 2> /dev/null) || true
  echo "caddy: $(systemctl is-active caddy.service 2> /dev/null || true) (${enabled:-not installed})"
  echo "listening on 80 and 443:"
  ss -ltnH '( sport = :80 or sport = :443 )' | awk '{print "  " $4}'
  # Only the certificate's lines: the others may name a visitor's address.
  echo "Caddy's words about the certificate, the last half hour:"
  journalctl -u caddy.service --since -30min -o cat --no-pager | python3 -c '
import json, sys
for line in sys.stdin:
    try:
        entry = json.loads(line)
    except ValueError:
        continue
    if str(entry.get("logger", "")).startswith("tls"):
        print("  ", entry.get("level"), entry.get("logger"), "-", entry.get("msg"),
              entry.get("identifier", ""), str(entry.get("error", ""))[:240])
' | tail -n 12
}

case "${1:-}" in
  install)
    install_caddy
    # The file is checked now, before anyone points the domain here.
    if [ -n "${2:-}" ]; then check_file "$2" && rm -f "$CADDYFILE.new"; fi
    ;;
  open) open_site "${2:-}" ;;
  status) status ;;
  *) echo "usage: web_setup.sh install [Caddyfile] | open <Caddyfile> | status" >&2; exit 2 ;;
esac
