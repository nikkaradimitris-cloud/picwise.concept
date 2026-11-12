"""The site's routes, written once (the clean-up of 2026-11-12, approved by the owner:
«Ναι, προχώρα με όλα»). Until then `api/index.py` and the local server's handler in
`app.py` each held a copy of every route, and a change to one was forgotten in the other.

`answer(environ, start_response, local_app)` is a WSGI answer for the given app: the
server's entry point passes its one `PicwiseLocalApp`, the local server its own.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import json
import mimetypes
from pathlib import Path
from typing import Callable
from html import escape
from urllib.parse import parse_qs, quote

from .app import (  # noqa: E402
    ASSET_CACHE_CONTROL,
    INFO_PAGE_CACHE_CONTROL,
    NOINDEX_HEADER,
    SECURITY_HEADERS,
)
from .buying_routes import render_best_slug_html, render_buying_sitemap_xml  # noqa: E402
from .prepared_renewal import RENEWAL_PATH, request_prepared_feed_renewal  # noqa: E402
from .search_log import SEARCH_LOG_PATH, record_search  # noqa: E402
from picwise_integrations import (  # noqa: E402
    UrllibSubbyBridgeEventSender,
    send_subby_live_proof_event,
)
from picwise_search.live_search_resolver import parse_shown_count  # noqa: E402
from picwise_surface.seo import SITEMAP_PATH, declares_to_google, robots_txt, sitemap_xml  # noqa: E402
from picwise_surface import (  # noqa: E402
    render_about_page,
    render_affiliate_disclosure_page,
    render_branded_not_found_page,
    render_contact_page,
    render_cookies_page,
    render_picwise_reference_surface,
    render_privacy_page,
    render_review_safe_landing_page,
    render_terms_page,
)

StartResponse = Callable[[str, list[tuple[str, str]]], None]
# The repository's root, where the site's own files are (`assets/`).
ROOT = Path(__file__).resolve().parents[2]

if TYPE_CHECKING:
    from .app import PicwiseLocalApp

_SUGGESTIONS_CACHE_CONTROL = "public, max-age=3600"


def _response(
    status: str,
    content_type: str,
    body: bytes,
    start_response: StartResponse,
    *,
    cache_control: str = "",
) -> list[bytes]:
    headers = [
        ("Content-Type", content_type),
        ("Content-Length", str(len(body))),
        *SECURITY_HEADERS,
    ]
    if cache_control:
        headers.append(("Cache-Control", cache_control))
    if content_type.startswith("application/json"):
        # Not a page: kept out of Google (owner, 2026-10-23).
        headers.append(NOINDEX_HEADER)
    start_response(status, headers)
    return [body]


def answer(environ: dict[str, object], start_response: StartResponse, local_app: "PicwiseLocalApp") -> list[bytes]:
    """Every request to the site, answered with `local_app`: the one table of routes, for
    the server (`api/index.py`, `deployment/server/wsgi_server.py`) and the local server
    (`app.PicwiseRequestHandler`) alike."""
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
            return _response("200 OK", content_type, body, start_response, cache_control=ASSET_CACHE_CONTROL)

    if path == "/robots.txt":
        body = robots_txt().encode("utf-8")
        return _response("200 OK", "text/plain; charset=utf-8", body, start_response)

    if path == SITEMAP_PATH and declares_to_google():
        # The pages Google may index, each at its one address (`picwise_surface.seo`);
        # while nothing is declared to Google (owner, 12/11), a page not found.
        body = sitemap_xml().encode("utf-8")
        return _response("200 OK", "application/xml; charset=utf-8", body, start_response)

    if path == "/":
        # Honour an inbound purchase-intent query: a visitor arriving from Google
        # on /?q=<intent> must see the decision result, not an empty landing.
        query_string = str(environ.get("QUERY_STRING", ""))
        params = parse_qs(query_string)
        query = params.get("q", [""])[0]
        html = local_app.root_landing_html(
            query,
            shown=parse_shown_count(params.get("shown", [""])[0]),
            assist_refresh=params.get("assist", [""])[0] == "1",
        )
        body = html.encode("utf-8")
        return _response("200 OK", "text/html; charset=utf-8", body, start_response)

    if path == "/demo":
        query_string = str(environ.get("QUERY_STRING", ""))
        query = parse_qs(query_string).get("q", ["power bank 20000mah for iphone"])[0]
        html = local_app.demo_html(query)
        body = html.encode("utf-8")
        return _response("200 OK", "text/html; charset=utf-8", body, start_response)

    if path == "/terms":
        html = render_terms_page()
        body = html.encode("utf-8")
        return _response(
            "200 OK", "text/html; charset=utf-8", body, start_response, cache_control=INFO_PAGE_CACHE_CONTROL
        )

    if path == "/privacy":
        html = render_privacy_page()
        body = html.encode("utf-8")
        return _response(
            "200 OK", "text/html; charset=utf-8", body, start_response, cache_control=INFO_PAGE_CACHE_CONTROL
        )

    if path == "/cookies":
        html = render_cookies_page()
        body = html.encode("utf-8")
        return _response(
            "200 OK", "text/html; charset=utf-8", body, start_response, cache_control=INFO_PAGE_CACHE_CONTROL
        )

    if path == "/affiliate-disclosure":
        html = render_affiliate_disclosure_page()
        body = html.encode("utf-8")
        return _response(
            "200 OK", "text/html; charset=utf-8", body, start_response, cache_control=INFO_PAGE_CACHE_CONTROL
        )

    if path == "/contact":
        html = render_contact_page()
        body = html.encode("utf-8")
        return _response(
            "200 OK", "text/html; charset=utf-8", body, start_response, cache_control=INFO_PAGE_CACHE_CONTROL
        )

    if path == "/about":
        html = render_about_page()
        body = html.encode("utf-8")
        return _response(
            "200 OK", "text/html; charset=utf-8", body, start_response, cache_control=INFO_PAGE_CACHE_CONTROL
        )

    if path == "/assist-status":
        # The search page's script asking whether a complex search's answer is there
        # (`picwise_app.assist_wiring`); never kept by a browser or a cache.
        key = parse_qs(str(environ.get("QUERY_STRING", ""))).get("k", [""])[0]
        body = local_app.assist_status_json(key).encode("utf-8")
        return _response(
            "200 OK", "application/json; charset=utf-8", body, start_response, cache_control="no-store"
        )

    if path == SEARCH_LOG_PATH:
        # The search page's script reporting a search once the page has loaded in a
        # browser: its words are kept where the server keeps searches (owner,
        # 2026-11-07; `picwise_app.search_log`), and nowhere else.
        record_search(parse_qs(str(environ.get("QUERY_STRING", ""))).get("q", [""])[0])
        return _response(
            "204 No Content", "application/json; charset=utf-8", b"", start_response, cache_control="no-store"
        )

    if path == "/suggest.json":
        # The search box's suggestions, fetched once by the page and kept by the
        # browser for an hour, so a keystroke costs no request (step 4).
        body = local_app.search_suggestions_json().encode("utf-8")
        return _response(
            "200 OK",
            "application/json; charset=utf-8",
            body,
            start_response,
            cache_control=_SUGGESTIONS_CACHE_CONTROL,
        )

    if path in {"/search", "/results"}:
        query_string = str(environ.get("QUERY_STRING", ""))
        params = parse_qs(query_string)
        query = params.get("q", [""])[0]
        source_page = "results" if path == "/results" else "search"
        html = local_app.picwise_reference_html(
            query,
            source_page=source_page,
            shown=parse_shown_count(params.get("shown", [""])[0]),
            assist_refresh=params.get("assist", [""])[0] == "1",
        )
        body = html.encode("utf-8")
        return _response("200 OK", "text/html; charset=utf-8", body, start_response)

    if path == "/picwise-reference":
        query_string = str(environ.get("QUERY_STRING", ""))
        params = parse_qs(query_string)
        query = params.get("q", [""])[0]
        html = local_app.picwise_reference_html(
            query,
            source_page="search",
            shown=parse_shown_count(params.get("shown", [""])[0]),
        )
        body = html.encode("utf-8")
        return _response("200 OK", "text/html; charset=utf-8", body, start_response)

    if path == "/out/feed":
        query_string = str(environ.get("QUERY_STRING", ""))
        query_params = parse_qs(query_string)
        product_id = (query_params.get("pid") or [""])[0]
        query = (query_params.get("q") or [""])[0]
        source_page = (query_params.get("src") or ["unknown"])[0]
        rec_param = (query_params.get("rec") or [""])[0].strip().lower()
        is_recommended = True if rec_param == "1" else False if rec_param == "0" else None
        resolved = local_app.resolve_outbound_feed_redirect(product_id)
        if resolved is None:
            local_app.record_feed_outbound_click(
                product_id=product_id,
                query=query,
                source_page=source_page,
                is_recommended=is_recommended,
                provider_key="unknown",
                merchant_name="unknown",
                redirect_url="",
                event_name="redirect_failure",
            )
            safe_query = quote(str(query or "").strip(), safe="")
            back_href = f"/search?q={safe_query}" if safe_query else "/"
            html = (
                "<!doctype html>"
                '<html lang="en"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width, initial-scale=1">'
                "<title>PicWise Option Unavailable</title>"
                "<style>"
                "body{margin:0;font-family:Inter,Segoe UI,Arial,sans-serif;background:#f6f9ff;color:#102744;}"
                ".pw-wrap{max-width:860px;margin:0 auto;padding:30px 20px;}"
                ".pw-card{background:#fff;border:1px solid #dbe8fb;border-radius:14px;padding:18px 20px;box-shadow:0 8px 24px rgba(17,44,91,.08);}"
                ".pw-note{margin:10px 0 0;line-height:1.6;color:#355174;}"
                ".pw-btn{display:inline-flex;align-items:center;justify-content:center;height:42px;padding:0 18px;border-radius:999px;background:#1f6dff;border:1px solid #1f6dff;color:#fff;font-size:14px;font-weight:700;text-decoration:none;margin-top:16px;}"
                "</style></head><body><main class=\"pw-wrap\"><section class=\"pw-card\">"
                "<h1>This option is no longer available</h1>"
                "<p class=\"pw-note\">PicWise could not confirm this offer is still "
                "showable, so it will not send you to it. This happens when an offer "
                "leaves the provider feed or is no longer in stock.</p>"
                f"<a class=\"pw-btn\" href=\"{escape(back_href, quote=True)}\">Back to results</a>"
                "</section></main></body></html>"
            )
            body = html.encode("utf-8")
            return _response("200 OK", "text/html; charset=utf-8", body, start_response)
        local_app.record_feed_outbound_click(
            product_id=product_id,
            query=query,
            source_page=source_page,
            is_recommended=is_recommended,
            provider_key=resolved["provider_key"],
            merchant_name=resolved["merchant_name"],
            redirect_url=resolved["redirect_url"],
            event_name="recommended_click" if is_recommended else "non_recommended_click",
        )
        local_app.record_feed_outbound_click(
            product_id=product_id,
            query=query,
            source_page=source_page,
            is_recommended=is_recommended,
            provider_key=resolved["provider_key"],
            merchant_name=resolved["merchant_name"],
            redirect_url=resolved["redirect_url"],
            event_name="redirect_success",
        )
        start_response(
            "302 Found",
            [
                ("Content-Type", "text/plain; charset=utf-8"),
                ("Content-Length", "0"),
                ("Location", resolved["redirect_url"]),
                # A click is never answered from a browser's or a cache's memory.
                ("Cache-Control", "no-store"),
                *SECURITY_HEADERS,
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
        payload = local_app.private_beta_readiness_payload()
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        return _response("200 OK", "application/json; charset=utf-8", body, start_response)

    if path == RENEWAL_PATH:
        # Vercel's daily scheduled job (vercel.json "crons"), with CRON_SECRET.
        status, payload = request_prepared_feed_renewal(str(environ.get("HTTP_AUTHORIZATION") or ""))
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        return _response(
            status, "application/json; charset=utf-8", body, start_response, cache_control="no-store"
        )

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

