from __future__ import annotations

import json
import mimetypes
import sys
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_app import PicwiseLocalApp  # noqa: E402
from picwise_app.buying_routes import render_best_slug_html, render_buying_sitemap_xml  # noqa: E402
from picwise_integrations import (  # noqa: E402
    UrllibSubbyBridgeEventSender,
    send_subby_live_proof_event,
)
from picwise_mvp import run_pickwise_mvp_search_flow  # noqa: E402
from picwise_surface import (  # noqa: E402
    render_mvp_search_results_surface,
    render_picwise_reference_surface,
    render_review_safe_landing_page,
)

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
    host = str(environ.get("HTTP_HOST") or environ.get("SERVER_NAME") or "picwise.subby.cloud")
    scheme = str(environ.get("wsgi.url_scheme", "https"))

    if method != "GET":
        body = json.dumps({"error": "method_not_allowed"}, ensure_ascii=True).encode("utf-8")
        return _response("405 Method Not Allowed", "application/json; charset=utf-8", body, start_response)

    if path == "/health":
        payload = {
            "status": "ok",
            "app": "picwise",
            "mode": "production",
            "domain_plan_primary": "picwise.subby.cloud",
        }
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        return _response("200 OK", "application/json; charset=utf-8", body, start_response)

    if path.startswith("/assets/"):
        asset_result = _asset_response(path)
        if asset_result is not None:
            content_type, body = asset_result
            return _response("200 OK", content_type, body, start_response)

    if path == "/":
        html = render_review_safe_landing_page()
        body = html.encode("utf-8")
        return _response("200 OK", "text/html; charset=utf-8", body, start_response)

    if path == "/demo":
        query_string = str(environ.get("QUERY_STRING", ""))
        query = parse_qs(query_string).get("q", ["power bank 20000mah for iphone"])[0]
        html = _APP.demo_html(query)
        body = html.encode("utf-8")
        return _response("200 OK", "text/html; charset=utf-8", body, start_response)

    if path in {"/search", "/results"}:
        query_string = str(environ.get("QUERY_STRING", ""))
        query = parse_qs(query_string).get("q", [""])[0]
        flow = run_pickwise_mvp_search_flow(query)
        html = render_mvp_search_results_surface(flow)
        body = html.encode("utf-8")
        return _response("200 OK", "text/html; charset=utf-8", body, start_response)

    if path == "/picwise-reference":
        html = render_picwise_reference_surface()
        body = html.encode("utf-8")
        return _response("200 OK", "text/html; charset=utf-8", body, start_response)

    if path.startswith("/best/"):
        slug = path.removeprefix("/best/")
        status_code, html = render_best_slug_html(slug)
        body = html.encode("utf-8")
        status = "200 OK" if status_code == 200 else "404 Not Found"
        return _response(status, "text/html; charset=utf-8", body, start_response)

    if path == "/sitemap-buying-pages.xml":
        xml = render_buying_sitemap_xml(base_url=f"{scheme}://{host}")
        body = xml.encode("utf-8")
        return _response("200 OK", "application/xml; charset=utf-8", body, start_response)

    if path == "/subby-proof":
        payload = send_subby_live_proof_event(sender=UrllibSubbyBridgeEventSender())
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        return _response("200 OK", "application/json; charset=utf-8", body, start_response)

    if path == "/private-beta-readiness":
        payload = _APP.private_beta_readiness_payload()
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        return _response("200 OK", "application/json; charset=utf-8", body, start_response)

    payload = {
        "error": "not_found",
        "available_routes": [
            "/",
            "/health",
            "/demo",
            "/search",
            "/results",
            "/picwise-reference",
            "/best/{slug}",
            "/sitemap-buying-pages.xml",
            "/subby-proof",
            "/private-beta-readiness",
        ],
    }
    body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    return _response("404 Not Found", "application/json; charset=utf-8", body, start_response)


def _asset_response(path: str) -> tuple[str, bytes] | None:
    relative_path = path.removeprefix("/")
    asset_path = (ROOT / relative_path).resolve()
    assets_root = (ROOT / "assets").resolve()
    if not str(asset_path).startswith(str(assets_root)):
        return None
    if not asset_path.exists() or not asset_path.is_file():
        return None
    mime_type, _ = mimetypes.guess_type(str(asset_path))
    content_type = (
        f"{mime_type}; charset=utf-8" if mime_type == "text/css" else (mime_type or "application/octet-stream")
    )
    return content_type, asset_path.read_bytes()

