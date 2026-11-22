"""Task 6's look before its rules: what the question "is it the kind itself" would be asked about.

Owner's plan of 21/11, step 8: a question to the AI for every product, «είναι το ίδιο το
προϊόν ή αξεσουάρ, ανταλλακτικό ή αναλώσιμο;»; the second opinion of the same day: asked
for the kind a search would show the product as, and the products the kinds' lists hide
wrongly brought back by it. Before any rule is written, this counts on a copy of the
server's prepared catalogue what that question would be asked about. Read-only: nothing is
asked of the AI, nothing on the server or the site changes.

    python3 deployment/server/look_itself.py CATALOGUE.json.gz --notes DIR [--shelves ANSWERS.jsonl.gz] \
        [--gone GONE.json] [--offers OFFERS.json] [--families FAMILIES.json] [--front 24] [--no-searches]

Written as numbered text files in `--notes` (a later step of the workflow says them as the
run's notes, which GitHub's API shows without a login) and printed:

1. the pairs: the products with a kind, each with every kind a search would show it as; a
   question is one (question key, kind): a product's sizes and colours share the key
   (`ai_shelves.key_of`); how long a product's line for the AI is;
2. the kinds by how many keys they hold;
3. the products with no kind whose own words name a kind: a search for that kind lists
   them too (`search_selection._unannotated_product_names_concept`);
4. what the kinds' lists took out of a kind (`ai_shelves.checked_kinds`): the products the
   question could bring back;
5. the front: each kind's first name searched as the site answers it, its first cards and
   its Recommended: how many questions the first cards are, and by which way each card
   came (its kind, or its words);
6. the 40 searches of the measure after (`measure_after.SEARCHES`), their first 12 cards:
   price, title, shop, the way it came and the AI's line.

Titles, shops, prices and categories are printed, never a link, an id or the key. Always
exits 0.
"""
from __future__ import annotations

import argparse
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for folder in (ROOT, ROOT / "src", HERE):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

FRONT = 24
CARDS = 12
TOP = 25
EXAMPLES = 20
# GitHub keeps about 4,000 characters of a note (the look of 22/11 lost the rest of each).
NOTE_CHARS = 3600
TITLE = 62


def _short(text: Any, width: int = TITLE) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= width else text[: width - 1].rstrip() + "…"


def _share(part: int, whole: int) -> str:
    return f"{part:,} of {whole:,} ({100 * part / whole:.1f}%)" if whole else f"{part:,} of 0"


class Notes:
    """The look's notes: each a title and lines, cut into files of at most `NOTE_CHARS`."""

    def __init__(self, folder: Path | None) -> None:
        self.folder = folder
        self.count = 0
        if folder is not None:
            folder.mkdir(parents=True, exist_ok=True)

    def say(self, title: str, lines: list[str]) -> None:
        part: list[str] = []
        size = 0
        parts: list[list[str]] = []
        for line in lines:
            if part and size + len(line) + 1 > NOTE_CHARS:
                parts.append(part)
                part, size = [], 0
            part.append(line)
            size += len(line) + 1
        if part:
            parts.append(part)
        for number, chunk in enumerate(parts, 1):
            name = title if len(parts) == 1 else f"{title} ({number} of {len(parts)})"
            print(f"== {name}")
            for line in chunk:
                print(line)
            if self.folder is not None:
                self.count += 1
                (self.folder / f"{self.count:02d}.txt").write_text(name + "\n" + "\n".join(chunk) + "\n", encoding="utf-8")


def real_kinds(kinds: Any) -> frozenset[str]:
    return frozenset(kind for kind in kinds if not kind.startswith("__"))


def narrowest(kinds: frozenset[str]) -> frozenset[str]:
    """The kinds of a product that are no broader kind of another of its kinds."""
    from picwise_nlu.product_concepts import broader_concepts

    broad = {wide for kind in kinds for wide in broader_concepts(kind)[1:]}
    return frozenset(kind for kind in kinds if kind not in broad) or kinds


