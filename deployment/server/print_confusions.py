"""Print which products confuse the search, on a copy of the server's catalogue and on the live site.

    ssh picwise 'sudo cat /srv/picwise/shared/prepared/catalogue.json.gz' > catalogue.json.gz
    python3 deployment/server/print_confusions.py catalogue.json.gz [--part kinds|searches|live|all] \
        [--gone gone.json] [--offers offers.json] [--site https://picwise.subby.cloud]

Owner, 2026-11-04: «Θέλω να μάθω ποια προϊόντα δημιουργούν μπέρδεμα στην αναζήτηση.. όπως τα
tablets... Banks...κτλ δηλαδή που μπορεί να μπερδευτεί το ευρετήριο και να βγάζει ακατάλληλα
προϊόντα.. θέλω έναν ολοκληρωμένο έλεγχο από άκρη σε άκρη», then «Ναι, προχώρα με τον
έλεγχο». Every product is read twice: as the server stored it (the rules of its
deployment) and with this checkout's rules (the main kind only, `_aisle_may_hold`, owner,
2026-11-03, not deployed). Printed, end to end:

1. where each kind comes from: the product's type or shelf named one (the title may have
   corrected it), or neither did and the reader fell back on the title alone
   (`_title_fallback_head`, the one path the rule reads); for the title alone, whether the
   aisle of Google's its shelf is in may hold the kind (`_AISLE_HOLDS`), may not (the rule
   makes it doubtful), or is not known (a shop's shelf Google has no name for, or none);
2. per kind, the products whose kind comes from the title alone, by the shop's shelf, with
   the cheapest of each (price first puts them at the top of a page);
3. what this checkout's rule takes away, per kind and shelf, and what it gives;
4. the products whose type or shelf named a kind, on an aisle that may not hold the kind
   they are read as: the rule does not read them;
5. the words that name more than one thing ("tablet", "bank", "mouse"...): the products
   whose title carries each, how they are read, and the aisles and shelves they come from;
6. every kind's search and the owner's words, searched on the copy as the server answers
   (its gone photos and offers, when given), with each set of kinds: the first 12 cards
   and which are suspects -- on an aisle that may not hold the kind, or of no kind and
   found by their words -- and which are unchecked (a kind from the title alone where no
   aisle is known);
7. with --site, the same searches on the live site, as a visitor reads them (public search
   pages only; no "View in Store" link is followed, which would count as a click): the
   first 12 cards, how many are the copy's own first 12, and the suspects among them;
each part ending in short: the words most read as their kind on an aisle that may not hold
it, and the searches whose first page holds suspects, with each set of kinds and live.
`--part` prints 1 to 5 ("kinds"), 6 ("searches") or 7 ("live"), or all of them.

Run by .github/workflows/server-confusions.yml on GitHub's runner, one job a part, each
from its own copies of the server's files; nothing on the server or shown changes.
Counts, kinds, shelves, titles, shops and prices only, never a link. Always exits 0.
"""
from __future__ import annotations

import argparse
import html
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass, field, replace
from pathlib import Path

# The owner's words (2026-11-04: «όπως τα tablets... Banks...») and those the handoff of
# 04/11 listed as naming more than one thing: read and searched first.
OWNER_WORDS = (
    "tablet", "tablets", "bank", "banks", "power bank", "mouse", "monitor", "toner", "case",
    "cable", "bed", "suit", "pad", "charger", "stand", "light", "speaker", "watch", "ring",
    "chain", "drill",
)
# How many cards a search is read for: three pages of four.
SHOWN = 12
# Per kind or word: the shelves, aisles and other readings named, and the cheapest listed.
SHELVES = 5
AISLES = 5
EXAMPLES = 2
OTHER_KINDS = 4
# Kinds and words listed with their examples; the others in one line each.
KINDS_IN_FULL = 80
CHANGES_IN_FULL = 60
OTHER_AISLES_IN_FULL = 40
WORDS_IN_FULL = 40
# Per search, the suspects and unchecked cards listed.
SUSPECTS_LISTED = 4
UNCHECKED_LISTED = 2
TITLE = 72
SHELF = 40
CRUMB = 80
# What a run prints: "kinds" (1 to 5), "searches" (6 and its short), "live" (7 and its
# short), or "all"; GitHub's runner runs each part in a job of its own, with its own log.
PARTS = ("kinds", "searches", "live", "compare", "all")
# Per change of one rule set against another ("compare"), the products listed in full.
COMPARED_LISTED = 40
# A visitor's browser, as `.github/scripts/live_photos.py` reads the site.
BROWSER = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0.0.0 Safari/537.36"
)
LIVE_PAUSE = 0.3

NOT_KNOWN = "not known"
HOLDS = "holds"
MAY_NOT = "may not"

_CARD = re.compile(r'<article class="pw-card([^"]*)" data-choice-id="([^"]*)">(.*?)</article>', re.S)


def _short(text: object, width: int) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= width else text[: width - 3] + "..."


