"""Prepare the feed once, so a server answers from the prepared file (step 5).

    python tools/prepare_catalogue.py
    python tools/prepare_catalogue.py --feed-file datafeed.csv.gz --out prepared/catalogue.json.gz
    python tools/prepare_catalogue.py --keep-going --static-dir public

Reads the configured feed (`AWIN_FEED_URL` or `AWIN_FEED_FILE`), or the file given,
judges it as a search does and writes `prepared/catalogue.json.gz`
(`src/picwise_providers/prepared_catalogue.py`): the products the cap of 15% a category
keeps (`picwise_providers.catalogue_cap`), the night before's its starting point; owner,
2026-11-08: «μπορούμε να κρατήσουμε αυτόν τον κανόνα και για το search έτσι ώστε να
επιτυγχάνουμε καλύτερες ταχύτητες». The same products, beside it, are the pool Google may
be given from (`google_pool.json.gz`). A cap that fails keeps every product a card can
show in the search and the night before's pool. It prints counts and sizes, never the
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
how often a title alone gives the kind its shelf gives (`title_alone`), what the shops'
own catalogues and the rows' barcodes gave (`shop_catalogues`,
`picwise_providers.shop_catalogue`), how the shown products spread and what a cap on a
share would cut (`balance`, `picwise_providers.catalogue_balance`), how many the
pool Google may be given from holds (`google_pool`), and which shops' feeds shrank or
vanished since the build before (`intake_change`), never the feed's link nor a row's
id.
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
# A shop whose feed comes with fewer than half the rows of the night before, having had
# at least this many, is named in the note and in the tool's output.
SHRUNK_SHARE = 0.5
SHRUNK_FROM_ROWS = 50


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--feed-file", type=Path, help="read this feed file instead of the configured feed")
    parser.add_argument("--out", type=Path, default=ROOT / "prepared" / "catalogue.json.gz")
    parser.add_argument(
        "--keep-going", action="store_true", help="exit 0 when the feed cannot be read or preparing it fails"
    )
    parser.add_argument("--static-dir", type=Path, help=f"write {STATIC_NOTE_NAME}, what this build prepared, here")
    parser.add_argument(
        "--memory", type=Path,
        help="keep the catalogue's memory in this SQLite file (picwise_providers.catalogue_memory)",
    )
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

        capping = _Cap(args.out)
        prepared = prepare_feed_catalogue(cap=capping)
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
    pool = capping.write_pool(prepared)
    print(
        f"prepare_catalogue: {prepared.feed_status.product_count} rows, "
        f"{len(prepared.products)} products in the search "
        f"({sum(1 for condition in prepared.non_new if not condition)} new), "
        f"{prepared.shop_count} shops, {len(prepared.suggestions)} suggestions, "
        f"{len(prepared.choices)} kinds asking which one is meant; "
        f"{size / 1e6:.1f} MB written to {args.out} in {time.perf_counter() - started:.1f} s"
    )
    if "error" in pool:
        print(
            f"prepare_catalogue: the pool Google may be given from failed ({pool['error']}); the night before's is"
            " kept, and the search holds every product a card can show"
        )
    else:
        print(
            f"prepare_catalogue: the cap: {pool['kept']:,} of {pool['products']:,} products a card can show kept"
            f" (at most {pool['size'] if pool['size'] is not None else 'all'} a category, {pool['share']:.0%}),"
            f" {pool['kept_from_before']:,} of them kept the night before; the search and the pool Google may be"
            " given from hold the same"
        )
    intake = _intake() if args.static_dir is not None else None
    memory = _memory(args.memory, prepared, intake)
    if memory is not None:
        if "error" in memory:
            print(f"prepare_catalogue: the catalogue's memory was not written ({memory['error']})")
        else:
            print(
                f"prepare_catalogue: the catalogue's memory: {memory['products_known']:,} products over "
                f"{memory['nights']} nights; tonight {memory['seen_tonight']:,} seen, {memory['new_tonight']:,} new, "
                f"{memory['price_changed_tonight']:,} with a new price"
                + (
                    f", {memory['gone_since']:,} of {memory['compared_with']} not seen"
                    if memory["compared_with"] is not None
                    else ""
                )
            )
    if args.static_dir is not None:
        change = _intake_change(_previous_note(args.static_dir), intake)
        if change.get("shrunk") or change.get("gone"):
            # Said where the server's journal and a deployment's run show it: nothing
            # else tells that a shop's feed came broken (the audit, 2026-11-10).
            print(
                "prepare_catalogue: fewer than half of the night before's rows from "
                + "; ".join(
                    f"{entry['shop']} ({entry['rows_before']:,} -> {entry['rows']:,})"
                    for entry in (change.get("gone") or []) + (change.get("shrunk") or [])
                )
            )
        _write_static_note(
            args.static_dir,
            {
                "prepared": True,
                "prepared_at": prepared.prepared_at.astimezone(timezone.utc).isoformat(timespec="seconds"),
                "products": len(prepared.products),
                "shops": prepared.shop_count,
                "freshness": _freshness(prepared),
                "intake": intake,
                "intake_change": change,
                "kinds": _kinds(prepared),
                "title_alone": _title_alone(prepared),
                "shop_catalogues": _shop_catalogues(),
                "balance": _balance(prepared),
                "google_pool": pool,
                **({"memory": memory} if memory is not None else {}),
            },
        )
    return 0


class _Cap:
    """The cap of 15% a category (`picwise_providers.catalogue_cap`), worked out once
    from every product a card can show with the night before's pool as its starting
    point, for the search (`state.prepare_feed_catalogue`) and the pool Google may be
    given from alike (owner, 2026-11-08). A failure keeps every product in the search
    and the night before's pool, and is only noted."""

    def __init__(self, out: Path) -> None:
        self.out = out
        self.result = None
        self.error = ""

    def __call__(self, products, kinds, feed_ctx):
        try:
            from picwise_providers.catalogue_cap import cap_catalogue, google_pool_path, read_google_pool

            self.result = cap_catalogue(
                products, kinds, feed_ctx=feed_ctx, kept_before=read_google_pool(google_pool_path(self.out))
            )
        except Exception as error:
            self.result, self.error = None, _where(error)
            return None
        return self.result.keep

    def write_pool(self, prepared) -> dict[str, object]:
        """Keep the pool beside the prepared file for the next night; what it holds."""
        if self.result is None:
            return {"error": self.error or "the cap was not worked out"}
        try:
            from picwise_providers.catalogue_cap import google_pool_path, write_google_pool

            write_google_pool(self.result, google_pool_path(self.out), prepared_at=prepared.prepared_at)
        except Exception as error:
            return {"error": _where(error)}
        result = self.result
        return {
            "share": result.share,
            "size": result.size,
            "products": len(result.keep),
            "kept": result.kept,
            "kept_from_before": result.kept_from_before,
            "over": sorted(result.inside),
        }


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


