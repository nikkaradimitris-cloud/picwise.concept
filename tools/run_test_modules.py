"""Run every test module, each on its own, several at a time, and say which did not pass.

    python tools/run_test_modules.py
    python tools/run_test_modules.py --skip-slow
    python tools/run_test_modules.py --only-slow --timeout 6000
    python tools/run_test_modules.py tests/test_picwise_kind_index.py tests/test_picwise_price_first.py

The audit of 2026-11-10 found that nothing ran the tests by itself: no workflow called
them and a deployment did not wait for them, so whether they had passed rested on the
session having run them by hand; and that the whole suite in one process took more than
25 minutes. This runs each module in a process of its own (as the sessions do before a
deployment: "every test module run on its own"), as many at a time as the machine has
processors, and is what `.github/workflows/tests.yml` runs on each push of code.

It exits 0 only when every module passed, or failed as `KNOWN_FAILING` says it does: the
two modules `README.md` names as failing since before 2026-10-23, each with the one test
that fails. They are run and reported every time, never skipped: a module of the list
that fails in another test, or any other module that fails or does not finish, exits 1;
one of the list that passes is said, so that it is taken off the list.

`SLOW` are the two modules that take many minutes each; `--skip-slow` leaves them to
`--only-slow`, which a workflow runs beside the rest.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# The modules `README.md` names as known to fail, each with the test that fails in it.
KNOWN_FAILING = {
    "test_picwise_canonical_vocabulary_registry_stage2": (
        "test_live_search_provider_and_surface_files_unchanged_in_this_stage",
    ),
    "test_picwise_search_index_generated_blind_stage4": (
        "test_generated_blind_evaluation_resolves_to_same_canonical_or_category",
    ),
}
# The modules that take many minutes each.
SLOW = ("test_picwise_learning_stage7b", "test_picwise_search_index_blind_evaluation_stage6a")
DEFAULT_TIMEOUT_SECONDS = 900


@dataclass(frozen=True)
class ModuleResult:
    module: str
    # "passed", "failed" or "timed_out".
    outcome: str
    ran: int = 0
    seconds: float = 0.0
    # The names of the tests that failed or raised.
    failed_tests: tuple[str, ...] = ()
    # The end of the module's output, for a failure's report.
    tail: str = ""


def test_modules(folder: Path | None = None) -> list[str]:
    """Every test module of the repository, by name, in order."""
    return sorted(path.stem for path in (folder or ROOT / "tests").glob("test_*.py"))


def read_output(module: str, returncode: int, output: str, seconds: float) -> ModuleResult:
    """What one module's run of `unittest` said."""
    ran = re.search(r"^Ran (\d+) tests? in", output, flags=re.M)
    failed = tuple(dict.fromkeys(re.findall(r"^(?:FAIL|ERROR): (\S+)", output, flags=re.M)))
    return ModuleResult(
        module=module,
        outcome="passed" if returncode == 0 else "failed",
        ran=int(ran.group(1)) if ran else 0,
        seconds=seconds,
        failed_tests=failed,
        tail="\n".join(output.strip().splitlines()[-25:]),
    )


def run_module(module: str, *, timeout: float = DEFAULT_TIMEOUT_SECONDS, root: Path = ROOT) -> ModuleResult:
    """Run one module in a process of its own."""
    started = time.perf_counter()
    try:
        done = subprocess.run(
            [sys.executable, "-m", "unittest", f"tests.{module}"],
            cwd=root, capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return ModuleResult(module=module, outcome="timed_out", seconds=time.perf_counter() - started)
    return read_output(module, done.returncode, done.stderr + done.stdout, time.perf_counter() - started)


def judge(results: list[ModuleResult]) -> tuple[list[str], int]:
    """What to say of a run, and the exit code: 0 only when every module passed or failed
    as `KNOWN_FAILING` says it does."""
    lines: list[str] = []
    wrong = 0
    for result in results:
        known = KNOWN_FAILING.get(result.module)
        if result.outcome == "passed":
            if known is not None:
                lines.append(f"NOW PASSES, take it off KNOWN_FAILING: {result.module}")
            continue
        if result.outcome == "timed_out":
            wrong += 1
            lines.append(f"DID NOT FINISH in {result.seconds:.0f} s: {result.module}")
            continue
        if known is not None and result.failed_tests and set(result.failed_tests) <= set(known):
            lines.append(f"known to fail ({', '.join(result.failed_tests)}): {result.module}")
            continue
        wrong += 1
        tests = ", ".join(result.failed_tests) or "no test named: the module did not load or run"
        lines.append(f"FAILED ({tests}): {result.module}")
        lines.extend(f"    {line}" for line in result.tail.splitlines())
    passed = sum(1 for result in results if result.outcome == "passed")
    tests_run = sum(result.ran for result in results)
    lines.append(
        f"{len(results)} modules, {tests_run} tests: {passed} modules passed, "
        f"{len(results) - passed - wrong} failed as known, {wrong} failed or did not finish"
    )
    return lines, 1 if wrong else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("modules", nargs="*", help="test modules or their files; every module when none")
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 2, help="how many modules run at a time")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS, help="seconds a module may take")
    slow = parser.add_mutually_exclusive_group()
    slow.add_argument("--skip-slow", action="store_true", help="leave the modules of SLOW out")
    slow.add_argument("--only-slow", action="store_true", help="run the modules of SLOW only")
    args = parser.parse_args(argv)

    modules = [Path(name).stem for name in args.modules] or test_modules()
    if args.skip_slow:
        modules = [module for module in modules if module not in SLOW]
    if args.only_slow:
        modules = [module for module in modules if module in SLOW]
    if not modules:
        print("no test module to run")
        return 1

    started = time.perf_counter()
    results: list[ModuleResult] = []
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        for result in pool.map(lambda module: run_module(module, timeout=args.timeout), modules):
            results.append(result)
            if result.outcome != "passed":
                print(f"{result.outcome}: {result.module} ({result.seconds:.0f} s)", flush=True)
    lines, code = judge(results)
    print("\n".join(lines))
    print(f"in {time.perf_counter() - started:.0f} s, {max(1, args.jobs)} at a time")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
