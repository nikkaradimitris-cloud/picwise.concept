from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any, Mapping, Protocol

from picwise_contracts import (
    ContractValidationError,
    MissingDataState,
    validate_missing_data_states,
)


class FeedValidationError(ContractValidationError):
    """Raised when a feed payload violates Picwise feed safety rules."""


@dataclass(frozen=True)
class FeedAdapterResult:
    candidates: list[dict[str, Any]]
    source_metadata: dict[str, Any]
    missing_data_states: list[MissingDataState]


class FeedAdapterProtocol(Protocol):
    def fetch_candidates(self, query: str) -> FeedAdapterResult:
        """Return engine-compatible candidate dictionaries for a query."""


@dataclass(frozen=True)
class FeedSourceConfig:
    source_type: str
    source_url: str
    api_key: str


@dataclass(frozen=True)
class FeedReadiness:
    status: str
    reason: str


class FeedTransportProtocol(Protocol):
    def fetch_candidates(self, query: str, config: FeedSourceConfig) -> list[dict[str, Any]]:
        """Fetch raw feed candidates from a configured source."""


class NoopFeedTransport:
    def fetch_candidates(self, query: str, config: FeedSourceConfig) -> list[dict[str, Any]]:
        _ = (query, config)
        return []


FORBIDDEN_FEED_KEYS = {
    "reviews",
    "review_count",
    "rating",
    "ratings",
    "fake_review",
    "fake_reviews",
    "fake_rating",
    "fake_ratings",
    "fake_revenue",
    "fake_conversion",
    "fake_conversions",
    "fake_savings",
    "fake_urgency",
    "fake_confidence",
    "fake_ai_confidence",
    "fake_price",
    "fake_prices",
    "fake_availability",
    "commission",
    "commission_score",
    "commission_rank",
    "commission_ranking",
    "rank_by_commission",
    "recommend_by_commission",
    "rank_by_commission_rate",
    "commission_weight",
}

FORBIDDEN_FAKE_VALUE_MARKERS = (
    "fake review",
    "fake rating",
    "fake price",
    "fake availability",
    "fake revenue",
    "fake conversion",
    "fake savings",
    "fake urgency",
    "fake confidence",
    "fake ai confidence",
)


def _contains_forbidden_keys(payload: Any) -> list[str]:
    found: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            lowered_key = str(key).lower()
            if lowered_key in FORBIDDEN_FEED_KEYS:
                found.append(str(key))
            found.extend(_contains_forbidden_keys(value))
    elif isinstance(payload, list):
        for item in payload:
            found.extend(_contains_forbidden_keys(item))
    return found


def _contains_forbidden_markers(payload: Any) -> list[str]:
    found: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            found.extend(_contains_forbidden_markers(key))
            found.extend(_contains_forbidden_markers(value))
    elif isinstance(payload, list):
        for item in payload:
            found.extend(_contains_forbidden_markers(item))
    elif isinstance(payload, str):
        lowered = payload.lower()
        for marker in FORBIDDEN_FAKE_VALUE_MARKERS:
            if marker in lowered:
                found.append(payload)
    return found


def _normalize_missing_states(raw_states: list[str] | None) -> list[MissingDataState]:
    if not raw_states:
        return [MissingDataState.UNKNOWN]
    validate_missing_data_states(raw_states)
    return [MissingDataState(state) for state in raw_states]


def _normalize_feed_candidate(
    candidate: dict[str, Any],
    source_id: str,
    *,
    data_origin: str,
    data_classification: str,
) -> dict[str, Any]:
    alias_map = {
        "id": "product_id",
        "provider": "merchant_or_provider",
        "merchant": "merchant_or_provider",
        "price": "price_or_cost_display",
        "price_display": "price_or_cost_display",
        "cta_text": "cta_label",
        "redirect_url": "redirect_target",
        "risk_or_limitation": "risks_or_limitations",
    }
    normalized = dict(candidate)
    for old_name, new_name in alias_map.items():
        if old_name in normalized and new_name not in normalized:
            normalized[new_name] = normalized[old_name]

    required_fields = (
        "product_id",
        "title",
        "merchant_or_provider",
        "price_or_cost_display",
        "role",
        "decision_label",
        "subtitle",
        "key_reasons",
        "risks_or_limitations",
        "cta_label",
        "redirect_target",
    )
    missing = [field for field in required_fields if field not in normalized]
    if missing:
        raise FeedValidationError(f"Feed candidate missing required fields: {missing}")

    metadata = dict(normalized.get("tracking_metadata", {}))
    metadata.update(
        {
            "provider_id": str(normalized.get("provider_id", normalized["merchant_or_provider"])),
            "merchant_or_provider": str(normalized["merchant_or_provider"]),
            "source_id": source_id,
            "data_origin": data_origin,
            "data_classification": data_classification,
        }
    )
    normalized["tracking_metadata"] = metadata
    return normalized


