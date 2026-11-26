"""The checks' bot: each night, the products asked on their shops' own sites.

    python3 deployment/bot/shop_checks_bot.py [--catalogue PATH] [--checks DIR]
        [--until 03:05] [--workers 0] [--processes 4] [--pause 3] [--shop-rule file|on|off]

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

How many of a shop's products pass (the rules' section 19, behind its switch,
`data/shop_cap_switch.json`; owner, 2026-11-22: «μόνο όσα έχουν σκανναριστεί περνάνε», 20,000
the most): a pass counts for the day it was made, three nights while a shop's asking is not
whole (21, owner, 25/11: «24 ώρες είναι το σκανάρισμα και ότι προλάβει να σκανάρει»; until
then three nights always, 19.3.1): a shop is asked whole when nothing stopped it and the bot
asked it all it had, or all day in a round that asked all day (`RoundTime`, kept across a
round started again); each day a shop's shown products are asked again first, in the order
of 19.4 (`picwise_providers.shop_cap.shop_order`, worked out from the prepared catalogue),
and new ones only in the time left (19.3.2); of a shop, at most its first 20,000 (19.3.3). Every shop is asked at once, one thread each, and the pages are
read on processes of their own (`--processes`; 19.5, owner: «Ναι, μαζί»): with every shop
asked on one process a request took twice as long (the look of 22/11). When the processes
cannot be started, the pages are read on the bot's own, as before, and it says so.

In clones (22, owner, 25/11: «μην αγνοείς τους 4 κλώνους»; behind `data/checks_clones.json`):
`--clone K/4` asks only the shops a code of their name gives clone K (`clone_of`) and keeps its
day; `--record 4`, after the round, records the night once from the four days (`record_round`).

Written, beside the catalogue on the server (never in the repo or a public place): the
ledger, the decisions the preparation reads, and the night's note. Printed: counts and
shop names only; never an address, an id, a key or a server name.
"""
from __future__ import annotations

import argparse
import dataclasses
import gc
import gzip
import http.client
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
import zlib
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Collection, Iterable, Mapping
from urllib.parse import quote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
for _folder in (ROOT, ROOT / "src", Path(__file__).resolve().parent, ROOT / "deployment" / "server"):
    if str(_folder) not in sys.path:
        sys.path.insert(0, str(_folder))

import shop_catalogue_test as look  # noqa: E402

from picwise_checks import ledger as L  # noqa: E402
from picwise_checks.rows import row_from_record, row_of, row_record  # noqa: E402,F401
from picwise_checks.page_reader import NOTHING, Offer, PageRead, options_in_stock  # noqa: E402
from picwise_checks.page_reader import read_catalogue_page, read_page_bytes, read_product_json  # noqa: E402
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
# Shops asked at once: 0 is every shop at once, one thread each, up to `SHOPS_AT_ONCE`
# (the rules 4.3, "many shops at once"; until 22/11, 48).
WORKERS = 0
SHOPS_AT_ONCE = 200
# The processes the pages are read on (the rules 19.5); 0 reads them on the bot's own.
PROCESSES = 4
UNTIL = "03:05"
# Between `UNTIL` and this the preparation (04:17) and the photos' check (04:40) run: a
# round started then asks nothing.
QUIET_UNTIL = "05:30"
MAX_HOURS = 22
TONIGHT = "tonight-{night}.jsonl"
# 21 (owner, 2026-11-25: «24 ώρες είναι το σκανάρισμα και ότι προλάβει να σκανάρει»): the time
# the night's round has asked, kept across a round started again, so that a round stuck for
# hours (the server or the bot down) is told from a whole day. A round that asked at least
# `WHOLE_ROUND_HOURS` is whole (from 05:30 to 03:05 a round asks about 21.5 hours; a deployment
# that starts it again costs minutes). A shop whose asking began over `LATE_HOURS` after the
# round's (waiting for a thread) was not asked all day.
TONIGHT_TIME = "tonight-{night}.time.json"
# 22 (owner, 2026-11-25: «μην αγνοείς τους 4 κλώνους»): a clone's day, kept at its end for the
# night's recording, and how long the recording waits for a clone still finishing its day.
CLONE_DAY = "clone-{name}.json"
RECORD_WAIT_MINUTES = 20.0
WHOLE_ROUND_HOURS = 20.0
LATE_HOURS = 1.0
TIME_KEPT_EVERY = 300.0
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
        except (OSError, http.client.HTTPException):
            body = b""
        return Answer(error.code, headers.get("Content-Type", ""), body, final_url=url,
                      retry_after=str(headers.get("Retry-After", "") or ""))
    except (urllib.error.URLError, OSError, ValueError, http.client.HTTPException) as error:
        # http.client.HTTPException: a body cut short (IncompleteRead), a status line or a
        # header the shop's server garbled; no answer, asked again at the end of the shop's
        # round like a timeout. Before 24/11 it went up through the round and ended it: the
        # night of 24/11 was not recorded (an IncompleteRead at 03:05 UTC).
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


def _path(url: str) -> str:
    parts = urlsplit(url)
    return (parts.path or "/") + (f"?{parts.query}" if parts.query else "")


