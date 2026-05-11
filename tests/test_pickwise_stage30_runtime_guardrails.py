import inspect
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_app import PicwiseLocalApp
from picwise_learning import stage30_failure_bridge, stage30_runtime_probe, stage30_shadow_runner


class _NoopProbe:
    def observe_runtime_decision(self, **_kwargs):
        return None


class _FailingProbe:
    def observe_runtime_decision(self, **_kwargs):
        raise RuntimeError("probe_failure")


class _RecordingProbe:
    def __init__(self) -> None:
        self.calls = 0
        self.last_payload = {}

    def observe_runtime_decision(self, **kwargs):
        self.calls += 1
        self.last_payload = dict(kwargs)
        return None


class TestPickwiseStage30RuntimeGuardrails(unittest.TestCase):
    def test_runtime_output_unchanged_when_probe_fails(self) -> None:
        app_noop = PicwiseLocalApp(stage30_probe=_NoopProbe())
        app_failing = PicwiseLocalApp(stage30_probe=_FailingProbe())
        query = "power bank for iphone"
        output_noop = app_noop.build_demo_output(query)
        output_failing = app_failing.build_demo_output(query)
        self.assertEqual(output_noop, output_failing)

    def test_passive_hook_runs_after_runtime_decision(self) -> None:
        probe = _RecordingProbe()
        app = PicwiseLocalApp(stage30_probe=probe)
        _ = app.build_demo_output("laptop for school")
        self.assertEqual(probe.calls, 1)
        self.assertIn("runtime_query", probe.last_payload)
        self.assertIn("runtime_decision", probe.last_payload)
        self.assertEqual(probe.last_payload["runtime_query"], "laptop for school")

    def test_stage30_does_not_apply_stage29_update_packs_or_stage31_logic(self) -> None:
        source = "\n".join(
            [
                inspect.getsource(stage30_runtime_probe).lower(),
                inspect.getsource(stage30_shadow_runner).lower(),
                inspect.getsource(stage30_failure_bridge).lower(),
            ]
        )
        forbidden = (
            "stage31",
            "build_update_pack(",
            "apply_update_pack",
            "checkout",
            "cart",
            "payment",
            "affiliate",
            "provider marketplace",
        )
        self.assertTrue(all(token not in source for token in forbidden))


if __name__ == "__main__":
    unittest.main()
