"""The site's WSGI entry point: the server runs it through
`deployment/server/wsgi_server.py`, Vercel's backup as `api/index`. The routes are
`picwise_app.routes` (one table since 2026-11-12); this module holds the site's one
`PicwiseLocalApp` (`_APP`).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_app import PicwiseLocalApp  # noqa: E402
from picwise_app.routes import StartResponse, answer  # noqa: E402

_APP = PicwiseLocalApp()


def app(environ: dict[str, object], start_response: StartResponse) -> list[bytes]:
    return answer(environ, start_response, _APP)
