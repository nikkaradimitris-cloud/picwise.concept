"""The checks' bot: each night, the products asked on their shops' own sites.

    python3 deployment/bot/shop_checks_bot.py [--catalogue PATH] [--checks DIR]
        [--until 03:05] [--workers 48] [--pause 3]

The checks' rules (`docs/PICWISE_CHECKS_RULES.md`; owner, 2026-11-21: «Ποιότητα πάνω από
ποσότητα. Όποιο προϊόν δεν περνά τον έλεγχο κόβεται...» and his six answers). Run by
picwise-checks.service all day (owner, 2026-11-22: «Ναι, όλη μέρα»): from 05:30 UTC until
`--until` (03:05 UTC the next day: before the updates' reboot window of 03:30 and the
preparation of 04:17, which reads what it writes); started between those two it asks
nothing. Each answer is kept as it comes (`tonight-<night>.jsonl`), so that a round stopped
(by a deployment that prepares the catalogue, or a reboot) goes on from where it was when
started again; a night recorded already is not asked again. Code that only fetches
(rules 14): what an answer means is
`picwise_checks.verdicts`; what the night does to each product and shop,
`picwise_checks.ledger`.

How a shop is asked (rules 4): only its own address, read as text from its rows
(`shop_catalogue.own_address`), never an Awin link and never the site's `/out/...`; its
robots.txt first, and only what it allows; one request at a time a shop, 3 seconds apart
(its crawl-delay when longer, up to 60 s), many shops at once, under the bot's own name; a
redirect to another site is not followed; a 429, or a 503 that says when to come back,
ends that shop's night. A Shopify shop is read by its catalogue (`/products.json`, 250
products a request, up to 100 pages), a product missing from it by its own
`/products/<name>.js`, and one with no `.js` of that name at its own page before it is
called gone; any other shop by each product's own page.

The products asked are those the site shows (the prepared catalogue), the cap's
candidates and the products the checks cut that the feed still lists (the preparation's
`candidates.json.gz`), in the rules' order (10). Awin's programmes and feed list are read
from its API, never by a click (5.6.3, 5.6.4).

Written, beside the catalogue on the server (never in the repo or a public place): the
ledger, the decisions the preparation reads, and the night's note. Printed: counts and
shop names only; never an address, an id, a key or a server name.
"""
from __future__ import annotations

import argparse
import gc
import gzip
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping
from urllib.parse import quote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
for _folder in (ROOT, ROOT / "src", Path(__file__).resolve().parent, ROOT / "deployment" / "server"):
    if str(_folder) not in sys.path:
        sys.path.insert(0, str(_folder))

import shop_catalogue_test as look  # noqa: E402

from picwise_checks import ledger as L  # noqa: E402
from picwise_checks.rows import row_from_record, row_of, row_record  # noqa: E402,F401
from picwise_checks.page_reader import NOTHING, Offer, PageRead, read_page, read_shopify_product  # noqa: E402
from picwise_checks.verdicts import (  # noqa: E402
    PageAnswer, Row, ShopNight, address_parts, page_verdict, shop_reads_pages, stock_reading, tie,
)

USER_AGENT = look.USER_AGENT
PREPARED = "/srv/picwise/shared/prepared/catalogue.json.gz"
CHECKS_DIR = "/srv/picwise/shared/checks"
CACHE_DIR = look.CACHE_DIR
PAUSE = look.PAUSE
MAX_CRAWL_DELAY = look.MAX_CRAWL_DELAY
TIMEOUT = 20
PAGE_BYTES = 4 * 1024 * 1024
JSON_BYTES = 20 * 1024 * 1024
ROBOTS_BYTES = look.ROBOTS_BYTES
LISTING_SIZE = 250
LISTING_PAGES = 100
WORKERS = 48
UNTIL = "03:05"
# Between `UNTIL` and this the preparation (04:17) and the photos' check (04:40) run: a
# round started then asks nothing.
QUIET_UNTIL = "05:30"
MAX_HOURS = 22
TONIGHT = "tonight-{night}.jsonl"
NOTE_NAME = "note.json"
OWNER_WORDS = ROOT / "data" / "checks_owner_words.json"
# What only a challenge page writes (a refusal that answers 403, 429 or 503, or a small 200).
# Not a reCAPTCHA box or Cloudflare's script, which shops put on every page: the look of
# 22/11 (run 44971464930) found them on GamingKit's and Webbs Motorcycles' product pages,
# whole and readable, which were read as challenges and so as refusals. A wall that makes a
# browser work or wait before the page (Anubis on Plusshop UK's and Bazta UK's pages; "One
# moment, please..." on Luxe Mattress's and Elixir's: the looks of 22/11, runs 44972305197
# and 44973108097) is a challenge too: never got around (the rules, 4.4).
CHALLENGE_SIGNS = (b"_cf_chl_opt", b"cf-chl-bypass", b"<title>Just a moment", b"Attention Required! | Cloudflare",
                   b"px-captcha", b"Incapsula incident ID", b"_Incapsula_Resource?CWUDNSAI", b"captcha-delivery.com",
                   b"/.well-known/sgcaptcha", b"Sucuri WebSite Firewall",
                   b"anubis_challenge", b"within.website/x/cmd/anubis", b"Making sure you&#39;re not a bot!",
                   b"Making sure you're not a bot!", b"<title>One moment, please...</title>",
                   b"Please wait while your request is being verified")