def way_of(kinds: frozenset[str], kind: str) -> str:
    """How a card of a search for `kind` came: by its kind, by its words (no kind read), as
    a doubtful product or an accessory found by its words, or as another kind."""
    if kind and kind in kinds:
        return "kind"
    if "__uncertain_kind__" in kinds:
        return "doubtful"
    if "__accessory__" in kinds:
        return "accessory"
    if not real_kinds(kinds):
        return "words"
    return "other kind"


def product_line_chars(product: Any, fields: dict[str, str]) -> int:
    """How long the line the AI would read of a product is (`audit_search._product_line`)."""
    category = fields.get("product_type") or fields.get("category") or ""
    return (
        len(_short(product.title, 140)) + len(_short(product.brand, 40)) + len(_short(category, 90))
        + len(str(product.price_text or "")) + 40
    )


def pairs_report(prepared: Any, keys: list[str]) -> tuple[list[str], list[str], dict[str, set[str]]]:
    """Parts 1 and 2: the questions of the products with a kind."""
    by_kind: dict[str, set[str]] = defaultdict(set)
    products_of: Counter[str] = Counter()
    narrow_pairs: set[tuple[str, str]] = set()
    with_kind = product_pairs = 0
    chars: list[int] = []
    markers: Counter[str] = Counter()
    for place, kinds in enumerate(prepared.kinds):
        for marker in kinds:
            if marker.startswith("__"):
                markers[marker] += 1
        real = real_kinds(kinds)
        if not real:
            if not kinds:
                markers["(no kind)"] += 1
            continue
        with_kind += 1
        product_pairs += len(real)
        for kind in real:
            by_kind[kind].add(keys[place])
            products_of[kind] += 1
        for kind in narrowest(real):
            narrow_pairs.add((keys[place], kind))
        if place % 7 == 0:
            chars.append(product_line_chars(prepared.products[place], prepared.search_fields[place]))
    questions = sum(len(found) for found in by_kind.values())
    totals = [
        f"products {len(prepared.products):,}; with a kind {with_kind:,}; " + "; ".join(
            f"{name} {count:,}" for name, count in markers.most_common()
        ),
        f"(product, kind) pairs {product_pairs:,}; questions, one a (key, kind): {questions:,}"
        f" in {len(by_kind):,} kinds; asked for the narrowest kind only: {len(narrow_pairs):,}",
        f"distinct keys among the products with a kind: {len({key for found in by_kind.values() for key in found}):,}",
    ]
    if chars:
        totals.append(
            f"a product's line for the AI: {statistics.median(chars):.0f} characters in the middle,"
            f" {statistics.mean(chars):.0f} on average (a sample of {len(chars):,})"
        )
    sizes = sorted((len(found) for found in by_kind.values()), reverse=True)
    steps = (12, 24, 48, 100, 500, 1000)
    kinds_lines = [
        "kinds by their keys: " + "; ".join(
            f"up to {step}: {sum(1 for size in sizes if size <= step)}" for step in steps
        ) + f"; over {steps[-1]}: {sum(1 for size in sizes if size > steps[-1])}",
        f"the keys beyond each kind's first {FRONT}: {sum(max(0, size - FRONT) for size in sizes):,};"
        f" within them: {sum(min(size, FRONT) for size in sizes):,}",
        "the largest: " + "; ".join(
            f"{kind} {len(found):,} keys ({products_of[kind]:,} products)"
            for kind, found in sorted(by_kind.items(), key=lambda item: -len(item[1]))[:TOP]
        ),
    ]
    return totals, kinds_lines, by_kind


