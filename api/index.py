from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_app import PicwiseLocalApp  # noqa: E402

StartResponse = Callable[[str, list[tuple[str, str]]], None]

_APP = PicwiseLocalApp()


def _response(
    status: str,
    content_type: str,
    body: bytes,
    start_response: StartResponse,
) -> list[bytes]:
    start_response(
        status,
        [
            ("Content-Type", content_type),
            ("Content-Length", str(len(body))),
        ],
    )
    return [body]


def app(environ: dict[str, object], start_response: StartResponse) -> list[bytes]:
    method = str(environ.get("REQUEST_METHOD", "GET")).upper()
    path = str(environ.get("PATH_INFO", "/"))

    if method != "GET":
        body = json.dumps({"error": "method_not_allowed"}, ensure_ascii=True).encode("utf-8")
        return _response("405 Method Not Allowed", "application/json; charset=utf-8", body, start_response)

    if path == "/health":
        payload = _APP.health_payload()
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        return _response("200 OK", "application/json; charset=utf-8", body, start_response)

    if path == "/demo":
        query_string = str(environ.get("QUERY_STRING", ""))
        query = parse_qs(query_string).get("q", ["power bank 20000mah for iphone"])[0]
        html = _APP.demo_html(query)
        body = html.encode("utf-8")
        return _response("200 OK", "text/html; charset=utf-8", body, start_response)

    payload = {"error": "not_found", "available_routes": ["/health", "/demo"]}
    body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    return _response("404 Not Found", "application/json; charset=utf-8", body, start_response)

