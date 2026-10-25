"""The site on PicWise's own server: what Vercel does around `api/index.py`.

Vercel serves the build's static folder first (`vercel.json` "outputDirectory": only
`prepared.json`, written by `tools/prepare_catalogue.py`) and hands every other request
to `api/index.py`'s app. On the server gunicorn runs this module, which does the same
with the folder the nightly preparation writes to (`PICWISE_STATIC_DIR`).
"""
from __future__ import annotations

import mimetypes
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.index import StartResponse, app as picwise_app  # noqa: E402

STATIC_DIR = Path(os.environ.get("PICWISE_STATIC_DIR") or ROOT / "public")


def app(environ: dict[str, object], start_response: StartResponse) -> list[bytes]:
    name = str(environ.get("PATH_INFO") or "/").removeprefix("/")
    if name and "/" not in name and not name.startswith("."):
        static = STATIC_DIR / name
        if static.is_file():
            body = static.read_bytes()
            content_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
            if content_type.startswith("text/") or content_type == "application/json":
                content_type += "; charset=utf-8"
            start_response("200 OK", [("Content-Type", content_type), ("Content-Length", str(len(body)))])
            return [body]
    return picwise_app(environ, start_response)
