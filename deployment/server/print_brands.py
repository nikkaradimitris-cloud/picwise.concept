"""The brands of the server's catalogue: their products, kinds, spellings and near names,
measured before the brands' list is built.

    ssh picwise 'sudo cat /srv/picwise/shared/prepared/catalogue.json.gz' > catalogue.json.gz
    python3 deployment/server/print_brands.py catalogue.json.gz [--words /usr/share/dict/words] \
        [--top 120] [--no-searches]

The owner's series of work agreed on 2026-11-19, step 3: a list of brands from the feeds,
their kinds counted; taken up on 2026-11-20: «PicWise: συνέχισε το βήμα 3, τη λίστα
brands, όπως γράφει το handoff». Seen live on 19/11: "dyson" and "samsung" alone show no
product ("PicWise is not sure which product you mean", no choice offered), and "samsnug
tv" could not match "samsnug" and put TV aerial splitters first. The plan
(`docs/picwise_session_handoff.md`, "start here"): (1) measure, on GitHub's runner and
never on the server; (2) put to the owner what it changes, with the numbers; (3) build.
This is (1):

1. the brands as the feeds write them: the products with a brand, with none, with a
   placeholder ("Generic", "Unbranded"), with their shop's own name; how many names, by
   size; those the search counts today (3 products or more,
   `search_selection._catalogue_brand_names`) and the products they cover;
2. the kinds of each brand, each product under its narrowest kind
   (`catalogue_balance._narrowest_kind`), accessories apart: what a search for the brand
   alone could show, its products when they are of one kind, else a question, "What kind
   of Dyson product?", as a general kind's "What kind of cable?" (`kind_choices`);
3. one brand written several ways ("SAMSUNG", "Samsung UK"): one name when case, accents,
   spaces, punctuation, "&" or "and", a leading "The" and an ending such as "Ltd" or "UK"
   are set aside (`brand_key`);
4. brands whose name is also a word: one the search reads alone as a kind, a word of a
   kind's name, an English word (the runner's word list), a word the search reads as
   describing a product; and the names other brands' titles carry ("for Apple iPhone");
5. near-identical names: two brands one slip apart (a letter more, less or other, or two
   swapped); and, for each brand, whether a slip of its name could be read as it alone:
   no other brand, kind's name or word within two slips, or within one;
6. the search today, on the copy as the site answers it (`audit_search.load_catalogue`):
   the owner's examples, then each of the largest brands alone, with its largest kind,
   misspelled alone and misspelled with its kind: what is shown, and how many of the
   first four cards are the brand's and of the kind.

Run by .github/workflows/brands-measure.yml on GitHub's runner from a copy of the server's
file; nothing on the server or shown changes. Counts, brands, kinds, titles and shops only,
never a link. Always exits 0.
"""
from __future__ import annotations

import argparse
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
for _folder in (HERE, ROOT, ROOT / "src"):
    if str(_folder) not in sys.path:
        sys.path.insert(0, str(_folder))

# A brand the search counts today from this many products (`_catalogue_brand_names`).
COUNTED = 3
# A kind a search for a brand alone could offer, from this many of the brand's products.
CHOICE = 3
# A question names at most this many kinds, as a general kind's offers a few.
ASKED = 8
# Lines printed of each list.
LISTED = 40
# Brands searched, the largest first.
TOP = 120
# The cards read of each search: the first page.
CARDS = 4
TITLE = 70
# The searches always measured, each with the brand and the kind it asks for: the owner's
# examples of 2026-11-19.
EXAMPLES = (
    ("dyson", "dyson", ""),
    ("samsung", "samsung", ""),
    ("samsnug", "samsung", ""),
    ("samsung tv", "samsung", "television"),
    ("samsnug tv", "samsung", "television"),
)

# The names as the brands' list reads them (`picwise_providers.brand_list`, from
# 2026-11-20): one module for the list, the site and this measure.
from picwise_providers.brand_list import (  # noqa: E402
    NearIndex,
    _deletions,
    brand_key,
    is_placeholder,
    mend_letters,
    plain,
    slips,
    spoken,
)


def a_slip_of(word: str, taken: Callable[[str], bool]) -> str:
    """The name with two letters side by side swapped, as "samsung" is typed "samsnug":
    near its end first, then near its start; never a name or word that exists ("" when
    every swap makes one, or the name is under 5 letters)."""
    if len(word) < 5 or not word.isalpha():
        return ""
    for i in (len(word) - 3, len(word) - 4, 1, 2):
        if 0 < i < len(word) - 1 and word[i] != word[i + 1]:
            slip = word[:i] + word[i + 1] + word[i] + word[i + 2 :]
            if not taken(slip):
                return slip
    return ""


