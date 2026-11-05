"""One request of the AI layer, end to end, on six fictional washing machines.

Before the offline measure (`measure_ai.py`, the AI layer's spec 4.8) reads the server's
catalogue, this sends Claude Haiku 5.5 the very request the layer builds
(`picwise_ai.request`), through the SDK installed from `requirements-ai.txt`, and reads
the answer with the layer's own code (`picwise_ai.client`, `picwise_ai.checks`). No
catalogue, server or site is involved; the products are fictional; one call costs well
under a cent. Printed: the answer for each product, the sentence and whether the checks
pass, the tokens, the cost, the time. Never the key.

    ANTHROPIC_API_KEY=... python3 deployment/server/ai_preflight.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for folder in (ROOT, ROOT / "src"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

# Two say quiet in their own words, four do not say.
PRODUCTS = (
    ("Fixturon WM1045 10kg 1400rpm Washing Machine White", "Fixturon", "279.00 GBP"),
    ("Testline Series 6 9kg Quiet Mark Approved Washing Machine", "Testline", "549.00 GBP"),
    ("Fixturon EcoWash 9kg Washing Machine Graphite", "Fixturon", "429.99 GBP"),
    ("Testline SilentDrive 8kg Washing Machine Low Noise 47dB", "Testline", "499.00 GBP"),
    ("Fixturon Compact 6kg Washing Machine", "Fixturon", "239.00 GBP"),
    ("Testline Steam Care 10kg Washing Machine", "Testline", "619.00 GBP"),
)


def main() -> int:
    from picwise_ai.checks import check_answer
    from picwise_ai.client import ask, make_client
    from picwise_ai.complex_search import Candidate, ComplexSearch
    from picwise_ai.request import EFFORT, MODEL, request_kwargs

    complex_search = ComplexSearch(
        search="quiet washing machine",
        words=("quiet",),
        kind_name="washing machine",
        fell_back=False,
        candidates=tuple(
            Candidate(number, f"preflight-{number}", title, brand, price, "GBP", "Fictional Appliances")
            for number, (title, brand, price) in enumerate(PRODUCTS, start=1)
        ),
        total=len(PRODUCTS),
    )
    asked = ask(request_kwargs(complex_search), client=make_client())
    print(f"model asked: {MODEL}, effort {EFFORT}; answered by: {asked.model or 'none'}")
    print(f"stop reason: {asked.stop_reason or 'none'}; error: {asked.error or 'none'}")
    print(f"tokens: {asked.input_tokens} in, {asked.output_tokens} out, cache written {asked.cache_write_tokens},"
          f" cache read {asked.cache_read_tokens}; cost ${asked.cost_usd:.6f}; {asked.seconds:.1f} s")
    answer = asked.answer or {}
    fits = {verdict.get("n"): verdict.get("fits") for verdict in answer.get("verdicts") or () if isinstance(verdict, dict)}
    for number, (title, _brand, price) in enumerate(PRODUCTS, start=1):
        print(f"  {fits.get(number, '(none)'):8} {number}. {title} | {price}")
    print(f"sentence written: {answer.get('sentence') or '(none)'}")
    checked = check_answer(asked.answer, complex_search, stop_reason=asked.stop_reason)
    print("the checks: " + ("PASS, the sentence would be shown" if checked.shown else f"withheld: {checked.failure}"))
    return 0 if asked.answer is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