CHALLENGE_MAX_BYTES = 100_000
SHOPS_LISTED = 60


# ---- asking ----------------------------------------------------------------------


@dataclass
class Answer:
    status: int = 0
    content_type: str = ""
    body: bytes = b""
    error: str = ""
    final_url: str = ""
    elsewhere: bool = False
    retry_after: str = ""


Fetch = Callable[[str, int], Answer]


class _Elsewhere(Exception):
    pass


class _SameSiteRedirects(urllib.request.HTTPRedirectHandler):
    """A redirect is followed only within the same site (with or without "www.")."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        if look._site(urlsplit(newurl).netloc) != look._site(urlsplit(req.full_url).netloc):
            raise _Elsewhere()
        return super().redirect_request(req, fp, code, msg, headers, newurl)


# Never through a proxy: the server asks the shop itself.
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}), _SameSiteRedirects())


def fetch(url: str, limit: int) -> Answer:
    accept = "application/json, */*;q=0.5" if ".json" in url or url.endswith(".js") else \
        "text/html,application/xhtml+xml;q=0.9,*/*;q=0.5"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept,
                                                   "Accept-Language": "en-GB,en;q=0.8"})
    try:
        with _OPENER.open(request, timeout=TIMEOUT) as response:
            return Answer(response.status, response.headers.get("Content-Type", ""), response.read(limit),
                          final_url=response.geturl())
    except _Elsewhere:
        return Answer(error="another site", elsewhere=True)
    except urllib.error.HTTPError as error:
        headers = error.headers or {}
        try:
            body = error.read(64 * 1024)
        except OSError:
            body = b""
        return Answer(error.code, headers.get("Content-Type", ""), body, final_url=url,
                      retry_after=str(headers.get("Retry-After", "") or ""))
    except (urllib.error.URLError, OSError, ValueError) as error:
        reason = getattr(error, "reason", error)
        return Answer(error=reason if isinstance(reason, str) else type(reason).__name__)


def is_challenge(answer: Answer, *, read_found: bool = False) -> bool:
    """A challenge page: a refusal dressed as a page. Never a page a product was read on,
    never a 404; a 200 only when small."""
    if read_found:
        return False
    if answer.status in (403, 429, 503):
        return any(sign in answer.body[:200_000] for sign in CHALLENGE_SIGNS)
    if answer.status == 200 and len(answer.body) < CHALLENGE_MAX_BYTES:
        return any(sign in answer.body for sign in CHALLENGE_SIGNS)
    return False


def _text(answer: Answer) -> str:
    charset = "utf-8"
    for part in answer.content_type.split(";")[1:]:
        name, _, value = part.strip().partition("=")
        if name.lower() == "charset" and value:
            charset = value.strip("\"' ")
    try:
        return answer.body.decode(charset, "replace")
    except LookupError:
        return answer.body.decode("utf-8", "replace")


def _json(answer: Answer) -> Any:
    if answer.status != 200 or answer.body.lstrip()[:1] not in (b"{", b"["):
        return None
    try:
        return json.loads(answer.body.decode("utf-8", "replace"))
    except ValueError:
        return None


def _path(url: str) -> str:
    parts = urlsplit(url)
    return (parts.path or "/") + (f"?{parts.query}" if parts.query else "")


@dataclass
class ShopResult:
    night: ShopNight
    answers: dict[str, PageAnswer] = field(default_factory=dict)
    stopped: str = ""


def _base_of(rows: Iterable[Row]) -> tuple[str, str]:
    """The shop's own site, the one most of its rows' own addresses give: (scheme, host)."""
    hosts = Counter((urlsplit(row.address).scheme.lower() or "https", urlsplit(row.address).netloc.lower())
                    for row in rows if row.address)
    if not hosts:
        return "", ""
    scheme, host = hosts.most_common(1)[0][0]
    return (scheme if scheme in ("http", "https") else "https"), host


def _count(counts: Counter, answer: PageAnswer) -> None:
    """What one product's answer adds to its shop's night (5.6.2)."""
    if answer.in_catalogue:
        return
    counts["requests"] += 1
    counts["answers"] += bool(answer.status)
    if answer.status in (401, 403, 429) or answer.challenge or answer.elsewhere:
        counts["refused"] += 1
    if answer.status == 200 and not answer.challenge:
        counts["pages_200"] += 1
        counts["pages_read"] += answer.read.found


def _counted(answer: PageAnswer) -> Counter:
    counts: Counter = Counter()
    _count(counts, answer)
    return counts


def ask_shop(rows: list[Row], *, fetch: Fetch, sleep: Callable[[float], None], clock: Callable[[], float],
             deadline: float, pause: float = PAUSE, done: Mapping[str, PageAnswer] | None = None,
             keep: Callable[[str, PageAnswer], None] | None = None) -> ShopResult:
    """One shop's night (module docstring): its robots.txt, its catalogue when it is a
    Shopify shop, then its products in the order given, until the deadline. `done`: the
    answers this night kept already (a round started again), not asked again; `keep`: told
    each new answer as it comes."""
    done = dict(done or {})
    scheme, host = _base_of(rows)
    if not host or "awin" in host:
        return ShopResult(ShopNight(own_address=False))
    base = f"{scheme}://{host}"
    counts = Counter()
    for answer in done.values():
        _count(counts, answer)
    state = {"last": None, "stopped": ""}

    def ask(path: str, limit: int, rules: list, wait: float) -> Answer | None:
        """One request, `wait` seconds after the last; None when not asked."""
        if state["stopped"] or clock() >= deadline or not look.robots_allows(rules, path.split("?")[0]):
            return None
        if state["last"] is not None:
            sleep(max(0.0, wait - (clock() - state["last"])))
        answer = fetch(base + path, limit)
        state["last"] = clock()
        if answer.status == 429 or (answer.status == 503 and answer.retry_after):
            state["stopped"] = f"{answer.status}: asked to come back later"
        return answer

    robots = fetch(f"{base}/robots.txt", ROBOTS_BYTES)
    state["last"] = clock()
    counts["requests"] += 1
    counts["answers"] += bool(robots.status)

    def ask_counted(path: str, limit: int, rules: list, wait: float) -> Answer | None:
        """A request that is no product's own (the catalogue's pages), counted here."""
        answer = ask(path, limit, rules, wait)
        if answer is not None:
            counts["requests"] += 1
            counts["answers"] += bool(answer.status)
            if answer.status in (401, 403, 429) or is_challenge(answer) or answer.elsewhere:
                counts["refused"] += 1
        return answer

    if robots.status == 200:
        rules, delay = look.robots_rules(_text(robots))
    elif robots.status in (404, 410):
        rules, delay = [], None
    elif robots.status in (401, 403):
        return ShopResult(ShopNight(robots="refused", requests=1, answers=1, refused=1))
    else:
        return ShopResult(ShopNight(requests=1, answers=int(bool(robots.status))))
    wait = max(pause, delay or 0.0)
    if wait > MAX_CRAWL_DELAY:
        return ShopResult(ShopNight(crawl_delay=delay, requests=1, answers=1))
    allowed = [row for row in rows if row.address and look.robots_allows(rules, urlsplit(row.address).path or "/")]
    if rows and not allowed:
        return ShopResult(ShopNight(robots="disallowed", requests=1, answers=1))

    answers: dict[str, PageAnswer] = {}
    catalogue: dict[str, PageRead] = {}
    whole = False
    listing = ask_counted(f"/products.json?limit={LISTING_SIZE}&page=1", JSON_BYTES, rules, wait)
    data = _json(listing) if listing else None
    shopify = isinstance(data, dict) and isinstance(data.get("products"), list)
    if shopify:
        page = 1
        while True:
            products = data.get("products") if isinstance(data, dict) else None
            if not isinstance(products, list):
                break
            for product in products:
                if isinstance(product, dict) and product.get("handle"):
                    catalogue[str(product["handle"]).lower()] = read_shopify_product(product, pence=False)
            if len(products) < LISTING_SIZE:
                whole = True
                break
            page += 1
            if page > LISTING_PAGES:
                break
            answer = ask_counted(f"/products.json?limit={LISTING_SIZE}&page={page}", JSON_BYTES, rules, wait)
            data = _json(answer) if answer else None

    def page_of(row: Row) -> PageAnswer | None:
        """A product asked at its own address: in a Shopify shop its `.js`, else its page.
        A row whose own address is on another site than its shop's is not asked."""
        if look._site(urlsplit(row.address).netloc) != look._site(host):
            return PageAnswer(elsewhere=True)
        if shopify and row.handle:
            requested = f"/products/{quote(row.handle)}.js"
            answer = ask(requested, JSON_BYTES, rules, wait)
            if answer is None:
                return None
            if answer.status not in (404, 410):
                final = answer.final_url or base + requested
                redirected = address_parts(final) != address_parts(base + requested)
                final = final[:-3] if final.endswith(".js") else final
                data = _json(answer)
                read = read_shopify_product(data, pence=True) if isinstance(data, dict) else NOTHING
                return PageAnswer(status=answer.status, error=answer.error, final_url=final, redirected=redirected,
                                  elsewhere=answer.elsewhere, challenge=is_challenge(answer, read_found=read.found),
                                  read=read)
            # Not in the catalogue and no `.js` of that name: before it is called gone it is
            # asked at its own address, the one a visitor's button opens (rules 5.1). A
            # product the shop renamed answers there with a redirect to its new address,
            # which its `.js` does not follow; one the shop took down answers 404 there too.
            counts["requests"] += 1
            counts["answers"] += 1
        requested = _path(row.address)
        answer = ask(requested, PAGE_BYTES, rules, wait)
        if answer is None:
            return None
        final = answer.final_url or row.address
        redirected = address_parts(final) != address_parts(row.address)
        read = read_page(_text(answer)) if answer.status == 200 else NOTHING
        return PageAnswer(status=answer.status, error=answer.error, final_url=final, redirected=redirected,
                          elsewhere=answer.elsewhere, challenge=is_challenge(answer, read_found=read.found), read=read)

    def take(row: Row, answer: PageAnswer, *, again_of: PageAnswer | None = None) -> None:
        if again_of is not None:
            # The answer asked again replaces the first in the shop's counts too.
            counts.subtract({name: value for name, value in _counted(again_of).items()})
        answers[row.key] = answer
        _count(counts, answer)
        if keep is not None:
            keep(row.key, answer)

    answers.update(done)
    again: list[Row] = []
    for row in rows:
        if row.key in done:
            continue
        if state["stopped"] or clock() >= deadline:
            break
        if shopify and row.handle and row.handle.lower() in catalogue:
            take(row, PageAnswer(status=200, in_catalogue=True, read=catalogue[row.handle.lower()]))
            continue
        if not look.robots_allows(rules, urlsplit(row.address).path or "/"):
            continue
        answer = page_of(row)
        if answer is None:
            continue
        take(row, answer)
        # A challenge page is a refusal, not a page that did not answer.
        if not answer.elsewhere and not answer.challenge and (answer.status == 0 or 500 <= answer.status < 600):
            again.append(row)
    # Nothing, or a 5xx: asked once more at the end of the shop's round (rules 5.1).
    for row in again:
        if state["stopped"] or clock() >= deadline:
            break
        answer = page_of(row)
        if answer is not None:
            take(row, answer, again_of=answers[row.key])
    night = ShopNight(requests=counts["requests"], answers=counts["answers"], refused=counts["refused"],
                      pages_200=counts["pages_200"], pages_read=counts["pages_read"], catalogue_read=shopify,
                      crawl_delay=delay)
    return ShopResult(night, answers, state["stopped"])