class Readers:
    """What reads an answer's bytes (the rules 19.5): processes of their own when started
    (`start`), else the bot's own process, as before. A pool that breaks (a process killed)
    is let go and the rest is read on the bot's own process."""

    def __init__(self, pool: ProcessPoolExecutor | None = None) -> None:
        self.pool = pool

    @classmethod
    def start(cls, processes: int, say: Callable[[str], None]) -> "Readers":
        if processes <= 0:
            return cls()
        import multiprocessing

        pool = None
        try:
            # Started fresh, not copied from the bot: a process reads pages and holds no catalogue.
            pool = ProcessPoolExecutor(max_workers=processes, mp_context=multiprocessing.get_context("spawn"))
            pool.submit(read_page_bytes, b"", "").result(timeout=120)
        except Exception as error:  # the sandbox may refuse it: read on the bot's own process
            if pool is not None:
                pool.shutdown(wait=False, cancel_futures=True)
            say(f"the pages are read on the bot's own process: the processes did not start ({type(error).__name__})")
            return cls()
        say(f"the pages are read on {processes} processes of their own")
        return cls(pool)

    @property
    def processes(self) -> int:
        return getattr(self.pool, "_max_workers", 0) if self.pool is not None else 0

    def _read(self, job: Callable[..., Any], *args: Any) -> Any:
        pool = self.pool
        if pool is not None:
            try:
                return pool.submit(job, *args).result()
            except (BrokenProcessPool, RuntimeError, OSError):
                self.pool = None
        return job(*args)

    def page(self, answer: "Answer") -> PageRead:
        return self._read(read_page_bytes, answer.body, answer.content_type) if answer.status == 200 else NOTHING

    def product(self, answer: "Answer") -> PageRead:
        return self._read(read_product_json, answer.body) if answer.status == 200 else NOTHING

    def catalogue_page(self, answer: "Answer | None") -> tuple[int, list[tuple[str, PageRead]]] | None:
        if answer is None or answer.status != 200:
            return None
        return self._read(read_catalogue_page, answer.body)

    def close(self) -> None:
        if self.pool is not None:
            self.pool.shutdown(wait=True, cancel_futures=True)
            self.pool = None


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
             keep: Callable[[str, PageAnswer], None] | None = None, readers: Readers | None = None) -> ShopResult:
    """One shop's night (module docstring): its robots.txt, its catalogue when it is a
    Shopify shop, then its products in the order given, until the deadline. `done`: the
    answers this night kept already (a round started again), not asked again; `keep`: told
    each new answer as it comes; `readers`: what reads the answers (the bot's own process
    when None)."""
    readers = readers or Readers()
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
    read_listing = readers.catalogue_page(listing)
    shopify = read_listing is not None
    if shopify:
        page = 1
        while read_listing is not None:
            size, found = read_listing
            catalogue.update(found)
            if size < LISTING_SIZE:
                whole = True
                break
            page += 1
            if page > LISTING_PAGES:
                break
            answer = ask_counted(f"/products.json?limit={LISTING_SIZE}&page={page}", JSON_BYTES, rules, wait)
            read_listing = readers.catalogue_page(answer)

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
                read = readers.product(answer)
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
        read = readers.page(answer)
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


def _ended(answers: Mapping[str, PageAnswer], why: str) -> ShopResult:
    """A shop's night ended by an error: its answers so far, counted as `ask_shop` counts
    them (its robots.txt among the requests, since it was asked first)."""
    counts: Counter = Counter({"requests": 1, "answers": 1})
    for answer in answers.values():
        _count(counts, answer)
    night = ShopNight(requests=counts["requests"], answers=counts["answers"], refused=counts["refused"],
                      pages_200=counts["pages_200"], pages_read=counts["pages_read"],
                      catalogue_read=any(answer.in_catalogue for answer in answers.values()))
    return ShopResult(night, dict(answers), f"error: {why}")


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
        for pattern in (TONIGHT, TONIGHT_TIME):
            for old in self.path.parent.glob(pattern.format(night="*")):
                old.unlink(missing_ok=True)


class RoundTime:
    """21: how long the night's round has asked, the seconds of a round stopped and started
    again added up (kept every few minutes beside the night's answers), never the hours it
    was down. `path` None: kept in memory only (a look)."""

    def __init__(self, path: Path | None, clock: Callable[[], float]) -> None:
        self.path = path
        self.clock = clock
        self.lock = threading.Lock()
        self.before = 0.0
        if path is not None and path.exists():
            try:
                self.before = max(0.0, float(json.loads(path.read_text(encoding="utf-8")).get("seconds") or 0.0))
            except (OSError, ValueError, TypeError, AttributeError):
                self.before = 0.0
        self.since = clock()
        self.kept = self.since

    def seconds(self) -> float:
        return self.before + max(0.0, self.clock() - self.since)

    def keep(self, *, now: bool = False) -> None:
        """Written when `TIME_KEPT_EVERY` seconds have gone since it last was, or `now`."""
        if self.path is None:
            return
        with self.lock:
            moment = self.clock()
            if not now and moment - self.kept < TIME_KEPT_EVERY:
                return
            self.kept = moment
            temporary = self.path.with_name(self.path.name + ".part")
            temporary.write_text(json.dumps({"seconds": round(self.seconds(), 1)}), encoding="utf-8")
            os.replace(temporary, self.path)


