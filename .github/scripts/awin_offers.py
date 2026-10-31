"""The offers Awin gives PicWise's account: what there is, and for which of PicWise's shops.

    AWIN_API_TOKEN=... AWIN_PUBLISHER_ID=... python3 .github/scripts/awin_offers.py \
        [--shops-from https://picwise.subby.cloud/prepared.json]

Owner, 2026-10-31: «σχετικά με τις προσφορές στα καταστήματα πρέπει να τις τραβήξουμε»;
which product an offer is for is a later talk («αργότερα πρέπει να συσχετίσουμε ... αυτό
είναι άλλη συζήτηση»). This is the first step: read the offers once, on GitHub's runner
(the session that wrote this cannot reach api.awin.com), and print what they are, so the
owner sees them before anything is built on them.

Awin's Offers API (the promotions and vouchers of the "My Offers" page): a POST to
`/publisher/{id}/promotions` with the account's API token, page by page. Asked for: the
offers live now, for the United Kingdom, of every advertiser, joined or not. The answer's
shape is printed (its field names, never its values) before the counts, since it was
written from Awin's documentation without a token to try it.

Printed: the offers by type, how many carry a voucher code (never the code: an exclusive
code is the account's own, and this log is public), how many end within a week; the
advertisers with the most offers, and which of them are PicWise's shops, matched by
name against the shops of the server's public note (`prepared.json`). The token and the
account's id are secrets and never printed. Nothing on the server or the site changes.
Exits 1 when Awin refuses or cannot be read; 0 with a note when the secrets are not set.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

API = "https://api.awin.com/publisher/{publisher}/promotions"
PAGE_SIZE = 200
# Awin allows a publisher about 20 calls a minute: one page every 3.5 seconds.
PAUSE_SECONDS = 3.5
MAX_PAGES = 100
TOP_ADVERTISERS = 30
EXAMPLES_PER_SHOP = 3
SOON = timedelta(days=7)

Post = Callable[[str, dict[str, Any], str], tuple[int, Any]]


def _post(url: str, body: dict[str, Any], token: str) -> tuple[int, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, json.loads(response.read().decode("utf-8") or "null")
    except urllib.error.HTTPError as error:
        text = error.read().decode("utf-8", errors="replace")
        try:
            return error.code, json.loads(text)
        except ValueError:
            return error.code, text[:500]


def _items(answer: Any) -> list[dict[str, Any]]:
    """The offers of one page, wherever the answer keeps them."""
    if isinstance(answer, list):
        return [item for item in answer if isinstance(item, dict)]
    if isinstance(answer, dict):
        for key in ("data", "promotions", "offers", "items", "results"):
            if isinstance(answer.get(key), list):
                return [item for item in answer[key] if isinstance(item, dict)]
    return []


def _shape(value: Any, depth: int = 0) -> str:
    """Field names only, nested once: what Awin sends, without what it says."""
    if isinstance(value, dict):
        if depth >= 2:
            return "{...}"
        return "{" + ", ".join(f"{key}: {_shape(item, depth + 1)}" for key, item in value.items()) + "}"
    if isinstance(value, list):
        return f"[{_shape(value[0], depth + 1)}]" if value else "[]"
    return type(value).__name__


def read_offers(
    publisher: str, token: str, *, post: Post = _post, pause: float = PAUSE_SECONDS
) -> tuple[list[dict[str, Any]], Any]:
    """Every page of the live offers for the UK; the first answer as well, for its shape."""
    url = API.format(publisher=publisher)
    offers: list[dict[str, Any]] = []
    first: Any = None
    for page in range(1, MAX_PAGES + 1):
        body = {
            "filters": {"membership": "all", "regionCodes": ["GB"], "status": "active", "type": "all"},
            "pagination": {"page": page, "pageSize": PAGE_SIZE},
        }
        status, answer = post(url, body, token)
        if status != 200:
            raise RuntimeError(f"Awin answered {status}: {_redact(str(answer), token, publisher)[:300]}")
        if first is None:
            first = answer
        items = _items(answer)
        offers.extend(items)
        if len(items) < PAGE_SIZE:
            break
        time.sleep(pause)
    return offers, first


def _redact(text: str, *secrets: str) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, "***")
    return text


def _advertiser(offer: dict[str, Any]) -> tuple[str, str, Any]:
    """(id, name, joined) of the offer's advertiser, as far as the offer says."""
    advertiser = offer.get("advertiser") if isinstance(offer.get("advertiser"), dict) else {}
    ident = advertiser.get("id", offer.get("advertiserId", ""))
    name = advertiser.get("name", offer.get("advertiserName", ""))
    joined = advertiser.get("joined", offer.get("joined"))
    return str(ident or ""), " ".join(str(name or "").split()), joined


def _code(offer: dict[str, Any]) -> bool:
    voucher = offer.get("voucher")
    if isinstance(voucher, dict):
        return bool(str(voucher.get("code") or "").strip())
    return bool(str(offer.get("code") or offer.get("voucherCode") or "").strip())


