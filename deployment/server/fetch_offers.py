"""Fetch the live Awin offers of PicWise's own shops, every night, onto the server.

    AWIN_API_TOKEN=... [AWIN_PUBLISHER_ID=...] python3 deployment/server/fetch_offers.py \
        [--feed-cache-dir /srv/picwise/shared/cache] [--out /srv/picwise/shared/offers/offers.json]

Owner, 2026-11-01: «Οκ να φέρνει τις προσφορές των δικών μας καταστημάτων»; how they are
shown on the site, and which product an offer is for, is a later talk. Run by
picwise-offers.service: every night after the preparation, and once by each deployment.

PicWise's shops are the advertisers of the feed the server last downloaded (the newest
`picwise_awin_feed_*.bin` the preparation keeps in its cache): read row by row, never held
whole, by the advertiser's id (`merchant_id`). Awin's Offers API is then asked only for
their offers (`advertiserIds`), live now, for the United Kingdom, page by page; the first
read of every advertiser's offers (31/10) found 28 of PicWise's 85 shops among 4,463.

Written: one JSON file, not served to anyone, replaced whole only when the read is whole:
for each shop with an offer, its name, whether PicWise's account is joined to it, and its
offers live now by their own dates (`startDate`, `endDate`), each with its type, title,
description, terms and dates, and its voucher code and tracking link only where Awin gives
them (to joined programmes only). Printed: counts only, never a code or a title, since a
title can carry a code. The token and the account's id are never printed.

Exits 0 with a note when the token is not set; 1 when the feed's shops or Awin cannot be
read, the last good file kept.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import os
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

PROMOTIONS_API = "https://api.awin.com/publisher/{publisher}/promotions"
ACCOUNTS_API = "https://api.awin.com/accounts?type=publisher"
PAGE_SIZE = 200
# Awin allows a publisher about 20 calls a minute: one call every 3.5 seconds.
PAUSE_SECONDS = 3.5
MAX_PAGES = 50
# Advertisers asked for in one series of pages.
IDS_PER_CALL = 50
DEFAULT_CACHE_DIR = Path("/srv/picwise/shared/cache")
DEFAULT_OUT = Path("/srv/picwise/shared/offers/offers.json")
FEED_PATTERN = "picwise_awin_feed_*.bin"
_GZIP_MAGIC = b"\x1f\x8b"
csv.field_size_limit(sys.maxsize)

Post = Callable[[str, dict[str, Any], str], tuple[int, Any]]
Get = Callable[[str, str], tuple[int, Any]]


def _request(request: urllib.request.Request) -> tuple[int, Any]:
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, json.loads(response.read().decode("utf-8") or "null")
    except urllib.error.HTTPError as error:
        text = error.read().decode("utf-8", errors="replace")
        try:
            return error.code, json.loads(text)
        except ValueError:
            return error.code, text[:500]


def _post(url: str, body: dict[str, Any], token: str) -> tuple[int, Any]:
    return _request(urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json"},
    ))


def _get(url: str, token: str) -> tuple[int, Any]:
    return _request(urllib.request.Request(
        url, method="GET", headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    ))


def _redact(text: str, *secrets: str) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***")
    return text


def newest_feed(cache_dir: Path) -> Path | None:
    files = [path for path in cache_dir.glob(FEED_PATTERN) if path.is_file()]
    return max(files, key=lambda path: path.stat().st_mtime) if files else None


def feed_shops(path: Path) -> dict[str, str]:
    """PicWise's shops in the feed: the advertiser's id -> its name."""
    with open(path, "rb") as probe:
        gzipped = probe.read(2) == _GZIP_MAGIC
    binary = gzip.open(path, "rb") if gzipped else open(path, "rb")
    with io.TextIOWrapper(binary, encoding="utf-8-sig", errors="replace", newline="") as text:
        reader = csv.reader(text)
        header = [name.strip().lower() for name in next(reader, None) or []]
        id_at = next((header.index(name) for name in ("merchant_id", "advertiser_id") if name in header), None)
        name_at = next((header.index(name) for name in ("merchant_name", "advertiser_name") if name in header), None)
        if id_at is None:
            raise ValueError("the feed has no advertiser id column")
        shops: dict[str, str] = {}
        for row in reader:
            ident = row[id_at].strip() if id_at < len(row) else ""
            if ident.isdigit() and ident not in shops:
                name = " ".join(row[name_at].split()) if name_at is not None and name_at < len(row) else ""
                shops[ident] = name
        return shops


def find_publisher(token: str, *, get: Get = _get) -> str:
    """The one publisher account the token reaches; ValueError when not exactly one."""
    status, answer = get(ACCOUNTS_API, token)
    if status != 200:
        raise ValueError(f"Awin's accounts call answered {status}")
    rows = answer.get("accounts") if isinstance(answer, dict) else answer
    found = [
        str(row.get("accountId") or row.get("id") or "").strip()
        for row in (rows if isinstance(rows, list) else ())
        if isinstance(row, dict) and str(row.get("accountType") or row.get("type") or "publisher").lower() == "publisher"
    ]
    found = [ident for ident in found if ident]
    if len(found) != 1:
        raise ValueError(f"the token reaches {len(found)} publisher accounts: set AWIN_PUBLISHER_ID")
    return found[0]


def _items(answer: Any) -> list[dict[str, Any]]:
    if isinstance(answer, dict) and isinstance(answer.get("data"), list):
        return [item for item in answer["data"] if isinstance(item, dict)]
    if isinstance(answer, list):
        return [item for item in answer if isinstance(item, dict)]
    return []


def read_offers(
    publisher: str, token: str, advertiser_ids: list[str], *, post: Post = _post, pause: float = PAUSE_SECONDS
) -> list[dict[str, Any]]:
    """The live UK offers of these advertisers, each once, page by page, a series of
    pages for each group of `IDS_PER_CALL` advertisers. RuntimeError when Awin refuses."""
    url = PROMOTIONS_API.format(publisher=publisher)
    offers: list[dict[str, Any]] = []
    seen: set[str] = set()
    first_call = True
    for start in range(0, len(advertiser_ids), IDS_PER_CALL):
        group = [int(ident) for ident in advertiser_ids[start:start + IDS_PER_CALL]]
        for page in range(1, MAX_PAGES + 1):
            if not first_call:
                time.sleep(pause)
            first_call = False
            body = {
                "filters": {
                    "advertiserIds": group, "membership": "all", "regionCodes": ["GB"],
                    "status": "active", "type": "all",
                },
                "pagination": {"page": page, "pageSize": PAGE_SIZE},
            }
            status, answer = post(url, body, token)
            if status != 200:
                raise RuntimeError(f"Awin's offers call answered {status}")
            items = _items(answer)
            fresh = []
            for item in items:
                key = str(item.get("promotionId") or json.dumps(item, sort_keys=True, default=str))
                if key not in seen:
                    seen.add(key)
                    fresh.append(item)
            offers.extend(fresh)
            if len(items) < PAGE_SIZE or not fresh:
                break
    return offers


def _date(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _text(value: Any, limit: int) -> str:
    return " ".join(str(value or "").split())[:limit]


def keep(offer: dict[str, Any], shops: dict[str, str], *, now: datetime) -> tuple[str, dict[str, Any]] | None:
    """(the advertiser's id, what is kept of the offer), or None for an offer that is not
    live now by its own dates or is not of one of PicWise's shops."""
    advertiser = offer.get("advertiser") if isinstance(offer.get("advertiser"), dict) else {}
    ident = str(advertiser.get("id") or "").strip()
    if ident not in shops:
        return None
    start, end = _date(offer.get("startDate")), _date(offer.get("endDate"))
    # Only an offer valid now by Awin's own dates (owner, 2026-10-31: the end date Awin gives).
    if end is None or end < now or (start is not None and start > now):
        return None
    voucher = offer.get("voucher") if isinstance(offer.get("voucher"), dict) else {}
    code = _text(voucher.get("code"), 80)
    regions = offer.get("regions") if isinstance(offer.get("regions"), dict) else {}
    kept: dict[str, Any] = {
        "id": offer.get("promotionId"),
        "type": _text(offer.get("type"), 20),
        "title": _text(offer.get("title"), 300),
        "description": _text(offer.get("description"), 1000),
        "terms": _text(offer.get("terms"), 1000),
        "start": start.isoformat() if start else None,
        "end": end.isoformat(),
        "regions_all": bool(regions.get("all")),
    }
    if code:
        kept["code"] = code
        kept["exclusive"] = bool(voucher.get("exclusive"))
    tracking = _text(offer.get("urlTracking"), 2000)
    if tracking.startswith("https://"):
        kept["url"] = tracking
    return ident, {"advertiser": advertiser, "offer": kept}


def build(offers: list[dict[str, Any]], shops: dict[str, str], *, now: datetime) -> dict[str, Any]:
    by_shop: dict[str, dict[str, Any]] = {}
    for offer in offers:
        kept = keep(offer, shops, now=now)
        if kept is None:
            continue
        ident, parts = kept
        shop = by_shop.setdefault(ident, {
            "name": shops.get(ident) or _text(parts["advertiser"].get("name"), 200),
            "joined": bool(parts["advertiser"].get("joined")),
            "offers": [],
        })
        shop["offers"].append(parts["offer"])
    for shop in by_shop.values():
        shop["offers"].sort(key=lambda offer: (offer["end"], str(offer["id"])))
    return {
        "fetched_at": now.isoformat(),
        "source": "Awin Offers API (live offers for the United Kingdom)",
        "shops_in_feed": len(shops),
        "shops": dict(sorted(by_shop.items(), key=lambda item: item[1]["name"].lower())),
    }


def write(document: dict[str, Any], out: Path) -> None:
    """Replace the file whole, never half written."""
    out.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=out.parent, prefix=".offers.", delete=False)
    try:
        with handle:
            json.dump(document, handle, ensure_ascii=False, indent=1)
        os.replace(handle.name, out)
    except BaseException:
        Path(handle.name).unlink(missing_ok=True)
        raise


