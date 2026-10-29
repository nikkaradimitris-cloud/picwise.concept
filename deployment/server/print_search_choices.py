"""Print what a buyer would see for each general word, searched on the server's prepared catalogue.

    ssh picwise 'sudo cat /srv/picwise/shared/prepared/catalogue.json.gz' > catalogue.json.gz
    python3 deployment/server/print_search_choices.py catalogue.json.gz

Owner, 2026-10-29: «Ναι προχώρα, βάλ' το στο search», the choices for a general word
("What kind of cable?") measured on the server's catalogue before any deployment. The
file was prepared by the server's deployed code, so it is prepared again here as this
checkout would prepare it: each product's kinds read with this checkout's rules, the
choices of every general kind worked out (`kind_choices.build_kind_choices`) and the
search box's suggestions with them; the search then answers from it in this process,
as the server answers from its file (`state._active_prepared_catalogue`). For every
general kind, the largest first: the search for its English name, how many products
it finds and its first card (the Recommended, at the middle price, when there is one;
else the cheapest), or the vocabulary's "too broad" when that answers instead, and each
choice it asks with how many products that choice's own search finds and whether they
are of the kind; then the Greek name of the first few, and the suggestions the box would
hold. Run by .github/workflows/server-cap.yml
on GitHub's runner, from a copy of the server's file; nothing on the server or shown
changes. Counts, kinds, words, titles and prices only, never a link. Always exits 0.
"""
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import replace
from pathlib import Path

# The general kinds whose every choice is searched too, the largest first; the rest
# show their choices only.
CHOICES_SEARCHED = 30
GREEK_SEARCHED = 5


