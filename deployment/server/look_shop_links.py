"""A look at the links of a few shops' products, as the prepared catalogue holds them (owner,
2026-11-24: PCHUB.UK's buy buttons do not lead to the shop, «βγάζεις σφάλμα 503 αν θυμάμαι
καλά»). Read as text, never an Awin link opened.

    ssh picwise 'sudo systemd-run ... /usr/bin/python3 - [--shop "PCHUB.UK" ...]' < deployment/server/look_shop_links.py

Run once by .github/workflows/server-look-shop-links.yml, on the server, as the site's user,
with the release in use as its working directory and its code on PYTHONPATH. It changes
nothing.

Per shop: how many products; the kind of link a button leads to (`pclick.php`, `cread.php`,
the shop's own); the parameters of Awin's link by name only, and whether its product number
is the row's id and its advertiser the row's; HTML codes left in a link or a title ("&amp;",
"&quot;"); the shop's own address (`merchant_deep_link`): its host, its shape. Then, for the
shops asked (`--ask`), a few of their own pages asked once from the server, as robots.txt
allows, a few seconds apart, exactly as the row writes the address and again with the HTML
codes read: their status. Never an Awin link. Prints hosts, counts and parameter names,
never a whole address and never a link.
"""
from __future__ import annotations

import argparse
import html
import os
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import parse_qsl, urlsplit

sys.path.insert(0, os.path.join(os.getcwd(), "deployment", "bot"))
sys.path.insert(0, os.path.join(os.getcwd(), "deployment", "server"))

PREPARED = "/srv/picwise/shared/prepared/catalogue.json.gz"
SHOPS = ("PCHUB.UK", "Back to the Office", "GamingKit", "Tooled Up")
ASK = ("PCHUB.UK",)
PAGES = 24
_ENTITY = re.compile(r"&(?:amp|quot|lt|gt|apos|#\d+|#x[0-9a-f]+);", re.IGNORECASE)


def link_kind(url: str) -> str:
    parts = urlsplit(str(url or ""))
    host = parts.netloc.lower()
    if "awin1.com" in host:
        return "Awin " + (parts.path.rsplit("/", 1)[-1] or "link")
    if parts.scheme in ("http", "https") and host:
        return "the shop's own link"
    return "not a link"


def param_names(url: str) -> str:
    """The names of a link's parameters, in order ("p,a,m"); a name an HTML code broke shows
    as it is read ("amp;a")."""
    return ",".join(name for name, _value in parse_qsl(urlsplit(str(url or "")).query, keep_blank_values=True))


def shape(url: str) -> str:
    """An address's shape, never the address: its scheme, whether it has a query, how it ends."""
    parts = urlsplit(str(url or ""))
    if not parts.netloc:
        return "no address"
    path = parts.path or "/"
    depth = len([segment for segment in path.split("/") if segment])
    end = "the home page" if depth == 0 else (
        ("ends .html" if path.endswith(".html") else ("ends /" if path.endswith("/") else "other path"))
        + f", {depth} part{'s' if depth > 1 else ''}")
    query = "with query (" + ",".join(name for name, _ in parse_qsl(parts.query, keep_blank_values=True)) + ")" \
        if parts.query else "no query"
    return f"{parts.scheme} {end} {query}"


def look_at(products: list[Any]) -> dict[str, Any]:
    from picwise_providers.normalization import extract_merchant_name

    shops: dict[str, Counter] = defaultdict(Counter)
    for product in products:
        raw = product.raw if isinstance(product.raw, dict) else {}
        shop = extract_merchant_name(raw) or "unknown"
        tally = shops[shop]
        url = str(product.product_url or "")
        own = str(raw.get("merchant_deep_link") or "")
        tally["products"] += 1
        tally["link: " + link_kind(url)] += 1
        tally["params: " + (param_names(url) or "none")] += 1
        if _ENTITY.search(url):
            tally["HTML code in the button's link"] += 1
        if _ENTITY.search(own):
            tally["HTML code in the shop's own address"] += 1
        if _ENTITY.search(str(product.title or "")):
            tally["HTML code in the title"] += 1
        if "awin1.com" in url:
            query = dict(parse_qsl(urlsplit(url).query, keep_blank_values=True))
            number = query.get("p") or query.get("amp;p") or ""
            if number:
                tally["Awin's product number " + ("= the row's id" if number == str(product.provider_product_id)
                                                  else "!= the row's id")] += 1
            advertiser = query.get("m") or query.get("amp;m") or query.get("mid") or query.get("amp;mid") or ""
            row_advertiser = str(raw.get("merchant_id") or "").strip()
            if advertiser and row_advertiser:
                tally["Awin's advertiser " + ("= the row's" if advertiser == row_advertiser else "!= the row's")] += 1
        tally["own host: " + (urlsplit(own).netloc.lower() or "none")] += 1
        tally["own shape: " + shape(own)] += 1
    return shops


