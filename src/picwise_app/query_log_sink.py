"""Persist what buyers searched and what PicWise understood, for the NLU training loop.

The in-process event list holds the last 400 events and is lost on every restart, which
on a serverless host is every few minutes. This sink also writes one row per served
query to a Supabase (PostgREST) table, when configured:

    PICWISE_QUERY_LOG_SUPABASE_URL   https://<project>.supabase.co
    PICWISE_QUERY_LOG_SUPABASE_KEY   a key allowed to insert into the table
    PICWISE_QUERY_LOG_TABLE          table name, default picwise_query_log

The table is created by `deployment/supabase_query_log.sql`. Unconfigured, the sink does
nothing, and nothing pretends to be stored.

What is written is only what the training loop needs: the query text, what was
understood, whether it was a typo correction, whether choices were shown, and the
resolver state. No IP address, user agent, session or other personal data.

Writes happen on one background thread so a slow or unreachable database never delays a
page. On a serverless host the process can be frozen right after a response, so a row
written in the last moments before that may be lost; the log is a training signal, not
an audit record.
"""
from __future__ import annotations

import json
import os
import queue
import threading
from typing import Any
from urllib.request import Request, urlopen

_URL_ENV = "PICWISE_QUERY_LOG_SUPABASE_URL"
_KEY_ENV = "PICWISE_QUERY_LOG_SUPABASE_KEY"
_TABLE_ENV = "PICWISE_QUERY_LOG_TABLE"
_DEFAULT_TABLE = "picwise_query_log"
_FIELDS = (
    "timestamp",
    "query",
    "source_page",
    "resolver_state",
    "understood_concept",
    "understood_by_correction",
    "choices_rendered",
)
_MAX_QUERY_LENGTH = 300


class QueryLogSink:
    def __init__(self) -> None:
        self._queue: "queue.Queue[dict[str, Any]]" = queue.Queue(maxsize=1000)
        self._worker: threading.Thread | None = None
        self._lock = threading.Lock()
        self.dropped = 0
        self.failed = 0
        self.written = 0

    @staticmethod
    def configured() -> bool:
        return bool(
            str(os.environ.get(_URL_ENV) or "").strip()
            and str(os.environ.get(_KEY_ENV) or "").strip()
        )

    def record(self, event: dict[str, Any]) -> bool:
        """Queue one served-query event for writing. Returns whether it was queued."""
        if not self.configured():
            return False
        row = {name: event.get(name) for name in _FIELDS}
        row["query"] = str(row.get("query") or "")[:_MAX_QUERY_LENGTH]
        row["understood_by_correction"] = str(row.get("understood_by_correction")) == "true"
        row["choices_rendered"] = str(row.get("choices_rendered")) == "true"
        try:
            self._queue.put_nowait(row)
        except queue.Full:
            self.dropped += 1
            return False
        self._ensure_worker()
        return True

    def flush(self, timeout: float = 5.0) -> None:
        """Wait for queued rows to be written. For tests and shutdown."""
        done = threading.Event()

        def wait() -> None:
            self._queue.join()
            done.set()

        threading.Thread(target=wait, daemon=True).start()
        done.wait(timeout)

    def _ensure_worker(self) -> None:
        with self._lock:
            if self._worker is None or not self._worker.is_alive():
                self._worker = threading.Thread(target=self._run, name="picwise-query-log", daemon=True)
                self._worker.start()

    def _run(self) -> None:
        while True:
            row = self._queue.get()
            try:
                self._write(row)
                self.written += 1
            except Exception:  # noqa: BLE001 - logging must never break serving
                self.failed += 1
            finally:
                self._queue.task_done()

    @staticmethod
    def _write(row: dict[str, Any]) -> None:
        base = str(os.environ.get(_URL_ENV) or "").strip().rstrip("/")
        key = str(os.environ.get(_KEY_ENV) or "").strip()
        table = str(os.environ.get(_TABLE_ENV) or "").strip() or _DEFAULT_TABLE
        request = Request(
            f"{base}/rest/v1/{table}",
            data=json.dumps(row).encode("utf-8"),
            method="POST",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
        )
        with urlopen(request, timeout=3) as response:
            response.read()


QUERY_LOG_SINK = QueryLogSink()
