"""The look at the checks' bot before the «ανέβασε» of how many of a shop's products pass.

The checks' rules 19.7.1 and 19.5 (`docs/PICWISE_CHECKS_RULES.md`): run on the server by
`.github/workflows/server-look-shop-rule.yml`, as the site's user, inside the limits the
bot's own unit has (`picwise-checks.service`: its sandbox and its memory), from a copy of
this commit's code unpacked in the unit's private temporary folder, which goes with the
unit. **No shop is asked and nothing is written**: the checks' real round goes on beside it
undisturbed.

    python3 deployment/server/look_bot_rule.py [--catalogue PATH] [--checks DIR] [--processes 4]

What it says:

1. whether the processes the pages are read on start inside the unit's sandbox (19.5), and
   read a page each (a page of this file's own, made up);
2. the prepared catalogue read as the bot reads it with the rule on, the order of 19.4
   worked out (`shop_cap.shop_order`): how long it takes;
3. what the bot would ask of each shop tonight, with the rule off and on
   (`ledger.asking_order`), from the ledger as it is;
4. what the decisions would not show until checked, a pass counting for 30 nights and for
   3 (`ledger.decisions`), from the ledger as it is: nothing is recorded;
5. what the round running has answered so far, per shop (the night's own file, read only);
6. the memory all of it took, against the unit's 4 GB.

Printed: counts and shop names only; never an address, an id or a key.
"""
from __future__ import annotations

import argparse
import json
import os
import resource
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for _folder in (ROOT, ROOT / "src", ROOT / "deployment" / "bot", HERE):
    if str(_folder) not in sys.path:
        sys.path.insert(0, str(_folder))

SHOPS_LISTED = 45
# A product page of this file's own: what a shop's page says of a product, made up.
PAGE = (
    b'<html><head><title>Fixturon Kettle 1</title><script type="application/ld+json">'
    b'{"@context":"https://schema.org","@type":"Product","name":"Fixturon Kettle 1","sku":"FX-1",'
    b'"gtin13":"5000000000017","offers":{"@type":"Offer","price":"19.99","priceCurrency":"GBP",'
    b'"availability":"https://schema.org/InStock"}}</script></head><body>Fixturon Kettle 1</body></html>'
)


def _mb(kilobytes: int) -> str:
    return f"{kilobytes / 1024:,.0f} MB"


def memory_lines() -> list[str]:
    """This process's peak, its children's, and the unit's own count when it can be read."""
    lines = [f"this process's peak {_mb(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)}; "
             f"its ended children's largest {_mb(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)}"]
    try:
        group = Path("/proc/self/cgroup").read_text(encoding="utf-8").strip().rsplit("::", 1)[-1]
        base = Path("/sys/fs/cgroup") / group.lstrip("/")
        found = []
        for name in ("memory.current", "memory.peak", "memory.high", "memory.max"):
            try:
                value = (base / name).read_text(encoding="utf-8").strip()
            except OSError:
                continue
            found.append(f"{name} {int(value) / 1048576:,.0f} MB" if value.isdigit() else f"{name} {value}")
        if found:
            lines.append("the unit: " + ", ".join(found))
    except OSError:
        pass
    return lines


def _pid_after(seconds: float) -> int:
    """A reader's own process id, after it was busy for `seconds`: so that as many readers
    as are asked at once must answer (the pool starts a process only when none is idle)."""
    time.sleep(seconds)
    return os.getpid()


def try_readers(readers: Any, pages: int = 8) -> str:
    """`pages` made-up pages read through `readers`, and where: how many processes other
    than the bot's own answer when as many as the readers are asked at once."""
    from picwise_checks.page_reader import read_page_bytes

    read = [readers._read(read_page_bytes, PAGE, "text/html; charset=utf-8") for _page in range(pages)]
    found = sum(1 for page in read if getattr(page, "found", False))
    pool = readers.pool
    if pool is None:
        return f"{found} of {pages} pages read, on the bot's own process"
    asked = [pool.submit(_pid_after, 0.5) for _reader in range(readers.processes)]
    others = {future.result(timeout=120) for future in asked} - {os.getpid()}
    return f"{found} of {pages} pages read; {len(others)} of {readers.processes} processes other than the bot's answered at once"


def tonight_counts(checks: Path, shop_of: dict[str, str]) -> list[str]:
    """What the round running has kept so far (`tonight-<night>.jsonl`), per shop."""
    lines: list[str] = []
    for path in sorted(checks.glob("tonight-*.jsonl")):
        per_shop: dict[str, Counter] = {}
        answers = unknown = 0
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                try:
                    record = json.loads(line)
                    key = str(record["key"])
                except (ValueError, KeyError, TypeError):
                    continue
                answers += 1
                shop = shop_of.get(key)
                if shop is None:
                    unknown += 1
                    continue
                counts = per_shop.setdefault(shop, Counter())
                status = record.get("s") or 0
                counts["answers"] += 1
                if record.get("k"):
                    counts["in its catalogue"] += 1
                elif record.get("c"):
                    counts["a wall"] += 1
                elif status == 200:
                    counts["a page"] += 1
                elif status in (404, 410):
                    counts["gone"] += 1
                elif status in (401, 403, 429):
                    counts["refused"] += 1
                else:
                    counts["no answer or another"] += 1
        stat = path.stat()
        age = time.time() - stat.st_mtime
        lines.append(f"{path.name}: {answers:,} answers of {len(per_shop)} shops, {stat.st_size / 1048576:,.0f} MB, "
                     f"last written {age:,.0f} s ago; of rows this catalogue does not hold {unknown:,}")
        lines.append("  shop: answers (in its catalogue, a page, gone, refused, a wall, no answer or another)")
        for shop, counts in sorted(per_shop.items(), key=lambda item: -item[1]["answers"])[:SHOPS_LISTED]:
            lines.append(f"  {shop}: {counts['answers']:,} ({counts['in its catalogue']:,}, {counts['a page']:,}, {counts['gone']:,}, "
                         f"{counts['refused']:,}, {counts['a wall']:,}, {counts['no answer or another']:,})")
    return lines or ["no file of a round running"]


