"""Compare the site on PicWise's server with the live site on Vercel, page by page.

    python3 deployment/server/compare_with_vercel.py --server http://127.0.0.1:18016

Run by .github/workflows/server-deploy.yml after a deployment, through an SSH tunnel to
the server's private port. The server is asked as the live site's host over HTTPS
(`Host`, `X-Forwarded-Proto`), so its pages carry the same links. Public pages only:
nothing is written anywhere and no "/out/" link is opened, since that counts as a click
on the shop. Prints, per page, the answer of each site and how they differ; then, once
the server has a prepared catalogue, the cards of the live check's 12 searches on each
site (price, shop, role, title). Exits 1 only when the server fails to answer a page.

    python3 deployment/server/compare_with_vercel.py --server ... --catalogue catalogue.json.gz

With the server's prepared catalogue (owner, 2026-10-25, while fixing the kinds a title
alone gives: a card shows no shelf, so a wrong card could not be traced), each server
card also gets the shelf and the kinds it was read with, found by its title. The file
stays on the runner; only those two are printed, never a link.
"""
from __future__ import annotations

import argparse
import difflib
import html
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

LIVE_SITE = "https://picwise.subby.cloud"
LIVE_HOST = "picwise.subby.cloud"
PATHS = (
    "/",
    "/terms",
    "/privacy",
    "/cookies",
    "/affiliate-disclosure",
    "/contact",
    "/robots.txt",
    "/health",
    "/suggest.json",
    "/sitemap-buying-pages.xml",
    "/no-such-page",
    "/demo",
    "/search?q=kettle",
    "/private-beta-readiness",
    "/prepared.json",
)
# The searches of the live check (.github/workflows/live-check.yml on ccr-fd5dc1bc-4vgsgl).
SEARCHES = (
    "tv",
    "laptop",
    "headphones",
    "ακουστικά",
    "kettle",
    "mouse",
    "keyboard",
    "phone charger",
    "camera",
    "speaker",
    "smartwatch",
    "vacuum cleaner",
)
HEADERS = ("content-type", "x-robots-tag", "cache-control")
# How much of a server card's shelf is printed.
SHELF_LENGTH = 110
USER_AGENT = "PicWise-server-compare/1 (GitHub Actions; the owner's own check)"
DIFF_LINES = 12


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def fetch(url: str, headers: dict[str, str]) -> tuple[int, dict[str, str], str]:
    """(status, the compared headers, body); status 0 when nothing answered."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **headers})
    try:
        with _OPENER.open(request, timeout=120) as response:
            status, raw_headers, body = response.status, response.headers, response.read()
    except urllib.error.HTTPError as error:
        status, raw_headers, body = error.code, error.headers, error.read()
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        return 0, {}, f"no answer: {type(error).__name__}"
    kept = {name: str(raw_headers.get(name) or "") for name in HEADERS}
    return status, kept, body.decode("utf-8", "replace")


def comparable_lines(body: str, content_type: str) -> list[str]:
    """The body split so that a difference shows as a few lines: JSON by key, HTML by tag."""
    if "json" in content_type:
        try:
            return json.dumps(json.loads(body), indent=1, sort_keys=True, ensure_ascii=False).splitlines()
        except ValueError:
            pass
    return re.sub(r">\s*<", ">\n<", body).splitlines()


def _text(fragment: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def card_titles(page: str) -> list[str]:
    """The whole title of each card of a search page, in order."""
    titles = []
    for card in re.findall(r'<article class="pw-card.*?</article>', page, re.S):
        title = re.search(r'class="pw-card-title">(.*?)</h2>', card, re.S)
        titles.append(_text(title.group(1)) if title else "")
    return titles


def catalogue_shelves(path: str) -> dict[str, str]:
    """Per product title of the prepared catalogue at `path`, the shelf and the kinds the
    search read it with, the first product of a title for all; empty when the file
    cannot be read with this checkout's code."""
    root = Path(__file__).resolve().parents[2]
    for folder in (root, root / "src"):
        if str(folder) not in sys.path:
            sys.path.insert(0, str(folder))
    try:
        from picwise_providers.prepared_catalogue import read_prepared_catalogue

        prepared = read_prepared_catalogue(Path(path))
    except Exception as error:  # a diagnosis only: the comparison goes on without it
        print(f"=== no shelves for the cards: {type(error).__name__}")
        return {}
    if prepared is None:
        print("=== no shelves for the cards: the prepared catalogue cannot be read with this code")
        return {}
    shelves: dict[str, str] = {}
    fields = prepared.search_fields or tuple({} for _product in prepared.products)
    for product, kinds, product_fields in zip(prepared.products, prepared.kinds, fields):
        title = " ".join(str(product.title or "").split())
        if title not in shelves:
            shelf = str(product_fields.get("category") or product.category_text or "-")
            shelves[title] = f"{shelf[:SHELF_LENGTH]} | {', '.join(sorted(kinds)) or '-'}"
    return shelves


