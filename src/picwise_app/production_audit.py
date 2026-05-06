from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from picwise_feeds import (
    LocalFixtureFeedAdapter,
    evaluate_feed_connection_readiness,
    load_feed_source_config_from_env,
)
from picwise_integrations import evaluate_subby_readiness, load_subby_config_from_env
from picwise_redirects import (
    evaluate_affiliate_redirect_readiness,
    load_affiliate_redirect_config_from_env,
)


EXPECTED_TITLES_1_TO_15 = [
    "1 | Root rules and concept lock",
    "2 | Mission docs/spec foundation",
    "3 | Quality rules and testing strategy",
    "4 | Contracts/schemas",
    "5 | Core decision engine",
    "6 | Brain selector",
    "7 | Decision depth selector",
    "8 | Product candidate adapter",
    "9 | Decision arbitration",
    "10 | Landing UI",
    "11 | CTA/redirect tracking",
    "12 | SEO landing generation",
    "13 | Dashboard/Subby event compatibility",
    "14 | Performance audit",
    "15 | Final V1 audit closure",
]

EXPECTED_TITLES_16_TO_21 = [
    "16. App implementation foundation",
    "17. Real product feed adapter",
    "18. Affiliate/provider redirect integration",
    "19. Live app deployment",
    "20. Live Subby dashboard integration",
    "21. Production V1 audit closure",
]

EXPECTED_TITLES_22_TO_25 = [
    "22. Live deployment to picwise.subby.cloud",
    "23. Real product/feed and affiliate redirect connection",
    "24. Live Subby dashboard event integration",
    "25. Production V1 live audit closure",
]


@dataclass(frozen=True)
class ProductionV1AuditResult:
    status: str
    checks: dict[str, bool]
    notes: list[str]


