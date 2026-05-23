from __future__ import annotations

from html import escape
import json
import mimetypes
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import socket
from typing import Any
from urllib.parse import parse_qs, quote, urlparse

from picwise_contracts import DecisionDepth, DecisionOutput, MissingDataState, ProductBrain
from picwise_engine import PicwiseDecisionEngine
from picwise_feeds import FeedAdapterProtocol, LocalFixtureFeedAdapter
from picwise_learning.stage30_runtime_probe import build_default_stage30_runtime_probe
from picwise_learning.stage31_runtime_controller import build_default_stage31_runtime_controller
from picwise_mvp import build_mvp_private_beta_readiness_report
from picwise_nlu import adapt_local_nlu_intent_for_router, build_local_nlu_intent
from picwise_search import resolve_live_search, route_search_query
from picwise_search.live_search_resolver import empty_landing_search_resolution, is_empty_search_query
from picwise_search.search_warmup import schedule_search_warmup_if_needed
from picwise_search.offer_resolver import resolve_specific_product_offers_from_candidates
from picwise_offers import (
    AMAZON_ASSOCIATES_TRACKING_ID,
    MANUAL_AMAZON_AFFILIATE_REGISTRY,
    AmazonManualAffiliateQualityStatus,
    AmazonManualAffiliateStatus,
    get_manual_amazon_record_by_asin,
    get_approved_manual_amazon_record_by_asin,
    validate_amazon_affiliate_url,
)
from picwise_surface import (
    render_amazon_affiliate_proof_page,
    render_affiliate_disclosure_page,
    render_branded_not_found_page,
    render_controlled_search_results_page,
    render_contact_page,
    render_cookies_page,
    render_demo_info_page,
    render_picwise_reference_surface,
    render_privacy_page,
    render_review_safe_landing_page,
    render_terms_page,
)
from .buying_routes import render_best_slug_html, render_buying_sitemap_xml

ROOT_DIR = Path(__file__).resolve().parents[2]
LOCAL_AVAILABLE_ROUTES = (
    "/",
    "/health",
    "/demo",
    "/terms",
    "/privacy",
    "/cookies",
    "/affiliate-disclosure",
    "/contact",
    "/search",
    "/results",
    "/picwise-reference",
    "/amazon-affiliate-proof",
    "/out/amazon",
    "/amazon-launch-check",
    "/amazon-click-proof",
    "/amazon-traffic-protocol",
    "/private-beta-readiness",
    "/best/{slug}",
    "/sitemap-buying-pages.xml",
)


