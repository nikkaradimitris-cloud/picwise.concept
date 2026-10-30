#!/usr/bin/env bash
# Where PicWise's domain points, read from its zone's own name servers as the registry
# names them now, so neither a resolver's memory nor a stale list of name servers stands
# between a change and this answer (.github/workflows/server-web.yml).
#
#   dns_state.sh <domain> <zone> <file of the server's addresses, one a line>
#
# Prints two lines and never an address: the zone's name servers, then one of "points at
# the server", "an alias (CNAME) to <name>", "points at the server and at N other
# address(es): the other record must go", "points at N other address(es), not the
# server", "no record", "no answer from the name servers".
set -uo pipefail

domain=${1:?domain}
zone=${2:?zone}
ours=${3:?file of the server\'s addresses}

# The registry of the zone's last label (.cloud) gives the zone's name servers as set at
# the registrar; a resolver's answer is the fallback.
registry=$(dig +short NS "${zone##*.}." 2> /dev/null | head -n 1)
servers=()
if [ -n "$registry" ]; then
  mapfile -t servers < <(dig +norecurse +noall +authority +time=5 +tries=2 NS "$zone" "@$registry" 2> /dev/null \
    | awk '$4 == "NS" {print $5}' | sed 's/\.$//' | sort -u)
fi
if [ "${#servers[@]}" = 0 ]; then
  mapfile -t servers < <(dig +short NS "$zone" 2> /dev/null | sed 's/\.$//' | sort -u)
fi
echo "the name servers of $zone: ${servers[*]:-none found}"

for server in "${servers[@]}"; do
  a4=$(dig +short +norecurse +time=5 +tries=1 A "$domain" "@$server" 2> /dev/null) || continue
  a6=$(dig +short +norecurse +time=5 +tries=1 AAAA "$domain" "@$server" 2> /dev/null) || a6=""
  # Names end with a dot (an alias); addresses do not.
  alias=$(printf '%s\n' "$a4" | grep -v '^;' | grep '\.$' | head -n 1 | sed 's/\.$//')
  mine=0
  others=0
  for address in $(printf '%s\n%s\n' "$a4" "$a6" | grep -v '\.$' | grep -E '^[0-9A-Fa-f:.]+$'); do
    if grep -qxF -- "$address" "$ours"; then mine=$((mine + 1)); else others=$((others + 1)); fi
  done
  if [ -n "$alias" ]; then echo "$domain: an alias (CNAME) to $alias"
  elif [ "$mine" -gt 0 ] && [ "$others" = 0 ]; then echo "$domain: points at the server"
  elif [ "$mine" -gt 0 ]; then echo "$domain: points at the server and at $others other address(es): the other record must go"
  elif [ "$others" -gt 0 ]; then echo "$domain: points at $others other address(es), not the server"
  else echo "$domain: no record"
  fi
  exit 0
done
echo "$domain: no answer from the name servers"