def prices_by_page(rows: Iterable[Row]) -> dict[tuple[str, str], set]:
    """The feed's prices for each product page (its rows' addresses, the query left out)."""
    by_page: dict[tuple[str, str], set] = defaultdict(set)
    for row in rows:
        by_page[address_parts(row.address)].add(row.price)
    return by_page


def answer_record(answer: PageAnswer) -> dict[str, Any]:
    """One answer as tonight's file keeps it (on the server, never in a public place)."""
    read = answer.read
    return {
        "s": answer.status, "e": answer.error, "f": answer.final_url, "r": answer.redirected,
        "x": answer.elsewhere, "c": answer.challenge, "k": answer.in_catalogue,
        "p": None if not read.found else [
            read.how, read.name,
            [[o.price, o.currency, o.availability, o.sku, o.gtin, o.mpn, o.variant] for o in read.offers],
            sorted(read.gtins), sorted(read.skus), sorted(read.mpns), read.canonical,
        ],
    }


def answer_from_record(record: Mapping[str, Any]) -> PageAnswer:
    page = record.get("p")
    read = NOTHING
    if page:
        how, name, offers, gtins, skus, mpns, canonical = page
        read = PageRead(how=how, name=name, offers=tuple(Offer(*offer) for offer in offers), gtins=frozenset(gtins),
                        skus=frozenset(skus), mpns=frozenset(mpns), canonical=canonical)
    return PageAnswer(status=record.get("s", 0), error=record.get("e", ""), final_url=record.get("f", ""),
                      redirected=bool(record.get("r")), elsewhere=bool(record.get("x")),
                      challenge=bool(record.get("c")), in_catalogue=bool(record.get("k")), read=read)


