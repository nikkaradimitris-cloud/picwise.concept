from __future__ import annotations

import socket
import sys
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_app import run_local_server  # noqa: E402
from picwise_buying_pages import generate_first_scale_batch  # noqa: E402


def _pick_open_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = int(sock.getsockname()[1])
    sock.close()
    return port


class BuyingPagesScaleRouteSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.port = _pick_open_port()
        cls.server = run_local_server(host="127.0.0.1", port=cls.port)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.candidate_slug = generate_first_scale_batch().candidate_pages[0].slug

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2.0)

    def _fetch_local(self, path: str) -> tuple[int, str]:
        with urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=5) as response:
            return response.status, response.read().decode("utf-8")

    def test_protected_and_known_public_routes_stay_safe(self) -> None:
        for path in (
            "/health",
            "/",
            "/demo",
            "/picwise-reference",
            "/best/power-bank-20000mah-for-iphone",
            "/best/kompiouteraki-casio-gia-panellinies",
            "/sitemap-buying-pages.xml",
        ):
            status, _body = self._fetch_local(path)
            self.assertEqual(status, 200)

    def test_unknown_slug_and_candidate_slug_return_404(self) -> None:
        for path in ("/best/unknown-test-slug", f"/best/{self.candidate_slug}"):
            with self.assertRaises(HTTPError) as ctx:
                urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=5)
            self.assertEqual(ctx.exception.code, 404)

    def test_sitemap_does_not_include_candidate_slug(self) -> None:
        status, body = self._fetch_local("/sitemap-buying-pages.xml")
        self.assertEqual(status, 200)
        self.assertNotIn(f"/best/{self.candidate_slug}", body)


if __name__ == "__main__":
    unittest.main()