# --------------------------------------------------------------------------------------
# The catalogue's brands
# --------------------------------------------------------------------------------------


class Brand:
    """One brand of the catalogue, however its products write it."""

    __slots__ = ("key", "forms", "products", "shops", "own", "kinds", "accessories", "no_kind")

    def __init__(self, key: str) -> None:
        self.key = key
        self.forms: Counter = Counter()
        self.products = 0
        self.shops: Counter = Counter()
        # Of its products, those whose shop's own name it is.
        self.own = 0
        self.kinds: Counter = Counter()
        self.accessories: Counter = Counter()
        self.no_kind = 0

    @property
    def name(self) -> str:
        return self.forms.most_common(1)[0][0] if self.forms else self.key

    @property
    def placeholder(self) -> bool:
        return is_placeholder(self.key)

    @property
    def shops_own(self) -> bool:
        """Its name is its shop's own for most of its products: an own label, or a shop
        writing its name where a brand goes."""
        return self.own * 2 > self.products

    @property
    def real(self) -> bool:
        return not self.placeholder and not self.shops_own

    def choices(self) -> list[tuple[str, int]]:
        """The kinds a search for it alone could offer, the largest first."""
        return [(kind, count) for kind, count in self.kinds.most_common() if count >= CHOICE]


ONE_KIND = "one kind (or one of 3 products or more)"
SOME_KINDS = f"2-{ASKED} kinds"
MANY_KINDS = f"more than {ASKED} kinds"
NO_KIND = "no kind read"


def brand_shape(brand: Brand) -> str:
    """What a search for the brand alone could show: its products, when they are of one
    kind (or of one kind of `CHOICE` products or more and a few others) or of no kind
    read; else a question naming its kinds."""
    choices = len(brand.choices())
    if not brand.kinds:
        return NO_KIND
    if choices <= 1:
        return ONE_KIND
    return SOME_KINDS if choices <= ASKED else MANY_KINDS


def kind_names() -> frozenset[str]:
    """The kinds' English names of one word, as a buyer types them."""
    from picwise_nlu.product_concepts import get_product_concepts

    return frozenset(
        name
        for concept in get_product_concepts()
        for name in (plain(form) for form in concept.english)
        if name and " " not in name
    )


def read_brands(products: Iterable[Any], kinds: Iterable[frozenset[str]]) -> dict[str, Brand]:
    from picwise_nlu.concept_understanding import ACCESSORY_MARKER
    from picwise_providers.catalogue_balance import _narrowest_kind
    from picwise_providers.normalization import extract_merchant_name
    from picwise_surface.shop_names import shop_display_name

    brands: dict[str, Brand] = {}
    shop_keys: dict[str, tuple[str, str]] = {}
    for product, product_kinds in zip(products, kinds):
        written = mend_letters(" ".join(str(product.brand or "").split()))
        key = brand_key(written)
        brand = brands.get(key)
        if brand is None:
            brand = brands[key] = Brand(key)
        brand.forms[written] += 1
        brand.products += 1
        raw = product.raw if isinstance(product.raw, Mapping) else {}
        merchant = " ".join(str(extract_merchant_name(raw) or "").split())
        shop = shop_keys.get(merchant)
        if shop is None:
            shown = shop_display_name(merchant)
            shop = shop_keys[merchant] = (shown, brand_key(shown))
        brand.shops[shop[0]] += 1
        if key and shop[1] == key:
            brand.own += 1
        kind = _narrowest_kind(product_kinds)
        if ACCESSORY_MARKER in product_kinds:
            brand.accessories[kind or "no kind"] += 1
        elif kind:
            brand.kinds[kind] += 1
        else:
            brand.no_kind += 1
    return brands


def _number(value: int) -> str:
    return f"{value:,}"


def _share(part: int, whole: int) -> str:
    return f"{100.0 * part / whole:.1f}%" if whole else "0%"


def _counted(counter: Counter | list[tuple[str, int]], most: int) -> str:
    items = counter.most_common() if isinstance(counter, Counter) else counter
    shown = [f"{name} {_number(count)}" for name, count in items[:most]]
    if len(items) > most:
        shown.append(f"+{len(items) - most} more")
    return ", ".join(shown) if shown else "none"


