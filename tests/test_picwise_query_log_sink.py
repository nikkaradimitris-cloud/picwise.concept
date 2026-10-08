"""Served queries reach the query log store when one is configured, and only then."""
from __future__ import annotations

import json
import os
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_app.query_log_sink import QueryLogSink  # noqa: E402

_ENV = ("PICWISE_QUERY_LOG_SUPABASE_URL", "PICWISE_QUERY_LOG_SUPABASE_KEY", "PICWISE_QUERY_LOG_TABLE")


class _Recorder(BaseHTTPRequestHandler):
    received: list[tuple[str, dict, dict]] = []

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length) or b"{}")
        _Recorder.received.append((self.path, {k.lower(): v for k, v in self.headers.items()}, body))
        self.send_response(201)
        self.end_headers()

    def log_message(self, *args) -> None:
        return None


class QueryLogSinkTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved = {name: os.environ.get(name) for name in _ENV + ("NO_PROXY", "no_proxy")}
        for name in _ENV:
            os.environ.pop(name, None)
        os.environ["NO_PROXY"] = os.environ["no_proxy"] = "127.0.0.1,localhost"
        _Recorder.received = []
        self.server = HTTPServer(("127.0.0.1", 0), _Recorder)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self._restore)

    def _restore(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        for name, value in self._saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    def _event(self, **overrides) -> dict:
        event = {
            "timestamp": "2026-10-01T10:00:00Z",
            "query": "πλιντηριο ρουχων",
            "source_page": "search",
            "resolver_state": "understood_provider_not_connected",
            "understood_concept": "washing_machine",
            "understood_by_correction": "false",
            "choices_rendered": "true",
            "session_id": "not_connected",
        }
        event.update(overrides)
        return event

    def test_nothing_is_written_when_not_configured(self) -> None:
        sink = QueryLogSink()
        self.assertFalse(sink.record(self._event()))
        self.assertEqual(_Recorder.received, [])

    def test_a_served_query_is_written_to_the_table(self) -> None:
        os.environ["PICWISE_QUERY_LOG_SUPABASE_URL"] = f"http://127.0.0.1:{self.server.server_port}"
        os.environ["PICWISE_QUERY_LOG_SUPABASE_KEY"] = "test-key"
        sink = QueryLogSink()
        self.assertTrue(sink.record(self._event()))
        sink.flush()
        self.assertEqual(sink.written, 1)
        path, headers, body = _Recorder.received[0]
        self.assertEqual(path, "/rest/v1/picwise_query_log")
        self.assertEqual(headers.get("apikey"), "test-key")
        self.assertEqual(body["query"], "πλιντηριο ρουχων")
        self.assertEqual(body["understood_concept"], "washing_machine")
        self.assertIs(body["choices_rendered"], True)
        self.assertIs(body["understood_by_correction"], False)

    def test_only_training_fields_are_written(self) -> None:
        os.environ["PICWISE_QUERY_LOG_SUPABASE_URL"] = f"http://127.0.0.1:{self.server.server_port}"
        os.environ["PICWISE_QUERY_LOG_SUPABASE_KEY"] = "test-key"
        sink = QueryLogSink()
        sink.record(self._event(client_ip="203.0.113.7"))
        sink.flush()
        body = _Recorder.received[0][2]
        self.assertNotIn("client_ip", body)
        self.assertNotIn("session_id", body)

    def test_an_unreachable_store_never_raises(self) -> None:
        os.environ["PICWISE_QUERY_LOG_SUPABASE_URL"] = "http://127.0.0.1:9"
        os.environ["PICWISE_QUERY_LOG_SUPABASE_KEY"] = "test-key"
        sink = QueryLogSink()
        self.assertTrue(sink.record(self._event()))
        sink.flush()
        self.assertEqual(sink.failed, 1)


if __name__ == "__main__":
    unittest.main()
