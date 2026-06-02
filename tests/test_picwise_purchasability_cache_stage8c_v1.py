"""Stage 8C-V1: persisted purchasability cache, search gate, batch verifier (no live HTTP in CI)."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_providers.contracts import ProviderProduct, PurchasabilityVerification  # noqa: E402
from picwise_providers.offer_health import (  # noqa: E402
    build_feed_availability_context,
    evaluate_product_eligibility,
)
from picwise_providers.purchasability_cache import (  # noqa: E402
    CACHE_ENV_VAR,
    PurchasabilityCache,
    clear_purchasability_cache_configuration,
    configure_purchasability_cache,
    enrich_provider_products_with_cache,
    merge_cache_entry_into_product_raw,
    normalize_product_url_key,
)
from picwise_providers.purchasability_verifier import (  # noqa: E402
    verify_product_page_purchasability,
)
from picwise_providers.search_selection import (  # noqa: E402
    provider_product_to_backend_dict,
    select_provider_products_for_query,
)

_PRODUCT_URL = "https://merchant.example/products/sku-8cv1-1"


def _sample_product(**overrides: object) -> ProviderProduct:
    raw: dict[str, object] = {
        "product_type": "Laptops",
        "description": (
            "A full description with enough detail to pass the minimal quality threshold "
            "for stage eight c v one purchasability cache tests."
        ),
        "in_stock": "in stock",
    }
    base: dict[str, object] = {
        "provider_key": "awin",
        "provider_product_id": "SKU-8CV1-1",
        "title": "Dell Latitude Laptop 15 inch",
        "brand": "Dell",
        "category_text": "Laptops",
        "product_url": _PRODUCT_URL,
        "image_url": "https://cdn.example/img.jpg",
        "price_text": "899.99",
        "availability_text": "1",
        "currency": "USD",
    }
    raw_override = overrides.pop("raw", None)
    if isinstance(raw_override, dict):
        raw.update(raw_override)
    base.update(overrides)
    base["raw"] = raw
    return ProviderProduct(**base)  # type: ignore[arg-type]


def _verification(
    state: str,
    *,
    confidence: str = "verified",
    buy_button_seen: bool | None = True,
    out_of_stock_seen: bool | None = None,
) -> PurchasabilityVerification:
    return PurchasabilityVerification(
        purchasability_state=state,
        buy_button_seen=buy_button_seen,
        out_of_stock_seen=out_of_stock_seen,
        final_url=_PRODUCT_URL,
        http_status=200,
        last_checked_at="2026-06-01T12:00:00+00:00",
        verification_source="page_verifier",
        verification_confidence=confidence,
    )


def _product_with_cache_entry(entry: dict[str, object]) -> ProviderProduct:
    raw = merge_cache_entry_into_product_raw({}, entry)
    return _sample_product(raw=raw)


class PurchasabilityCacheModuleTests(unittest.TestCase):
    def setUp(self) -> None:
        clear_purchasability_cache_configuration()
        self._env_pop = os.environ.pop(CACHE_ENV_VAR, None)

    def tearDown(self) -> None:
        clear_purchasability_cache_configuration()
        if self._env_pop is not None:
            os.environ[CACHE_ENV_VAR] = self._env_pop

    def test_cache_load_save_roundtrip(self) -> None:
        cache = PurchasabilityCache.empty()
        cache.set(_PRODUCT_URL, _verification("purchasable"))
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "cache.json")
            cache.save(path)
            loaded = PurchasabilityCache.load(path)
        self.assertEqual(loaded.entries.keys(), cache.entries.keys())
        entry = loaded.get(_PRODUCT_URL)
        self.assertIsNotNone(entry)
        self.assertEqual(entry.get("purchasability_state"), "purchasable")
        self.assertEqual(entry.get("cache_key"), normalize_product_url_key(_PRODUCT_URL))

    def test_cache_key_lookup_by_product_url(self) -> None:
        cache = PurchasabilityCache.empty()
        cache.set("HTTPS://Merchant.Example/products/sku-8cv1-1/", _verification("purchasable"))
        key = normalize_product_url_key(_PRODUCT_URL)
        self.assertTrue(cache.has(_PRODUCT_URL))
        self.assertIn(key, cache.entries)

    def test_missing_cache_keeps_unknown_unverified(self) -> None:
        product = _sample_product()
        payload = provider_product_to_backend_dict(product)
        self.assertEqual(payload["purchasability_state"], "purchasability_unknown")
        self.assertFalse(payload["verified_purchasable"])

    def test_cached_purchasable_verified_only_with_positive_evidence(self) -> None:
        product = _product_with_cache_entry(
            _verification("purchasable", confidence="verified").to_dict()
        )
        payload = provider_product_to_backend_dict(product)
        self.assertEqual(payload["purchasability_state"], "purchasable")
        self.assertTrue(payload["verified_purchasable"])

        weak = _product_with_cache_entry(
            _verification("purchasable", confidence="weak").to_dict()
        )
        weak_payload = provider_product_to_backend_dict(weak)
        self.assertFalse(weak_payload["verified_purchasable"])

    def _eligible_laptop_siblings(self, count: int, *, prefix: str) -> tuple[ProviderProduct, ...]:
        rows: list[ProviderProduct] = []
        for index in range(count):
            rows.append(
                _sample_product(
                    provider_product_id=f"{prefix}-{index}",
                    title=f"Lenovo ThinkPad Laptop {index} inch",
                )
            )
        return tuple(rows)

    def test_cached_out_of_stock_blocks_selection(self) -> None:
        blocked = _product_with_cache_entry(_verification("out_of_stock").to_dict())
        pool = (blocked,) + self._eligible_laptop_siblings(4, prefix="SKU-OK")
        selection = select_provider_products_for_query("laptop", pool, max_products=4)
        ids = {p.provider_product_id for p in selection.selected_products}
        self.assertNotIn(blocked.provider_product_id, ids)

    def test_cached_discontinued_blocks_selection(self) -> None:
        blocked = _product_with_cache_entry(_verification("discontinued").to_dict())
        pool = (blocked,) + self._eligible_laptop_siblings(4, prefix="SKU-OK-2")
        selection = select_provider_products_for_query("laptop", pool, max_products=4)
        ids = {p.provider_product_id for p in selection.selected_products}
        self.assertNotIn(blocked.provider_product_id, ids)

    def test_cached_missing_buy_button_blocks_selection(self) -> None:
        blocked = _product_with_cache_entry(
            {
                "purchasability_state": "missing_buy_button",
                "buy_button_seen": False,
                "verification_source": "page_verifier",
                "verification_confidence": "limited",
                "last_checked_at": "2026-06-01T12:00:00+00:00",
            }
        )
        pool = (blocked,) + self._eligible_laptop_siblings(4, prefix="SKU-OK-3")
        selection = select_provider_products_for_query("laptop", pool, max_products=4)
        ids = {p.provider_product_id for p in selection.selected_products}
        self.assertNotIn(blocked.provider_product_id, ids)

    def test_cached_invalid_page_blocks_selection(self) -> None:
        blocked = _product_with_cache_entry(
            _verification("invalid_page", confidence="unknown").to_dict()
        )
        pool = (blocked,) + self._eligible_laptop_siblings(4, prefix="SKU-OK-4")
        selection = select_provider_products_for_query("laptop", pool, max_products=4)
        ids = {p.provider_product_id for p in selection.selected_products}
        self.assertNotIn(blocked.provider_product_id, ids)

    def test_cached_redirect_suspect_blocks_selection(self) -> None:
        blocked = _product_with_cache_entry(
            _verification("redirect_suspect", confidence="weak").to_dict()
        )
        pool = (blocked,) + self._eligible_laptop_siblings(4, prefix="SKU-OK-5")
        selection = select_provider_products_for_query("laptop", pool, max_products=4)
        ids = {p.provider_product_id for p in selection.selected_products}
        self.assertNotIn(blocked.provider_product_id, ids)

    def test_live_search_path_does_not_call_verifier(self) -> None:
        products = (_sample_product(),) * 5
        with patch(
            "picwise_providers.purchasability_verifier.verify_product_page_purchasability"
        ) as verify_mock:
            select_provider_products_for_query("laptop", products, max_products=4)
            verify_mock.assert_not_called()

    def test_enrich_products_does_not_call_verifier(self) -> None:
        cache = PurchasabilityCache.empty()
        cache.set(_PRODUCT_URL, _verification("purchasable"))
        with patch(
            "picwise_providers.purchasability_verifier.verify_product_page_purchasability"
        ) as verify_mock:
            enriched = enrich_provider_products_with_cache((_sample_product(),), cache)
            verify_mock.assert_not_called()
        self.assertEqual(
            dict(enriched[0].raw).get("purchasability_state"),
            "purchasable",
        )


class PurchasabilityBatchVerifierCacheTests(unittest.TestCase):
    def test_batch_verifier_writes_cache_only_when_configured(self) -> None:
        from tools import purchasability_verifier_audit as audit_tool  # noqa: E402

        product = _sample_product()
        verification = _verification("purchasable")
        with patch.object(
            audit_tool,
            "resolve_search_provider_feed_product_selection",
            return_value=type(
                "Sel",
                (),
                {
                    "status": "selected",
                    "selected_products": (product,),
                    "reason_codes": (),
                },
            )(),
        ):
            with patch.object(
                audit_tool,
                "verify_product_page_purchasability",
                return_value=verification,
            ) as verify_mock:
                with tempfile.TemporaryDirectory() as tmp:
                    path = str(Path(tmp) / "cache.json")
                    result = audit_tool.audit_query_with_verification(
                        "laptop",
                        limit=1,
                        timeout_seconds=1.0,
                        cache=PurchasabilityCache.load(path),
                        cache_path=path,
                    )
                    loaded = PurchasabilityCache.load(path)
                no_cache = audit_tool.audit_query_with_verification(
                    "laptop",
                    limit=1,
                    timeout_seconds=1.0,
                    cache=None,
                    cache_path=None,
                )
        verify_mock.assert_called()
        self.assertTrue(result["verified_products"][0]["cache_written"])
        self.assertTrue(loaded.has(_PRODUCT_URL))
        self.assertFalse(no_cache["verified_products"][0]["cache_written"])


class RuntimeTruthAuditCacheTests(unittest.TestCase):
    def test_runtime_truth_audit_reports_cache_fields(self) -> None:
        from tools import runtime_truth_audit as audit_tool  # noqa: E402

        product = provider_product_to_backend_dict(
            _product_with_cache_entry(_verification("out_of_stock").to_dict())
        )
        product["card_eligible"] = False
        product["card_eligibility_reason_codes"] = ["purchasability_out_of_stock"]
        row = audit_tool._truth_row(product, cache_used=True)
        self.assertTrue(row["cache_used"])
        self.assertEqual(row["purchasability_state"], "out_of_stock")
        self.assertFalse(row["verified_purchasable"])
        self.assertEqual(row["blocked_reason"], "purchasability_out_of_stock")

    def test_synthetic_cache_blocks_without_live_website(self) -> None:
        product = _product_with_cache_entry(_verification("out_of_stock").to_dict())
        feed_ctx = build_feed_availability_context((product,))
        eligibility = evaluate_product_eligibility(product, feed_ctx=feed_ctx)
        self.assertFalse(eligibility.card_eligible)
        self.assertIn("purchasability_out_of_stock", eligibility.reason_codes)


if __name__ == "__main__":
    unittest.main()