class LocalFixtureFeedAdapter:
    """Local non-production fixture adapter for demo/testing only."""

    def __init__(self) -> None:
        self._source_id = "local_fixture_feed_v1"

    def fetch_candidates(self, query: str) -> FeedAdapterResult:
        if not query or not query.strip():
            raise FeedValidationError("Query is required for feed adapter.")
        fixtures = self._build_fixture_candidates()
        normalized = validate_feed_candidates(
            fixtures,
            source_id=self._source_id,
            data_origin="local_test_fixture",
            data_classification="not_production_data",
        )
        return FeedAdapterResult(
            candidates=normalized,
            source_metadata={
                "adapter": "LocalFixtureFeedAdapter",
                "source_id": self._source_id,
                "local_test_fixture": True,
                "not_production_data": True,
            },
            missing_data_states=_normalize_missing_states(["data_not_yet", "unknown"]),
        )

    def _build_fixture_candidates(self) -> list[dict[str, Any]]:
        return [
            {
                "product_id": "fixture-p1",
                "title": "TravelCore 20K",
                "merchant_or_provider": "FixtureMerchantA",
                "price_or_cost_display": "EUR 29-34",
                "role": "budget",
                "decision_label": "Budget pick for occasional travel charging",
                "subtitle": "EUR 29-34 • Lightweight • Basic reliability",
                "key_reasons": ["Compact size", "Simple cable setup", "Widely available"],
                "risks_or_limitations": "Lower sustained output under heavy load.",
                "cta_label": "View in Store",
                "redirect_target": "https://example.com/fixture/p1",
            },
            {
                "product_id": "fixture-p2",
                "title": "DailyBalance PD20",
                "merchant_or_provider": "FixtureMerchantB",
                "price_or_cost_display": "EUR 37-45",
                "role": "value",
                "decision_label": "Value pick with stable everyday compatibility",
                "subtitle": "EUR 37-45 • USB-C PD • Lower mismatch risk",
                "key_reasons": ["Balanced output", "Reliable compatibility", "Solid build quality"],
                "risks_or_limitations": "Slightly heavier than compact alternatives.",
                "cta_label": "Go to Store",
                "redirect_target": "https://example.com/fixture/p2",
            },
            {
                "product_id": "fixture-p3",
                "title": "EverydaySure 22.5W",
                "merchant_or_provider": "FixtureMerchantC",
                "price_or_cost_display": "EUR 44-52",
                "role": "best_overall",
                "decision_label": "Best overall fit for frequent charging routines",
                "subtitle": "EUR 44-52 • Strong output • Better long-run reliability",
                "key_reasons": ["Consistent charging speed", "Good cable support", "Trusted warranty terms"],
                "risks_or_limitations": "Price sits above entry-level options.",
                "cta_label": "View Details and Buy",
                "redirect_target": "https://example.com/fixture/p3",
            },
            {
                "product_id": "fixture-p4",
                "title": "PowerMax Elite 25K",
                "merchant_or_provider": "FixtureMerchantD",
                "price_or_cost_display": "EUR 59-69",
                "role": "premium",
                "decision_label": "Premium pick for heavy and multi-device usage",
                "subtitle": "EUR 59-69 • Higher capacity • Better sustained output",
                "key_reasons": ["High capacity headroom", "Premium thermal design", "Extended accessory kit"],
                "risks_or_limitations": "Higher price and larger carry footprint.",
                "cta_label": "View in Store",
                "redirect_target": "https://example.com/fixture/p4",
            },
            {
                "product_id": "fixture-p5",
                "title": "TripFlex 18K",
                "merchant_or_provider": "FixtureMerchantE",
                "price_or_cost_display": "EUR 33-39",
                "role": "value",
                "decision_label": "Alternative value option for lighter travel packs",
                "subtitle": "EUR 33-39 • Compact profile • Flexible cables",
                "key_reasons": ["Good portability", "Simple usage", "Decent output profile"],
                "risks_or_limitations": "Lower top-end performance than premium devices.",
                "cta_label": "Go to Store",
                "redirect_target": "https://example.com/fixture/p5",
            },
        ]