def main(argv: list[str] | None = None) -> int:
    import shop_checks_bot as bot
    from picwise_checks import ledger as L
    from picwise_providers.shop_cap import SHOP_LIMIT, shop_cap_on

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--catalogue", type=Path, default=Path(bot.PREPARED))
    parser.add_argument("--checks", type=Path, default=Path(bot.CHECKS_DIR))
    parser.add_argument("--processes", type=int, default=bot.PROCESSES)
    args = parser.parse_args(argv)
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass
    say = print
    began = time.perf_counter()
    say(f"== the look at the bot, {datetime.now(timezone.utc).isoformat(timespec='seconds')}; the switch in this copy of the"
        f" code: {'on' if shop_cap_on() else 'off'} (the look reads the rule both ways)")

    say("== 1. the processes the pages are read on (19.5)")
    readers = bot.Readers.start(args.processes, say)
    try:
        try:
            say(try_readers(readers))
        except Exception as error:  # a look only
            say(f"the pages could not be read through the processes ({type(error).__name__})")

        say("== 2. the catalogue read as the bot reads it, the order of 19.4 worked out")
        at = time.perf_counter()
        try:
            rows, parts, _shared, orders = bot.rows_from_catalogue(args.catalogue, order=True)
        except ValueError as error:
            say(f"{error}; the look ends here")
            return 0
        shown = set(rows)
        by_shop = Counter(row.shop for row in rows.values())
        say(f"{len(shown):,} products shown, of {len(by_shop)} shops; read and ordered in {time.perf_counter() - at:.0f} s; "
            f"the order names {sum(len(keys) for keys in orders.values()):,} products of {len(orders)} shops")
        for line in memory_lines():
            say(line)
        extra, candidates = bot.rows_from_candidates(args.checks / L.CANDIDATES_NAME)
        for key, row in extra.items():
            rows.setdefault(key, row)
        ledger = L.load(args.checks / L.LEDGER_NAME)
        night = bot._deadline(datetime.now(timezone.utc), bot.UNTIL).date()
        say(f"the night of {night}: {len(candidates):,} candidates, {len(extra) - len(candidates):,} cut ones the feed still lists; "
            f"the ledger: {len(ledger.products):,} products, {len(ledger.shops)} shops, nights recorded "
            + (", ".join(str(entry.get("night")) for entry in ledger.nights[-5:]) or "none"))

        say("== 3. what the bot would ask tonight: the rule off, the rule on (at most 20,000 of a shop past the failed due)")
        at = time.perf_counter()
        off = L.asking_order(ledger, night, rows, shown=shown, candidates=candidates, parts=parts)
        on = L.asking_order(ledger, night, rows, shown=shown, candidates=candidates, parts=parts, scanned=True,
                            shown_order=orders, limit=SHOP_LIMIT)
        say(f"in all: {sum(len(keys) for keys in off.values()):,} products of {len(off)} shops, the rule off; "
            f"{sum(len(keys) for keys in on.values()):,} of {len(on)} shops, the rule on; worked out in {time.perf_counter() - at:.0f} s")
        say("  shop: shown | to ask, the rule off | to ask, the rule on | of them shown | of them the same first 100")
        for shop, count in by_shop.most_common(SHOPS_LISTED):
            first, second = off.get(shop, []), on.get(shop, [])
            say(f"  {shop}: {count:,} | {len(first):,} | {len(second):,} | {sum(1 for key in second if key in shown):,} | "
                f"{len(set(first[:100]) & set(second[:100]))}")

        say("== 4. what the decisions would not show until checked, from the ledger as it is")
        yes = bot.owner_yes()
        for nights, over in ((L.PASS_VALID_NIGHTS, 0), (L.PASS_NIGHTS_SCANNED, SHOP_LIMIT)):
            made = L.decisions(ledger, night, rows, shown=shown, candidates=candidates, old_feed_rule=yes["old_feed_rule"],
                               pass_nights=nights, passed_over=over)
            waits = Counter(made["wait"].values())
            by = Counter(rows[key].shop for key, why in made["wait"].items() if why == L.NOT_PASSED_IN_THREE)
            say(f"a pass counts for {nights} nights: shops out {len(made['shops_out'])}, cut {len(made['cut']):,}, not shown until "
                f"checked {sum(waits.values()):,}"
                + (" (" + ", ".join(f"{why} {count:,}" for why, count in sorted(waits.items())) + ")" if waits else "")
                + f", may enter {len(made['enter']):,}"
                + (f", named as passed {len(made.get('passed') or ()):,}" if over else ""))
            if by:
                say("  not passed in 3 nights, by shop: " + ", ".join(f"{shop} {count:,}" for shop, count in by.most_common(20)))

        say("== 5. what the round running has answered so far")
        for line in tonight_counts(args.checks, {key: row.shop for key, row in rows.items()}):
            say(line)

        say("== 6. the memory, against the unit's 4 GB (MemoryHigh) and 5 GB (MemoryMax)")
        for line in memory_lines():
            say(line)
    finally:
        readers.close()
    say(f"the look took {time.perf_counter() - began:.0f} s; no shop was asked, nothing was written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
