from __future__ import annotations

import inspect
import json
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_buying_pages import (  # noqa: E402
    build_human_activation_review_packet,
    evaluate_human_activation_batch,
    evaluate_human_activation_decision,
    simulate_human_activation_rollback,
)


def _load_step13_fixture() -> dict[str, Any]:
    fixture_path = ROOT / "tests" / "fixtures" / "step13_human_activation_review_inputs.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


class PickWiseStep13HumanActivationReviewTests(unittest.TestCase):
    def test_clean_pilot_ready_packet_becomes_activation_review_ready(self) -> None:
        payload = _load_step13_fixture()
        packet = build_human_activation_review_packet(
            payload["pilot_results"]["clean_pilot_ready_packet"],
            governance_batch=payload["governance_batch_clean"],
        )
        decision = evaluate_human_activation_decision(packet)
        self.assertEqual(decision["decision_status"], "activation_review_ready")

    def test_approval_never_assumed_without_explicit_operator_action(self) -> None:
        payload = _load_step13_fixture()
        packet = build_human_activation_review_packet(
            payload["pilot_results"]["clean_pilot_ready_packet"],
            governance_batch=payload["governance_batch_clean"],
        )
        decision = evaluate_human_activation_decision(
            packet,
            operator_id="operator-step13-none",
            reason="No explicit action supplied.",
        )
        self.assertNotEqual(decision["decision_status"], "activation_approved_for_next_phase")
        self.assertEqual(decision["operator_action"], "none")

    def test_explicit_approve_only_when_clean_and_rollback_passes(self) -> None:
        payload = _load_step13_fixture()
        packet = build_human_activation_review_packet(
            payload["pilot_results"]["clean_pilot_ready_packet"],
            governance_batch=payload["governance_batch_clean"],
        )
        approval = payload["operator_scenarios"]["explicit_approve"]
        decision = evaluate_human_activation_decision(
            packet,
            operator_action=approval["operator_action"],
            operator_id=approval["operator_id"],
            reason=approval["reason"],
        )
        self.assertEqual(decision["decision_status"], "activation_approved_for_next_phase")
        self.assertTrue(decision["rollback_simulation"]["passed"])
        self.assertTrue(decision["can_move_to_next_phase"])

    def test_explicit_reject_produces_activation_rejected(self) -> None:
        payload = _load_step13_fixture()
        packet = build_human_activation_review_packet(
            payload["pilot_results"]["clean_pilot_ready_packet"],
            governance_batch=payload["governance_batch_clean"],
        )
        rejection = payload["operator_scenarios"]["explicit_reject"]
        decision = evaluate_human_activation_decision(
            packet,
            operator_action=rejection["operator_action"],
            operator_id=rejection["operator_id"],
            reason=rejection["reason"],
        )
        self.assertEqual(decision["decision_status"], "activation_rejected")

    def test_hold_produces_activation_hold_manual_review(self) -> None:
        payload = _load_step13_fixture()
        packet = build_human_activation_review_packet(
            payload["pilot_results"]["clean_pilot_ready_packet"],
            governance_batch=payload["governance_batch_clean"],
        )
        hold = payload["operator_scenarios"]["explicit_hold"]
        decision = evaluate_human_activation_decision(
            packet,
            operator_action=hold["operator_action"],
            operator_id=hold["operator_id"],
            reason=hold["reason"],
        )
        self.assertEqual(decision["decision_status"], "activation_hold_manual_review")

    def test_request_remediation_produces_hold_with_remediation_actions(self) -> None:
        payload = _load_step13_fixture()
        packet = build_human_activation_review_packet(
            payload["pilot_results"]["clean_pilot_ready_packet"],
            governance_batch=payload["governance_batch_clean"],
        )
        remediation = payload["operator_scenarios"]["request_remediation"]
        decision = evaluate_human_activation_decision(
            packet,
            operator_action=remediation["operator_action"],
            operator_id=remediation["operator_id"],
            reason=remediation["reason"],
        )
        self.assertEqual(decision["decision_status"], "activation_hold_manual_review")
        self.assertIn("operator_requested_remediation", decision["remediation_actions"])

    def test_pilot_needs_remediation_does_not_approve(self) -> None:
        payload = _load_step13_fixture()
        packet = build_human_activation_review_packet(
            payload["pilot_results"]["pilot_needs_remediation_packet"],
            governance_batch=payload["governance_batch_pending"],
        )
        approval = payload["operator_scenarios"]["explicit_approve"]
        decision = evaluate_human_activation_decision(
            packet,
            operator_action=approval["operator_action"],
            operator_id=approval["operator_id"],
            reason=approval["reason"],
        )
        self.assertNotEqual(decision["decision_status"], "activation_approved_for_next_phase")

    def test_pilot_blocked_blocks_activation(self) -> None:
        payload = _load_step13_fixture()
        packet = build_human_activation_review_packet(
            payload["pilot_results"]["pilot_blocked_packet"],
            governance_batch=payload["governance_batch_pending"],
        )
        decision = evaluate_human_activation_decision(packet)
        self.assertEqual(decision["decision_status"], "activation_blocked")

    def test_rollback_simulation_failure_blocks_approval(self) -> None:
        payload = _load_step13_fixture()
        packet = build_human_activation_review_packet(
            payload["pilot_results"]["rollback_simulation_failure_packet"],
            governance_batch=payload["governance_batch_clean"],
        )
        simulation = simulate_human_activation_rollback(packet)
        self.assertFalse(simulation["passed"])
        approval = payload["operator_scenarios"]["explicit_approve"]
        decision = evaluate_human_activation_decision(
            packet,
            operator_action=approval["operator_action"],
            operator_id=approval["operator_id"],
            reason=approval["reason"],
        )
        self.assertEqual(decision["decision_status"], "activation_blocked")

    def test_audit_record_is_deterministic(self) -> None:
        payload = _load_step13_fixture()
        packet = build_human_activation_review_packet(
            payload["pilot_results"]["clean_pilot_ready_packet"],
            governance_batch=payload["governance_batch_clean"],
        )
        approval = payload["operator_scenarios"]["explicit_approve"]
        first = evaluate_human_activation_decision(
            packet,
            operator_action=approval["operator_action"],
            operator_id=approval["operator_id"],
            reason=approval["reason"],
        )
        second = evaluate_human_activation_decision(
            packet,
            operator_action=approval["operator_action"],
            operator_id=approval["operator_id"],
            reason=approval["reason"],
        )
        self.assertEqual(first["audit_records"], second["audit_records"])

    def test_non_public_and_non_sitemap_and_non_mass_publish_locks(self) -> None:
        payload = _load_step13_fixture()
        packet = build_human_activation_review_packet(
            payload["pilot_results"]["clean_pilot_ready_packet"],
            governance_batch=payload["governance_batch_clean"],
        )
        approval = payload["operator_scenarios"]["explicit_approve"]
        decision = evaluate_human_activation_decision(
            packet,
            operator_action=approval["operator_action"],
            operator_id=approval["operator_id"],
            reason=approval["reason"],
        )
        self.assertFalse(packet["can_publish_publicly"])
        self.assertFalse(packet["can_expand_live_sitemap"])
        self.assertFalse(packet["is_mass_publish"])
        self.assertFalse(decision["can_publish_publicly"])
        self.assertFalse(decision["can_expand_live_sitemap"])
        self.assertFalse(decision["is_public"])
        self.assertFalse(decision["is_live_sitemap_included"])
        self.assertFalse(decision["is_mass_publish"])

    def test_no_route_sitemap_naming_changes_no_gates_relaxed_no_fake_data_or_credentials(self) -> None:
        source = inspect.getsource(evaluate_human_activation_decision).lower()
        forbidden_tokens = (
            "requests",
            "httpx",
            "urllib.request",
            "scrape",
            "selenium",
            "playwright",
            "google api",
            "analytics api",
            "affiliate api",
            "api_key",
            "credential =",
            "impression",
            "clicks",
            "conversion",
            "revenue",
            "search_volume",
            "product_price",
        )
        for token in forbidden_tokens:
            self.assertNotIn(token, source)

    def test_mixed_activation_review_batch_summary(self) -> None:
        payload = _load_step13_fixture()
        clean_packet = build_human_activation_review_packet(
            payload["pilot_results"]["clean_pilot_ready_packet"],
            governance_batch=payload["governance_batch_clean"],
        )
        remediation_packet = build_human_activation_review_packet(
            payload["pilot_results"]["pilot_needs_remediation_packet"],
            governance_batch=payload["governance_batch_pending"],
        )
        blocked_packet = build_human_activation_review_packet(
            payload["pilot_results"]["pilot_blocked_packet"],
            governance_batch=payload["governance_batch_pending"],
        )
        rollback_fail_packet = build_human_activation_review_packet(
            payload["pilot_results"]["rollback_simulation_failure_packet"],
            governance_batch=payload["governance_batch_clean"],
        )
        action_map = {
            clean_packet["review_packet_id"]: payload["operator_scenarios"]["explicit_approve"],
            remediation_packet["review_packet_id"]: payload["operator_scenarios"]["request_remediation"],
            blocked_packet["review_packet_id"]: payload["operator_scenarios"]["explicit_hold"],
            rollback_fail_packet["review_packet_id"]: payload["operator_scenarios"]["explicit_approve"],
        }
        batch = evaluate_human_activation_batch(
            [clean_packet, remediation_packet, blocked_packet, rollback_fail_packet],
            operator_actions_by_packet=action_map,
        )
        self.assertEqual(batch["total_packets"], 4)
        self.assertEqual(batch["activation_approved_for_next_phase_count"], 1)
        self.assertEqual(batch["activation_hold_manual_review_count"], 0)
        self.assertEqual(batch["activation_blocked_count"], 3)
        self.assertFalse(batch["can_move_to_next_phase"])


if __name__ == "__main__":
    unittest.main()