def run_production_v1_audit(
    repo_root: str | Path,
    *,
    tests_passed: bool,
    live_deployment_proven: bool,
    live_subby_proven: bool,
    live_feed_affiliate_proven: bool = False,
) -> ProductionV1AuditResult:
    root = Path(repo_root)
    progress_path = root / "PROGRESS.md"
    readme_path = root / "README.md"
    fixture_result = LocalFixtureFeedAdapter().fetch_candidates("power bank 20000mah for iphone")
    feed_readiness = evaluate_feed_connection_readiness(load_feed_source_config_from_env())
    affiliate_readiness = evaluate_affiliate_redirect_readiness(
        load_affiliate_redirect_config_from_env()
    )
    subby_readiness = evaluate_subby_readiness(load_subby_config_from_env())
    stage22_status = _extract_stage_status(progress_path, 22)
    stage23_status = _extract_stage_status(progress_path, 23)
    stage24_status = _extract_stage_status(progress_path, 24)
    stage25_status = _extract_stage_status(progress_path, 25)
    checks = {
        "stage_16_local_app_ready": (root / "src" / "picwise_app" / "app.py").exists(),
        "stage_17_feed_adapter_ready": (root / "src" / "picwise_feeds" / "adapters.py").exists(),
        "stage_18_redirect_ready": (root / "src" / "picwise_redirects" / "resolver.py").exists(),
        "stage_19_deployment_doc_ready": (root / "docs" / "STAGE_19_LIVE_APP_DEPLOYMENT.md").exists(),
        "stage_20_subby_doc_ready": (root / "docs" / "STAGE_20_LIVE_SUBBY_DASHBOARD_INTEGRATION.md").exists(),
        "stage_23_to_25_doc_ready": (
            root / "docs" / "STAGE_23_TO_25_LIVE_PRODUCTION_INTEGRATION.md"
        ).exists(),
        "tests_passed": tests_passed,
        "no_fake_data_fields": _fixture_candidates_have_no_forbidden_fields(
            fixture_result.candidates, _forbidden_fake_patterns()
        ),
        "no_commission_ranking_fields": _fixture_candidates_have_no_forbidden_fields(
            fixture_result.candidates, _forbidden_commission_patterns()
        ),
        "no_committed_secrets": _scan_forbidden_patterns(root, _secret_like_patterns()) == [],
        "roadmap_titles_1_to_15_unchanged": _contains_all_fragments(progress_path, EXPECTED_TITLES_1_TO_15),
        "roadmap_titles_16_to_21_present": _contains_all_fragments(progress_path, EXPECTED_TITLES_16_TO_21),
        "roadmap_titles_22_to_25_present": _contains_all_fragments(progress_path, EXPECTED_TITLES_22_TO_25),
        "stage_22_live_proof_logged": _progress_has_stage_22_proof(progress_path),
        "stage_23_progress_honest": _stage_23_progress_honest(
            stage23_status=stage23_status,
            live_feed_affiliate_proven=live_feed_affiliate_proven,
            feed_readiness_status=feed_readiness.status,
            affiliate_readiness_status=affiliate_readiness.status,
        ),
        "stage_24_progress_honest": _stage_24_progress_honest(
            stage24_status=stage24_status,
            live_subby_proven=live_subby_proven,
            subby_readiness_status=subby_readiness.status,
        ),
        "stage_25_progress_honest": _stage_25_progress_honest(
            stage25_status=stage25_status,
            live_deployment_proven=live_deployment_proven,
            live_feed_affiliate_proven=live_feed_affiliate_proven,
            live_subby_proven=live_subby_proven,
        ),
        "stage_22_marked_passed": stage22_status == "PASSED",
        "stage_22_input_proof_flag": live_deployment_proven,
        "stage_23_feed_readiness_known": feed_readiness.status in {"NEEDS_REAL_FEED_CONFIG", "FEED_READY"},
        "stage_23_affiliate_readiness_known": affiliate_readiness.status
        in {"NEEDS_AFFILIATE_CONFIG", "REDIRECT_READY"},
        "stage_24_subby_readiness_known": subby_readiness.status
        in {"NEEDS_LIVE_SUBBY_CONFIG", "INTEGRATION_READY"},
        "not_live_statements_present": _contains_not_live_statements(progress_path, readme_path),
    }
    notes = []
    if not checks["no_committed_secrets"]:
        notes.append("Secret-like patterns detected; remove before release.")
    if not checks["stage_23_progress_honest"]:
        notes.append("Stage 23 progress status overclaims feed/affiliate live status.")
    if not checks["stage_24_progress_honest"]:
        notes.append("Stage 24 progress status overclaims live Subby status.")
    if not checks["stage_25_progress_honest"]:
        notes.append("Stage 25 progress status overclaims audit closure.")
    if not checks["tests_passed"]:
        notes.append("Tests did not pass.")
    if not checks["stage_22_live_proof_logged"]:
        notes.append("Stage 22 live proof URLs are not logged in PROGRESS.md.")

    local_readiness_ok = all(
        checks[key]
        for key in (
            "stage_16_local_app_ready",
            "stage_17_feed_adapter_ready",
            "stage_18_redirect_ready",
            "stage_19_deployment_doc_ready",
            "stage_20_subby_doc_ready",
            "stage_23_to_25_doc_ready",
            "tests_passed",
            "no_fake_data_fields",
            "no_commission_ranking_fields",
            "no_committed_secrets",
            "roadmap_titles_1_to_15_unchanged",
            "roadmap_titles_16_to_21_present",
            "roadmap_titles_22_to_25_present",
            "stage_22_live_proof_logged",
            "stage_22_marked_passed",
            "stage_23_progress_honest",
            "stage_24_progress_honest",
            "stage_25_progress_honest",
            "stage_23_feed_readiness_known",
            "stage_23_affiliate_readiness_known",
            "stage_24_subby_readiness_known",
            "not_live_statements_present",
        )
    )
    if not local_readiness_ok:
        return ProductionV1AuditResult(status="FAILED", checks=checks, notes=notes)
    if live_deployment_proven and live_feed_affiliate_proven and live_subby_proven:
        return ProductionV1AuditResult(status="PASSED", checks=checks, notes=notes)
    notes.append("Local readiness passed but missing live feed/affiliate and/or Subby proof.")
    return ProductionV1AuditResult(status="NEEDS_LIVE_PROOF", checks=checks, notes=notes)


def _contains_all_fragments(path: Path, fragments: list[str]) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    return all(fragment in text for fragment in fragments)


def _contains_not_live_statements(progress_path: Path, readme_path: Path) -> bool:
    snippets = [
        "must NOT be PASSED unless actual live deployment proof exists",
        "must NOT be PASSED unless actual live Subby proof exists",
        "not live",
    ]
    text = ""
    if progress_path.exists():
        text += progress_path.read_text(encoding="utf-8").lower()
    if readme_path.exists():
        text += "\n" + readme_path.read_text(encoding="utf-8").lower()
    return all(snippet.lower() in text for snippet in snippets)


