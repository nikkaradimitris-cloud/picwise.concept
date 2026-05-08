from __future__ import annotations

import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from picwise_contracts import DecisionOutput
from picwise_engine import PicwiseDecisionEngine
from picwise_feeds import FeedAdapterProtocol, LocalFixtureFeedAdapter
from picwise_redirects import build_redirect_tracking_payload, resolve_redirect
from picwise_surface import render_landing_surface, render_picwise_reference_surface

ROOT_DIR = Path(__file__).resolve().parents[2]


class PicwiseLocalApp:
    def __init__(
        self,
        *,
        feed_adapter: FeedAdapterProtocol | None = None,
        engine: PicwiseDecisionEngine | None = None,
    ) -> None:
        self._feed_adapter = feed_adapter or LocalFixtureFeedAdapter()
        self._engine = engine or PicwiseDecisionEngine()

    def health_payload(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "app": "picwise_local_app",
            "mode": "local_non_live",
            "domain_plan_primary": "picwise.subby.cloud",
        }

    def demo_html(self, query: str) -> str:
        output = self.build_demo_output(query)
        rendered = render_landing_surface(output)
        resolution = resolve_redirect(
            output,
            selected_product_id=output.recommended_product_id,
            session_id=str(uuid4()),
            click_to_redirect_budget_ms=220,
            local_safe_mode=True,
        )
        redirect_payload = build_redirect_tracking_payload(resolution)
        payload_text = json.dumps(redirect_payload, ensure_ascii=True, separators=(",", ":"))
        marker = (
            "<!-- data_origin:local_test_fixture;data_classification:not_production_data; "
            "non_live_demo:true -->"
        )
        return rendered.replace(
            "</body>",
            (
                f'<script type="application/json" id="redirect-preview">{payload_text}</script>'
                f"{marker}</body>"
            ),
        )

    def picwise_reference_html(self) -> str:
        return render_picwise_reference_surface()

    def build_demo_output(self, query: str) -> DecisionOutput:
        normalized_query = query.strip() or "power bank 20000mah for iphone"
        feed_result = self._feed_adapter.fetch_candidates(normalized_query)
        context_metadata = {
            "category": "electronics",
            "product_type": "power bank",
            "service_type": "retail",
            "risk_level": "medium",
            "price_band": "mid",
            "missing_data_states": [state.value for state in feed_result.missing_data_states],
            "tracking_context": {
                "feed_adapter": feed_result.source_metadata.get("adapter"),
                "source_id": feed_result.source_metadata.get("source_id"),
                "local_test_fixture": True,
                "not_production_data": True,
            },
        }
        return self._engine.run(
            query=normalized_query,
            candidates=feed_result.candidates,
            context_metadata=context_metadata,
        )


class PicwiseRequestHandler(BaseHTTPRequestHandler):
    app = PicwiseLocalApp()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path.startswith("/assets/"):
            if self._send_static_asset(parsed.path):
                return
        if parsed.path == "/health":
            self._send_json(HTTPStatus.OK, self.app.health_payload())
            return
        if parsed.path in {"/", "/demo"}:
            query = parse_qs(parsed.query).get("q", ["power bank 20000mah for iphone"])[0]
            html = self.app.demo_html(query)
            self._send_html(HTTPStatus.OK, html)
            return
        if parsed.path == "/picwise-reference":
            html = self.app.picwise_reference_html()
            self._send_html(HTTPStatus.OK, html)
            return
        self._send_json(
            HTTPStatus.NOT_FOUND,
            {"error": "not_found", "available_routes": ["/", "/health", "/demo", "/picwise-reference"]},
        )

    def log_message(self, _format: str, *_args: Any) -> None:
        return

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, status: HTTPStatus, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_static_asset(self, raw_path: str) -> bool:
        relative_path = raw_path.removeprefix("/")
        asset_path = (ROOT_DIR / relative_path).resolve()
        assets_root = (ROOT_DIR / "assets").resolve()
        if not str(asset_path).startswith(str(assets_root)):
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "asset_not_found"})
            return True
        if not asset_path.exists() or not asset_path.is_file():
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "asset_not_found"})
            return True
        mime_type, _ = mimetypes.guess_type(str(asset_path))
        content_type = f"{mime_type}; charset=utf-8" if mime_type == "text/css" else (mime_type or "application/octet-stream")
        body = asset_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        return True


def run_local_server(host: str = "127.0.0.1", port: int = 8016) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), PicwiseRequestHandler)
    return server