def summary(document: dict[str, Any]) -> list[str]:
    """Counts only: never a code, never a title."""
    shops = document["shops"]
    offers = sum(len(shop["offers"]) for shop in shops.values())
    codes = sum(1 for shop in shops.values() for offer in shop["offers"] if offer.get("code"))
    joined = sum(1 for shop in shops.values() if shop["joined"])
    lines = [
        f"offers: {offers} live, of {len(shops)} of the {document['shops_in_feed']} shops in the feed "
        f"(joined to {joined} of them); with a voucher code: {codes}"
    ]
    for shop in sorted(shops.values(), key=lambda shop: (-len(shop["offers"]), shop["name"].lower())):
        lines.append(f"  {len(shop['offers']):>4}  {shop['name'][:50]}{'  (joined)' if shop['joined'] else ''}")
    return lines


def main(argv: list[str] | None = None, *, post: Post = _post, get: Get = _get, now: datetime | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--feed-cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    token = str(os.environ.get("AWIN_API_TOKEN") or "").strip()
    publisher = str(os.environ.get("AWIN_PUBLISHER_ID") or "").strip()
    if not token:
        print("offers: no Awin token in the server's secrets; nothing fetched")
        return 0
    feed = newest_feed(args.feed_cache_dir)
    if feed is None:
        print("offers: no downloaded feed to read PicWise's shops from; the last file kept")
        return 1
    try:
        shops = feed_shops(feed)
        if not publisher:
            publisher = find_publisher(token, get=get)
        offers = read_offers(publisher, token, sorted(shops, key=int), post=post)
    except (ValueError, RuntimeError, OSError, urllib.error.URLError, TimeoutError) as error:
        print(_redact(f"offers: not fetched ({error}); the last file kept", token, publisher))
        return 1
    document = build(offers, shops, now=now or datetime.now(timezone.utc))
    write(document, args.out)
    for line in summary(document):
        print(_redact(line, token, publisher))
    return 0


if __name__ == "__main__":
    sys.exit(main())
