"""The tests run by themselves on each push of code (the audit, 2026-11-10).

The audit found that no workflow ran the tests and that a deployment did not wait for
them. `tools/run_test_modules.py` runs each module in a process of its own, several at a
time, and `.github/workflows/tests.yml` runs it on each push that changes code. Pinned
here, without running the suite inside itself:

- what a module's run said is read from `unittest`'s own output;
- the run is wrong, exit 1, when a module fails or does not finish; unless the module is
  one of the two `README.md` names as known to fail and fails in its known test only:
  those are run and reported every time, never skipped;
- a known module that fails in another test is wrong; one that passes is said;
- a module really run: one that passes, one that fails;
- the workflow runs the tool on a push of code to a session's branch, reads the
  repository and nothing else, and holds no key.
"""
from __future__ import annotations

import importlib.util
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_tool():
    spec = importlib.util.spec_from_file_location("run_test_modules_tool", ROOT / "tools" / "run_test_modules.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


tool = _load_tool()
_STAGE2 = "test_picwise_canonical_vocabulary_registry_stage2"
_STAGE2_TEST = "test_live_search_provider_and_surface_files_unchanged_in_this_stage"


class ReadingARunTests(unittest.TestCase):
    def test_what_a_run_said(self) -> None:
        passed = tool.read_output("test_a", 0, "....\n" + "-" * 70 + "\nRan 4 tests in 0.012s\n\nOK\n", 0.5)
        self.assertEqual((passed.outcome, passed.ran, passed.failed_tests), ("passed", 4, ()))
        output = (
            "F.E\n======\nFAIL: test_one (tests.test_b.Some.test_one)\n------\nTraceback ...\n"
            "======\nERROR: test_two (tests.test_b.Some.test_two)\n------\nTraceback ...\n"
            "Ran 3 tests in 0.2s\n\nFAILED (failures=1, errors=1)\n"
        )
        failed = tool.read_output("test_b", 1, output, 1.0)
        self.assertEqual((failed.outcome, failed.ran, failed.failed_tests), ("failed", 3, ("test_one", "test_two")))
        self.assertIn("FAILED (failures=1, errors=1)", failed.tail)
        # A module that could not be loaded names no test of its own.
        broken = tool.read_output("test_c", 1, "ImportError: no module named x\n", 0.1)
        self.assertEqual((broken.outcome, broken.ran, broken.failed_tests), ("failed", 0, ()))

    def test_every_module_of_the_repository_is_found(self) -> None:
        modules = tool.test_modules()
        self.assertIn("test_picwise_run_test_modules", modules)
        self.assertEqual(modules, sorted(path.stem for path in (ROOT / "tests").glob("test_*.py")))
        for module in (*tool.KNOWN_FAILING, *tool.SLOW):
            self.assertIn(module, modules)


class JudgingARunTests(unittest.TestCase):
    def _result(self, module: str, outcome: str = "passed", failed: tuple[str, ...] = (), ran: int = 3):
        return tool.ModuleResult(module=module, outcome=outcome, ran=ran, seconds=1.0, failed_tests=failed, tail="the tail")

    def test_every_module_passed(self) -> None:
        lines, code = tool.judge([self._result("test_a"), self._result("test_b")])
        self.assertEqual(code, 0)
        self.assertEqual(lines, ["2 modules, 6 tests: 2 modules passed, 0 failed as known, 0 failed or did not finish"])

    def test_a_module_that_fails_or_does_not_finish_is_wrong(self) -> None:
        lines, code = tool.judge([
            self._result("test_a"),
            self._result("test_b", "failed", ("test_one",)),
            self._result("test_c", "timed_out", ran=0),
            self._result("test_d", "failed", (), ran=0),
        ])
        self.assertEqual(code, 1)
        self.assertIn("FAILED (test_one): test_b", lines)
        self.assertIn("    the tail", lines)
        self.assertIn("DID NOT FINISH in 1 s: test_c", lines)
        self.assertIn("FAILED (no test named: the module did not load or run): test_d", lines)
        self.assertTrue(lines[-1].endswith("1 modules passed, 0 failed as known, 3 failed or did not finish"))

    def test_the_two_known_modules_are_reported_and_do_not_make_the_run_wrong(self) -> None:
        self.assertEqual(
            set(tool.KNOWN_FAILING),
            {_STAGE2, "test_picwise_search_index_generated_blind_stage4"},
        )
        # The two README.md names, and no other.
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for module in tool.KNOWN_FAILING:
            self.assertIn(module, readme)
        lines, code = tool.judge([self._result("test_a"), self._result(_STAGE2, "failed", (_STAGE2_TEST,))])
        self.assertEqual(code, 0)
        self.assertIn(f"known to fail ({_STAGE2_TEST}): {_STAGE2}", lines)
        self.assertTrue(lines[-1].endswith("1 modules passed, 1 failed as known, 0 failed or did not finish"))

    def test_a_known_module_that_fails_in_another_test_is_wrong(self) -> None:
        for failed in ((_STAGE2_TEST, "test_another"), ("test_another",), ()):
            with self.subTest(failed=failed):
                _lines, code = tool.judge([self._result(_STAGE2, "failed", failed)])
                self.assertEqual(code, 1)
        _lines, code = tool.judge([self._result(_STAGE2, "timed_out")])
        self.assertEqual(code, 1)

    def test_a_known_module_that_passes_is_said(self) -> None:
        lines, code = tool.judge([self._result(_STAGE2)])
        self.assertEqual(code, 0)
        self.assertIn(f"NOW PASSES, take it off KNOWN_FAILING: {_STAGE2}", lines)


class AModuleReallyRunTests(unittest.TestCase):
    def _folder(self) -> Path:
        root = Path(tempfile.mkdtemp())
        (root / "tests").mkdir()
        (root / "tests" / "__init__.py").write_text("", encoding="utf-8")
        (root / "tests" / "test_good.py").write_text(
            "import unittest\n\nclass T(unittest.TestCase):\n    def test_fine(self):\n        self.assertTrue(True)\n",
            encoding="utf-8",
        )
        (root / "tests" / "test_bad.py").write_text(
            "import unittest\n\nclass T(unittest.TestCase):\n    def test_wrong(self):\n        self.assertEqual(1, 2)\n",
            encoding="utf-8",
        )
        (root / "tests" / "test_long.py").write_text(
            "import time, unittest\n\nclass T(unittest.TestCase):\n    def test_slow(self):\n        time.sleep(30)\n",
            encoding="utf-8",
        )
        return root

    def test_one_that_passes_one_that_fails_one_that_does_not_finish(self) -> None:
        root = self._folder()
        self.assertEqual(tool.test_modules(root / "tests"), ["test_bad", "test_good", "test_long"])
        good = tool.run_module("test_good", root=root)
        self.assertEqual((good.outcome, good.ran, good.failed_tests), ("passed", 1, ()))
        bad = tool.run_module("test_bad", root=root)
        self.assertEqual((bad.outcome, bad.ran, bad.failed_tests), ("failed", 1, ("test_wrong",)))
        long = tool.run_module("test_long", root=root, timeout=1)
        self.assertEqual(long.outcome, "timed_out")
        lines, code = tool.judge([good, bad, long])
        self.assertEqual(code, 1)
        self.assertIn("FAILED (test_wrong): test_bad", lines)


class TheWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workflow = (ROOT / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")

    def test_it_runs_the_tool_on_a_push_of_code_to_a_sessions_branch(self) -> None:
        self.assertIn('branches: ["ccr-**"]', self.workflow)
        self.assertIn("workflow_dispatch:", self.workflow)
        for path in ('"src/**"', '"api/**"', '"tests/**"', '"tools/**"', '"deployment/**"'):
            self.assertIn(f"- {path}", self.workflow)
        self.assertIn("run: python tools/run_test_modules.py --skip-slow", self.workflow)
        self.assertIn("run: python tools/run_test_modules.py --only-slow", self.workflow)
        # Never on `main`, as every workflow of the repository (`README.md`).
        self.assertNotIn("main", re.sub(r"#.*", "", self.workflow))

    def test_it_reads_the_repository_and_holds_no_key(self) -> None:
        self.assertIn("permissions:\n  contents: read\n", self.workflow)
        for never in ("secrets.", "ssh", "SERVER_", "AWIN_", "ANTHROPIC_"):
            self.assertNotIn(never, self.workflow)


if __name__ == "__main__":
    unittest.main()