def _kinds_line(brand: Brand, most: int = ASKED) -> str:
    line = f"kinds: {_counted(brand.kinds, most)}"
    if brand.accessories:
        line += f"; accessories {_number(sum(brand.accessories.values()))}"
    if brand.no_kind:
        line += f"; no kind {_number(brand.no_kind)}"
    return line


def _short(text: object, width: int = TITLE) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= width else text[: width - 3] + "..."


# --------------------------------------------------------------------------------------
# 1 to 5: the brands
# --------------------------------------------------------------------------------------


def print_brands(
    prepared: Any, brands: dict[str, Brand], words: frozenset[str], out: Callable[[str], None] = print
) -> None:
    total = len(prepared.products)
    real = sorted(
        (brand for brand in brands.values() if brand.real and brand.products >= COUNTED),
        key=lambda brand: (-brand.products, brand.key),
    )
    _print_the_brands(prepared, brands, real, total, out)
    _print_the_kinds(brands, real, out)
    _print_the_spellings(brands, out)
    _print_the_words(prepared, brands, real, words, out)
    _print_the_near_names(brands, real, words, out)


def _print_the_brands(prepared: Any, brands: dict[str, Brand], real: list[Brand], total: int, out) -> None:
    out("== 1. THE BRANDS AS THE FEEDS WRITE THEM")
    empty = brands.get("")
    none = empty.products if empty else 0
    placeholders = [brand for brand in brands.values() if brand.key and brand.placeholder]
    in_placeholders = sum(brand.products for brand in placeholders)
    out(
        f"products: {_number(total)}; with a brand {_number(total - none - in_placeholders)} "
        f"({_share(total - none - in_placeholders, total)}); none written {_number(none)}; "
        f"a placeholder {_number(in_placeholders)}"
    )
    if placeholders:
        forms: Counter = Counter()
        for brand in placeholders:
            forms.update(brand.forms)
        out(f"  the placeholders: {_counted(forms, 12)}")
    own = sorted(
        (brand for brand in brands.values() if brand.key and not brand.placeholder and brand.shops_own),
        key=lambda brand: (-brand.products, brand.key),
    )
    out(
        f"a shop's own name where the brand goes: {_number(len(own))} names, "
        f"{_number(sum(brand.products for brand in own))} products"
    )
    for brand in own[:12]:
        out(f"  {brand.name}: {_number(brand.products)} ({_counted(brand.shops, 2)})")
    named = [brand for brand in brands.values() if brand.key and not brand.placeholder]
    written = {form.lower() for brand in named for form in brand.forms}
    out(
        f"brand names: {_number(len(written))} as written (case aside); {_number(len(named))} when "
        "accents, spaces, punctuation, \"&\"/\"and\", a leading \"The\" and an ending such as "
        "\"Ltd\" or \"UK\" are set aside"
    )
    sizes = Counter()
    for brand in named:
        size = brand.products
        sizes[
            "1" if size == 1 else "2" if size == 2 else "3-9" if size < 10 else "10-99" if size < 100
            else "100-999" if size < 1000 else "1,000+"
        ] += 1
    out(
        "  by their products: "
        + ", ".join(f"{label}: {_number(sizes[label])}" for label in ("1", "2", "3-9", "10-99", "100-999", "1,000+"))
    )
    # As the search counts them today: each brand field as written, lowercased.
    fields = prepared.search_fields or ()
    counted = Counter(" ".join(str(row.get("brand") or "").split()) for row in fields)
    kept = {name: count for name, count in counted.items() if name and count >= COUNTED}
    out(
        f"the search counts a brand today from {COUNTED} products, as written: {_number(len(kept))} names, "
        f"{_number(sum(kept.values()))} products ({_share(sum(kept.values()), total)})"
    )
    out(f"real brands of {COUNTED} products or more (no placeholder, no shop's own name): {_number(len(real))}, "
        f"{_number(sum(brand.products for brand in real))} products")
    out(f"the {LISTED} largest: products | shops | kinds | the largest kinds")
    for brand in real[:LISTED]:
        out(
            f"  {brand.name}: {_number(brand.products)} | {len(brand.shops)} shops | {len(brand.kinds)} kinds | "
            f"{_counted(brand.kinds, 3)}"
        )
    out("")


