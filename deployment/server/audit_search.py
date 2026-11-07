"""The debugging's measure on the server's catalogue: the products put in each kind and the cards searches show, judged by Claude Haiku 5.5.

    python3 deployment/server/audit_search.py searches CATALOGUE.json.gz SEARCHES.json
    python3 deployment/server/audit_search.py cards CATALOGUE.json.gz SEARCHES.json CARDS.json \
        [--src CHECKOUT] [--gone GONE.json] [--offers OFFERS.json]
    python3 deployment/server/audit_search.py judge CATALOGUE.json.gz SEARCHES.json CARDS.json \
        [--before CARDS-BEFORE.json --before-name NAME] [--budget 3.00] [--dry-run]

Owner, 2026-11-07: «ζητάω μία μεγάλη γενική απασφαλμάτωση», the method's steps 2 and 3 and
about $3 for them («Ναι σε όλα»), not every product («Κατάλαβα τη διευκρίνιση δεν χρειάζεται
να τα ελέγξουμε όλα»), the rules built on the same day deployed after it («Ανέβασε μετά τη
μέτρηση..»). Run by .github/workflows/search-audit.yml on GitHub's runner, from a copy of
the server's prepared catalogue; nothing on the server or the site changes.

1. `searches`: the searches measured, written once so that both sets of rules read the same
   ones: each kind's English names (three at most), its catalogue's commonest brand with
   its name, and the searches the offline measure (`print_search_reading.py`) found read as
   another kind; each with the kind it is for.
2. `cards`: each search on the copy as the site answers it with a checkout's code (this
   one, or `--src`: the rules deployed), its first 12 cards.
3. `judge`: Haiku asked, 40 products a call, whether each is what was asked for:
   a. the products of each kind (by this checkout's rules) the reports flag -- the title
      names none of the kind's words, an accessory word in it, a price under a quarter of
      the kind's middle one -- the cheapest first, as price first shows them, 150 a kind
      at most, and 60 others of each kind, to see what the flags miss;
   b. 10,000 products with no kind: which of the kinds each is, or none (the gaps);
   c. every card of every search, for the kind the search was for.
   Printed per category (`print_search_reading.CATEGORY_CODES`): the share of each kind's
   products that are not of it, flagged and not; the gaps; for each set of rules, the
   share of the first 12 cards that are right, the absurd ones (not right, and of no kind
   of the search's category) and the searches with no card; then in short. The calls stop
   at `--budget` dollars. Without `ANTHROPIC_API_KEY`, or with `--dry-run`, nothing is
   asked: the run says what would be.

The repository and its logs are public: titles, brands, prices and shops are printed,
never a link, never the key. Always exits 0.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable, Iterable

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent

MODEL = "claude-haiku-5-5"
BATCH = 40
CARDS = 12
NAMES_A_KIND = 3
FLAGGED_A_KIND = 150
SAMPLE_A_KIND = 60
NO_KIND_SAMPLE = 10_000
WORKERS = 8
TITLE = 90
EXAMPLES = 5
# Words that make a product something used with another, not the thing: a title carrying
# one, of a kind whose names do not, is flagged.
ACCESSORY_WORDS = frozenset(
    """
    case cases cover covers strap straps replacement replacements compatible holder holders
    mount mounts adapter adapters refill refills spare spares part parts sleeve sleeves
    protector protectors film skin skins lid lids attachment attachments accessory
    accessories bracket brackets charger chargers cable cables pouch pouches
    """.split()
)

KIND_PROMPT = """\
You check the catalogue of PicWise, a shopping search. You are given what a buyer asked for \
and numbered products, each with its title, brand, the shop's own category and its price.

For each product, answer whether it IS what the buyer asked for: the thing itself, the one a \
buyer typing those words wants to buy. A part, an accessory, a refill, a case or cover, a \
spare, an attachment, a set of parts, a toy, book or picture of one, or a different product \
used with one is "no". A product that is the thing, of any brand, size or style, is "yes". \
When the title cannot tell, "unsure".

