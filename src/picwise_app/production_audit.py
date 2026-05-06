from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from picwise_feeds import LocalFixtureFeedAdapter


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
) -> ProductionV1AuditResult:
    root = Path(repo_root)
    progress_path = root / "PROGRESS.md"
    readme_path = root / "README.md"
    fixture_result = LocalFixtureFeedAdapter().fetch_candidates("power bank 20000mah for iphone")
    checks = {
        "stage_16_local_app_ready": (root / "src" / "picwise_app" / "app.py").exists(),
        "stage_17_feed_adapter_ready": (root / "src" / "picwise_feeds" / "adapters.py").exists(),
        "stage_18_redirect_ready": (root / "src" / "picwise_redirects" / "resolver.py").exists(),
        "stage_19_deployment_doc_ready": (root / "docs" / "STAGE_19_LIVE_APP_DEPLOYMENT.md").exists(),
        "stage_20_subby_doc_ready": (root / "docs" / "STAGE_20_LIVE_SUBBY_DASHBOARD_INTEGRATION.md").exists(),
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
        "progress_is_honest_for_live_stages": _progress_honest_for_live(prog_path=progress_path),
        "not_live_statements_present": _contains_not_live_statements(progress_path, readme_path),
    }
    notes = []
    if not checks["no_committed_secrets"]:
        notes.append("Secret-like patterns detected; remove before release.")
    if not checks["progress_is_honest_for_live_stages"]:
        notes.append("PROGRESS.md overstates live deployment/subby status.")
    if not checks["tests_passed"]:
        notes.append("Tests did not pass.")

    local_readiness_ok = all(
        checks[key]
        for key in (
            "stage_16_local_app_ready",
            "stage_17_feed_adapter_ready",
            "stage_18_redirect_ready",
            "stage_19_deployment_doc_ready",
            "stage_20_subby_doc_ready",
            "tests_passed",
            "no_fake_data_fields",
            "no_commission_ranking_fields",
            "no_committed_secrets",
            "roadmap_titles_1_to_15_unchanged",
            "roadmap_titles_16_to_21_present",
            "progress_is_honest_for_live_stages",
            "not_live_statements_present",
        )
    )
    if not local_readiness_ok:
        return ProductionV1AuditResult(status="FAILED", checks=checks, notes=notes)
    if live_deployment_proven and live_subby_proven:
        return ProductionV1AuditResult(status="PASSED", checks=checks, notes=notes)
    notes.append("Local readiness passed but missing proof for live deployment and/or live Subby integration.")
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


def _progress_honest_for_live(*, prog_path: Path) -> bool:
    if not prog_path.exists():
        return False
    text = prog_path.read_text(encoding="utf-8")
    stage19_ok = "19 | Live app deployment | DEPLOYMENT_READY |" in text or "19 | Live app deployment | NEEDS_LIVE_DEPLOY |" in text
    stage20_ok = "20 | Live Subby dashboard integration | INTEGRATION_READY |" in text or "20 | Live Subby dashboard integration | NEEDS_LIVE_SUBBY_PROOF |" in text
    stage21_ok = "21 | Production V1 audit closure | NEEDS_LIVE_PROOF |" in text
    return stage19_ok and stage20_ok and stage21_ok


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
