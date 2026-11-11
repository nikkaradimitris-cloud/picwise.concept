"""The site on PicWise's own server: what Vercel does around `api/index.py`.

Vercel serves the build's static folder first (`vercel.json` "outputDirectory": only
`prepared.json`, written by `tools/prepare_catalogue.py`) and hands every other request
to `api/index.py`'s app. On the server gunicorn runs this module, which does the same
with the folder the nightly preparation writes to (`PICWISE_STATIC_DIR`), and keeps the
prepared catalogue loaded in each worker (`state.keep_prepared_catalogue_loaded`).
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
from picwise_app.app import NOINDEX_HEADER, SECURITY_HEADERS  # noqa: E402
from picwise_providers.state import keep_prepared_catalogue_loaded  # noqa: E402
from picwise_search import resolve_live_search  # noqa: E402

STATIC_DIR = Path(os.environ.get("PICWISE_STATIC_DIR") or ROOT / "public")

# Each worker loads the prepared catalogue as it starts and brings in each night's new
# one off to the side (`state.refresh_prepared_catalogue`), so that no visitor waits for
# either: the audit of 2026-11-10 measured 5.4 to 5.7 s for the first request of each
# worker after the night's preparation. Once loaded, the worker makes one search of its
# own, kept nowhere and shown to no one, so that what a first search reads into memory
# (the vocabulary, a second or so) is read before a visitor's. gunicorn runs this module
# in each worker (the service does not preload it), so each has its own keeper;
# `PICWISE_CATALOGUE_KEEPER=off` leaves the loading to the first request, as before.
if str(os.environ.get("PICWISE_CATALOGUE_KEEPER") or "").strip().lower() != "off":
    keep_prepared_catalogue_loaded(once_loaded=lambda: resolve_live_search("kettle"))


def app(environ: dict[str, object], start_response: StartResponse) -> list[bytes]:
    name = str(environ.get("PATH_INFO") or "/").removeprefix("/")
    if name and "/" not in name and not name.startswith("."):
        static = STATIC_DIR / name
        if static.is_file():
            body = static.read_bytes()
            content_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
            headers = [("Content-Length", str(len(body))), *SECURITY_HEADERS]
            if content_type == "application/json":
                # Not a page (`prepared.json`, the preparation's public note): kept out of
                # Google, as the app's own JSON answers are (owner, 2026-10-23).
                headers.append(NOINDEX_HEADER)
            if content_type.startswith("text/") or content_type == "application/json":
                content_type += "; charset=utf-8"
            start_response("200 OK", [("Content-Type", content_type), *headers])
            return [body]
    return picwise_app(environ, start_response)