class PicwiseLocalApp:
    def __init__(
        self,
        *,
        feed_adapter: FeedAdapterProtocol | None = None,
        engine: PicwiseDecisionEngine | None = None,
        stage30_probe: Any | None = None,
        stage31_controller: Any | None = None,
    ) -> None:
        self._feed_adapter = feed_adapter or LocalFixtureFeedAdapter()
        self._engine = engine or PicwiseDecisionEngine()
        self._stage30_probe = stage30_probe if stage30_probe is not None else build_default_stage30_runtime_probe()
        self._stage31_controller = (
            stage31_controller if stage31_controller is not None else build_default_stage31_runtime_controller()
        )
        self._amazon_outbound_click_events: list[dict[str, str]] = []

    def health_payload(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "app": "picwise_local_app",
            "mode": "local_non_live",
            "domain_plan_primary": "picwise.subby.cloud",
        }

    def demo_html(self, query: str) -> str:
        _ = query
        return render_demo_info_page()

    def root_landing_html(self) -> str:
        return self.picwise_reference_html("")

    def picwise_reference_html(self, query: str = "", *, source_page: str = "search") -> str:
        if is_empty_search_query(query):
            resolution = empty_landing_search_resolution(query)
        else:
            resolution = resolve_live_search(query)
        html = render_picwise_reference_surface(query=query, resolution=resolution, source_page=source_page)
        if resolution.resolver_state == "broad_query_suggestions":
            html = _inject_broad_query_suggestions(html, resolution)
        if is_empty_search_query(query):
            schedule_search_warmup_if_needed()
        return html

    def amazon_affiliate_proof_html(self) -> str:
        return render_amazon_affiliate_proof_page()

    def amazon_launch_check_html(self) -> str:
        approved_count = len(MANUAL_AMAZON_AFFILIATE_REGISTRY)
        active_count = sum(
            1
            for record in MANUAL_AMAZON_AFFILIATE_REGISTRY
            if record.status == AmazonManualAffiliateStatus.APPROVED
            and record.quality_status == AmazonManualAffiliateQualityStatus.ACTIVE
        )
        disabled_or_review_count = len(MANUAL_AMAZON_AFFILIATE_REGISTRY) - active_count
        return (
            "<!doctype html>"
            '<html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            "<title>PicWise Amazon Launch Check</title>"
            "<style>"
            "body{margin:0;font-family:Inter,Segoe UI,Arial,sans-serif;background:#f6f9ff;color:#102744;}"
            ".pw-wrap{max-width:860px;margin:0 auto;padding:30px 20px;}"
            ".pw-card{background:#fff;border:1px solid #dbe8fb;border-radius:14px;padding:18px 20px;box-shadow:0 8px 24px rgba(17,44,91,.08);}"
            ".pw-list{margin:10px 0 0;padding-left:18px;line-height:1.7;color:#355174;}"
            "code{background:#eef4ff;padding:2px 6px;border-radius:6px;}"
            "</style></head><body><main class=\"pw-wrap\"><section class=\"pw-card\">"
            "<h1>Amazon launch check</h1>"
            "<ul class=\"pw-list\">"
            f"<li>Tracking ID configured: <code>{escape(AMAZON_ASSOCIATES_TRACKING_ID)}</code></li>"
            f"<li>Approved manual links: {approved_count}</li>"
            f"<li>Active public links: {active_count}</li>"
            f"<li>Disabled/manual review links: {disabled_or_review_count}</li>"
            "<li>Search route: <code>/search?q=power%20bank</code></li>"
            "<li>Results route: <code>/results?q=power%20bank</code></li>"
            "<li>Outbound redirect validation: enabled</li>"
            "<li>API access: not available yet</li>"
            "<li>Amazon images/live prices: not used</li>"
            "<li>Disclosure: present</li>"
            "</ul></section></main></body></html>"
        )

    def amazon_click_proof_html(self) -> str:
        active_count = sum(
            1
            for record in MANUAL_AMAZON_AFFILIATE_REGISTRY
            if record.status == AmazonManualAffiliateStatus.APPROVED
            and record.quality_status == AmazonManualAffiliateQualityStatus.ACTIVE
        )
        disabled_or_review_count = len(MANUAL_AMAZON_AFFILIATE_REGISTRY) - active_count
        total_clicks = len(self._amazon_outbound_click_events)
        last_event = self._amazon_outbound_click_events[-1] if self._amazon_outbound_click_events else {}
        last_asin = escape(last_event.get("asin", "none") or "none")
        last_query = escape(last_event.get("query", "none") or "none")
        last_source_page = escape(last_event.get("source_page", "none") or "none")
        last_event_type = escape(last_event.get("event_type", "none") or "none")
        return (
            "<!doctype html>"
            '<html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            "<title>PicWise Amazon Click Proof</title>"
            "<style>"
            "body{margin:0;font-family:Inter,Segoe UI,Arial,sans-serif;background:#f6f9ff;color:#102744;}"
            ".pw-wrap{max-width:860px;margin:0 auto;padding:30px 20px;}"
            ".pw-card{background:#fff;border:1px solid #dbe8fb;border-radius:14px;padding:18px 20px;box-shadow:0 8px 24px rgba(17,44,91,.08);}"
            ".pw-list{margin:10px 0 0;padding-left:18px;line-height:1.7;color:#355174;}"
            "code{background:#eef4ff;padding:2px 6px;border-radius:6px;}"
            "</style></head><body><main class=\"pw-wrap\"><section class=\"pw-card\">"
            "<h1>Amazon click proof</h1>"
            "<ul class=\"pw-list\">"
            f"<li>Tracking ID configured: <code>{escape(AMAZON_ASSOCIATES_TRACKING_ID)}</code></li>"
            f"<li>Recorded outbound clicks: {total_clicks}</li>"
            f"<li>Last click ASIN: {last_asin}</li>"
            f"<li>Last click query: {last_query}</li>"
            f"<li>Last click source: {last_source_page}</li>"
            f"<li>Last event type: {last_event_type}</li>"
            f"<li>Active public links: {active_count}</li>"
            f"<li>Disabled/manual review links: {disabled_or_review_count}</li>"
            "<li>Sales verification: check Amazon Associates</li>"
            "<li>Amazon sales are not verified here. Check Amazon Associates for actual sales.</li>"
            "</ul></section></main></body></html>"
        )

    def amazon_traffic_protocol_html(self) -> str:
        return (
            "<!doctype html>"
            '<html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            "<title>PicWise First Live Traffic Protocol</title>"
            "<style>"
            "body{margin:0;font-family:Inter,Segoe UI,Arial,sans-serif;background:#f6f9ff;color:#102744;}"
            ".pw-wrap{max-width:920px;margin:0 auto;padding:30px 20px;}"
            ".pw-card{background:#fff;border:1px solid #dbe8fb;border-radius:14px;padding:18px 20px;box-shadow:0 8px 24px rgba(17,44,91,.08);margin-bottom:16px;}"
            ".pw-list{margin:10px 0 0;padding-left:18px;line-height:1.7;color:#355174;}"
            "code{background:#eef4ff;padding:2px 6px;border-radius:6px;}"
            "</style></head><body><main class=\"pw-wrap\">"
            "<section class=\"pw-card\">"
            "<h1>First live traffic protocol</h1>"
            "<ul class=\"pw-list\">"
            "<li>This page documents a manual operator protocol only.</li>"
            "<li>This stage does not generate traffic automatically.</li>"
            "<li>Tracking ID: picwise-20</li>"
            "</ul>"
            "</section>"
            "<section class=\"pw-card\">"
            "<h2>PicWise can verify</h2>"
            "<ul class=\"pw-list\">"
            "<li>outbound click route works</li>"
            "<li>click is recorded locally</li>"
            "<li>redirect URL includes <code>tag=picwise-20</code></li>"
            "<li>disabled products do not redirect</li>"
            "</ul>"
            "</section>"
            "<section class=\"pw-card\">"
            "<h2>PicWise cannot verify yet</h2>"
            "<ul class=\"pw-list\">"
            "<li>Amazon orders</li>"
            "<li>Amazon shipped items</li>"
            "<li>Amazon commissions</li>"
            "<li>Amazon conversion rate</li>"
            "<li>Amazon buyer behavior</li>"
            "</ul>"
            "</section>"
            "<section class=\"pw-card\">"
            "<h2>Operator manual Amazon Associates check</h2>"
            "<ul class=\"pw-list\">"
            "<li>Reports</li>"
            "<li>Summary / Full Report</li>"
            "<li>Clicks</li>"
            "<li>Ordered items</li>"
            "<li>Shipped items</li>"
            "<li>Earnings</li>"
            "<li>Tracking ID: picwise-20</li>"
            "</ul>"
            "</section>"
            "<section class=\"pw-card\">"
            "<h2>First traffic test protocol</h2>"
            "<ul class=\"pw-list\">"
            "<li>Use only a small controlled test.</li>"
            "<li>Do not run ads yet.</li>"
            "<li>Do not spam clicks.</li>"
            "<li>Do not click your own links repeatedly.</li>"
            "<li>Share the public search URL with 1-3 trusted real users only.</li>"
            "<li>Ask them to search/open normally if interested.</li>"
            "<li>Wait for Amazon Associates reporting delay.</li>"
            "<li>Then check reports manually.</li>"
            "</ul>"
            "</section>"
            "<section class=\"pw-card\">"
            "<h2>URLs</h2>"
            "<ul class=\"pw-list\">"
            "<li>Safe public test URL: <code>https://picwise.subby.cloud/search?q=power%20bank</code></li>"
            "<li>Internal proof URL: <code>/amazon-click-proof</code></li>"
            "<li>Internal proof URL: <code>/amazon-launch-check</code></li>"
            "</ul>"
            "</section>"
            "<section class=\"pw-card\">"
            "<h2>Readiness checklist</h2>"
            "<ul class=\"pw-list\">"
            "<li>Search page active: ready</li>"
            "<li>Active Amazon links: 4</li>"
            "<li>Disabled links blocked: ready</li>"
            "<li>Click proof: ready</li>"
            "<li>Amazon sales proof: manual Amazon Associates only</li>"
            "<li>Ads: not ready</li>"
            "<li>API reporting: not available yet</li>"
            "</ul>"
            "</section>"
            "<section class=\"pw-card\">"
            "<h2>Hard rules</h2>"
            "<ul class=\"pw-list\">"
            "<li>no Amazon API</li>"
            "<li>no scraping</li>"
            "<li>no live Amazon report fetch</li>"
            "<li>no fake sales</li>"
            "<li>no fake earnings</li>"
            "<li>no fake conversion rate</li>"
            "<li>no auto-clicking</li>"
            "<li>no traffic bot</li>"
            "<li>no tracking pixel</li>"
            "<li>no cookies</li>"
            "<li>no external analytics</li>"
            "</ul>"
            "</section>"
            "</main></body></html>"
        )

    def terms_html(self) -> str:
        return render_terms_page()

    def privacy_html(self) -> str:
        return render_privacy_page()

    def cookies_html(self) -> str:
        return render_cookies_page()

    def affiliate_disclosure_html(self) -> str:
        return render_affiliate_disclosure_page()

    def contact_html(self) -> str:
        return render_contact_page()

    def not_found_html(self) -> str:
        return render_branded_not_found_page()

    def mvp_search_html(self, query: str, *, source_page: str = "search") -> str:
        return self.picwise_reference_html(query, source_page=source_page)

    def resolve_outbound_amazon_redirect(self, asin: str) -> str | None:
        record = get_approved_manual_amazon_record_by_asin(asin)
        if record is None:
            return None
        validation = validate_amazon_affiliate_url(record.affiliate_url, required_tracking_id=AMAZON_ASSOCIATES_TRACKING_ID)
        if not validation.valid:
            return None
        return record.affiliate_url

    def outbound_asin_manual_status_message(self, asin: str) -> str:
        record = get_manual_amazon_record_by_asin(asin)
        if record is None:
            return (
                "This Amazon option is not currently available through PicWise. "
                "Please return to search results."
            )
        if record.status == AmazonManualAffiliateStatus.DISABLED or (
            record.quality_status == AmazonManualAffiliateQualityStatus.UNAVAILABLE_MANUAL
        ):
            return (
                "This Amazon option is not currently available through PicWise. "
                "This option has been disabled after manual review. "
                "Please return to search results."
            )
        return (
            "This Amazon option is not currently available through PicWise. "
            "Please return to search results."
        )

    def record_amazon_outbound_click(self, *, asin: str, query: str, source_page: str) -> dict[str, str]:
        event = {
            "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "asin": str(asin or "").strip().upper(),
            "query": " ".join(str(query or "").split()),
            "source_page": source_page if source_page in {"search", "results", "unknown"} else "unknown",
            "tracking_id": AMAZON_ASSOCIATES_TRACKING_ID,
            "event_type": "amazon_outbound_click",
        }
        self._amazon_outbound_click_events.append(event)
        if len(self._amazon_outbound_click_events) > 200:
            self._amazon_outbound_click_events = self._amazon_outbound_click_events[-200:]
        return event

    def get_amazon_outbound_click_count(self) -> int:
        return len(self._amazon_outbound_click_events)

    def clear_amazon_outbound_click_events(self) -> None:
        self._amazon_outbound_click_events = []

    def private_beta_readiness_payload(self) -> dict[str, Any]:
        report = build_mvp_private_beta_readiness_report()
        return {
            "status": report.status.value,
            "sample_flow_state": report.sample_flow_state,
            "reason_codes": list(report.reason_codes),
            "checks": [
                {"key": check.key, "status": check.status.value, "details": check.details}
                for check in report.checks
            ],
        }

    def build_demo_output(self, query: str) -> DecisionOutput:
        raw_query = str(query or "")
        local_nlu_intent: dict[str, Any] | None = None
        local_nlu_adapter: dict[str, Any] | None = None
        router_input_query = raw_query
        enforce_safe_no_result = False
        router_fallback_used = False
        adapter_decision = "router_only"
        nlu_error: str | None = None

        try:
            local_nlu_intent = build_local_nlu_intent(raw_query)
            local_nlu_adapter = adapt_local_nlu_intent_for_router(local_nlu_intent)
            adapter_decision = str(local_nlu_adapter.get("adapter_decision", "safe_review_only"))
            metadata = local_nlu_adapter.get("router_metadata", {})
            if isinstance(metadata, dict):
                enforce_safe_no_result = bool(metadata.get("enforce_safe_no_result", False))
        except Exception as error:  # pragma: no cover - explicit runtime safety fallback.
            router_fallback_used = True
            nlu_error = str(error.__class__.__name__)
            router_input_query = raw_query
            enforce_safe_no_result = False
            local_nlu_intent = None
            local_nlu_adapter = None
            adapter_decision = "router_fallback_on_nlu_error"

        decision = route_search_query(router_input_query)
        if enforce_safe_no_result:
            decision = route_search_query("")
            router_input_query = ""
        local_nlu_debug = self._build_local_nlu_debug_payload(
            raw_query=raw_query,
            local_nlu_intent=local_nlu_intent,
            local_nlu_adapter=local_nlu_adapter,
            router_input_query=router_input_query,
            router_fallback_used=router_fallback_used,
            adapter_decision=adapter_decision,
            nlu_error=nlu_error,
        )
        self._observe_stage30_shadow(
            raw_query=raw_query,
            decision=decision.to_dict(),
            local_nlu_debug=local_nlu_debug,
        )
        if decision.route_type in {"ambiguous_query", "no_safe_result"}:
            return self._build_safe_no_result_output(
                raw_query=raw_query,
                decision=decision,
                local_nlu_debug=local_nlu_debug,
                local_nlu_adapter=local_nlu_adapter,
            )
        normalized_query = raw_query.strip()

        feed_result = self._feed_adapter.fetch_candidates(normalized_query)
        if decision.route_type == "specific_product":
            offer_set, ranking = resolve_specific_product_offers_from_candidates(
                decision.normalized_query or normalized_query,
                feed_result.candidates,
            )
            return self._build_specific_product_safe_output(
                raw_query=raw_query,
                decision=decision,
                offer_set=offer_set,
                ranking=ranking,
                local_nlu_debug=local_nlu_debug,
                local_nlu_adapter=local_nlu_adapter,
            )
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
                "search_decision": decision.to_dict(),
                "raw_query": raw_query,
                "effective_query": normalized_query,
                "local_nlu_debug": local_nlu_debug,
                "local_nlu_adapter": local_nlu_adapter or {"source": "local_nlu_adapter", "adapter_decision": "not_available"},
            },
        }
        return self._engine.run(
            query=normalized_query,
            candidates=feed_result.candidates,
            context_metadata=context_metadata,
        )

    def _build_local_nlu_debug_payload(
        self,
        *,
        raw_query: str,
        local_nlu_intent: dict[str, Any] | None,
        local_nlu_adapter: dict[str, Any] | None,
        router_input_query: str,
        router_fallback_used: bool,
        adapter_decision: str,
        nlu_error: str | None,
    ) -> dict[str, Any]:
        intent = local_nlu_intent or {}
        visual_intent = {
            "category": intent.get("category"),
            "brands": list(intent.get("brand_candidates", [])),
            "models": list(intent.get("model_candidates", [])),
            "specs": dict(intent.get("specs", {})) if isinstance(intent.get("specs"), dict) else {},
            "priorities": list(intent.get("buying_priority", [])),
            "confidence": intent.get("confidence", 0.0),
            "status": intent.get("status", "not_available"),
            "needs_review": bool(intent.get("needs_review", True)),
        }
        system_flow = {
            "raw_query": raw_query,
            "normalized_query": intent.get("normalized_query") or raw_query.strip().lower(),
            "typo_normalized_query": intent.get("normalized_query"),
            "adapter_decision": adapter_decision,
            "router_fallback_used": router_fallback_used,
            "router_input_query": router_input_query,
            "nlu_error": nlu_error,
        }
        return {
            "json_output": intent if intent else {"status": "not_available", "source": "local_nlu"},
            "visual_intent": visual_intent,
            "system_flow": system_flow,
            "adapter_metadata": local_nlu_adapter or {"source": "local_nlu_adapter", "adapter_decision": "not_available"},
        }

    def _build_safe_no_result_output(
        self,
        *,
        raw_query: str,
        decision: Any,
        local_nlu_debug: dict[str, Any] | None = None,
        local_nlu_adapter: dict[str, Any] | None = None,
    ) -> DecisionOutput:
        normalized_query = raw_query.strip()
        return DecisionOutput(
            query=normalized_query or raw_query,
            selected_brain=ProductBrain.TECH_SPECS_ELECTRONICS,
            decision_depth=DecisionDepth.FAST_DECISION,
            page_title="Picwise safe search result",
            choices=[],
            recommended_product_id="",
            missing_data_states=[MissingDataState.NOT_APPLICABLE],
            tracking_context={
                "safe_no_result": True,
                "search_decision": decision.to_dict(),
                "raw_query": raw_query,
                "effective_query": normalized_query,
                "status": decision.status,
                "result_mode": decision.result_mode,
                "local_nlu_debug": local_nlu_debug or {},
                "local_nlu_adapter": local_nlu_adapter or {"source": "local_nlu_adapter", "adapter_decision": "not_available"},
            },
            more_choices=[],
            warnings=[],
        )

    def _build_specific_product_safe_output(
        self,
        *,
        raw_query: str,
        decision: Any,
        offer_set: Any,
        ranking: Any,
        local_nlu_debug: dict[str, Any] | None = None,
        local_nlu_adapter: dict[str, Any] | None = None,
    ) -> DecisionOutput:
        resolved_status = "manual_review_required"
        resolved_result_mode = "review_only"
        resolver_reason_codes = list(getattr(offer_set, "reason_codes", ()))
        if getattr(offer_set, "status", "") == "no_valid_offers":
            resolved_status = "no_valid_offers"
            resolved_result_mode = "no_result"
        elif getattr(offer_set, "status", "") == "ready":
            # Specific-product offer rendering is intentionally isolated from the 4-choice engine path.
            resolved_status = "manual_review_required"
            resolved_result_mode = "review_only"
            resolver_reason_codes = resolver_reason_codes or ["specific_product_surface_not_enabled"]
        return DecisionOutput(
            query=raw_query.strip() or raw_query,
            selected_brain=ProductBrain.TECH_SPECS_ELECTRONICS,
            decision_depth=DecisionDepth.FAST_DECISION,
            page_title="Picwise specific product safe result",
            choices=[],
            recommended_product_id="",
            missing_data_states=[MissingDataState.NOT_APPLICABLE],
            tracking_context={
                "safe_no_result": True,
                "search_decision": {
                    **decision.to_dict(),
                    "status": resolved_status,
                    "result_mode": resolved_result_mode,
                    "reason_codes": resolver_reason_codes,
                },
                "raw_query": raw_query,
                "effective_query": decision.normalized_query or raw_query.strip(),
                "specific_product_resolution": {
                    "status": getattr(offer_set, "status", "unknown"),
                    "identity_key": getattr(getattr(offer_set, "identity", None), "normalized_key", ""),
                    "matched_offer_count": len(getattr(offer_set, "offers", ())),
                    "recommended_offer_index": getattr(ranking, "recommended_offer_index", None),
                    "reason_codes": list(getattr(ranking, "reason_codes", ())),
                },
                "local_nlu_debug": local_nlu_debug or {},
                "local_nlu_adapter": local_nlu_adapter or {"source": "local_nlu_adapter", "adapter_decision": "not_available"},
            },
            more_choices=[],
            warnings=[],
        )

    def _observe_stage30_shadow(
        self,
        *,
        raw_query: str,
        decision: dict[str, Any],
        local_nlu_debug: dict[str, Any],
    ) -> None:
        if self._stage30_probe is None:
            return
        runtime_decision = {
            **decision,
            "existing_runtime_decision": str(decision.get("status") or ""),
            "existing_runtime_target": str(local_nlu_debug.get("visual_intent", {}).get("category") or "unknown"),
            "existing_runtime_vertical": "retail_physical_products",
            "vertical": "retail_physical_products",
        }
        try:
            shadow_record = self._stage30_probe.observe_runtime_decision(
                runtime_query=raw_query,
                runtime_decision=runtime_decision,
                source_surface="runtime_app",
                source_route="/demo",
            )
            if self._stage31_controller is not None:
                self._stage31_controller.process_runtime_decision(
                    runtime_query=raw_query,
                    runtime_decision=runtime_decision,
                    source_shadow_record=shadow_record,
                )
        except Exception:
            # Stage30/31 instrumentation must never change user-facing flow.
            return

    def _safe_no_result_html(self, output: DecisionOutput) -> str:
        decision = output.tracking_context.get("search_decision", {})
        route_type = str(decision.get("route_type", "no_safe_result"))
        status = str(decision.get("status", "no_valid_offers"))
        result_mode = str(decision.get("result_mode", "no_result"))
        query = escape((output.query or "").strip() or "(empty query)")
        reason_codes = decision.get("reason_codes") or []
        reasons_text = ", ".join(escape(str(code)) for code in reason_codes) if reason_codes else "none"
        return (
            "<!doctype html>"
            '<html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            "<title>Picwise Safe Search</title>"
            "<style>"
            "body{margin:0;font-family:Inter,Segoe UI,Arial,sans-serif;background:#f6f9ff;color:#102744;}"
            ".pw-wrap{max-width:860px;margin:0 auto;padding:32px 20px;}"
            ".pw-card{background:#fff;border:1px solid #dbe8fb;border-radius:14px;padding:18px 20px;box-shadow:0 8px 24px rgba(17,44,91,.08);}"
            ".pw-chip{display:inline-block;background:#eaf2ff;color:#2a6deb;border-radius:999px;padding:6px 10px;font-size:12px;font-weight:700;margin-right:8px;}"
            ".pw-note{margin:12px 0 0;color:#355174;line-height:1.5;}"
            ".pw-list{margin:12px 0 0;padding-left:18px;line-height:1.6;}"
            "code{background:#eef4ff;padding:2px 6px;border-radius:6px;}"
            "</style></head><body>"
            '<main class="pw-wrap"><section class="pw-card">'
            "<h1>Safe no-result response</h1>"
            f"<p>Query: <code>{query}</code></p>"
            f'<p><span class="pw-chip">route_type: {escape(route_type)}</span>'
            f'<span class="pw-chip">status: {escape(status)}</span>'
            f'<span class="pw-chip">result_mode: {escape(result_mode)}</span></p>'
            '<ul class="pw-list">'
            "<li>public_allowed: false</li>"
            "<li>indexable_allowed: false</li>"
            "<li>sitemap_allowed: false</li>"
            "<li>products/results: empty</li>"
            f"<li>reason_codes: {reasons_text}</li>"
            "</ul>"
            '<p class="pw-note">No fallback products are shown. Manual review or query refinement is required.</p>'
            "</section></main></body></html>"
        )


