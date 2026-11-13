from __future__ import annotations

from html import escape
import json
import re
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import socket
from typing import Any
from urllib.parse import quote, urlparse, unquote

from picwise_contracts import DecisionDepth, DecisionOutput, MissingDataState, ProductBrain
from picwise_engine import PicwiseDecisionEngine
from picwise_feeds import FeedAdapterProtocol, LocalFixtureFeedAdapter
from picwise_learning.stage30_runtime_probe import build_default_stage30_runtime_probe
from picwise_learning.stage31_runtime_controller import build_default_stage31_runtime_controller
from picwise_mvp import build_mvp_private_beta_readiness_report
from picwise_nlu import adapt_local_nlu_intent_for_router, build_local_nlu_intent
from picwise_search import resolve_live_search, route_search_query
from picwise_search.live_search_resolver import (
    SEARCH_IN_ENGLISH_REASON,
    empty_landing_search_resolution,
    is_empty_search_query,
)
from picwise_search.search_warmup import schedule_search_warmup_if_needed
from picwise_search.offer_resolver import resolve_specific_product_offers_from_candidates
from picwise_providers import resolve_card_eligible_provider_feed_product_by_id
from picwise_providers.state import (
    peek_search_catalogue_counts,
    prepared_catalogue_status,
    resolve_provider_feed_status,
    search_suggestions,
)
from picwise_providers.normalization import extract_merchant_name, is_valid_http_url
# Read, not changed: the columns a product's barcode and maker's code are read from, as
# the selection reads them to know one product in several shops.
from picwise_providers.search_selection import (
    _GTIN_KEYS,
    _GTIN_LENGTHS,
    _MPN_KEYS,
    _raw_value_any_case,
)
from picwise_surface import (
    provider_feed_cards_will_render,
    render_about_page,
    render_affiliate_disclosure_page,
    render_branded_not_found_page,
    render_contact_page,
    render_cookies_page,
    render_demo_info_page,
    render_picwise_reference_surface,
    render_privacy_page,
    render_terms_page,
)
from picwise_surface.seo import robots_txt
from picwise_ai.store import assist_directory

from .assist_wiring import assist_status, resolve_with_assist
from .query_log_sink import QUERY_LOG_SINK

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
    "/about",
    "/search",
    "/results",
    "/picwise-reference",
    "/out/feed",
    "/private-beta-readiness",
    "/best/{slug}",
    "/sitemap-buying-pages.xml",
    "/sitemap.xml",
    "/robots.txt",
)

# What crawlers may fetch while the site is built (owner, 2026-10-23: «προστάτεψε το
# site από την google όσο το χτίζουμε»). Kept off: the redirect to the shops, which
# records a click, and two routes that act when called. The search is not blocked here:
# its pages carry `noindex`, which Google reads only on a page it may fetch, so it is
# blocked once Google has dropped them (docs/PICWISE_GOOGLE_PAGES_SPEC.md, section 2).
# It also names the sitemap of the pages Google may index (`picwise_surface.seo`).
ROBOTS_TXT = robots_txt()
# Answers that are not pages, such as the JSON routes, carry this header instead.
NOINDEX_HEADER = ("X-Robots-Tag", "noindex")
# What every answer tells the browser to refuse (the audit, 2026-11-10: the live site sent
# only Strict-Transport-Security, from its front door). A page of the site runs its own
# scripts and styles, written into it; shows the shops' photos from the shops' servers;
# asks only the site itself for anything; is never shown inside another site's page; and
# sends a form nowhere but here. A photo's address is the shop's, http or https, as the
# feed gives it. The microphone is for the search by voice, asked for only when the
# visitor presses its button; nothing else of the device is used.
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' https: http: data:; connect-src 'self'; manifest-src 'self'; "
    "object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
)
SECURITY_HEADERS = (
    ("Content-Security-Policy", CONTENT_SECURITY_POLICY),
    ("X-Content-Type-Options", "nosniff"),
    ("X-Frame-Options", "DENY"),
    ("Referrer-Policy", "strict-origin-when-cross-origin"),
    ("Permissions-Policy", "camera=(), geolocation=(), payment=(), usb=(), microphone=(self)"),
)
# How long a browser may keep what does not change between deployments or within the
# hour: the site's own files (its icons), and the pages that say who runs PicWise. A
# search's page is never kept: its products are the catalogue's of that moment.
ASSET_CACHE_CONTROL = "public, max-age=604800"
INFO_PAGE_CACHE_CONTROL = "public, max-age=3600"


