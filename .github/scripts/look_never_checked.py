"""A read-only look at the products the checks hold as "never checked" (owner, 26/11).

The morning of 26/11 (PROGRESS.md, 26/11 08:20) the site fell from 148,362 products to
111,503: the night of 26/11, the first recorded by the code deployed on 25/11, held 40,562
shown products as "never checked" (the checks' rules 9.3), none the night before. Asked
whether to look, read-only, at which shops and products they are, whether the ledger knows
them under another key, and whether they were shown on 24/11, the owner said «ναι» (26/11,
11:38 Athens).

Run on the server as the site's user by .github/workflows/server-look-never-checked.yml, in
a unit that can write nowhere: the standard library only, every file opened to read, the
catalogue's memory as an unchanging file. It reads the checks' ledger, decisions, note and
candidates, the answers the bot keeps today, and the catalogue's memory. It prints counts,
dates and shop names only, never a key, an id, an address or a title: the log is public, as
the repository is.

    python3 look_never_checked.py [--root /srv/picwise/shared]
"""
from __future__ import annotations

import gc
import glob
import gzip
import html
import json
import os
import sqlite3
import sys
import unicodedata
from collections import Counter, defaultdict

ROOT = "/srv/picwise/shared"
if len(sys.argv) > 2 and sys.argv[1] == "--root":  # a copy, for a test; the server's by default
    ROOT = sys.argv[2]
CHECKS = os.path.join(ROOT, "checks")
LEDGER = os.path.join(CHECKS, "ledger.json.gz")
DECISIONS = os.path.join(CHECKS, "decisions.json.gz")
NOTE = os.path.join(CHECKS, "note.json")
CANDIDATES = os.path.join(CHECKS, "candidates.json.gz")
MEMORY = os.path.join(ROOT, "prepared", "catalogue_memory.sqlite")

# `catalogue_memory.history_key`: the shop as the feed's row names it, then its id.
SEP = "\x1f"
NEVER = "never checked"
# The nights looked at: the checks' first recorded night (23/11) and the ones around it.
DAYS = ("2026-11-21", "2026-11-22", "2026-11-23", "2026-11-24", "2026-11-25", "2026-11-26")
TOP = 25
SEEN_BITS = 62

# `picwise_checks.ledger.Product`, its fields in order (a product is kept as a list).
STATE, ASKED, FAILS, PASSED_ON = 1, 3, 4, 7


def say(line: str = "") -> None:
    print(line, flush=True)


def load_gz(path: str):
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def read_json(path: str):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def shop_of(key: str) -> str:
    return key.split(SEP, 1)[0]


def id_of(key: str) -> str:
    return key.split(SEP, 1)[1] if SEP in key else ""


def name_key(name: str) -> str:
    """`picwise_checks.ledger.shop_name_key`: a shop's name as two sources may write it."""
    return " ".join(unicodedata.normalize("NFKC", html.unescape(str(name or ""))).casefold().split())


def field(values, place, default=""):
    return values[place] if isinstance(values, list) and len(values) > place else default


def decided_once(values) -> bool:
    """`picwise_checks.ledger._decided_once`: passed once, failed once, or failed or held now."""
    try:
        fails = int(field(values, FAILS, 0) or 0)
    except (TypeError, ValueError):
        fails = 0
    return bool(field(values, PASSED_ON)) or fails > 0 or field(values, STATE) in ("failed", "held")


def top(counter: Counter, count: int = TOP) -> str:
    return ", ".join(f"{name} {number:,}" for name, number in counter.most_common(count)) or "none"


def dated(counter: Counter) -> str:
    return ", ".join(f"{name} {number:,}" for name, number in sorted(counter.items())) or "none"


def short(day: str) -> str:
    return day[8:10] + "/" + day[5:7] if len(day) == 10 else day


