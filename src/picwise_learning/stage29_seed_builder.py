from __future__ import annotations

import hashlib

from picwise_market_scope import get_market_scope_manifest
from picwise_taxonomy.engine_registry import get_engine_registry
from picwise_taxonomy.mega_category_registry import get_mega_category_registry
from picwise_verticals.finance_insurance import get_finance_insurance_taxonomy_manifest
from picwise_verticals.saas_erp import get_saas_erp_taxonomy_manifest

from .stage29_contracts import Stage29SeedRecord

_RETAIL_GOOGLE_PATHS = {
    "phones_mobile_accessories": "Electronics > Communications > Telephony > Mobile Phones",
    "computers_office_peripherals": "Electronics > Computers > Laptops",
    "audio_video_gaming_cameras": "Electronics > Video > Televisions",
    "home_appliances_laundry_climate": "Home & Garden > Household Appliances",
}

_FINANCE_BLOCKED_TERMS = ("advice", "quote", "eligibility", "approval", "application", "provider")


def _stable_seed_id(*parts: str) -> str:
    payload = "|".join(str(part or "").strip().lower() for part in parts)
    return f"s29_seed_{hashlib.sha1(payload.encode('utf-8')).hexdigest()[:12]}"


def _retail_seed_records() -> list[Stage29SeedRecord]:
    engines = {row["engine_id"]: row for row in get_engine_registry()}
    categories = get_mega_category_registry()
    records: list[Stage29SeedRecord] = []
    for category in categories:
        mega_category = category["mega_category_id"]
        engine_id = category["engine_id"]
        display_name = category["display_name"]
        canonical = f"best {display_name.lower()} options"
        seed_id = _stable_seed_id("retail", engine_id, mega_category)
        records.append(
            Stage29SeedRecord(
                seed_id=seed_id,
                vertical="retail_physical_products",
                canonical_query=canonical,
                expected_nlu_target=mega_category,
                expected_intent="specific_product",
                language="en",
                retail_engine=engine_id if engine_id in engines else None,
                mega_category=mega_category,
                google_taxonomy_path=_RETAIL_GOOGLE_PATHS.get(mega_category, "unavailable"),
                metadata={"display_name": display_name, "source_stage": "22B"},
            )
        )
    return records


def _saas_seed_records() -> list[Stage29SeedRecord]:
    manifest = get_saas_erp_taxonomy_manifest()
    records: list[Stage29SeedRecord] = []
    for bucket in manifest["category_buckets"]:
        bucket_id = bucket["bucket_id"]
        seed_id = _stable_seed_id("saas", bucket_id)
        canonical = f"compare {bucket['display_name'].lower()} tools"
        records.append(
            Stage29SeedRecord(
                seed_id=seed_id,
                vertical="software_saas_erp",
                canonical_query=canonical,
                expected_nlu_target=bucket_id,
                expected_intent="general_intent",
                language="en",
                saas_erp_contract_ref="Stage 28E",
                metadata={"bucket_display_name": bucket["display_name"]},
            )
        )
    return records


def _finance_seed_records() -> list[Stage29SeedRecord]:
    manifest = get_finance_insurance_taxonomy_manifest()
    records: list[Stage29SeedRecord] = []
    for bucket in manifest["category_buckets"]:
        text = bucket["display_name"].lower()
        if any(token in text for token in _FINANCE_BLOCKED_TERMS):
            continue
        bucket_id = bucket["bucket_id"]
        seed_id = _stable_seed_id("finance", bucket_id)
        canonical = f"compare {text} options"
        records.append(
            Stage29SeedRecord(
                seed_id=seed_id,
                vertical="finance_insurance_business_finance",
                canonical_query=canonical,
                expected_nlu_target=bucket_id,
                expected_intent="general_intent",
                language="en",
                finance_insurance_contract_ref="Stage 28F",
                metadata={"bucket_display_name": bucket["display_name"]},
            )
        )
    return records


def build_stage29_seeds() -> list[Stage29SeedRecord]:
    manifest = get_market_scope_manifest()
    verticals = set(manifest["verticals"].keys())
    output: list[Stage29SeedRecord] = []
    if "retail_physical_products" in verticals:
        output.extend(_retail_seed_records())
    if "software_saas_erp" in verticals:
        output.extend(_saas_seed_records())
    if "finance_insurance_business_finance" in verticals:
        output.extend(_finance_seed_records())
    return sorted(output, key=lambda row: row.seed_id)
