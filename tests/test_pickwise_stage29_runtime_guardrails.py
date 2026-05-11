import inspect
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_learning import stage29_evaluation, stage29_query_generator, stage29_seed_builder


class TestPickwiseStage29RuntimeGuardrails(unittest.TestCase):
    def test_stage29_modules_are_offline_and_do_not_import_runtime_surfaces(self) -> None:
        source = "\n".join(
            [
                inspect.getsource(stage29_seed_builder).lower(),
                inspect.getsource(stage29_query_generator).lower(),
                inspect.getsource(stage29_evaluation).lower(),
            ]
        )
        forbidden = (
            "picwise_app",
            "picwise_search",
            "offer_resolver",
            "buying_page",
            "router",
            "stage30",
            "http://",
            "https://",
            "requests.",
        )
        self.assertTrue(all(token not in source for token in forbidden))

    def test_stage29_does_not_include_commercial_or_marketplace_logic(self) -> None:
        source = "\n".join(
            [
                inspect.getsource(stage29_seed_builder).lower(),
                inspect.getsource(stage29_query_generator).lower(),
                inspect.getsource(stage29_evaluation).lower(),
            ]
        )
        forbidden = (
            "inventory",
            "seller",
            "sku",
            "stock",
            "affiliate",
            "checkout",
            "cart",
            "payment",
            "ranking",
            "redirect",
        )
        self.assertTrue(all(token not in source for token in forbidden))


if __name__ == "__main__":
    unittest.main()