def main() -> int:
    say("A read-only look at the products held as never checked; counts, dates and shop names only.")

    # ---- the decisions the preparation of 26/11 read -------------------------------------
    decisions = load_gz(DECISIONS)
    wait = decisions.get("wait") or {}
    reasons = Counter(str(why) for why in wait.values())
    never = sorted(key for key, why in wait.items() if why == NEVER)
    never_set = frozenset(never)
    by_shop = Counter(shop_of(key) for key in never)
    say()
    say(f"1. The decisions of the night of {decisions.get('night')}: cut {len(decisions.get('cut') or {}):,}, "
        f"not shown until checked {len(wait):,} ({top(reasons)}), may enter {len(decisions.get('enter') or []):,}, "
        f"shops out {len(decisions.get('shops_out') or {})}")
    say(f"   never checked: {len(never):,} products of {len(by_shop)} shops")
    say(f"   by shop: {top(by_shop, 60)}")
    del decisions, wait
    gc.collect()

    note = read_json(NOTE) or {}
    rule = note.get("shop_rule") or {}
    asked_by_shop = note.get("asked_by_shop") or {}
    seconds_by_shop = note.get("seconds_by_shop") or {}
    say(f"   the bot's note of that night: {note.get('shops_asked')} shops asked, decided {int(note.get('decided') or 0):,}; "
        f"the round asked {rule.get('round_hours')} hours, all day: {rule.get('whole_round')}; "
        f"shops asked whole {rule.get('asked_whole')}")

    # ---- the ledger -------------------------------------------------------------------------
    ledger = load_gz(LEDGER)
    products = ledger.get("products") or {}
    shops = ledger.get("shops") or {}
    nights = ledger.get("nights") or []
    say()
    say(f"2. The ledger (written {ledger.get('written_at')}): {len(products):,} products, {len(shops)} shops")
    say("   its nights: " + ", ".join(f"{entry.get('night')}" + (" (ours)" if entry.get("ours") else "")
                                      for entry in nights[-12:]))
    say("   shops by their first night: "
        + dated(Counter(str(shop.get("first_night") or "none") for shop in shops.values())))
    say("   shops by the night their first round ended: "
        + dated(Counter(str(shop.get("round_over") or "not ended") for shop in shops.values())))
    say("   the never checked, by their shop's first night: "
        + dated(Counter(str((shops.get(shop_of(key)) or {}).get("first_night") or "none") for key in never)))
    say("   the never checked, by the night their shop's first round ended: "
        + dated(Counter(str((shops.get(shop_of(key)) or {}).get("round_over") or "not ended") for key in never)))

    never_ids = {id_of(key) for key in never}
    known_undecided: Counter = Counter()
    known_by_shop: Counter = Counter()
    decided_by_shop: Counter = Counter()
    same_id: dict[str, list] = defaultdict(list)
    decided_keys: set[str] = set()
    for key, values in products.items():
        decided = decided_once(values)
        if decided:
            decided_keys.add(key)
            decided_by_shop[shop_of(key)] += 1
        if key in never_set:
            known_undecided[str(field(values, ASKED)) or "never asked"] += 1
            known_by_shop[shop_of(key)] += 1
            continue
        ident = id_of(key)
        if ident in never_ids:
            same_id[ident].append((shop_of(key), decided))
    del ledger, products
    gc.collect()
    known = sum(known_undecided.values())
    say()
    say(f"3. Does the ledger know them? In it but never decided (asked, no verdict): {known:,}; "
        f"not in it at all: {len(never) - known:,}")
    say(f"   of those in it, by the night last asked: {dated(known_undecided)}")
    if known:
        say(f"   in it but never decided, by shop: {top(known_by_shop, 15)}")
    under_other = Counter()
    under_other_decided = 0
    written_otherwise = 0
    pairs: Counter = Counter()
    for key in never:
        shop, ident = shop_of(key), id_of(key)
        found = [(other, decided) for other, decided in same_id.get(ident, ()) if other != shop]
        if not found:
            continue
        under_other[shop] += 1
        under_other_decided += any(decided for _other, decided in found)
        written_otherwise += any(name_key(other) == name_key(shop) for other, _decided in found)
        pairs[f"{shop} -> {found[0][0]}"] += 1
    say(f"   the same id under another shop's name: {sum(under_other.values()):,} "
        f"(decided there {under_other_decided:,}; the same shop's name written otherwise {written_otherwise:,})")
    if pairs:
        say(f"   which names: {top(pairs, 10)}")

    # ---- the catalogue's memory -----------------------------------------------------------------
    db = sqlite3.connect(f"file:{MEMORY}?mode=ro&immutable=1", uri=True)
    prepared = db.execute("SELECT night, prepared_at, kept FROM nights ORDER BY night").fetchall()
    order = [night for night, _at, _kept in prepared]
    place = {night: index for index, night in enumerate(order)}
    say()
    say("4. The catalogue's memory (what the site showed each night; a night prepared twice counts once): "
        + ", ".join(f"{short(night)} {kept:,} (last at {str(at)[11:16]})" for night, at, kept in prepared[-8:]))

    def seen_nights(last: str, mask) -> set:
        where = place.get(last)
        if where is None or mask is None:
            return {last}
        return {order[where - bit] for bit in range(SEEN_BITS) if (int(mask) >> bit) & 1 and where - bit >= 0}

    their_shops = set(by_shop)
    mine: dict[str, tuple] = {}
    by_code: dict[tuple, list] = defaultdict(list)
    by_title: dict[tuple, list] = defaultdict(list)
    for key, shop, gtin, title, first, last, count, mask in db.execute(
            "SELECT key, shop, gtin, title, first_seen, last_seen, nights_seen, seen_nights FROM products"):
        if key in never_set:
            mine[key] = (gtin, title, first, last, count, mask)
        elif shop in their_shops:
            if gtin:
                by_code[(shop, gtin)].append(key)
            if title:
                by_title[(shop, title)].append(key)
    seen_on: Counter = Counter()
    first_seen: Counter = Counter()
    last_seen: Counter = Counter()
    how_many: Counter = Counter()
    shown_before_by_shop: Counter = Counter()
    new_by_shop: Counter = Counter()
    same_code_decided = same_title_decided = with_code = 0
    for key in never:
        row = mine.get(key)
        if row is None:
            continue
        gtin, title, first, last, count, mask = row
        first_seen[first] += 1
        last_seen[last] += 1
        seen = seen_nights(last, mask)
        for day in DAYS:
            seen_on[day] += day in seen
        how_many["1 night" if count == 1 else "2-3 nights" if count <= 3 else "4-7 nights" if count <= 7
                 else "8 nights or more"] += 1
        if "2026-11-24" in seen:
            shown_before_by_shop[shop_of(key)] += 1
        if first >= "2026-11-25":
            new_by_shop[shop_of(key)] += 1
        shop = shop_of(key)
        if gtin:
            with_code += 1
            same_code_decided += any(other in decided_keys for other in by_code.get((shop, gtin), ()))
        if title:
            same_title_decided += any(other in decided_keys for other in by_title.get((shop, title), ()))
    say(f"   the never checked in the memory: {len(mine):,} of {len(never):,}")
    say("   shown on: " + ", ".join(f"{short(day)} {seen_on[day]:,}" for day in DAYS))
    say(f"   first shown: {dated(first_seen)}")
    say(f"   last shown: {dated(last_seen)}")
    say(f"   how many nights shown: {dated(how_many)}")
    say(f"   first shown on 25/11 or after, by shop: {top(new_by_shop, 15)}")
    say(f"   another product of the same shop with the same barcode, decided by the checks: {same_code_decided:,} "
        f"(of {with_code:,} with a barcode)")
    say(f"   another product of the same shop with the same title, decided by the checks (sizes and colours of one "
        f"product share it): {same_title_decided:,}")
    del by_code, by_title, mine
    gc.collect()

    kept: dict[str, dict[str, int]] = defaultdict(dict)
    for shop, night, _rows, _shown, count in db.execute(
            "SELECT shop, night, rows, shown, kept FROM shop_nights WHERE night >= ?", (DAYS[0],)):
        kept[shop][night] = count
    db.close()

    # ---- what the bot asks of them today ---------------------------------------------------
    named = set()
    written_at = None
    try:
        candidates = load_gz(CANDIDATES)
        named = set(candidates.get("candidates") or ())
        written_at = candidates.get("written_at")
        del candidates
    except (OSError, ValueError):
        pass
    named_of_them: Counter = Counter(shop_of(key) for key in never if key in named)
    say()
    say(f"5. Named for the bot today (written {written_at}): {len(named):,} candidates; of them never checked last "
        f"night {sum(named_of_them.values()):,}: {top(named_of_them, 15)}")
    asked_today: Counter = Counter()
    read_today = 0
    for path in sorted(glob.glob(os.path.join(CHECKS, "tonight-*.jsonl"))):
        answers = 0
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                answers += 1
                key = str(record.get("key"))
                if key in never_set:
                    asked_today[shop_of(key)] += 1
                    read_today += bool(record.get("p"))
        hours = read_json(path[: -len(".jsonl")] + ".time.json") or {}
        say(f"   {os.path.basename(path)}: {answers:,} answers so far, "
            f"{float(hours.get('seconds') or 0) / 3600:.1f} hours asked")
    say(f"   of the never checked, asked again today: {sum(asked_today.values()):,} (their product read on the page "
        f"{read_today:,}; the verdicts are given at 03:05 UTC): {top(asked_today, 15)}")

    # ---- each shop ----------------------------------------------------------------------------
    say()
    say(f"6. Each shop with the most never checked (kept by night: what the site showed of it)")
    for shop, count in by_shop.most_common(TOP):
        entry = shops.get(shop) or {}
        asked = asked_by_shop.get(shop) or [0, 0, ""]
        spent = seconds_by_shop.get(shop) or [0, 0]
        say(f"   {shop}: never checked {count:,} (shown on 24/11 {shown_before_by_shop[shop]:,}); decided in the ledger "
            f"{decided_by_shop[shop]:,}; first night {entry.get('first_night') or '-'}, first round ended "
            f"{entry.get('round_over') or '-'}, asked whole {entry.get('complete_on') or 'never'}"
            + (f", out: {entry.get('out')}" if entry.get("out") else "")
            + f"; the night of 26/11 asked {int(asked[0] or 0):,} requests, {int(asked[1] or 0):,} answers"
            + (f", stopped: {asked[2]}" if len(asked) > 2 and asked[2] else "")
            + f", {float(spent[0] or 0) / 3600:.1f} h"
            + "; kept " + ", ".join(f"{short(day)} {kept[shop].get(day, 0):,}" for day in DAYS))
    say()
    say("The look changed nothing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
