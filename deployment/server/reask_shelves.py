"""The products whose AI line is in doubt, asked again with more care.

Owner, 2026-11-20 (20:51 Athens), after the measure after of the kinds' lists: «Πρώτα
διόρθωση: να ξαναρωτηθεί το AI μόνο για τα περίπου 16.000 προϊόντα (τα 9.304 που βγαίνουν
και τα 6.866 με λάθος κατηγορία) και μετά νέα μέτρηση». The measure (run 44789340760) found
about 3,700 real products hidden: the first scan had put them on a line of the right
department and the wrong branch (car tyres on "Vehicle Hardtops", garden taps on "Taps &
Dies"); and it had given 6,866 products one of the tree's first five lines, a slip
(`ai_shelves.SLIP_LINES`).

Asked again, by their key (`scan_shelves.groups_of`): every product whose line is a slip,
and every product whose line is on none of the lists of the kinds its own words name in the
server's catalogue (`ai_shelves.kind_lists`, `on_list`): the products the lists take out of
a kind. The same question as the scan's, with more care: `shelves.CAREFUL_NOTE`, effort
"medium", fewer products a call (`--per-call`, 30). A key answered again keeps its new line,
the old one beside it ("was"); a key refused again keeps its old answer. Whether a new line
is right is not decided here: the rule reads it as it reads every line, and the measure
after says what it gives.

Written to `--out` (the scan's form: `scan_shelves.write_answers`), all the answers, old and
new. Printed, and kept as GitHub's notes: the keys asked and why, how many answered, the
lines that changed, how many of the products taken out of a kind are now on its list, the
cost. Titles and counts only, never a link or the key.

    python3 deployment/server/reask_shelves.py CATALOGUE.json.gz --answers KEPT.jsonl.gz \
        --out ANSWERS.jsonl.gz [--workers 8] [--budget 1.20] [--stop-after 5400] \
        [--per-call 30] [--limit N] [--dry-run]
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from collections import Counter
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for folder in (ROOT, ROOT / "src", HERE):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

EFFORT = "medium"
PER_CALL = 30


def doubted_keys(
    rows: Iterable[tuple[str, frozenset[str]]],
    lines: Mapping[str, str | None],
    lists: Mapping[str, Any],
) -> dict[str, str]:
    """The keys to ask again and why ("slip" or "taken"), from each product's key and the
    kinds the catalogue reads it as: its line a slip, or its line on none of the lists of
    its real kinds that have one (a kind with no list takes nothing out)."""
    from picwise_providers.ai_shelves import is_slip, on_list

    found: dict[str, str] = {}
    for key, kinds in rows:
        line = lines.get(key)
        if not line or found.get(key) == "slip":
            continue
        if is_slip(line):
            found[key] = "slip"
            continue
        real = [kind for kind in kinds if not kind.startswith("__") and kind in lists]
        if real and not all(on_list(line, lists[kind]) for kind in real):
            found.setdefault(key, "taken")
    return found


def settle(
    asked: Iterable[str],
    before: Mapping[str, dict[str, Any]],
    answers: dict[str, dict[str, Any]],
    today: str,
) -> Counter[str]:
    """After the asking: a key answered again keeps the new line with the old beside it; a
    key refused again, or not asked by a limit, keeps its old answer. The tally."""
    tally: Counter[str] = Counter()
    for key in asked:
        old = before.get(key)
        new = answers.get(key)
        if old is None:
            continue
        if new is None or new is old or new.get("line") is None:
            answers[key] = old
            tally["kept (refused or not asked)"] += 1
            continue
        new = dict(new)
        new["was"] = old.get("line")
        new["again"] = today
        answers[key] = new
        tally["the same line" if new.get("line") == old.get("line") else "another line"] += 1
    return tally


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("catalogue", type=Path)
    parser.add_argument("--answers", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--budget", type=float, default=1.20)
    parser.add_argument("--stop-after", type=float, default=5400.0, help="seconds")
    parser.add_argument("--per-call", type=int, default=PER_CALL)
    parser.add_argument("--limit", type=int, default=0, help="ask at most so many keys")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass

    from picwise_ai.shelves import request_kwargs, taxonomy_lines
    from picwise_providers.ai_shelves import key_of, kind_lists, on_list
    from picwise_providers.prepared_catalogue import read_prepared_catalogue_to_measure
    from scan_shelves import Asking, Notices, _Recording, groups_of, read_answers, report_totals, run_round, write_answers

    began = time.monotonic()
    lines = taxonomy_lines()
    prepared = read_prepared_catalogue_to_measure(args.catalogue)
    if prepared is None or not lines:
        print("the copy is not a prepared catalogue, or no taxonomy: nothing to ask")
        return 1
    products = prepared.products
    groups = groups_of(products, lines)
    answers = read_answers(args.answers)
    before = dict(answers)
    product_keys = [key_of(str(product.title or ""), str(product.brand or ""), product.raw) for product in products]
    lists = kind_lists()
    why = doubted_keys(
        zip(product_keys, prepared.kinds),
        {key: record.get("line") for key, record in answers.items()},
        lists,
    )
    # The kinds each key's products are read as, to say after whether the new line keeps them.
    kinds_of: dict[str, set[str]] = {}
    count_of: Counter[str] = Counter()
    for key, kinds in zip(product_keys, prepared.kinds):
        if key in why:
            count_of[key] += 1
            kinds_of.setdefault(key, set()).update(kind for kind in kinds if not kind.startswith("__") and kind in lists)
    del prepared
    keys = sorted((key for key in why if key in groups), key=lambda key: (-count_of[key], key))
    if args.limit:
        keys = keys[: args.limit]
    reasons = Counter(why[key] for key in keys)
    products_asked = sum(count_of[key] for key in keys)
    notices = Notices()
    notices.say(
        "start",
        f"{len(products):,} products, {len(answers):,} answers kept; to ask again {len(keys):,} keys "
        f"({products_asked:,} products): a slip {reasons['slip']:,} keys "
        f"({sum(count_of[key] for key in keys if why[key] == 'slip'):,} products), taken out of a kind "
        f"{reasons['taken']:,} keys ({sum(count_of[key] for key in keys if why[key] == 'taken'):,} products); "
        f"{args.per_call} a call, effort {EFFORT}, budget ${args.budget:.2f}, {args.workers} at a time",
    )
    if args.dry_run or not os.environ.get("ANTHROPIC_API_KEY") or not keys:
        print("not asked: " + ("--dry-run" if args.dry_run else "nothing to ask" if not keys else "no ANTHROPIC_API_KEY"))
        if not args.dry_run:
            write_answers(args.out, answers)
        return 0

    from picwise_ai.client import ask, make_client

    client = _Recording(make_client(timeout=240.0, max_retries=3))

    def ask_fn(request: dict[str, Any]) -> tuple[Any, str]:
        asked = ask(request, client=client)
        return asked, client.message

    def careful(items, lines_):
        return request_kwargs(items, lines_, effort=EFFORT, careful=True)

    asking = Asking(
        ask_fn=ask_fn,
        groups=groups,
        answers=answers,
        lines=lines,
        workers=max(1, args.workers),
        budget=args.budget,
        deadline=time.monotonic() + args.stop_after,
        out=None,
        notices=notices,
        request_fn=careful,
    )
    failed = run_round(asking, keys, args.per_call, label="asked again")
    again = list(dict.fromkeys(failed))
    if again and not asking.totals.stopped:
        run_round(asking, again, max(1, args.per_call // 2), label="asked a second time")
    today = datetime.now(timezone.utc).date().isoformat()
    tally = settle(keys, before, answers, today)
    write_answers(args.out, answers)

    from picwise_providers.ai_shelves import is_slip

    outcome: Counter[str] = Counter()
    for key in keys:
        record = answers.get(key) or {}
        if "was" not in record:
            outcome[f"{why[key]}: kept the old answer"] += count_of[key]
            continue
        line = record.get("line") or ""
        if why[key] == "slip":
            outcome["slip: a real line now" if line and not is_slip(line) else "slip: a slip or no line again"] += count_of[key]
        else:
            kinds = kinds_of.get(key, set())
            if line and kinds and all(on_list(line, lists[kind]) for kind in kinds):
                outcome["taken: now on its kinds' lists"] += count_of[key]
            else:
                outcome["taken: still off a kind's list"] += count_of[key]
    done = [
        *report_totals(asking, began, sum(1 for key in keys if asking.tries[key] == 0)),
        "keys: " + ", ".join(f"{name} {count:,}" for name, count in tally.most_common()),
        "products: " + ", ".join(f"{name} {count:,}" for name, count in sorted(outcome.items())),
    ]
    notices.say("asked again", "\n".join(done), final=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