def words_report(prepared: Any, keys: list[str]) -> list[str]:
    """Part 3: the products with no kind whose own words name a kind."""
    from picwise_nlu.concept_understanding import _head_of_text

    by_kind: dict[str, set[str]] = defaultdict(set)
    products_of: Counter[str] = Counter()
    examples: dict[str, list[str]] = defaultdict(list)
    no_kind = named = 0
    for place, kinds in enumerate(prepared.kinds):
        if kinds:
            continue
        no_kind += 1
        fields = prepared.search_fields[place]
        text = " ".join(part for part in (fields.get("title", ""), fields.get("product_type", "")) if part)
        head = _head_of_text(text, strict_tail=True)
        if not head or head.startswith("__"):
            continue
        named += 1
        by_kind[head].add(keys[place])
        products_of[head] += 1
        if len(examples[head]) < 2:
            examples[head].append(_short(prepared.products[place].title, 50))
    lines = [
        f"products with no kind {no_kind:,}; their own words name a kind: {named:,},"
        f" {sum(len(found) for found in by_kind.values()):,} questions in {len(by_kind):,} kinds",
    ]
    for kind, found in sorted(by_kind.items(), key=lambda item: -len(item[1]))[:TOP]:
        lines.append(f"  {kind} {len(found):,} keys ({products_of[kind]:,} products), e.g. " + "; ".join(examples[kind]))
    return lines


def taken_report(prepared: Any, keys: list[str]) -> list[str]:
    """Part 4: what the kinds' lists took out of a kind."""
    from picwise_providers.ai_shelves import line_of
    from picwise_providers.search_selection import kinds_before_the_kind_lists

    by_kind: dict[str, set[str]] = defaultdict(set)
    products_of: Counter[str] = Counter()
    lines_of: dict[str, Counter[str]] = defaultdict(Counter)
    products = left_with_none = 0
    narrow_pairs: set[tuple[str, str]] = set()
    for place, (product, fields, kinds) in enumerate(zip(prepared.products, prepared.search_fields, prepared.kinds)):
        after = real_kinds(kinds)
        before = real_kinds(kinds_before_the_kind_lists(product, fields))
        lost = before - after
        if not lost:
            continue
        products += 1
        left_with_none += not after
        line = str(line_of(str(product.title or ""), str(product.brand or ""), product.raw) or "")
        last = line.split(">")[-1].strip() or "(no line)"
        for kind in lost:
            by_kind[kind].add(keys[place])
            products_of[kind] += 1
            lines_of[kind][last] += 1
        for kind in narrowest(frozenset(lost)):
            narrow_pairs.add((keys[place], kind))
    lines = [
        f"products the lists took out of a kind {products:,} (left with none, so doubtful: {left_with_none:,});"
        f" questions, one a (key, kind): {sum(len(found) for found in by_kind.values()):,} in {len(by_kind):,} kinds;"
        f" for the narrowest kind only: {len(narrow_pairs):,}",
    ]
    for kind, found in sorted(by_kind.items(), key=lambda item: -len(item[1]))[:TOP]:
        lines.append(
            f"  {kind} {len(found):,} keys ({products_of[kind]:,} products): "
            + ", ".join(f"{name} {count:,}" for name, count in lines_of[kind].most_common(3))
        )
    return lines


def searched(query: str, shown: int) -> dict[str, Any]:
    """One search as the site answers it: the kind it is read as, its first cards' ids, its
    Recommended's id, how many products it found, how long it took."""
    from picwise_nlu.concept_understanding import understand_product_query
    from picwise_search import resolve_live_search

    began = time.monotonic()
    kind = str(understand_product_query(query).concept_id or "")
    try:
        resolution = resolve_live_search(query, shown=shown)
    except Exception as error:  # a look only
        return {"q": query, "kind": kind, "cards": [], "total": 0, "recommended": "", "error": type(error).__name__,
                "seconds": time.monotonic() - began}
    products = list(resolution.provider_feed_selected_products) + list(resolution.provider_feed_more_products)
    return {
        "q": query,
        "kind": kind,
        "cards": [str(product.get("provider_product_id") or "") for product in products[:shown]],
        "total": int(resolution.provider_feed_total_count or len(products)),
        "recommended": str(resolution.provider_feed_recommended_product_id or ""),
        "error": "",
        "seconds": time.monotonic() - began,
    }


