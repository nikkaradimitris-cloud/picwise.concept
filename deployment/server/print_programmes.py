"""Which of the catalogue's shops PicWise's Awin account is joined to, and how fresh each
shop's feed is: read from Awin, never by a click (owner, 2026-11-21: «Δεν πατιούνται ποτέ
αυτόματα τα links του Awin, για να μη γίνονται ψεύτικα κλικ»; task 3 of the work split by
model: «Awin's feed list and programmes (joined, last update)»). The look at 95 cards of
21/11 found every button sound on PicWise's side, each leading to an Awin link; what
happens past it is Awin's, and a programme PicWise is not joined to, closed or suspended
is where it can fail.

    ssh picwise 'sudo systemd-run ... -p EnvironmentFile=/etc/picwise/picwise.env /usr/bin/python3 -' \\
        < deployment/server/print_programmes.py

Run once by .github/workflows/server-programmes.yml, on the server, as the site's user,
with the server's secrets in its environment (the Awin token, the feed links whose key the
feed list is read with). It asks Awin, a call every `PAUSE` seconds (Awin allows a
publisher about 20 a minute):

- the account's programmes, by PicWise's relationship to each: joined, pending,
  not joined, suspended, rejected (the Publisher API, `/publishers/<id>/programmes`);
- the product feed list (`productdata.awin.com/datafeed/list`): each feed's advertiser,
  its membership status, when Awin last imported it and how many products it holds.

The catalogue's shops are the advertisers of the feed's copies the preparation downloaded
(one per Awin link), by their id; the products each holds on the site are the night's
public note's (`balance.by_shop`). Prints per shop, the most products first, its
relationship, its feeds' membership and last import; then the products of the site by
relationship. Never the token, a key, a link or the account's id: each is masked before a
line is printed. Changes nothing.
"""
from __future__ import annotations

import csv
import glob
import gzip
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Mapping

ACCOUNTS_API = "https://api.awin.com/accounts?type=publisher"
PROGRAMMES_API = "https://api.awin.com/publishers/{publisher}/programmes?relationship={relationship}"
FEED_LIST = "https://productdata.awin.com/datafeed/list/apikey/{key}"
RELATIONSHIPS = ("joined", "pending", "notjoined", "suspended", "rejected")
PAUSE = 3.5
CACHE_DIR = "/srv/picwise/shared/cache"
NOTE = "/srv/picwise/shared/public/prepared.json"
COPIES_APART_HOURS = 30.0
SHOPS_LISTED = 200
_GZIP_MAGIC = b"\x1f\x8b"
_KEY = re.compile(r"/apikey/([^/?#]+)")
_LINK = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://\S+")
csv.field_size_limit(sys.maxsize)

Get = Callable[[str, Mapping[str, str]], tuple[int, bytes]]


def _get(url: str, headers: Mapping[str, str]) -> tuple[int, bytes]:
    request = urllib.request.Request(url, headers=dict(headers))
    try:
        with urllib.request.urlopen(request, timeout=120) as answer:
            return answer.status, answer.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()[:2000]
    except (urllib.error.URLError, OSError) as error:
        return 0, type(error).__name__.encode()


class Masked:
    """Every secret value, and each key a feed link carries, masked before a line is printed."""

    def __init__(self, values: Iterable[str]) -> None:
        self.values = sorted({value for value in values if value and len(value) >= 6}, key=len, reverse=True)

    def __call__(self, line: str) -> str:
        for value in self.values:
            line = line.replace(value, "***")
        return _LINK.sub("<link>", line)


def feed_key(*links: str) -> str:
    """The key a feed link carries (`.../apikey/<key>/...`), the feed list's key too."""
    for link in links:
        match = _KEY.search(str(link or ""))
        if match:
            return match.group(1)
    return ""


def feed_copies(cache_dir: str) -> list[str]:
    """Every copy of the feed the preparation downloaded, one per Awin link: those written
    within `COPIES_APART_HOURS` of the newest (as the nightly bot reads them)."""
    copies = glob.glob(os.path.join(cache_dir, "picwise_awin_feed_*.bin"))
    if not copies:
        return []
    written = {path: os.path.getmtime(path) for path in copies}
    newest = max(written.values())
    return sorted((path for path in copies if newest - written[path] <= COPIES_APART_HOURS * 3600),
                  key=lambda path: -written[path])


