import inspect
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_app import PicwiseLocalApp
from picwise_learning.stage31_config import Stage31ActivationConfig
from picwise_learning.stage31_runtime_controller import Stage31RuntimeController


class _NoopProbe:
    def observe_runtime_decision(self, **_kwargs):
        return None


class _Stage31RecordingController:
    def __init__(self) -> None:
        self.calls = 0
        self.last_candidate = None

    def process_runtime_decision(self, **kwargs):
        self.calls += 1
        runtime_decision = dict(kwargs["runtime_decision"])
        candidate = {
            "did_affect_runtime": False,
            "activation_status": "disabled",
            "vertical": runtime_decision.get("vertical"),
        }
        self.last_candidate = candidate
        return runtime_decision, candidate


class _FailingStage31Controller:
    def process_runtime_decision(self, **_kwargs):
        raise RuntimeError("stage31_failure")


class TestPickwiseStage31RuntimeGuardrails(unittest.TestCase):
    def test_default_runtime_output_unchanged_when_stage31_disabled(self) -> None:
        app_default = PicwiseLocalApp(stage30_probe=_NoopProbe())
        app_stage31_disabled = PicwiseLocalApp(
            stage30_probe=_NoopProbe(),
            stage31_controller=Stage31RuntimeController(
                config=Stage31ActivationConfig(activation_enabled=False)
            ),
        )
        query = "power bank for iphone"
        output_default = app_default.build_demo_output(query)
        output_stage31_disabled = app_stage31_disabled.build_demo_output(query)
        self.assertEqual(output_default, output_stage31_disabled)

    def test_activation_disabled_keeps_did_affect_runtime_false(self) -> None:
        stage31 = _Stage31RecordingController()
        app = PicwiseLocalApp(stage30_probe=_NoopProbe(), stage31_controller=stage31)
        _ = app.build_demo_output("power bank for iphone")
        self.assertEqual(stage31.calls, 1)
        self.assertFalse(stage31.last_candidate["did_affect_runtime"])

    def test_stage31_controller_failure_does_not_change_runtime_output(self) -> None:
        app_noop = PicwiseLocalApp(stage30_probe=_NoopProbe())
        app_failing = PicwiseLocalApp(
            stage30_probe=_NoopProbe(),
            stage31_controller=_FailingStage31Controller(),
        )
        query = "power bank for iphone"
        output_noop = app_noop.build_demo_output(query)
        output_failing = app_failing.build_demo_output(query)
        self.assertEqual(output_noop, output_failing)

    def test_finance_never_auto_activates(self) -> None:
        controller = Stage31RuntimeController(config=Stage31ActivationConfig(activation_enabled=True))
        runtime_decision, candidate = controller.process_runtime_decision(
            runtime_query="best business finance software",
            runtime_decision={
                "status": "general_product_discovery_allowed",
                "existing_runtime_target": "finance_tax_accounting",
                "existing_runtime_vertical": "finance_insurance_business_finance",
                "vertical": "finance_insurance_business_finance",
                "comparison_status": "aligned",
                "shadow_confidence": 0.99,
                "shadow_nlu_target": "finance_tax_accounting",
            },
        )
        self.assertEqual(candidate.activation_status, "manual_review")
        self.assertFalse(candidate.did_affect_runtime)
        self.assertEqual(runtime_decision["vertical"], "finance_insurance_business_finance")

    def test_saas_erp_not_forced_into_retail_vertical(self) -> None:
        controller = Stage31RuntimeController(
            config=Stage31ActivationConfig(
                activation_enabled=True,
                allow_saas_erp=True,
                allowed_verticals=("retail_physical_products", "software_saas_erp"),
                min_confidence=0.8,
            )
        )
        _runtime_decision, candidate = controller.process_runtime_decision(
            runtime_query="best saas erp for inventory planning",
            runtime_decision={
                "status": "general_product_discovery_allowed",
                "existing_runtime_target": "erp_core",
                "existing_runtime_vertical": "software_saas_erp",
                "vertical": "software_saas_erp",
                "comparison_status": "aligned",
                "shadow_confidence": 0.95,
                "shadow_nlu_target": "erp_core",
            },
        )
        self.assertEqual(candidate.vertical, "software_saas_erp")

    def test_stage31_no_commercial_or_stage32_logic_in_controller(self) -> None:
        with patch("picwise_app.app.build_default_stage30_runtime_probe", return_value=_NoopProbe()):
            app = PicwiseLocalApp(
                stage31_controller=Stage31RuntimeController(
                    config=Stage31ActivationConfig(activation_enabled=False)
                )
            )
        output = app.build_demo_output("power bank for iphone")
        self.assertEqual(len(output.choices), 4)

        controller_source = inspect.getsource(Stage31RuntimeController).lower()
        forbidden = (
            "apply_update_pack",
            "build_update_pack(",
            "stage32",
            "checkout",
            "cart",
            "payment",
            "quote",
            "affiliate",
            "commission",
            "seller",
            "stock",
            "sku",
            "offer",
            "price",
            "redirect",
            "ranking",
            "provider",
            "eligibility",
            "application",
        )
        self.assertTrue(all(token not in controller_source for token in forbidden))


if __name__ == "__main__":
    unittest.main()
