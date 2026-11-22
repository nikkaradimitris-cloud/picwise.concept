"""The look before the «ανέβασε» of how many of a shop's products pass (the checks' rules 19.7.1).

Owner, 2026-11-22: what the bot scans of a shop passes to the site, 20,000 the most
(`docs/PICWISE_CHECKS_RULES.md`, section 19; `picwise_providers.shop_cap`), built behind its
switch (`data/shop_cap_switch.json`) and not deployed. Before his «ανέβασε» the catalogue is
prepared twice on GitHub's runner, never on the server, from the copies of what the server
prepared from (its feed copies, the night before's pool, the shops' catalogues, the AI's
lines, the checks' decisions when there are any): once with the switch as it is and once with
it on, by the preparation's own code (`tools/prepare_catalogue.py`), and the two are set side
by side. Read-only: nothing on the server or the site changes.

    python3 deployment/server/look_shop_rule.py prepare DIR [the preparation's own arguments]
    python3 deployment/server/look_shop_rule.py summary DIR --name on [--gone GONE.json] \
        [--offers OFFERS.json] [--families FAMILIES.json] [--seconds N] [--peak-kb N] [--no-searches]
    python3 deployment/server/look_shop_rule.py compare OFF/summary.json ON/summary.json

`prepare` runs the preparation into `DIR` (`catalogue.json.gz`, the note `prepared.json`) and
counts, where the caps are worked out, every product a card can show: per shop, per category
and per kind, how many there are, how many the shops' rule keeps and how many the cap of a
category then keeps; which were shown the night before; the candidates each cap names
(`caps.json`). `summary` reads the catalogue that run wrote as the site reads it and writes
`summary.json`: the products per shop, category and kind, every kind searched by its first
name and the 40 searches of the measure after, their first cards. `compare` prints the two
side by side.

Written and printed: counts, shops' names, kinds, categories, titles and prices; never a
link, an id or a key.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Collection, Mapping, Sequence

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for folder in (ROOT, ROOT / "src", HERE, ROOT / "tools"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

CAPS_NAME = "caps.json"
SUMMARY_NAME = "summary.json"
NOTE_NAME = "prepared.json"
CATALOGUE_NAME = "catalogue.json.gz"
# The first cards of a kind's own search, and of each of the 40 searches.
KIND_CARDS = 4
SEARCH_CARDS = 12
TITLE = 60
# How many lines of a list the comparison prints.
LISTED = 40
# A kind is thin under this many products (the rules 19.4 a); a search's first page is 4 cards.
THIN = 100
STARTED = time.perf_counter()


def _short(text: Any, width: int = TITLE) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= width else text[: width - 1].rstrip() + "…"


def _real(kinds: Collection[str]) -> list[str]:
    return [kind for kind in kinds if not kind.startswith("__")]


# ---- prepare: the caps counted where they are worked out -------------------------------


def count_caps(
    products: Sequence[Any],
    kinds: Sequence[Collection[str]],
    *,
    shop_keep: Sequence[bool] | None,
    keep: Sequence[bool] | None,
    pool: Collection[str] = frozenset(),
    shop_candidates: Sequence[int] = (),
    cap_candidates: Sequence[int] = (),
) -> dict[str, Any]:
    """Every product a card can show, counted by shop, category and kind: how many there
    are, how many the shops' rule keeps (`shop_keep`; None: no shop is capped), how many are
    kept in the end (`keep`; None: the cap failed and every product is kept); per shop also
    those shown the night before (their row key in `pool`), those of them the shops' rule
    leaves out, and the candidates each cap names (indices into the products)."""
    from picwise_providers.catalogue_cap import category_of, row_key, shop_of

    count = len(products)
    # Per shop: can show, shown before, after the shops' rule, kept, shown before and left
    # out by the shops' rule, the shops' rule's candidates, the category cap's candidates.
    shops: dict[str, list[int]] = {}
    shop_names: dict[str, str] = {}
    categories: dict[str, list[int]] = {}
    by_kind: dict[str, list[int]] = {}
    names: list[str] = []
    for place, product in enumerate(products):
        shop = shop_of(product)
        entry = shops.get(shop)
        if entry is None:
            entry = shops[shop] = [0, 0, 0, 0, 0, 0, 0]
            shop_names[shop] = shop
        # One name held once for all a shop's products: there are over a million of them.
        names.append(shop_names[shop])
        after = True if shop_keep is None else bool(shop_keep[place])
        kept = True if keep is None else bool(keep[place])
        before = bool(pool) and row_key(product) in pool
        entry[0] += 1
        entry[1] += before
        entry[2] += after
        entry[3] += kept
        entry[4] += before and not after
        category = category_of(product)
        found = categories.get(category)
        if found is None:
            found = categories[category] = [0, 0, 0]
        found[0] += 1
        found[1] += after
        found[2] += kept
        for kind in _real(kinds[place]):
            counted = by_kind.get(kind)
            if counted is None:
                counted = by_kind[kind] = [0, 0, 0]
            counted[0] += 1
            counted[1] += after
            counted[2] += kept
    for place in shop_candidates:
        shops[names[place]][5] += 1
    for place in cap_candidates:
        shops[names[place]][6] += 1
    return {
        "products": count,
        "after_the_shops_rule": count if shop_keep is None else sum(1 for kept in shop_keep if kept),
        "kept": count if keep is None else sum(1 for kept in keep if kept),
        "cap_failed": keep is None,
        "pool": len(pool),
        "shops": shops,
        "categories": categories,
        "kinds": by_kind,
    }


def _counting(real: Any, folder: Path) -> Any:
    """`_Cap.__call__` with what it kept counted into `caps.json` beside the catalogue."""

    def call(self: Any, products: Any, kinds: Any, feed_ctx: Any) -> Any:
        began = time.perf_counter()
        keep = real(self, products, kinds, feed_ctx)
        took = time.perf_counter() - began
        try:
            from picwise_providers import checks_applied
            from picwise_providers.catalogue_cap import google_pool_path, read_google_pool

            counts = count_caps(
                products, kinds,
                shop_keep=self.shops.keep if self.shops is not None else None,
                keep=keep,
                pool=read_google_pool(google_pool_path(self.out)),
                shop_candidates=self.shops.candidates if self.shops is not None else (),
                cap_candidates=self.result.candidates if self.result is not None else (),
            )
            counts["gate"] = bool(checks_applied.gate_on())
            counts["gate_off"] = str(self.gate_off or "")
            counts["shops_rule_error"] = str(self.shops_error or "")
            counts["cap_error"] = str(self.error or "")
            counts["seconds"] = {"until_the_caps": round(began - STARTED, 1), "the_caps": round(took, 1),
                                 "counting": round(time.perf_counter() - began - took, 1)}
            (folder / CAPS_NAME).write_text(json.dumps(counts, ensure_ascii=True), encoding="utf-8")
            print(f"look: the caps counted: {counts['products']:,} products a card can show, "
                  f"{counts['after_the_shops_rule']:,} after the shops' rule, {counts['kept']:,} kept; "
                  f"the caps took {took:.0f} s, {began - STARTED:.0f} s after the start", flush=True)
        except Exception as error:  # a look only: the preparation goes on
            print(f"look: the caps could not be counted ({type(error).__name__})", flush=True)
        return keep

    return call


def prepare(folder: Path, arguments: list[str]) -> int:
    """The preparation's own run into `folder`, the caps counted on the way."""
    import os

    import prepare_catalogue as tool
    from picwise_providers.checks_applied import checks_switch_on
    from picwise_providers.kind_itself import gate_on as itself_on
    from picwise_providers.shop_cap import shop_cap_on

    folder.mkdir(parents=True, exist_ok=True)
    print(f"look: the switches as this run reads them: the checks {'on' if checks_switch_on() else 'off'}, "
          f"how many of a shop's products pass {'ON' if shop_cap_on() else 'off'}, "
          f"the kind itself {'on' if itself_on() else 'off'}", flush=True)
    real_call, real_trace = tool._Cap.__call__, tool._trace

    def trace(stage: str) -> None:
        print(f"look: {stage}: {time.perf_counter() - STARTED:.0f} s after the start", flush=True)
        real_trace(stage)

    tool._Cap.__call__, tool._trace = _counting(real_call, folder), trace
    os.environ.setdefault("PICWISE_MEMORY_TRACE", "1")
    try:
        status = tool.main(["--keep-going", "--out", str(folder / CATALOGUE_NAME), "--static-dir", str(folder), *arguments])
    finally:
        tool._Cap.__call__, tool._trace = real_call, real_trace
    print(f"look: the preparation took {time.perf_counter() - STARTED:.0f} s", flush=True)
    if status != 0 or not (folder / CATALOGUE_NAME).is_file():
        print("look: NO CATALOGUE WAS WRITTEN")
        return 1
    return 0


