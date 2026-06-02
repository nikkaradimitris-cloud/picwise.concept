"""Audit-only: verify a small sample of provider product pages after feed selection.

Does not modify live search. Safe to run manually from PowerShell.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_providers.offer_health import (  # noqa: E402
    build_feed_availability_context,
    evaluate_product_eligibility,
)
from picwise_providers.purchasability_verifier import (  # noqa: E402
    merge_verification_into_product_raw,
    verify_product_page_purchasability,
)
from picwise_providers.search_selection import (  # noqa: E402
    provider_product_to_backend_dict,
)
from picwise_providers.state import (  # noqa: E402
    resolve_search_provider_feed_product_selection,
)

_DEFAULT_FEED = Path(
    r"C:\Users\User\Desktop\picwise-private-feeds\back_to_office_clean_full_columns.csv.gz"
)
_DEFAULT_LIMIT = 4


def _truth_row_from_verified(product_dict: dict) -> dict:
    return {
        "title": product_dict.get("title"),
        "product_url": product_dict.get("product_url"),
        "verifier_run": product_dict.get("verification_source") == "page_verifier",
        "verification_source": product_dict.get("verification_source"),
        "verification_confidence": product_dict.get("verification_confidence"),
        "http_status": product_dict.get("http_status"),
        "final_url": product_dict.get("final_url"),
        "buy_button_seen": product_dict.get("buy_button_seen"),
        "out_of_stock_seen": product_dict.get("out_of_stock_seen"),
        "purchasability_state": product_dict.get("purchasability_state"),
        "last_checked_at": product_dict.get("last_checked_at"),
        "verified_purchasable": product_dict.get("verified_purchasable"),
        "card_eligible": product_dict.get("card_eligible"),
        "card_eligibility_reason_codes": product_dict.get("card_eligibility_reason_codes"),
    }


def audit_query_with_verification(
    query: str,
    *,
    limit: int,
    timeout_seconds: float,
) -> dict:
    selection = resolve_search_provider_feed_product_selection(query=query)
    verified_rows: list[dict] = []
    sample = selection.selected_products[: max(0, int(limit))]

    for product in sample:
        verification = verify_product_page_purchasability(
            product.product_url,
            timeout_seconds=timeout_seconds,
        )
        raw = product.raw if isinstance(product.raw, dict) else {}
        merged_raw = merge_verification_into_product_raw(raw, verification)
        enriched = type(product)(
            provider_key=product.provider_key,
            provider_product_id=product.provider_product_id,
            title=product.title,
            brand=product.brand,
            category_text=product.category_text,
            product_url=product.product_url,
            image_url=product.image_url,
            price_text=product.price_text,
            availability_text=product.availability_text,
            currency=product.currency,
            raw=merged_raw,
        )
        feed_ctx = build_feed_availability_context((enriched,))
        eligibility = evaluate_product_eligibility(enriched, feed_ctx=feed_ctx)
        payload = provider_product_to_backend_dict(enriched)
        payload["card_eligible"] = eligibility.card_eligible
        payload["card_eligibility_reason_codes"] = list(eligibility.reason_codes)
        verified_rows.append(_truth_row_from_verified(payload))

    return {
        "query": query,
        "selection_status": selection.status,
        "selected_count": len(selection.selected_products),
        "verified_count": len(verified_rows),
        "verified_products": verified_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Background purchasability page verifier audit")
    parser.add_argument("--query", default="laptop", help="Search query for feed selection sample")
    parser.add_argument("--limit", type=int, default=_DEFAULT_LIMIT, help="Max product URLs to verify")
    parser.add_argument("--timeout", type=float, default=12.0, help="HTTP timeout per page")
    args = parser.parse_args()

    if not os.environ.get("AWIN_FEED_FILE") and _DEFAULT_FEED.is_file():
        os.environ["AWIN_FEED_FILE"] = str(_DEFAULT_FEED)

    safe_limit = max(0, min(int(args.limit), 20))
    result = audit_query_with_verification(
        str(args.query),
        limit=safe_limit,
        timeout_seconds=float(args.timeout),
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
