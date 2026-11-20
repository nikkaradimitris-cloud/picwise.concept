"""Each kind of the site given its own lines of Google's taxonomy by the AI, once.

Owner, 2026-11-20 (19:00 Athens): «Κάθε είδος του site να έχει τη δική του λίστα κατηγοριών
Google ... Τη λίστα να τη φτιάξει το AI μία φορά (περίπου 0,50 $) και να ελεγχθεί». Claude
Haiku 5.5 is given Google's taxonomy (cached, as the scan of the products) and the kinds of
the site, a few of one department a call (`picwise_ai.kind_lines`); every line it gives is
checked against the taxonomy (`kind_lines.checked_kind_lines`). A kind not answered, or
answered twice, is asked again alone, at most twice more.

With `--catalogue` (the server's prepared file) and `--answers` (the scan's answers), each
kind comes with the lines the scan's AI gave the products the catalogue reads as that kind,
how many and a few titles (`kind_lines.evidence`): the lists then hold the lines where the
products really are, and the model sees which of them are look-alikes.

Written to `--out` (JSON, the repository's form: `kind_lines.write`) and printed in few
characters (`kind_lines.compact`: `id=number,number`, the numbers the taxonomy file's
lines), kept as GitHub's notes, which its API shows without a login: the lists come back
to the repository from those, read against the same taxonomy (`kind_lines.from_compact`),
and are checked there before any rule reads them. No product, link or key is read or
printed; nothing on the server or the site changes.

    python3 deployment/server/write_kind_lines.py --out LISTS.json [--catalogue CATALOGUE.json.gz \
        --answers ANSWERS.jsonl.gz] [--budget 1.00] [--workers 4] [--dry-run]
"""
from __future__ import annotations

import argparse
import os
import sys
import threading
import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for folder in (ROOT / "src", HERE):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

# Tries a call in all, for an error of the network or the API's load.
MOST_TRIES = 4
PAUSE_SECONDS = 15.0
# Notes GitHub keeps a step: one for the totals, the rest for the lists.
MOST_NOTES = 10


class Run:
    """The calls of one run: what they cost, and the lists answered."""

    def __init__(self, ask: Callable[[dict[str, Any]], Any] | None, budget: float, lines: Sequence[str]) -> None:
        self.ask = ask
        self.budget = budget
        self.lines = lines
        self.spent = 0.0
        self.calls = 0
        self.failed = 0
        self.refused = 0
        self.found: dict[str, list[str]] = {}
        self.lock = threading.Lock()
        self.errors: list[str] = []

    def one(self, kinds: list[dict[str, Any]]) -> None:
        from picwise_ai.kind_lines import checked_kind_lines, request_kwargs

        if self.ask is None:
            return
        request = request_kwargs(kinds, self.lines)
        for attempt in range(MOST_TRIES):
            with self.lock:
                if self.spent >= self.budget:
                    return
            asked = self.ask(request)
            with self.lock:
                self.calls += 1
                self.spent += float(getattr(asked, "cost_usd", 0.0) or 0.0)
            error = str(getattr(asked, "error", "") or "")
            answer = getattr(asked, "answer", None)
            if answer is not None:
                found, refused = checked_kind_lines(answer, [kind["id"] for kind in kinds], self.lines)
                with self.lock:
                    self.refused += refused
                    for kind, chosen in found.items():
                        self.found.setdefault(kind, chosen)
                return
            with self.lock:
                self.failed += 1
                self.errors.append(error or str(getattr(asked, "stop_reason", "") or "no answer"))
            if "HTTP 401" in error or "HTTP 403" in error:
                return
            time.sleep(PAUSE_SECONDS * (attempt + 1))


def run_all(run: Run, kinds: list[dict[str, Any]], workers: int) -> None:
    """Every kind asked with its department, then each kind not answered asked alone."""
    from picwise_ai.kind_lines import batches

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        list(pool.map(run.one, batches(kinds)))
    for _round in range(2):
        missing = [kind for kind in kinds if kind["id"] not in run.found]
        if not missing or run.ask is None:
            break
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            list(pool.map(run.one, [[kind] for kind in missing]))


