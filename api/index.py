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
from picwise_surface import (  # noqa: E402
    render_amazon_affiliate_proof_page,
    render_affiliate_disclosure_page,
    render_branded_not_found_page,
    render_contact_page,
    render_controlled_search_results_page,
    render_cookies_page,
    render_picwise_reference_surface,
    render_privacy_page,
    render_review_safe_landing_page,
    render_terms_page,
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
        html = _APP.picwise_reference_html("")
        body = html.encode("utf-8")
        return _response("200 OK", "text/html; charset=utf-8", body, start_response)

    if path == "/demo":
        query_string = str(environ.get("QUERY_STRING", ""))
        query = parse_qs(query_string).get("q", ["power bank 20000mah for iphone"])[0]
        html = _APP.demo_html(query)
        body = html.encode("utf-8")
        return _response("200 OK", "text/html; charset=utf-8", body, start_response)

    if path == "/terms":
        html = render_terms_page()
        body = html.encode("utf-8")
        return _response("200 OK", "text/html; charset=utf-8", body, start_response)

    if path == "/privacy":
        html = render_privacy_page()
        body = html.encode("utf-8")
        return _response("200 OK", "text/html; charset=utf-8", body, start_response)

    if path == "/cookies":
        html = render_cookies_page()
        body = html.encode("utf-8")
        return _response("200 OK", "text/html; charset=utf-8", body, start_response)

    if path == "/affiliate-disclosure":
        html = render_affiliate_disclosure_page()
        body = html.encode("utf-8")
        return _response("200 OK", "text/html; charset=utf-8", body, start_response)

    if path == "/contact":
        html = render_contact_page()
        body = html.encode("utf-8")
        return _response("200 OK", "text/html; charset=utf-8", body, start_response)

    if path in {"/search", "/results"}:
        query_string = str(environ.get("QUERY_STRING", ""))
        query = parse_qs(query_string).get("q", [""])[0]
        source_page = "results" if path == "/results" else "search"
        html = _APP.picwise_reference_html(query, source_page=source_page)
        body = html.encode("utf-8")
        return _response("200 OK", "text/html; charset=utf-8", body, start_response)

    if path == "/picwise-reference":
        query_string = str(environ.get("QUERY_STRING", ""))
        query = parse_qs(query_string).get("q", [""])[0]
        html = _APP.picwise_reference_html(query, source_page="search")
        body = html.encode("utf-8")
        return _response("200 OK", "text/html; charset=utf-8", body, start_response)

    if path == "/amazon-affiliate-proof":
        html = render_amazon_affiliate_proof_page()
        body = html.encode("utf-8")
        return _response("200 OK", "text/html; charset=utf-8", body, start_response)

    if path == "/amazon-launch-check":
        html = _APP.amazon_launch_check_html()
        body = html.encode("utf-8")
        return _response("200 OK", "text/html; charset=utf-8", body, start_response)

    if path == "/amazon-click-proof":
        html = _APP.amazon_click_proof_html()
        body = html.encode("utf-8")
        return _response("200 OK", "text/html; charset=utf-8", body, start_response)

    if path == "/amazon-traffic-protocol":
        html = _APP.amazon_traffic_protocol_html()
        body = html.encode("utf-8")
        return _response("200 OK", "text/html; charset=utf-8", body, start_response)

    if path == "/out/amazon":
        query_string = str(environ.get("QUERY_STRING", ""))
        query_params = parse_qs(query_string)
        asin = (query_params.get("asin") or [""])[0]
        query = (query_params.get("q") or [""])[0]
        source_page = (query_params.get("src") or ["unknown"])[0]
        target_url = _APP.resolve_outbound_amazon_redirect(asin)
        if target_url is None:
            safe_asin = str(asin or "").strip().upper() or "UNKNOWN"
            message = _APP.outbound_asin_manual_status_message(asin)
            html = (
                "<!doctype html>"
                '<html lang="en"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width, initial-scale=1">'
                "<title>PicWise Amazon Option Disabled</title>"
                "<style>"
                "body{margin:0;font-family:Inter,Segoe UI,Arial,sans-serif;background:#f6f9ff;color:#102744;}"
                ".pw-wrap{max-width:860px;margin:0 auto;padding:30px 20px;}"
                ".pw-card{background:#fff;border:1px solid #dbe8fb;border-radius:14px;padding:18px 20px;box-shadow:0 8px 24px rgba(17,44,91,.08);}"
                ".pw-note{margin:10px 0 0;line-height:1.6;color:#355174;}"
                ".pw-btn{display:inline-flex;align-items:center;justify-content:center;height:42px;padding:0 18px;border-radius:999px;background:#1f6dff;border:1px solid #1f6dff;color:#fff;font-size:14px;font-weight:700;text-decoration:none;margin-top:16px;}"
                "</style></head><body><main class=\"pw-wrap\"><section class=\"pw-card\">"
                "<h1>Amazon option disabled</h1>"
                f"<p class=\"pw-note\">ASIN: {safe_asin}</p>"
                f"<p class=\"pw-note\">{message}</p>"
                "<a class=\"pw-btn\" href=\"/search?q=power%20bank\">Return to search results</a>"
                "</section></main></body></html>"
            )
            body = html.encode("utf-8")
            return _response("200 OK", "text/html; charset=utf-8", body, start_response)
        _APP.record_amazon_outbound_click(asin=asin, query=query, source_page=source_page)
        start_response(
            "302 Found",
            [
                ("Content-Type", "text/plain; charset=utf-8"),
                ("Content-Length", "0"),
                ("Location", target_url),
            ],
        )
        return [b""]

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

    html = render_branded_not_found_page()
    body = html.encode("utf-8")
    return _response("404 Not Found", "text/html; charset=utf-8", body, start_response)


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

