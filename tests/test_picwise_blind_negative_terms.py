"""The blind evaluation's broad negative terms, checked in seconds instead of an hour.

`tests/test_picwise_search_index_blind_evaluation_stage6a.py` expects eleven broad terms
among the generated cases (`test_negative_broad_terms_are_included`). The generator's
list, `blind_evaluation._NEGATIVE_BROAD_TERMS`, held nine of them from 2026-05-21: that
day's commit (`6944f94`) put "amazon" and "galaxy" into the test and into the unsafe
broad queries of `broad_query_suggestions`, and not into the list, so the test could
never pass. A session ran the module to its end on 2026-11-05 and recorded this very
cause (`PROGRESS.md`), and nothing was changed for it: the module builds the registry,
the index and some 15,000 cases again before each of its 13 tests, half an hour to an
hour in all, and runs before no deployment. GitHub's "Tests" ran it on 2026-11-11 and
the review of the audit's fixes fixed it on 2026-11-12. Pinned here, where every push
runs it:

- the generator's list is the terms the slow test expects, read from that test's source;
- each of them is an unsafe broad query, by the rule the search itself uses;
- the cases generated hold exactly those terms as broad negatives, none to be matched.
"""
from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_search_memory import blind_evaluation  # noqa: E402
from picwise_search_memory.broad_query_suggestions import is_unsafe_broad_query  # noqa: E402
from picwise_search_memory.canonical_registry import build_canonical_vocabulary_registry  # noqa: E402
from picwise_search_memory.index_builder import build_offline_search_index  # noqa: E402

_SLOW_TEST = ROOT / "tests" / "test_picwise_search_index_blind_evaluation_stage6a.py"
_ELEVEN = {
    "bank", "apple", "nike", "bosch", "insurance", "loan", "erp", "crm", "accounting software",
    "amazon", "galaxy",
}


def _expected_by_the_slow_test() -> set[str]:
    """The set `test_negative_broad_terms_are_included` compares the cases with."""
    tree = ast.parse(_SLOW_TEST.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "test_negative_broad_terms_are_included":
            for inner in ast.walk(node):
                if (
                    isinstance(inner, ast.Assign)
                    and isinstance(inner.value, ast.Set)
                    and any(isinstance(target, ast.Name) and target.id == "broad_terms" for target in inner.targets)
                ):
                    return {str(ast.literal_eval(element)) for element in inner.value.elts}
    raise AssertionError("the slow test no longer names its broad terms as it did")


class BroadNegativeTermsTests(unittest.TestCase):
    def test_the_generators_list_is_what_the_slow_test_expects(self) -> None:
        expected = _expected_by_the_slow_test()
        self.assertEqual(expected, _ELEVEN)
        self.assertEqual(set(blind_evaluation._NEGATIVE_BROAD_TERMS), expected)
        # Each once.
        self.assertEqual(len(blind_evaluation._NEGATIVE_BROAD_TERMS), len(expected))

    def test_each_is_an_unsafe_broad_query(self) -> None:
        for term in blind_evaluation._NEGATIVE_BROAD_TERMS:
            with self.subTest(term=term):
                self.assertTrue(is_unsafe_broad_query(term))

    def test_the_cases_generated_hold_exactly_those_terms_as_broad_negatives(self) -> None:
        registry = build_canonical_vocabulary_registry()
        index = build_offline_search_index(registry)
        cases = blind_evaluation.generate_blind_evaluation_cases(registry, include_negative_terms=True, index=index)
        broad = [case for case in cases if case.variant_type == "broad_term_negative"]
        self.assertEqual({case.query for case in broad}, _ELEVEN)
        self.assertEqual(len(broad), len(_ELEVEN))
        self.assertTrue(all(not case.should_match for case in broad))
        # And the index answers none of them with a product (what the slow module's
        # thresholds read as the broad terms' safety).
        results = blind_evaluation.evaluate_blind_cases(broad, index)
        self.assertEqual([result.passed for result in results], [True] * len(broad))


if __name__ == "__main__":
    unittest.main()