# ---- summary: the catalogue a run wrote, as the site reads it ---------------------------


def _card(product: Any, recommended: bool) -> list[Any]:
    from picwise_providers.catalogue_cap import shop_of

    return [str(product.price_text or ""), _short(product.title), _short(shop_of(product), 24), bool(recommended)]


def _search(query: str, shown: int, prepared: Any, index: Mapping[str, int]) -> dict[str, Any]:
    import look_itself

    found = look_itself.searched(query, shown)
    cards = []
    for product_id in found["cards"]:
        place = index.get(product_id)
        if place is not None:
            cards.append(_card(prepared.products[place], product_id == found["recommended"]))
    return {"q": query, "kind": found["kind"], "total": found["total"], "cards": cards, "error": found["error"]}


def summarize(prepared: Any, *, searches: bool = True) -> dict[str, Any]:
    """What a prepared catalogue shows: products per shop, category and kind; and, searched
    as the site answers (`look_itself.searched`; the catalogue must be the site's of this
    process), every kind by its first name and the 40 searches, their first cards."""
    from picwise_providers.catalogue_cap import category_of, shop_of

    shops: Counter[str] = Counter()
    categories: Counter[str] = Counter()
    kinds: Counter[str] = Counter()
    with_a_kind = 0
    for product, product_kinds in zip(prepared.products, prepared.kinds):
        shops[shop_of(product)] += 1
        categories[category_of(product)] += 1
        real = _real(product_kinds)
        with_a_kind += bool(real)
        kinds.update(real)
    summary: dict[str, Any] = {
        "prepared_at": prepared.prepared_at.isoformat(timespec="seconds"),
        "products": len(prepared.products),
        "with_a_kind": with_a_kind,
        "shops": dict(shops),
        "categories": dict(categories),
        "kinds": dict(kinds),
    }
    if searches:
        from measure_after import SEARCHES
        from picwise_nlu.product_concepts import get_product_concepts

        index = {str(product.provider_product_id): place for place, product in enumerate(prepared.products)}
        began = time.perf_counter()
        summary["kind_searches"] = {
            concept.concept_id: _search(concept.english[0], KIND_CARDS, prepared, index)
            for concept in get_product_concepts() if concept.english
        }
        summary["searches"] = [_search(query, SEARCH_CARDS, prepared, index) for query in SEARCHES]
        summary["searching_seconds"] = round(time.perf_counter() - began, 1)
    return summary