def asked_whole(result: "ShopResult", asked_of_it: int, *, whole_round: bool, late: float) -> bool:
    """21: a shop's asking was whole tonight: nothing stopped it (no 429 or 503 that said to
    come back, no error, no robots.txt that did not answer: a shop asked nothing was not
    asked), and the bot asked it every product of its order, or asked it all the round long
    in a round that asked all day."""
    if result.stopped or not result.answers:
        return False
    if asked_of_it and len(result.answers) >= asked_of_it:
        return True
    return whole_round and late <= LATE_HOURS * 3600.0


def judge(rows: Mapping[str, Row], result: ShopResult, *, shared_ids: Iterable[str] = (),
          by_page: Mapping[tuple[str, str], set] | None = None,
          stock_words: Counter | None = None) -> dict[str, L.Reading]:
    """What each answer of one shop's night means (`picwise_checks.verdicts`).
    `by_page`: the feed's prices of each product page, over all the shop's rows;
    `stock_words`: when given, counts the shop's own availability words behind each stock
    reading ("outofstock", "backorder", "preorder"...), for a look."""
    shared = frozenset(shared_ids)
    reads_pages = shop_reads_pages(result.night.pages_200, result.night.pages_read)
    by_page = by_page if by_page is not None else prices_by_page(rows.values())
    readings: dict[str, L.Reading] = {}
    for key, answer in result.answers.items():
        row = rows[key]
        verdict = page_verdict(row, answer, shop_reads_pages=reads_pages, shared_id=row.product_id in shared)
        site_price, how, stock, options = None, "", "", ""
        if verdict.state == "passed" and answer.read.found:
            options = options_in_stock(answer.read)
            tied, how = tie(row, answer.read,
                            feed_rows_one_price=len(by_page.get(address_parts(row.address), ())) <= 1)
            site_price = tied.price if tied is not None else None
            stock = stock_reading(row, answer.read, tied)
            if stock_words is not None and stock:
                said = {tied.availability} if tied is not None and tied.availability else \
                    {offer.availability for offer in answer.read.offers if offer.availability}
                for word in said:
                    stock_words[f"{stock}: {word}"] += 1
        readings[key] = L.Reading(page=verdict, site_price=site_price, tie=how, stock=stock, options=options)
    return readings


# ---- what is asked -----------------------------------------------------------------


def rows_from_catalogue(path: Path, *, order: bool = False,
                        ) -> tuple[dict[str, Row], dict[str, str], set[str], dict[str, list[str]], set[str]]:
    """The products the site shows: their rows, their kinds as the cap reads them, the ids
    more than one of them carries (the site's button finds a product by its id), and, with
    `order`, per shop its products' keys in the order of 19.4 (`shop_cap.shop_order`), the
    order its shown products are asked again in (19.3.2), and of them the keys a cheaper shop
    shows, asked after the cap's candidates (20.7.4)."""
    from picwise_providers.catalogue_cap import part_of
    from picwise_providers.prepared_catalogue import read_prepared_catalogue_to_measure

    prepared = read_prepared_catalogue_to_measure(path)
    if prepared is None:
        raise ValueError("the prepared catalogue cannot be read")
    rows: dict[str, Row] = {}
    parts: dict[str, str] = {}
    ids: Counter = Counter()
    keys: list[str] = []
    for product, kinds in zip(prepared.products, prepared.kinds):
        row = row_of(product)
        rows[row.key] = row
        parts[row.key] = part_of(product, kinds)
        ids[row.product_id] += 1
        keys.append(row.key)
    orders: dict[str, list[str]] = {}
    dearer: set[str] = set()
    if order:
        from picwise_providers.shop_cap import shop_order

        copies: set[int] = set()
        orders = {shop: [keys[place] for place in places]
                  for shop, places in shop_order(prepared.products, prepared.kinds,
                                                 feed_ctx=prepared.availability_context,
                                                 copies=copies).items()}
        dearer = {keys[place] for place in copies}
    del prepared, keys
    gc.collect()
    return rows, parts, {ident for ident, count in ids.items() if count > 1}, orders, dearer


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


def clone_of(shop: str, clones: int) -> int:
    """22 (owner, 2026-11-25: «μην αγνοείς τους 4 κλώνους»): the clone, 1 to `clones`, that asks
    a shop, by a code of its name: always the same clone, and a shop asked by one clone only, so
    that no shop is asked faster than it allows."""
    return zlib.crc32(" ".join(str(shop or "").split()).casefold().encode("utf-8", "surrogatepass")) % clones + 1