def _previous_note(folder: Path | None) -> dict[str, object] | None:
    """The public note of the preparation before this one, still in its place; None when
    there is none or it cannot be read."""
    if folder is None:
        return None
    try:
        note = json.loads((folder / STATIC_NOTE_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return note if isinstance(note, dict) else None


def _shop_rows(note: object) -> dict[str, int] | None:
    """Per shop, the rows its feed brought, as a note's `intake` gives them."""
    shops = note.get("shops") if isinstance(note, dict) else None
    if not isinstance(shops, list):
        return None
    rows: dict[str, int] = {}
    for shop in shops:
        if isinstance(shop, dict) and isinstance(shop.get("rows"), int):
            rows[str(shop.get("shop") or "")] = shop["rows"]
    return rows


def _intake_change(previous: dict[str, object] | None, intake: object) -> dict[str, object]:
    """What changed in each shop's feed since the preparation before: the shops that
    brought fewer than half its rows (`shrunk`), none at all (`gone`), and the shops it
    did not have (`new`); names and counts only. Measured, and said: the catalogue is
    still built from tonight's feed alone, so a shop whose feed came broken is short
    tonight (the audit, 2026-11-10: one shop held 61% of the site's products, and nothing
    told when a shop's feed shrank). Keeping the night before's rows for such a shop
    needs the catalogue to remember them (`docs/PICWISE_GOOGLE_PAGES_SPEC.md`, section 7)."""
    before = _shop_rows(previous.get("intake")) if previous and previous.get("prepared") else None
    now = _shop_rows(intake)
    if before is None or now is None:
        return {"compared_with": None}

    def listed(names: list[str]) -> list[dict[str, object]]:
        return [
            {"shop": name, "rows_before": before[name], "rows": now.get(name, 0)}
            for name in sorted(names, key=lambda name: (-before[name], name))
        ]

    large = [name for name, rows in before.items() if rows >= SHRUNK_FROM_ROWS]
    return {
        "compared_with": previous.get("prepared_at"),
        "shrunk": listed([name for name in large if 0 < now.get(name, 0) < before[name] * SHRUNK_SHARE]),
        "gone": listed([name for name in large if now.get(name, 0) == 0]),
        "new": sorted(name for name in now if name not in before),
    }


def _kinds(prepared) -> dict[str, object]:
    """Per kind, the products shown as it whose title does not name it; a failure is only
    noted."""
    try:
        from picwise_providers.kind_check import measure_kind_titles

        return measure_kind_titles(prepared.products, prepared.kinds, prepared.search_fields or None)
    except Exception as error:
        return {"error": _where(error)}


def _title_alone(prepared) -> dict[str, object]:
    """How often a shown product's title alone gives the kind its shelf gives; a failure
    is only noted."""
    try:
        from picwise_providers.kind_check import measure_title_alone

        return measure_title_alone(prepared.products, prepared.search_fields or None)
    except Exception as error:
        return {"error": _where(error)}


def _shop_catalogues() -> dict[str, object] | None:
    """What the shops' own catalogues and the rows' barcodes gave the feed's rows
    (`picwise_providers.shop_catalogue`); a failure here is only noted."""
    try:
        from picwise_providers.shop_catalogue import last_shop_catalogue_note

        return last_shop_catalogue_note()
    except Exception as error:
        return {"error": _where(error)}


def _memory(path: Path | None, prepared, intake: object) -> dict[str, object] | None:
    """The night written into the catalogue's memory, when one is named (`--memory`, else
    `PICWISE_CATALOGUE_MEMORY_FILE`); what it now says, or the error, which never fails
    the preparation (picwise_providers.catalogue_memory)."""
    try:
        from picwise_providers.catalogue_memory import configured_memory_path, remember_night

        path = path or configured_memory_path()
        if path is None:
            return None
        return remember_night(
            path, prepared.products, prepared_at=prepared.prepared_at,
            intake=intake if isinstance(intake, dict) else None,
        )
    except Exception as error:
        return {"error": _where(error)}


def _balance(prepared) -> dict[str, object]:
    """How the shown products spread over departments, aisles, shops and kinds, and what
    a cap would cut (`picwise_providers.catalogue_balance`); measured only, and a
    failure here is only noted."""
    try:
        from picwise_providers.catalogue_balance import measure_catalogue_balance

        return measure_catalogue_balance(prepared.products, prepared.kinds)
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