def ask_pages(products: list[Any], shop: str, *, pages: int, fetch=None, sleep=time.sleep,
              clock=time.monotonic) -> list[str]:
    """A few of a shop's own pages asked once, as robots.txt allows: as written, and again with
    the HTML codes read when the row carries some. Never an Awin link."""
    import look_cards
    import shop_catalogue_test as look
    from picwise_providers.normalization import extract_merchant_name

    asker = look_cards.Asker(fetch or look.fetch, sleep, clock)
    lines = []
    chosen = [p for p in products
              if (extract_merchant_name(p.raw if isinstance(p.raw, dict) else {}) or "") == shop]
    # As many of each shape of address as the pages allow, spread over the shop's products.
    by_shape: dict[str, list[Any]] = defaultdict(list)
    for product in chosen:
        by_shape[shape(str((product.raw if isinstance(product.raw, dict) else {}).get("merchant_deep_link") or ""))].append(product)
    each = max(1, pages // max(1, len(by_shape)))
    picked = []
    for group in by_shape.values():
        step = max(1, len(group) // each)
        picked.extend(group[::step][:each])
    for product in picked:
        raw = product.raw if isinstance(product.raw, dict) else {}
        own = str(raw.get("merchant_deep_link") or "").strip()
        if not own or "awin1.com" in urlsplit(own).netloc.lower():
            lines.append("   no own address to ask")
            continue
        tries = [("as written", own)]
        if _ENTITY.search(own):
            tries.append(("codes read", html.unescape(own)))
        said = []
        for name, address in tries:
            answer = asker.page(address)
            said.append(f"{name}: {answer if isinstance(answer, str) else look._said(answer)}")
        lines.append(f"   {shape(own)} | " + "; ".join(said))
    lines.append(f"   requests to the shop: {asker.requests}")
    return lines


def main(argv: list[str] | None = None, *, prepared: Any = None, fetch=None, sleep=time.sleep) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--shop", action="append", help="a shop's name as the feed writes it (again for more)")
    parser.add_argument("--ask", action="append", help="a shop whose own pages to ask (again for more)")
    parser.add_argument("--pages", type=int, default=PAGES)
    parser.add_argument("--prepared", default=PREPARED)
    args = parser.parse_args(argv)
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass
    if prepared is None:
        from picwise_providers.prepared_catalogue import read_prepared_catalogue_to_measure

        prepared = read_prepared_catalogue_to_measure(Path(args.prepared))
        if prepared is None:
            print("the prepared catalogue could not be read")
            return 1
    print(f"the prepared catalogue of {prepared.prepared_at:%Y-%m-%d %H:%M} UTC: {len(prepared.products):,} products")
    wanted = tuple(args.shop or SHOPS)
    shops = look_at(list(prepared.products))
    for shop in wanted:
        tally = shops.get(shop)
        print(f"== {shop}: " + (f"{tally['products']:,} products" if tally else "not in the catalogue"))
        if not tally:
            continue
        for key, count in sorted(tally.items(), key=lambda item: (item[0].split(":")[0], -item[1])):
            if key != "products":
                print(f"   {count:>7,}  {key}")
    for shop in tuple(args.ask or ASK):
        print(f"== {shop}: its own pages, asked from the server")
        for line in ask_pages(list(prepared.products), shop, pages=args.pages, fetch=fetch, sleep=sleep):
            print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