Answer as JSON only: {"answers": [{"n": 1, "answer": "yes"}, ...]}, one per product, "yes", \
"no" or "unsure"."""

GAP_PROMPT_HEAD = """\
You check the catalogue of PicWise, a shopping search. You are given numbered products, \
each with its title, brand and the shop's own category, and the list of kinds of product \
PicWise knows, each as an id and its name.

For each product, answer the id of the one kind it IS (the thing itself, not a part or \
accessory of it), or "none" when it is none of them.

Answer as JSON only: {"answers": [{"n": 1, "kind": "washing_machine"}, ...]}, one per product.

The kinds:
"""

KIND_SCHEMA = {
    "type": "object",
    "properties": {
        "answers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"n": {"type": "integer"}, "answer": {"type": "string", "enum": ["yes", "no", "unsure"]}},
                "required": ["n", "answer"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["answers"],
    "additionalProperties": False,
}
GAP_SCHEMA = {
    "type": "object",
    "properties": {
        "answers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"n": {"type": "integer"}, "kind": {"type": "string"}},
                "required": ["n", "kind"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["answers"],
    "additionalProperties": False,
}


def _use_checkout(src: str | None) -> None:
    """Read PicWise's code from `src` (another checkout: the rules deployed), else this one."""
    root = Path(src).resolve() if src else ROOT
    for folder in (HERE, root, root / "src"):
        if str(folder) in sys.path:
            sys.path.remove(str(folder))
        sys.path.insert(0, str(folder))


def _short(text: object, width: int = TITLE) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= width else text[: width - 3] + "..."


def _hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------------------
# The catalogue, read with a checkout's rules
# --------------------------------------------------------------------------------------


def load_catalogue(path: Path, *, gone: str = "", offers: str = "") -> Any:
    """The copy read with the running checkout's rules and made the search's catalogue, as
    `print_search_choices.py` does: the site then answers from it in this process."""
    for name in ("AWIN_FEED_URL", "AWIN_FEED_FILE", "PICWISE_PURCHASABILITY_CACHE_FILE",
                 "PICWISE_GONE_PHOTOS_FILE", "PICWISE_OFFERS_FILE"):
        os.environ.pop(name, None)
    os.environ["PICWISE_PREPARED_CATALOGUE_FILE"] = str(path)
    os.environ["PICWISE_PREPARED_MAX_AGE_HOURS"] = "100000"
    for option, name in ((gone, "PICWISE_GONE_PHOTOS_FILE"), (offers, "PICWISE_OFFERS_FILE")):
        if option and Path(option).is_file() and Path(option).stat().st_size:
            os.environ[name] = str(Path(option).resolve())
    from picwise_nlu.concept_understanding import annotate_product_concepts
    from picwise_providers import state
    from picwise_providers.awin_adapter import feed_file_cache_key
    from picwise_providers.prepared_catalogue import PreparedFileCheck, read_prepared_catalogue_to_measure
    from picwise_providers.search_selection import _product_search_fields, product_kind_key
    from picwise_providers.suggestions import build_search_suggestions

    prepared = read_prepared_catalogue_to_measure(path)
    if prepared is None:
        return None
    fields = prepared.search_fields
    if not fields or "category" not in fields[0]:
        fields = tuple(_product_search_fields(product) for product in prepared.products)
        prepared = replace(prepared, search_fields=fields)
    kinds = tuple(
        annotate_product_concepts(*product_kind_key(product, product_fields))
        for product, product_fields in zip(prepared.products, fields)
    )
    prepared = replace(prepared, kinds=kinds, choices={})

    def answer_from(catalogue_file: Any) -> None:
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
    return prepared


# --------------------------------------------------------------------------------------
# 1. The searches
# --------------------------------------------------------------------------------------