@dataclass
class Round:
    """One asker's day (the bot's, or a clone's): what each of its shops gave, how many of
    its products each one's order held, how long each one's asking took and how late it
    began, the threads and processes it asked on, and the hours it asked (`RoundTime`)."""

    results: dict[str, ShopResult]
    ordered: dict[str, int]
    seconds: dict[str, float]
    late: dict[str, float]
    threads: int
    processes: int
    hours: float

    @property
    def whole(self) -> bool:
        return self.hours >= WHOLE_ROUND_HOURS

    def complete(self) -> set[str]:
        """21: its shops asked whole."""
        return {shop for shop, result in self.results.items()
                if asked_whole(result, self.ordered.get(shop, 0), whole_round=self.whole, late=self.late.get(shop, 0.0))}

    def to_record(self) -> dict[str, Any]:
        """What a clone keeps of its day for the night's recording (22); its answers are kept in
        its own night's file as they come."""
        return {"hours": round(self.hours, 3), "threads": self.threads, "processes": self.processes,
                "shops": {shop: {"night": dataclasses.asdict(result.night), "stopped": result.stopped,
                                 "ordered": self.ordered.get(shop, 0), "seconds": round(self.seconds.get(shop, 0.0), 1),
                                 "late": round(self.late.get(shop, 0.0), 1)}
                          for shop, result in self.results.items()}}

    @classmethod
    def from_record(cls, record: Mapping[str, Any], answers: Mapping[str, PageAnswer],
                    rows: Mapping[str, Row]) -> "Round":
        """A clone's day as it kept it, its shops' answers from its night's file."""
        of_shop: dict[str, dict[str, PageAnswer]] = defaultdict(dict)
        for key, answer in answers.items():
            if key in rows:
                of_shop[rows[key].shop][key] = answer
        shops = record.get("shops") or {}
        return cls(
            results={shop: ShopResult(ShopNight(**entry["night"]), dict(of_shop.get(shop) or {}), str(entry.get("stopped") or ""))
                     for shop, entry in shops.items()},
            ordered={shop: int(entry.get("ordered") or 0) for shop, entry in shops.items()},
            seconds={shop: float(entry.get("seconds") or 0.0) for shop, entry in shops.items()},
            late={shop: float(entry.get("late") or 0.0) for shop, entry in shops.items()},
            threads=int(record.get("threads") or 0), processes=int(record.get("processes") or 0),
            hours=float(record.get("hours") or 0.0))

    @classmethod
    def unfinished(cls, answers: Mapping[str, PageAnswer], rows: Mapping[str, Row]) -> "Round":
        """A clone that kept no day (it stopped, or was stopped): its shops' answers so far count,
        as a shop's asking ended by an error does (`_ended`), and none of its shops was asked
        whole (21: their products stay as they were)."""
        of_shop: dict[str, dict[str, PageAnswer]] = defaultdict(dict)
        for key, answer in answers.items():
            if key in rows:
                of_shop[rows[key].shop][key] = answer
        return cls(results={shop: _ended(got, "the clone did not finish") for shop, got in of_shop.items()},
                   ordered={}, seconds={}, late={}, threads=0, processes=0, hours=0.0)


def ask_round(rows: dict[str, Row], *, shown: set[str], parts: Mapping[str, str], candidates: list[str],
              ledger: L.Ledger, night: date, fetch: Fetch, sleep: Callable[[float], None], clock: Callable[[], float],
              deadline: float, workers: int, pause: float, say: Callable[[str], None], sample: int = 0,
              tonight: Tonight | None = None, shops: frozenset[str] = frozenset(), scanned: bool = False,
              shown_order: Mapping[str, list[str]] | None = None, dearer: Collection[str] = (),
              readers: Readers | None = None, round_time: RoundTime | None = None,
              clone: tuple[int, int] | None = None) -> Round:
    """Ask every shop (of `clone`, (its number, how many), when given) its products in the rules'
    order, until the deadline. `sample`: a look, at most this many products a shop; `tonight`:
    the night's answers kept as they come, those kept already not asked again; `scanned`: the
    rule of how many of a shop's products pass (section 19), with `shown_order` the order of
    19.4 of each shop's shown products and `dearer` those of them a cheaper shop shows, asked
    after the cap's candidates (20.7.4); `readers`: what reads the answers (19.5);
    `round_time`: how long the night's round has asked, a round started again included (21)."""
    from picwise_providers.shop_cap import shop_limits

    tonight = tonight or Tonight(None)
    round_time = round_time or RoundTime(None, clock)
    began = clock()
    # 23 (owner, 2026-11-26): of a shop the bot asks at most `asked` a day, which may be more than
    # the most it passes to the site; the rest of a shop's day goes to new products.
    asked_most = shop_limits()[1]
    order = L.asking_order(ledger, night, rows, shown=shown, candidates=candidates, parts=parts, scanned=scanned,
                           shown_order=shown_order, dearer=dearer, limit=asked_most if scanned else 0)
    if clone is not None:
        order = {shop: keys for shop, keys in order.items() if clone_of(shop, clone[1]) == clone[0]}
    if shops:
        order = {shop: keys for shop, keys in order.items() if shop in shops}
    if sample > 0:
        order = {shop: keys[:sample] for shop, keys in order.items()}
    kept = tonight.load()
    say(f"to ask: {sum(len(keys) for keys in order.values()):,} products of {len(order)} shops"
        + (f" (clone {clone[0]} of {clone[1]})" if clone is not None else "")
        + (f"; {len(kept):,} answered already tonight (the round goes on)" if kept else ""))
    results: dict[str, ShopResult] = {}
    seconds: dict[str, float] = {}
    late: dict[str, float] = {}
    lock = threading.Lock()

    def one(shop: str) -> None:
        done = {key: kept[key] for key in order[shop] if key in kept}
        started = clock()
        got: dict[str, PageAnswer] = dict(done)

        def keep(key: str, answer: PageAnswer) -> None:
            got[key] = answer
            tonight.keep(key, answer)
            round_time.keep()

        try:
            result = ask_shop([rows[key] for key in order[shop]], fetch=fetch, sleep=sleep, clock=clock,
                              deadline=deadline, pause=pause, done=done, keep=keep, readers=readers)
        except Exception as error:  # noqa: BLE001 - one shop never ends the whole round
            # What went wrong with one shop's asking ends that shop's night, never the round:
            # its answers so far count, as for a shop stopped by the deadline.
            say(f"the checks: {shop}: its asking ended by an error ({type(error).__name__}); "
                f"its {len(got):,} answers count")
            result = _ended(got, type(error).__name__)
        with lock:
            results[shop] = result
            seconds[shop] = clock() - started
            late[shop] = started - began

    threads = workers if workers > 0 else min(SHOPS_AT_ONCE, len(order))
    with ThreadPoolExecutor(max_workers=max(1, threads)) as pool:
        list(pool.map(one, sorted(order, key=lambda shop: (-len(order[shop]), shop))))
    round_time.keep(now=True)
    return Round(results=results, ordered={shop: len(keys) for shop, keys in order.items()}, seconds=seconds,
                 late=late, threads=max(1, threads), processes=readers.processes if readers is not None else 0,
                 hours=round_time.seconds() / 3600.0)


