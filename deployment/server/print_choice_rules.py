"""Print what each rule of the choices for a general word changes, on the server's prepared catalogue.

    ssh picwise 'sudo cat /srv/picwise/shared/prepared/catalogue.json.gz' > catalogue.json.gz
    python3 deployment/server/print_choice_rules.py catalogue.json.gz

Owner, 2026-10-29: «εσύ πρέπει να αποφασίσεις ποιος είναι ο βέλτιστος τρόπος», after the
buyer's view of the choices (run 40911685093) showed one shop's own words ("robertson
hoodie", "eng ring"), halves of phrases ("piece suit"), choices keeping the whole kind
("diamond ring") and singulars the search does not read ("bootcut jean"). The file is
read again with this checkout's rules, as `print_search_choices.py` reads it, and the
choices are worked out with every rule of `kind_choices.CHOICE_RULES` and again without
each: for each rule, the choices it leaves out and those it lets in instead, the
largest first; then every general kind's choices with every rule, with how many of the
kind each one's search keeps, and why the largest left out were. Run by
.github/workflows/server-cap.yml on GitHub's runner, from a copy of the server's file;
nothing on the server or shown changes. Counts, kinds and words only, never a link.
Always exits 0.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# How many choices left out or let in each rule's list prints, the largest first; how
# many of the choices left out each kind's line names.
LISTED = 30
LEFT_OUT_NAMED = 4


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: print_choice_rules.py CATALOGUE.json.gz")
        return 0
    root = Path(__file__).resolve().parents[2]
    for folder in (root, root / "src"):
        if str(folder) not in sys.path:
            sys.path.insert(0, str(folder))
    for name in ("AWIN_FEED_URL", "AWIN_FEED_FILE", "PICWISE_PURCHASABILITY_CACHE_FILE"):
        os.environ.pop(name, None)
    try:
        from picwise_nlu.concept_understanding import annotate_product_concepts
        from picwise_providers import kind_choices
        from picwise_providers.prepared_catalogue import read_prepared_catalogue_to_measure
        from picwise_providers.search_selection import _product_search_fields, product_kind_key

        prepared = read_prepared_catalogue_to_measure(Path(argv[1]).resolve())
        if prepared is None:
            print("no prepared catalogue could be read")
            return 0
        started = time.monotonic()
        all_fields = prepared.search_fields
        if not all_fields or "category" not in all_fields[0]:
            all_fields = tuple(_product_search_fields(product) for product in prepared.products)
        # What a search reads: the products a card can show that are new.
        new = [index for index, condition in enumerate(prepared.non_new) if not condition]
        products = [prepared.products[index] for index in new]
        fields = [all_fields[index] for index in new]
        kinds = [
            annotate_product_concepts(*product_kind_key(product, product_fields))
            for product, product_fields in zip(products, fields)
        ]
        groups, _generic_words = kind_choices._kind_groups(products, kinds)
        read_in = time.monotonic() - started
        variants = {"every rule": kind_choices.CHOICE_RULES}
        for rule in sorted(kind_choices.CHOICE_RULES):
            variants[f"without {rule}"] = kind_choices.CHOICE_RULES - {rule}
        considered = {
            name: kind_choices.choice_candidates_of(groups, products, kinds, fields, rules=rules)
            for name, rules in variants.items()
        }
    except Exception as error:  # a measure only: the run goes on without it
        print(f"the choices could not be worked out with this checkout's rules: {type(error).__name__}")
        return 0

    def offered(name: str) -> dict[tuple[str, str], int]:
        """(kind, choice) -> products, for the kinds that ask."""
        rows: dict[tuple[str, str], int] = {}
        for kind, candidates in considered[name].items():
            kept = [row for row in candidates if row.outcome == kind_choices.OFFERED]
            if len(kept) >= kind_choices.MIN_CHOICES:
                rows.update({(kind, row.text): row.products for row in kept})
        return rows

    every = offered("every rule")
    print(
        f"the prepared catalogue of {prepared.prepared_at.isoformat()}: {len(products):,} new products a search"
        f" reads, read again with this checkout's rules in {read_in:.0f} s"
    )
    for name in variants:
        rows = offered(name)
        print(f"{name}: {len({kind for kind, _text in rows}):,} kinds ask which one is meant, {len(rows):,} choices")
    why = {
        (kind, row.text): row
        for kind, candidates in considered["every rule"].items()
        for row in candidates
    }
    for rule in sorted(kind_choices.CHOICE_RULES):
        without = offered(f"without {rule}")
        left_out = sorted(((key, count) for key, count in without.items() if key not in every), key=lambda item: -item[1])
        let_in = sorted(((key, count) for key, count in every.items() if key not in without), key=lambda item: -item[1])
        print(f"the rule {rule!r} leaves out {len(left_out):,} choices and lets in {len(let_in):,}; left out, the largest first:")
        for (kind, text), count in left_out[:LISTED]:
            row = why.get((kind, text))
            reason = _reason(row) if row is not None else "the kind no longer asks"
            print(f"    {kind}: {text} {count:,} ({reason})")
        if let_in:
            print("  let in:")
            for (kind, text), count in let_in[:LISTED]:
                print(f"    {kind}: {text} {count:,}")
    print("every general kind's choices with every rule, the largest kind first (titles naming it so, kept by its search):")
    general = sorted({kind for kind, _text in every}, key=lambda kind: (-groups[kind].products, kind))
    for kind in general:
        candidates = considered["every rule"][kind]
        kept = [row for row in candidates if row.outcome == kind_choices.OFFERED]
        shown = "; ".join(
            f"{row.text} {row.products:,}" + (f"/{row.found:,}" if row.found is not None else "") for row in kept
        )
        print(f"  {kind} {groups[kind].products:,}: {shown}")
        dropped = [
            row for row in candidates if row.outcome not in (kind_choices.OFFERED, kind_choices.BEYOND)
        ]
        if dropped:
            print(
                "      left out: "
                + "; ".join(f"{row.text} {row.products:,} ({_reason(row)})" for row in dropped[:LEFT_OUT_NAMED])
            )
    return 0


def _reason(row) -> str:
    """Why a choice was left out, with its count where it says more."""
    from picwise_providers import kind_choices

    if row.outcome == kind_choices.FEW_SHOPS:
        return f"{row.shops or 0} shop" + ("" if row.shops == 1 else "s")
    if row.outcome == kind_choices.WHOLE_KIND and row.found is not None:
        return f"its search keeps {row.found:,}"
    return row.outcome


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