class Tonight:
    """The night's answers, one line each as they come, so that a round stopped goes on
    from where it was (module docstring)."""

    def __init__(self, path: Path | None) -> None:
        self.path = path
        self.lock = threading.Lock()

    def load(self) -> dict[str, PageAnswer]:
        found: dict[str, PageAnswer] = {}
        if self.path is None or not self.path.exists():
            return found
        with self.path.open(encoding="utf-8") as handle:
            for line in handle:
                try:
                    record = json.loads(line)
                    found[str(record["key"])] = answer_from_record(record)
                except (ValueError, KeyError, TypeError):
                    continue  # a line cut short by a stop
        return found

    def keep(self, key: str, answer: PageAnswer) -> None:
        if self.path is None:
            return
        line = json.dumps({"key": key, **answer_record(answer)}, separators=(",", ":")) + "\n"
        with self.lock, self.path.open("a", encoding="utf-8") as handle:
            handle.write(line)

    def forget(self) -> None:
        if self.path is None:
            return
        for old in self.path.parent.glob(TONIGHT.format(night="*")):
            old.unlink(missing_ok=True)


def judge(rows: Mapping[str, Row], result: ShopResult, *, shared_ids: Iterable[str] = (),
          by_page: Mapping[tuple[str, str], set] | None = None) -> dict[str, L.Reading]:
    """What each answer of one shop's night means (`picwise_checks.verdicts`).
    `by_page`: the feed's prices of each product page, over all the shop's rows."""
    shared = frozenset(shared_ids)
    reads_pages = shop_reads_pages(result.night.pages_200, result.night.pages_read)
    by_page = by_page if by_page is not None else prices_by_page(rows.values())
    readings: dict[str, L.Reading] = {}
    for key, answer in result.answers.items():
        row = rows[key]
        verdict = page_verdict(row, answer, shop_reads_pages=reads_pages, shared_id=row.product_id in shared)
        site_price, how, stock = None, "", ""
        if verdict.state == "passed" and answer.read.found:
            tied, how = tie(row, answer.read,
                            feed_rows_one_price=len(by_page.get(address_parts(row.address), ())) <= 1)
            site_price = tied.price if tied is not None else None
            stock = stock_reading(row, answer.read, tied)
        readings[key] = L.Reading(page=verdict, site_price=site_price, tie=how, stock=stock)
    return readings