def _short(text: str, width: int = 60) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= width else text[: width - 3] + "..."


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: print_search_choices.py CATALOGUE.json.gz")
        return 0
    root = Path(__file__).resolve().parents[2]
    for folder in (root, root / "src"):
        if str(folder) not in sys.path:
            sys.path.insert(0, str(folder))
    path = Path(argv[1]).resolve()
    # The copy stands in for the server's file; nothing else is read for the feed.
    for name in ("AWIN_FEED_URL", "AWIN_FEED_FILE", "PICWISE_PURCHASABILITY_CACHE_FILE"):
        os.environ.pop(name, None)
    os.environ["PICWISE_PREPARED_CATALOGUE_FILE"] = str(path)
    os.environ["PICWISE_PREPARED_MAX_AGE_HOURS"] = "100000"
    try:
        from picwise_nlu.concept_understanding import annotate_product_concepts
        from picwise_nlu.product_concepts import broader_concepts, get_product_concepts_by_id
        from picwise_providers import state
        from picwise_providers.awin_adapter import feed_file_cache_key
        from picwise_providers.decision_labels import parse_price_amount
        from picwise_providers.prepared_catalogue import PreparedFileCheck, read_prepared_catalogue_to_measure
        from picwise_providers.search_selection import _product_search_fields, product_kind_key
        from picwise_providers.suggestions import build_search_suggestions
        from picwise_search.live_search_resolver import resolve_live_search

        prepared = read_prepared_catalogue_to_measure(path)
        if prepared is None:
            print("no prepared catalogue could be read")
            return 0
        started = time.monotonic()
        fields = prepared.search_fields
        if not fields or "category" not in fields[0]:
            fields = tuple(_product_search_fields(product) for product in prepared.products)
            prepared = replace(prepared, search_fields=fields)
        kinds = tuple(
            annotate_product_concepts(*product_kind_key(product, product_fields))
            for product, product_fields in zip(prepared.products, fields)
        )
        prepared = replace(prepared, kinds=kinds, choices={})

        def answer_from(catalogue_file) -> None:
            state._PREPARED_STATE.clear()
            state._PREPARED_STATE.update(
                file_key=feed_file_cache_key(str(path)),
                prepared=catalogue_file,
                check=PreparedFileCheck("fresh", catalogue_file, catalogue_file.prepared_at),
            )
            state.remember_product_kinds({})

        answer_from(prepared)
        catalogue = state._prepared_search_catalogue(prepared)
        choices = state._catalogue_kind_choices(catalogue)
        suggestions = build_search_suggestions(catalogue.new_products, choices=choices)
        prepared = replace(prepared, choices=choices, suggestions=suggestions)
        answer_from(prepared)
        prepared_in = time.monotonic() - started
    except Exception as error:  # a measure only: the run goes on without it
        print(f"the catalogue could not be prepared with this checkout's rules: {type(error).__name__}")
        return 0

    by_id = get_product_concepts_by_id()
    general = sorted(choices, key=lambda kind: (-sum(choice.products for choice in choices[kind]), kind))
    print(
        f"the prepared catalogue of {prepared.prepared_at.isoformat()}: {len(prepared.products):,} products a card"
        f" can show, {len(catalogue.new_products):,} of them new; prepared again with this checkout's rules in"
        f" {prepared_in:.0f} s: {len(general):,} general kinds ask which one is meant"
    )
    print("each general kind's search, what it shows, and each choice's own search (products found, of the kind):")
    searched = 0
    seconds = 0.0
    for position, kind in enumerate(general):
        concept = by_id.get(kind)
        name = concept.primary_english if concept is not None else kind
        try:
            began = time.monotonic()
            resolution = resolve_live_search(name)
            seconds += time.monotonic() - began
            searched += 1
        except Exception as error:  # a measure only
            print(f"  {name}: the search failed: {type(error).__name__}")
            continue
        products = resolution.provider_feed_selected_products
        if not products and "broad_query_suggestions" in resolution.reason_codes:
            # The older broad suggestions, from the vocabulary, answer instead of the feed.
            offered = ", ".join(str(row.canonical_term) for row in resolution.suggestions)
            print(f"  {name}: no products; the vocabulary's \"too broad\" answers instead: {offered}")
            continue
        first = products[0] if products else {}
        price = parse_price_amount(str(first.get("price_text") or "")) if first else None
        shown = f"{price:,.2f} {first.get('currency') or ''}".strip() if price is not None else "-"
        print(
            f"  {name}: {resolution.provider_feed_total_count:,} products, the first card {shown}"
            f" {_short(first.get('title') or '')!r}"
        )
        asked = resolution.kind_choices
        if not asked:
            print("      asks nothing")
            continue
        print(f"      What kind of {resolution.kind_choices_name}? " + ", ".join(asked))
        if position >= CHOICES_SEARCHED:
            continue
        found = []
        for text in asked:
            try:
                began = time.monotonic()
                narrowed = resolve_live_search(text)
                seconds += time.monotonic() - began
                searched += 1
            except Exception as error:  # a measure only
                found.append(f"{text}: failed ({type(error).__name__})")
                continue
            understood = narrowed.understood_concept_id or ""
            of_kind = "yes" if understood and kind in broader_concepts(understood) else f"no: {understood or 'none'}"
            found.append(f"{text} {narrowed.provider_feed_total_count:,} ({of_kind})")
        print("      each found: " + "; ".join(found))
    for kind in general[:GREEK_SEARCHED]:
        concept = by_id.get(kind)
        if concept is None or not concept.greek:
            continue
        resolution = resolve_live_search(concept.greek[0])
        print(
            f"  the Greek {concept.greek[0]}: {resolution.provider_feed_total_count:,} products; asks:"
            f" {', '.join(resolution.kind_choices) or 'nothing'}"
        )
    phrases = {choice.text for kind_choices in choices.values() for choice in kind_choices}
    texts = [suggestion.text for suggestion in suggestions]
    size = len(json.dumps({"v": 1, "suggestions": texts}, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    print(
        f"the search box: {len(texts):,} suggestions, {sum(1 for text in texts if text in phrases):,} of them choices,"
        f" {size / 1024:.0f} KB; {searched:,} searches in {seconds:.0f} s"
        f" ({1000 * seconds / max(searched, 1):.0f} ms each on the runner)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