def _progress_has_stage_22_proof(progress_path: Path) -> bool:
    if not progress_path.exists():
        return False
    text = progress_path.read_text(encoding="utf-8")
    return (
        "https://picwise.subby.cloud/health" in text
        and "https://picwise.subby.cloud/demo" in text
        and "22. Live deployment to picwise.subby.cloud — PASSED" in text
    )


def _extract_stage_status(progress_path: Path, stage_number: int) -> str:
    if not progress_path.exists():
        return ""
    text = progress_path.read_text(encoding="utf-8")
    pattern = re.compile(rf"^\|\s*{stage_number}\s*\|.*\|\s*([A-Z_]+)\s*\|$", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return ""
    return match.group(1)


def _stage_23_progress_honest(
    *,
    stage23_status: str,
    live_feed_affiliate_proven: bool,
    feed_readiness_status: str,
    affiliate_readiness_status: str,
) -> bool:
    if live_feed_affiliate_proven:
        return stage23_status in {
            "PASSED",
            "FEED_READY",
            "REDIRECT_READY",
            "NEEDS_REAL_FEED_CONFIG",
            "NEEDS_AFFILIATE_CONFIG",
        }
    allowed = {"FEED_READY", "REDIRECT_READY", "NEEDS_REAL_FEED_CONFIG", "NEEDS_AFFILIATE_CONFIG"}
    if stage23_status not in allowed:
        return False
    if feed_readiness_status == "NEEDS_REAL_FEED_CONFIG" and stage23_status == "PASSED":
        return False
    if affiliate_readiness_status == "NEEDS_AFFILIATE_CONFIG" and stage23_status == "PASSED":
        return False
    return True


def _stage_24_progress_honest(
    *,
    stage24_status: str,
    live_subby_proven: bool,
    subby_readiness_status: str,
) -> bool:
    if live_subby_proven:
        return stage24_status in {"PASSED", "INTEGRATION_READY", "NEEDS_LIVE_SUBBY_CONFIG"}
    if stage24_status not in {"INTEGRATION_READY", "NEEDS_LIVE_SUBBY_CONFIG"}:
        return False
    if subby_readiness_status == "NEEDS_LIVE_SUBBY_CONFIG" and stage24_status == "PASSED":
        return False
    return True


def _stage_25_progress_honest(
    *,
    stage25_status: str,
    live_deployment_proven: bool,
    live_feed_affiliate_proven: bool,
    live_subby_proven: bool,
) -> bool:
    if live_deployment_proven and live_feed_affiliate_proven and live_subby_proven:
        return stage25_status in {"PASSED", "NEEDS_LIVE_PROOF"}
    return stage25_status == "NEEDS_LIVE_PROOF"


def _scan_forbidden_patterns(root: Path, patterns: list[re.Pattern[str]]) -> list[str]:
    hits: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".py", ".md", ".txt", ".yml", ".yaml", ".json", ".ini"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in patterns:
            if pattern.search(text):
                hits.append(f"{path}:{pattern.pattern}")
                break
    return hits


def _fixture_candidates_have_no_forbidden_fields(
    candidates: list[dict[str, object]],
    patterns: list[re.Pattern[str]],
) -> bool:
    for candidate in candidates:
        for key in candidate.keys():
            for pattern in patterns:
                if pattern.search(str(key)):
                    return False
    return True


def _forbidden_fake_patterns() -> list[re.Pattern[str]]:
    return [
        re.compile(r"\bfake_reviews?\b", re.IGNORECASE),
        re.compile(r"\bfake_ratings?\b", re.IGNORECASE),
        re.compile(r"\bfake_revenue\b", re.IGNORECASE),
        re.compile(r"\bfake_conversions?\b", re.IGNORECASE),
        re.compile(r"\bfake_savings?\b", re.IGNORECASE),
        re.compile(r"\bfake_urgency\b", re.IGNORECASE),
        re.compile(r"\bfake_ai_confidence\b", re.IGNORECASE),
    ]


def _forbidden_commission_patterns() -> list[re.Pattern[str]]:
    return [
        re.compile(r"\bcommission_rank\b", re.IGNORECASE),
        re.compile(r"\bcommission_score\b", re.IGNORECASE),
        re.compile(r"\brank_by_commission\b", re.IGNORECASE),
    ]


def _secret_like_patterns() -> list[re.Pattern[str]]:
    return [
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"(?i)api[_-]?key\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}"),
        re.compile(r"(?i)secret[_-]?key\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}"),
        re.compile(r"-----BEGIN (?:RSA|EC|DSA|OPENSSH) PRIVATE KEY-----"),
    ]
