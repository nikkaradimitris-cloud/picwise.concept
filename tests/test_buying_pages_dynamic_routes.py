from __future__ import annotations

import io
import socket
import sys
import threading
import unittest
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from api.index import app as deployment_app  # noqa: E402
from picwise_app import run_local_server  # noqa: E402


def _pick_open_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = int(sock.getsockname()[1])
    sock.close()
    return port


def _call_wsgi(path: str) -> tuple[str, dict[str, str], str]:
    status_holder: dict[str, Any] = {}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        status_holder["status"] = status
        status_holder["headers"] = {key: value for key, value in headers}

    environ: dict[str, object] = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": path,
        "QUERY_STRING": "",
        "wsgi.input": io.BytesIO(b""),
        "CONTENT_LENGTH": "0",
        "SERVER_NAME": "localhost",
        "SERVER_PORT": "443",
        "HTTP_HOST": "localhost",
        "wsgi.url_scheme": "https",
    }
    body_chunks = deployment_app(environ, start_response)
    body = b"".join(body_chunks).decode("utf-8")
    return status_holder["status"], status_holder["headers"], body


class BuyingPagesDynamicRoutesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.port = _pick_open_port()
        cls.server = run_local_server(host="127.0.0.1", port=cls.port)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2.0)

    def _fetch_local(self, path: str) -> tuple[int, str]:
        with urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=5) as response:
            return response.status, response.read().decode("utf-8")

    def test_best_route_known_slugs_return_200(self) -> None:
        status_a, body_a = self._fetch_local("/best/power-bank-20000mah-for-iphone")
        status_b, body_b = self._fetch_local("/best/kompiouteraki-casio-gia-panellinies")
        self.assertEqual(status_a, 200)
        self.assertEqual(status_b, 200)
        self.assertIn("Showing 4 options for:", body_a)
        self.assertIn("Showing 4 options for:", body_b)

    def test_best_route_unknown_slug_returns_404(self) -> None:
        with self.assertRaises(HTTPError) as ctx:
            urlopen(f"http://127.0.0.1:{self.port}/best/does-not-exist", timeout=5)
        self.assertEqual(ctx.exception.code, 404)

    def test_protected_routes_keep_working(self) -> None:
        for path in ("/", "/demo", "/health", "/picwise-reference"):
            status, _body = self._fetch_local(path)
            self.assertEqual(status, 200)

    def test_deployment_entrypoint_serves_best_route(self) -> None:
        status, headers, body = _call_wsgi("/best/power-bank-20000mah-for-iphone")
        self.assertEqual(status, "200 OK")
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn("Recommended by PickWise", body)


if __name__ == "__main__":
    unittest.main()
