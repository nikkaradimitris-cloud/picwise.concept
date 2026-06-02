"""Audit-only: verify a small sample of provider product pages after feed selection.

Writes results to a local JSON cache when --cache-file is set. Does not modify live search.
Safe to run manually from PowerShell.
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
    PurchasabilityCache,
    blocked_reason_from_eligibility,
    cache_entry_from_verification,
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


def _print_verification_row(row: dict) -> None:
    for key in (
        "query",
        "title",
        "product_url",
        "final_url",
        "http_status",
        "purchasability_state",
        "verification_confidence",
        "buy_button_seen",
        "out_of_stock_seen",
        "missing_buy_button",
        "discontinued_seen",
        "redirect_suspect",
        "last_checked_at",
        "cache_written",
    ):
        print(f"{key}: {row.get(key)}")


def audit_query_with_verification(
    query: str,
    *,
    limit: int,
    timeout_seconds: float,
    cache: PurchasabilityCache | None = None,
    cache_path: str | None = None,
) -> dict:
    selection = resolve_search_provider_feed_product_selection(query=query)
    verified_rows: list[dict] = []
    sample = selection.selected_products[: max(0, int(limit))]

    for product in sample:
        verification = verify_product_page_purchasability(
            product.product_url,
            timeout_seconds=timeout_seconds,
        )
        cache_written = False
        if cache is not None and cache_path:
            cache.set(product.product_url, verification)
            cache_written = True

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
        entry = cache_entry_from_verification(verification, product_url=product.product_url)
        row = {
            "query": query,
            "title": payload.get("title"),
            "product_url": payload.get("product_url"),
            "final_url": payload.get("final_url"),
            "http_status": payload.get("http_status"),
            "purchasability_state": payload.get("purchasability_state"),
            "verification_confidence": payload.get("verification_confidence"),
            "buy_button_seen": payload.get("buy_button_seen"),
            "out_of_stock_seen": payload.get("out_of_stock_seen"),
            "missing_buy_button": entry.get("missing_buy_button"),
            "discontinued_seen": entry.get("discontinued_seen"),
            "redirect_suspect": entry.get("redirect_suspect"),
            "last_checked_at": payload.get("last_checked_at"),
            "cache_written": cache_written,
            "blocked_reason": blocked_reason_from_eligibility(eligibility.reason_codes),
            "verified_purchasable": payload.get("verified_purchasable"),
            "card_eligible": payload.get("card_eligible"),
        }
        verified_rows.append(row)

    if cache is not None and cache_path:
        cache.save(cache_path)

    return {
        "query": query,
        "selection_status": selection.status,
        "selected_count": len(selection.selected_products),
        "verified_count": len(verified_rows),
        "cache_file": cache_path,
        "verified_products": verified_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Background purchasability page verifier audit")
    parser.add_argument("--query", default="laptop", help="Search query for feed selection sample")
    parser.add_argument("--limit", type=int, default=_DEFAULT_LIMIT, help="Max product URLs to verify")
    parser.add_argument("--timeout", type=float, default=12.0, help="HTTP timeout per page")
    parser.add_argument(
        "--cache-file",
        default="",
        help="Write verification results to this JSON cache file",
    )
    args = parser.parse_args()

    if not os.environ.get("AWIN_FEED_FILE") and _DEFAULT_FEED.is_file():
        os.environ["AWIN_FEED_FILE"] = str(_DEFAULT_FEED)

    safe_limit = max(0, min(int(args.limit), 20))
    cache_path = str(args.cache_file or "").strip()
    cache = PurchasabilityCache.load(cache_path) if cache_path else None

    result = audit_query_with_verification(
        str(args.query),
        limit=safe_limit,
        timeout_seconds=float(args.timeout),
        cache=cache,
        cache_path=cache_path or None,
    )
    for row in result.get("verified_products", []):
        print("---")
        _print_verification_row(row)
    print("---")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
