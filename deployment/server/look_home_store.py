"""The look before the «ανέβασε» of the home page as a store (task H5;
docs/PICWISE_HOME_STORE_SPEC.md, sections 9 and 10.2): this commit's pages, the switch on in
this process alone, on the server's own data. Read-only: nothing on the server or the site
changes, no shop is asked, nothing is asked of any AI, no search is kept.

    ssh picwise "sudo systemd-run ... /bin/sh -c 'mkdir /tmp/look && cd /tmp/look && tar xzf - \
        && exec /usr/bin/python3 deployment/server/look_home_store.py'" < code.tgz > pages.tgz

Run once by .github/workflows/server-look-home-store.yml, on the server, as the site's user,
in a unit of its own whose files are read-only, from a copy of this commit's code in the
unit's private temporary folder (it goes with the unit). The report is printed on standard
error (the log, which is public: shops, titles and prices as the site shows them, hosts
never, no address, no link); a few of the pages go to standard output as a gzipped tar, for
the runner's browser to measure (deployment/server/measure_store_pages.py).

1. **The switch off, nothing changes.** Today's pages and the live check's searches, asked
   of the running site on the server itself (as the deployment's own comparison asks them)
   and of this commit's code in this process: the same bytes, or what differs.
2. **The night's facts** (`home_store_facts`), as each of the site's workers would work
   them out after a night's catalogue: their time, each search's, and this process's
   memory before and after.
3. **Every department's kinds** (`data/home_departments.json`): what kind each one's words
   are understood as, how many products, from what price, its Recommended; the words that
   are understood as another kind, or show nothing.
4. **The pages, the switch on**: each answering, its words, never "compare"; every link
   inside the site followed in this process (never a shop's button), none broken, none
   leading out; each Recommended on a page against its own search's first card; each offer
   against its products' page.
"""
from __future__ import annotations

import argparse
import html
import io
import json
import os
import re
import statistics
import sys
import tarfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

SITE = "http://127.0.0.1:8016"
LIVE_HOST = "picwise.subby.cloud"
USER_AGENT = "PicWise-look-home-store/1 (the owner's own look; read-only)"
# The site's own settings (deployment/server/picwise-web.service), but: no folder for the
# searches (none is kept) and no key of any AI (none is in this unit: nothing can be asked).
SETTINGS = {
    "PICWISE_PREPARED_CATALOGUE_FILE": "/srv/picwise/shared/prepared/catalogue.json.gz",
    "PICWISE_STATIC_DIR": "/srv/picwise/shared/public",
    "PICWISE_OFFERS_FILE": "/srv/picwise/shared/offers/offers.json",
    "PICWISE_GONE_PHOTOS_FILE": "/srv/picwise/shared/photos/gone.json",
    "PICWISE_ASSIST_DIR": "/srv/picwise/assist",
    "PICWISE_FAMILIES_FILE": "/srv/picwise/assist/families/answers/families.json",
    "PICWISE_CATALOGUE_KEEPER": "off",
    "PYTHONDONTWRITEBYTECODE": "1",
}
# Today's pages (deployment/server/compare_with_vercel.py), "/about", and the addresses this
# work adds, which are not found while the switch is off.
TODAY = (
    "/", "/about", "/terms", "/privacy", "/cookies", "/affiliate-disclosure", "/contact", "/robots.txt",
    "/suggest.json", "/sitemap-buying-pages.xml", "/no-such-page", "/demo", "/private-beta-readiness", "/prepared.json",
    "/departments", "/department/kitchen", "/offers", "/offers/1", "/how-picwise-works", "/how-we-choose", "/our-checks",
    "/our-shops",
)
SEARCHES = ("tv", "laptop", "headphones", "ακουστικά", "kettle", "mouse", "keyboard", "phone charger", "camera",
            "speaker", "smartwatch", "vacuum cleaner")
INFO = ("/about", "/contact", "/terms", "/privacy", "/cookies", "/affiliate-disclosure")
FOUR = ("/how-picwise-works", "/how-we-choose", "/our-checks", "/our-shops")


def say(*parts: Any) -> None:
    print(*parts, file=sys.stderr, flush=True)