def seen_in(catalogue: Path, answers: Path) -> tuple[dict[str, list[tuple[str, int, list[str]]]], str]:
    """Per kind, the AI's lines of the products the catalogue reads as it; and a line
    saying what was read."""
    from picwise_ai.kind_lines import evidence
    from picwise_providers.ai_shelves import line_of, read_answers
    from picwise_providers.prepared_catalogue import read_prepared_catalogue_to_measure

    prepared = read_prepared_catalogue_to_measure(catalogue)
    if prepared is None:
        return {}, "the copy is not a prepared catalogue: no products shown with the kinds"
    table = read_answers(answers)
    if not table:
        return {}, "no answers of the AI: no products shown with the kinds"
    with_line = 0

    def rows():
        nonlocal with_line
        for product, kinds in zip(prepared.products, prepared.kinds):
            line = line_of(str(product.title or ""), str(product.brand or ""), product.raw, table)
            with_line += bool(line)
            yield kinds, line, str(product.title or "")

    found = evidence(rows())
    return found, (
        f"the catalogue of {prepared.prepared_at.isoformat()}: {len(prepared.products):,} products, "
        f"{with_line:,} with a line of the AI; {len(found)} kinds have products read as them"
    )


def ordered(found: dict[str, list[str]], ids: Sequence[str]) -> dict[str, list[str]]:
    return {kind: found[kind] for kind in ids if kind in found}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--catalogue", type=Path, default=None)
    parser.add_argument("--answers", type=Path, default=None)
    parser.add_argument("--budget", type=float, default=1.00)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass
    from picwise_ai.kind_lines import MODEL, all_ids, batches, chunks, compact, kinds_described, write
    from picwise_ai.shelves import taxonomy_lines
    from scan_shelves import Notices

    notices = Notices(most=MOST_NOTES, keep=MOST_NOTES)
    lines = taxonomy_lines()
    kinds = kinds_described()
    ids = all_ids(kinds)
    print(f"{len(kinds)} kinds in {len(batches(kinds))} calls; the taxonomy {len(lines):,} lines")
    read_note = "no catalogue given: the kinds asked without their products"
    if args.catalogue is not None and args.answers is not None:
        began_reading = time.monotonic()
        seen, read_note = seen_in(args.catalogue, args.answers)
        read_note += f" (read in {time.monotonic() - began_reading:.0f} s)"
        if seen:
            for kind in kinds:
                kind["seen"] = seen.get(kind["id"], [])
    print(read_note)
    ask = None
    if not args.dry_run and os.environ.get("ANTHROPIC_API_KEY"):
        from picwise_ai.client import ask as ask_one, make_client

        client = make_client(timeout=180.0, max_retries=2)
        ask = lambda request: ask_one(request, client=client)  # noqa: E731
    else:
        print("the AI: not asked (a dry run, or no key)")
    began = time.monotonic()
    run = Run(ask, args.budget, lines)
    run_all(run, kinds, args.workers)
    found = ordered(run.found, ids)
    empty = [kind for kind, chosen in found.items() if not chosen]
    missing = [kind for kind in ids if kind not in found]
    given = sum(len(chosen) for chosen in found.values())
    totals = [
        read_note,
        f"{len(found)} of {len(ids)} kinds answered; {given} lines in all; refused {run.refused}",
        f"kinds with no line: {len(empty)}" + (f" ({', '.join(empty[:40])})" if empty else ""),
        f"kinds not answered: {len(missing)}" + (f" ({', '.join(missing[:40])})" if missing else ""),
        f"{run.calls} calls, {run.failed} failed" + (f" ({'; '.join(sorted(set(run.errors))[:5])})" if run.errors else ""),
        f"cost ${run.spent:.4f} (budget ${args.budget:.2f}); {time.monotonic() - began:.0f} s",
    ]
    text = compact(found, lines)
    pieces = chunks(text)
    if len(pieces) > MOST_NOTES - 1:
        totals.append(f"the lists need {len(pieces)} notes, {MOST_NOTES - 1} fit: read the log for the rest")
    notices.say("kind lines: in all", "\n".join(totals), final=True)
    for number, piece in enumerate(pieces, 1):
        notices.say(f"kind lines {number} of {len(pieces)}", piece, final=True)
    write(
        found,
        args.out,
        note={
            "written": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "model": MODEL,
            "taxonomy": "data/taxonomy_sources/google/taxonomy.en-US.txt",
            "cost_usd": round(run.spent, 4),
        },
    )
    print(f"written: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
