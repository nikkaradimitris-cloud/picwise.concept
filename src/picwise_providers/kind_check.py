"""Which shown products have a title that does not name their kind: measured, not a rule.

Owner, 2026-10-23: «Ναι, φτιάξ' το», to a list the build writes by itself, so that new
ways of writing titles show up from every shop, every morning, without a file. The wrong
kinds found on the live site so far had titles that never named the kind they were
shown as: "Canon EF 50mm f/1.8 STM Lens" as a camera, "Batteryguard L-10 HE VDMA 24994
Certified | Lithium-Ion Battery Charging Safe" as a phone charger. Price first puts the
cheapest products of a kind first, so for each kind the note lists the cheapest of
these. A product listed is a suspect, not a mistake: "Samsung Galaxy S24" names no phone
and is one, and a wrong product whose title holds the kind's word ("Camera Lens") is not
listed. Nothing shown changes.

Owner, 2026-10-25, with every Google-format shop on the server: the 12 searches showed
the other way round too. "Colleen Hoover 6 Book Collection Set" on a books shelf answers
"vacuum cleaner", "Chocolate Mice" on a sweets shelf answers "mouse", "DEATH BY TV -
Hoody" answers "tv": a shelf naming no kind PicWise knows leaves the title to decide,
and the title names the kind's word for something else. So the note also lists, per
kind, the shown products whose title names the kind while neither their product type
nor their shelf does: suspects again, not mistakes ("Kitchen Appliances" names no
kettle and holds kettles).

Owner, 2026-10-25, «ναι, ξεκίνα με το ρολόι»: the cheapest three showed piercing oil
read as a watch on "Body Jewellery", which named no watch; the whole shelf, as the kind
reader saw it, did ("jewellery & watches > body jewellery"). So each kind listed also
gives the three shelves its suspects most often sit on, whole, with their counts: where
a wrong kind comes from, not only what it looks like.

Owner, 2026-10-25, «προχώρα στο επόμενο λάθος»: a title's kind on an aisle of Google's
that holds no kind of that department is doubtful now (chocolate mice under "Food,
Beverages & Tobacco"), and two real smartwatches left the "smartwatch" page with it. So
the note also lists, per kind, the shown products that rule made doubtful, read as
before it (`kinds_before_the_aisle_rule`): what it took away, right or wrong.

Owner, 2026-10-25, «Ναι», to a measure of how often a title alone finds the right kind:
about 389,000 rows of the server's feed have no category, so only their title could give
them a kind, and nothing tells how far to trust it. `measure_title_alone` reads each
shown product twice, by its type and shelf alone and by its title alone, and counts how
often the two agree, per shop (InStock UK has rows with and without a category), with
the most frequent disagreements and their cheapest products.

The deployment's build writes it into its public note (`tools/prepare_catalogue.py
--static-dir`), next to `intake`: counts, kinds, shelves, and a few product titles,
shops and prices, never a link.
"""
from __future__ import annotations

import heapq
import re
from collections import Counter
from functools import lru_cache
from typing import Any, Collection, Mapping, Sequence

from picwise_nlu.concept_understanding import (
    ACCESSORY_MARKER,
    UNCERTAIN_MARKER,
    annotate_product_concepts,
    kinds_before_the_aisle_rule,
    normalize_understanding_text,
)
from picwise_nlu.product_concepts import broader_concepts, get_product_concepts_by_id

from .contracts import ProviderProduct
from .decision_labels import parse_price_amount
from .normalization import extract_merchant_name

# The kinds with the most such products, how many of each the note shows (the
# cheapest), and how long a title and its shelf may be there.
_KINDS_LISTED = 25
_EXAMPLES = 3
_TITLE_LENGTH = 70
_SHELF_LENGTH = 40
# How many whole shelves of a kind's suspects the note shows, and how long each may be.
_SHELVES = 3
_WHOLE_SHELF_LENGTH = 100
# "headphones/headset", "CPU/Processor": a slash in a title joins two words.
_TITLE_WORD_SPLIT_RE = re.compile(r"[\s/]+")
_SHELF_SPLIT_RE = re.compile(r"\s*(?:>|\|\|)\s*")


def _forms(word: str) -> set[str]:
    forms = {word}
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        forms.add(word[:-1])
    if len(word) > 4 and word.endswith("es"):
        forms.add(word[:-2])
    if len(word) > 4 and word.endswith("ies"):
        forms.add(word[:-3] + "y")
    return forms


@lru_cache(maxsize=1024)
def _kind_nouns(kind: str) -> frozenset[str]:
    """The nouns a title names this kind by: the last word of each English name
    ("digital camera", "dslr"), the first of each Greek one ("φορτιστής κινητού")."""
    concept = get_product_concepts_by_id().get(kind)
    if concept is None:
        return frozenset()
    nouns: set[str] = set()
    for name in (*concept.english, *concept.weak):
        words = normalize_understanding_text(name).split()
        if words:
            nouns |= _forms(words[-1])
    for name in concept.greek:
        words = normalize_understanding_text(name).split()
        if words:
            nouns |= _forms(words[0])
    return frozenset(nouns)


