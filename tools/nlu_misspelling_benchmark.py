"""Run the end-to-end misspelling benchmark and print how well PicWise understands buyers.

    python tools/nlu_misspelling_benchmark.py
    python tools/nlu_misspelling_benchmark.py --json report.json
    python tools/nlu_misspelling_benchmark.py --failures 40

Runs against the in-repo coverage fixture feed by default, so it measures understanding
given inventory, not the contents of any real provider feed.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_app.nlu_benchmark import (  # noqa: E402
    DEFAULT_BENCHMARK_FEED,
    build_misspelling_benchmark,
    run_misspelling_benchmark,
)


def _print_group(title: str, group: dict[str, dict]) -> None:
    print(f"\n{title}")
    width = max((len(name) for name in group), default=10)
    for name, row in group.items():
        bar = "#" * int(round(row["pass_rate"] * 20))
        extra = []
        if row["wrong_family"]:
            extra.append(f"WRONG {row['wrong_family']}")
        if row["ambiguous"]:
            extra.append(f"ambiguous {row['ambiguous']}")
        if row["empty"]:
            extra.append(f"empty {row['empty']}")
        print(
            f"  {name:<{width}}  {row['pass_rate']*100:5.1f}%  {bar:<20}  "
            f"n={row['cases']:<4} {'  '.join(extra)}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="PicWise misspelling benchmark")
    parser.add_argument("--feed", default=str(DEFAULT_BENCHMARK_FEED))
    parser.add_argument("--json", default="", help="Write the full outcome list to this file")
    parser.add_argument("--failures", type=int, default=25, help="How many failures to list")
    parser.add_argument("--no-product-types", action="store_true")
    args = parser.parse_args()

    logging.disable(logging.WARNING)
    cases = build_misspelling_benchmark()
    outcomes, summary = run_misspelling_benchmark(cases, feed_file=args.feed)

    print(f"PicWise misspelling benchmark — {summary['cases']} cases")
    print(
        f"  PASS {summary['pass_rate']*100:.1f}%   "
        f"wrong answers {summary['wrong_family']}   "
        f"not understood {summary['empty']}   "
        f"ambiguous {summary['ambiguous']}   "
        f"latency median {summary['latency_ms_median']:.0f}ms p95 {summary['latency_ms_p95']:.0f}ms"
    )
    _print_group("By source", summary["by_source"])
    _print_group("By language", summary["by_language"])
    _print_group("By error class", summary["by_error_class"])
    if not args.no_product_types:
        _print_group("By product type", summary["by_product_type"])

    failures = [o for o in outcomes if o.outcome != "pass"]
    failures.sort(key=lambda o: (o.outcome != "wrong_family", o.case.source, o.case.query))
    if failures and args.failures:
        print(f"\nFailures (first {min(args.failures, len(failures))} of {len(failures)}, wrong answers first)")
        for o in failures[: args.failures]:
            got = ",".join(sorted(set(o.rendered_product_types))) or "-"
            print(
                f"  [{o.outcome:12s}] {o.case.query!r:40s} expected={o.case.expected_product_type or 'refuse'!s:26s}"
                f" got={got} ({o.case.error_class})"
            )

    if args.json:
        Path(args.json).write_text(
            json.dumps(
                {"summary": summary, "outcomes": [o.to_dict() for o in outcomes]},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"\nWrote {args.json}")


if __name__ == "__main__":
    main()