def record_round(rows: dict[str, Row], rounds: list[Round], *, shown: set[str], parts: Mapping[str, str],
                 shared_ids: set[str], candidates: list[str], ledger: L.Ledger, night: date,
                 awin: Mapping[str, tuple[str | None, str]] | None, feeds: Mapping[str, date | None],
                 owner_cut_shops: list[str], owner_awin_word: bool, old_feed_rule: bool = False,
                 awin_closed_out: bool = False, scanned: bool = False) -> tuple[L.Night, dict]:
    """The night recorded from the askers' days (the bot's, or every clone's, 22): every
    answer judged, the night recorded, the decisions; the note."""
    from picwise_providers.shop_cap import shop_limits

    most, asked_most = shop_limits()
    # 21: with the rule on, a pass counts for the day (three nights while a shop's asking was
    # not whole); without it, thirty nights as before.
    pass_nights = L.PASS_NIGHTS_DAY if scanned else L.PASS_VALID_NIGHTS
    results: dict[str, ShopResult] = {}
    seconds: dict[str, float] = {}
    complete: set[str] = set()
    for asked in rounds:
        results.update(asked.results)
        seconds.update(asked.seconds)
        complete |= asked.complete()
    asked_hours = min((asked.hours for asked in rounds), default=0.0)
    whole_round = bool(rounds) and all(asked.whole for asked in rounds)
    readings: dict[str, L.Reading] = {}
    shop_nights: dict[str, ShopNight] = {}
    words: dict[str, Counter] = defaultdict(Counter)
    by_page = prices_by_page(rows.values())
    for shop, result in results.items():
        shop_nights[shop] = result.night
        readings.update(judge({key: rows[key] for key in result.answers}, result, shared_ids=shared_ids,
                              by_page=by_page, stock_words=words[shop]))
    night_result = L.record_night(ledger, night, rows, readings, shop_nights, shown=shown, parts=parts, awin=awin,
                                  feeds=feeds, owner_cut_shops=owner_cut_shops, owner_awin_word=owner_awin_word,
                                  awin_closed_out=awin_closed_out, complete=complete if scanned else ())
    made = L.decisions(ledger, night, rows, shown=shown, candidates=candidates, came_back=night_result.came_back,
                       old_feed_rule=old_feed_rule, pass_nights=pass_nights, passed_over=most if scanned else 0)
    if not old_feed_rule and not night_result.note.get("ours"):
        # What the Proposed rule of a feed over 7 days old (5.6.4) would not show tonight, while
        # it waits for the owner's yes: counted for him, changing nothing.
        with_it = L.decisions(ledger, night, rows, shown=shown, candidates=candidates, old_feed_rule=True,
                              pass_nights=pass_nights)["wait"]
        would: Counter = Counter(rows[key].shop for key, why in with_it.items()
                                 if why == "old feed, no fresh reading" and key not in made["wait"])
        night_result.note["old_feed_would_wait"] = {"products": sum(would.values()), "shops": len(would),
                                                    "most": [[shop, count] for shop, count in would.most_common(10)]}
    # How many of a shop's products pass (section 19): whether the rule was on, the nights a
    # pass counts for, the most asked of a shop, the processes the pages were read on (19.5).
    night_result.note["shop_rule"] = {"on": scanned, "pass_nights": pass_nights,
                                      "most_asked_of_a_shop": asked_most if scanned else None,
                                      # 23: the most a shop passes to the site, when fewer than it is asked.
                                      "most_shown_of_a_shop": most if scanned else None,
                                      "processes": sum(asked.processes for asked in rounds),
                                      "shops_at_once": sum(asked.threads for asked in rounds) or 1,
                                      # 21: how long the round asked, whether that was all day, and
                                      # the shops asked whole (their products not passed tonight wait).
                                      "round_hours": round(asked_hours, 1), "whole_round": whole_round,
                                      "asked_whole": len(complete) if scanned else 0,
                                      "not_whole": sorted(set(results) - complete)[:SHOPS_LISTED] if scanned else [],
                                      # 22: the clones the day was asked by (1: the bot alone), and each one's hours.
                                      "clones": len(rounds),
                                      "clone_hours": [round(asked.hours, 1) for asked in rounds]}
    night_result.note["asked_by_shop"] = {shop: [result.night.requests, len(result.answers), result.stopped]
                                          for shop, result in sorted(results.items())}
    # How long each shop's asking took, and the crawl-delay it asks for: the bot's pace (rules 4.7).
    night_result.note["seconds_by_shop"] = {shop: [round(seconds.get(shop, 0.0), 1), result.night.crawl_delay]
                                            for shop, result in sorted(results.items())}
    # The shops' own availability words behind tonight's stock readings (rules 5.2).
    night_result.note["stock_words_by_shop"] = {shop: dict(sorted(counts.items()))
                                                for shop, counts in sorted(words.items()) if counts}
    return night_result, made