def _json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def summary(folder: Path, *, name: str, gone: str = "", offers: str = "", families: str = "",
            seconds: float = 0.0, peak_kb: int = 0, searches: bool = True) -> int:
    import look_itself

    prepared = look_itself._load(folder / CATALOGUE_NAME, gone=gone, offers=offers, families=families)
    if prepared is None:
        print("look: the catalogue could not be read")
        return 1
    found = summarize(prepared, searches=searches)
    note = _json(folder / NOTE_NAME)
    checks = note.get("checks") if isinstance(note.get("checks"), dict) else {}
    found.update({
        "name": name,
        "seconds": seconds,
        "peak_kb": peak_kb,
        "caps": _json(folder / CAPS_NAME),
        "note": {
            "products": note.get("products"),
            "shops": note.get("shops"),
            "google_pool": note.get("google_pool"),
            # The checks' own note without the bot's long lists.
            "checks": {key: value for key, value in checks.items() if key not in ("bot", "cut_by_shop")},
            "cut_by_shop": checks.get("cut_by_shop"),
        },
    })
    (folder / SUMMARY_NAME).write_text(json.dumps(found, ensure_ascii=False), encoding="utf-8")
    print(f"look: {name}: {found['products']:,} products of {len(found['shops'])} shops, {found['with_a_kind']:,} with a kind,"
          f" {len(found['kinds'])} kinds; written to {SUMMARY_NAME}")
    return 0


