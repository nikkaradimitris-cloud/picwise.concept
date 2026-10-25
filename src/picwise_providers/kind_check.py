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

The deployment's build writes it into its public note (`tools/prepare_catalogue.py
--static-dir`), next to `intake`: counts, kinds, and a few product titles, shops and
prices, never a link.
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Any, Collection, Sequence

from picwise_nlu.concept_understanding import normalize_understanding_text
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


def _listed(by_kind: dict[str, dict[str, Any]], suspects: str, count_name: str) -> list[dict[str, Any]]:
    """The kinds with the most suspects of this list, each with its cheapest."""
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
        }
        for kind, entry in listed
    ]


def measure_kind_titles(
    products: Sequence[ProviderProduct], kinds: Sequence[Collection[str]]
) -> dict[str, Any]:
    """Per kind: the shown products of that kind, how many of them have a title naming
    none of the kind's nouns, and the cheapest of those; and how many have a title
    naming one of their kinds while neither their product type nor their shelf names
    any, and the cheapest of those.

    `products` and `kinds` are a prepared catalogue's, side by side. Only kinds a search
    can show a product by count: the markers (accessory, doubtful, pet, camping) do not.
    """
    by_kind: dict[str, dict[str, Any]] = {}
    counted = 0
    names_none = 0
    only_title = 0
    for product, product_kinds in zip(products, kinds):
        real = sorted(kind for kind in product_kinds if not kind.startswith("__"))
        if not real:
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
        for kind in real:
            entry = by_kind.setdefault(kind, {"products": 0, "suspects": [], "title_alone": []})
            entry["products"] += 1
            if kind in missing:
                entry["suspects"].append(product)
            if title_alone:
                entry["title_alone"].append(product)
    return {
        "products": counted,
        "title_names_no_kind": names_none,
        "by_kind": _listed(by_kind, "suspects", "title_without_kind"),
        "only_title_names_kind": only_title,
        "by_kind_only_title": _listed(by_kind, "title_alone", "only_title_names_it"),
    }