class ConfiguredFeedAdapter:
    """Live-ready feed adapter that is config-driven and test-safe by default."""

    def __init__(
        self,
        *,
        config: FeedSourceConfig,
        transport: FeedTransportProtocol | None = None,
    ) -> None:
        self._config = config
        self._transport = transport or NoopFeedTransport()
        self._source_id = f"configured_feed_{config.source_type or 'unknown'}"

    def fetch_candidates(self, query: str) -> FeedAdapterResult:
        if not query or not query.strip():
            raise FeedValidationError("Query is required for feed adapter.")
        readiness = evaluate_feed_connection_readiness(self._config)
        if readiness.status != "FEED_READY":
            return FeedAdapterResult(
                candidates=[],
                source_metadata={
                    "adapter": "ConfiguredFeedAdapter",
                    "source_id": self._source_id,
                    "status": readiness.status,
                    "reason": readiness.reason,
                },
                missing_data_states=[MissingDataState.NOT_CONNECTED, MissingDataState.DATA_NOT_YET],
            )
        raw_candidates = self._transport.fetch_candidates(query, self._config)
        normalized = validate_feed_candidates(
            raw_candidates,
            source_id=self._source_id,
            data_origin="configured_external_feed",
            data_classification="production_ready_not_verified",
        )
        return FeedAdapterResult(
            candidates=normalized,
            source_metadata={
                "adapter": "ConfiguredFeedAdapter",
                "source_id": self._source_id,
                "status": readiness.status,
                "reason": readiness.reason,
            },
            missing_data_states=[MissingDataState.DATA_NOT_YET, MissingDataState.UNKNOWN],
        )


def load_feed_source_config_from_env(
    env: Mapping[str, str] | None = None,
) -> FeedSourceConfig:
    source = env if env is not None else os.environ
    return FeedSourceConfig(
        source_type=str(source.get("PICWISE_FEED_SOURCE_TYPE", "")).strip(),
        source_url=str(source.get("PICWISE_FEED_SOURCE_URL", "")).strip(),
        api_key=str(source.get("PICWISE_FEED_API_KEY", "")).strip(),
    )


def evaluate_feed_connection_readiness(config: FeedSourceConfig) -> FeedReadiness:
    if not config.source_type or not config.source_url or not config.api_key:
        return FeedReadiness(
            status="NEEDS_REAL_FEED_CONFIG",
            reason=(
                "Missing PICWISE_FEED_SOURCE_TYPE, PICWISE_FEED_SOURCE_URL, "
                "or PICWISE_FEED_API_KEY."
            ),
        )
    return FeedReadiness(status="FEED_READY", reason="Feed config is present. Live proof still required.")


def validate_feed_candidates(
    raw_candidates: list[dict[str, Any]],
    *,
    source_id: str,
    data_origin: str = "local_test_fixture",
    data_classification: str = "not_production_data",
) -> list[dict[str, Any]]:
    forbidden = _contains_forbidden_keys(raw_candidates)
    if forbidden:
        raise FeedValidationError(
            f"Forbidden fake/commission fields in feed candidates: {sorted(set(forbidden))}"
        )
    forbidden_markers = _contains_forbidden_markers(raw_candidates)
    if forbidden_markers:
        raise FeedValidationError("Forbidden fake marker values detected in feed payload.")
    return [
        _normalize_feed_candidate(
            item,
            source_id,
            data_origin=data_origin,
            data_classification=data_classification,
        )
        for item in raw_candidates
    ]
