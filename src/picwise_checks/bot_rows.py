"""What the checks' bots ask, and which bot asks each shop (the checks' rules 22 and 23).

Owner, 2026-11-26: «8 bot αντί για 4, 2 σε κάθε πυρήνα. Κάθε bot είναι ξεχωριστό πρόγραμμα και
αναλαμβάνει έως περίπου 100 καταστήματα»; «κάθε κατάστημα παίρνει σταθερό κωδικό ... και πηγαίνει
πάντα στο ίδιο bot»; «όποιο προϊόν δεν πληροί τις προϋποθέσεις σβήνεται αμέσως και δεν μένει να
πιάνει μνήμη». And the brief he gave the builder: the code from the shop's number at Awin, not its
name; a switch for each bot, so that they open one by one.

- **Which bot** (`clone_of`): a code of the shop's number at Awin (its advertiser id, which both of
  Awin's links give: `rows.advertiser_of`), modulo the number of bots, plus one; a shop whose rows
  name no number, by a code of its name, as from 25/11. Always the same bot, and a shop asked by
  one bot only, so never faster than it allows (the rules 4.3). Every bot works the assignment
  out from the same files, so they agree.
- **The switch** (`data/checks_clones.json`, `clones_switch`): how many bots the shops are split
  into, and which of them ask as bots of their own. None: the bot alone asks every shop, as
  before. Some: the bot alone asks the shops of the others and records the night from its day and
  theirs. All: the bot alone is off, and the night's recording records it from every bot's day.
- **What a bot reads** (`read_bot_rows`): the prepared catalogue and the preparation's rows for the
  bot are read **in a process of their own** (`read_apart`), which hands back only the rows of
  the shops the bot asks and ends: the catalogue's products are never held by the bot, and the
  memory they took goes back to the server when that process ends (a process that has let go of
  objects keeps much of their memory). Where that process cannot start, the files are read on
  the bot's own process, as before, and it says so.

Code without a network (the rules 14).
"""
from __future__ import annotations

import gc
import gzip
import json
import resource
import zlib
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Collection, Iterable, Mapping

from .rows import row_from_record, row_of
from .verdicts import Row

SWITCH_FILE = Path(__file__).resolve().parents[2] / "data" / "checks_clones.json"
# Owner, 2026-11-26: eight bots.
CLONES = 8
# 23, the second asking (the brief: «Ξεκινά από τα προϊόντα που βγαίνουν στις πρώτες κάρτες κάθε
# είδους»): a kind's first cards are its cheapest four and its middle price (the Recommended).
FIRST_CARDS = 4


def clone_of(shop: str, clones: int, advertiser: str = "") -> int:
    """The bot, 1 to `clones`, that asks a shop: by a code of its number at Awin when its rows give
    one, else of its name (spaces and case aside, as from 25/11)."""
    ident = str(advertiser or "").strip()
    text = f"awin {ident}" if ident else " ".join(str(shop or "").split()).casefold()
    return zlib.crc32(text.encode("utf-8", "surrogatepass")) % max(1, clones) + 1


def shop_advertisers(rows: Iterable[Row]) -> dict[str, str]:
    """Each shop's number at Awin, the one most of its rows give (the smallest of those tied);
    "" for a shop whose rows give none."""
    seen: dict[str, Counter] = {}
    for row in rows:
        counts = seen.setdefault(row.shop, Counter())
        if row.advertiser:
            counts[row.advertiser] += 1
    found: dict[str, str] = {}
    for shop, counts in seen.items():
        if counts:
            most = max(counts.values())
            found[shop] = min(ident for ident, count in counts.items() if count == most)
        else:
            found[shop] = ""
    return found


def assignment(rows: Iterable[Row], clones: int) -> dict[str, int]:
    """Every shop of `rows`, the bot that asks it."""
    return {shop: clone_of(shop, clones, ident) for shop, ident in shop_advertisers(rows).items()}


@dataclass(frozen=True)
class Clones:
    """The switch: how many bots the shops are split into, and which ask as bots of their own."""

    clones: int = CLONES
    bots: frozenset[int] = frozenset()

    @property
    def every(self) -> frozenset[int]:
        return frozenset(range(1, self.clones + 1))

    @property
    def rest(self) -> frozenset[int]:
        """The bots whose shops the bot alone asks."""
        return self.every - self.bots

    @property
    def all_on(self) -> bool:
        return bool(self.bots) and not self.rest


