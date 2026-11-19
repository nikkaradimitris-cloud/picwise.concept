"""The sets of listings the AI is asked about, written after the catalogue is prepared
(`picwise_providers.variant_families`; owner, 2026-11-19).

    family_jobs.py --catalogue /srv/picwise/shared/prepared/catalogue.json.gz \
        --jobs /srv/picwise/assist/families/jobs \
        --answers /srv/picwise/assist/families/answers/sets.json

Run by `picwise-family-jobs.service` as the site's user, after each preparation and at
each deployment. It reads the prepared catalogue, finds the products of one shop and brand
whose titles differ by a colour or a number, and writes the sets the AI has not answered
yet as jobs for `picwise-families`. Printed: counts only. Exits 0, or 1 when the
catalogue cannot be read.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for folder in (ROOT, ROOT / "src"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write the sets of listings the AI is asked about.")
    parser.add_argument("--catalogue", required=True, type=Path)
    parser.add_argument("--jobs", required=True, type=Path)
    parser.add_argument("--answers", required=True, type=Path, help="the sets answered (sets.json)")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    from picwise_providers.prepared_catalogue import read_prepared_catalogue_to_measure
    from picwise_providers.variant_families import answered_set_ids, doubtful_sets, write_jobs

    prepared = read_prepared_catalogue_to_measure(args.catalogue)
    if prepared is None:
        print("family_jobs: the prepared catalogue cannot be read")
        return 1
    sets = doubtful_sets(prepared.products)
    answered = answered_set_ids(args.answers)
    written = write_jobs(sets, args.jobs, answered=answered)
    waiting = sum(1 for found in sets if found["id"] not in answered)
    print(
        f"family_jobs: {len(prepared.products):,} products; {len(sets):,} sets a colour or a number tells "
        f"apart, {len(sets) - waiting:,} answered before; {waiting:,} asked now, in {written:,} jobs"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
