"""Print which products of the server's prepared catalogue this checkout reads as another kind.

    ssh picwise 'sudo cat /srv/picwise/shared/prepared/catalogue.json.gz' > catalogue.json.gz
    python3 deployment/server/print_kind_changes.py catalogue.json.gz [--step NAME=KINDS.txt ...]

Owner, 2026-10-27: «Διόρθω τους κανόνες και άντε να δούμε πού θα καταλήξουμε τελικά»,
after the check of far prices (`print_prices.py`) listed products read as the wrong kind.
Each product is read again as the preparation reads it (`annotate_product_concepts` of
its type, its categories and its title) with this checkout's rules, and its narrowest
kind set against the one the server stored: how many are read as another kind, from which
to which, with the shops, the words their titles share most and the cheapest titles of
each change (price first puts the cheapest at the top of a page), and the kinds whose
counts change; the accessories the cap counts in the kind their shelf names; then the
check of far prices again (`print_prices.print_far`), with the kinds read so: where it
ends. Run by .github/workflows/server-cap.yml on GitHub's runner, from a copy of the
server's file; nothing on the server or shown changes until a deployment. Counts, names,
titles and prices only; the file's links are never printed. Always exits 0.

Owner, 2026-10-28: each of the three things to finish is measured before it is built.
The kinds stored count every change of the rules since the last deployment, so each
`--step` names the kinds other rules read (`kinds_of.py`, the commit before a change):
the steps are set against each other and the last against this checkout's, with whole
titles, so that each change is seen on its own. The accessories the cap counts in a kind
also say the word their titles put right after the kind's name, where a title naming it
is read as an accessory still (3,075 of Finediam's engagement rings named the ring only
after a "With", and a word after its name can void it).
"""
from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

CHANGES = 20
SHOPS = 4
EXAMPLES = 5
LISTED = 20
WORDS = 12
# How long a title may be where the words after a kind's name decide.
WHOLE_TITLE = 160
# Words too common in titles to say what a group of products is.
_COMMON = frozenset("and the for with from pack set new black white".split())


def _short(text: str, width: int = 70) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= width else text[: width - 3] + "..."


def _label(kinds, narrowest) -> str:
    """A product's kind as the cap and the price check name it: its narrowest kind, or
    what its markers say."""
    if "__accessory__" in kinds:
        return "(accessory)"
    if "__uncertain_kind__" in kinds:
        return "(doubtful)"
    return narrowest(kinds) or "(no kind)"


def _print_group(products: list, shop_of, parse_price_amount, width: int = 70) -> None:
    """A group's shops, the words its titles share most, and its cheapest titles."""
    shops = Counter(shop_of(product) for product in products)
    print("             shops: " + ", ".join(f"{shop} {count:,}" for shop, count in shops.most_common(SHOPS)))
    words = Counter(
        word
        for product in products
        for word in set(re.findall(r"[a-z]{3,}", str(product.title or "").lower()))
        if word not in _COMMON
    )
    commonest = sorted(words.items(), key=lambda item: (-item[1], item[0]))[:WORDS]
    print("             words: " + ", ".join(f"{word} {count:,}" for word, count in commonest))
    priced = sorted(
        products,
        key=lambda product: (parse_price_amount(product.price_text) is None, parse_price_amount(product.price_text) or 0, str(product.title)),
    )
    for product in priced[:EXAMPLES]:
        price = parse_price_amount(product.price_text)
        shown = f"{price:,.2f} {str(product.currency or '').strip().upper()}" if price is not None else "no price"
        print(f"             {shown:>14} | {shop_of(product)} | {_short(product.title, width)}")


def _changes(labels_from: list[str], labels_to: list[str], products: list) -> dict[tuple[str, str], list]:
    changes: dict[tuple[str, str], list] = defaultdict(list)
    for old, new, product in zip(labels_from, labels_to, products):
        if old != new:
            changes[(old, new)].append(product)
    return changes


def _print_changes(changes: dict[tuple[str, str], list], shop_of, parse_price_amount, width: int = 70) -> None:
    for (old, new), products in sorted(changes.items(), key=lambda item: (-len(item[1]), item[0]))[:CHANGES]:
        print(f"  {len(products):>9,}  {old} -> {new}")
        _print_group(products, shop_of, parse_price_amount, width)


def _word_after_name(title: str, kind: str, concepts_in_text, normalize) -> str:
    """The word a title puts right after the kind's name, "(end)" when the name ends it, or
    "(not named)" when the title names the kind only by a weak name or not at all."""
    tokens = normalize(title).split()
    for span in concepts_in_text(title):
        if span.concept_id == kind:
            return tokens[span.end] if span.end < len(tokens) else "(end)"
    return "(not named)"


