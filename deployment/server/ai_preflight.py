"""Two requests of the AI layer, end to end, on fictional washing machines.

Before the offline measure (`measure_ai.py`, the AI layer's spec 4.8) reads the server's
catalogue, this sends Claude Haiku 5.5 the very requests the layer builds
(`picwise_ai.request`), through the SDK installed from `requirements-ai.txt`, and reads
the answers with the layer's own code (`picwise_ai.client`, `picwise_ai.checks`):

1. "quiet washing machine": two titles say it, a third product only in its description;
   the answer is a sentence;
2. "washing machine for a small kitchen": no title or description says it, two titles say
   "Compact"; the answer is no sentence, but the shops' words (owner, 2026-11-05: «ΟΤΑΝ
   ΔΕΝ ΒΡΙΣΚΕΙ ΚΑΤΙ ΝΑ ΜΗΝ ΛΕΕΙ ΔΕΝ ΒΡΕΘΗΚΕ ΣΚΕΨΟΥ ΚΑΤΙ ΠΙΟ ΕΞΥΠΝΟ», then «ΣΩΣΤΑ»).

No catalogue, server or site is involved, so the words are not counted by a catalogue
here; the products are fictional; the two calls cost well under a cent. Printed: each
product's answer, the sentence or the words, whether the checks pass, the tokens, the
cost, the time. Never the key.

    ANTHROPIC_API_KEY=... python3 deployment/server/ai_preflight.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for folder in (ROOT, ROOT / "src"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

# (title, brand, price, description)
QUIET = (
    ("Fixturon WM1045 10kg 1400rpm Washing Machine White", "Fixturon", "279.00 GBP",
     "A 10kg drum with 15 programmes and a 1400rpm spin."),
    ("Testline Series 6 9kg Quiet Mark Approved Washing Machine", "Testline", "549.00 GBP", ""),
    ("Fixturon EcoWash 9kg Washing Machine Graphite", "Fixturon", "429.99 GBP",
     "Inverter motor with low noise: 49 dB when washing, so it can run at night."),
    ("Testline SilentDrive 8kg Washing Machine Low Noise 47dB", "Testline", "499.00 GBP", ""),
    ("Fixturon Compact 6kg Washing Machine", "Fixturon", "239.00 GBP", "A 6kg drum, 1200rpm."),
    ("Testline Steam Care 10kg Washing Machine", "Testline", "619.00 GBP", "Steam programmes for shirts."),
)
SMALL_KITCHEN = (
    ("Fixturon WM1045 10kg 1400rpm Washing Machine White", "Fixturon", "279.00 GBP", ""),
    ("Fixturon Compact 6kg Washing Machine", "Fixturon", "239.00 GBP", "A 6kg drum, 1200rpm."),
    ("Testline Compact Slim 7kg Washing Machine", "Testline", "329.00 GBP", "Steam programmes."),
    ("Testline Steam Care 10kg Washing Machine", "Testline", "619.00 GBP", ""),
)


def _run(search: str, words: tuple[str, ...], products: tuple, client) -> bool:
    from picwise_ai.checks import check_answer
    from picwise_ai.client import ask
    from picwise_ai.complex_search import Candidate, ComplexSearch
    from picwise_ai.request import request_kwargs

    complex_search = ComplexSearch(
        search=search,
        words=words,
        kind_name="washing machine",
        fell_back=False,
        candidates=tuple(
            Candidate(number, f"preflight-{number}", title, brand, price, "GBP", "Fictional Appliances", description)
            for number, (title, brand, price, description) in enumerate(products, start=1)
        ),
        total=len(products),
        kind_id="washing_machine",
    )
    asked = ask(request_kwargs(complex_search), client=client)
    print()
    print(f"== {search}")
    print(f"answered by: {asked.model or 'none'}; stop reason: {asked.stop_reason or 'none'}; error: {asked.error or 'none'}")
    print(f"tokens: {asked.input_tokens} in, {asked.output_tokens} out, cache written {asked.cache_write_tokens},"
          f" cache read {asked.cache_read_tokens}; cost ${asked.cost_usd:.6f}; {asked.seconds:.1f} s")
    answer = asked.answer or {}
    fits = {verdict.get("n"): verdict.get("fits") for verdict in answer.get("verdicts") or () if isinstance(verdict, dict)}
    for number, (title, _brand, price, description) in enumerate(products, start=1):
        print(f"  {fits.get(number, '(none)'):8} {number}. {title} | {price}" + (f" | {description}" if description else ""))
    print(f"sentence written: {answer.get('sentence') or '(none)'}")
    print(f"shops' words written: {', '.join(answer.get('shop_words') or ()) or '(none)'}")
    checked = check_answer(asked.answer, complex_search, stop_reason=asked.stop_reason)
    if checked.shown:
        print("the checks: PASS, the sentence would be shown")
    elif checked.failure:
        print(f"the checks: withheld: {checked.failure}")
    else:
        print("the checks: no sentence; the shops' words that pass: " + (", ".join(checked.shop_words) or "none"))
    return asked.answer is not None


def main() -> int:
    from picwise_ai.client import make_client
    from picwise_ai.request import EFFORT, MODEL

    client = make_client(timeout=30.0)
    print(f"model asked: {MODEL}, effort {EFFORT}")
    first = _run("quiet washing machine", ("quiet",), QUIET, client)
    second = _run("washing machine for a small kitchen", ("small", "kitchen"), SMALL_KITCHEN, client)
    return 0 if first and second else 1


if __name__ == "__main__":
    raise SystemExit(main())