# ---- what is asked -----------------------------------------------------------------


def rows_from_catalogue(path: Path) -> tuple[dict[str, Row], dict[str, str], set[str]]:
    """The products the site shows: their rows, their kinds as the cap reads them, and
    the ids more than one of them carries (the site's button finds a product by its id)."""
    from picwise_providers.catalogue_cap import part_of
    from picwise_providers.prepared_catalogue import read_prepared_catalogue_to_measure

    prepared = read_prepared_catalogue_to_measure(path)
    if prepared is None:
        raise ValueError("the prepared catalogue cannot be read")
    rows: dict[str, Row] = {}
    parts: dict[str, str] = {}
    ids: Counter = Counter()
    for product, kinds in zip(prepared.products, prepared.kinds):
        row = row_of(product)
        rows[row.key] = row
        parts[row.key] = part_of(product, kinds)
        ids[row.product_id] += 1
    del prepared
    gc.collect()
    return rows, parts, {ident for ident, count in ids.items() if count > 1}


def rows_from_candidates(path: Path) -> tuple[dict[str, Row], list[str]]:
    """The rows the preparation names for the bot: the cap's candidates and the cut
    products the feed still lists; and which of them are candidates."""
    if not path.exists():
        return {}, []
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    rows = {}
    for values in payload.get("rows", []):
        row = row_from_record(values)
        rows[row.key] = row
    return rows, [key for key in payload.get("candidates", []) if key in rows]


def owner_words(path: Path = OWNER_WORDS) -> tuple[list[str], bool]:
    """The owner's words the brakes wait for (rules 7.2, 5.6.3), kept in the repo with
    their dates: the shops whose held products he said to cut, and his word on a reading
    of Awin that waits."""
    try:
        words = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return [], False
    return [str(name) for name in words.get("cut_held_shops", [])], bool(words.get("awin_reading_let_through"))


def owner_yes(path: Path = OWNER_WORDS) -> dict[str, bool]:
    """The owner's yes to the two Proposed rules that wait for it (rules 13.2; asked 21/11
    to be reminded of them): `old_feed_rule`, a product of a feed over 7 days old shown
    only with a reading of its shop's site of the last 3 nights (5.6.4); `awin_closed_out`,
    a shop suspended, in no list or offline at Awin out (5.6.3). Each is off, and changes
    nothing on the site, until the file says true on his word."""
    try:
        words = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        words = {}
    return {name: words.get(name) is True for name in ("old_feed_rule", "awin_closed_out")}


# ---- Awin --------------------------------------------------------------------------