def _print_the_kinds(brands: dict[str, Brand], real: list[Brand], out) -> None:
    out(f"== 2. THE KINDS OF EACH BRAND (the real brands of {COUNTED} products or more)")
    shapes: Counter = Counter()
    products: Counter = Counter()
    for brand in real:
        shape = brand_shape(brand)
        shapes[shape] += 1
        products[shape] += brand.products
    out(f"what a search for the brand alone could show, a kind counted from {CHOICE} of its products:")
    for shape, meaning in (
        (ONE_KIND, "its products, cheapest first, with a Recommended"),
        (SOME_KINDS, "a question, \"What kind of Dyson product?\", each kind a choice"),
        (MANY_KINDS, f"a question naming its {ASKED} largest kinds"),
        (NO_KIND, "its products, no kind to ask by"),
    ):
        out(f"  {shape}: {_number(shapes[shape])} brands, {_number(products[shape])} products ({meaning})")
    out("the owner's examples:")
    for name in ("dyson", "samsung"):
        brand = brands.get(brand_key(name))
        if brand is None:
            out(f"  {name}: no product of the catalogue carries it")
            continue
        out(
            f"  {brand.name}: {_number(brand.products)} products, {len(brand.shops)} shops "
            f"({_counted(brand.shops, 5)}); written {_counted(brand.forms, 5)}"
        )
        out(f"    {_kinds_line(brand, 30)}")
        if brand.accessories:
            out(f"    the accessories by kind: {_counted(brand.accessories, 10)}")
        out(f"    a question would offer: {_counted(brand.choices(), ASKED)}")
    several = [brand for brand in real if len(brand.choices()) >= 2]
    out(f"the {LISTED} largest brands of several kinds:")
    for brand in several[:LISTED]:
        out(f"  {brand.name} ({_number(brand.products)}): {_kinds_line(brand)}")
    out("")


def _print_the_spellings(brands: dict[str, Brand], out) -> None:
    out("== 3. ONE BRAND, SEVERAL SPELLINGS")
    case_only = 0
    spelled: list[Brand] = []
    for brand in brands.values():
        if not brand.key or brand.placeholder or len(brand.forms) < 2:
            continue
        if len({form.lower() for form in brand.forms}) == 1:
            case_only += 1
        else:
            spelled.append(brand)
    out(f"written in other case only: {_number(case_only)} brands (the search reads every brand lowercased)")
    spelled.sort(key=lambda brand: (-brand.products, brand.key))
    out(
        f"written otherwise: {_number(len(spelled))} brands, {_number(sum(brand.products for brand in spelled))} "
        f"products; the {LISTED} largest:"
    )
    for brand in spelled[:LISTED]:
        out(f"  {brand.name} ({_number(brand.products)}): {_counted(brand.forms, 6)}")
    out("")


def _title_names(prepared: Any, names: set[str], longest: int) -> tuple[Counter, Counter]:
    """For each brand's name as a buyer types it, the titles that carry it: of the
    brand's own products and of other brands' (`spoken`, word for word)."""
    own: Counter = Counter()
    others: Counter = Counter()
    for product in prepared.products:
        words = plain(product.title).split()
        brand = spoken(product.brand)
        seen: set[str] = set()
        for size in range(1, longest + 1):
            for start in range(len(words) - size + 1):
                phrase = " ".join(words[start : start + size])
                if phrase in names and phrase not in seen:
                    seen.add(phrase)
                    (own if phrase == brand else others)[phrase] += 1
    return own, others


