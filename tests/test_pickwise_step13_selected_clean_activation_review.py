from __future__ import annotations

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
)


def _load_step13_fixture() -> dict[str, Any]:
    fixture_path = ROOT / "tests" / "fixtures" / "step13_human_activation_review_inputs.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


class PickWiseStep13SelectedCleanActivationReviewTests(unittest.TestCase):
    def test_selected_clean_activation_review_fixture_loads(self) -> None:
        payload = _load_step13_fixture()
        self.assertIn("selected_clean_approval_cohort", payload)
        self.assertGreater(len(payload["selected_clean_approval_cohort"]), 0)

    def test_selected_clean_packets_are_approval_ready(self) -> None:
        payload = _load_step13_fixture()
        packets = [
            build_human_activation_review_packet(item, governance_batch=payload["governance_batch_clean"])
            for item in payload["selected_clean_approval_cohort"]
        ]
        self.assertTrue(all(packet["pilot_status"] == "pilot_ready" for packet in packets))
        self.assertTrue(all(packet["can_request_human_activation_review"] for packet in packets))
        self.assertTrue(all(packet["rollback_drill_status"] == "rollback_drill_passed" for packet in packets))

    def test_explicit_approve_yields_all_activation_approved_and_can_move_next_phase(self) -> None:
        payload = _load_step13_fixture()
        packets = [
            build_human_activation_review_packet(item, governance_batch=payload["governance_batch_clean"])
            for item in payload["selected_clean_approval_cohort"]
        ]
        action_map = {
            packet["review_packet_id"]: {
                "operator_action": "approve",
                "operator_id": "operator-selected-clean",
                "reason": "Selected clean cohort approved for next phase.",
            }
            for packet in packets
        }
        batch = evaluate_human_activation_batch(packets, operator_actions_by_packet=action_map)
        self.assertEqual(batch["total_packets"], len(packets))
        self.assertEqual(batch["activation_approved_for_next_phase_count"], len(packets))
        self.assertEqual(batch["rollback_simulation_pass_count"], len(packets))
        self.assertTrue(batch["can_move_to_next_phase"])

    def test_selected_clean_batch_remains_non_public_non_sitemap_non_mass_publish(self) -> None:
        payload = _load_step13_fixture()
        packets = [
            build_human_activation_review_packet(item, governance_batch=payload["governance_batch_clean"])
            for item in payload["selected_clean_approval_cohort"]
        ]
        action_map = {
            packet["review_packet_id"]: {
                "operator_action": "approve",
                "operator_id": "operator-selected-clean",
                "reason": "Selected clean cohort approved for next phase.",
            }
            for packet in packets
        }
        batch = evaluate_human_activation_batch(packets, operator_actions_by_packet=action_map)
        for decision in batch["decisions"]:
            self.assertFalse(decision["can_publish_publicly"])
            self.assertFalse(decision["can_expand_live_sitemap"])
            self.assertFalse(decision["is_public"])
            self.assertFalse(decision["is_live_sitemap_included"])
            self.assertFalse(decision["is_mass_publish"])

    def test_selected_clean_batch_no_credentials_api_or_live_provider_integration(self) -> None:
        payload = _load_step13_fixture()
        packets = [
            build_human_activation_review_packet(item, governance_batch=payload["governance_batch_clean"])
            for item in payload["selected_clean_approval_cohort"]
        ]
        for packet in packets:
            evidence = packet["evidence_summary"]
            self.assertTrue(evidence["dry_run_only"])
            self.assertFalse(packet["can_publish_publicly"])
            self.assertFalse(packet["can_expand_live_sitemap"])
            self.assertFalse(packet["is_mass_publish"])


if __name__ == "__main__":
    unittest.main()