def run(rows: dict[str, Row], *, shown: set[str], parts: Mapping[str, str], shared_ids: set[str],
        candidates: list[str], ledger: L.Ledger, night: date, fetch: Fetch, sleep: Callable[[float], None],
        clock: Callable[[], float], deadline: float, workers: int, pause: float,
        awin: Mapping[str, tuple[str | None, str]] | None, feeds: Mapping[str, date | None],
        owner_cut_shops: list[str], owner_awin_word: bool, say: Callable[[str], None],
        sample: int = 0, tonight: Tonight | None = None, shops: frozenset[str] = frozenset(),
        old_feed_rule: bool = False, awin_closed_out: bool = False, scanned: bool = False,
        shown_order: Mapping[str, list[str]] | None = None, dearer: Collection[str] = (),
        readers: Readers | None = None, round_time: RoundTime | None = None,
        ) -> tuple[L.Night, dict]:
    """Ask every shop its products in the rules' order (`ask_round`); record the night; the
    decisions (`record_round`): the bot alone, as before the clones (22)."""
    asked = ask_round(rows, shown=shown, parts=parts, candidates=candidates, ledger=ledger, night=night, fetch=fetch,
                      sleep=sleep, clock=clock, deadline=deadline, workers=workers, pause=pause, say=say, sample=sample,
                      tonight=tonight, shops=shops, scanned=scanned, shown_order=shown_order, dearer=dearer,
                      readers=readers, round_time=round_time)
    return record_round(rows, [asked], shown=shown, parts=parts, shared_ids=shared_ids, candidates=candidates,
                        ledger=ledger, night=night, awin=awin, feeds=feeds, owner_cut_shops=owner_cut_shops,
                        owner_awin_word=owner_awin_word, old_feed_rule=old_feed_rule, awin_closed_out=awin_closed_out,
                        scanned=scanned)


def pass_counts_for(rule: Mapping[str, Any]) -> str:
    """How long a pass counts, as the night's note says (19.3.1; 21), with the round's hours."""
    nights = int(rule.get("pass_nights") or 0)
    if nights != L.PASS_NIGHTS_DAY:
        return f"{nights} nights"
    text = f"the day it was made, {L.PASS_NIGHTS_SCANNED} nights while its shop is not asked whole"
    if "round_hours" in rule:
        text += (f" (the round asked {float(rule.get('round_hours') or 0):.1f} hours, "
                 + ("all day" if rule.get("whole_round") else "NOT all day: shops not asked all their products keep them")
                 + f"; {int(rule.get('asked_whole') or 0):,} shops asked whole)")
    return text