def _print_the_words(prepared: Any, brands: dict[str, Brand], real: list[Brand], words: frozenset[str], out) -> None:
    from picwise_nlu.concept_understanding import kinds_named_by_word, understand_product_query
    from picwise_providers.search_selection import _DESCRIBING_WORDS

    out("== 4. BRANDS WHOSE NAME IS ALSO A WORD")
    typed = {brand.key: spoken(brand.name) for brand in real}
    read_as_kind = []
    kind_word = []
    english = []
    describing = []
    for brand in real:
        name = typed[brand.key]
        if not name:
            continue
        concept = understand_product_query(name).concept_id
        if concept:
            read_as_kind.append((brand, concept))
        elif " " not in name and kinds_named_by_word(name):
            kind_word.append((brand, ", ".join(sorted(kinds_named_by_word(name))[:3])))
        if " " not in name and name in words:
            english.append(brand)
        if " " not in name and name in _DESCRIBING_WORDS:
            describing.append(brand)
    names = set(typed.values())
    longest = max((len(name.split()) for name in names), default=1)
    own, others = _title_names(prepared, names, min(longest, 3))
    out(f"a. read alone by the search as a kind: {_number(len(read_as_kind))} brands; the {LISTED} largest:")
    for brand, concept in read_as_kind[:LISTED]:
        out(f"  {brand.name} ({_number(brand.products)}): read as {concept}; {_kinds_line(brand, 3)}")
    out(f"b. a word of a kind's name, not read alone as one: {_number(len(kind_word))} brands; the {LISTED} largest:")
    for brand, concepts in kind_word[:LISTED]:
        out(f"  {brand.name} ({_number(brand.products)}): a word of {concepts}; {_kinds_line(brand, 3)}")
    if words:
        out(
            f"c. an English word (the word list, {_number(len(words))} words): {_number(len(english))} brands; "
            f"the {LISTED} largest, with the titles of other brands carrying the word:"
        )
        for brand in english[:LISTED]:
            name = typed[brand.key]
            out(
                f"  {brand.name} ({_number(brand.products)}): other brands' titles {_number(others[name])}; "
                f"{_kinds_line(brand, 3)}"
            )
    else:
        out("c. an English word: no word list on this machine, not measured")
    out(f"d. a word the search reads as describing a product: {_number(len(describing))} brands: "
        + (", ".join(f"{brand.name} ({_number(brand.products)})" for brand in describing[:LISTED]) or "none"))
    carried = sorted(
        ((brand, others[typed[brand.key]]) for brand in real if others[typed[brand.key]]),
        key=lambda item: (-item[1], item[0].key),
    )
    out(
        f"e. names other brands' titles carry (\"for Apple iPhone\"): {_number(len(carried))} brands; "
        f"the {LISTED} most carried:"
    )
    for brand, count in carried[:LISTED]:
        out(
            f"  {brand.name}: in {_number(count)} titles of other brands, {_number(own[typed[brand.key]])} of its own "
            f"{_number(brand.products)}"
        )
    out("")


