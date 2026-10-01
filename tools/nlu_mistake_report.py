"""Review what the NLU could not understand in real buyer queries.

This is the NLU's training loop. PicWise's understanding comes from a lexicon of product
names (`src/picwise_nlu/product_concepts.py`) read by sound and by edit distance, so it
is taught by adding the names buyers actually use, not by retraining a model:

1. collect real queries: the `query` of `query_served` tracking events, a Search
   Console export, or any list of searches, one per line
2. run this report over them
3. for each query in "not understood", decide whether it names a product. If it does,
   add the missing name to the concept's English or Greek names; if it names a product
   PicWise has no concept for, add the concept
4. check every "corrected" reading: a wrong correction is a false friend to add to
   `_COMMON_WORDS` in `picwise_nlu/concept_understanding.py`
5. rerun `python tools/nlu_misspelling_benchmark.py` and confirm wrong answers stay at 0

    python tools/nlu_mistake_report.py queries.txt
    python tools/nlu_mistake_report.py queries.txt --csv review.csv
    python tools/nlu_mistake_report.py --from-query-log     # the site's stored queries

`--from-query-log` reads the table `src/picwise_app/query_log_sink.py` writes to, using
the same PICWISE_QUERY_LOG_SUPABASE_URL / _KEY environment variables.

Only correctly spelled names belong in the lexicon. Misspellings are handled by the
matcher; adding them as names would teach it one mistake at a time.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_nlu.concept_understanding import understand_product_query  # noqa: E402


def classify(query: str) -> tuple[str, str]:
    reading = understand_product_query(query)
    if reading.non_retail:
        return "non_retail", ""
    if not reading.understood:
        return "not_understood", ""
    return ("exact" if reading.exact else "corrected"), str(reading.concept_id)


def _query_log_lines(limit: int) -> list[str]:
    from urllib.request import Request, urlopen

    base = str(os.environ.get("PICWISE_QUERY_LOG_SUPABASE_URL") or "").strip().rstrip("/")
    key = str(os.environ.get("PICWISE_QUERY_LOG_SUPABASE_KEY") or "").strip()
    table = str(os.environ.get("PICWISE_QUERY_LOG_TABLE") or "").strip() or "picwise_query_log"
    if not base or not key:
        sys.exit("Set PICWISE_QUERY_LOG_SUPABASE_URL and PICWISE_QUERY_LOG_SUPABASE_KEY.")
    request = Request(
        f"{base}/rest/v1/{table}?select=query&order=created_at.desc&limit={int(limit)}",
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
    )
    with urlopen(request, timeout=30) as response:
        rows = json.loads(response.read() or b"[]")
    return [str(row.get("query") or "") for row in rows]


def main() -> None:
    parser = argparse.ArgumentParser(description="PicWise NLU mistake report")
    parser.add_argument("queries", nargs="?", default="", help="Text file, one query per line")
    parser.add_argument("--from-query-log", action="store_true", help="Read the site's stored queries")
    parser.add_argument("--log-limit", type=int, default=50000)
    parser.add_argument("--csv", default="", help="Write every row to this CSV for review")
    parser.add_argument("--limit", type=int, default=40)
    args = parser.parse_args()

    if args.from_query_log:
        lines = _query_log_lines(args.log_limit)
    elif args.queries:
        lines = Path(args.queries).read_text(encoding="utf-8").splitlines()
    else:
        sys.exit("Give a queries file or --from-query-log.")
    counts = Counter(" ".join(line.split()).lower() for line in lines if line.strip())
    rows = []
    for query, frequency in counts.most_common():
        outcome, concept = classify(query)
        rows.append({"query": query, "frequency": frequency, "outcome": outcome, "concept": concept})

    total = sum(row["frequency"] for row in rows) or 1
    by_outcome = Counter()
    for row in rows:
        by_outcome[row["outcome"]] += row["frequency"]
    print(f"{total} searches, {len(rows)} distinct")
    for outcome in ("exact", "corrected", "not_understood", "non_retail"):
        print(f"  {outcome:15s} {by_outcome[outcome]:6d}  {by_outcome[outcome] / total * 100:5.1f}%")

    for outcome, title in (
        ("not_understood", "Not understood -- add the product name if it is one"),
        ("corrected", "Understood through a correction -- check each is right"),
    ):
        picked = [row for row in rows if row["outcome"] == outcome][: args.limit]
        if picked:
            print(f"\n{title}")
            for row in picked:
                print(f"  {row['frequency']:5d}  {row['query']!r:45s} {row['concept']}")

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["query", "frequency", "outcome", "concept"])
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nWrote {args.csv}")


if __name__ == "__main__":
    main()
