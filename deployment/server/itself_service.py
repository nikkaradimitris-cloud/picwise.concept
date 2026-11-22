"""The service `picwise-itself`: each morning, the question "is it the kind itself" asked for
the products the night's preparation named (`docs/PICWISE_KIND_ITSELF_RULES.md`, 8.2; the
owner's plan of 21/11, step 8: «είναι το ίδιο το προϊόν ή αξεσουάρ, ανταλλακτικό ή
αναλώσιμο;»).

Run by `picwise-itself.service` after the night's preparation and the category's asking,
under the AI layer's own user, with the Anthropic SDK of its own environment and the key in
its environment only (`/etc/picwise/assist.env`), never the site's. It reads the questions
the preparation names (`jobs/itself.jsonl.gz`, `picwise_providers.kind_itself.job_items`: of
the products the catalogue shows or the cap would take next, the questions with no first
reading, those that wait for a second, those to ask again, and each kind's first cards),
asks them (`picwise_ai.itself_asking.run`: the first reading by Claude Haiku 5.5, the second
by Claude Sonnet 5.5, every answer checked), and keeps the answers in the file the next
night's preparation reads (`answers.jsonl.gz`), written whole and then put in place.

It stops for the night before passing $5 (the rules' 4.6: a brake for a loop gone wrong, not
a budget; a night's need is cents) and after 2 hours; what it did not ask is named again by
the next preparation. Its note (`night.json`: counts and the cost, never a product) is read
by the morning's health run, which tells a stop at the $5.

    itself_service.py --dir /srv/picwise/assist/itself [--budget 5] [--stop-after 7200]
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

JOB_NAME = "itself.jsonl.gz"
ANSWERS_NAME = "answers.jsonl.gz"
NOTE_NAME = "night.json"
BUDGET_USD = 5.0
STOP_AFTER_SECONDS = 7200.0
WORKERS = 4


def read_job(path: Path) -> list[dict[str, Any]]:
    """The questions named, in their order; none when the file is not there or cannot be read."""
    items: list[dict[str, Any]] = []
    try:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for text in handle:
                try:
                    item = json.loads(text)
                except ValueError:
                    continue
                if isinstance(item, dict) and isinstance(item.get("k"), str) and isinstance(item.get("kind"), str):
                    items.append(item)
    except (OSError, EOFError, gzip.BadGzipFile):
        return []
    return items


def write_note(directory: Path, note: dict[str, Any]) -> None:
    target = directory / NOTE_NAME
    temporary = target.with_name(target.name + ".part")
    temporary.write_text(json.dumps(note, indent=1, sort_keys=True), encoding="utf-8")
    os.replace(temporary, target)


def run(
    directory: Path,
    *,
    ask_fn: Callable[[dict[str, Any]], Any],
    budget: float = BUDGET_USD,
    stop_after: float = STOP_AFTER_SECONDS,
    workers: int = WORKERS,
    today: str | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    """One morning's asking; its note (also written as `NOTE_NAME`)."""
    from picwise_ai import itself_asking
    from picwise_ai.client import Budget
    from picwise_providers import kind_itself

    today = today or datetime.now(timezone.utc).date().isoformat()
    job = directory / "jobs" / JOB_NAME
    answers_path = directory / ANSWERS_NAME
    items = read_job(job)
    note: dict[str, Any] = {"night": today, "named": len(items), "cost_usd": 0.0, "stopped": "", "left": 0}
    if items:
        if not kind_itself.answers_readable(answers_path):
            # A file that is there and cannot be read is never written over.
            note["stopped"] = "the answers file cannot be read: nothing asked"
            write_note(directory, note)
            print(f"the kind itself: {note['stopped']}")
            return note
        records = kind_itself.read_answers(answers_path)
        kept_before = len(records)
        totals = itself_asking.run(
            items, records, ask_fn=ask_fn, budget=Budget(budget), today=today, deadline=clock() + stop_after,
            clock=clock, workers=max(1, workers), save=lambda: kind_itself.write_answers(answers_path, records),
        )
        note.update(totals.note())
        note.update({"named": len(items), "questions_kept": len(records), "questions_kept_before": kept_before})
        for line in itself_asking.report(totals):
            print(line)
    if note["left"] == 0:
        job.unlink(missing_ok=True)
    write_note(directory, note)
    print(f"the kind itself: {note['named']:,} questions named, {note['left']:,} readings left; ${note['cost_usd']:.4f}"
          + (f"; stopped at {note['stopped']}" if note["stopped"] else ""))
    return note


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Ask the AI "is it the kind itself" for the products named.')
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
        write_note(args.dir, {"night": datetime.now(timezone.utc).date().isoformat(), "named": 0, "cost_usd": 0.0,
                              "stopped": "", "left": 0})
        print("no questions named: nothing to ask")
        return 0

    from picwise_ai.client import ask, make_client

    client = make_client(timeout=180.0, max_retries=3)
    run(args.dir, ask_fn=lambda request: ask(request, client=client), budget=args.budget,
        stop_after=args.stop_after, workers=args.workers)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
