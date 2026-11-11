"""Time searches against a prepared catalogue with the code of one checkout, and write
what each search answered, so two checkouts can be compared answer for answer.

    python tools/bench_search.py <repo checkout> <prepared catalogue> <answers.json> [rounds]
    python tools/bench_search.py --compare <answers.json> <answers.json>

It times the search (`resolve_live_search`) and the whole page a visitor gets, the best
of the rounds each. `--compare` says which answers and pages differ between two files
and exits 1 when any does (the times are not compared).

Run it on a machine doing nothing else. A measure taken beside other work (a test run,
another measure) once showed 2.9 s for a search that takes 0.1 s.

The prepared file is read whatever code wrote it (its fingerprint is taken as this
checkout's): a speed measure, never the site (`docs/PICWISE_AUDIT_FIXES.md`, section 7).
"""
import gzip
import hashlib
import json
import os
import statistics
import sys
import time
from pathlib import Path

if len(sys.argv) > 1 and sys.argv[1] == "--compare":
    one, other = (json.loads(Path(name).read_text(encoding="utf-8"))["answers"] for name in sys.argv[2:4])
    differing = sorted(key for key in set(one) | set(other) if one.get(key) != other.get(key))
    for key in differing:
        print(f"differs: {key}")
    print(f"{len(set(one) | set(other))} answers and pages compared, {len(differing)} differ")
    raise SystemExit(1 if differing else 0)

REPO = Path(sys.argv[1]).resolve()
PREPARED = Path(sys.argv[2]).resolve()
OUT = Path(sys.argv[3])
ROUNDS = int(sys.argv[4]) if len(sys.argv) > 4 else 3

os.environ["PICWISE_PREPARED_CATALOGUE_FILE"] = str(PREPARED)
os.environ.pop("AWIN_FEED_FILE", None)
os.environ.pop("AWIN_FEED_URL", None)
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))

from picwise_providers import prepared_catalogue  # noqa: E402

file_code = json.loads(gzip.decompress(PREPARED.read_bytes()).decode("utf-8"))["code"]
prepared_catalogue.code_fingerprint = lambda **_kwargs: file_code

import api.index as site  # noqa: E402
from picwise_search import resolve_live_search  # noqa: E402

QUERIES = [
    "washing machine", "kettle", "laptop", "ring", "power bank 20000mah", "3 seater sofa grey",
    "tv", "smart tv 55 inch", "running shoes", "office chair", "coffee machine", "giftware",
    "blue ornament", "keepsake piece", "bth rugs", "laptop bag", "quiet washing machine",
    "fixturon washing machine", "trainers size 9", "dishwasher", "necklace silver", "t shirt",
    "tablet", "vitamin tablets", "tv stand", "phone case", "smartphone", "mobile phone",
    "used laptop", "refurbished phone", "novelty", "bundle 42", "xyzzy", "",
]


def answer(resolution) -> dict:
    def ids(name):
        return [str(product.get("provider_product_id")) for product in (getattr(resolution, name, ()) or ())]

    return {
        "state": str(getattr(resolution, "resolver_state", "")),
        "concept": str(getattr(resolution, "understood_concept_id", "") or ""),
        "total": int(getattr(resolution, "provider_feed_total_count", 0) or 0),
        "selected": ids("provider_feed_selected_products"),
        "more": ids("provider_feed_more_products"),
        "recommended": str(getattr(resolution, "provider_feed_recommended_product_id", "") or ""),
        "unmatched": list(getattr(resolution, "provider_feed_unmatched_query_terms", ()) or ()),
        "did_you_mean": [str(name) for name in (getattr(resolution, "did_you_mean", ()) or ())],
        "reasons": list(getattr(resolution, "reason_codes", ()) or ()),
    }


started = time.perf_counter()
first = resolve_live_search("washing machine")
load_seconds = time.perf_counter() - started
print(f"first search, catalogue loaded with it: {load_seconds:.2f} s; total {getattr(first, 'provider_feed_total_count', 0)}")

answers = {}
timings = {}
page_timings = {}
for query in QUERIES:
    samples = []
    for shown in (0,):
        for _round in range(ROUNDS):
            began = time.perf_counter()
            resolution = resolve_live_search(query, shown=shown) if query else None
            samples.append(time.perf_counter() - began)
    if query:
        answers[query] = answer(resolution)
        answers[query + " |shown=12"] = answer(resolve_live_search(query, shown=12))
        page_samples = []
        for _round in range(ROUNDS):
            began = time.perf_counter()
            html = site._APP.picwise_reference_html(query)
            page_samples.append(time.perf_counter() - began)
        page_timings[query] = min(page_samples)
        answers[query + " |page"] = hashlib.sha256(html.encode("utf-8")).hexdigest()[:16]
    timings[query] = min(samples)

for query, seconds in sorted(timings.items(), key=lambda item: -item[1]):
    row = answers.get(query, {})
    print(f"{seconds * 1000:9.1f} ms  {query!r:34} total={row.get('total', '')} state={row.get('state', '')}")
values = [seconds for query, seconds in timings.items() if query]
print(f"median {statistics.median(values) * 1000:.1f} ms, mean {statistics.mean(values) * 1000:.1f} ms, max {max(values) * 1000:.1f} ms over {len(values)} searches")
pages = list(page_timings.values())
print(f"the page: median {statistics.median(pages) * 1000:.1f} ms, max {max(pages) * 1000:.1f} ms over {len(pages)} pages")
OUT.write_text(json.dumps({"timings": timings, "page_timings": page_timings, "answers": answers}, indent=1, sort_keys=True))