def clones_switch(path: Path | None = None) -> Clones:
    """`data/checks_clones.json`: `clones`, how many (8 when it names none), and `bots`, the numbers
    that ask as bots of their own, each from 1 to `clones` (anything else left out). A file that
    cannot be read: none on, the bot alone asks every shop."""
    try:
        words = json.loads((path or SWITCH_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return Clones()
    if not isinstance(words, dict):
        return Clones()
    clones = words.get("clones")
    clones = clones if isinstance(clones, int) and not isinstance(clones, bool) and 1 <= clones <= 64 else CLONES
    bots = words.get("bots") if isinstance(words.get("bots"), list) else []
    return Clones(clones=clones, bots=frozenset(number for number in bots
                                                if isinstance(number, int) and not isinstance(number, bool)
                                                and 1 <= number <= clones))


@dataclass
class BotRows:
    """What a bot asks: the rows of its shops (the shown, the cap's candidates, the cut ones the
    feed still lists), which of them the site shows, each shown one's kind as the cap reads it,
    the ids more than one shown product carries, per shop its shown products in the order of
    19.4 and those of them a cheaper shop shows, the candidates in their order; every shop of the
    night and its bot; and the counts of the whole night, before the shops were chosen."""

    rows: dict[str, Row] = field(default_factory=dict)
    shown: set[str] = field(default_factory=set)
    parts: dict[str, str] = field(default_factory=dict)
    shared_ids: set[str] = field(default_factory=set)
    orders: dict[str, list[str]] = field(default_factory=dict)
    dearer: set[str] = field(default_factory=set)
    candidates: list[str] = field(default_factory=list)
    bot_of: dict[str, int] = field(default_factory=dict)
    counts: dict[str, int] = field(default_factory=dict)
    # How the files were read: "apart" (a process of their own) or "here", and that process's peak
    # memory in MB.
    read: str = "here"
    read_peak_mb: float = 0.0
    # The ledger's part of the shops chosen (a bot of its own reads only its shops'), when asked for.
    ledger: Any = None
    # 23: the shown products on the first cards of their kind, over the whole catalogue, each with its
    # place among them (`first_cards`).
    first_cards: dict[str, int] = field(default_factory=dict)

    @property
    def shops(self) -> frozenset[str]:
        return frozenset(row.shop for row in self.rows.values())


def catalogue_rows(path: Path, *, order: bool = False,
                   ) -> tuple[dict[str, Row], dict[str, str], set[str], dict[str, list[str]], set[str]]:
    """The products the site shows: their rows, their kinds as the cap reads them, the ids more
    than one of them carries (the site's button finds a product by its id), and, with `order`,
    per shop its products' keys in the order of 19.4 (`shop_cap.shop_order`), the order its shown
    products are asked again in (19.3.2), and of them the keys a cheaper shop shows, asked after
    the cap's candidates (20.7.4)."""
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


def candidate_rows(path: Path) -> tuple[dict[str, Row], list[str]]:
    """The rows the preparation names for the bot: the cap's candidates and the cut products the
    feed still lists; and which of them are candidates."""
    if not path.exists():
        return {}, []
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    rows = {}
    for values in payload.get("rows", []):
        row = row_from_record(values)
        rows[row.key] = row
    return rows, [key for key in payload.get("candidates", []) if key in rows]


def first_cards(rows: Mapping[str, Row], shown: Collection[str], parts: Mapping[str, str]) -> dict[str, int]:
    """The shown products a search for their kind puts first, over every shop, each with its place:
    of each kind (as the cap reads it), its middle price first (the Recommended, which a search
    shows first), then its `FIRST_CARDS` cheapest, cheapest first."""
    by_part: dict[str, list[str]] = {}
    for key in shown:
        if key in rows:
            by_part.setdefault(parts.get(key, ""), []).append(key)
    found: dict[str, int] = {}
    for keys in by_part.values():
        priced = sorted(keys, key=lambda key: (rows[key].price is None, rows[key].price or 0.0, key))
        for place, key in enumerate([priced[len(priced) // 2]] + priced[:FIRST_CARDS]):
            found.setdefault(key, place)
    return found


def read_bot_rows(catalogue: Path, candidates: Path, *, order: bool = False, clones: int = 0,
                  chosen: Collection[int] = (), ledger: Path | None = None) -> BotRows:
    """What the bots numbered `chosen` (of `clones`) ask; every shop when `chosen` is empty or
    `clones` 0; with `ledger`, that file's part of their shops (`ledger.load`). Raises ValueError
    when the catalogue cannot be read."""
    rows, parts, shared_ids, orders, dearer = catalogue_rows(catalogue, order=order)
    shown = set(rows)
    extra, named = candidate_rows(candidates)
    for key, row in extra.items():
        rows.setdefault(key, row)
    counts = {"shown": len(shown), "candidates": len(named), "cut_listed": len(extra) - len(named),
              "shared_ids": len(shared_ids), "shops": len({row.shop for row in rows.values()})}
    bot_of = assignment(rows.values(), clones) if clones else {}
    cards = first_cards(rows, shown, parts)
    wanted = frozenset(chosen)
    if clones and wanted and wanted != frozenset(range(1, clones + 1)):
        shops = {shop for shop, number in bot_of.items() if number in wanted}
        rows = {key: row for key, row in rows.items() if row.shop in shops}
        shown &= set(rows)
        parts = {key: part for key, part in parts.items() if key in rows}
        ids = {row.product_id for row in rows.values()}
        shared_ids &= ids
        orders = {shop: keys for shop, keys in orders.items() if shop in shops}
        dearer &= set(rows)
        named = [key for key in named if key in rows]
        cards = {key: place for key, place in cards.items() if key in rows}
    found = BotRows(rows=rows, shown=shown, parts=parts, shared_ids=shared_ids, orders=orders, dearer=dearer,
                    candidates=named, bot_of=bot_of, counts=counts, first_cards=cards)
    if ledger is not None:
        from .ledger import load

        found.ledger = load(ledger, shops=found.shops if clones and wanted else None)
    return found


def _peak_mb(who: int) -> float:
    """The peak memory of this process (`resource.RUSAGE_SELF`) or of its children that have ended
    (`RUSAGE_CHILDREN`), in MB (Linux gives kilobytes)."""
    try:
        return round(resource.getrusage(who).ru_maxrss / 1024.0, 1)
    except (OSError, ValueError):
        return 0.0


def peak_mb() -> float:
    return _peak_mb(resource.RUSAGE_SELF)


def ready() -> bool:
    """What a process of its own is first asked, to know it started."""
    return True


def read_apart(catalogue: Path, candidates: Path, *, order: bool, clones: int, chosen: Collection[int],
               say: Callable[[str], None], apart: bool = True, ledger: Path | None = None) -> BotRows:
    """`read_bot_rows` in a process of its own, started fresh (not copied from the bot), which ends
    once it has handed back the rows: the memory the catalogue took goes back to the server
    (module docstring). Read on the bot's own process when `apart` is false or that process cannot
    start (the service's sandbox), and said so."""
    if apart:
        import multiprocessing
        from concurrent.futures import ProcessPoolExecutor
        from concurrent.futures.process import BrokenProcessPool

        pool = None
        try:
            pool = ProcessPoolExecutor(max_workers=1, mp_context=multiprocessing.get_context("spawn"))
            pool.submit(ready).result(timeout=120)
        except Exception as error:  # noqa: BLE001 - the sandbox may refuse it: read here, and say so
            if pool is not None:
                pool.shutdown(wait=False, cancel_futures=True)
            pool = None
            say(f"the catalogue is read on the bot's own process: a process of its own did not start ({type(error).__name__})")
        if pool is not None:
            try:
                found = pool.submit(read_bot_rows, catalogue, candidates, order=order, clones=clones,
                                    chosen=tuple(chosen), ledger=ledger).result()
            except BrokenProcessPool:
                # Stopped while it read (its memory's limit, most likely): never read again here,
                # which would only stop the bot itself the same way.
                raise ValueError("the process the catalogue was read in stopped before it ended (its memory?)") from None
            finally:
                pool.shutdown(wait=True)
            found.read = "apart"
            # The largest of this process's children that have ended: the reading's (the readers
            # of pages end only with the bot's day).
            found.read_peak_mb = _peak_mb(resource.RUSAGE_CHILDREN)
            return found
    found = read_bot_rows(catalogue, candidates, order=order, clones=clones, chosen=chosen, ledger=ledger)
    found.read = "here"
    return found


def shops_of(bot_of: Mapping[str, int], numbers: Collection[int]) -> frozenset[str]:
    """The shops the bots numbered `numbers` ask."""
    wanted = frozenset(numbers)
    return frozenset(shop for shop, number in bot_of.items() if number in wanted)


def table(rows: Mapping[str, Row], shown: Collection[str], candidates: Collection[str], bot_of: Mapping[str, int],
          clones: int) -> list[dict[str, Any]]:
    """Per bot: its shops, by their number at Awin or by name, its shown products and its candidates,
    and its largest shop (for a look, and the night's note)."""
    shown = frozenset(shown)
    named = frozenset(candidates)
    advertiser = shop_advertisers(rows.values())
    per: dict[int, dict[str, Any]] = {number: {"bot": number, "shops": 0, "by_number": 0, "by_name": 0, "shown": 0,
                                               "candidates": 0, "largest": ["", 0]} for number in range(1, clones + 1)}
    by_shop: Counter = Counter()
    for key, row in rows.items():
        if key in shown:
            by_shop[row.shop] += 1
    for shop, number in bot_of.items():
        entry = per.setdefault(number, {"bot": number, "shops": 0, "by_number": 0, "by_name": 0, "shown": 0,
                                        "candidates": 0, "largest": ["", 0]})
        entry["shops"] += 1
        entry["by_number" if advertiser.get(shop) else "by_name"] += 1
        if by_shop[shop] > entry["largest"][1]:
            entry["largest"] = [shop, by_shop[shop]]
    for key, row in rows.items():
        number = bot_of.get(row.shop)
        if number is None:
            continue
        if key in shown:
            per[number]["shown"] += 1
        elif key in named:
            per[number]["candidates"] += 1
    return [per[number] for number in sorted(per)]
