"""The service that answers the site's complex searches: `picwise-assist` (the AI layer's
spec, `docs/PICWISE_AI_LAYER_SPEC.md`, 4.5 to 4.7).

It runs under a user of its own, the only one given the key, and reads the jobs the site
writes (`store.write_job`): for each, it asks Claude Haiku 5.5 (`request`, `client`),
reads the answer with the layer's checks (`checks.check_answer`) and writes the result the
site reads (`store.write_result`): the sentence and the products whose own words show they
fit, which the site puts first (owner, 2026-11-06), or the shops' words for the need, or
nothing. It never loads the catalogue: the site counts the shops' words itself.

The owner's limits (4.7): at most one euro a day (owner, 2026-11-06: «Το όριο μπορεί να
παραμείνει στο 1 ευρώ»), kept as $1.00, which is below it; the spend is added up from each
answer's tokens per UTC day, and nothing is asked past it; at most 30 calls a minute; a
few calls at a time, the newest job first, since its visitor is waiting.
"""
from __future__ import annotations

import json
import re
import threading
import time
from collections import deque
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from picwise_ai import store
from picwise_ai.checks import check_answer
from picwise_ai.client import Asked, ask
from picwise_ai.complex_search import Candidate, ComplexSearch
from picwise_ai.request import request_kwargs

# One euro a day (the owner), kept in dollars as the API is priced, below it.
DAILY_CAP_USD = 1.00
CALLS_PER_MINUTE = 30
WORKERS = 3
POLL_SECONDS = 0.5