def memory() -> tuple[int, int]:
    """(now, the most so far) of this process, in MB."""
    now = peak = 0
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith("VmRSS:"):
            now = int(line.split()[1]) // 1024
        elif line.startswith("VmHWM:"):
            peak = int(line.split()[1]) // 1024
    return now, peak


def text_of(fragment: str) -> str:
    fragment = re.sub(r"<(script|style)\b.*?</\1>", " ", fragment, flags=re.S)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def no_address(words: str) -> str:
    return re.sub(r"https?://\S+", "<address>", words)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        return None


def running(path: str) -> tuple[int, bytes]:
    """A page of the running site, asked on the server itself as the live site's host."""
    request = urllib.request.Request(
        SITE + urllib.request.quote(path, safe="/?=&%"),
        headers={"Host": LIVE_HOST, "X-Forwarded-Proto": "https", "User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.build_opener(_NoRedirect).open(request, timeout=120) as answer:
            return answer.status, answer.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()
    except OSError:
        return 0, b""


def asker(app: Callable[..., Any]) -> Callable[[str], tuple[int, dict[str, str], bytes]]:
    def ask(path: str) -> tuple[int, dict[str, str], bytes]:
        """A page of this commit's code, in this process, asked as the same host."""
        where, _, query = path.partition("?")
        seen: dict[str, Any] = {}

        def start_response(status: str, headers: list[tuple[str, str]], *_more: Any) -> None:
            seen["status"], seen["headers"] = int(status.split()[0]), dict(headers)

        environ = {
            "REQUEST_METHOD": "GET", "PATH_INFO": where, "QUERY_STRING": urllib.request.quote(query, safe="=&%+"),
            "SERVER_NAME": LIVE_HOST, "SERVER_PORT": "443", "HTTP_HOST": LIVE_HOST, "HTTP_X_FORWARDED_PROTO": "https",
            "HTTP_USER_AGENT": USER_AGENT, "wsgi.url_scheme": "https", "wsgi.input": io.BytesIO(b""),
            "wsgi.errors": sys.stderr, "SERVER_PROTOCOL": "HTTP/1.1",
        }
        body = b"".join(app(environ, start_response))
        return seen.get("status", 0), seen.get("headers", {}), body

    return ask


def cards_of(page: str) -> list[dict[str, str]]:
    cards = []
    for card in re.findall(r'<article class="pw-card.*?</article>', page, re.S):
        title = re.search(r'class="pw-card-title">(.*?)</h2>', card, re.S)
        price = re.search(r'class="pw-price">(.*?)</p>', card, re.S)
        shop = re.search(r'class="pw-card-shop">(.*?)</p>', card, re.S)
        cards.append({
            "title": text_of(title.group(1)) if title else "",
            "price": text_of(price.group(1)) if price else "",
            "shop": text_of(shop.group(1)) if shop else "",
            "recommended": "yes" if "pw-card-recommended" in card.split(">", 1)[0] else "",
            "role": text_of(m.group(1)) if (m := re.search(r'class="pw-role-label">(.*?)</p>', card, re.S)) else "",
        })
    return cards


def links_of(page: str) -> list[str]:
    body = re.sub(r"<(script|style)\b.*?</\1>", " ", page, flags=re.S)
    return [html.unescape(href) for href in re.findall(r'<a\b[^>]*\bhref="([^"]*)"', body)]


def first_difference(old: bytes, new: bytes) -> str:
    a = re.sub(r">\s*<", ">\n<", old.decode("utf-8", "replace")).splitlines()
    b = re.sub(r">\s*<", ">\n<", new.decode("utf-8", "replace")).splitlines()
    for index, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return f"line {index + 1} of {len(a)}/{len(b)}: running «{no_address(text_of(x) or x[:90])[:110]}» | this «{no_address(text_of(y) or y[:90])[:110]}»"
    return f"{len(a)} lines against {len(b)}"


def part_one(ask: Callable[..., Any]) -> None:
    say("\n== 1. The switch off: today's pages and searches, the running site against this commit ==")
    same = differ = 0
    for path in TODAY + tuple(f"/search?q={query}" for query in SEARCHES):
        old_status, old = running(path)
        new_status, _headers, new = ask(path)
        if old_status == 0:
            say(f"  {path}: the running site did not answer")
            differ += 1
        elif (old_status, old) == (new_status, new):
            same += 1
            say(f"  same     {old_status} {len(old):>7,} bytes  {path}")
        else:
            differ += 1
            say(f"  DIFFERS  {old_status}/{new_status} {len(old):,}/{len(new):,} bytes  {path}\n           {first_difference(old, new)}")
    say(f"  {same} the same, {differ} not")


def part_two() -> tuple[Any, Any, dict[str, Any]]:
    from picwise_providers import state
    from picwise_surface import home_store, home_store_facts

    say("\n== 2. The night's facts, as one worker works them out ==")
    now, peak = memory()
    say(f"  memory before: {now:,} MB (the most so far {peak:,} MB); the site runs 3 workers")
    started = time.monotonic()
    home = home_store_facts.work_out_home_facts()
    took_home = time.monotonic() - started
    home_store_facts.set_home_facts_for_tests(home)
    now, peak = memory()
    say(f"  the home page's facts: {took_home:.1f} s; memory {now:,} MB (most {peak:,} MB)")
    say(f"    Recommended on the band: {len(home.picks)} of {len(home_store.load_home_lists().recommended)}; "
        f"tiles with products: {len(home.tiles_with_products or ())}; shops: {home.shop_count} "
        f"(the catalogue's own count: {(state.peek_search_catalogue_counts() or (0, 0))[1]}); "
        f"offers on the row: {len(home.offers)}; offers in all: {len(home.all_offers)}")
    times: list[tuple[float, str]] = []
    answers: dict[str, Any] = {}

    def search(query: str) -> Any:
        begun = time.monotonic()
        try:
            answer = home_store_facts._whole_answer_search(query)
        finally:
            times.append((time.monotonic() - begun, query))
        answers[query] = answer
        return answer

    started = time.monotonic()
    kinds = home_store_facts.work_out_kind_facts(search=search)
    took_kinds = time.monotonic() - started
    home_store_facts.set_kind_facts_for_tests(kinds)
    now, peak = memory()
    each = sorted(t for t, _q in times)
    say(f"  the departments' facts: {took_kinds:.1f} s for {len(times)} searches (each as far as \"More\" opens it): "
        f"median {statistics.median(each) * 1000:.0f} ms, the slowest {each[-1] * 1000:.0f} ms "
        f"({', '.join(q for _t, q in sorted(times, reverse=True)[:4])}); memory {now:,} MB (most {peak:,} MB)")
    say(f"    kinds with products: {len(kinds.kinds)} of {len(times)}; offers with a department's kind: {len(kinds.offer_kinds)}")
    say(f"  together {took_home + took_kinds:.1f} s a worker, after each night's catalogue, in a thread beside its requests")
    return home, kinds, answers


def part_three(kinds: Any, answers: dict[str, Any]) -> None:
    from picwise_nlu.concept_understanding import understand_product_query
    from picwise_surface import home_store

    say("\n== 3. Every department's kinds, by their own words ==")
    departments = home_store.load_departments()
    other: list[str] = []
    nothing: list[str] = []
    for slug, items in departments.kinds.items():
        shown = []
        for item in items:
            understood = str(understand_product_query(item.query).concept_id or "")
            fact = kinds.kinds.get(item.query)
            answer = answers.get(item.query)
            status = str(getattr(answer, "provider_feed_selection_status", "") or "")
            if understood != item.kind:
                other.append(f"{slug}: «{item.query}» ({item.name}) is understood as «{understood or 'nothing'}», not «{item.kind}»"
                             + (f"; {fact.count} products" if fact else "; shows nothing"))
            if fact is None:
                nothing.append(f"{slug}: {item.name} «{item.query}» [{status or 'no answer'}]")
                continue
            pick = f" | Rec {fact.pick.price} {fact.pick.shop}: {fact.pick.title[:46]}" if fact.pick else " | no Recommended"
            shown.append((fact.count, f"    {item.name}: {fact.count:,} from {fact.low}{pick}"))
        say(f"  {slug}: {len(shown)} of {len(items)} kinds with products")
        for _count, line in sorted(shown, key=lambda pair: -pair[0]):
            say(line)
    say(f"\n  words understood as another kind: {len(other)}")
    for line in other:
        say("    " + line)
    say(f"  kinds that show nothing tonight (not drawn): {len(nothing)}")
    for line in nothing:
        say("    " + line)


def part_four(ask: Callable[..., Any], home: Any, kinds: Any, before: dict[str, bytes]) -> dict[str, bytes]:
    from picwise_surface import home_store

    say("\n== 4. The pages, the switch on ==")
    pages: dict[str, bytes] = {}
    departments = [d.slug for d in home_store.load_home_lists().departments if len(home_store.load_departments().kinds.get(d.slug, ())) > 1]
    offers = list(home.all_offers)
    paths = ["/", "/departments", *(f"/department/{slug}" for slug in departments), "/offers", *FOUR, *INFO,
             *(f"/search?q={query}" for query in SEARCHES)]
    failed = 0
    for path in paths:
        begun = time.monotonic()
        status, headers, body = ask(path)
        took = (time.monotonic() - begun) * 1000
        pages[path] = body
        page = body.decode("utf-8", "replace")
        words = text_of(page.split("<body", 1)[-1])
        notes = []
        if status != 200:
            failed += 1
            notes.append("NOT 200")
        store = not path.startswith("/search")
        if store and re.search(r"compar", words, re.I):
            notes.append("says «compar…»")
        if 'class="pw-hs-head"' not in page:
            notes.append("NOT under the store's header")
        if "No Cookie Policy" not in words:
            notes.append("no footer line")
        robots = "noindex" if re.search(r'<meta name="robots" content="noindex', page) else "indexable"
        say(f"  {status} {len(body):>7,} bytes {took:>5.0f} ms  {robots:9}  {path}  {' / '.join(notes)}")
    say(f"  {len(paths)} pages, {failed} not answering")

    # What the home page shows of tonight.
    home_page = pages["/"].decode("utf-8", "replace")
    words = text_of(home_page.split("<body", 1)[-1])
    ticks = re.search(r'<ul class="pw-hs-trust">(.*?)</ul>', home_page, re.S)
    markup = re.sub(r"<(script|style)\b.*?</\1>", "", home_page, flags=re.S)
    banners = markup.count('class="pw-hs-banner pw-hs-banner-')
    row = markup.count('class="pw-hs-offer"')
    band = markup.count('class="pw-hs-pick"')
    strip = "yes" if "pw-hs-strip" in markup else "no"
    say(f"  the home page: ticks «{text_of(ticks.group(1)) if ticks else 'none'}»; banners {banners}; "
        f"offers on the row {row}; Recommended cards {band}; strip drawn: {strip}")
    shops = re.search(r"Some of our ([\d,]+) UK shops", words)
    say(f"    «{shops.group(0) if shops else 'no shops line'}»; our-shops: «{text_of(pages['/our-shops'].decode('utf-8', 'replace')).split('ABOUT PICWISE Our shops ', 1)[-1][:60]}»")
    # Before tonight's facts were known: the same pages, what they left out.
    for path, body in before.items():
        page = re.sub(r"<(script|style)\b.*?</\1>", "", body.decode("utf-8", "replace"), flags=re.S)
        band_drawn = "drawn" if 'class="pw-hs-pick"' in page else "left out"
        row_drawn = "drawn" if 'class="pw-hs-offer"' in page else "left out"
        numbers = "shown" if re.search(r"products? from £", page) else "left out"
        say(f"  before the facts: {path}: band {band_drawn}, offers row {row_drawn}, numbers {numbers}")

    # Every link inside the site, once; never a shop's button.
    say("\n  -- every link of these pages, followed in this process --")
    seen: dict[str, int] = {}
    out_buttons = outside = 0
    queue: list[str] = []
    for path, body in pages.items():
        for href in links_of(body.decode("utf-8", "replace")):
            if href.startswith("#") or not href:
                continue
            if href.startswith("/out/"):
                out_buttons += 1
                continue
            if not href.startswith("/"):
                outside += 1
                say(f"    LEADS OUT of the site, on {path}: {no_address(href)[:60]}")
                continue
            target = href.split("#", 1)[0]
            if target not in seen and target not in pages:
                seen[target] = -1
                queue.append(target)
    broken = 0
    picks = {pick.query: pick for pick in home.picks}
    picks.update({query: fact.pick for query, fact in kinds.kinds.items() if fact.pick is not None})
    checked = unlike = 0
    for target in queue:
        status, headers, body = ask(target)
        seen[target] = status
        if status == 302:
            where = headers.get("Location", "")
            status2, _h, _b = ask(where) if where.startswith("/") else (0, {}, b"")
            if status2 != 200:
                broken += 1
                say(f"    BROKEN after a redirect ({status2}): {target}")
            continue
        if status != 200:
            broken += 1
            say(f"    BROKEN ({status}): {target}")
            continue
        found = re.fullmatch(r"/search\?q=([^&]+)", target)
        if found:
            query = urllib.request.unquote(found.group(1))
            pick = picks.get(query)
            if pick is not None:
                checked += 1
                cards = cards_of(body.decode("utf-8", "replace"))
                first = cards[0] if cards else {}
                # A page shows a title's runs of spaces as one, and its entities as written.
                same_title = " ".join(html.unescape(pick.title).split()) == " ".join(html.unescape(first.get("title", "")).split())
                if not (first.get("recommended") and same_title and first.get("price") == pick.price):
                    unlike += 1
                    say(f"    a Recommended UNLIKE its search «{query}»: page «{pick.price} {pick.title[:40]}», search «{first.get('price', '')} {first.get('title', '')[:40]}»")
    say(f"  {len(queue)} more addresses followed: {broken} broken; {outside} leading out of the site; "
        f"{out_buttons} shop buttons on the search pages, none pressed")
    say(f"  {checked} Recommended against their own search's first card: {unlike} unlike")

    # The offers.
    say("\n  -- the offers --")
    by_scope: dict[str, int] = {}
    for card in offers:
        by_scope[card.scope or "?"] = by_scope.get(card.scope or "?", 0) + 1
    shops = sorted({card.shop for card in offers})
    say(f"  {len(offers)} offers of {len(shops)} shops cover products shown tonight {by_scope}")
    dead = 0
    kept: dict[str, bytes] = {}
    for card in offers:
        covered = kinds.offer_kinds.get(card.offer_id, ())
        status, headers, body = ask(f"/offers/{card.offer_id}")
        line = f"    {card.shop[:22]:22} [{card.scope:4}] «{card.title[:44]}» covers {card.products:,} products; kinds: {len(covered)}"
        if not covered:
            dead += 1
            say(line + f"  -> {status}, NO KIND TO OFFER (its page has no row)")
            continue
        if status == 200 and "offer_kinds" not in kept:
            kept["offer_kinds"] = body
        first = covered[0]
        status2, _h, body2 = ask(f"/search?q={first.query}&offer={card.offer_id}")
        page = body2.decode("utf-8", "replace")
        cards = cards_of(page)
        counter = re.search(r'class="pw-counter">([^<]*)<', page)
        wrong = [c for c in cards if card.shop.casefold() not in c["shop"].casefold()]
        heading = re.search(r'<h1 class="pw-query-line">(.*?)</h1>', page, re.S)
        marks = []
        if status2 != 200 or not cards:
            marks.append("NO CARDS")
        if wrong:
            marks.append(f"{len(wrong)} cards of ANOTHER SHOP")
        if any(c["recommended"] or c["role"] for c in cards):
            marks.append("a card with a ROLE")
        if not (heading and card.shop in text_of(heading.group(1))):
            marks.append("heading does not name the shop")
        if "offer_products" not in kept and cards and not marks:
            kept["offer_products"] = body2
        say(line + f"  -> {status}; «{first.query}»: {len(cards)} cards, counter «{counter.group(1) if counter else '-'}» "
            f"(counted {first.count}) {' / '.join(marks)}")
    say(f"  offers whose page has no kind to offer: {dead} of {len(offers)}")
    pages.update({f"@{name}": body for name, body in kept.items()})
    return pages


def part_zero() -> None:
    """A search's page as the running site answers it, against what the store's dressing
    needs of it (`store_pages.dress_search_page`): which of its conditions holds."""
    import re
    from picwise_surface import home_store, store_pages

    say("== 0. A search's page as the running site answers it ==")
    say(f"  the switch as this release's file says: {home_store.home_store_on()}")
    header = home_store._header_html(home_store.load_home_lists(), home_store.PARTS_BUILT, nav_row=False)
    say(f"  the store's header holds the box's marker {header.count('name=\"q\" value=\"\"')} time(s)")
    for query in ("blender", "kettle"):
        status, raw = running(f"/search?q={query}")
        page = raw.decode("utf-8", "replace")
        dressed = store_pages.dress_search_page(page, query)
        say(f"  «{query}»: {status}, {len(page):,} characters; the store's frame: {'yes' if 'pw-hs-body' in page else 'no'}; "
            f"this commit dresses it: {'yes' if dressed != page else 'no'}")
        for name, found in (
            ("<header class=\"pw-topbar\">…</header>", len(re.findall(r'<header class="pw-topbar">.*?</header>', page, flags=re.S))),
            ("<section class=\"pw-search-wrap\"…</section>", len(re.findall(r'<section class="pw-search-wrap".*?</section>', page, flags=re.S))),
            ("<footer class=\"pw-footer\">…</footer>", len(re.findall(r'<footer class="pw-footer">.*?</footer>', page, flags=re.S))),
            ("<main class=\"pw-reference-viewport\">", page.count('<main class="pw-reference-viewport">')),
            ("<body>", page.count("<body>")),
            ("<body", page.count("<body")),
            ("<main", page.count("<main")),
        ):
            say(f"    {name}: {found}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-pages", action="store_true", help="print the report only")
    parser.add_argument("--local", action="store_true",
                        help="a dry run off the server: no prepared catalogue, the feed the environment names")
    args = parser.parse_args(argv)
    if not args.local:
        for name, value in SETTINGS.items():
            os.environ[name] = value
    os.environ["PICWISE_CATALOGUE_KEEPER"] = "off"
    os.environ.pop("PICWISE_SEARCH_LOG_DIR", None)
    root = Path(__file__).resolve().parents[2]
    for path in (root / "deployment" / "server", root, root / "src"):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))

    from picwise_providers import state
    from picwise_surface import home_store, home_store_facts
    import wsgi_server  # the server's own entry: its static files, then the site's pages

    ask = asker(wsgi_server.app)
    started = time.monotonic()
    done = "not asked (a dry run)" if args.local else state.refresh_prepared_catalogue()
    now, peak = memory()
    prepared_at = state.loaded_prepared_at()
    if prepared_at is not None:
        say(f"this commit's code on the server's data, read-only; the catalogue {done} in {time.monotonic() - started:.1f} s, "
            f"prepared {prepared_at:%Y-%m-%d %H:%M} UTC; memory {now:,} MB (most {peak:,} MB)")
    elif args.local:
        say("a dry run off the server: no prepared catalogue")
    else:
        say(f"the catalogue could not be read ({done})")
        return 1

    if not args.local:
        part_zero()
    home_store.set_home_store_on_for_tests(False)
    part_one(ask)

    home_store.set_home_store_on_for_tests(True)
    home_store_facts.set_home_facts_for_tests(None)
    home_store_facts.set_kind_facts_for_tests(None)
    before = {path: ask(path)[2] for path in ("/", "/department/kitchen", "/our-shops", "/offers")}
    home, kinds, answers = part_two()
    part_three(kinds, answers)
    pages = part_four(ask, home, kinds, before)
    now, peak = memory()
    say(f"\nthe look's own memory at its end: {now:,} MB (most {peak:,} MB)")

    if not args.no_pages:
        names = {
            "/": "home", "/departments": "departments", "/department/kitchen": "department_kitchen",
            "/department/computers": "department_computers", "/offers": "offers", "@offer_kinds": "offer_kinds",
            "@offer_products": "offer_products", "/how-picwise-works": "how_picwise_works", "/how-we-choose": "how_we_choose",
            "/our-checks": "our_checks", "/our-shops": "our_shops", "/search?q=kettle": "search_kettle",
            "/search?q=laptop": "search_laptop", "/privacy": "privacy", "/about": "about",
        }
        with tarfile.open(fileobj=sys.stdout.buffer, mode="w|gz") as tar:
            for path, name in names.items():
                body = pages.get(path)
                if body is None:
                    continue
                info = tarfile.TarInfo(f"{name}.html")
                info.size = len(body)
                tar.addfile(info, io.BytesIO(body))
        sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