def _date(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def shop_key(name: str) -> str:
    """A shop's name made comparable: lower case, letters and digits only, without the
    words networks add to it ("Geepas Partner Program" is Geepas's)."""
    words = re.sub(r"[^0-9a-z]+", " ", str(name or "").lower()).split()
    noise = {"uk", "ltd", "limited", "the", "partner", "program", "programme", "affiliate", "store", "shop", "official"}
    kept = [word for word in words if word not in noise]
    return "".join(kept or words)


def our_shops(note: Any) -> dict[str, tuple[str, int]]:
    """PicWise's shops from the server's public note: key -> (name, products shown)."""
    shops: dict[str, tuple[str, int]] = {}
    intake = note.get("intake") if isinstance(note, dict) else None
    for shop in (intake or {}).get("shops") or ():
        name = " ".join(str(shop.get("shop") or "").split())
        if name:
            shops[shop_key(name)] = (name, int(shop.get("shown") or 0))
    return shops


def report(offers: list[dict[str, Any]], first: Any, shops: dict[str, tuple[str, int]], *, now: datetime) -> list[str]:
    lines = [f"the answer's shape: {_shape(first)}"]
    if offers:
        lines.append(f"an offer's shape: {_shape(offers[0])}")
    lines.append(f"== {len(offers):,} live offers for the United Kingdom")
    if not offers:
        return lines
    types = Counter(str(offer.get("type") or "?") for offer in offers)
    lines.append("by type: " + ", ".join(f"{name} {count:,}" for name, count in types.most_common()))
    with_code = sum(1 for offer in offers if _code(offer))
    ending = sum(1 for offer in offers if (end := _date(offer.get("endDate"))) and now <= end <= now + SOON)
    no_end = sum(1 for offer in offers if _date(offer.get("endDate")) is None)
    lines.append(f"with a voucher code: {with_code:,}; ending within 7 days: {ending:,}; no end date: {no_end:,}")
    per_advertiser: dict[str, list[dict[str, Any]]] = {}
    names: dict[str, tuple[str, Any]] = {}
    for offer in offers:
        ident, name, joined = _advertiser(offer)
        key = ident or name or "?"
        per_advertiser.setdefault(key, []).append(offer)
        names[key] = (name or key, joined)
    lines.append(f"advertisers with an offer: {len(per_advertiser):,}")
    matched = {
        key: shops[shop_key(names[key][0])]
        for key in per_advertiser
        if shop_key(names[key][0]) in shops
    }
    lines.append(
        f"== PicWise's shops with an offer: {len(matched)} of {len(shops)}"
        + ("" if shops else " (the shops could not be read)")
    )
    for key, (shop, shown) in sorted(matched.items(), key=lambda item: -len(per_advertiser[item[0]])):
        own = per_advertiser[key]
        joined = names[key][1]
        lines.append(
            f"  {shop} ({shown:,} products shown): {len(own)} offers"
            + ("" if joined is None else f", joined: {'yes' if joined else 'no'}")
        )
        for offer in own[:EXAMPLES_PER_SHOP]:
            end = _date(offer.get("endDate"))
            title = " ".join(str(offer.get("title") or "").split())[:90]
            lines.append(
                f"      {offer.get('type') or '?'} | until {end.date() if end else '-'} | "
                f"code: {'yes' if _code(offer) else 'no'} | {title}"
            )
    lines.append(f"== the advertisers with the most offers (shop of PicWise or not), the first {TOP_ADVERTISERS}")
    for key, own in sorted(per_advertiser.items(), key=lambda item: (-len(item[1]), names[item[0]][0]))[:TOP_ADVERTISERS]:
        name, joined = names[key]
        mark = "PicWise's shop" if key in matched else "-"
        lines.append(
            f"  {len(own):>5}  {name[:50]:50}  {mark}"
            + ("" if joined is None else f"  joined: {'yes' if joined else 'no'}")
        )
    return lines


def _read_note(url: str) -> Any:
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, ValueError, TimeoutError) as error:
        print(f"the shops could not be read from the note: {error}")
        return None


def main(argv: list[str] | None = None, *, post: Post = _post, note: Any = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--shops-from", help="the server's public note, prepared.json, for PicWise's shops")
    args = parser.parse_args(argv)
    token = str(os.environ.get("AWIN_API_TOKEN") or "").strip()
    publisher = str(os.environ.get("AWIN_PUBLISHER_ID") or "").strip()
    missing = [name for name, value in (("AWIN_API_TOKEN", token), ("AWIN_PUBLISHER_ID", publisher)) if not value]
    if missing:
        print(f"not in GitHub's secrets yet: {', '.join(missing)}; nothing read")
        return 0
    if note is None and args.shops_from:
        note = _read_note(args.shops_from)
    try:
        offers, first = read_offers(publisher, token, post=post)
    except (RuntimeError, urllib.error.URLError, TimeoutError, ValueError) as error:
        print(_redact(f"the offers could not be read: {error}", token, publisher))
        return 1
    for line in report(offers, first, our_shops(note), now=datetime.now(timezone.utc)):
        print(_redact(line, token, publisher))
    return 0


if __name__ == "__main__":
    sys.exit(main())
