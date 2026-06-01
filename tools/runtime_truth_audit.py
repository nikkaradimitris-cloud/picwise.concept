"""Audit-only helper: capture runtime truth fields from resolve_live_search.

Does not modify runtime behavior. Read-only inspection for stage closure audits.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_search.live_search_resolver import resolve_live_search  # noqa: E402

_DEFAULT_FEED = Path(
    r"C:\Users\User\Desktop\picwise-private-feeds\back_to_office_clean_full_columns.csv.gz"
)

AUDIT_QUERIES = (
    "laptop",
    "dell laptop",
    "monitor",
    "mouse",
    "headphones",
    "printer",
    "toner cartridge",
    "ink cartridge",
    "logitech webcam",
    "mini pc",
    "office chair",
)


def _truth_row(product: dict) -> dict:
    raw = product.get("raw") if isinstance(product.get("raw"), dict) else {}
    return {
        "title": product.get("title"),
        "product_url": product.get("product_url"),
        "provider_key": product.get("provider_key"),
        "price_text": product.get("price_text"),
        "brand": product.get("brand") or raw.get("brand"),
        "currency": product.get("currency"),
        "product_type": product.get("product_type") or raw.get("product_type"),
        "product_type_evidence": product.get("product_type_evidence"),
        "category_evidence": product.get("category_evidence"),
        "category_text": product.get("category_text") or raw.get("category_text"),
        "card_eligible": product.get("card_eligible"),
        "availability_state": product.get("availability_state"),
        "availability_source_field": product.get("availability_source_field"),
        "feed_availability_signal": product.get("feed_availability_signal"),
        "purchasability_state": product.get("purchasability_state"),
        "verified_purchasable": product.get("verified_purchasable"),
        "recommendation_confidence": product.get("recommendation_confidence"),
        "recommendation_confidence_ceiling": product.get("recommendation_confidence_ceiling"),
        "verification_source": product.get("verification_source"),
        "verification_confidence": product.get("verification_confidence"),
        "buy_button_seen": product.get("buy_button_seen"),
        "out_of_stock_seen": product.get("out_of_stock_seen"),
        "card_eligibility_reason_codes": product.get("card_eligibility_reason_codes"),
    }


def audit_query(query: str) -> dict:
    resolution = resolve_live_search(query)
    products = [
        _truth_row(dict(p)) for p in resolution.provider_feed_selected_products
    ]
    return {
        "query": query,
        "decision_status": resolution.provider_feed_decision_status,
        "selection_status": resolution.provider_feed_selection_status,
        "resolver_state": resolution.resolver_state,
        "provider_feed_status": resolution.provider_feed_status,
        "selected_count": resolution.provider_feed_selected_count,
        "recommended_product_id": resolution.provider_feed_recommended_product_id,
        "recommendation_reason_codes": list(resolution.provider_feed_recommendation_reason_codes),
        "recommendation_confidence": resolution.provider_feed_recommendation_confidence,
        "resolver_reason_codes": list(resolution.reason_codes),
        "selected_products": products,
        "result_allowed": resolution.result_allowed,
        "provider_key": resolution.provider_key,
    }


def main() -> None:
    if not os.environ.get("AWIN_FEED_FILE") and _DEFAULT_FEED.is_file():
        os.environ["AWIN_FEED_FILE"] = str(_DEFAULT_FEED)
    results = [audit_query(q) for q in AUDIT_QUERIES]
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