def print_night(note: Mapping[str, Any], made: Mapping[str, Any], ledger: L.Ledger, say: Callable[[str], None]) -> None:
    """Counts and shop names only (rules 11)."""
    if note.get("ours"):
        say("the round is ours: fewer than half of the shops answered at all; nothing recorded (rules 7.1)")
        return
    rule = note.get("shop_rule") or {}
    if rule:
        say(f"how many of a shop's products pass (section 19): {'ON' if rule.get('on') else 'off'}; a pass counts for "
            + pass_counts_for(rule)
            + (f"; at most {rule['most_asked_of_a_shop']:,} asked of a shop" if rule.get("most_asked_of_a_shop") else "")
            + f"; {rule.get('shops_at_once')} shops at once, pages read on "
            + (f"{rule['processes']} processes" if rule.get("processes") else "the bot's own process"))
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
    old_feed = note.get("old_feed_would_wait") or {}
    if old_feed.get("products"):
        say(f"the Proposed rule of a feed over 7 days old (waits for the owner's yes) would not show "
            f"{old_feed['products']:,} products of {old_feed['shops']} shops: "
            + ", ".join(f"{shop} {count:,}" for shop, count in old_feed.get("most") or []))
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
    parser.add_argument("--workers", type=int, default=WORKERS, help="shops asked at once; 0: every shop")
    parser.add_argument("--processes", type=int, default=PROCESSES, help="processes the pages are read on; 0: none")
    parser.add_argument("--shop-rule", choices=("file", "on", "off"), default="file",
                        help="how many of a shop's products pass (section 19): as its switch says, or on or off for a look")
    parser.add_argument("--pause", type=float, default=PAUSE)
    parser.add_argument("--dry", action="store_true",
                        help="a look: write nothing (no ledger, no decisions, no note); print what the night decided")
    parser.add_argument("--sample", type=int, default=0, help="a look: at most this many products a shop")
    parser.add_argument("--minutes", type=float, default=0.0, help="a look: ask for this many minutes only")
    parser.add_argument("--shop", action="append", default=[], help="a look: these shops only")
    parser.add_argument("--clone", default="",
                        help="22: K/N, ask only clone K's shops of N (by a code of each shop's name) and keep its "
                             "day for the night's recording; record nothing")
    parser.add_argument("--record", type=int, default=0,
                        help="22: record the night from N clones' days (run after --until); ask nothing")
    parser.add_argument("--wait-minutes", type=float, default=RECORD_WAIT_MINUTES,
                        help="22: with --record, how long to wait for a clone still finishing its day")
    args = parser.parse_args(argv)
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass
    say = print
    start = now or datetime.now(timezone.utc)
    if args.record:
        # The night is the morning of the last `--until` passed: the clones' night.
        night = _deadline(start, args.until).date() - timedelta(days=1)
        return _record_night(args, night=night, sleep=sleep, clock=clock, environ=environ, say=say)
    clone = _clone_of_argument(args.clone)
    if args.clone and clone is None:
        say(f"the checks: --clone {args.clone!r} is not K/N; nothing asked")
        return 2
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
    from picwise_providers.shop_cap import shop_cap_on

    scanned = shop_cap_on() if args.shop_rule == "file" else args.shop_rule == "on"
    # Started before the catalogue is read, so that nothing of it is in their way (19.5).
    readers = Readers.start(args.processes, say)
    try:
        if clone is not None:
            return _clone_day(args, clone, readers=readers, scanned=scanned, night=night, deadline=deadline,
                              fetch=fetch, sleep=sleep, clock=clock, say=say)
        return _night(args, readers=readers, scanned=scanned, night=night, deadline=deadline,
                      fetch=fetch, sleep=sleep, clock=clock, environ=environ, say=say)
    finally:
        readers.close()


def _clone_of_argument(text: str) -> tuple[int, int] | None:
    """"K/N" as (K, N), 1 <= K <= N; None when not so."""
    try:
        number, of = (int(part) for part in str(text or "").split("/"))
    except ValueError:
        return None
    return (number, of) if 1 <= number <= of else None


def clone_name(night: date | str, clone: tuple[int, int]) -> str:
    """The name a clone's files carry for the night (its answers, its hours, its day)."""
    return f"{night}-clone{clone[0]}of{clone[1]}"


def _write_whole(path: Path, text: str) -> None:
    temporary = path.with_name(path.name + ".part")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def _clone_day(args: argparse.Namespace, clone: tuple[int, int], *, readers: Readers, scanned: bool, night: date,
               deadline: float, fetch: Fetch, sleep: Callable[[float], None], clock: Callable[[], float],
               say: Callable[[str], None]) -> int:
    """22: one clone's day: only its shops asked, its answers kept as they come, its day kept
    at its end (`CLONE_DAY`) for the night's recording (`--record`), which records the night
    once from every clone's day. Awin is read by the recording, not by a clone."""
    try:
        rows, parts, _shared_ids, orders, dearer = rows_from_catalogue(args.catalogue, order=scanned)
    except ValueError as error:
        say(f"the checks: {error}; nothing asked")
        return 1
    shown = set(rows)
    extra, candidates = rows_from_candidates(args.checks / L.CANDIDATES_NAME)
    for key, row in extra.items():
        rows.setdefault(key, row)
    # Only its shops' rows kept: a clone holds a part of the catalogue.
    mine = {key: row for key, row in rows.items() if clone_of(row.shop, clone[1]) == clone[0]}
    del rows
    ledger = L.load(args.checks / L.LEDGER_NAME)
    if any(entry.get("night") == night.isoformat() for entry in ledger.nights):
        say(f"the night of {night} is recorded already: nothing asked")
        return 0
    name = clone_name(night, clone)
    tonight = Tonight(args.checks / TONIGHT.format(night=name))
    round_time = RoundTime(args.checks / TONIGHT_TIME.format(night=name), clock)
    if round_time.before:
        say(f"clone {clone[0]} of {clone[1]}: its day of the night of {night} goes on: it has asked "
            f"{round_time.before / 3600.0:.1f} hours already")
    asked = ask_round(mine, shown=shown & set(mine), parts=parts, candidates=[key for key in candidates if key in mine],
                      ledger=ledger, night=night, fetch=fetch, sleep=sleep, clock=clock, deadline=deadline,
                      workers=args.workers, pause=args.pause, say=say, tonight=tonight, scanned=scanned,
                      shown_order={shop: keys for shop, keys in orders.items() if clone_of(shop, clone[1]) == clone[0]},
                      dearer=dearer, readers=readers, round_time=round_time, clone=clone)
    _write_whole(args.checks / CLONE_DAY.format(name=name), json.dumps(asked.to_record(), sort_keys=True))
    say(f"clone {clone[0]} of {clone[1]}: {len(asked.results)} shops asked, "
        f"{sum(len(result.answers) for result in asked.results.values()):,} answers, {asked.hours:.1f} hours; "
        "kept for the night's recording")
    return 0