def front_report(prepared: Any, keys: list[str], index: dict[str, int], shown: int) -> list[str]:
    """Part 5: each kind's first name searched, its first `shown` cards."""
    from picwise_nlu.product_concepts import get_product_concepts

    questions: set[tuple[str, str]] = set()
    ways: Counter[str] = Counter()
    read_as_other = no_card = short = cards = with_recommended = 0
    seconds: list[float] = []
    for concept in get_product_concepts():
        if not concept.english:
            continue
        found = searched(concept.english[0], shown)
        seconds.append(found["seconds"])
        if found["kind"] != concept.concept_id:
            read_as_other += 1
        if not found["cards"]:
            no_card += 1
            continue
        short += len(found["cards"]) < shown
        with_recommended += bool(found["recommended"])
        for product_id in found["cards"]:
            place = index.get(product_id)
            if place is None:
                continue
            cards += 1
            ways[way_of(prepared.kinds[place], found["kind"])] += 1
            questions.add((keys[place], found["kind"] or concept.concept_id))
    return [
        f"{len(seconds)} kinds searched by their first name, the first {shown} cards of each:"
        f" read as another kind {read_as_other}; with no card {no_card}; with fewer than {shown} cards {short};"
        f" with a Recommended {with_recommended}",
        f"cards {cards:,}; questions (key, kind) {len(questions):,}; the way each card came: "
        + ", ".join(f"{name} {count:,}" for name, count in ways.most_common()),
        f"a search took {statistics.median(seconds):.2f} s in the middle, {max(seconds):.2f} s at most,"
        f" {sum(seconds):.0f} s in all" if seconds else "no search",
    ]


def searches_report(prepared: Any, index: dict[str, int]) -> list[str]:
    """Part 6: the measure after's 40 searches, their first 12 cards."""
    from measure_after import SEARCHES
    from picwise_providers.ai_shelves import line_of
    from picwise_providers.catalogue_cap import shop_of

    lines: list[str] = []
    ways: Counter[str] = Counter()
    for query in SEARCHES:
        found = searched(query, CARDS)
        head = f'"{query}" ({found["kind"] or "no kind"}, {found["total"]:,} products)'
        if found["error"]:
            lines.append(head + f": the search failed ({found['error']})")
            continue
        lines.append(head + ":")
        for product_id in found["cards"]:
            place = index.get(product_id)
            if place is None:
                continue
            product = prepared.products[place]
            way = way_of(prepared.kinds[place], found["kind"])
            ways[way] += 1
            line = str(line_of(str(product.title or ""), str(product.brand or ""), product.raw) or "")
            lines.append(
                f"  {'R ' if product_id == found['recommended'] else ''}{product.price_text} | {_short(product.title)}"
                f" | {_short(shop_of(product), 16)} | {way} | {_short(line.split('>')[-1].strip() or '-', 28)}"
            )
    lines.append("the way each card came: " + ", ".join(f"{name} {count:,}" for name, count in ways.most_common()))
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("catalogue", type=Path)
    parser.add_argument("--notes", type=Path, default=None)
    parser.add_argument("--shelves", default="")
    parser.add_argument("--gone", default="")
    parser.add_argument("--offers", default="")
    parser.add_argument("--families", default="")
    parser.add_argument("--front", type=int, default=FRONT)
    parser.add_argument("--no-searches", action="store_true")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass
    import os

    import audit_search

    notes = Notes(args.notes)
    began = time.monotonic()
    if args.shelves and Path(args.shelves).is_file() and Path(args.shelves).stat().st_size:
        os.environ["PICWISE_AI_SHELVES_FILE"] = str(Path(args.shelves).resolve())
    try:
        # The copy read whatever code wrote it and made the site's catalogue for this
        # process, its kinds kept as the server read them.
        prepared = _load(args.catalogue, gone=args.gone, offers=args.offers, families=args.families)
    except Exception as error:  # a look only
        notes.say("look: failed", [f"the catalogue could not be read: {type(error).__name__}: {error}"])
        return 0
    if prepared is None:
        notes.say("look: failed", ["the copy is not a prepared catalogue"])
        return 0
    del audit_search
    from picwise_providers.ai_shelves import key_of

    keys = [key_of(product.title, product.brand, product.raw) for product in prepared.products]
    index = {str(product.provider_product_id): place for place, product in enumerate(prepared.products)}
    notes.say("look: the catalogue", [
        f"prepared at {prepared.prepared_at.isoformat()}: {len(prepared.products):,} products,"
        f" {len(set(keys)):,} question keys; read in {time.monotonic() - began:.0f} s"
    ])
    for title, build in (
        ("look: 1 and 2, the questions of the products with a kind", lambda: _first_two(prepared, keys)),
        ("look: 3, no kind but named by their words", lambda: words_report(prepared, keys)),
        ("look: 4, taken out of a kind by the lists", lambda: taken_report(prepared, keys)),
    ):
        try:
            notes.say(title, build())
        except Exception as error:  # a look only
            notes.say(title, [f"failed: {type(error).__name__}: {error}"])
    if not args.no_searches:
        for title, build in (
            (f"look: 5, the first {args.front} cards of every kind", lambda: front_report(prepared, keys, index, args.front)),
            ("look: 6, the 40 searches", lambda: searches_report(prepared, index)),
        ):
            try:
                notes.say(title, build())
            except Exception as error:  # a look only
                notes.say(title, [f"failed: {type(error).__name__}: {error}"])
    print(f"the look took {time.monotonic() - began:.0f} s")
    return 0