_GTIN_NAMES = {13: "EAN", 12: "UPC", 8: "EAN-8", 14: "GTIN"}


def single_product_code(resolution: Any) -> str:
    """The barcode, else the maker's part number, of the one product of an answer that
    has only one, as its shop gives it: "EAN 5012345678900", "Part no. KT-17".

    For that product's own layout (owner, 2026-10-31; the design's single product). Read
    from the shop's row, found again by its id with the eligibility re-checked, as a
    click on it is; "" when the shop gives neither, or for any other answer.
    """
    if not getattr(resolution, "provider_feed_price_first", False):
        return ""
    products = tuple(getattr(resolution, "provider_feed_selected_products", ()) or ())
    if len(products) != 1 or int(getattr(resolution, "provider_feed_total_count", 0) or 0) > 1:
        return ""
    product = resolve_card_eligible_provider_feed_product_by_id(
        str(products[0].get("provider_product_id") or "")
    )
    if product is None:
        return ""
    raw = product.raw if isinstance(product.raw, dict) else {}
    gtin = re.sub(r"\D", "", _raw_value_any_case(raw, _GTIN_KEYS))
    if len(gtin) in _GTIN_LENGTHS and gtin.strip("0"):
        return f"{_GTIN_NAMES.get(len(gtin), 'GTIN')} {gtin}"
    part_number = _raw_value_any_case(raw, _MPN_KEYS)
    return f"Part no. {part_number}" if part_number else ""


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
        self._feed_outbound_click_events: list[dict[str, str]] = []
        self._decision_impression_events: list[dict[str, str]] = []

    def health_payload(self) -> dict[str, Any]:
        from picwise_search_memory.search_runtime_artifact import get_search_runtime_artifact_status

        return {
            "status": "ok",
            "app": "picwise_local_app",
            "mode": "local_non_live",
            "domain_plan_primary": "picwise.subby.cloud",
            "search_runtime_artifact": get_search_runtime_artifact_status(),
        }

    def demo_html(self, query: str) -> str:
        _ = query
        return render_demo_info_page()

    def root_landing_html(
        self,
        query: str = "",
        *,
        shown: int = 0,
        assist_refresh: bool = False,
        min_price: float | None = None,
    ) -> str:
        """Render the landing surface, honouring an inbound purchase-intent query.

        The mission requires that a visitor arriving from Google on
        `/?q=<purchase intent>` sees the decision result immediately instead of an
        empty search page, so the query is resolved here exactly as on /search.
        With no query this stays the plain landing page, the one page here Google may
        index; with one it is a search page like any other.
        """
        return self.picwise_reference_html(
            query,
            source_page="search",
            shown=shown,
            indexable=is_empty_search_query(query),
            assist_refresh=assist_refresh,
            min_price=min_price,
        )

    def picwise_reference_html(
        self,
        query: str = "",
        *,
        source_page: str = "search",
        shown: int = 0,
        indexable: bool = False,
        assist_refresh: bool = False,
        min_price: float | None = None,
    ) -> str:
        """The search page. `shown` is how many products "More" has opened the page to;
        `min_price` the price the buyer chose on the price bar (owner, 2026-11-12).

        Not `indexable` unless it is the home page without a search: Google is told not
        to index the site's own search (owner, 2026-10-23).

        A complex search on a server with the AI layer (`assist_wiring`): the products that
        fit first and marked, from the stored answer, or a job written and an empty place
        the page's script fills (owner, 2026-11-06). `assist_refresh` is that script
        reading the page again: no job is written and no second impression counted.
        """
        assist = None
        if is_empty_search_query(query):
            resolution = empty_landing_search_resolution(query)
        elif assist_directory() is None or min_price is not None:
            # A server without the AI layer searches exactly as before it. So does a page
            # whose buyer chose a price on the price bar: the AI layer is not asked again
            # for every price (its daily spend is capped), and the order is the usual one.
            resolution = (
                resolve_live_search(query, shown=shown)
                if min_price is None
                else resolve_live_search(query, shown=shown, min_price=min_price)
            )
        else:
            resolution, assist = resolve_with_assist(query, shown=shown, write_jobs=not assist_refresh)
        html = render_picwise_reference_surface(
            query=query,
            resolution=resolution,
            source_page=source_page,
            catalogue=peek_search_catalogue_counts(),
            indexable=indexable,
            single_product_code=single_product_code(resolution),
            assist=assist,
        )
        if not assist_refresh:
            self.record_decision_impression(
                query=query,
                source_page=source_page,
                resolution=resolution,
            )
        # Where the feed's products answer, the catalogue asks which one is meant ("What
        # kind of cable?") when it has several, and the vocabulary's older "too broad"
        # list, of words the catalogue may not have, does not ask too: one question, one
        # logic (owner, 2026-10-29). It stays for a broad word with nothing to show.
        if resolution.resolver_state == "broad_query_suggestions" and not provider_feed_cards_will_render(
            resolution
        ):
            html = _inject_broad_query_suggestions(html, resolution)
        elif getattr(resolution, "did_you_mean", ()) and not provider_feed_cards_will_render(resolution):
            html = _inject_did_you_mean(html, resolution)
        elif SEARCH_IN_ENGLISH_REASON in tuple(getattr(resolution, "reason_codes", ()) or ()):
            html = _inject_search_in_english(html)
        if is_empty_search_query(query):
            schedule_search_warmup_if_needed()
        return html

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

    def about_html(self) -> str:
        return render_about_page()

    def not_found_html(self) -> str:
        return render_branded_not_found_page()

    def search_suggestions_json(self) -> str:
        """The search box's suggestions as JSON: `{"v": 1, "suggestions": [...]}`, the
        larger first. Empty when no feed is connected; the box then suggests nothing."""
        return json.dumps(
            {"v": 1, "suggestions": [suggestion.text for suggestion in search_suggestions()]},
            ensure_ascii=False,
            separators=(",", ":"),
        )

    def mvp_search_html(
        self,
        query: str,
        *,
        source_page: str = "search",
        shown: int = 0,
        assist_refresh: bool = False,
        min_price: float | None = None,
    ) -> str:
        return self.picwise_reference_html(
            query, source_page=source_page, shown=shown, assist_refresh=assist_refresh, min_price=min_price
        )

    def assist_status_json(self, key: str) -> str:
        """What the search page's script is told of a complex search's answer
        (`assist_wiring.assist_status`)."""
        return json.dumps(assist_status(key), separators=(",", ":"))

    def record_decision_impression(
        self,
        *,
        query: str,
        source_page: str,
        resolution: Any,
    ) -> list[dict[str, str]]:
        """Record the impression side of the tracking contract for one rendered page.

        Event names follow docs/TRACKING_EVENTS_SPEC.md. `choices_shown` and
        `recommended_shown` are emitted only when the surface actually renders the
        cards, read from the renderer's own gate, so an event never claims choices
        were shown on a page that refused to show them. Fields PicWise does not have
        use the missing-data enum rather than invented values, and no conversion or
        revenue is ever recorded here.
        """
        timestamp = (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )
        safe_source = (
            source_page
            if source_page in {"search", "results", "landing", "reference", "unknown"}
            else "unknown"
        )
        safe_query = " ".join(str(query or "").split())
        base = {
            "timestamp": timestamp,
            "query": safe_query or MissingDataState.NOT_APPLICABLE.value,
            "source_page": safe_source,
            "resolver_state": str(getattr(resolution, "resolver_state", "") or "")
            or MissingDataState.UNKNOWN.value,
            "session_id": MissingDataState.NOT_CONNECTED.value,
            "conversion_value": MissingDataState.NOT_APPLICABLE.value,
            "revenue_value": MissingDataState.NOT_APPLICABLE.value,
        }
        events: list[dict[str, str]] = [dict(base, event_name="page_impression")]
        cards_rendered = provider_feed_cards_will_render(resolution)
        if safe_query:
            # What the NLU understood, so queries it could not read -- or read only
            # through a typo correction -- can be reviewed and taught to the lexicon.
            # This is the NLU's training signal; see tools/nlu_mistake_report.py.
            served = dict(
                base,
                event_name="query_served",
                understood_concept=str(
                    getattr(resolution, "understood_concept_id", "") or ""
                )
                or MissingDataState.UNKNOWN.value,
                understood_by_correction=(
                    "true" if getattr(resolution, "understood_by_correction", False) else "false"
                ),
                choices_rendered="true" if cards_rendered else "false",
            )
            events.append(served)
            # Kept beyond this process only when a query log store is configured.
            QUERY_LOG_SINK.record(served)

        if cards_rendered:
            selected = list(getattr(resolution, "provider_feed_selected_products", ()) or ())
            shown_count = len(selected)
            if getattr(resolution, "provider_feed_price_first", False):
                # The page holds the first page and every four "More" opened.
                shown_count += len(getattr(resolution, "provider_feed_more_products", ()) or ())
            events.append(
                dict(
                    base,
                    event_name="choices_shown",
                    choice_count=str(shown_count),
                    provider_id=str(
                        (selected[0].get("provider_key") if selected else "") or ""
                    )
                    or MissingDataState.UNKNOWN.value,
                )
            )
            recommended_id = str(
                getattr(resolution, "provider_feed_recommended_product_id", "") or ""
            )
            if recommended_id:
                events.append(
                    dict(
                        base,
                        event_name="recommended_shown",
                        choice_id=recommended_id,
                        recommendation_confidence=str(
                            getattr(
                                resolution, "provider_feed_recommendation_confidence", ""
                            )
                            or ""
                        )
                        or MissingDataState.UNKNOWN.value,
                    )
                )
        else:
            events.append(
                dict(
                    base,
                    event_name="choices_shown",
                    choice_count="0",
                    provider_id=MissingDataState.NOT_CONNECTED.value,
                )
            )

        self._decision_impression_events.extend(events)
        if len(self._decision_impression_events) > 400:
            self._decision_impression_events = self._decision_impression_events[-400:]
        return events

    def get_decision_impression_events(self) -> list[dict[str, str]]:
        return list(self._decision_impression_events)

    def clear_decision_impression_events(self) -> None:
        self._decision_impression_events = []

    def resolve_outbound_feed_redirect(self, product_id: str) -> dict[str, str] | None:
        """Resolve a provider-feed product id to a validated redirect target.

        Returns None when the id is unknown or the product is no longer
        card-eligible, so a stale link cannot send a buyer to an offer PicWise
        would refuse to show now.
        """
        product = resolve_card_eligible_provider_feed_product_by_id(product_id)
        if product is None:
            return None
        target_url = str(product.product_url or "").strip()
        if not is_valid_http_url(target_url):
            return None
        raw = product.raw if isinstance(product.raw, dict) else {}
        return {
            "redirect_url": target_url,
            "provider_key": str(product.provider_key or "").strip() or "unknown",
            "merchant_name": extract_merchant_name(raw) or "unknown",
        }

    def record_feed_outbound_click(
        self,
        *,
        product_id: str,
        query: str,
        source_page: str,
        is_recommended: bool | None,
        provider_key: str,
        merchant_name: str,
        redirect_url: str,
        event_name: str,
    ) -> dict[str, str]:
        """Record one real outbound click on a provider-feed card.

        Event names follow docs/TRACKING_EVENTS_SPEC.md. Fields PicWise does not
        genuinely have are written with the missing-data enum instead of invented
        values: there is no session or brain/depth context on this route, and no
        conversion or revenue is ever recorded here.
        """
        if is_recommended is None:
            recommended_field = MissingDataState.UNKNOWN.value
        else:
            recommended_field = "true" if is_recommended else "false"
        event = {
            "timestamp": datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
            "event_name": event_name,
            "choice_id": str(product_id or "").strip() or MissingDataState.UNKNOWN.value,
            "query": " ".join(str(query or "").split()) or MissingDataState.UNKNOWN.value,
            "source_page": source_page
            if source_page in {"search", "results", "landing", "unknown"}
            else "unknown",
            "is_recommended": recommended_field,
            "provider_id": str(provider_key or "").strip() or MissingDataState.UNKNOWN.value,
            "merchant_name": str(merchant_name or "").strip() or MissingDataState.UNKNOWN.value,
            "redirect_url": str(redirect_url or "").strip() or MissingDataState.UNKNOWN.value,
            "session_id": MissingDataState.NOT_CONNECTED.value,
            "conversion_value": MissingDataState.NOT_APPLICABLE.value,
            "revenue_value": MissingDataState.NOT_APPLICABLE.value,
        }
        self._feed_outbound_click_events.append(event)
        if len(self._feed_outbound_click_events) > 200:
            self._feed_outbound_click_events = self._feed_outbound_click_events[-200:]
        return event

    def get_feed_outbound_click_events(self) -> list[dict[str, str]]:
        return list(self._feed_outbound_click_events)

    def get_feed_outbound_click_count(self) -> int:
        return len(self._feed_outbound_click_events)

    def clear_feed_outbound_click_events(self) -> None:
        self._feed_outbound_click_events = []

    def private_beta_readiness_payload(self) -> dict[str, Any]:
        # Report the feed the site actually serves from, not the MVP flow's local
        # fixture, which would call the source "connected" with no feed configured.
        feed_status = resolve_provider_feed_status().status
        report = build_mvp_private_beta_readiness_report(production_feed_status=feed_status)
        return {
            "status": report.status.value,
            "sample_flow_state": report.sample_flow_state,
            "reason_codes": list(report.reason_codes),
            "checks": [
                {"key": check.key, "status": check.status.value, "details": check.details}
                for check in report.checks
            ],
            # Whether the feed above is answered from the build's prepared file (step 5).
            "prepared_feed": prepared_catalogue_status(),
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


def _replace_disclaimer(html: str, replacement: str) -> str:
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


def _inject_did_you_mean(html: str, resolution: Any) -> str:
    """Ask which product was meant when a search was not understood.

    The suggestions are links to a new search, never results: a correction too
    uncertain to act on may still be worth asking about.
    """
    links = [
        f'<a href="/search?q={quote(str(name), safe="")}">{escape(str(name))}</a>'
        for name in getattr(resolution, "did_you_mean", ())
    ]
    if not links:
        return html
    text = "PicWise did not recognise this search. Did you mean: " + ", ".join(links) + "?"
    return _without_examples(_replace_disclaimer(html, f'<p class="pw-reference-disclaimer">{text}</p>'))


def _without_examples(html: str) -> str:
    """A page that offers its own searches ("Did you mean", "Try") does not add the two
    general ones under "No products found" (`reference._no_products_try_html`)."""
    start = html.find('<section class="pw-empty-state">')
    end = html.find("</section>", start) if start != -1 else -1
    if start == -1 or end == -1:
        return html
    return html[:start] + '<section class="pw-empty-state"></section>' + html[end + len("</section>") :]


def _inject_search_in_english(html: str) -> str:
    """Say that PicWise searches in English, for a search in Greek letters (owner,
    2026-11-07: «Ναι σε όλα, κλείσε και τα δύο»)."""
    text = "PicWise searches in English. Please type the product's name in English."
    return _replace_disclaimer(html, f'<p class="pw-reference-disclaimer">{text}</p>')


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
    return _without_examples(_replace_disclaimer(html, replacement))


class PicwiseRequestHandler(BaseHTTPRequestHandler):
    """The local server: every request answered by the site's one table of routes
    (`routes.answer`) with this handler's `app`, as the server answers it with its own
    (the clean-up of 2026-11-12; until then this class held a second copy of every
    route). A method other than GET is answered by the routes too (405), as on the
    server."""

    app = PicwiseLocalApp()

    def do_GET(self) -> None:  # noqa: N802
        self._answer("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._answer("POST")

    def do_HEAD(self) -> None:  # noqa: N802
        self._answer("HEAD")

    def _answer(self, method: str) -> None:
        # Here, not at the top: `routes` imports this module.
        from .routes import answer

        parsed = urlparse(self.path)
        host = self.headers.get("Host", "127.0.0.1:8016")
        environ: dict[str, object] = {
            "REQUEST_METHOD": method,
            "PATH_INFO": unquote(parsed.path or "/"),
            "QUERY_STRING": parsed.query,
            "HTTP_HOST": host,
            "SERVER_NAME": host.split(":")[0],
            "SERVER_PORT": str(self.server.server_address[1]),
            "wsgi.url_scheme": "http",
        }
        for name, value in self.headers.items():
            key = "HTTP_" + name.upper().replace("-", "_")
            environ.setdefault(key, value)
        held: dict[str, object] = {}

        def start_response(status: str, headers: list[tuple[str, str]]) -> None:
            held["status"], held["headers"] = status, headers

        body = b"".join(answer(environ, start_response, self.app))
        code, _space, reason = str(held["status"]).partition(" ")
        self.send_response(int(code), reason)
        for name, value in held["headers"]:  # type: ignore[union-attr]
            self.send_header(name, value)
        self.end_headers()
        if method != "HEAD":
            self.wfile.write(body)


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

