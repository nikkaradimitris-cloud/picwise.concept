"""The service `picwise-shelves`: each morning, the AI's line of Google's taxonomy for the
products not asked yet (the checks' rules 5.5 and 7.6; owner, 2026-11-21: «Το AI ρωτιέται
μία φορά για την κατηγορία κάθε προϊόντος. Όποιο προϊόν δεν μπαίνει σε κατηγορία βγαίνει»).

Run by `picwise-shelves.service` after the night's preparation, under the AI layer's own
user, with the Anthropic SDK of its own environment and the key in its environment only
(`/etc/picwise/assist.env`), never the site's. It reads the products the preparation names
(`jobs/shelves.jsonl.gz`, `checks_applied.shelf_items`: those the catalogue shows, or the
cap would take next, that the AI has not answered), asks them as the scan of 20/11 asked
every product (`scan_shelves.scan`: 50 a call, two rounds, every answer checked, a key
refused twice kept as refused), and keeps the answers in the file the preparation reads
(`answers.jsonl.gz`), written whole and then put in place. A new product enters the next
night only once answered with a line; one with none is cut (`checks_applied`).

It stops for the night before passing $10 (the rules 7.6: a brake for a loop gone wrong,
not a budget; a night's need is cents) and after 2 hours; what it did not ask waits for
the next morning. Its note (`night.json`: counts and the cost, never a product) is read by
the morning's health run, which tells a stop at the $10.

    shelves_service.py --dir /srv/picwise/assist/shelves [--budget 10] [--stop-after 7200]
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
for folder in (ROOT, ROOT / "src", Path(__file__).resolve().parent):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import scan_shelves  # noqa: E402  (the scan of 20/11: its rounds, checks and limits)

JOB_NAME = "shelves.jsonl.gz"
ANSWERS_NAME = "answers.jsonl.gz"
NOTE_NAME = "night.json"
BUDGET_USD = 10.0
STOP_AFTER_SECONDS = 7200.0
WORKERS = 4


def read_job(path: Path) -> dict[str, scan_shelves.Group]:
    """The products named, as the scan's groups: one a key, shown to the AI as its item."""
    groups: dict[str, scan_shelves.Group] = {}
    try:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for text in handle:
                try:
                    item = json.loads(text)
                except ValueError:
                    continue
                if not isinstance(item, dict) or not isinstance(item.get("k"), str) or item["k"] in groups:
                    continue
                groups[item["k"]] = scan_shelves.Group(
                    key=item["k"],
                    item={name: item.get(name) or "" for name in ("title", "brand", "price", "category", "about")},
                    shop=str(item.get("shop") or ""),
                    title=str(item.get("title") or ""),
                    second=False,
                    shelf_now="",
                    products=int(item.get("products") or 1),
                )
    except (OSError, EOFError, gzip.BadGzipFile):
        return {}
    return groups


def write_note(directory: Path, note: dict[str, Any]) -> None:
    target = directory / NOTE_NAME
    temporary = target.with_name(target.name + ".part")
    temporary.write_text(json.dumps(note, indent=1, sort_keys=True), encoding="utf-8")
    os.replace(temporary, target)


def run(
    directory: Path,
    *,
    ask_fn: Callable[[dict[str, Any]], tuple[Any, str]],
    lines: Any,
    budget: float = BUDGET_USD,
    stop_after: float = STOP_AFTER_SECONDS,
    workers: int = WORKERS,
    today: str | None = None,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """One morning's asking; its note (also written as `NOTE_NAME`)."""
    today = today or datetime.now(timezone.utc).date().isoformat()
    job = directory / "jobs" / JOB_NAME
    answers_path = directory / ANSWERS_NAME
    groups = read_job(job)
    answers = scan_shelves.read_answers(answers_path)
    keys = scan_shelves.to_ask(groups, answers)
    note: dict[str, Any] = {"night": today, "named": len(groups), "asked": len(keys), "calls": 0, "answered": 0,
                            "no_line_fits": 0, "refused": 0, "left": 0, "cost_usd": 0.0, "stopped": ""}
    if keys:
        asking = scan_shelves.Asking(
            ask_fn=ask_fn, groups=groups, answers=answers, lines=lines, workers=max(1, workers), budget=budget,
            deadline=clock() + stop_after, out=answers_path, clock=clock, sleep=sleep, today=today,
            notices=scan_shelves.Notices(enabled=False),
        )
        from picwise_ai.shelves import PER_CALL

        unasked = scan_shelves.scan(asking, keys, PER_CALL)
        scan_shelves.write_answers(answers_path, answers)
        totals = asking.totals
        note.update({"calls": totals.calls, "answered": totals.answered, "no_line_fits": totals.no_line,
                     "refused": sum(1 for key in keys if (answers.get(key) or {}).get("line", "") is None),
                     "left": len(unasked), "cost_usd": round(totals.cost, 4), "stopped": totals.stopped})
        for line in scan_shelves.report_totals(asking, clock(), len(unasked)):
            print(line)
    if note["left"] == 0:
        job.unlink(missing_ok=True)
    write_note(directory, note)
    print(f"the categories: {note['named']:,} named, {note['asked']:,} asked, {note['answered']:,} answered "
          f"({note['no_line_fits']:,} no line fits), {note['refused']:,} refused, {note['left']:,} left; "
          f"${note['cost_usd']:.4f}" + (f"; stopped: {note['stopped']}" if note["stopped"] else ""))
    return note


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ask the AI the category of the products not asked yet.")
    parser.add_argument("--dir", type=Path, required=True, help="the folder shared with the preparation")
    parser.add_argument("--budget", type=float, default=BUDGET_USD)
    parser.add_argument("--stop-after", type=float, default=STOP_AFTER_SECONDS, help="seconds")
    parser.add_argument("--workers", type=int, default=WORKERS)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("no key in the environment: nothing is asked")
        return 0
    if not (args.dir / "jobs" / JOB_NAME).is_file():
        write_note(args.dir, {"night": datetime.now(timezone.utc).date().isoformat(), "named": 0, "asked": 0,
                              "cost_usd": 0.0, "stopped": "", "left": 0})
        print("no products named: nothing to ask")
        return 0

    from picwise_ai.client import ask, make_client
    from picwise_ai.shelves import taxonomy_lines

    lines = taxonomy_lines()
    if not lines:
        print("no Google taxonomy file: nothing to ask")
        return 1
    client = scan_shelves._Recording(make_client(timeout=180.0, max_retries=3))

    def ask_fn(request: dict[str, Any]) -> tuple[Any, str]:
        asked = ask(request, client=client)
        return asked, client.message

    run(args.dir, ask_fn=ask_fn, lines=lines, budget=args.budget, stop_after=args.stop_after, workers=args.workers)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