def _title_words(title: str) -> set[str]:
    words: set[str] = set()
    for word in _TITLE_WORD_SPLIT_RE.split(normalize_understanding_text(title)):
        if word:
            words |= _forms(word)
    return words


def _cut(text: str, length: int) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= length else text[: length - 3] + "..."


def _example(product: ProviderProduct) -> str:
    """"price | shop | title | shelf": the shelf is the category's narrowest, which says
    where the product's kind most likely came from."""
    price = " ".join(
        part for part in (str(product.price_text or "").strip(), str(product.currency or "").strip()) if part
    )
    raw = product.raw if isinstance(product.raw, dict) else {}
    shop = " ".join(str(extract_merchant_name(raw) or "?").split())
    shelves = [shelf for shelf in _SHELF_SPLIT_RE.split(str(product.category_text or "")) if shelf.strip()]
    shelf = _cut(shelves[-1], _SHELF_LENGTH) if shelves else "-"
    return f"{price} | {shop} | {_cut(product.title, _TITLE_LENGTH)} | {shelf}"


def _cheapest(products: list[ProviderProduct]) -> list[ProviderProduct]:
    def price(product: ProviderProduct) -> float:
        amount = parse_price_amount(product.price_text)
        return amount if amount is not None else float("inf")

    return sorted(products, key=lambda product: (price(product), str(product.title or "")))[:_EXAMPLES]


def _top_shelves(shelves: Counter) -> list[dict[str, Any]]:
    return [
        {"shelf": _cut(shelf, _WHOLE_SHELF_LENGTH) if shelf else "-", "products": count}
        for shelf, count in heapq.nsmallest(_SHELVES, shelves.items(), key=lambda item: (-item[1], item[0]))
    ]


def _listed(by_kind: dict[str, dict[str, Any]], suspects: str, count_name: str) -> list[dict[str, Any]]:
    """The kinds with the most suspects of this list, each with its cheapest and the
    shelves they most often sit on."""
    listed = sorted(
        ((kind, entry) for kind, entry in by_kind.items() if entry[suspects]),
        key=lambda item: (-len(item[1][suspects]), item[0]),
    )[:_KINDS_LISTED]
    return [
        {
            "kind": kind,
            "products": entry["products"],
            count_name: len(entry[suspects]),
            "cheapest": [_example(product) for product in _cheapest(entry[suspects])],
            "shelves": _top_shelves(entry[f"{suspects}_shelves"]),
        }
        for kind, entry in listed
    ]


def measure_kind_titles(
    products: Sequence[ProviderProduct],
    kinds: Sequence[Collection[str]],
    fields: Sequence[Mapping[str, str]] | None = None,
) -> dict[str, Any]:
    """Per kind: the shown products of that kind, how many of them have a title naming
    none of the kind's nouns, and the cheapest of those; and how many have a title
    naming one of their kinds while neither their product type nor their shelf names
    any, and the cheapest of those; for each, the shelves they most often sit on.

    `products` and `kinds` are a prepared catalogue's, side by side, and `fields` its
    search fields, whose `category` is the whole shelf the kind reader saw; without
    them, a product's own category stands for it, and the products made doubtful by
    their aisle are not measured. Only kinds a search can show a product by count: the
    markers (accessory, doubtful, pet, camping) do not.
    """
    by_kind: dict[str, dict[str, Any]] = {}
    counted = 0
    names_none = 0
    only_title = 0
    doubted = 0

    def entry_of(kind: str) -> dict[str, Any]:
        return by_kind.setdefault(
            kind,
            {"products": 0, "suspects": [], "title_alone": [], "doubted": [],
             "suspects_shelves": Counter(), "title_alone_shelves": Counter(), "doubted_shelves": Counter()},
        )

    for index, (product, product_kinds) in enumerate(zip(products, kinds)):
        real = sorted(kind for kind in product_kinds if not kind.startswith("__"))
        if not real:
            if fields is not None and UNCERTAIN_MARKER in product_kinds:
                raw = product.raw if isinstance(product.raw, dict) else {}
                shelf = str(fields[index].get("category") or "")
                before = kinds_before_the_aisle_rule(str(raw.get("product_type") or ""), shelf, str(product.title or ""))
                before_real = sorted(kind for kind in before if not kind.startswith("__"))
                if before_real:
                    doubted += 1
                for kind in before_real:
                    entry = entry_of(kind)
                    entry["doubted"].append(product)
                    entry["doubted_shelves"][shelf] += 1
            continue
        counted += 1
        words = _title_words(str(product.title or ""))
        # A title naming a narrower kind names the broader ones too: a "Bookcase" is
        # shelving.
        named = {kind for kind in real if words & _kind_nouns(kind)}
        covered = {wider for kind in named for wider in broader_concepts(kind)}
        missing = {kind for kind in real if kind not in covered}
        if not named:
            names_none += 1
        raw = product.raw if isinstance(product.raw, dict) else {}
        shelf_words = _title_words(f"{raw.get('product_type') or ''} {product.category_text or ''}")
        title_alone = bool(named) and not any(shelf_words & _kind_nouns(kind) for kind in real)
        if title_alone:
            only_title += 1
        shelf = (
            str(fields[index].get("category") or "") if fields is not None else str(product.category_text or "")
        )
        for kind in real:
            entry = entry_of(kind)
            entry["products"] += 1
            if kind in missing:
                entry["suspects"].append(product)
                entry["suspects_shelves"][shelf] += 1
            if title_alone:
                entry["title_alone"].append(product)
                entry["title_alone_shelves"][shelf] += 1
    return {
        "products": counted,
        "title_names_no_kind": names_none,
        "by_kind": _listed(by_kind, "suspects", "title_without_kind"),
        "only_title_names_kind": only_title,
        "by_kind_only_title": _listed(by_kind, "title_alone", "only_title_names_it"),
        "doubted_by_aisle": doubted if fields is not None else None,
        "by_kind_doubted_by_aisle": _listed(by_kind, "doubted", "doubted_by_its_aisle"),
    }


