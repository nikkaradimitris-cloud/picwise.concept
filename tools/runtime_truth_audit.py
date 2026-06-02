"""Audit-only helper: capture runtime truth fields from resolve_live_search.

Does not modify runtime behavior. Read-only inspection for stage closure audits.
Optional --cache-file applies persisted purchasability verification to search (no page fetch).
Optional --verify-pages runs background page verification on a limited sample only.
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
from picwise_providers.purchasability_cache import (  # noqa: E402
    CACHE_ENV_VAR,
    blocked_reason_from_eligibility,
    clear_purchasability_cache_configuration,
    configure_purchasability_cache,
    resolve_purchasability_cache,
)
from picwise_providers.purchasability_verifier import (  # noqa: E402
    merge_verification_into_product_raw,
    verify_product_page_purchasability,
)
from picwise_providers.search_selection import provider_product_to_backend_dict  # noqa: E402
from picwise_providers.state import resolve_search_provider_feed_product_selection  # noqa: E402
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


def _cache_hit_for_product(product: dict, *, cache_used: bool) -> bool:
    if not cache_used:
        return False
    cache = resolve_purchasability_cache()
    if cache is None:
        return False
    url = str(product.get("product_url") or "").strip()
    return cache.has(url) if url else False


def _truth_row(product: dict, *, cache_used: bool) -> dict:
    raw = product.get("raw") if isinstance(product.get("raw"), dict) else {}
    verification_source = product.get("verification_source") or raw.get("verification_source")
    verifier_run = verification_source == "page_verifier"
    reason_codes = tuple(product.get("card_eligibility_reason_codes") or ())
    blocked_reason = product.get("blocked_reason")
    if blocked_reason is None and not product.get("card_eligible", True):
        blocked_reason = blocked_reason_from_eligibility(reason_codes)
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
        "verifier_run": verifier_run,
        "verification_source": verification_source,
        "verification_confidence": product.get("verification_confidence")
        or raw.get("verification_confidence"),
        "http_status": product.get("http_status") or raw.get("http_status"),
        "final_url": product.get("final_url") or raw.get("final_url"),
        "buy_button_seen": product.get("buy_button_seen")
        if "buy_button_seen" in product
        else raw.get("buy_button_seen"),
        "out_of_stock_seen": product.get("out_of_stock_seen")
        if "out_of_stock_seen" in product
        else raw.get("out_of_stock_seen"),
        "last_checked_at": product.get("last_checked_at") or raw.get("last_checked_at"),
        "card_eligibility_reason_codes": list(reason_codes),
        "cache_used": cache_used,
        "cache_hit": _cache_hit_for_product(product, cache_used=cache_used),
        "blocked_reason": blocked_reason,
    }


def audit_query(query: str, *, cache_used: bool) -> dict:
    resolution = resolve_live_search(query)
    products = []
    for product in resolution.provider_feed_selected_products:
        row = dict(product)
        if not row.get("card_eligible", True):
            row["blocked_reason"] = blocked_reason_from_eligibility(
                tuple(row.get("card_eligibility_reason_codes") or ())
            )
        products.append(_truth_row(row, cache_used=cache_used))
    return {
        "query": query,
        "cache_used": cache_used,
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


def audit_query_with_page_verification(query: str, *, limit: int) -> dict:
    selection = resolve_search_provider_feed_product_selection(query=query)
    verified_products: list[dict] = []
    for product in selection.selected_products[: max(0, limit)]:
        verification = verify_product_page_purchasability(product.product_url)
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
        verified_products.append(_truth_row(payload, cache_used=False))

    return {
        "query": query,
        "selection_status": selection.status,
        "page_verification_limit": limit,
        "verified_products": verified_products,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Runtime truth audit (read-only)")
    parser.add_argument(
        "--verify-pages",
        action="store_true",
        help="Run background page verifier on a small feed sample (audit only)",
    )
    parser.add_argument("--query", default="laptop", help="Query when --verify-pages is set")
    parser.add_argument("--limit", type=int, default=4, help="Max URLs to verify with --verify-pages")
    parser.add_argument(
        "--cache-file",
        default="",
        help="Apply persisted purchasability cache during live search audit (no page fetch)",
    )
    args = parser.parse_args()

    if not os.environ.get("AWIN_FEED_FILE") and _DEFAULT_FEED.is_file():
        os.environ["AWIN_FEED_FILE"] = str(_DEFAULT_FEED)

    cache_path = str(args.cache_file or "").strip()
    cache_used = bool(cache_path)
    try:
        if cache_path:
            configure_purchasability_cache(cache_path)
            os.environ[CACHE_ENV_VAR] = cache_path
        else:
            clear_purchasability_cache_configuration()
            os.environ.pop(CACHE_ENV_VAR, None)

        if args.verify_pages:
            safe_limit = max(0, min(int(args.limit), 20))
            result = audit_query_with_page_verification(str(args.query), limit=safe_limit)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return

        results = [audit_query(q, cache_used=cache_used) for q in AUDIT_QUERIES]
        summary = {
            "cache_used": cache_used,
            "cache_file": cache_path or None,
            "cache_entry_count": len(resolve_purchasability_cache().entries)
            if cache_used and resolve_purchasability_cache()
            else 0,
            "queries": results,
        }
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    finally:
        clear_purchasability_cache_configuration()


if __name__ == "__main__":
    main()
