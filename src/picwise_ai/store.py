"""Where the AI layer's jobs and answers are kept on the server (the AI layer's spec,
`docs/PICWISE_AI_LAYER_SPEC.md`, 4.5 and 4.7).

The site never calls the API and never waits. For a complex search it writes a job (the
search and the products the AI reads) to `jobs/`; the service `picwise-assist`, under a
user of its own and the only one given the key, answers it, checks the answer and writes
the result to `results/`; the site reads it. Each is a small JSON file named by a key of
the search and the products read (`job_key`): the same search with the same products, at
the same prices, is answered once and its answer kept for 24 hours. The shops' words a
result offers are counted once by the site's own catalogue and kept in `served/`.

A result's `status` is what the page may do with it: "shown" (a sentence that passed the
checks, and the products whose own words show they fit, which come first: owner,
2026-11-06), "buttons" (no product fits; the shops' words for the need), "nothing",
"withheld" (the checks refused the answer) or "failed" (no answer; kept only for
`FAILED_MINUTES`, so that the search is asked again later). Only "shown" changes the
order.

The standard library only: the site imports this module.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Iterable
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from picwise_ai.complex_search import Candidate, ComplexSearch

# The folder the site and the service share, e.g. /srv/picwise/shared/assist. Unset: the
# site writes no job and the page is as it was before the AI layer.
ASSIST_DIR_ENV = "PICWISE_ASSIST_DIR"
# How long an answer stands for the same search with the same products (the spec, 4.7).
RESULT_HOURS = 24
# How long a failed call keeps the search from being asked again.
FAILED_MINUTES = 15
# A job older than this is dropped unanswered: its visitor has long left, and a backlog
# after the service was down must not spend the day's cap at once.
JOB_MAX_MINUTES = 60
FORMAT = 1
STATUSES = ("shown", "buttons", "nothing", "withheld", "failed")
_KEY = re.compile(r"^[0-9a-f]{32}$")


def assist_directory() -> Path | None:
    """The shared folder, when the server names one and it holds `jobs/`; None for a site
    without the layer. The deployment makes `jobs/` only when the service has its key
    (`deploy.sh`), so a server without the key writes no job and its pages are as before."""
    configured = str(os.environ.get(ASSIST_DIR_ENV) or "").strip()
    if not configured:
        return None
    directory = Path(configured)
    return directory if (directory / "jobs").is_dir() else None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def search_text(search: str) -> str:
    """The search as its answer is kept: spaces and letter case do not make another one."""
    return " ".join(str(search or "").split()).casefold()


def job_key(search: str, signature: str) -> str:
    """The name of a search's job and answer: the search and the products the AI reads,
    in order, at their prices (`search_selection.candidates_signature`)."""
    text = f"{search_text(search)}\n{str(signature or '').strip()}"
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]


def valid_key(key: Any) -> bool:
    """A key the site wrote: 32 hexadecimal digits, so a key from a URL names no other file."""
    return bool(_KEY.match(str(key or "")))


def complex_search_payload(complex_search: ComplexSearch) -> dict[str, Any]:
    payload = asdict(complex_search)
    payload["words"] = list(complex_search.words)
    payload["candidates"] = [asdict(candidate) for candidate in complex_search.candidates]
    return payload


def complex_search_from_payload(payload: dict[str, Any]) -> ComplexSearch:
    return ComplexSearch(
        search=str(payload.get("search") or ""),
        words=tuple(str(word) for word in payload.get("words") or ()),
        kind_name=str(payload.get("kind_name") or ""),
        fell_back=bool(payload.get("fell_back")),
        candidates=tuple(
            Candidate(
                number=int(row["number"]),
                product_id=str(row.get("product_id") or ""),
                title=str(row.get("title") or ""),
                brand=str(row.get("brand") or ""),
                price_text=str(row.get("price_text") or ""),
                currency=str(row.get("currency") or ""),
                shop=str(row.get("shop") or ""),
                description=str(row.get("description") or ""),
            )
            for row in payload.get("candidates") or ()
        ),
        total=int(payload.get("total") or 0),
        kind_id=str(payload.get("kind_id") or ""),
    )


def _folder(directory: Path, name: str) -> Path:
    return Path(directory) / name


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    """Written whole or not at all: a reader never sees half a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f".{path.name}.{os.getpid()}.partial")
    partial.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    os.replace(partial, path)


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return payload if isinstance(payload, dict) and payload.get("v") == FORMAT else None


def _written_at(payload: dict[str, Any]) -> datetime | None:
    try:
        written = datetime.fromisoformat(str(payload.get("written_at") or ""))
    except ValueError:
        return None
    return written if written.tzinfo is not None else written.replace(tzinfo=timezone.utc)


