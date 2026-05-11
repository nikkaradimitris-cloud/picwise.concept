from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .contracts import OfferCandidate, OfferIntakeResult, ProductSourceRecord, ProductSourceStatus


def _retail_fixture_candidates(source: ProductSourceRecord) -> tuple[OfferCandidate, ...]:
    base = {
        "source_id": source.source_id,
        "source_type": source.source_type,
        "vertical": "retail_physical_products",
        "engine": "electronics_hypermarket",
        "category_bucket": "power_banks",
        "google_taxonomy_path": "Electronics > Electronics Accessories > Power Banks",
        "saas_erp_contract_ref": None,
        "finance_insurance_contract_ref": None,
        "metadata": {"fixture": True, "network": "disabled"},
    }
    return (
        OfferCandidate(
            candidate_id="retail-pb-1",
            title="TravelCore 20K Power Bank",
            brand="TravelCore",
            model="20K",
            image_url="https://example.com/images/travelcore-20k.jpg",
            price=29.0,
            currency="EUR",
            seller_name="Example Store A",
            seller_url="https://example.com/stores/a",
            availability_status="available",
            outbound_url="https://example.com/products/travelcore-20k",
            affiliate_url="https://example.invalid/aff/travelcore-20k",
            category="power_bank",
            source_updated_at="2026-05-01T09:00:00Z",
            **base,
        ),
        OfferCandidate(
            candidate_id="retail-pb-2",
            title="DailyBalance PD20 Power Bank",
            brand="DailyBalance",
            model="PD20",
            image_url="https://example.com/images/dailybalance-pd20.jpg",
            price=37.0,
            currency="EUR",
            seller_name="Example Store B",
            seller_url="https://example.com/stores/b",
            availability_status="limited",
            outbound_url="https://example.com/products/dailybalance-pd20",
            affiliate_url=None,
            category="power_bank",
            source_updated_at="2026-05-01T09:00:00Z",
            **base,
        ),
        OfferCandidate(
            candidate_id="retail-pb-3",
            title="EverydaySure 22.5W Power Bank",
            brand="EverydaySure",
            model="22.5W",
            image_url="https://example.com/images/everydaysure-225w.jpg",
            price=44.0,
            currency="EUR",
            seller_name="Example Store C",
            seller_url="https://example.com/stores/c",
            availability_status="available",
            outbound_url="https://example.com/products/everydaysure-225w",
            affiliate_url="https://example.invalid/aff/everydaysure-225w",
            category="power_bank",
            source_updated_at="2026-05-01T09:00:00Z",
            **base,
        ),
        OfferCandidate(
            candidate_id="retail-pb-4",
            title="PowerMax Elite 25K",
            brand="PowerMax",
            model="Elite 25K",
            image_url="https://example.com/images/powermax-25k.jpg",
            price=59.0,
            currency="EUR",
            seller_name="Example Store D",
            seller_url="https://example.com/stores/d",
            availability_status="available",
            outbound_url="https://example.com/products/powermax-25k",
            affiliate_url="https://example.invalid/aff/powermax-25k",
            category="power_bank",
            source_updated_at="2026-05-01T09:00:00Z",
            **base,
        ),
        OfferCandidate(
            candidate_id="retail-pb-5",
            title="TripFlex 18K",
            brand="TripFlex",
            model="18K",
            image_url="https://example.com/images/tripflex-18k.jpg",
            price=33.0,
            currency="EUR",
            seller_name="Example Store E",
            seller_url="https://example.com/stores/e",
            availability_status="available",
            outbound_url="https://example.com/products/tripflex-18k",
            affiliate_url=None,
            category="power_bank",
            source_updated_at="2026-05-01T09:00:00Z",
            **base,
        ),
    )