# How many shops, and pairs of a shelf's kind and a title's other kind, the note lists.
_SHOPS_LISTED = 20
_PAIRS_LISTED = 25


def _narrowest(kinds: Collection[str]) -> str:
    """The narrowest of a product's kinds: the one with the longest chain of broader ones."""
    return max(sorted(kinds), key=lambda kind: len(broader_concepts(kind)))


def _related(left: Collection[str], right: Collection[str]) -> bool:
    """Do two readings share a kind, or a kind and a broader or narrower one?"""
    return any(a == b or a in broader_concepts(b) or b in broader_concepts(a) for a in left for b in right)


def measure_title_alone(
    products: Sequence[ProviderProduct], fields: Sequence[Mapping[str, str]] | None = None
) -> dict[str, Any]:
    """Of the shown products that their type and shelf alone give a kind, how many their
    title alone gives a kind too, how many of those agree with the shelf (the same kind,
    a broader or a narrower one) and how many do not, and why the rest get none: an
    accessory, doubtful, nothing. In all, per shop (the most products first), and per
    pair of the shelf's kind and the title's other kind, with the cheapest of each.

    The shelf is the whole category the search read (`fields`, else the product's own),
    the title is read with no type and no category, as a row without a category would
    be. Measured only: nothing shown changes.
    """
    totals = {"products": 0, "agrees": 0, "differs": 0, "accessory": 0, "doubtful": 0, "none": 0}
    shops: dict[str, dict[str, int]] = {}
    pairs: dict[tuple[str, str], list[ProviderProduct]] = {}
    for index, product in enumerate(products):
        raw = product.raw if isinstance(product.raw, dict) else {}
        shelf = str(fields[index].get("category") or "") if fields is not None else str(product.category_text or "")
        by_shelf = [
            kind
            for kind in annotate_product_concepts(str(raw.get("product_type") or ""), shelf, "")
            if not kind.startswith("__")
        ]
        if not by_shelf:
            continue
        by_title = annotate_product_concepts("", "", str(product.title or ""))
        real = [kind for kind in by_title if not kind.startswith("__")]
        if real:
            outcome = "agrees" if _related(by_shelf, real) else "differs"
        elif ACCESSORY_MARKER in by_title:
            outcome = "accessory"
        elif UNCERTAIN_MARKER in by_title:
            outcome = "doubtful"
        else:
            outcome = "none"
        shop = shops.setdefault(
            " ".join(str(extract_merchant_name(raw) or "?").split()), {key: 0 for key in totals}
        )
        for bucket in (totals, shop):
            bucket["products"] += 1
            bucket[outcome] += 1
        if outcome == "differs":
            pairs.setdefault((_narrowest(by_shelf), _narrowest(real)), []).append(product)
    listed_pairs = sorted(pairs.items(), key=lambda item: (-len(item[1]), item[0]))[:_PAIRS_LISTED]
    return {
        **totals,
        "by_shop": [
            {"shop": name, **counts}
            for name, counts in sorted(shops.items(), key=lambda item: (-item[1]["products"], item[0]))[
                :_SHOPS_LISTED
            ]
        ],
        "differs_by_pair": [
            {
                "shelf_kind": shelf_kind,
                "title_kind": title_kind,
                "products": len(found),
                "cheapest": [_example(product) for product in _cheapest(found)],
            }
            for (shelf_kind, title_kind), found in listed_pairs
        ],
    }
