from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .contracts import (
    OfferIntakeResult,
    ProductSourceRecord,
    ProductSourceStatus,
    SourceTrustLevel,
)


class OfferSourceAdapter(Protocol):
    def fetch(
        self,
        *,
        query: str,
        search_decision: dict[str, Any],
        local_nlu_intent: dict[str, Any],
        source: ProductSourceRecord,
    ) -> OfferIntakeResult:
        """Return deterministic offer candidates for a source."""


@dataclass(frozen=True)
class OfferIntakeRequest:
    query: str
    search_decision: dict[str, Any]
    local_nlu_intent: dict[str, Any]
    source: ProductSourceRecord


def build_default_product_source() -> ProductSourceRecord:
    return ProductSourceRecord(
        source_id="local_fixture_offer_source_v1",
        source_type="local_fixture",
        source_label="Local Fixture Offer Source",
        status=ProductSourceStatus.CONNECTED,
        trust_level=SourceTrustLevel.PARTNER_VERIFIED,
        verticals=(
            "retail_physical_products",
            "software_saas_erp",
            "finance_insurance_business_finance",
        ),
        metadata={
            "adapter": "LocalFixtureOfferSourceAdapter",
            "network_access": "disabled",
            "scraping": "not_allowed",
            "production_data": False,
        },
    )


def intake_offer_candidates(
    request: OfferIntakeRequest,
    adapter: OfferSourceAdapter,
) -> OfferIntakeResult:
    query = str(request.query or "").strip()
    if not query:
        return OfferIntakeResult(
            source=request.source,
            status=ProductSourceStatus.NEEDS_DATA,
            candidates=tuple(),
            reason_codes=("empty_query",),
            metadata={"intake_mode": "safe_empty"},
        )
    if request.source.status != ProductSourceStatus.CONNECTED:
        return OfferIntakeResult(
            source=request.source,
            status=ProductSourceStatus.NOT_CONNECTED,
            candidates=tuple(),
            reason_codes=("source_not_connected",),
            metadata={"intake_mode": "safe_not_connected"},
        )
    if request.source.trust_level == SourceTrustLevel.UNSAFE:
        return OfferIntakeResult(
            source=request.source,
            status=ProductSourceStatus.MANUAL_REVIEW,
            candidates=tuple(),
            reason_codes=("source_marked_unsafe",),
            metadata={"intake_mode": "blocked_unsafe_source"},
        )
    return adapter.fetch(
        query=query,
        search_decision=request.search_decision,
        local_nlu_intent=request.local_nlu_intent,
        source=request.source,
    )
