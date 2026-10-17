"""Prepare the feed once, so a server answers from the prepared file (step 5).

    python tools/prepare_catalogue.py
    python tools/prepare_catalogue.py --feed-file datafeed.csv.gz --out prepared/catalogue.json.gz
    python tools/prepare_catalogue.py --keep-going

Reads the configured feed (`AWIN_FEED_URL` or `AWIN_FEED_FILE`), or the file given,
judges it as a search does and writes `prepared/catalogue.json.gz`
(`src/picwise_providers/prepared_catalogue.py`). It prints counts and sizes, never the
feed's link, which carries the account's API key.

`--keep-going` is for a deployment's build: when the feed cannot be read it says why and
exits 0, writing nothing, and the server then reads the feed itself, as before.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (str(ROOT), str(SRC)):
    if path not in sys.path:
        sys.path.insert(0, path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--feed-file", type=Path, help="read this feed file instead of the configured feed")
    parser.add_argument("--out", type=Path, default=ROOT / "prepared" / "catalogue.json.gz")
    parser.add_argument("--keep-going", action="store_true", help="exit 0 when the feed cannot be read")
    args = parser.parse_args(argv)
    if args.feed_file is not None:
        if not args.feed_file.is_file():
            parser.error(f"no feed file at {args.feed_file}")
        os.environ["AWIN_FEED_FILE"] = str(args.feed_file.resolve())
    logging.disable(logging.WARNING)

    from picwise_providers.prepared_catalogue import write_prepared_catalogue
    from picwise_providers.state import prepare_feed_catalogue

    started = time.perf_counter()
    prepared = prepare_feed_catalogue()
    if prepared is None:
        print("prepare_catalogue: the feed could not be read; nothing written")
        return 0 if args.keep_going else 1
    size = write_prepared_catalogue(prepared, args.out)
    print(
        f"prepare_catalogue: {prepared.feed_status.product_count} rows, "
        f"{len(prepared.products)} products a card can show "
        f"({sum(1 for condition in prepared.non_new if not condition)} new), "
        f"{prepared.shop_count} shops, {len(prepared.suggestions)} suggestions; "
        f"{size / 1e6:.1f} MB written to {args.out} in {time.perf_counter() - started:.1f} s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