def build_searches(prepared: Any) -> list[dict[str, str]]:
    """The searches measured, each with the kind it is for and how it was made."""
    import print_search_reading as reading_measure
    from picwise_nlu.product_concepts import get_product_concepts

    brands: dict[str, Counter] = defaultdict(Counter)
    for product, kinds in zip(prepared.products, prepared.kinds):
        brand = " ".join(str(product.brand or "").split())
        if brand:
            for kind in kinds:
                if not kind.startswith("__"):
                    brands[kind][brand] += 1
    searches: list[dict[str, str]] = []
    seen: set[str] = set()

    by_id = {concept.concept_id: concept for concept in get_product_concepts()}

    def add(text: str, kind: str, how: str) -> None:
        key = " ".join(text.lower().split())
        if key and key not in seen:
            seen.add(key)
            concept = by_id.get(kind)
            code = reading_measure.CODE_BY_CATEGORY.get(concept.mega_category_id, "") if concept else ""
            searches.append({"q": text, "kind": kind, "category": code, "how": how})

    for concept in get_product_concepts():
        for name in concept.english[:NAMES_A_KIND]:
            add(name, concept.concept_id, "name")
        top = brands.get(concept.concept_id)
        if top:
            brand = top.most_common(1)[0][0]
            if brand.lower() not in {"generic", "unbranded", "unknown", "n/a"}:
                add(f"{brand} {concept.english[0]}", concept.concept_id, "brand")
    readings = reading_measure.read_searches(reading_measure.kind_searches())
    for read in readings:
        if read.search.kind and read.outcome in (reading_measure.OTHER_CATEGORY, reading_measure.OTHER_KIND):
            add(read.search.text, read.search.kind, f"read as another kind offline ({read.search.how})")
    return searches


# --------------------------------------------------------------------------------------
# 2. The cards
# --------------------------------------------------------------------------------------