# ---- compare ------------------------------------------------------------------------------


def _change(before: int, after: int) -> str:
    return f"{before:>9,} -> {after:>9,} ({after - before:+,})"


def _minutes(seconds: float) -> str:
    return f"{seconds / 60:.1f} min" if seconds else "not measured"


def kinds_compared(before: Mapping[str, int], after: Mapping[str, int]) -> dict[str, Any]:
    """The kinds of two catalogues: how many hold no product, under 4 (a search's first
    page), under 24 and under `THIN`, before and after; the kinds that lose over half."""
    names = sorted(set(before) | set(after))

    def under(counts: Mapping[str, int], limit: int) -> int:
        return sum(1 for name in names if counts.get(name, 0) < limit)

    halved = [name for name in names if before.get(name, 0) and after.get(name, 0) * 2 < before[name]]
    return {
        "kinds": len(names),
        "empty": (under(before, 1), under(after, 1)),
        "under_4": (under(before, 4), under(after, 4)),
        "under_24": (under(before, 24), under(after, 24)),
        "thin": (under(before, THIN), under(after, THIN)),
        "lose_over_half": sorted(halved, key=lambda name: (after.get(name, 0) - before[name], name)),
        "emptied": [name for name in names if before.get(name, 0) and not after.get(name, 0)],
    }


def searches_compared(before: Sequence[Mapping[str, Any]], after: Sequence[Mapping[str, Any]], *,
                      first: int = KIND_CARDS) -> dict[str, Any]:
    """Two runs of the same searches: in how many the first `first` cards, all the cards
    listed, the Recommended or the count of products differ; the ones that lost every card."""
    by_query = {str(item.get("q")): item for item in after}
    same_first = same_all = same_recommended = same_total = both = 0
    emptied: list[str] = []
    changed: list[str] = []
    for item in before:
        other = by_query.get(str(item.get("q")))
        if other is None:
            continue
        both += 1
        mine = [card[:3] for card in item.get("cards") or []]
        theirs = [card[:3] for card in other.get("cards") or []]
        recommended = next((card[:3] for card in item.get("cards") or [] if card[3]), None)
        other_recommended = next((card[:3] for card in other.get("cards") or [] if card[3]), None)
        same_first += mine[:first] == theirs[:first]
        same_all += mine == theirs
        same_recommended += recommended == other_recommended
        same_total += item.get("total") == other.get("total")
        if mine and not theirs:
            emptied.append(str(item.get("q")))
        if mine != theirs:
            changed.append(str(item.get("q")))
    return {"searches": both, "same_first": same_first, "same_cards": same_all, "same_recommended": same_recommended,
            "same_total": same_total, "emptied": emptied, "changed": changed}


def _cards_lines(item: Mapping[str, Any]) -> list[str]:
    return [f"      {'R ' if card[3] else '  '}{card[0]:>9} | {card[1]} | {card[2]}" for card in item.get("cards") or []]