def feed_shops(path: str) -> dict[str, str]:
    """The advertisers of one copy of the feed: id -> name, read row by row."""
    with open(path, "rb") as probe:
        gzipped = probe.read(2) == _GZIP_MAGIC
    binary = gzip.open(path, "rb") if gzipped else open(path, "rb")
    with io.TextIOWrapper(binary, encoding="utf-8-sig", errors="replace", newline="") as text:
        reader = csv.reader(text)
        header = [name.strip().lower() for name in next(reader, None) or []]
        id_at = next((header.index(name) for name in ("merchant_id", "advertiser_id") if name in header), None)
        name_at = next((header.index(name) for name in ("merchant_name", "advertiser_name") if name in header), None)
        if id_at is None:
            return {}
        shops: dict[str, str] = {}
        for row in reader:
            ident = row[id_at].strip() if id_at < len(row) else ""
            if ident.isdigit() and ident not in shops:
                shops[ident] = " ".join(row[name_at].split()) if name_at is not None and name_at < len(row) else ""
        return shops


def note_products(path: str) -> dict[str, int]:
    """The products each shop holds on the site, by its name folded: the night's note."""
    try:
        with open(path, encoding="utf-8") as handle:
            note = json.load(handle)
    except (OSError, ValueError):
        return {}
    rows = ((note.get("balance") or {}).get("by_shop") or []) if isinstance(note, dict) else []
    return {" ".join(str(row.get("shop") or "").split()).casefold(): int(row.get("products") or 0)
            for row in rows if isinstance(row, dict)}


def _json(body: bytes) -> Any:
    try:
        return json.loads(body.decode("utf-8") or "null")
    except ValueError:
        return None


def find_publisher(token: str, get: Get) -> str:
    status, body = get(ACCOUNTS_API, {"Authorization": f"Bearer {token}", "Accept": "application/json"})
    answer = _json(body) if status == 200 else None
    rows = answer.get("accounts") if isinstance(answer, dict) else answer
    found = [str(row.get("accountId") or row.get("id") or "").strip() for row in (rows if isinstance(rows, list) else ())
             if isinstance(row, dict) and str(row.get("accountType") or row.get("type") or "publisher").lower() == "publisher"]
    found = [ident for ident in found if ident]
    if len(found) != 1:
        raise ValueError(f"the accounts call answered {status}, {len(found)} publisher accounts")
    return found[0]


def programmes(publisher: str, token: str, get: Get, sleep: Callable[[float], None],
               say: Callable[[str], None]) -> dict[str, dict[str, Any]]:
    """Advertiser id -> its programme as Awin lists it, with PicWise's relationship to it."""
    found: dict[str, dict[str, Any]] = {}
    keys: set[str] = set()
    for relationship in RELATIONSHIPS:
        sleep(PAUSE)
        status, body = get(PROGRAMMES_API.format(publisher=publisher, relationship=relationship),
                           {"Authorization": f"Bearer {token}", "Accept": "application/json"})
        answer = _json(body)
        rows = answer if isinstance(answer, list) else (answer or {}).get("data") if isinstance(answer, dict) else None
        if status != 200 or not isinstance(rows, list):
            say(f"programmes, {relationship}: Awin answered {status}")
            continue
        statuses = Counter(str(row.get("status") or "-") for row in rows if isinstance(row, dict))
        say(f"programmes, {relationship}: {len(rows):,}" + (f" ({', '.join(f'{k} {v}' for k, v in statuses.most_common())})"
                                                            if statuses else ""))
        for row in rows:
            if isinstance(row, dict) and str(row.get("id") or "").strip():
                keys.update(row)
                found.setdefault(str(row["id"]).strip(), {**row, "relationship": relationship})
    if keys:
        say("  a programme's fields: " + ", ".join(sorted(keys)))
    return found


def feed_list(key: str, get: Get) -> list[dict[str, str]]:
    """The product feed list: one row a feed, its columns named as Awin names them."""
    status, body = get(FEED_LIST.format(key=key), {"Accept": "text/csv"})
    if status != 200:
        raise ValueError(f"the feed list answered {status}")
    text = body.decode("utf-8-sig", errors="replace")
    return [dict(row) for row in csv.DictReader(io.StringIO(text))]


def _column(row: Mapping[str, str], *names: str) -> str:
    folded = {str(key).strip().casefold(): value for key, value in row.items()}
    for name in names:
        value = folded.get(name.casefold())
        if value is not None:
            return " ".join(str(value).split())
    return ""


