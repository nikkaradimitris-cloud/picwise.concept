"""Print which words of the server's prepared catalogue are general, and the choices each would offer.

    ssh picwise 'sudo cat /srv/picwise/shared/prepared/catalogue.json.gz' > catalogue.json.gz
    python3 deployment/server/print_choices.py catalogue.json.gz

Owner, 2026-10-28: «Το search όταν του βάζεις καλώδιο πρέπει να συμπληρώνει προτάσεις τι
καλώδιο ζητάει ... το ίδιο με όλες αυτές τις γενικές λέξεις»; 2026-10-29: one logic for all
of them, never word by word. Each product is read with this checkout's rules
(`annotate_product_concepts` of its type, its categories and its title), and every kind
of at least `kind_choices.MIN_PRODUCTS` products is grouped by the word its titles put
before its noun, by its narrower kinds and by its shops' narrowest shelves
(`picwise_providers.kind_choices`). Prints how many kinds are general by each way, the
general ones with their choices, the largest that are not with their largest groups, and
the words left out as saying how a product is rather than which kind. Run by
.github/workflows/server-cap.yml on GitHub's runner, from a copy of the server's file;
measured before anything is built, nothing on the server or shown changes. Counts, kinds,
words and shelves only, never a title or a link. Always exits 0.
"""
from __future__ import annotations

import sys
from pathlib import Path

GENERAL_LISTED = 80
NOT_GENERAL_LISTED = 25
CHOICES_SHOWN = 8
WORDS_SHOWN = 40


def _share(part: int, whole: int) -> str:
    return f"{100 * part / max(whole, 1):.0f}%"


def _line(pairs, total: int, label=lambda name: name) -> str:
    return ", ".join(f"{label(name)} {count:,} ({_share(count, total)})" for name, count in pairs[:CHOICES_SHOWN]) or "-"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: print_choices.py CATALOGUE.json.gz")
        return 0
    root = Path(__file__).resolve().parents[2]
    for folder in (root, root / "src"):
        if str(folder) not in sys.path:
            sys.path.insert(0, str(folder))
    try:
        from picwise_nlu.concept_understanding import annotate_product_concepts
        from picwise_providers import kind_choices
        from picwise_providers.prepared_catalogue import read_prepared_catalogue_to_measure
        from picwise_providers.search_selection import _product_search_fields, product_kind_key

        prepared = read_prepared_catalogue_to_measure(Path(argv[1]))
        if prepared is None:
            print("no prepared catalogue could be read")
            return 0
        fields = prepared.search_fields
        if not fields or "category" not in fields[0]:
            fields = tuple(_product_search_fields(product) for product in prepared.products)
        kinds = [
            annotate_product_concepts(*product_kind_key(product, product_fields))
            for product, product_fields in zip(prepared.products, fields)
        ]
        measure = kind_choices.measure_kind_choices(prepared.products, kinds)
    except Exception as error:  # a measure only: the run goes on without it
        print(f"the choices could not be measured: {type(error).__name__}")
        return 0

    read = measure.kinds
    by_words = [entry for entry in read if entry.general_by_words]
    by_shelves = [entry for entry in read if entry.general_by_shelves]
    general = [entry for entry in read if entry.general]
    print(
        f"the prepared catalogue of {prepared.prepared_at.isoformat()}: {len(prepared.products):,} products a card"
        f" can show, read with this checkout's rules; kinds of at least {kind_choices.MIN_PRODUCTS} products:"
        f" {len(read):,}; general by the words before their noun: {len(by_words):,}; by their shelves:"
        f" {len(by_shelves):,}; by either: {len(general):,} (a choice holds at least"
        f" {100 * kind_choices.MIN_SHARE:.0f}% of its kind and {kind_choices.MIN_GROUP} products; a general kind has"
        f" {kind_choices.MIN_CHOICES} or more)"
    )
    print("general kinds, the most products first: the choices by the word before the noun, by narrower kind, by shelf:")
    for entry in general[:GENERAL_LISTED]:
        mark = "+".join(name for name, on in (("words", entry.general_by_words), ("shelves", entry.general_by_shelves)) if on)
        print(
            f"  {entry.kind} {entry.products:,} [{mark}]; the title names it as \"{entry.noun}\""
            f" in {entry.named:,} ({_share(entry.named, entry.products)})"
        )
        print(f"      words: {_line(entry.words, entry.products, lambda word, noun=entry.noun: f'{word} {noun}')}")
        if entry.narrower:
            print(f"      narrower: {_line(entry.narrower, entry.products)}")
        print(f"      shelves: {_line(entry.shelves, entry.products)}")
    print("the largest kinds that are not general, with their largest groups:")
    for entry in [entry for entry in read if not entry.general][:NOT_GENERAL_LISTED]:
        print(
            f"  {entry.kind} {entry.products:,}; words: {_line(entry.words[:3], entry.products)};"
            f" shelves: {_line(entry.shelves[:3], entry.products)}"
        )
    words = measure.generic_words
    print(
        f"the words left out as saying how a product is, before the nouns of {kind_choices.GENERIC_KINDS} kinds"
        f" or more: {len(words):,}: " + ", ".join(f"{word} {count}" for word, count in words[:WORDS_SHOWN])
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