def search_cards(page: str) -> list[str]:
    """The counter and one line per card of a search page, as the live check prints them."""
    counter = re.search(r'class="pw-counter">([^<]*)<', page)
    lines = [f"counter: {counter.group(1) if counter else '-'}"]
    for card in re.findall(r'<article class="pw-card.*?</article>', page, re.S):
        title = re.search(r'class="pw-card-title">(.*?)</h2>', card, re.S)
        price = re.search(r'class="pw-price">(.*?)</p>', card, re.S)
        meta = re.search(r'class="pw-meta">(.*?)</p>', card, re.S)
        role = re.search(r'class="pw-role-label">(.*?)</p>', card, re.S)
        shop = _text(meta.group(1)).split("Provider:")[-1].strip() if meta else ""
        lines.append(
            f"{_text(price.group(1)) if price else '?':>12} | {shop[:28]:28} | "
            f"{_text(role.group(1)) if role else '':22} | {_text(title.group(1))[:70] if title else '?'}"
        )
    return lines


def compare_searches(
    live_site: str, server_site: str, server_headers: dict[str, str], shelves: dict[str, str] | None = None
) -> int:
    """Prints both sites' cards for each search, each server card with its shelf and kinds
    when `shelves` has them; returns how many searches show the same."""
    same = 0
    for query in SEARCHES:
        path = "/search?q=" + urllib.parse.quote_plus(query)
        live = fetch(live_site + path, {})
        server = fetch(server_site + path, server_headers)
        live_cards, server_cards = search_cards(live[2]), search_cards(server[2])
        server_shelves = [(shelves or {}).get(title, "-") for title in card_titles(server[2])] if shelves else []
        print(f"=== {path} ({query})")
        if live[0] == server[0] and live_cards == server_cards:
            same += 1
            print(f"  the same cards on both ({live[0]})")
            print_cards(live_cards, server_shelves)
            continue
        print(f"  live   {live[0]}")
        print_cards(live_cards, [])
        print(f"  server {server[0]}")
        print_cards(server_cards, server_shelves)
    return same


def print_cards(lines: list[str], shelves: list[str]) -> None:
    """The counter, then each card, followed by its shelf and kinds when known."""
    for index, line in enumerate(lines):
        print("    " + line)
        if 0 < index <= len(shelves):
            print("        shelf: " + shelves[index - 1])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--server", required=True, help="the server's site, e.g. http://127.0.0.1:18016")
    parser.add_argument("--live", default=LIVE_SITE)
    parser.add_argument("--catalogue", help="the server's prepared catalogue, to give each server card its shelf")
    args = parser.parse_args(argv)
    server_headers = {"Host": LIVE_HOST, "X-Forwarded-Proto": "https"}
    same = 0
    server_failed = 0
    for path in PATHS:
        live = fetch(args.live + path, {})
        server = fetch(args.server + path, server_headers)
        print(f"=== {path}")
        for label, (status, headers, body) in (("live  ", live), ("server", server)):
            shown = ", ".join(f"{name}: {value}" for name, value in headers.items() if value)
            print(f"  {label} {status} {len(body):>7} chars  {shown}")
        if server[0] == 0 or server[0] >= 500:
            server_failed += 1
        # Vercel adds headers of its own (a cache rule, for one), so they are named, and
        # a page counts as the same when its answer and its content are.
        for name in HEADERS:
            if live[1].get(name, "") != server[1].get(name, ""):
                print(f"  header {name} differs")
        if live[0] == server[0] and live[2] == server[2]:
            same += 1
            print("  content the same")
            continue
        content_type = server[1].get("content-type", "") or live[1].get("content-type", "")
        diff = [
            line
            for line in difflib.unified_diff(
                comparable_lines(live[2], content_type),
                comparable_lines(server[2], content_type),
                "live",
                "server",
                n=0,
                lineterm="",
            )
            if not line.startswith(("---", "+++", "@@"))
        ]
        print(f"  {len(diff)} lines differ (- live, + server); the first {min(DIFF_LINES, len(diff))}:")
        for line in diff[:DIFF_LINES]:
            print("    " + (line if len(line) <= 200 else line[:200] + " ..."))
    print(f"=== {same} of {len(PATHS)} pages with the same answer and content; the server failed {server_failed}")
    note = fetch(args.server + "/prepared.json", server_headers)
    try:
        prepared = note[0] == 200 and bool(json.loads(note[2]).get("prepared"))
    except ValueError:
        prepared = False
    if not prepared:
        print("=== the searches are not compared: the server has no prepared catalogue")
    else:
        shelves = catalogue_shelves(args.catalogue) if args.catalogue else None
        same_searches = compare_searches(args.live, args.server, server_headers, shelves)
        print(f"=== {same_searches} of {len(SEARCHES)} searches show the same cards on both")
    return 1 if server_failed else 0


if __name__ == "__main__":
    sys.exit(main())