def read_result(directory: Path, key: str, *, now: datetime | None = None) -> dict[str, Any] | None:
    """A search's answer while it stands (24 hours; a failure 15 minutes), else None."""
    if not valid_key(key):
        return None
    payload = _read_json(_folder(directory, "results") / f"{key}.json")
    if payload is None or payload.get("key") != key or payload.get("status") not in STATUSES:
        return None
    written = _written_at(payload)
    if written is None:
        return None
    life = timedelta(minutes=FAILED_MINUTES) if payload["status"] == "failed" else timedelta(hours=RESULT_HOURS)
    return payload if (now or utc_now()) - written <= life else None


def write_result(directory: Path, key: str, payload: dict[str, Any], *, now: datetime | None = None) -> None:
    """The service's answer to a job (`service.answer_job`), under the job's key."""
    if not valid_key(key):
        raise ValueError("not a job's key")
    _write_json(
        _folder(directory, "results") / f"{key}.json",
        {**payload, "v": FORMAT, "key": key, "written_at": (now or utc_now()).isoformat()},
    )


def job_pending(directory: Path, key: str) -> bool:
    """A job waits, or the service is answering it (it renames a job it takes)."""
    if not valid_key(key):
        return False
    jobs = _folder(directory, "jobs")
    return (jobs / f"{key}.json").is_file() or (jobs / f".{key}.taken").is_file()


def write_job(
    directory: Path, complex_search: ComplexSearch, signature: str, *, now: datetime | None = None
) -> str:
    """Ask the service about a complex search, once: nothing is written while an answer
    stands or a job waits. Returns the key the page asks about."""
    key = job_key(complex_search.search, signature)
    moment = now or utc_now()
    if read_result(directory, key, now=moment) is not None or job_pending(directory, key):
        return key
    _write_json(
        _folder(directory, "jobs") / f"{key}.json",
        {
            "v": FORMAT,
            "key": key,
            "signature": signature,
            "written_at": moment.isoformat(),
            "complex_search": complex_search_payload(complex_search),
        },
    )
    return key


def read_job(path: Path) -> tuple[str, str, datetime, ComplexSearch] | None:
    """A job as the service reads it: its key, signature, time and search; None when it is
    not one."""
    payload = _read_json(path)
    if payload is None or not valid_key(payload.get("key")):
        return None
    written = _written_at(payload)
    search = payload.get("complex_search")
    if written is None or not isinstance(search, dict):
        return None
    try:
        return str(payload["key"]), str(payload.get("signature") or ""), written, complex_search_from_payload(search)
    except (KeyError, TypeError, ValueError):
        return None


def read_served(directory: Path, key: str) -> list[dict[str, Any]] | None:
    """The shops' words of a result as the site's catalogue counted them, once; None
    before they are counted."""
    if not valid_key(key):
        return None
    payload = _read_json(_folder(directory, "served") / f"{key}.json")
    if payload is None or not isinstance(payload.get("buttons"), list):
        return None
    return [row for row in payload["buttons"] if isinstance(row, dict)]


def write_served(directory: Path, key: str, buttons: Iterable[dict[str, Any]]) -> None:
    if not valid_key(key):
        raise ValueError("not a job's key")
    _write_json(_folder(directory, "served") / f"{key}.json", {"v": FORMAT, "key": key, "buttons": list(buttons)})


class AssistLookup:
    """For one search on the site: given the signature of the products the AI reads
    (`search_selection.candidates_signature`), the ids of those its standing answer read
    as fitting, which then come first (owner, 2026-11-06); it keeps what it read for the
    page. Passed to the search as its `fitting_for`."""

    def __init__(self, directory: Path, search: str, *, now: datetime | None = None) -> None:
        self.directory = Path(directory)
        self.search = search
        self.now = now or utc_now()
        self.key = ""
        self.result: dict[str, Any] | None = None

    def __call__(self, signature: str) -> tuple[str, ...]:
        self.key = job_key(self.search, signature)
        self.result = read_result(self.directory, self.key, now=self.now)
        return fitting_ids(self.result)


def fitting_ids(result: dict[str, Any] | None) -> tuple[str, ...]:
    """The products a result reads as fitting, when its sentence is shown; else none."""
    if not result or result.get("status") != "shown":
        return ()
    return tuple(
        str(row.get("product_id") or "").strip()
        for row in result.get("fitting") or ()
        if isinstance(row, dict) and str(row.get("product_id") or "").strip()
    )


def fitting_words(result: dict[str, Any] | None) -> dict[str, str]:
    """Each fitting product's own words that show it, by its id, for its mark."""
    if not result or result.get("status") != "shown":
        return {}
    return {
        str(row.get("product_id") or "").strip(): str(row.get("words") or "").strip()
        for row in result.get("fitting") or ()
        if isinstance(row, dict) and str(row.get("product_id") or "").strip()
    }