def _text(fragment: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def _first(pattern: str, text: str) -> str:
    found = re.search(pattern, text, re.S)
    return _text(found.group(1)) if found else ""


@dataclass
class LiveCard:
    product_id: str
    recommended: bool
    role: str
    price: str
    shop: str
    title: str


def page_cards(page: str) -> list[LiveCard]:
    """The cards of a search page, in order (the markup the tests pin)."""
    cards = []
    for classes, product_id, inner in _CARD.findall(page):
        cards.append(
            LiveCard(
                product_id=html.unescape(product_id),
                recommended="recommended" in classes,
                role=_first(r'class="pw-role-label">(.*?)</p>', inner),
                price=_first(r'class="pw-price">(.*?)</p>', inner),
                shop=_first(r'class="pw-card-shop">(.*?)</p>', inner).removesuffix(" via Awin"),
                title=_first(r'class="pw-card-title">(.*?)</h2>', inner),
            )
        )
    return cards


def aisles_of(category: str, cu) -> tuple[frozenset[str], str]:
    """The aisles of Google's a category is in, read as `_aisle_may_hold` reads them, and
    how: "google" (it starts with an aisle of Google's), "shelf" (a shop's own shelf found
    among Google's by its name, `_shelf_aisles`), "unknown" (a shelf Google has no name
    for), "none" (no shelf at all)."""
    aisles_of_google = set(cu._AISLE_HOLDS) | set(cu._aisle_departments())
    seen = False
    for crumb in str(category or "").split(cu.CATEGORY_FIELD_SEPARATOR.strip()):
        names = [
            cu._us_shelf_name(name)
            for name in (" ".join(segment.lower().split()) for segment in cu._BREADCRUMB_SPLIT_RE.split(crumb))
            if name
        ]
        if not names:
            continue
        seen = True
        if names[0] in aisles_of_google:
            return frozenset({names[0]}), "google"
        found = cu._shelf_aisles(names[-1])
        if found:
            return frozenset(found), "shelf"
    return frozenset(), ("unknown" if seen else "none")


def aisle_name(aisles: frozenset[str], how: str) -> str:
    if how == "unknown":
        return "(a shelf Google has no name for)"
    if how == "none":
        return "(no shelf)"
    names = sorted(aisles)
    shown = " / ".join(names[:3]) + (f" / +{len(names) - 3}" if len(names) > 3 else "")
    return shown if how == "google" else f"{shown} (by the shelf's name)"


@dataclass
class Searched:
    """One search on the copy with one set of kinds."""

    query: str
    understood: str = ""
    total: int = 0
    cards: list[int] = field(default_factory=list)
    reason: str = ""
    error: str = ""


class Audit:
    """The copy, each product read with both sets of kinds, and what each says."""

    def __init__(self, prepared, modules) -> None:
        self.m = modules
        cu = modules.cu
        self.prepared = prepared
        self.products = prepared.products
        self.fields = prepared.search_fields
        self.categories = [str(fields.get("category") or "") for fields in self.fields]
        self.then = list(prepared.kinds)
        # Each product read with this checkout's rules, noting whether the reader fell back
        # on its title (`_title_fallback_head`: neither the type nor the shelf named a kind),
        # the one path the main-kind rule reads; the path is the same with the rules
        # deployed, which differ only in `_aisle_may_hold`.
        started = time.monotonic()
        fell_back = [False]
        original = cu._title_fallback_head

        def recording(title: str, category: str):
            fell_back[0] = True
            return original(title, category)

        seen: dict[tuple[str, str, str], tuple[frozenset[str], str]] = {}
        self.now = []
        self.source = []
        cu._title_fallback_head = recording
        cu.annotate_product_concepts.cache_clear()
        try:
            for product, fields in zip(self.products, self.fields):
                key = modules.product_kind_key(product, fields)
                read = seen.get(key)
                if read is None:
                    fell_back[0] = False
                    kinds = cu.annotate_product_concepts(*key)
                    read = seen[key] = (kinds, "title" if fell_back[0] else "shelf")
                self.now.append(read[0])
                self.source.append(read[1])
        finally:
            cu._title_fallback_head = original
            cu.annotate_product_concepts.cache_clear()
        self.read_in = time.monotonic() - started
        self.labels_then = [self.label(kinds) for kinds in self.then]
        self.labels_now = [self.label(kinds) for kinds in self.now]
        self._aisles: dict[str, tuple[frozenset[str], str]] = {}
        self._holds: dict[tuple[str, str], bool] = {}
        self._broader: dict[str, frozenset[str]] = {}
        self.index_by_id: dict[str, list[int]] = defaultdict(list)
        for index, product in enumerate(self.products):
            self.index_by_id[str(product.provider_product_id or "").strip()].append(index)

    # -- what one product is -------------------------------------------------------------

    def label(self, kinds) -> str:
        if self.m.cu.ACCESSORY_MARKER in kinds:
            return "(accessory)"
        if self.m.cu.UNCERTAIN_MARKER in kinds:
            return "(doubtful)"
        return self.m.narrowest(kinds) or "(no kind)"

    def broader(self, kind: str) -> frozenset[str]:
        found = self._broader.get(kind)
        if found is None:
            found = self._broader[kind] = frozenset(self.m.broader_concepts(kind)) if not kind.startswith("(") else frozenset()
        return found

    def aisles(self, index: int) -> tuple[frozenset[str], str]:
        category = self.categories[index]
        found = self._aisles.get(category)
        if found is None:
            found = self._aisles[category] = aisles_of(category, self.m.cu)
        return found

    def aisle(self, index: int) -> str:
        return aisle_name(*self.aisles(index))

    def aisle_only(self, index: int) -> str:
        """The aisle's name alone, for a list of shelves: "health & beauty"."""
        aisles, how = self.aisles(index)
        return _short(" / ".join(sorted(aisles)), 36) if aisles else aisle_name(aisles, how)

    def verdict(self, index: int, kind: str) -> str:
        """Whether the aisle this product is in may hold the kind: "holds", "may not", or
        "not known" when nothing says which aisle it is in."""
        if self.aisles(index)[1] in ("unknown", "none"):
            return NOT_KNOWN
        key = (self.categories[index], kind)
        holds = self._holds.get(key)
        if holds is None:
            holds = self._holds[key] = self.m.cu._aisle_may_hold(self.categories[index], kind)
        return HOLDS if holds else MAY_NOT

    def shelf(self, index: int) -> str:
        return self.m.cu._narrowest_shelf(self.categories[index]).strip() or "-"

    def crumb(self, index: int) -> str:
        return _short(self.categories[index], CRUMB) or "-"

    def context(self, kinds) -> str:
        cu = self.m.cu
        marks = [name for marker, name in ((cu.PET_MARKER, "pet"), (cu.CAMPING_MARKER, "camping")) if marker in kinds]
        return "+".join(marks)

    def price(self, index: int) -> float:
        amount = self.m.parse_price_amount(self.products[index].price_text)
        return amount if amount is not None else float("inf")

    def example(self, index: int, with_shelf: bool = True) -> str:
        product = self.products[index]
        amount = self.m.parse_price_amount(product.price_text)
        price = f"{amount:,.2f} {str(product.currency or '').strip().upper()}" if amount is not None else "no price"
        mark = self.context(self.then[index])
        line = f"{price:>14} | {_short(self.m.shop_of(product), 24)} | {_short(product.title, TITLE)}"
        line += f" [{mark}]" if mark else ""
        return f"{line} | {_short(self.shelf(index), SHELF)}" if with_shelf else line

    def cheapest(self, indices) -> list[int]:
        return sorted(indices, key=lambda index: (self.price(index), str(self.products[index].title or "")))[:EXAMPLES]

    def is_real(self, label: str) -> bool:
        return not label.startswith("(")


# -- 1 and 2: where each kind comes from ----------------------------------------------------


def _named(groups: dict, width: int = 34) -> str:
    """"name count, ..." for the largest groups of a dict of lists."""
    listed = sorted(groups.items(), key=lambda item: (-len(item[1]), item[0]))[:SHELVES]
    more = len(groups) - len(listed)
    return ", ".join(f"{_short(name, width)} {len(found):,}" for name, found in listed) + (f" (+{more:,})" if more > 0 else "")


def print_where_from(audit: Audit) -> None:
    print("== 1. Where each kind comes from")
    for name, labels, kinds in (("the rules deployed (the kinds the server stored)", audit.labels_then, audit.then),
                                ("this checkout's rules (the main kind only)", audit.labels_now, audit.now)):
        counts: Counter = Counter()
        context = 0
        for index, label in enumerate(labels):
            if not audit.is_real(label):
                counts[label] += 1
                continue
            if audit.context(kinds[index]):
                context += 1
            source = audit.source[index]
            counts[source if source != "title" else f"title {audit.verdict(index, label)}"] += 1
        real = sum(count for key, count in counts.items() if not key.startswith("("))
        title = sum(count for key, count in counts.items() if key.startswith("title "))
        print(
            f"with {name}: {real:,} products of a kind; the type or the shelf named one {counts['shelf']:,} (the"
            f" title may have corrected it); from the title alone, neither naming one, {title:,}: on an aisle"
            f" that may hold the kind {counts['title ' + HOLDS]:,}, on one that may not {counts['title ' + MAY_NOT]:,},"
            f" the aisle not known {counts['title ' + NOT_KNOWN]:,}; of no kind: doubtful {counts['(doubtful)']:,},"
            f" an accessory {counts['(accessory)']:,}, none {counts['(no kind)']:,}; {context:,} of a kind carry a pet"
            " or camping mark, which a search for the kind alone leaves out"
        )
    how = Counter(audit.aisles(index)[1] for index in range(len(audit.products)))
    print(
        f"the aisle each product is in: by a path of Google's {how['google']:,}, by the shop's shelf found among"
        f" Google's {how['shelf']:,}, a shelf Google has no name for {how['unknown']:,}, no shelf {how['none']:,}"
    )


def print_title_alone(audit: Audit) -> None:
    print()
    print(
        "== 2. Per kind (the rules deployed), the products whose kind comes from the title alone, by the aisle's"
        " verdict and the shop's shelf; then the cheapest that may not be of the kind (price | shop | title | shelf)"
    )
    kinds: dict[str, dict] = {}
    for index, label in enumerate(audit.labels_then):
        if not audit.is_real(label):
            continue
        entry = kinds.setdefault(label, {"all": 0, HOLDS: defaultdict(list), MAY_NOT: defaultdict(list), NOT_KNOWN: defaultdict(list)})
        entry["all"] += 1
        if audit.source[index] == "title":
            verdict = audit.verdict(index, label)
            shelf = audit.shelf(index)
            if verdict == MAY_NOT:
                shelf = f"{shelf} ({audit.aisle_only(index)})"
            entry[verdict][shelf].append(index)
    now = Counter(label for label in audit.labels_now if audit.is_real(label))

    def size(entry: dict, verdict: str) -> int:
        return sum(map(len, entry[verdict].values()))

    listed = sorted(
        ((kind, entry) for kind, entry in kinds.items() if size(entry, HOLDS) + size(entry, MAY_NOT) + size(entry, NOT_KNOWN)),
        key=lambda item: (-(size(item[1], MAY_NOT) + size(item[1], NOT_KNOWN)), -size(item[1], HOLDS), item[0]),
    )
    print(f"{len(listed):,} kinds have products whose kind comes from the title alone; the most doubtful first")
    for position, (kind, entry) in enumerate(listed):
        holds, may_not, unknown = size(entry, HOLDS), size(entry, MAY_NOT), size(entry, NOT_KNOWN)
        print(
            f"  {kind}: {entry['all']:,} products ({now[kind]:,} with this checkout's rules); from the title alone"
            f" {holds + may_not + unknown:,}: may hold {holds:,}, may not {may_not:,}, not known {unknown:,}"
        )
        if position >= KINDS_IN_FULL or not (may_not or unknown):
            continue
        for verdict in (MAY_NOT, NOT_KNOWN, HOLDS):
            if entry[verdict]:
                print(f"      {verdict}: {_named(entry[verdict], 70)}")
        for verdict in (MAY_NOT, NOT_KNOWN):
            every = [index for indices in entry[verdict].values() for index in indices]
            for index in audit.cheapest(every):
                print(f"      e.g. {verdict}: {audit.example(index)}")


# -- 3 and 4: what the rule changes, and what it does not read ------------------------------


def print_rule_changes(audit: Audit) -> None:
    print()
    print("== 3. What this checkout's rule changes, per kind as deployed: to what, from which shelves, the cheapest")
    taken: dict[str, list[int]] = defaultdict(list)
    given: dict[str, list[int]] = defaultdict(list)
    for index, (then, now) in enumerate(zip(audit.labels_then, audit.labels_now)):
        if then == now:
            continue
        if audit.is_real(then):
            taken[then].append(index)
        if audit.is_real(now):
            given[now].append(index)
    total = sum(map(len, taken.values()))
    print(f"{total:,} products lose their kind or change it, in {len(taken):,} kinds; {sum(map(len, given.values())):,} gain one")
    for position, (kind, indices) in enumerate(sorted(taken.items(), key=lambda item: (-len(item[1]), item[0]))):
        to = Counter(audit.labels_now[index] for index in indices)
        shelves: dict[str, list[int]] = defaultdict(list)
        for index in indices:
            shelves[f"{audit.shelf(index)} ({audit.aisle_only(index)})"].append(index)
        print(
            f"  {kind}: {len(indices):,} -> " + ", ".join(f"{label} {count:,}" for label, count in to.most_common(OTHER_KINDS))
            + f" | shelves: {_named(shelves, 60)}"
        )
        if position < CHANGES_IN_FULL:
            for index in audit.cheapest(indices):
                print(f"      e.g. {audit.example(index)}")
    for kind, indices in sorted(given.items(), key=lambda item: (-len(item[1]), item[0])):
        before = Counter(audit.labels_then[index] for index in indices)
        print(f"  gains {kind}: {len(indices):,}, before " + ", ".join(f"{label} {count:,}" for label, count in before.most_common(OTHER_KINDS)))
        for index in audit.cheapest(indices):
            print(f"      e.g. {audit.example(index)}")


def print_shelf_on_another_aisle(audit: Audit) -> None:
    print()
    print(
        "== 4. Products whose type or shelf named a kind, on an aisle that may not hold the kind they are read as"
        " (the rule reads only a kind from the title alone): per kind, the whole shelves, the cheapest"
    )
    kinds: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    for index, label in enumerate(audit.labels_now):
        if not audit.is_real(label) or audit.source[index] == "title":
            continue
        if audit.verdict(index, label) == MAY_NOT:
            kinds[label][audit.crumb(index)].append(index)
    listed = sorted(kinds.items(), key=lambda item: (-sum(map(len, item[1].values())), item[0]))
    print(f"{sum(sum(map(len, crumbs.values())) for _kind, crumbs in listed):,} products in {len(listed):,} kinds")
    for position, (kind, crumbs) in enumerate(listed):
        print(f"  {kind}: {sum(map(len, crumbs.values())):,} | {_named(crumbs, CRUMB)}")
        if position < OTHER_AISLES_IN_FULL:
            every = [index for indices in crumbs.values() for index in indices]
            for index in audit.cheapest(every):
                print(f"      e.g. {audit.example(index)}")


# -- 5: the words that name more than one thing ---------------------------------------------


@dataclass
class Word:
    key: str
    kinds: set[str]
    carrying: list[int] = field(default_factory=list)
    then: list[int] = field(default_factory=list)
    now: list[int] = field(default_factory=list)
    # Read as the word's kind on an aisle that may not hold it, and from the title alone
    # where no aisle is known: as deployed, and with this checkout's rules.
    may_not: tuple[int, int] = (0, 0)
    unknown: tuple[int, int] = (0, 0)


def measure_words(audit: Audit) -> tuple[list[str], dict[str, Word]]:
    """The nouns of the kinds' names (and of the owner's words) carried by titles: per
    noun, its kinds and how the products carrying it are read. The owner's first."""
    m = audit.m
    nouns: dict[str, set[str]] = defaultdict(set)
    for kind in m.by_id:
        for noun in m.kind_nouns(kind):
            nouns[noun].add(kind)
    # The noun of each of the owner's words: "power bank" is read as "bank".
    owner_nouns = []
    for words in OWNER_WORDS:
        noun = m.normalize(words).split()[-1]
        nouns.setdefault(noun, set())
        owner_nouns.append(noun)
    known = set(nouns)
    key_of = {noun: min((m.forms(noun) & known) | {noun}, key=lambda word: (len(word), word)) for noun in nouns}
    words: dict[str, Word] = {}
    for noun, kinds in nouns.items():
        words.setdefault(key_of[noun], Word(key_of[noun], set())).kinds.update(kinds)
    for index, product in enumerate(audit.products):
        for key in {key_of[word] for word in m.title_words(str(product.title or "")) if word in key_of}:
            words[key].carrying.append(index)
    for word in words.values():
        scores = []
        for name, labels in (("then", audit.labels_then), ("now", audit.labels_now)):
            own = [index for index in word.carrying if audit.is_real(labels[index]) and word.kinds & audit.broader(labels[index])]
            setattr(word, name, own)
            verdicts = [audit.verdict(index, labels[index]) for index in own]
            scores.append((
                sum(verdict == MAY_NOT for verdict in verdicts),
                sum(verdict == NOT_KNOWN and audit.source[index] == "title" for index, verdict in zip(own, verdicts)),
            ))
        word.may_not = (scores[0][0], scores[1][0])
        word.unknown = (scores[0][1], scores[1][1])
    owner_keys: list[str] = []
    for noun in owner_nouns:
        if key_of[noun] not in owner_keys:
            owner_keys.append(key_of[noun])
    return owner_keys, words


def print_words(audit: Audit) -> None:
    print()
    print(
        "== 5. The words that name more than one thing: the products whose title carries each, how they are read"
        " (the rules deployed -> this checkout's), the aisles they come from, the cheapest of each sense"
    )
    owner_keys, words = measure_words(audit)
    others = sorted(
        (key for key, word in words.items() if key not in owner_keys and word.may_not[0]),
        key=lambda key: (-words[key].may_not[0], -words[key].unknown[0], key),
    )
    carried = sum(1 for word in words.values() if word.carrying)
    print(
        f"{carried:,} words of the kinds' names are carried by titles; the owner's first, then those whose products"
        " read as their kind sit most on an aisle that may not hold it"
    )
    for position, key in enumerate(owner_keys + others):
        word = words[key]
        kinds = sorted(word.kinds)
        names = (", ".join(kinds[:4]) + (f" +{len(kinds) - 4}" if len(kinds) > 4 else "")) if kinds else "no kind's name"
        print(
            f"  {key} ({names}): {len(word.carrying):,} titles; read as its kind {len(word.then):,} -> {len(word.now):,};"
            f" of those on an aisle that may not hold it {word.may_not[0]:,} -> {word.may_not[1]:,}, from the title"
            f" alone where no aisle is known {word.unknown[0]:,} -> {word.unknown[1]:,}"
        )
        if position >= len(owner_keys) + WORDS_IN_FULL or not word.carrying:
            continue
        own = set(word.then)
        readings: Counter = Counter(
            "its kind" if index in own else audit.labels_then[index] if not audit.is_real(audit.labels_then[index])
            else f"another: {audit.labels_then[index]}"
            for index in word.carrying
        )
        print("      read as: " + ", ".join(f"{reading} {count:,}" for reading, count in readings.most_common(OTHER_KINDS + 3)))
        aisles: dict[str, list[int]] = defaultdict(list)
        for index in word.carrying:
            aisles[audit.aisle(index)].append(index)
        now = set(word.now)
        parts = [
            f"{_short(aisle, 36)} {len(found):,} ({sum(i in own for i in found):,} -> {sum(i in now for i in found):,})"
            for aisle, found in sorted(aisles.items(), key=lambda item: (-len(item[1]), item[0]))[:AISLES]
        ]
        print("      aisles (as its kind, deployed -> this checkout): " + "; ".join(parts))
        wrong = [index for index in word.then if audit.verdict(index, audit.labels_then[index]) == MAY_NOT]
        for index in audit.cheapest(wrong)[:1]:
            print(f"      e.g. as {audit.labels_then[index]} on another aisle: {audit.example(index)}")
        loose = [
            index for index in word.then
            if audit.source[index] == "title" and audit.verdict(index, audit.labels_then[index]) == NOT_KNOWN
        ]
        for index in audit.cheapest(loose)[:1]:
            print(f"      e.g. as {audit.labels_then[index]} by its title, no aisle known: {audit.example(index)}")
        senses: dict[str, list[int]] = defaultdict(list)
        for index in word.carrying:
            if index not in own:
                senses[audit.aisle(index)].append(index)
        for aisle, found in sorted(senses.items(), key=lambda item: (-len(item[1]), item[0]))[:2]:
            index = audit.cheapest(found)[0]
            print(f"      e.g. not its kind ({audit.labels_then[index]}), {_short(aisle, 30)}: {audit.example(index)}")
    quiet = sum(1 for key, word in words.items() if key not in owner_keys and word.carrying and not word.may_not[0])
    print(f"  words whose products read as their kind sit on no aisle that may not hold it: {quiet:,}")
    print()
    print("== In short (the kinds): the words whose products read as their kind sit on an aisle that may not hold it,")
    print("   or come from the title alone where no aisle is known (deployed -> this checkout's rules), the most first")
    ranked = sorted(
        (word for word in words.values() if word.may_not[0] or word.unknown[0]),
        key=lambda word: (-(word.may_not[0] + word.unknown[0]), word.key),
    )
    for word in ranked[:60]:
        print(
            f"  {word.key}: of {len(word.then):,} -> {len(word.now):,} read as its kind, another aisle"
            f" {word.may_not[0]:,} -> {word.may_not[1]:,}, no aisle known {word.unknown[0]:,} -> {word.unknown[1]:,}"
        )
    taken = sum(1 for then, now in zip(audit.labels_then, audit.labels_now) if then != now and audit.is_real(then))
    print(f"  this checkout's rule changes the kind of {taken:,} products of {len(audit.products):,}")


# -- the compare part: one change of the rules on its own ------------------------------------


def print_compare(audit: Audit, path: str, name: str) -> None:
    """Every product whose kind the rules of another checkout (`kinds_of.py`, one label a
    line in the file's order) read otherwise than this checkout's, grouped by the change
    and listed in full: what one change of the rules does on its own."""
    print()
    print(f"== Compare: the rules of {name} -> this checkout's, every product read otherwise (price | shop | title | shelf)")
    try:
        labels = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        print(f"  the kinds of {name} could not be read")
        return
    if len(labels) != len(audit.products):
        print(f"  the kinds of {name} are {len(labels):,}, for {len(audit.products):,} products: not compared")
        return
    changes: dict[tuple[str, str], list[int]] = defaultdict(list)
    for index, (before, now) in enumerate(zip(labels, audit.labels_now)):
        if before != now:
            changes[(before, now)].append(index)
    print(f"  {sum(map(len, changes.values())):,} products read otherwise, in {len(changes):,} changes")
    for (before, now), indices in sorted(changes.items(), key=lambda item: (-len(item[1]), item[0])):
        print(f"  {before} -> {now}: {len(indices):,}")
        listed = sorted(indices, key=lambda index: (audit.price(index), str(audit.products[index].title or "")))
        for index in listed[:COMPARED_LISTED]:
            print(f"      {audit.example(index)} | {_short(audit.aisle(index), 40)}")


# -- 6 and 7: every search, on the copy and live --------------------------------------------


def search_queries(audit: Audit, limit: int = 0) -> list[str]:
    names = sorted({concept.primary_english for concept in audit.m.by_id.values() if concept.primary_english})
    if limit:
        names = names[:limit]
    queries = list(OWNER_WORDS)
    for name in names:
        if name not in queries:
            queries.append(name)
    return queries


def card_flags(audit: Audit, index: int, kind: str, labels: list[str]) -> tuple[str, str]:
    """("suspect" | "unchecked" | "", why) for one card of a search understood as `kind`:
    a suspect is of no kind (found by its words), of another kind, or on an aisle that may
    not hold the kind; unchecked, a kind from its title alone where no aisle is known."""
    label = labels[index]
    if not audit.is_real(label):
        return "suspect", f"of no kind ({label}), found by its words"
    if kind not in audit.broader(label):
        return "suspect", f"read as {label}"
    verdict = audit.verdict(index, kind)
    if verdict == MAY_NOT:
        return "suspect", f"on an aisle that may not hold {kind}: {_short(audit.aisle(index), 40)}"
    if verdict == NOT_KNOWN and audit.source[index] == "title":
        return "unchecked", "its kind from its title alone, no aisle known"
    return "", ""


def search_on_copy(audit: Audit, queries: list[str], name: str) -> list[Searched]:
    m = audit.m
    results = []
    began = time.monotonic()
    for query in queries:
        searched = Searched(query)
        try:
            resolution = m.resolve_live_search(query, shown=SHOWN)
        except Exception as error:  # a measure only: the run goes on without it
            searched.error = type(error).__name__
            results.append(searched)
            continue
        searched.understood = str(resolution.understood_concept_id or "")
        searched.total = int(resolution.provider_feed_total_count or 0)
        rows = list(resolution.provider_feed_selected_products) + list(resolution.provider_feed_more_products)
        for row in rows[:SHOWN]:
            found = audit.index_by_id.get(str(row.get("provider_product_id") or "").strip())
            searched.cards.append(found[0] if found else -1)
        if not rows:
            families = tuple(resolution.provider_feed_ambiguous_product_families or ())
            reasons = ["which do you mean: " + ", ".join(families[:6])] if families else []
            reasons += [code for code in resolution.reason_codes if "broad" in code or "ambiguous" in code][:2]
            searched.reason = "; ".join(reasons) or "no products"
        results.append(searched)
    seconds = time.monotonic() - began
    print(f"  ({len(queries):,} searches with {name} in {seconds:.0f} s, {1000 * seconds / max(len(queries), 1):.0f} ms each)")
    return results


def _tally(audit: Audit, searched: Searched, labels: list[str]) -> tuple[int, int, int, list[tuple[int, int, str, str]]]:
    """(suspects, of them among the first 4, unchecked, the flagged cards) of one search."""
    flagged = []
    suspects = first = unchecked = 0
    if not searched.understood:
        return 0, 0, 0, flagged
    for position, index in enumerate(searched.cards, start=1):
        if index < 0:
            continue
        flag, why = card_flags(audit, index, searched.understood, labels)
        if flag == "suspect":
            suspects += 1
            first += position <= 4
        elif flag == "unchecked":
            unchecked += 1
        if flag:
            flagged.append((position, index, flag, why))
    return suspects, first, unchecked, flagged


def print_searches(audit: Audit, then: list[Searched], now: list[Searched]) -> dict[str, dict[str, int]]:
    print()
    print(
        f"== 6. Every kind's search and the owner's words, on the copy as the server answers: the first {SHOWN}"
        " cards with the rules deployed and with this checkout's; S a suspect (an aisle that may not hold the kind,"
        " another kind, or no kind), U unchecked (a kind from the title alone, no aisle known)"
    )
    counts: dict[str, dict[str, int]] = {}
    for before, after in zip(then, now):
        tallies = []
        lines = []
        counts[before.query] = {}
        for name, searched, labels in (("deployed", before, audit.labels_then), ("this checkout", after, audit.labels_now)):
            if searched.error:
                tallies.append(f"{name}: the search failed ({searched.error})")
                continue
            if not searched.cards:
                tallies.append(f"{name}: {searched.total:,} products, no card ({_short(searched.reason, 160)})")
                continue
            missing = sum(1 for index in searched.cards if index < 0)
            if not searched.understood:
                # No kind: the cards are what the words found, of whatever kinds and aisles.
                cards = [index for index in searched.cards if index >= 0]
                kinds = Counter(labels[index] for index in cards)
                aisles = Counter(_short(audit.aisle(index), 30) for index in cards)
                tallies.append(
                    f"{name}: {searched.total:,} products, by their words, of the kinds "
                    + ", ".join(f"{kind} {count}" for kind, count in kinds.most_common(4))
                    + " in the aisles " + ", ".join(f"{aisle} {count}" for aisle, count in aisles.most_common(3))
                )
                if name == "deployed":
                    for index in audit.cheapest(cards):
                        lines.append(f"      {name}: {_short(labels[index], 18)} | {audit.example(index)}")
                continue
            suspects, first, unchecked, flagged = _tally(audit, searched, labels)
            counts[before.query][name] = suspects
            tallies.append(
                f"{name}: {searched.total:,} ({searched.understood}) S {suspects}/{len(searched.cards)}"
                f" ({first} in the first 4) U {unchecked}" + (f", {missing} not in the copy" if missing else "")
            )
            listed = Counter()
            for position, index, flag, why in flagged:
                # Suspects as each set of kinds shows them; unchecked as this checkout's page would.
                if flag == "unchecked" and name != "this checkout":
                    continue
                limit = SUSPECTS_LISTED if flag == "suspect" else UNCHECKED_LISTED
                if listed[flag] >= limit:
                    continue
                listed[flag] += 1
                lines.append(f"      {name} #{position} {flag[0].upper()} {audit.example(index)} | {why}")
        print(f"  {before.query}: " + " | ".join(tallies))
        for line in lines:
            print(line)
    return counts


def _get(url: str) -> tuple[int, str]:
    request = urllib.request.Request(url, headers={"User-Agent": BROWSER, "Accept": "text/html"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as error:
        return error.code, ""
    except Exception as error:  # a read only: every failure is said, none stops it
        return 0, type(error).__name__


def print_live(audit: Audit, site: str, then: list[Searched]) -> tuple[dict[str, int], int, int]:
    print()
    print(
        f"== 7. The same searches on the live site, read as a visitor: its first {SHOWN} cards, how many are the"
        " copy's own with the rules deployed, and the suspects among them (S)"
    )
    suspects_of: dict[str, int] = {}
    same_pages = read = 0
    for searched in then:
        query = urllib.parse.urlencode({"q": searched.query, "shown": str(SHOWN)})
        status, page = _get(f"{site.rstrip('/')}/search?{query}")
        time.sleep(LIVE_PAUSE)
        if status != 200:
            print(f"  {searched.query}: HTTP {status or page}")
            continue
        read += 1
        cards = page_cards(page)
        counter = _first(r'<p class="pw-counter">(.*?)</p>', page)
        copy_ids = [str(audit.products[index].provider_product_id or "").strip() for index in searched.cards if index >= 0]
        live_ids = [card.product_id for card in cards]
        in_copy = set(copy_ids)
        same = sum(1 for product_id in live_ids if product_id in in_copy)
        same_pages += live_ids == copy_ids
        suspects = 0
        lines = []
        for position, card in enumerate(cards, start=1):
            found = audit.index_by_id.get(card.product_id)
            if not found:
                lines.append(f"      live #{position} not in the copy: {card.price} | {_short(card.shop, 24)} | {_short(card.title, TITLE)}")
                continue
            if not searched.understood:
                continue
            flag, why = card_flags(audit, found[0], searched.understood, audit.labels_then)
            if flag == "suspect":
                suspects += 1
                if suspects <= SUSPECTS_LISTED:
                    lines.append(f"      live #{position} S {audit.example(found[0])} | {why}")
        suspects_of[searched.query] = suspects
        print(
            f"  {searched.query}: {counter or 'no counter'}, {len(cards)} cards, {same} of them the copy's"
            f"{', the same in order' if live_ids == copy_ids else ''}; S {suspects}"
        )
        for line in lines[: SUSPECTS_LISTED + 4]:
            print(line)
    print(f"  {read:,} pages read; {same_pages:,} show the copy's cards, card for card")
    return suspects_of, read, same_pages


def print_short(counts: dict[str, dict[str, int]]) -> None:
    print()
    print(f"== In short (the searches on the copy): the searches whose first {SHOWN} cards hold suspects, the most first")
    for name in ("deployed", "this checkout"):
        listed = sorted(
            ((query, found[name]) for query, found in counts.items() if found.get(name)),
            key=lambda item: (-item[1], item[0]),
        )
        total = sum(1 for found in counts.values() if name in found)
        print(f"  {name}: {len(listed):,} of {total:,} searches of a kind: " + ", ".join(f"{query} {count}" for query, count in listed))


def print_live_short(live: dict[str, int], read: int, same: int) -> None:
    print()
    print(f"== In short (the live site): the pages whose first {SHOWN} cards hold suspects, the most first")
    listed = sorted(((query, count) for query, count in live.items() if count), key=lambda item: (-item[1], item[0]))
    print(f"  {len(listed):,} of {read:,} pages read ({same:,} the copy's cards, card for card): "
          + ", ".join(f"{query} {count}" for query, count in listed))


# -- the run --------------------------------------------------------------------------------


class _Modules:
    """This checkout's code the audit reads, imported once."""

    def __init__(self) -> None:
        from picwise_nlu import concept_understanding as cu
        from picwise_nlu.product_concepts import broader_concepts, get_product_concepts_by_id
        from picwise_providers import kind_check, state
        from picwise_providers.awin_adapter import feed_file_cache_key
        from picwise_providers.catalogue_balance import _narrowest_kind
        from picwise_providers.catalogue_cap import shop_of
        from picwise_providers.decision_labels import parse_price_amount
        from picwise_providers.prepared_catalogue import PreparedFileCheck, read_prepared_catalogue_to_measure
        from picwise_providers.search_selection import _product_search_fields, product_kind_key
        from picwise_providers.suggestions import build_search_suggestions
        from picwise_search.live_search_resolver import resolve_live_search

        self.cu = cu
        self.broader_concepts = broader_concepts
        self.by_id = get_product_concepts_by_id()
        self.state = state
        self.feed_file_cache_key = feed_file_cache_key
        self.narrowest = _narrowest_kind
        self.shop_of = shop_of
        self.parse_price_amount = parse_price_amount
        self.PreparedFileCheck = PreparedFileCheck
        self.read_prepared_catalogue_to_measure = read_prepared_catalogue_to_measure
        self.product_search_fields = _product_search_fields
        self.product_kind_key = product_kind_key
        self.build_search_suggestions = build_search_suggestions
        self.resolve_live_search = resolve_live_search
        self.kind_nouns = kind_check._kind_nouns
        self.title_words = kind_check._title_words
        self.forms = kind_check._forms
        self.normalize = cu.normalize_understanding_text


def _answer_from(m: _Modules, path: Path, prepared) -> None:
    """The search answers from `prepared` in this process, as the server from its file."""
    m.state._PREPARED_STATE.clear()
    m.state._PREPARED_STATE.update(
        file_key=m.feed_file_cache_key(str(path)),
        prepared=prepared,
        check=m.PreparedFileCheck("fresh", prepared, prepared.prepared_at),
    )
    m.state.remember_product_kinds({})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], add_help=False)
    parser.add_argument("catalogue")
    parser.add_argument("--gone", default="")
    parser.add_argument("--offers", default="")
    parser.add_argument("--site", default="")
    parser.add_argument("--part", default="all", choices=PARTS)
    # The kinds another checkout's rules read (`kinds_of.py`), and its name, for "compare".
    parser.add_argument("--compare", default="")
    parser.add_argument("--compare-name", default="another checkout")
    # Only the first N kinds' names are searched (the owner's words always): for tests.
    parser.add_argument("--kinds", type=int, default=0)
    try:
        args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    except SystemExit:
        print(
            "usage: print_confusions.py CATALOGUE.json.gz [--part kinds|searches|live|all] [--gone GONE.json]"
            " [--offers OFFERS.json] [--site URL]"
        )
        return 0
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass
    root = Path(__file__).resolve().parents[2]
    for folder in (root, root / "src"):
        if str(folder) not in sys.path:
            sys.path.insert(0, str(folder))
    path = Path(args.catalogue).resolve()
    # The copies stand in for the server's files; nothing else is read for the feed.
    for name in ("AWIN_FEED_URL", "AWIN_FEED_FILE", "PICWISE_PURCHASABILITY_CACHE_FILE",
                 "PICWISE_GONE_PHOTOS_FILE", "PICWISE_OFFERS_FILE"):
        os.environ.pop(name, None)
    os.environ["PICWISE_PREPARED_CATALOGUE_FILE"] = str(path)
    os.environ["PICWISE_PREPARED_MAX_AGE_HOURS"] = "100000"
    given = []
    for option, name in ((args.gone, "PICWISE_GONE_PHOTOS_FILE"), (args.offers, "PICWISE_OFFERS_FILE")):
        if option and Path(option).is_file() and Path(option).stat().st_size:
            os.environ[name] = str(Path(option).resolve())
            given.append(name)
    try:
        m = _Modules()
        prepared = m.read_prepared_catalogue_to_measure(path)
        if prepared is None:
            print("no prepared catalogue could be read")
            return 0
        if not prepared.search_fields or "category" not in prepared.search_fields[0]:
            prepared = replace(prepared, search_fields=tuple(m.product_search_fields(product) for product in prepared.products))
        audit = Audit(prepared, m)
    except Exception as error:  # a measure only
        print(f"the catalogue could not be read with this checkout's rules: {type(error).__name__}: {error}")
        return 0
    changed = sum(then != now for then, now in zip(audit.labels_then, audit.labels_now))
    print(
        f"the prepared catalogue of {prepared.prepared_at.isoformat()}: {len(audit.products):,} products a card can"
        f" show; read again with this checkout's rules in {audit.read_in:.0f} s, {changed:,} read otherwise;"
        f" the gone photos {'given' if 'PICWISE_GONE_PHOTOS_FILE' in given else 'not given'}, the offers"
        f" {'given' if 'PICWISE_OFFERS_FILE' in given else 'not given'}; the part: {args.part}"
    )
    if args.part in ("kinds", "all"):
        for section in (print_where_from, print_title_alone, print_rule_changes, print_shelf_on_another_aisle, print_words):
            began = time.monotonic()
            try:
                section(audit)
            except Exception as error:  # a measure only: the next section goes on
                print(f"  the section could not be measured: {type(error).__name__}: {error}")
            print(f"  ({time.monotonic() - began:.0f} s)")
    if args.part == "compare":
        print_compare(audit, args.compare, args.compare_name)
        return 0
    if args.part == "kinds":
        return 0
    queries = search_queries(audit, args.kinds)
    print()
    print(f"searching {len(queries):,} words on the copy" + (", twice" if args.part != "live" else ""))
    try:
        _answer_from(m, path, prepared)
        then = search_on_copy(audit, queries, "the rules deployed")
        now = None
        if args.part != "live":
            started = time.monotonic()
            prepared_now = replace(prepared, kinds=tuple(audit.now), choices={})
            _answer_from(m, path, prepared_now)
            catalogue = m.state._prepared_search_catalogue(prepared_now)
            choices = m.state._catalogue_kind_choices(catalogue)
            suggestions = m.build_search_suggestions(catalogue.new_products, choices=choices)
            prepared_now = replace(prepared_now, choices=choices, suggestions=suggestions)
            _answer_from(m, path, prepared_now)
            print(f"  (the copy prepared again with this checkout's kinds in {time.monotonic() - started:.0f} s)")
            now = search_on_copy(audit, queries, "this checkout's rules")
        m.state._PREPARED_STATE.clear()
    except Exception as error:  # a measure only
        print(f"  the searches could not be run: {type(error).__name__}: {error}")
        return 0
    if now is not None:
        print_short(print_searches(audit, then, now))
    if args.part in ("live", "all") and args.site:
        try:
            print_live_short(*print_live(audit, args.site, then))
        except Exception as error:  # a read only
            print(f"  the live site could not be read: {type(error).__name__}: {error}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