def search_cards(searches: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Each search answered as the site answers it, its first `CARDS` cards."""
    from picwise_search.live_search_resolver import resolve_live_search

    answered = []
    for search in searches:
        began = time.monotonic()
        try:
            resolution = resolve_live_search(search["q"], shown=CARDS)
        except Exception as error:  # a measure only
            answered.append({"q": search["q"], "error": type(error).__name__, "cards": []})
            continue
        products = list(resolution.provider_feed_selected_products) + list(resolution.provider_feed_more_products)
        answered.append(
            {
                "q": search["q"],
                "state": str(resolution.resolver_state),
                "total": int(resolution.provider_feed_total_count or len(products)),
                "did_you_mean": list(getattr(resolution, "did_you_mean", ()) or ()),
                "cards": [str(product.get("provider_product_id") or "") for product in products[:CARDS]],
                "seconds": round(time.monotonic() - began, 2),
            }
        )
    return answered


# --------------------------------------------------------------------------------------
# 3. Judging
# --------------------------------------------------------------------------------------


class Asker:
    """The calls to Haiku, `WORKERS` at a time, stopping once they have cost the budget."""

    def __init__(self, client: Any, budget: float, ask: Callable[..., Any]) -> None:
        self.client = client
        self.budget = budget
        self.ask = ask
        self.spent = 0.0
        self.calls = 0
        self.failed = 0
        self.stopped = 0
        self.lock = threading.Lock()

    def __call__(self, request: dict[str, Any]) -> dict[str, Any] | None:
        with self.lock:
            if self.spent >= self.budget:
                self.stopped += 1
                return None
        asked = self.ask(request, client=self.client)
        with self.lock:
            self.calls += 1
            self.spent += float(asked.cost_usd or 0.0)
            if asked.answer is None:
                self.failed += 1
        return asked.answer


def _product_line(number: int, product: Any, fields: dict[str, str]) -> str:
    category = fields.get("product_type") or fields.get("category") or ""
    return (
        f"{number}. {_short(product.title, 140)} | brand: {_short(product.brand, 40) or '-'}"
        f" | category: {_short(category, 90) or '-'} | price: {product.price_text} {product.currency}"
    )


def kind_request(asked_for: str, rows: list[tuple[Any, dict[str, str]]]) -> dict[str, Any]:
    lines = "\n".join(_product_line(i, product, fields) for i, (product, fields) in enumerate(rows, start=1))
    return {
        "model": MODEL,
        "max_tokens": 1500,
        "system": [{"type": "text", "text": KIND_PROMPT, "cache_control": {"type": "ephemeral"}}],
        "messages": [{"role": "user", "content": f"The buyer asked for: {asked_for}\n\nProducts:\n{lines}"}],
        "output_config": {"effort": "low", "format": {"type": "json_schema", "schema": KIND_SCHEMA}},
    }


def gap_request(kind_list: str, rows: list[tuple[Any, dict[str, str]]]) -> dict[str, Any]:
    lines = "\n".join(_product_line(i, product, fields) for i, (product, fields) in enumerate(rows, start=1))
    return {
        "model": MODEL,
        "max_tokens": 1500,
        "system": [{"type": "text", "text": GAP_PROMPT_HEAD + kind_list, "cache_control": {"type": "ephemeral"}}],
        "messages": [{"role": "user", "content": f"Products:\n{lines}"}],
        "output_config": {"effort": "low", "format": {"type": "json_schema", "schema": GAP_SCHEMA}},
    }


def _answers(answer: dict[str, Any] | None, size: int, key: str) -> list[str]:
    """The answers by product number, "" where none was given."""
    found = [""] * size
    for item in (answer or {}).get("answers") or ():
        try:
            number = int(item.get("n"))
        except (TypeError, ValueError, AttributeError):
            continue
        if 1 <= number <= size:
            found[number - 1] = str(item.get(key) or "")
    return found


def _batches(items: list[Any], size: int = BATCH) -> Iterable[list[Any]]:
    for start in range(0, len(items), size):
        yield items[start:start + size]


def flagged_and_sampled(prepared: Any) -> dict[str, dict[str, list[int]]]:
    """Per kind, the products the reports flag (the cheapest first, `FLAGGED_A_KIND` at
    most) and `SAMPLE_A_KIND` others, as indexes into the catalogue."""
    from picwise_nlu.concept_understanding import normalize_understanding_text
    from picwise_nlu.product_concepts import get_product_concepts
    from picwise_providers.decision_labels import parse_price_amount

    words_of = {
        concept.concept_id: {
            word for name in concept.english for word in normalize_understanding_text(name).split()
        }
        for concept in get_product_concepts()
    }
    members: dict[str, list[int]] = defaultdict(list)
    for index, kinds in enumerate(prepared.kinds):
        if "__accessory__" in kinds or "__uncertain_kind__" in kinds:
            continue
        for kind in kinds:
            if kind in words_of:
                members[kind].append(index)
    chosen: dict[str, dict[str, list[int]]] = {}
    for kind, indexes in members.items():
        prices = {i: parse_price_amount(prepared.products[i].price_text) for i in indexes}
        known = sorted(price for price in prices.values() if price)
        middle = known[len(known) // 2] if known else None
        own = words_of[kind]
        flagged, others = [], []
        for i in indexes:
            title_words = set(normalize_understanding_text(prepared.products[i].title).split())
            reasons = (
                not title_words & own
                or bool((title_words & ACCESSORY_WORDS) - own)
                or bool(middle and prices[i] and prices[i] < middle / 4)
            )
            (flagged if reasons else others).append(i)
        flagged.sort(key=lambda i: (prices[i] or 0.0, i))
        others.sort(key=lambda i: _hash(str(prepared.products[i].provider_product_id)))
        chosen[kind] = {"flagged": flagged[:FLAGGED_A_KIND], "sample": others[:SAMPLE_A_KIND],
                        "members": [len(indexes)], "flagged_all": [len(flagged)]}
    return chosen


def judge(
    prepared: Any,
    searches: list[dict[str, str]],
    cards: dict[str, list[dict[str, Any]]],
    *,
    asker: Asker | None,
    out: Callable[[str], None] = print,
) -> dict[str, Any]:
    """Every judgement the measure needs, asked or (without `asker`) counted; the report."""
    import print_search_reading as reading_measure
    from picwise_nlu.product_concepts import _MEGA, get_product_concepts

    by_id = {concept.concept_id: concept for concept in get_product_concepts()}
    index_of = {str(product.provider_product_id): i for i, product in enumerate(prepared.products)}
    fields = prepared.search_fields

    def rows_of(indexes: list[int]) -> list[tuple[Any, dict[str, str]]]:
        return [(prepared.products[i], fields[i]) for i in indexes]

    def asked_for(kind: str, query: str = "") -> str:
        concept = by_id.get(kind)
        name = concept.english[0] if concept and concept.english else kind.replace("_", " ")
        return f'"{query}" (a {name})' if query and query.lower() != name.lower() else f"a {name}"

    # Every (what was asked for, product) pair, once.
    pairs: dict[tuple[str, str], list[int]] = defaultdict(list)
    chosen = flagged_and_sampled(prepared)
    for kind, groups in chosen.items():
        for i in groups["flagged"] + groups["sample"]:
            pairs[(asked_for(kind), kind)].append(i)
    kind_of_search = {search["q"]: search["kind"] for search in searches}
    for answered in cards.values():
        for search in answered:
            kind = kind_of_search.get(search["q"], "")
            for product_id in search.get("cards", []):
                if product_id in index_of and kind:
                    key = (asked_for(kind, search["q"]), kind)
                    if index_of[product_id] not in pairs[key]:
                        pairs[key].append(index_of[product_id])
    no_kind = [
        i for i, kinds in enumerate(prepared.kinds) if not [kind for kind in kinds if not kind.startswith("__")]
    ]
    no_kind.sort(key=lambda i: _hash(str(prepared.products[i].provider_product_id)))
    no_kind = no_kind[:NO_KIND_SAMPLE]

    kind_calls = [(key, batch) for key, indexes in pairs.items() for batch in _batches(indexes)]
    gap_calls = list(_batches(no_kind))
    out(
        f"to ask: {sum(len(batch) for _key, batch in kind_calls):,} (asked for, product) pairs in {len(kind_calls):,}"
        f" calls, {len(no_kind):,} products with no kind in {len(gap_calls):,} calls"
    )
    verdict: dict[tuple[str, int], str] = {}
    gaps: dict[int, str] = {}
    if asker is not None:
        kind_list = "\n".join(f"{concept.concept_id}: {concept.english[0]}" for concept in get_product_concepts())

        def kind_call(item: tuple[tuple[str, str], list[int]]) -> None:
            (what, _kind), batch = item
            answer = asker(kind_request(what, rows_of(batch)))
            for i, said in zip(batch, _answers(answer, len(batch), "answer")):
                if said:
                    verdict[(what, i)] = said

        def gap_call(batch: list[int]) -> None:
            answer = asker(gap_request(kind_list, rows_of(batch)))
            for i, said in zip(batch, _answers(answer, len(batch), "kind")):
                if said:
                    gaps[i] = said

        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            list(pool.map(kind_call, kind_calls))
            list(pool.map(gap_call, gap_calls))

    report = _report(prepared, searches, cards, chosen, pairs, verdict, gaps, no_kind, asked_for, by_id,
                     reading_measure, _MEGA, out)
    if asker is not None:
        out(
            f"the AI: {asker.calls:,} calls, {asker.failed:,} with no answer, {asker.stopped:,} not made"
            f" (the budget reached), ${asker.spent:.4f}"
        )
    return report


def _report(prepared, searches, cards, chosen, pairs, verdict, gaps, no_kind, asked_for, by_id,
            reading_measure, mega, out) -> dict[str, Any]:
    def code_of(kind: str) -> str:
        concept = by_id.get(kind)
        return reading_measure.CODE_BY_CATEGORY.get(concept.mega_category_id, "") if concept else ""

    def describe(i: int) -> str:
        product = prepared.products[i]
        return f"{_short(product.title)} | {product.price_text} {product.currency} | {_short(product.brand, 30)}"

    board: dict[str, dict[str, Any]] = {code: Counter() for code in reading_measure.CATEGORY_CODES}
    out("")
    out("== THE PRODUCTS IN EACH KIND (the kinds by this checkout's rules)")
    misfiled: dict[str, list[int]] = defaultdict(list)
    for kind in sorted(chosen, key=lambda k: (code_of(k), k)):
        groups = chosen[kind]
        what = asked_for(kind)
        row = board[code_of(kind)] if code_of(kind) in board else Counter()
        for group in ("flagged", "sample"):
            for i in groups[group]:
                said = verdict.get((what, i), "")
                row[f"{group} judged"] += int(bool(said))
                row[f"{group} no"] += int(said == "no")
                row[f"{group} unsure"] += int(said == "unsure")
                if said == "no":
                    misfiled[kind].append(i)
        row["members"] += groups["members"][0]
        row["flagged"] += groups["flagged_all"][0]
    for code in reading_measure.CATEGORY_CODES:
        row = board[code]
        out(
            f"{code}: {row['members']:,} products of a kind, {row['flagged']:,} flagged; judged {row['flagged judged']:,}"
            f" flagged, {row['flagged no']:,} not of their kind; judged {row['sample judged']:,} others,"
            f" {row['sample no']:,} not of their kind"
        )
    for kind in sorted(misfiled, key=lambda k: (-len(misfiled[k]), k)):
        sample_no = sum(1 for i in misfiled[kind] if i in set(chosen[kind]["sample"]))
        out(f"  {kind} ({code_of(kind)}): {len(misfiled[kind])} not of it ({sample_no} of the {len(chosen[kind]['sample'])} unflagged)")
        for i in misfiled[kind][:EXAMPLES]:
            out(f"      {describe(i)}")

    out("")
    out("== THE PRODUCTS WITH NO KIND (the gaps)")
    named = Counter(kind for kind in gaps.values() if kind in by_id)
    out(f"judged {len(gaps):,} of {len(no_kind):,} sampled; {sum(named.values()):,} read as one of the kinds, "
        f"{sum(1 for kind in gaps.values() if kind == 'none'):,} as none")
    for kind, count in named.most_common(40):
        examples = [i for i, said in gaps.items() if said == kind][:3]
        out(f"  {kind} ({code_of(kind)}): {count}, e.g. " + "; ".join(_short(prepared.products[i].title, 60) for i in examples))

    out("")
    out("== WHAT THE VISITOR SEES: the first 12 cards of each search, for the kind it is for")
    kind_of_search = {search["q"]: search for search in searches}
    index_of = {str(product.provider_product_id): i for i, product in enumerate(prepared.products)}
    scores: dict[str, dict[str, Counter]] = {}
    absurd_examples: dict[str, list[str]] = defaultdict(list)
    for rules, answered in cards.items():
        per: dict[str, Counter] = defaultdict(Counter)
        for search in answered:
            meta = kind_of_search.get(search["q"])
            if not meta:
                continue
            kind, code = meta["kind"], meta["category"]
            row = per[code]
            row["searches"] += 1
            if not search.get("cards"):
                row["no card"] += 1
                row["did you mean"] += int(bool(search.get("did_you_mean")))
                continue
            what = asked_for(kind, search["q"])
            for product_id in search["cards"]:
                i = index_of.get(product_id)
                if i is None:
                    continue
                said = verdict.get((what, i), "")
                row["cards"] += 1
                row["judged"] += int(bool(said))
                row["right"] += int(said == "yes")
                own = {code_of(k) for k in prepared.kinds[i] if not k.startswith("__")}
                if said == "no" and code not in own:
                    row["absurd"] += 1
                    if len(absurd_examples[rules]) < 40:
                        absurd_examples[rules].append(f'"{search["q"]}" ({kind}): {describe(i)}')
        scores[rules] = per
    for code in reading_measure.CATEGORY_CODES:
        parts = []
        for rules, per in scores.items():
            row = per.get(code, Counter())
            share = f"{100 * row['right'] / row['judged']:.1f}%" if row["judged"] else "-"
            parts.append(
                f"{rules}: {row['searches']} searches, right {share} of {row['judged']:,} cards judged,"
                f" {row['absurd']} absurd, {row['no card']} with no card ({row['did you mean']} asking)"
            )
        out(f"{code} {mega.get(code, '')}: " + " | ".join(parts))
    for rules, examples in absurd_examples.items():
        out(f"  absurd cards with {rules}: {len(examples)} listed")
        for line in examples:
            out(f"      {line}")
    return {"board": board, "scores": scores}


# --------------------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("part", choices=("searches", "cards", "judge"))
    parser.add_argument("catalogue")
    parser.add_argument("searches")
    parser.add_argument("cards", nargs="?", default="")
    parser.add_argument("--src", default="")
    parser.add_argument("--gone", default="")
    parser.add_argument("--offers", default="")
    parser.add_argument("--before", default="")
    parser.add_argument("--before-name", default="the rules deployed")
    parser.add_argument("--budget", type=float, default=3.0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    _use_checkout(args.src or None)
    began = time.monotonic()
    try:
        prepared = load_catalogue(Path(args.catalogue), gone=args.gone, offers=args.offers)
    except Exception as error:  # a measure only
        print(f"the catalogue could not be read with this code: {type(error).__name__}")
        return 0
    if prepared is None:
        print("no prepared catalogue could be read")
        return 0
    print(f"the prepared catalogue of {prepared.prepared_at.isoformat()}: {len(prepared.products):,} products,"
          f" read in {time.monotonic() - began:.0f} s")
    if args.part == "searches":
        searches = build_searches(prepared)
        Path(args.searches).write_text(json.dumps(searches, ensure_ascii=False), encoding="utf-8")
        print(f"{len(searches):,} searches written: " + ", ".join(
            f"{how} {count}" for how, count in Counter(s["how"].split(" (")[0] for s in searches).most_common()))
        return 0
    searches = json.loads(Path(args.searches).read_text(encoding="utf-8"))
    if args.part == "cards":
        began = time.monotonic()
        answered = search_cards(searches)
        Path(args.cards).write_text(json.dumps(answered, ensure_ascii=False), encoding="utf-8")
        seconds = sorted(search.get("seconds", 0.0) for search in answered)
        print(f"{len(answered):,} searches answered in {time.monotonic() - began:.0f} s"
              f" ({seconds[len(seconds) // 2] if seconds else 0:.2f} s in the middle);"
              f" {sum(1 for search in answered if not search.get('cards')):,} with no card")
        return 0
    cards = {"this commit": json.loads(Path(args.cards).read_text(encoding="utf-8"))}
    if args.before and Path(args.before).is_file():
        cards = {args.before_name: json.loads(Path(args.before).read_text(encoding="utf-8")), **cards}
    asker = None
    if not args.dry_run and os.environ.get("ANTHROPIC_API_KEY"):
        from picwise_ai.client import ask, make_client

        asker = Asker(make_client(max_retries=4, timeout=60.0), args.budget, ask)
    else:
        print("the AI: not asked (a dry run, or no key)")
    judge(prepared, searches, cards, asker=asker)
    return 0


if __name__ == "__main__":
    sys.exit(main())