class SpendLedger:
    """What the calls cost per UTC day, kept in `spend/<day>.json` so that a restart does
    not forget it; one lock for the service's threads."""

    def __init__(self, directory: Path, *, cap_usd: float = DAILY_CAP_USD) -> None:
        self.folder = Path(directory) / "spend"
        self.cap_usd = cap_usd
        self._lock = threading.Lock()

    def _path(self, now: datetime) -> Path:
        return self.folder / f"{now.astimezone(timezone.utc).date().isoformat()}.json"

    def spent(self, now: datetime) -> float:
        try:
            payload = json.loads(self._path(now).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return 0.0
        return float(payload.get("spent_usd") or 0.0) if isinstance(payload, dict) else 0.0

    def reserve(self, now: datetime) -> bool:
        """Whether a call may be made today: the day's spend is still under the cap."""
        with self._lock:
            return self.spent(now) < self.cap_usd

    def add(self, now: datetime, cost_usd: float) -> float:
        with self._lock:
            path = self._path(now)
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                payload = {}
            spent = float(payload.get("spent_usd") or 0.0) + max(0.0, float(cost_usd))
            calls = int(payload.get("calls") or 0) + 1
            path.parent.mkdir(parents=True, exist_ok=True)
            partial = path.with_name(f".{path.name}.partial")
            partial.write_text(json.dumps({"spent_usd": round(spent, 6), "calls": calls}), encoding="utf-8")
            partial.replace(path)
            return spent


class MinuteLimit:
    """At most `per_minute` calls in any sixty seconds: a burst of searches waits its turn
    rather than spending a day's cap in minutes."""

    def __init__(self, per_minute: int = CALLS_PER_MINUTE, clock: Callable[[], float] = time.monotonic) -> None:
        self.per_minute = per_minute
        self.clock = clock
        self._calls: deque[float] = deque()
        self._lock = threading.Lock()

    def wait_time(self) -> float:
        """0 when a call may be made now (and it is counted); else how long to wait."""
        with self._lock:
            now = self.clock()
            while self._calls and now - self._calls[0] >= 60.0:
                self._calls.popleft()
            if len(self._calls) < self.per_minute:
                self._calls.append(now)
                return 0.0
            return 60.0 - (now - self._calls[0])


def _original_words(proof: str, candidate: Candidate) -> str:
    """A fitting product's own words as its title or description writes them, for its
    mark: the words the check found (lower case, one space) looked for again in its text."""
    text = f"{candidate.title} {candidate.description}"
    shown = []
    for piece in (part for part in proof.split("; ") if part.strip()):
        pattern = r"\s+".join(re.escape(word) for word in piece.split())
        match = re.search(pattern, text, flags=re.IGNORECASE) if pattern else None
        shown.append(" ".join(match.group(0).split()) if match else piece)
    return " … ".join(shown)


def answer_job(complex_search: ComplexSearch, asked: Asked) -> dict[str, Any]:
    """The result of one call, as the site reads it (`store` explains each status)."""
    common: dict[str, Any] = {
        "search": complex_search.search,
        "kind_name": complex_search.kind_name,
        "model": asked.model,
        "cost_usd": round(asked.cost_usd, 6),
        "seconds": round(asked.seconds, 2),
    }
    if asked.answer is None:
        return {**common, "status": "failed", "reason": asked.error or asked.stop_reason or "no answer"}
    checked = check_answer(asked.answer, complex_search, stop_reason=asked.stop_reason)
    if checked.failure:
        return {**common, "status": "withheld", "reason": checked.failure}
    by_number = {candidate.number: candidate for candidate in complex_search.candidates}
    if checked.sentence:
        return {
            **common,
            "status": "shown",
            "sentence": checked.sentence,
            "fitting": [
                {"product_id": by_number[number].product_id, "words": _original_words(proof, by_number[number])}
                for number, proof in checked.proof
                if by_number[number].product_id
            ],
        }
    if checked.shop_words:
        return {**common, "status": "buttons", "shop_words": list(checked.shop_words)}
    return {**common, "status": "nothing"}


def _log(message: str) -> None:
    print(message, flush=True)


class AssistService:
    """The jobs folder read in a loop; each job claimed by renaming it, so that no two
    threads answer one."""

    def __init__(
        self,
        directory: Path,
        *,
        client: Any,
        ask_fn: Callable[..., Asked] = ask,
        ledger: SpendLedger | None = None,
        limit: MinuteLimit | None = None,
        now: Callable[[], datetime] = store.utc_now,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.directory = Path(directory)
        self.jobs = self.directory / "jobs"
        self.client = client
        self.ask_fn = ask_fn
        self.ledger = ledger or SpendLedger(self.directory)
        self.limit = limit or MinuteLimit()
        self.now = now
        self.sleep = sleep

    def waiting_jobs(self) -> list[Path]:
        """The jobs not yet taken, the newest first: its visitor is the one waiting."""
        try:
            paths = [path for path in self.jobs.iterdir() if path.suffix == ".json" and not path.name.startswith(".")]
        except OSError:
            return []

        def written(path: Path) -> float:
            try:
                return path.stat().st_mtime
            except OSError:
                return 0.0

        return sorted(paths, key=written, reverse=True)

    def take(self, path: Path) -> Path | None:
        taken = path.with_name(f".{path.stem}.taken")
        try:
            path.rename(taken)
        except OSError:
            return None
        return taken

    def run_job(self, taken: Path) -> str:
        """Answer one taken job and write its result; what happened, for the log."""
        try:
            job = store.read_job(taken)
            if job is None:
                return "not a job: dropped"
            key, _signature, written, complex_search = job
            now = self.now()
            if now - written > timedelta(minutes=store.JOB_MAX_MINUTES):
                return f"{key[:8]} too old: dropped"
            if store.read_result(self.directory, key, now=now) is not None:
                return f"{key[:8]} already answered"
            if not self.ledger.reserve(now):
                return f"{key[:8]} the day's cap of ${self.ledger.cap_usd:.2f} reached: not asked"
            while True:
                wait = self.limit.wait_time()
                if wait <= 0:
                    break
                self.sleep(min(wait, 5.0))
            asked = self.ask_fn(request_kwargs(complex_search), client=self.client)
            spent = self.ledger.add(self.now(), asked.cost_usd)
            result = answer_job(complex_search, asked)
            store.write_result(self.directory, key, result, now=self.now())
            reason = f" ({result['reason']})" if result.get("reason") else ""
            return (
                f"{key[:8]} {result['status']}{reason}; {asked.seconds:.1f} s; ${asked.cost_usd:.5f};"
                f" ${spent:.4f} today"
            )
        finally:
            try:
                taken.unlink()
            except OSError:
                pass

    def give_back_taken(self) -> None:
        """Jobs a stopped service had taken wait again: answered, or dropped as too old."""
        for taken in self.jobs.glob(".*.taken"):
            key = taken.name[1 : -len(".taken")]
            if store.valid_key(key):
                try:
                    taken.rename(self.jobs / f"{key}.json")
                except OSError:
                    continue

    def run(self, *, once: bool = False, workers: int = WORKERS, poll_seconds: float = POLL_SECONDS) -> None:
        """Answer the jobs as they come; with `once`, those waiting now, then return."""
        self.jobs.mkdir(parents=True, exist_ok=True)
        self.give_back_taken()
        with ThreadPoolExecutor(max_workers=workers) as pool:
            running: set[Any] = set()
            while True:
                # The answers no search may use any more, at most once an hour.
                store.prune(self.directory, "results", older_than=timedelta(hours=store.RESULT_HOURS + 1),
                            now=self.now())
                running = {future for future in running if not future.done()}
                for path in self.waiting_jobs():
                    if len(running) >= workers:
                        break
                    taken = self.take(path)
                    if taken is not None:
                        future = pool.submit(self.run_job, taken)
                        future.add_done_callback(lambda done: _log(_outcome(done)))
                        running.add(future)
                if once:
                    for future in list(running):
                        future.result()
                    if not self.waiting_jobs():
                        return
                    continue
                self.sleep(poll_seconds)


def _outcome(future: Any) -> str:
    try:
        return str(future.result())
    except Exception as error:  # one job's failure never stops the service
        return f"a job failed: {type(error).__name__}"
