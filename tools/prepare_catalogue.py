"""Prepare the feed once, so a server answers from the prepared file (step 5).

    python tools/prepare_catalogue.py
    python tools/prepare_catalogue.py --feed-file datafeed.csv.gz --out prepared/catalogue.json.gz
    python tools/prepare_catalogue.py --keep-going --static-dir public

Reads the configured feed (`AWIN_FEED_URL` or `AWIN_FEED_FILE`), or the file given,
judges it as a search does and writes `prepared/catalogue.json.gz`
(`src/picwise_providers/prepared_catalogue.py`). It prints counts and sizes, never the
feed's link, which carries the account's API key.

`--keep-going` is for a deployment's build (`vercel.json`): when the feed cannot be read,
or preparing it fails, it says so and exits 0, writing nothing, and the server then
reads the feed itself, as before. A deployment never fails because of the feed. Of an
error it prints the kind and the line of code only: an error's own text can quote the
feed's link.

`--static-dir` is for the same build: Vercel serves that folder as the site's static
files and refuses to deploy it empty, so the tool writes `prepared.json` there, a public
note of what this build prepared: counts, the time, how fresh the feed's listings are
(`picwise_providers.feed_freshness`: listing age, stock quantities, per shop), and what
each shop's feed brings in (`picwise_providers.feed_intake`: rows, shown, shown only
when asked for, held back and why, and what its `product_type` column carries), and per
kind the products shown as it whose title does not name it (`picwise_providers.kind_check`),
never the feed's link.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (str(ROOT), str(SRC)):
    if path not in sys.path:
        sys.path.insert(0, path)

STATIC_NOTE_NAME = "prepared.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--feed-file", type=Path, help="read this feed file instead of the configured feed")
    parser.add_argument("--out", type=Path, default=ROOT / "prepared" / "catalogue.json.gz")
    parser.add_argument(
        "--keep-going", action="store_true", help="exit 0 when the feed cannot be read or preparing it fails"
    )
    parser.add_argument("--static-dir", type=Path, help=f"write {STATIC_NOTE_NAME}, what this build prepared, here")
    args = parser.parse_args(argv)
    if args.feed_file is not None:
        if not args.feed_file.is_file():
            parser.error(f"no feed file at {args.feed_file}")
        os.environ["AWIN_FEED_FILE"] = str(args.feed_file.resolve())
    logging.disable(logging.WARNING)

    started = time.perf_counter()
    try:
        from picwise_providers.prepared_catalogue import write_prepared_catalogue
        from picwise_providers.state import prepare_feed_catalogue

        prepared = prepare_feed_catalogue()
        size = write_prepared_catalogue(prepared, args.out) if prepared is not None else 0
    except Exception as error:
        if not args.keep_going:
            raise
        print(f"prepare_catalogue: preparing the feed failed ({_where(error)}); nothing written")
        _write_static_note(args.static_dir, {"prepared": False, "reason": "preparing_failed"})
        return 0
    if prepared is None:
        print("prepare_catalogue: the feed could not be read; nothing written")
        _write_static_note(args.static_dir, {"prepared": False, "reason": "feed_not_readable"})
        return 0 if args.keep_going else 1
    print(
        f"prepare_catalogue: {prepared.feed_status.product_count} rows, "
        f"{len(prepared.products)} products a card can show "
        f"({sum(1 for condition in prepared.non_new if not condition)} new), "
        f"{prepared.shop_count} shops, {len(prepared.suggestions)} suggestions; "
        f"{size / 1e6:.1f} MB written to {args.out} in {time.perf_counter() - started:.1f} s"
    )
    if args.static_dir is not None:
        _write_static_note(
            args.static_dir,
            {
                "prepared": True,
                "prepared_at": prepared.prepared_at.astimezone(timezone.utc).isoformat(timespec="seconds"),
                "products": len(prepared.products),
                "shops": prepared.shop_count,
                "freshness": _freshness(prepared),
                "intake": _intake(),
                "kinds": _kinds(prepared),
            },
        )
    return 0


def _freshness(prepared) -> dict[str, object]:
    """How fresh the prepared products' listings are; a failure here is only noted."""
    try:
        from picwise_providers.feed_freshness import measure_feed_freshness

        return measure_feed_freshness(prepared.products, today=prepared.prepared_at.date())
    except Exception as error:
        return {"error": _where(error)}


def _intake() -> dict[str, object] | None:
    """What each shop's feed brings in and why the rest is held; a failure is only noted."""
    try:
        from picwise_providers.state import measure_configured_feed_intake

        return measure_configured_feed_intake()
    except Exception as error:
        return {"error": _where(error)}


def _kinds(prepared) -> dict[str, object]:
    """Per kind, the products shown as it whose title does not name it; a failure is only
    noted."""
    try:
        from picwise_providers.kind_check import measure_kind_titles

        return measure_kind_titles(prepared.products, prepared.kinds)
    except Exception as error:
        return {"error": _where(error)}


def _where(error: BaseException) -> str:
    """The error's kind and the line it came from, without its text."""
    frames = traceback.extract_tb(error.__traceback__)
    if not frames:
        return type(error).__name__
    frame = frames[-1]
    try:
        place = Path(frame.filename).resolve().relative_to(ROOT)
    except ValueError:
        place = Path(frame.filename).name
    return f"{type(error).__name__} at {place}:{frame.lineno}"


def _write_static_note(folder: Path | None, note: dict[str, object]) -> None:
    if folder is None:
        return
    folder.mkdir(parents=True, exist_ok=True)
    note = {**note, "written_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    (folder / STATIC_NOTE_NAME).write_text(json.dumps(note, ensure_ascii=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