def _first_two(prepared: Any, keys: list[str]) -> list[str]:
    totals, kinds_lines, _by_kind = pairs_report(prepared, keys)
    return totals + kinds_lines


def _load(path: Path, *, gone: str, offers: str, families: str) -> Any:
    """The copy made the site's catalogue for this process, with the kinds the server read
    (not read again with this checkout's rules, as `audit_search.load_catalogue` does)."""
    import os
    from dataclasses import replace

    for name in ("AWIN_FEED_URL", "AWIN_FEED_FILE", "AWIN_FEED_URL_AWIN", "AWIN_FEED_FILE_AWIN",
                 "PICWISE_PURCHASABILITY_CACHE_FILE", "PICWISE_GONE_PHOTOS_FILE", "PICWISE_OFFERS_FILE",
                 "PICWISE_FAMILIES_FILE"):
        os.environ.pop(name, None)
    os.environ["PICWISE_PREPARED_CATALOGUE_FILE"] = str(path.resolve())
    os.environ["PICWISE_PREPARED_MAX_AGE_HOURS"] = "100000"
    for option, name in ((gone, "PICWISE_GONE_PHOTOS_FILE"), (offers, "PICWISE_OFFERS_FILE"),
                         (families, "PICWISE_FAMILIES_FILE")):
        if option and Path(option).is_file() and Path(option).stat().st_size:
            os.environ[name] = str(Path(option).resolve())
    from picwise_providers import state
    from picwise_providers.awin_adapter import feed_file_cache_key
    from picwise_providers.prepared_catalogue import PreparedFileCheck, read_prepared_catalogue_to_measure
    from picwise_providers.search_selection import _product_search_fields, product_kind_key

    prepared = read_prepared_catalogue_to_measure(path)
    if prepared is None:
        return None
    if not prepared.search_fields or "category" not in prepared.search_fields[0]:
        prepared = replace(prepared, search_fields=tuple(_product_search_fields(product) for product in prepared.products))
    state._PREPARED_STATE.clear()
    state._PREPARED_STATE.update(
        file_key=feed_file_cache_key(str(path)),
        prepared=prepared,
        check=PreparedFileCheck("fresh", prepared, prepared.prepared_at),
    )
    state.remember_product_kinds({
        product_kind_key(product, fields): kinds
        for product, fields, kinds in zip(prepared.products, prepared.search_fields, prepared.kinds)
    })
    return prepared


if __name__ == "__main__":
    sys.exit(main())