def _saas_fixture_candidates(source: ProductSourceRecord) -> tuple[OfferCandidate, ...]:
    base = {
        "source_id": source.source_id,
        "source_type": source.source_type,
        "vertical": "software_saas_erp",
        "engine": None,
        "category_bucket": "saas_erp_tools",
        "google_taxonomy_path": None,
        "saas_erp_contract_ref": "saas_erp_stage28e_contract",
        "finance_insurance_contract_ref": None,
        "metadata": {"fixture": True, "network": "disabled"},
    }
    return (
        OfferCandidate(
            candidate_id="saas-erp-1",
            title="FlowLedger ERP Cloud",
            brand="FlowLedger",
            model="ERP Cloud",
            image_url="https://example.com/images/flowledger.jpg",
            price=79.0,
            currency="EUR",
            seller_name="FlowLedger",
            seller_url="https://example.com/vendors/flowledger",
            availability_status="available",
            outbound_url="https://example.com/saas/flowledger-erp",
            affiliate_url=None,
            category="erp_software",
            source_updated_at="2026-05-01T09:00:00Z",
            **base,
        ),
        OfferCandidate(
            candidate_id="saas-erp-2",
            title="OpsCanvas ERP Starter",
            brand="OpsCanvas",
            model="Starter",
            image_url="https://example.com/images/opscanvas.jpg",
            price=59.0,
            currency="EUR",
            seller_name="OpsCanvas",
            seller_url="https://example.com/vendors/opscanvas",
            availability_status="available",
            outbound_url="https://example.com/saas/opscanvas-erp",
            affiliate_url=None,
            category="erp_software",
            source_updated_at="2026-05-01T09:00:00Z",
            **base,
        ),
    )


def _finance_fixture_candidates(source: ProductSourceRecord) -> tuple[OfferCandidate, ...]:
    base = {
        "source_id": source.source_id,
        "source_type": source.source_type,
        "vertical": "finance_insurance_business_finance",
        "engine": None,
        "category_bucket": "finance_tools",
        "google_taxonomy_path": None,
        "saas_erp_contract_ref": None,
        "finance_insurance_contract_ref": "finance_insurance_stage28f_contract",
        "metadata": {
            "fixture": True,
            "regulated": True,
            "network": "disabled",
            "requires_manual_review": True,
        },
    }
    return (
        OfferCandidate(
            candidate_id="finance-1",
            title="Business Expense Tracker Pro",
            brand="LedgerWise",
            model="Pro",
            image_url="https://example.com/images/ledgerwise-pro.jpg",
            price=19.0,
            currency="EUR",
            seller_name="LedgerWise",
            seller_url="https://example.com/vendors/ledgerwise",
            availability_status="available",
            outbound_url="https://example.com/finance/ledgerwise-pro",
            affiliate_url=None,
            category="business_finance_tool",
            source_updated_at="2026-05-01T09:00:00Z",
            **base,
        ),
    )


class LocalFixtureOfferSourceAdapter:
    """Stage32 deterministic non-network source adapter."""

    def fetch(
        self,
        *,
        query: str,
        search_decision: dict[str, Any],
        local_nlu_intent: dict[str, Any],
        source: ProductSourceRecord,
    ) -> OfferIntakeResult:
        lowered = query.lower()
        category = str(local_nlu_intent.get("category") or "").lower()
        route_type = str(search_decision.get("route_type") or "")
        if route_type == "no_safe_result":
            return OfferIntakeResult(
                source=source,
                status=ProductSourceStatus.NEEDS_DATA,
                candidates=tuple(),
                reason_codes=("query_not_actionable",),
                metadata={"source_adapter": "LocalFixtureOfferSourceAdapter"},
            )
        if any(token in lowered for token in ("finance", "insurance", "loan", "credit")):
            candidates = _finance_fixture_candidates(source)
        elif any(token in lowered for token in ("saas", "erp", "software")) or category in {
            "saas",
            "software",
            "erp",
        }:
            candidates = _saas_fixture_candidates(source)
        else:
            candidates = _retail_fixture_candidates(source)
        return OfferIntakeResult(
            source=source,
            status=ProductSourceStatus.CONNECTED,
            candidates=tuple(candidates),
            reason_codes=("fixture_source_connected",),
            metadata={
                "source_adapter": "LocalFixtureOfferSourceAdapter",
                "candidate_count": len(candidates),
                "snapshot": [asdict(candidate) for candidate in candidates[:1]],
            },
        )