def read_awin(environ: Mapping[str, str], *, cache_dir: str, say: Callable[[str], None],
              get: Callable | None = None, sleep: Callable[[float], None] = time.sleep,
              ) -> tuple[dict[str, tuple[str | None, str]] | None, dict[str, date | None]]:
    """Awin's word on each shop of the feed (5.6.3) and each feed's last import (5.6.4),
    from its API (`print_programmes`); (None, {}) when it does not answer: the last
    reading stands."""
    import print_programmes as awin

    get = get or awin._get
    token = str(environ.get("AWIN_API_TOKEN") or "").strip()
    links = [str(environ.get(name) or "").strip() for name in ("AWIN_FEED_URL", "AWIN_FEED_URL_AWIN")]
    key = awin.feed_key(*links)
    publisher = str(environ.get("AWIN_PUBLISHER_ID") or "").strip()
    shops: dict[str, str] = {}
    for copy in awin.feed_copies(cache_dir):
        for ident, name in awin.feed_shops(copy).items():
            shops.setdefault(ident, name)
    if not token or not shops:
        say("Awin: not read (no token, or no copy of the feed)")
        return None, {}
    failures: list[str] = []
    try:
        publisher = publisher or awin.find_publisher(token, get)
        listed = awin.programmes(publisher, token, get, sleep,
                                 lambda line: failures.append(line) if "Awin answered" in line else None)
    except ValueError:
        say("Awin: its programmes did not answer; the last reading stands")
        return None, {}
    # One list of the five not read would put its shops "in no list": the reading is whole or none.
    if failures or not listed:
        say(f"Awin: {len(failures)} of its lists did not answer; the last reading stands")
        return None, {}
    imports: dict[str, date | None] = {}
    if key:
        try:
            for row in awin.feed_list(key, get):
                ident = awin._column(row, "Advertiser ID", "advertiser_id")
                stamp = awin._column(row, "Last Imported", "last_imported")[:10]
                try:
                    day = date.fromisoformat(stamp)
                except ValueError:
                    continue
                if ident in shops and (imports.get(shops[ident]) is None or day > imports[shops[ident]]):
                    imports[shops[ident]] = day
        except ValueError:
            say("Awin: the feed list did not answer")
    reading = {}
    for ident, name in shops.items():
        programme = listed.get(ident)
        reading[name] = (str(programme.get("relationship")) if programme else None,
                         str((programme or {}).get("linkStatus") or ""))
    say(f"Awin: {len(listed):,} programmes read; the feed's {len(shops)} shops: "
        + ", ".join(f"{word} {count}" for word, count in Counter(r or "in no list" for r, _l in reading.values()).most_common()))
    return reading, imports


# ---- the night ---------------------------------------------------------------------


def quiet(moment: datetime, until: str, quiet_until: str) -> bool:
    """Whether `moment` falls in the hours kept for the preparation and the photos."""
    def minutes(text: str) -> int:
        hours, mins = (int(part) for part in text.split(":"))
        return hours * 60 + mins

    now = moment.hour * 60 + moment.minute
    return minutes(until) <= now < minutes(quiet_until)


def _deadline(start: datetime, until: str) -> datetime:
    hours, minutes = (int(part) for part in until.split(":"))
    end = start.replace(hour=hours, minute=minutes, second=0, microsecond=0)
    return end if end > start else end + timedelta(days=1)


def run(rows: dict[str, Row], *, shown: set[str], parts: Mapping[str, str], shared_ids: set[str],
        candidates: list[str], ledger: L.Ledger, night: date, fetch: Fetch, sleep: Callable[[float], None],
        clock: Callable[[], float], deadline: float, workers: int, pause: float,
        awin: Mapping[str, tuple[str | None, str]] | None, feeds: Mapping[str, date | None],
        owner_cut_shops: list[str], owner_awin_word: bool, say: Callable[[str], None],
        sample: int = 0, tonight: Tonight | None = None, shops: frozenset[str] = frozenset(),
        old_feed_rule: bool = False, awin_closed_out: bool = False) -> tuple[L.Night, dict]:
    """Ask every shop its products in the rules' order; record the night; the decisions.
    `sample`: a look, at most this many products a shop; `tonight`: the night's answers
    kept as they come, those kept already not asked again."""
    tonight = tonight or Tonight(None)
    order = L.asking_order(ledger, night, rows, shown=shown, candidates=candidates, parts=parts)
    if shops:
        order = {shop: keys for shop, keys in order.items() if shop in shops}
    if sample > 0:
        order = {shop: keys[:sample] for shop, keys in order.items()}
    kept = tonight.load()
    say(f"to ask: {sum(len(keys) for keys in order.values()):,} products of {len(order)} shops"
        + (f"; {len(kept):,} answered already tonight (the round goes on)" if kept else ""))
    results: dict[str, ShopResult] = {}
    seconds: dict[str, float] = {}
    lock = threading.Lock()

    def one(shop: str) -> None:
        done = {key: kept[key] for key in order[shop] if key in kept}
        started = clock()
        result = ask_shop([rows[key] for key in order[shop]], fetch=fetch, sleep=sleep, clock=clock,
                          deadline=deadline, pause=pause, done=done, keep=tonight.keep)
        with lock:
            results[shop] = result
            seconds[shop] = clock() - started

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        list(pool.map(one, sorted(order, key=lambda shop: (-len(order[shop]), shop))))
    readings: dict[str, L.Reading] = {}
    shop_nights: dict[str, ShopNight] = {}
    by_page = prices_by_page(rows.values())
    for shop, result in results.items():
        shop_nights[shop] = result.night
        readings.update(judge({key: rows[key] for key in result.answers}, result, shared_ids=shared_ids,
                              by_page=by_page))
    night_result = L.record_night(ledger, night, rows, readings, shop_nights, shown=shown, parts=parts, awin=awin,
                                  feeds=feeds, owner_cut_shops=owner_cut_shops, owner_awin_word=owner_awin_word,
                                  awin_closed_out=awin_closed_out)
    made = L.decisions(ledger, night, rows, shown=shown, candidates=candidates, came_back=night_result.came_back,
                       old_feed_rule=old_feed_rule)
    night_result.note["asked_by_shop"] = {shop: [result.night.requests, len(result.answers), result.stopped]
                                          for shop, result in sorted(results.items())}
    # How long each shop's asking took, and the crawl-delay it asks for: the bot's pace (rules 4.7).
    night_result.note["seconds_by_shop"] = {shop: [round(seconds.get(shop, 0.0), 1), result.night.crawl_delay]
                                            for shop, result in sorted(results.items())}
    return night_result, made