def _read_steps(arguments: list[str], total: int) -> list[tuple[str, list[str]]]:
    """The kinds other rules read (`--step NAME=KINDS.txt`, `kinds_of.py`), in order; a
    file that does not hold one kind per product is said and left out."""
    steps = []
    for index, argument in enumerate(arguments):
        if argument != "--step" or index + 1 >= len(arguments) or "=" not in arguments[index + 1]:
            continue
        name, path = arguments[index + 1].split("=", 1)
        try:
            labels = Path(path).read_text(encoding="utf-8").splitlines()
        except OSError:
            print(f"the kinds of the rules of {name} could not be read")
            continue
        if len(labels) != total:
            print(f"the kinds of the rules of {name} are {len(labels):,}, for {total:,} products: left out")
            continue
        steps.append((name, labels))
    return steps


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1].startswith("--"):
        print("usage: print_kind_changes.py CATALOGUE.json.gz [--step NAME=KINDS.txt ...]")
        return 0
    root = Path(__file__).resolve().parents[2]
    for folder in (root, root / "src"):
        if str(folder) not in sys.path:
            sys.path.insert(0, str(folder))
    try:
        from picwise_nlu.concept_understanding import (
            _concepts_in_text,
            annotate_product_concepts,
            normalize_understanding_text,
        )
        from picwise_providers.catalogue_balance import _narrowest_kind
        from picwise_providers.catalogue_cap import shop_of
        from picwise_providers.decision_labels import parse_price_amount
        from picwise_providers.prepared_catalogue import read_prepared_catalogue_to_measure
        from picwise_providers.search_selection import _product_search_fields, product_kind_key
        from print_prices import print_far, rows_of

        prepared = read_prepared_catalogue_to_measure(Path(argv[1]))
        if prepared is None:
            print("no prepared catalogue could be read")
            return 0
        # The fields the preparation read each kind from, when the file holds them.
        fields = prepared.search_fields
        if not fields or "category" not in fields[0]:
            fields = tuple(_product_search_fields(product) for product in prepared.products)
        changes: dict[tuple[str, str], list] = defaultdict(list)
        before: Counter = Counter()
        after: Counter = Counter()
        widened = 0
        kinds_now = []
        labels_now = []
        for product, stored, product_fields in zip(prepared.products, prepared.kinds, fields):
            now = annotate_product_concepts(*product_kind_key(product, product_fields))
            kinds_now.append(now)
            old, new = _label(stored, _narrowest_kind), _label(now, _narrowest_kind)
            labels_now.append(new)
            before[old] += 1
            after[new] += 1
            if old != new:
                changes[(old, new)].append(product)
            elif set(stored) != set(now):
                widened += 1
    except Exception as error:  # a measure only: the run goes on without it
        print(f"the kinds could not be read again: {type(error).__name__}")
        return 0

    total = len(prepared.products)
    changed = sum(len(products) for products in changes.values())
    print(
        f"the prepared catalogue of {prepared.prepared_at.isoformat()}: {total:,} products a card can show;"
        f" read again with this checkout's rules, {changed:,} are read as another kind"
        f" ({100 * changed / max(total, 1):.2f}%); {widened:,} keep their kind and gain or lose a broader one"
    )
    print("from -> to, the most first, with their shops, their titles' commonest words and the cheapest titles (price | shop | title):")
    _print_changes(changes, shop_of, parse_price_amount)
    moved = sorted(
        (name for name in set(before) | set(after) if before[name] != after[name]),
        key=lambda name: (-abs(after[name] - before[name]), name),
    )
    print(f"the kinds whose counts change, the most first: {len(moved):,}")
    for name in moved[:LISTED]:
        print(f"  {before[name]:>9,} -> {after[name]:>9,}  {name}")
    # What each change of the rules does on its own: the kinds other rules read, step by
    # step, the last set against this checkout's.
    steps = _read_steps(argv[2:], total)
    if steps:
        steps.append(("this checkout", labels_now))
        print("the kinds read step by step, each change of the rules on its own (whole titles):")
        for (name_from, labels_from), (name_to, labels_to) in zip(steps, steps[1:]):
            step = _changes(labels_from, labels_to, list(prepared.products))
            moved_in_step = sum(len(products) for products in step.values())
            print(
                f"from the rules of {name_from} to those of {name_to}: {moved_in_step:,} are read as"
                f" another kind ({100 * moved_in_step / max(total, 1):.2f}%)"
            )
            _print_changes(step, shop_of, parse_price_amount, WHOLE_TITLE)
    # The products the cap counts in a kind they are read as no product of: an accessory
    # on a shelf naming a kind joins that kind (`catalogue_cap.joined_parts`), as the
    # owner chose for the rings on a shelf of rings. Listed for the owner's word on how
    # the cap counts them (2026-10-28: 3,075 on Finediam's shelf of rings).
    try:
        from picwise_providers.catalogue_cap import category_of, joined_parts, part_of

        parts = [part_of(product, kinds) for product, kinds in zip(prepared.products, kinds_now)]
        joined = joined_parts([category_of(product) for product in prepared.products], parts)
        counted: dict[str, list] = defaultdict(list)
        for product, kinds, part, joined_part in zip(prepared.products, kinds_now, parts, joined):
            if "__accessory__" in kinds and joined_part != part:
                counted[joined_part].append(product)
        print(
            f"accessories the cap counts in the kind their shelf names: {sum(map(len, counted.values())):,}"
            f" in {len(counted):,} kinds, the most first:"
        )
        for kind, products in sorted(counted.items(), key=lambda item: (-len(item[1]), item[0]))[:CHANGES]:
            print(f"  {len(products):>9,}  {kind}")
            _print_group(products, shop_of, parse_price_amount, WHOLE_TITLE)
            after_name = Counter(
                _word_after_name(product.title, kind, _concepts_in_text, normalize_understanding_text)
                for product in products
            )
            commonest = sorted(after_name.items(), key=lambda item: (-item[1], item[0]))[:WORDS]
            print("             after the kind's name: " + ", ".join(f"{word} {count:,}" for word, count in commonest))
    except Exception as error:  # a measure only
        print(f"the accessories on a kind's shelf could not be counted: {type(error).__name__}")
    print("the check of far prices again, with the kinds this checkout's rules read:")
    try:
        print_far([row for row in rows_of(prepared, kinds_now) if row[0] is not None])
    except Exception as error:  # a measure only
        print(f"the far prices could not be measured again: {type(error).__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