def _print_the_near_names(brands: dict[str, Brand], real: list[Brand], words: frozenset[str], out) -> None:
    out("== 5. NEAR-IDENTICAL NAMES")
    named = {brand.key: brand for brand in brands.values() if len(brand.key) >= 4 and not brand.placeholder}
    index = NearIndex(named, 1)
    pairs = []
    for key, brand in named.items():
        for other in index.near(key, 1):
            if key < other:
                # The larger first.
                pair = tuple(sorted((brand, named[other]), key=lambda each: (-each.products, each.key)))
                if pair[0].products >= COUNTED:
                    pairs.append(pair)
    pairs.sort(key=lambda pair: (-pair[1].products, -pair[0].products, pair[0].key))
    out(
        f"two brands one slip apart (names of 4 letters or more, one of {COUNTED} products or more): "
        f"{_number(len(pairs))} pairs; the {LISTED} whose smaller is largest:"
    )
    for first, second in pairs[:LISTED]:
        out(
            f"  {first.name} ({_number(first.products)}; {_counted(first.kinds, 2)})  ~  "
            f"{second.name} ({_number(second.products)}; {_counted(second.kinds, 2)})"
        )
    targets: dict[str, set[str]] = defaultdict(set)
    for brand in real:
        targets[brand.key].add("brand")
    for name in kind_names():
        targets[name].add("kind")
    for word in words:
        targets[word].add("word")
    near = NearIndex(targets, 2)
    safe = 0
    two: list[tuple[Brand, dict[str, int]]] = []
    one: list[tuple[Brand, dict[str, int]]] = []
    short = 0
    for brand in real:
        if len(brand.key) < 5 or not brand.key.isalpha():
            short += 1
            continue
        found = near.near(brand.key, 2)
        if not found:
            safe += 1
        elif min(found.values()) == 1:
            one.append((brand, found))
        else:
            two.append((brand, found))
    checked = safe + len(one) + len(two)
    out(
        f"a slip of a real brand's name ({COUNTED} products or more, 5 letters or more, letters only: "
        f"{_number(checked)} brands) read as it alone:"
    )
    out(f"  nothing else within two slips (any slip reads as it alone): {_number(safe)}")
    out(f"  a brand, kind's name or word two slips away (some slips doubtful): {_number(len(two))}")
    out(f"  one slip away (a slip may be the other): {_number(len(one))}")
    out(f"  names under 5 letters or not of letters only (a slip never read as them): {_number(short)}")

    def described(found: dict[str, int]) -> str:
        nearest = sorted(found.items(), key=lambda item: (item[1], item[0]))[:4]
        return ", ".join(f"{name} ({'/'.join(sorted(targets[name]))}, {distance})" for name, distance in nearest)

    out(f"  one slip away, the {LISTED} largest:")
    for brand, found in one[:LISTED]:
        out(f"    {brand.name} ({_number(brand.products)}): {described(found)}")
    out(f"  two slips away, the {LISTED // 2} largest:")
    for brand, found in two[: LISTED // 2]:
        out(f"    {brand.name} ({_number(brand.products)}): {described(found)}")
    out("")


# --------------------------------------------------------------------------------------
# 6. The search today
# --------------------------------------------------------------------------------------


def answer(query: str, kinds_of: Mapping[str, frozenset[str]]) -> dict[str, Any]:
    """`query` answered as the site answers it from the copy: how, and its first cards'
    brands and kinds."""
    from picwise_search.live_search_resolver import resolve_live_search

    began = time.monotonic()
    try:
        resolution = resolve_live_search(query, shown=0)
    except Exception as error:  # a measure only
        return {"q": query, "how": f"error {type(error).__name__}", "cards": [], "seconds": 0.0}
    cards = list(resolution.provider_feed_selected_products)[:CARDS]
    families = list(resolution.provider_feed_ambiguous_product_families or ())
    if cards:
        how = "shown"
    elif families:
        how = "not sure"
    elif resolution.did_you_mean:
        how = "did you mean"
    else:
        how = "nothing"
    return {
        "q": query,
        "how": how,
        "total": int(resolution.provider_feed_total_count or len(cards)),
        "families": families,
        "did_you_mean": list(resolution.did_you_mean or ()),
        "unmatched": list(resolution.provider_feed_unmatched_query_terms or ()),
        "choices": list(resolution.kind_choices or ()),
        "asks": str(resolution.kind_choices_name or ""),
        "understood_brand": str(getattr(resolution, "understood_brand_name", "") or ""),
        "decision": str(resolution.provider_feed_decision_status or ""),
        "cards": [
            {
                "brand": brand_key(card.get("brand") or ""),
                "title": str(card.get("title") or ""),
                "kinds": kinds_of.get(str(card.get("provider_product_id") or ""), frozenset()),
            }
            for card in cards
        ],
        "seconds": round(time.monotonic() - began, 2),
    }


def _of_kind(kinds: frozenset[str], kind: str) -> bool:
    from picwise_nlu.concept_understanding import ACCESSORY_MARKER
    from picwise_nlu.product_concepts import broader_concepts

    if not kind or ACCESSORY_MARKER in kinds:
        return False
    return any(kind in broader_concepts(own) for own in kinds if not own.startswith("__"))


def describe(answered: dict[str, Any], brand: str = "", kind: str = "") -> str:
    how = answered["how"]
    if how == "shown":
        line = f"{len(answered['cards'])} of {_number(answered['total'])} shown"
        parts = []
        if brand:
            parts.append(f"{sum(card['brand'] == brand for card in answered['cards'])} the brand's")
        if kind:
            parts.append(f"{sum(_of_kind(card['kinds'], kind) for card in answered['cards'])} {kind}")
        if parts:
            line += f"; of the first {len(answered['cards'])}: " + ", ".join(parts)
        line += f"; first: {_short(answered['cards'][0]['title'], 60)}"
    elif how == "not sure":
        line = "not sure: " + " and ".join(answered["families"][:3])
    elif how == "did you mean":
        line = "did you mean: " + ", ".join(answered["did_you_mean"][:3])
    else:
        line = how
    if answered.get("unmatched"):
        line += " | could not match: " + ", ".join(answered["unmatched"])
    if answered.get("understood_brand"):
        line += f" | understood as: {answered['understood_brand']}"
    if answered.get("choices"):
        asks = f"What kind of {answered['asks']}? " if answered.get("asks") else ""
        line += f" | asks {asks}{', '.join(answered['choices'][:4])}"
        if len(answered["choices"]) > 4:
            line += f" +{len(answered['choices']) - 4} more"
    if how == "shown" and answered.get("decision") and answered["decision"] != "recommended":
        line += f" | {answered['decision'].replace('_', ' ')}"
    return f"{line} | {answered['seconds']:.2f} s"


def print_searches(
    prepared: Any,
    brands: dict[str, Brand],
    words: frozenset[str],
    top: int,
    out: Callable[[str], None] = print,
    examples: Iterable[tuple[str, str, str]] = EXAMPLES,
) -> list[dict[str, Any]]:
    from picwise_nlu.product_concepts import get_product_concepts_by_id

    out("== 6. THE SEARCH TODAY (the copy, as the site answers it)")
    kinds_of = {str(product.provider_product_id or ""): kinds for product, kinds in zip(prepared.products, prepared.kinds)}
    answered: list[dict[str, Any]] = []
    out("the owner's examples:")
    for query, named, kind in examples:
        result = answer(query, kinds_of)
        answered.append(result)
        out(f'  "{query}": {describe(result, brand_key(named) if brand_key(named) in brands else "", kind)}')
    by_id = get_product_concepts_by_id()
    taken_names = {brand.key for brand in brands.values()} | kind_names()

    def taken(word: str) -> bool:
        return word in taken_names or word in words

    real = sorted(
        (
            brand for brand in brands.values()
            if brand.real and brand.products >= COUNTED and len(brand.key) >= 2 and spoken(brand.name)
        ),
        key=lambda brand: (-brand.products, brand.key),
    )[:top]
    ways = ("alone", "with its kind", "a slip, alone", "a slip, with its kind")
    tallies: dict[str, Counter] = {way: Counter() for way in ways}
    lines: dict[str, list[str]] = {way: [] for way in ways}
    for brand in real:
        name = spoken(brand.name)
        kind = brand.kinds.most_common(1)[0][0] if brand.kinds else ""
        kind_name = by_id[kind].english[0] if kind in by_id and by_id[kind].english else ""
        longest = max(name.split(), key=len)
        slip = a_slip_of(longest, taken)
        slipped = name.replace(longest, slip, 1) if slip else ""
        for way, query, with_kind in (
            ("alone", name, False),
            ("with its kind", f"{name} {kind_name}" if kind_name else "", True),
            ("a slip, alone", slipped, False),
            ("a slip, with its kind", f"{slipped} {kind_name}" if slipped and kind_name else "", True),
        ):
            if not query:
                continue
            result = answer(query, kinds_of)
            result["way"] = way
            answered.append(result)
            tally = tallies[way]
            tally["searched"] += 1
            tally[result["how"]] += 1
            if result.get("asks"):
                tally["asks which kind"] += 1
            if result.get("understood_brand"):
                tally["understood as the brand"] += 1
            cards = result["cards"]
            if cards:
                if cards[0]["brand"] == brand.key:
                    tally["the first card the brand's"] += 1
                if all(card["brand"] == brand.key for card in cards):
                    tally["every card the brand's"] += 1
                if with_kind and cards[0]["brand"] == brand.key and _of_kind(cards[0]["kinds"], kind):
                    tally["the first card the brand's and of the kind"] += 1
            lines[way].append(f'  "{query}": {describe(result, brand.key, kind if with_kind else "")}')
    out(f"the {len(real)} largest real brands, each searched four ways:")
    for way in ways:
        tally = tallies[way]
        searched = tally["searched"]
        if not searched:
            continue
        parts = [f"{key} {_number(tally[key])}" for key in ("shown", "not sure", "did you mean", "nothing") if tally[key]]
        parts += [
            f"{key} {_number(tally[key])}"
            for key in (
                "the first card the brand's", "every card the brand's", "the first card the brand's and of the kind",
                "asks which kind", "understood as the brand",
            )
            if tally[key]
        ]
        out(f"  {way}: {_number(searched)} searches; " + "; ".join(parts))
    seconds = sorted(result["seconds"] for result in answered)
    if seconds:
        out(f"  a search took {seconds[len(seconds) // 2]:.2f} s in the middle, {seconds[-1]:.2f} s the slowest")
    for way in ways:
        if lines[way]:
            out(f"-- {way}:")
            for line in lines[way]:
                out(line)
    out("")
    return answered


# --------------------------------------------------------------------------------------
# 7. The list as the search reads it
# --------------------------------------------------------------------------------------


def print_the_list(brands: dict[str, Brand], real: list[Brand], out: Callable[[str], None] = print) -> None:
    """The brands' list the site reads (`state.search_brands`, from 2026-11-20): its size and
    shapes; the brands' names the reading read as a kind before and how it reads them now;
    and the names of one word one slip from a kind's name, whose slip of the kind the
    reading no longer corrects (a buyer's "razer" for a razor reads as Razer)."""
    from picwise_nlu.concept_understanding import known_english_words, understand_product_query
    from picwise_providers.brand_list import BrandReader
    from picwise_providers.state import search_brands

    out("== 7. THE BRANDS' LIST AS THE SEARCH READS IT")
    reader = search_brands()
    if not isinstance(reader, BrandReader) or not len(reader):
        out("no list: the search reads no brand")
        out("")
        return
    listed = sorted(reader.brands.values(), key=lambda brand: (-brand.products, brand.key))
    shapes = Counter()
    for brand in listed:
        own = [kind for kind, count in brand.kinds if count >= CHOICE]
        shapes["several kinds (a question)" if len(own) >= 2 else "one kind" if own else "no kind read"] += 1
    out(
        f"listed: {_number(len(listed))} brands of {COUNTED} products or more, "
        f"{_number(sum(brand.products for brand in listed))} products; "
        + ", ".join(f"{name} {_number(count)}" for name, count in shapes.most_common())
    )
    single, several = reader.reading_names()
    out(f"names the reading never corrects: {_number(len(single))} of one word, {_number(len(several))} of several")
    before = []
    for brand in real:
        name = spoken(brand.name)
        if not name:
            continue
        now = understand_product_query(name)
        if now.understood and now.filters:
            continue
        before.append((brand, name, now.concept_id or ""))
    still = [(brand, concept) for brand, _name, concept in before if concept]
    out(
        f"read alone as a kind with the names given: {_number(len(still))} brands (a kind's own name, as "
        f"'lego'); the {LISTED // 2} largest:"
    )
    for brand, concept in still[: LISTED // 2]:
        out(f"  {brand.name} ({_number(brand.products)}): {concept}")
    kinds_words = NearIndex(known_english_words(), 1)
    near_kind = []
    for word in sorted(single):
        if len(word) < 4 or not word.isalpha():
            continue
        close = kinds_words.near(word, 1)
        if close:
            brand = reader.brands.get(brand_key(word))
            near_kind.append((brand, word, sorted(close)[:3]))
    near_kind.sort(key=lambda item: (-(item[0].products if item[0] else 0), item[1]))
    out(
        f"names of one word one slip from a word the search knows (a buyer's slip of that word now reads "
        f"as the brand): {_number(len(near_kind))}; the {LISTED} largest:"
    )
    for brand, word, close in near_kind[:LISTED]:
        products = _number(brand.products) if brand else "?"
        out(f"  {word} ({products}): near {', '.join(close)}")
    out("")


# --------------------------------------------------------------------------------------
# The run
# --------------------------------------------------------------------------------------


def read_words(path: str) -> frozenset[str]:
    """The word list's everyday words: lowercase, letters only, 3 letters or more (a name
    is a proper noun there, written with a capital)."""
    if not path or not Path(path).is_file():
        return frozenset()
    with open(path, encoding="utf-8", errors="ignore") as handle:
        return frozenset(
            word for word in (line.strip() for line in handle) if len(word) >= 3 and word.isascii() and word.isalpha()
            and word.islower()
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("catalogue", type=Path)
    parser.add_argument("--words", default="", help="a word list, one word a line (e.g. /usr/share/dict/words)")
    parser.add_argument("--top", type=int, default=TOP, help="how many of the largest brands to search")
    parser.add_argument("--no-searches", action="store_true", help="the brands only, no search")
    args = parser.parse_args(argv)
    for folder in (HERE, ROOT, ROOT / "src"):
        if str(folder) not in sys.path:
            sys.path.insert(0, str(folder))
    try:
        import audit_search

        began = time.monotonic()
        prepared = audit_search.load_catalogue(args.catalogue)
        if prepared is None:
            print("no prepared catalogue could be read")
            return 0
        words = read_words(args.words)
        brands = read_brands(prepared.products, prepared.kinds)
        shops = set().union(*(brand.shops for brand in brands.values())) - {""}
        print(
            f"the copy: prepared at {prepared.prepared_at:%Y-%m-%d %H:%M} UTC, {_number(len(prepared.products))} products, "
            f"{_number(len(shops))} shops; read with this commit's rules in {time.monotonic() - began:.0f} s"
        )
        print_brands(prepared, brands, words)
        if not args.no_searches:
            print_searches(prepared, brands, words, args.top)
        real = sorted(
            (brand for brand in brands.values() if brand.real and brand.products >= COUNTED),
            key=lambda brand: (-brand.products, brand.key),
        )
        print_the_list(brands, real)
    except Exception as error:  # a measure only
        print(f"the brands could not be measured: {type(error).__name__}: {_short(error, 200)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
