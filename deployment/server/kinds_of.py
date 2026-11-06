"""Write the kind each product of the server's prepared catalogue is read as by other rules.

    git worktree add rules-before <commit>
    python3 deployment/server/kinds_of.py rules-before catalogue.json.gz kinds-before.txt
    python3 deployment/server/print_kind_changes.py catalogue.json.gz --step <commit>=kinds-before.txt

Owner, 2026-10-28: each of the three things to finish is measured on a copy of the
server's catalogue and shown before it is built. The kinds the server stored were read by
the rules of its last deployment, so setting them against this checkout's counts every
change made since; this reads them with the rules of another checkout (the commit before
a change), so that print_kind_changes.py can show what that one change does on its own.
Each product is read as the preparation reads it (`annotate_product_concepts` of its
type, its categories and its title) with that checkout's code, and its kind written as
print_kind_changes.py names it -- its narrowest kind, "(accessory)", "(doubtful)" or "(no
kind)" -- one line per product, in the file's order. Run by
.github/workflows/server-cap.yml on GitHub's runner, from a copy of the server's file;
nothing on the server or shown changes. Kinds only, never a title or a link. Always exits
0, and writes nothing when the catalogue cannot be read with those rules.
"""
from __future__ import annotations

import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print("usage: kinds_of.py RULES_CHECKOUT CATALOGUE.json.gz KINDS.txt")
        return 0
    rules = Path(argv[1]).resolve()
    # That checkout's code is read before anything of this one's: only print_kind_changes
    # (beside this file) comes from here, for the names it gives the kinds.
    for folder in (rules, rules / "src"):
        sys.path.insert(0, str(folder))
    try:
        from picwise_nlu.concept_understanding import annotate_product_concepts
        from picwise_providers.catalogue_balance import _narrowest_kind
        from picwise_providers.prepared_catalogue import read_prepared_catalogue_to_measure
        from picwise_providers.search_selection import _product_search_fields, product_kind_key
        from print_kind_changes import _label

        prepared = read_prepared_catalogue_to_measure(Path(argv[2]))
        if prepared is None:
            print("no prepared catalogue could be read with those rules")
            return 0
        fields = prepared.search_fields
        if not fields or "category" not in fields[0]:
            fields = tuple(_product_search_fields(product) for product in prepared.products)
        labels = [
            _label(annotate_product_concepts(*product_kind_key(product, product_fields)), _narrowest_kind)
            for product, product_fields in zip(prepared.products, fields)
        ]
    except Exception as error:  # a measure only: the run goes on without it
        print(f"the kinds could not be read with those rules: {type(error).__name__}")
        return 0
    Path(argv[3]).write_text("".join(f"{label}\n" for label in labels), encoding="utf-8")
    print(f"{len(labels):,} products read with those rules")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