def print_night(note: Mapping[str, Any], made: Mapping[str, Any], ledger: L.Ledger, say: Callable[[str], None]) -> None:
    """Counts and shop names only (rules 11)."""
    if note.get("ours"):
        say("the round is ours: fewer than half of the shops answered at all; nothing recorded (rules 7.1)")
        return
    failed = note.get("failed") or {}
    say(f"decided {note.get('decided', 0):,}: passed {note.get('passed', 0):,}, failed {sum(failed.values()):,}"
        + (" (" + ", ".join(f"{reason} {count:,}" for reason, count in sorted(failed.items())) + ")" if failed else ""))
    say(f"cut tonight {note.get('cut_tonight', 0):,}; back {note.get('back_tonight', 0):,}; held "
        + (", ".join(f"by {brake} {count:,}" for brake, count in (note.get("held") or {}).items()) or "none")
        + ("; THE NIGHT'S BRAKE: nothing new cut" if note.get("night_brake") else "")
        + ("; CUTTING STOPPED until the owner's word" if note.get("stopped") else ""))
    if note.get("braked_shops"):
        say("shops braked: " + ", ".join(note["braked_shops"]))
    for name, (why, days) in (note.get("cannot_be_checked") or {}).items():
        say(f"cannot be checked: {name}: {why} (day {days})")
    if note.get("awin"):
        awin = note["awin"]
        if awin.get("names_not_matched"):
            say("Awin: shops whose name its reading does not hold (not judged by it): "
                + ", ".join(awin["names_not_matched"]))
        say("Awin: newly out " + (", ".join(f"{name} ({reason})" for name, reason in awin["newly_out"]) or "none")
            + (f"; WAITS for the owner's word ({awin['products']:,} products)" if awin.get("waits") else ""))
        if awin.get("would_be_out_if_proposed"):
            say("Awin: not out, the Proposed rule waits for the owner's yes: "
                + ", ".join(f"{name} ({reason[6:]}, {count:,} products)" for name, reason, count in awin["would_be_out_if_proposed"]))
    waits = Counter((made.get("wait") or {}).values())
    say(f"the decisions: shops out {len(made['shops_out'])}, products cut {len(made['cut']):,}, not shown until "
        f"checked {sum(waits.values()):,}"
        + (" (" + ", ".join(f"{reason} {count:,}" for reason, count in sorted(waits.items())) + ")" if waits else "")
        + ", may enter "
        f"{len(made['enter']):,}, the page's price {len(made['prices']):,}, the page's stock {len(made['stock']):,}, "
        f"keeping their place {len(made['returning']):,}")
    for name, reason in made["shops_out"].items():
        say(f"out: {name}: {reason}")
    say(f"{'asked':>7} {'answered':>8}  {'reader':<8} {'proof':<9} shop")
    for name, (asked, answered, stopped) in sorted((note.get("asked_by_shop") or {}).items(),
                                                   key=lambda item: -item[1][0])[:SHOPS_LISTED]:
        shop = ledger.shops.get(name) or L.Shop()
        proof = L.brakes.reader_proof((tied, same) for _n, tied, same in shop.proof)
        ratio = L.brakes.commonest_ratio(shop.ratios)
        say(f"{asked:>7,} {answered:>8,}  {shop.reader or '-':<8} {f'{proof.same}/{proof.tied}':<9} {name}"
            + (f" (the commonest ratio {ratio:g})" if proof.tied and not L.proven(shop) and ratio else "")
            + (f"; {stopped}" if stopped else ""))