def compare(off: Mapping[str, Any], on: Mapping[str, Any], say: Any = print) -> int:
    """The two runs side by side (module docstring)."""
    off_caps, on_caps = off.get("caps") or {}, on.get("caps") or {}
    off_checks = (off.get("note") or {}).get("checks") or {}
    on_checks = (on.get("note") or {}).get("checks") or {}
    rule = on_checks.get("shop_cap") or {}

    say("== 1. the two preparations")
    for label, run in (("as the site is (the switch off)", off), ("with the rule ON", on)):
        caps = run.get("caps") or {}
        checks = (run.get("note") or {}).get("checks") or {}
        seconds = caps.get("seconds") or {}
        say(f"{label}: {run.get('products', 0):,} products of {len(run.get('shops') or {})} shops, "
            f"{run.get('with_a_kind', 0):,} with a kind; a card can show {caps.get('products', 0):,}, after the shops' rule "
            f"{caps.get('after_the_shops_rule', 0):,}; the pool of the night before {caps.get('pool', 0):,}")
        say(f"    the checks: {'applied, the night of ' + str(checks.get('night')) if checks.get('applied') else 'not applied (' + str(checks.get('why')) + ')'}"
            f"; the cap's gate {'on' if caps.get('gate') else 'off'}"
            + (f"; THE GATE DID NOT STAND: {caps['gate_off']}" if caps.get("gate_off") else "")
            + (f"; THE SHOPS' RULE FAILED: {caps['shops_rule_error']}" if caps.get("shops_rule_error") else "")
            + (f"; THE CAP FAILED: {caps['cap_error']}" if caps.get("cap_error") else ""))
        say(f"    time {_minutes(float(run.get('seconds') or 0))} (to the caps {seconds.get('until_the_caps', 0):,.0f} s, the caps "
            f"{seconds.get('the_caps', 0):,.0f} s); peak memory {int(run.get('peak_kb') or 0) / 1048576:.2f} GB")
    say(f"products: {_change(int(off.get('products') or 0), int(on.get('products') or 0))}; with a kind: "
        f"{_change(int(off.get('with_a_kind') or 0), int(on.get('with_a_kind') or 0))}")

    say("== 2. the shops over the most a shop passes, counted before the cap of a category")
    if rule.get("applied"):
        say(f"the rule (at most {rule.get('limit', 0):,}; a kind thin under {rule.get('thin')}): {rule.get('capped_shops')} shops over it, "
            f"{rule.get('cut', 0):,} of their products left out, candidates {rule.get('candidates', 0):,}")
    else:
        say(f"THE RULE WAS NOT APPLIED in the run with the switch on: {rule.get('why') or rule.get('error') or rule}")
    off_shops, on_shops = off_caps.get("shops") or {}, on_caps.get("shops") or {}
    noted = {str(entry.get("shop")): entry for entry in rule.get("shops") or []}
    capped = [name for name, entry in on_shops.items() if entry[2] < entry[0]]
    say("shop: a card can show | shown the night before | shown now (the switch off) | the rule keeps | then the cap of a"
        " category keeps | shown the night before and left out by the rule | candidates named by the rule")
    for name in sorted(capped, key=lambda name: -on_shops[name][0]):
        entry = on_shops[name]
        before = off_shops.get(name) or [0] * 7
        say(f"  {name}: {entry[0]:,} | {entry[1]:,} | {before[3]:,} | {entry[2]:,} | {entry[3]:,} | {entry[4]:,} | {entry[5]:,}")
        note = noted.get(name)
        if note:
            say("      kept by step: " + ", ".join(f"{step} {count:,}" for step, count in (note.get("kept_by_step") or {}).items() if count)
                + f"; from the night before {note.get('kept_from_before', 0):,}, passed {note.get('kept_passed', 0):,}, "
                f"waiting at the gate {note.get('waiting_at_the_gate', 0):,}")
    say(f"in all, of the {len(capped)} shops: a card can show {sum(on_shops[name][0] for name in capped):,}; shown now "
        f"{sum((off_shops.get(name) or [0] * 7)[3] for name in capped):,}; the rule keeps {sum(on_shops[name][2] for name in capped):,}; "
        f"shown with the rule {sum(on_shops[name][3] for name in capped):,}")

    say("== 3. every shop whose products shown change")
    names = sorted(set(off.get("shops") or {}) | set(on.get("shops") or {}),
                   key=lambda name: ((on.get("shops") or {}).get(name, 0) - (off.get("shops") or {}).get(name, 0), name))
    moved = [name for name in names if (off.get("shops") or {}).get(name, 0) != (on.get("shops") or {}).get(name, 0)]
    for name in moved[:LISTED]:
        say(f"  {_change((off.get('shops') or {}).get(name, 0), (on.get('shops') or {}).get(name, 0))}  {name}")
    if len(moved) > LISTED:
        for name in moved[-LISTED // 2:]:
            say(f"  {_change((off.get('shops') or {}).get(name, 0), (on.get('shops') or {}).get(name, 0))}  {name}")
    gone = [name for name in names if (off.get("shops") or {}).get(name, 0) and not (on.get("shops") or {}).get(name, 0)]
    say(f"shops whose count changes {len(moved)} of {len(names)}; shops left with no product: {', '.join(gone) or 'none'}")

    say("== 4. the categories (the cap of a category): a card can show | kept, the switch off | after the shops' rule | kept, the rule on")
    off_categories, on_categories = off_caps.get("categories") or {}, on_caps.get("categories") or {}
    off_pool, on_pool = (off.get("note") or {}).get("google_pool") or {}, (on.get("note") or {}).get("google_pool") or {}
    say(f"a category keeps at most: {off_pool.get('size')} (the switch off), {on_pool.get('size')} (the rule on); over it: "
        f"{len(off_pool.get('over') or [])} and {len(on_pool.get('over') or [])} categories")
    for name in sorted(set(off_categories) | set(on_categories), key=lambda name: -(off_categories.get(name) or [0])[0])[:LISTED]:
        before, after = off_categories.get(name) or [0, 0, 0], on_categories.get(name) or [0, 0, 0]
        say(f"  {before[0]:>9,} | {before[2]:>7,} | {after[1]:>9,} | {after[2]:>7,}  {name or '(none)'}")
    filled = [name for name in off_categories if (on_categories.get(name) or [0, 0, 0])[2] < off_categories[name][2]]
    say(f"categories that keep fewer with the rule: {len(filled)} of {len(off_categories)}")

    say("== 5. the kinds, before and after")
    kinds = kinds_compared(off.get("kinds") or {}, on.get("kinds") or {})
    say(f"the kinds ({kinds['kinds']}), before and after: with no product {kinds['empty'][0]} and {kinds['empty'][1]}; under 4 products "
        f"{kinds['under_4'][0]} and {kinds['under_4'][1]}; under 24 {kinds['under_24'][0]} and {kinds['under_24'][1]}; under {THIN} "
        f"{kinds['thin'][0]} and {kinds['thin'][1]}; that lose over half {len(kinds['lose_over_half'])}; left with none: "
        f"{', '.join(kinds['emptied']) or 'none'}")
    available = on_caps.get("kinds") or {}
    say("the kinds that lose the most: shown before -> after | of the kind a card can show | of them the shops' rule keeps")
    lost = sorted(set(off.get("kinds") or {}) | set(on.get("kinds") or {}),
                  key=lambda name: ((on.get("kinds") or {}).get(name, 0) - (off.get("kinds") or {}).get(name, 0), name))
    for name in lost[:LISTED]:
        can = available.get(name) or [0, 0, 0]
        say(f"  {_change((off.get('kinds') or {}).get(name, 0), (on.get('kinds') or {}).get(name, 0))} | {can[0]:>8,} | {can[1]:>8,}  {name}")
    say("the kinds that lose over half: " + (", ".join(
        f"{name} {(off.get('kinds') or {}).get(name, 0):,} to {(on.get('kinds') or {}).get(name, 0):,}" for name in kinds["lose_over_half"]) or "none"))
    gained = [name for name in reversed(lost) if (on.get("kinds") or {}).get(name, 0) > (off.get("kinds") or {}).get(name, 0)]
    say("the kinds that gain: " + (", ".join(
        f"{name} {(off.get('kinds') or {}).get(name, 0):,} to {(on.get('kinds') or {}).get(name, 0):,}" for name in gained[:LISTED]) or "none"))

    if off.get("kind_searches") and on.get("kind_searches"):
        say("== 6. every kind searched by its first name, its first 4 cards")
        before = list((off.get("kind_searches") or {}).values())
        after = list((on.get("kind_searches") or {}).values())
        found = searches_compared(before, after)
        say(f"{found['searches']} kinds searched: the same first {KIND_CARDS} cards in {found['same_first']}; the same Recommended in "
            f"{found['same_recommended']}; the same count of products in {found['same_total']}; with cards before and none after: "
            f"{', '.join(found['emptied']) or 'none'}")
        by_query = {str(item.get("q")): item for item in after}
        fewer = sorted(before, key=lambda item: int(by_query.get(str(item.get("q")), {}).get("total") or 0) - int(item.get("total") or 0))
        say("the searches that lose the most products: before -> after")
        for item in fewer[:LISTED]:
            other = by_query.get(str(item.get("q")), {})
            if int(other.get("total") or 0) < int(item.get("total") or 0):
                say(f"  {_change(int(item.get('total') or 0), int(other.get('total') or 0))}  \"{item.get('q')}\"")
        short = [str(item.get("q")) for item in before
                 if len(item.get("cards") or []) >= KIND_CARDS > len(by_query.get(str(item.get("q")), {}).get("cards") or [])]
        say(f"with {KIND_CARDS} cards before and fewer after: {', '.join(short) or 'none'}")

    if off.get("searches") and on.get("searches"):
        say("== 7. the 40 searches, their first 12 cards")
        found = searches_compared(off["searches"], on["searches"])
        say(f"{found['searches']} searches: the same first {KIND_CARDS} cards in {found['same_first']}; the same {SEARCH_CARDS} cards in "
            f"{found['same_cards']}; the same Recommended in {found['same_recommended']}; the same count of products in {found['same_total']}")
        by_query = {str(item.get("q")): item for item in on["searches"]}
        for item in off["searches"]:
            other = by_query.get(str(item.get("q")), {})
            same = [card[:3] for card in item.get("cards") or []] == [card[:3] for card in other.get("cards") or []]
            say(f"  \"{item.get('q')}\" ({item.get('kind') or 'no kind'}): {_change(int(item.get('total') or 0), int(other.get('total') or 0))}"
                + ("; the same cards" if same else "; THE CARDS DIFFER"))
            if not same:
                say("    before:")
                for line in _cards_lines(item):
                    say(line)
                say("    after:")
                for line in _cards_lines(other):
                    say(line)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass
    if not args or args[0] not in ("prepare", "summary", "compare"):
        print(__doc__)
        return 1
    mode, rest = args[0], args[1:]
    if mode == "prepare":
        if not rest:
            print(__doc__)
            return 1
        return prepare(Path(rest[0]), rest[1:])
    if mode == "summary":
        parser = argparse.ArgumentParser(prog="look_shop_rule.py summary")
        parser.add_argument("folder", type=Path)
        parser.add_argument("--name", default="")
        parser.add_argument("--gone", default="")
        parser.add_argument("--offers", default="")
        parser.add_argument("--families", default="")
        parser.add_argument("--seconds", type=float, default=0.0)
        parser.add_argument("--peak-kb", type=int, default=0)
        parser.add_argument("--no-searches", action="store_true")
        found = parser.parse_args(rest)
        return summary(found.folder, name=found.name, gone=found.gone, offers=found.offers, families=found.families,
                       seconds=found.seconds, peak_kb=found.peak_kb, searches=not found.no_searches)
    if len(rest) != 2:
        print(__doc__)
        return 1
    off, on = _json(Path(rest[0])), _json(Path(rest[1]))
    if not off or not on:
        print("look: a summary is missing: " + ", ".join(name for name, found in (("off", off), ("on", on)) if not found))
        return 1
    return compare(off, on)


if __name__ == "__main__":
    sys.exit(main())