def report(shops: Mapping[str, str], products: Mapping[str, int], listed: Mapping[str, Mapping[str, Any]],
           feeds: list[dict[str, str]], say: Callable[[str], None], *, now: datetime) -> None:
    """Per shop of the catalogue its relationship, its feeds' membership and last import; then
    the site's products by relationship."""
    by_advertiser: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in feeds:
        ident = _column(row, "Advertiser ID", "advertiser_id")
        if ident:
            by_advertiser[ident].append(row)
    memberships = Counter(_column(row, "Membership Status", "membership_status") or "-" for row in feeds)
    say(f"the feed list: {len(feeds):,} feeds of {len(by_advertiser):,} advertisers; membership: "
        + ", ".join(f"{status} {count}" for status, count in memberships.most_common()))
    rows = []
    for ident, name in shops.items():
        programme = listed.get(ident) or {}
        own_feeds = by_advertiser.get(ident) or []
        imported = sorted((_column(row, "Last Imported", "last_imported") for row in own_feeds), reverse=True)
        rows.append({
            "id": ident, "name": name, "products": products.get(" ".join(name.split()).casefold(), 0),
            "relationship": programme.get("relationship") or "in no list",
            "status": str(programme.get("status") or "-"),
            "membership": ", ".join(sorted({_column(row, "Membership Status", "membership_status") or "-"
                                            for row in own_feeds})) or "no feed listed",
            "imported": imported[0] if imported and imported[0] else "-",
        })
    rows.sort(key=lambda row: (-row["products"], row["name"].casefold()))
    total = sum(row["products"] for row in rows) or 1
    say(f"the catalogue's shops: {len(rows)} advertisers in the feed's copies, {total:,} products on the site")
    by_relationship: dict[str, list] = defaultdict(list)
    for row in rows:
        by_relationship[row["relationship"]].append(row)
    for relationship, members in sorted(by_relationship.items(), key=lambda item: -sum(r["products"] for r in item[1])):
        held = sum(row["products"] for row in members)
        say(f"  {relationship}: {len(members)} shops, {held:,} products ({100 * held / total:.1f}%)")
    say(f"{'products':>9}  {'relationship':<12} {'status':<10} {'feed':<22} {'last imported':<20} shop (advertiser id)")
    for row in rows[:SHOPS_LISTED]:
        say(f"{row['products']:>9,}  {row['relationship']:<12} {row['status'][:10]:<10} {row['membership'][:22]:<22} "
            f"{row['imported'][:20]:<20} {row['name']} ({row['id']})")


def main(*, get: Get = _get, sleep: Callable[[float], None] = time.sleep, environ: Mapping[str, str] = os.environ,
         cache_dir: str = CACHE_DIR, note: str = NOTE, now: datetime | None = None) -> int:
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass
    token = str(environ.get("AWIN_API_TOKEN") or "").strip()
    links = [str(environ.get(name) or "").strip() for name in ("AWIN_FEED_URL", "AWIN_FEED_URL_AWIN")]
    key = feed_key(*links)
    publisher = str(environ.get("AWIN_PUBLISHER_ID") or "").strip()
    secrets = [token, key, publisher, *links]
    mask = Masked(secrets)

    def say(line: str) -> None:
        print(mask(line))

    copies = feed_copies(cache_dir)
    shops: dict[str, str] = {}
    for copy in copies:
        for ident, name in feed_shops(copy).items():
            shops.setdefault(ident, name)
    say(f"the feed's copies: {len(copies)}; advertisers in them: {len(shops)}")
    listed: dict[str, dict[str, Any]] = {}
    if token:
        try:
            if not publisher:
                publisher = find_publisher(token, get)
                mask.values = sorted({*mask.values, publisher}, key=len, reverse=True)
            listed = programmes(publisher, token, get, sleep, say)
        except ValueError as error:
            say(f"programmes not read: {error}")
    else:
        say("no Awin token in the server's secrets: the programmes not read")
    feeds: list[dict[str, str]] = []
    if key:
        sleep(PAUSE)
        try:
            feeds = feed_list(key, get)
        except ValueError as error:
            say(f"the feed list not read: {error}")
    else:
        say("no feed link with a key in the server's secrets: the feed list not read")
    report(shops, note_products(note), listed, feeds, say, now=now or datetime.now(timezone.utc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