def _inject_broad_query_suggestions(html: str, resolution: Any) -> str:
    suggestions = tuple(getattr(resolution, "suggestions", ()) or ())
    if not suggestions:
        return html
    links: list[str] = []
    for row in suggestions:
        term = escape(str(row.canonical_term))
        href = f"/search?q={quote(str(row.canonical_term), safe='')}"
        links.append(f'<a href="{href}">{term}</a>')
    suggestion_text = "This search is too broad. Try: " + ", ".join(links)
    replacement = f'<p class="pw-reference-disclaimer">{suggestion_text}</p>'
    marker = '<p class="pw-reference-disclaimer">'
    start = html.find(marker)
    if start == -1:
        return html.replace(
            '<section class="pw-empty-state">',
            f'{replacement}<section class="pw-empty-state">',
            1,
        )
    end = html.find("</p>", start)
    if end == -1:
        return html
    return html[:start] + replacement + html[end + 4 :]


class PicwiseRequestHandler(BaseHTTPRequestHandler):
    app = PicwiseLocalApp()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        host = self.headers.get("Host", "127.0.0.1:8016")
        if parsed.path.startswith("/assets/"):
            if self._send_static_asset(parsed.path):
                return
        if parsed.path == "/health":
            self._send_json(HTTPStatus.OK, self.app.health_payload())
            return
        if parsed.path == "/":
            html = self.app.root_landing_html()
            self._send_html(HTTPStatus.OK, html)
            return
        if parsed.path == "/demo":
            query = parse_qs(parsed.query).get("q", ["best products to buy"])[0]
            html = self.app.demo_html(query)
            self._send_html(HTTPStatus.OK, html)
            return
        if parsed.path == "/terms":
            html = self.app.terms_html()
            self._send_html(HTTPStatus.OK, html)
            return
        if parsed.path == "/privacy":
            html = self.app.privacy_html()
            self._send_html(HTTPStatus.OK, html)
            return
        if parsed.path == "/cookies":
            html = self.app.cookies_html()
            self._send_html(HTTPStatus.OK, html)
            return
        if parsed.path == "/affiliate-disclosure":
            html = self.app.affiliate_disclosure_html()
            self._send_html(HTTPStatus.OK, html)
            return
        if parsed.path == "/contact":
            html = self.app.contact_html()
            self._send_html(HTTPStatus.OK, html)
            return
        if parsed.path in {"/search", "/results"}:
            query = parse_qs(parsed.query).get("q", [""])[0]
            source_page = "results" if parsed.path == "/results" else "search"
            html = self.app.mvp_search_html(query, source_page=source_page)
            self._send_html(HTTPStatus.OK, html)
            return
        if parsed.path == "/picwise-reference":
            query = parse_qs(parsed.query).get("q", [""])[0]
            html = self.app.picwise_reference_html(query, source_page="search")
            self._send_html(HTTPStatus.OK, html)
            return
        if parsed.path == "/amazon-affiliate-proof":
            html = self.app.amazon_affiliate_proof_html()
            self._send_html(HTTPStatus.OK, html)
            return
        if parsed.path == "/amazon-launch-check":
            html = self.app.amazon_launch_check_html()
            self._send_html(HTTPStatus.OK, html)
            return
        if parsed.path == "/amazon-click-proof":
            html = self.app.amazon_click_proof_html()
            self._send_html(HTTPStatus.OK, html)
            return
        if parsed.path == "/amazon-traffic-protocol":
            html = self.app.amazon_traffic_protocol_html()
            self._send_html(HTTPStatus.OK, html)
            return
        if parsed.path == "/out/amazon":
            params = parse_qs(parsed.query or "")
            asin = (params.get("asin") or [""])[0]
            query = (params.get("q") or [""])[0]
            source_page = (params.get("src") or ["unknown"])[0]
            target_url = self.app.resolve_outbound_amazon_redirect(asin)
            if target_url is None:
                safe_asin = escape(str(asin or "").strip().upper() or "UNKNOWN")
                message = escape(self.app.outbound_asin_manual_status_message(asin))
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
                self._send_html(HTTPStatus.OK, html)
                return
            self.app.record_amazon_outbound_click(asin=asin, query=query, source_page=source_page)
            self.send_response(HTTPStatus.FOUND)
            self.send_header("Location", target_url)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if parsed.path == "/private-beta-readiness":
            self._send_json(HTTPStatus.OK, self.app.private_beta_readiness_payload())
            return
        if parsed.path.startswith("/best/"):
            slug = parsed.path.removeprefix("/best/")
            status_code, html = render_best_slug_html(slug)
            self._send_html(HTTPStatus(status_code), html)
            return
        if parsed.path == "/sitemap-buying-pages.xml":
            xml = render_buying_sitemap_xml(base_url=f"http://{host}")
            self._send_xml(HTTPStatus.OK, xml)
            return
        self._send_html(HTTPStatus.NOT_FOUND, self.app.not_found_html())

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

    def _send_xml(self, status: HTTPStatus, xml: str) -> None:
        body = xml.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/xml; charset=utf-8")
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


class PicwiseThreadingHTTPServer(ThreadingHTTPServer):
    # Prevent multiple local harness instances from binding the same port,
    # which can route requests to stale code processes on Windows.
    allow_reuse_address = False
    allow_reuse_port = False

    def server_bind(self) -> None:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def run_local_server(host: str = "127.0.0.1", port: int = 8016) -> ThreadingHTTPServer:
    server = PicwiseThreadingHTTPServer((host, port), PicwiseRequestHandler)
    return server