def _record_night(args: argparse.Namespace, *, night: date, sleep: Callable[[float], None],
                  clock: Callable[[], float], environ: Mapping[str, str], say: Callable[[str], None]) -> int:
    """22: the night recorded once from every clone's day: each clone's shops' answers and
    what each shop gave, a clone that kept no day counted as stopped (its shops' answers so far
    count, none of its shops asked whole); then the ledger, the decisions and the note, as the
    bot alone records them."""
    clones = args.record
    names = [clone_name(night, (number, clones)) for number in range(1, clones + 1)]
    waited_until = clock() + max(0.0, args.wait_minutes) * 60.0
    while not all((args.checks / CLONE_DAY.format(name=name)).exists() for name in names) and clock() < waited_until:
        sleep(30.0)
    try:
        rows, parts, shared_ids, _orders, _dearer = rows_from_catalogue(args.catalogue)
    except ValueError as error:
        say(f"the checks: {error}; nothing recorded")
        return 1
    shown = set(rows)
    extra, candidates = rows_from_candidates(args.checks / L.CANDIDATES_NAME)
    for key, row in extra.items():
        rows.setdefault(key, row)
    ledger = L.load(args.checks / L.LEDGER_NAME)
    if any(entry.get("night") == night.isoformat() for entry in ledger.nights):
        say(f"the night of {night} is recorded already: nothing recorded")
        return 0
    rounds: list[Round] = []
    for number, name in enumerate(names, start=1):
        answers = Tonight(args.checks / TONIGHT.format(night=name)).load()
        day = args.checks / CLONE_DAY.format(name=name)
        try:
            rounds.append(Round.from_record(json.loads(day.read_text(encoding="utf-8")), answers, rows))
        except (OSError, ValueError, KeyError, TypeError):
            say(f"clone {number} of {clones} kept no day: its {len(answers):,} answers count, none of its shops "
                "asked whole")
            rounds.append(Round.unfinished(answers, rows))
    from picwise_providers.shop_cap import shop_cap_on

    scanned = shop_cap_on() if args.shop_rule == "file" else args.shop_rule == "on"
    awin, feeds = read_awin(environ, cache_dir=args.cache, say=say)
    cut_shops, awin_word = owner_words()
    yes = owner_yes()
    result, made = record_round(rows, rounds, shown=shown, parts=parts, shared_ids=shared_ids, candidates=candidates,
                                ledger=ledger, night=night, awin=awin, feeds=feeds, owner_cut_shops=cut_shops,
                                owner_awin_word=awin_word, old_feed_rule=yes["old_feed_rule"],
                                awin_closed_out=yes["awin_closed_out"], scanned=scanned)
    L.save(ledger, args.checks / L.LEDGER_NAME)
    L.write_decisions(made, args.checks / L.DECISIONS_NAME)
    (args.checks / NOTE_NAME).write_text(json.dumps(result.note, indent=1, sort_keys=True), encoding="utf-8")
    Tonight(args.checks / TONIGHT.format(night=names[0])).forget()
    for old in args.checks.glob(CLONE_DAY.format(name="*")):
        old.unlink(missing_ok=True)
    print_night(result.note, made, ledger, say)
    return 0


def _night(args: argparse.Namespace, *, readers: Readers, scanned: bool, night: date, deadline: float,
           fetch: Fetch, sleep: Callable[[float], None], clock: Callable[[], float], environ: Mapping[str, str],
           say: Callable[[str], None]) -> int:
    """`main`'s night, once its readers have started."""
    try:
        rows, parts, shared_ids, orders, dearer = rows_from_catalogue(args.catalogue, order=scanned)
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
    round_time = RoundTime(None if args.dry else args.checks / TONIGHT_TIME.format(night=night), clock)
    if round_time.before:
        say(f"the round of the night of {night} goes on: it has asked {round_time.before / 3600.0:.1f} hours already")
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
                       old_feed_rule=yes["old_feed_rule"], awin_closed_out=yes["awin_closed_out"],
                       scanned=scanned, shown_order=orders, dearer=dearer, readers=readers, round_time=round_time)
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
    said = note.get("stock_words_by_shop") or {}
    say("== stock read as sold out, per shop: the shop's own words (rules 5.2)")
    for name in sorted(said, key=lambda shop: -sum(count for word, count in said[shop].items() if word.startswith("sold out"))):
        sold_out = {word: count for word, count in said[name].items() if word.startswith("sold out")}
        if sold_out:
            say(f"{name}: " + ", ".join(f"{word[10:]} {count}" for word, count in sorted(sold_out.items()))
                + f"; in stock {sum(count for word, count in said[name].items() if word.startswith('in stock'))}")
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