def main(argv: list[str] | None = None, *, fetch: Fetch = fetch, sleep: Callable[[float], None] = time.sleep,
         clock: Callable[[], float] = time.time, now: datetime | None = None,
         environ: Mapping[str, str] = os.environ) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--catalogue", type=Path, default=Path(PREPARED))
    parser.add_argument("--checks", type=Path, default=Path(CHECKS_DIR))
    parser.add_argument("--cache", default=CACHE_DIR)
    parser.add_argument("--until", default=UNTIL, help="UTC time the asking stops, HH:MM")
    parser.add_argument("--workers", type=int, default=WORKERS)
    parser.add_argument("--pause", type=float, default=PAUSE)
    parser.add_argument("--dry", action="store_true",
                        help="a look: write nothing (no ledger, no decisions, no note); print what the night decided")
    parser.add_argument("--sample", type=int, default=0, help="a look: at most this many products a shop")
    parser.add_argument("--minutes", type=float, default=0.0, help="a look: ask for this many minutes only")
    parser.add_argument("--shop", action="append", default=[], help="a look: these shops only")
    args = parser.parse_args(argv)
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass
    say = print
    start = now or datetime.now(timezone.utc)
    if quiet(start, args.until, QUIET_UNTIL):
        say(f"the checks: between {args.until} and {QUIET_UNTIL} UTC the preparation and the photos run; nothing asked")
        return 0
    # Never past `--until`, never over 22 hours; the night is the morning the preparation
    # reads it.
    ends = min(_deadline(start, args.until), start + timedelta(hours=MAX_HOURS))
    if args.minutes > 0:
        ends = min(ends, start + timedelta(minutes=args.minutes))
    night = _deadline(start, args.until).date()
    deadline = clock() + (ends - start).total_seconds()
    try:
        rows, parts, shared_ids = rows_from_catalogue(args.catalogue)
    except ValueError as error:
        say(f"the checks: {error}; nothing asked")
        return 1
    shown = set(rows)
    extra, candidates = rows_from_candidates(args.checks / L.CANDIDATES_NAME)
    for key, row in extra.items():
        rows.setdefault(key, row)
    ledger = L.load(args.checks / L.LEDGER_NAME)
    if not args.dry and any(entry.get("night") == night.isoformat() for entry in ledger.nights):
        say(f"the night of {night} is recorded already: nothing asked")
        return 0
    tonight = Tonight(None if args.dry else args.checks / TONIGHT.format(night=night))
    say(f"the night of {night}: {len(shown):,} products shown, {len(candidates):,} candidates, "
        f"{len(extra) - len(candidates):,} cut ones the feed still lists; ids shared {len(shared_ids)}")
    awin, feeds = read_awin(environ, cache_dir=args.cache, say=say)
    cut_shops, awin_word = owner_words()
    yes = owner_yes()
    result, made = run(rows, shown=shown, parts=parts, shared_ids=shared_ids, candidates=candidates, ledger=ledger,
                       night=night, fetch=fetch, sleep=sleep, clock=clock, deadline=deadline, workers=args.workers,
                       pause=args.pause, awin=awin, feeds=feeds, owner_cut_shops=cut_shops,
                       owner_awin_word=awin_word, say=say, sample=args.sample, tonight=tonight,
                       shops=frozenset(args.shop) if args.dry else frozenset(),
                       old_feed_rule=yes["old_feed_rule"], awin_closed_out=yes["awin_closed_out"])
    if args.dry:
        say("a look (--dry): nothing written")
    else:
        L.save(ledger, args.checks / L.LEDGER_NAME)
        L.write_decisions(made, args.checks / L.DECISIONS_NAME)
        (args.checks / NOTE_NAME).write_text(json.dumps(result.note, indent=1, sort_keys=True), encoding="utf-8")
        tonight.forget()
    print_night(result.note, made, ledger, say)
    if args.dry:
        print_look(result.note, ledger, say)
    return 0


def print_look(note: Mapping[str, Any], ledger: L.Ledger, say: Callable[[str], None]) -> None:
    """For a look before the «ανέβασε» (task 7): per shop asked, its verdicts by reason,
    its prices tied and the same, its stock read. Counts and shop names only."""
    per_shop: dict[str, Counter] = defaultdict(Counter)
    tonight = str(note.get("night") or "")
    for product in ledger.products.values():
        if product.asked != tonight:
            continue
        counts = per_shop[product.shop]
        counts[product.state or "not checked"] += 1
        if product.state in ("failed", "held"):
            counts[f"  {product.reason}"] += 1
        if product.price_on == tonight:
            counts["price tied"] += 1
            counts["price the same"] += product.site_price == product.feed_price
        if product.stock_on == tonight:
            counts[f"stock {product.stock}"] += 1
    say("== the look, per shop: verdicts, prices tied and the same, stock read")
    for name in sorted(per_shop, key=lambda shop: -sum(per_shop[shop][key] for key in ("passed", "failed", "held"))):
        counts = per_shop[name]
        say(f"{name}: " + ", ".join(f"{key.strip()} {value}" for key, value in sorted(counts.items())))
    asked = note.get("asked_by_shop") or {}
    pace = note.get("seconds_by_shop") or {}
    say("== the pace, per shop: its requests, the seconds they took, seconds a request, the crawl-delay it asks for")
    for name in sorted(pace, key=lambda shop: -(asked.get(shop) or [0])[0])[:SHOPS_LISTED]:
        requests, (spent, delay) = (asked.get(name) or [0])[0], pace[name]
        if requests:
            say(f"{name}: {requests:,} requests in {spent:,.0f} s, {spent / requests:.1f} s a request"
                + (f"; crawl-delay {delay:g} s" if delay else ""))


if __name__ == "__main__":
    raise SystemExit(main())
