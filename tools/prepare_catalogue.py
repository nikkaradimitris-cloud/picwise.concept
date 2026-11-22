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
pool Google may be given from holds (`google_pool`), which shops' feeds shrank or
vanished since the build before (`intake_change`), and what the answers to the question
"is it the kind itself" did (`itself`, `picwise_providers.kind_itself`), never the feed's
link nor a row's id.
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
        from picwise_providers.awin_adapter import awin_feed_config_from_env
        from picwise_providers.prepared_catalogue import write_prepared_catalogue
        from picwise_providers.state import prepare_feed_catalogue

        # The feed's copy is chosen once, here, and the intake below reads the same (owner,
        # 2026-11-20: «Η επεξεργασία να διαβάζει το feed μία φορά, ακόμα κι αν λήξει στη
        # μέση»). Asked for again past its six hours (`awin_adapter.materialize_feed_url`), a
        # link was downloaded and parsed a second time beside the first, and the run passed its
        # memory ceiling (20/11, 10:30 UTC).
        feed_config = awin_feed_config_from_env()
        capping = _Cap(args.out)
        prepared = prepare_feed_catalogue(feed_config, cap=capping)
        _trace("the catalogue prepared")
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
    checks = _checks(capping)
    itself = _itself(capping)
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
    _trace("the file written")
    intake = _intake(feed_config) if args.static_dir is not None else None
    _trace("the intake measured")
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
                # The shops' sale prices (owner, 2026-11-19).
                + f"; {memory['on_sale_tonight']:,} at the shop's sale price"
                + f" (of {memory['sale_prices']['given']:,} giving one)"
                + (
                    f", {memory['history_restarted_tonight']:,} of them starting their price's history again"
                    if memory["history_restarted_tonight"]
                    else ""
                )
            )
    notes = _price_notes(args.memory, args.out, prepared, memory)
    if notes is not None:
        if "error" in notes:
            print(f"prepare_catalogue: the price notes were not written ({notes['error']}); the cards show none")
        else:
            print(
                f"prepare_catalogue: the price notes: {notes['notes']:,} products, {notes['down']:,} down, "
                f"{notes['up']:,} up, {notes['same']:,} at the same price, {notes['watch']:,} moved with no arrow yet"
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
                "checks": checks,
                "itself": itself,
                **({"memory": memory} if memory is not None else {}),
                **({"price_notes": notes} if notes is not None else {}),
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
        # What the checks' bot asks next (the checks' rules 9.4, 8.1): rows, never products.
        self.candidates: dict[str, object] | None = None
        # What the AI is asked next (the checks' rules 5.5): the products kept or next with no category yet.
        self.shelf: list[dict[str, object]] = []
        # Why the checks' gate did not stand tonight, when it did not.
        self.gate_off = ""
        # What the AI is asked next of the question "is it the kind itself" (its rules 8.2):
        # the questions that wait, of the products kept or next, and each kind's first cards;
        # and what tonight's catalogue shows, for the next night's brakes (its rules 7).
        self.itself: list[dict[str, object]] | None = None
        self.itself_shown: dict[str, str] | None = None
        self.itself_error = ""
        self.itself_gate = False
        try:
            from picwise_providers import kind_itself

            kind_itself.remember_at(kind_itself.shown_path(out))
        except Exception as error:  # the brakes then have no night before to hold against
            self.itself_error = _where(error)

    def __call__(self, products, kinds, feed_ctx):
        try:
            from picwise_providers import checks_applied, kind_itself
            from picwise_providers.catalogue_balance import cap_limits
            from picwise_providers.catalogue_cap import cap_catalogue, google_pool_path, read_google_pool, row_key

            share, category_max = cap_limits()
            kept_before = read_google_pool(google_pool_path(self.out))
            gate = checks_applied.may_enter if checks_applied.gate_on() else None
            if gate is not None and not kept_before:
                # No memory of the night before (the pool missing or unreadable): the gate would
                # take every product for a new one and hold the whole site back. Tonight it holds
                # only the products the checks name as not shown until checked.
                gate = checks_applied.may_enter_without_memory
                self.gate_off = "the night before's pool could not be read: only the products not checked are held back"
            elif gate is not None and kind_itself.gate_on():
                # A new product also waits for its answers to the question "is it the kind
                # itself" (its rules, section 6), asked only of the few whose checks passed.
                self.itself_gate = True

                def gate(product, _checks=checks_applied.may_enter, _itself=kind_itself.may_enter):
                    return _checks(product) and _itself(product)

            if gate is not None:
                # Back within 7 nights of its cut: as kept the night before (the checks' rules 8.2);
                # not shown until checked: out of the night before's, to wait at the gate (9.3, 9.5).
                kept_before = (frozenset(kept_before) | checks_applied.returning_row_keys(products, row_key)) \
                    - checks_applied.unchecked_row_keys(products, row_key)
            self.result = cap_catalogue(
                products, kinds, feed_ctx=feed_ctx, kept_before=kept_before,
                share=share, category_max=category_max, may_enter=gate,
            )
            if gate is not None:
                from picwise_checks.rows import row_of, row_record

                next_ones = [products[index] for index in self.result.candidates]
                self.candidates = checks_applied.candidates_document(
                    next_ones, checks_applied.take_cut_products(), row_record, row_of,
                )
                self.shelf = checks_applied.shelf_items(
                    [product for product, kept in zip(products, self.result.keep) if kept] + next_ones
                )
        except Exception as error:
            self.result, self.error = None, _where(error)
            return None
        self._itself_job(products, kinds)
        return self.result.keep

    def _itself_job(self, products, kinds) -> None:
        """The questions "is it the kind itself" the AI is asked next, when the night read
        its answers; a failure here is only noted, and nothing is asked that morning."""
        try:
            from picwise_providers import kind_itself
            from picwise_providers.search_selection import _product_search_fields, kinds_read

            night = kind_itself.tonight()
            if night is None or self.result is None:
                return
            kept_places = [place for place, kept in enumerate(self.result.keep) if kept]
            self.itself_shown = kind_itself.shown_rows(night, products, kinds, kept_places)
            self.itself = kind_itself.job_items(
                night, products, kept_places + list(self.result.candidates),
                lambda place: kinds_read(products[place], _product_search_fields(products[place])),
                kept=[products[place] for place in kept_places], kept_kinds=[kinds[place] for place in kept_places],
            )
        except Exception as error:
            self.itself, self.itself_error = None, _where(error)

    def write_itself_shown(self) -> dict[str, object] | None:
        """What tonight's catalogue shows, kept beside it for the next night's brakes, once
        the catalogue itself is written. A night that read no answer keeps nothing: the
        first night that reads them again has no night before to hold against."""
        try:
            from picwise_providers import kind_itself

            path = kind_itself.shown_path(self.out)
            night = kind_itself.tonight()
            if night is None or self.itself_shown is None:
                path.unlink(missing_ok=True)
                return None
            written = kind_itself.write_shown(
                path, self.itself_shown, held=night.held_since, night_held=night.night_held_since, night=night.today)
            return {"rows": written}
        except Exception as error:
            return {"error": _where(error)}

    def write_itself_job(self) -> dict[str, object] | None:
        """The questions written for picwise-itself; what was written, or why not."""
        if self.itself_error:
            return {"error": self.itself_error}
        if self.itself is None:
            return None
        try:
            from picwise_providers.kind_itself import write_job

            return write_job(self.itself)
        except Exception as error:
            return {"error": _where(error)}

    def write_candidates(self) -> dict[str, object] | None:
        """The rows the checks' bot asks next, beside the decisions it wrote; what was written."""
        if self.candidates is None:
            return None
        try:
            from picwise_checks.ledger import CANDIDATES_NAME, _write_gzip_json
            from picwise_providers.checks_applied import DECISIONS_ENV

            folder = Path(str(os.environ.get(DECISIONS_ENV) or "")).parent
            _write_gzip_json(self.candidates, folder / CANDIDATES_NAME)
        except Exception as error:
            return {"error": _where(error)}
        written: dict[str, object] = {"candidates": len(self.candidates["candidates"]), "rows": len(self.candidates["rows"])}
        try:
            from picwise_providers.checks_applied import write_shelf_job

            shelf = write_shelf_job(self.shelf)
            if shelf is not None:
                written["for_the_ai"] = shelf
        except Exception as error:
            written["for_the_ai"] = {"error": _where(error)}
        return written

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


def _checks(capping: _Cap) -> dict[str, object]:
    """What the checks' decisions did tonight (`picwise_providers.checks_applied`): counts
    and shop names only; printed and kept in the night's note."""
    from picwise_providers.checks_applied import last_checks_note

    note = last_checks_note() or {"applied": False, "why": "not read"}
    written = capping.write_candidates()
    result = capping.result
    if note.get("applied"):
        print(
            f"prepare_catalogue: the checks of {note.get('night')}: {len(note.get('shops_out') or {})} shops out "
            f"({note.get('products_of_shops_out', 0):,} products), {note.get('cut', 0):,} products cut, "
            f"{note.get('not_shown_until_checked', 0):,} not shown until checked, "
            f"{note.get('price_from_site', 0):,} at the price of the shop's own page; held back by the cap's gate "
            f"{getattr(result, 'held_by_checks', 0):,}, candidates {len(getattr(result, 'candidates', ()) or ()):,}"
            + (f"; the bot's rows not written ({written['error']})" if written and "error" in written else "")
        )
        category = note.get("category") or {}
        print(
            f"prepare_catalogue: the category (5.5): {category.get('no_category', 0):,} products with none"
            + (" (HELD by its brake: none cut)" if category.get("held_by_its_brake") else " (cut)")
            + f", {category.get('not_asked_yet', 0):,} not asked yet"
            + (f"; for the AI next: {written['for_the_ai']}" if written and written.get("for_the_ai") else "")
            + ("" if category.get("answers") else "; no answers file: nothing decided")
        )
    else:
        print(f"prepare_catalogue: the checks not applied ({note.get('why')})")
    if capping.gate_off:
        print(f"prepare_catalogue: THE CHECKS' GATE DID NOT STAND tonight: {capping.gate_off}")
    return {**note, "held_by_the_gate": getattr(result, "held_by_checks", 0),
            "candidates": len(getattr(result, "candidates", ()) or ()), "written": written,
            **({"gate_off": capping.gate_off} if capping.gate_off else {})}


def _itself(capping: _Cap) -> dict[str, object]:
    """What the answers to the question "is it the kind itself" did tonight
    (`picwise_providers.kind_itself`): counts and kinds' names only; printed and kept in the
    night's note."""
    from picwise_providers.kind_itself import last_note

    note = last_note() or {"applied": False, "why": "not read"}
    written = capping.write_itself_job()
    kept = capping.write_itself_shown()
    if note.get("applied"):
        left = ", ".join(f"{name} {count:,}" for name, count in (note.get("left_by_answer") or {}).items())
        print(
            f"prepare_catalogue: the kind itself: {note.get('products_with_a_second_reading', 0):,} products read twice,"
            f" {note.get('left_a_kind', 0):,} left a kind ({left or 'none'}), {note.get('came_back', 0):,} came back;"
            f" {note.get('products_with_a_question_waiting', 0):,} with a question waiting,"
            f" {note.get('products_to_ask_again', 0):,} to ask again"
            + (f"; for the AI next: {written}" if written else "")
            + ("; a new product waits for its answers at the cap's gate" if capping.itself_gate else "")
        )
        held = note.get("held_by_a_kinds_brake") or []
        if note.get("brakes") != "stood":
            print(f"prepare_catalogue: the kind itself, its brakes: {note.get('brakes')}")
        if note.get("held_by_the_nights_brake"):
            print(
                f"prepare_catalogue: THE KIND ITSELF, THE NIGHT'S BRAKE HOLDS since {note['held_by_the_nights_brake']}:"
                f" {note.get('held_as_shown', 0):,} products stay as they were shown, until the owner's word"
            )
        elif held:
            print("prepare_catalogue: THE KIND ITSELF, A KIND'S BRAKE HOLDS: " + "; ".join(
                f"{entry['kind']} {entry['products']:,} (since {entry['since']})" for entry in held
            ))
        if kept and "error" in kept:
            print(f"prepare_catalogue: the kind itself, what tonight shows was not kept ({kept['error']}):"
                  " the next night's brakes have nothing to hold against")
    else:
        print(f"prepare_catalogue: the kind itself not read ({note.get('why')})")
    return {**note, **({"for_the_ai": written} if written else {}),
            **({"new_products_wait": True} if capping.itself_gate else {}),
            **({"shown_not_kept": kept["error"]} if kept and "error" in kept else {})}


def _freshness(prepared) -> dict[str, object]:
    """How fresh the prepared products' listings are; a failure here is only noted."""
    try:
        from picwise_providers.feed_freshness import measure_feed_freshness

        return measure_feed_freshness(prepared.products, today=prepared.prepared_at.date())
    except Exception as error:
        return {"error": _where(error)}



def _trace(stage: str) -> None:
    """With PICWISE_MEMORY_TRACE set, the peak memory so far at each step of the night, so
    that a trial shows where the memory goes (2026-11-19, the two Awin links)."""
    if not os.environ.get("PICWISE_MEMORY_TRACE"):
        return
    import resource

    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1048576
    print(f"prepare_catalogue: memory after {stage}: peak {peak:.1f} GB so far", flush=True)

def _intake(feed_config: object = None) -> dict[str, object] | None:
    """What each shop's feed brings in and why the rest is held, read from the copy of the
    feed the catalogue was read from (`feed_config`); a failure is only noted."""
    try:
        from picwise_providers.state import measure_configured_feed_intake

        return measure_configured_feed_intake(feed_config)
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


def _price_notes(path: Path | None, out: Path, prepared, memory: dict[str, object] | None) -> dict[str, object] | None:
    """Tonight's price notes, beside the prepared catalogue, from the memory just written
    (`picwise_providers.price_history`); none without a memory written tonight. A
    failure is only noted: the site shows a card's price note only beside the catalogue
    of the same preparation, so it then shows none."""
    if memory is None or "error" in memory:
        return None
    try:
        from picwise_providers.catalogue_memory import configured_memory_path
        from picwise_providers.price_history import PRICE_NOTES_NAME, write_price_notes

        path = path or configured_memory_path()
        if path is None:
            return None
        return write_price_notes(path, Path(out).parent / PRICE_NOTES_NAME, prepared_at=prepared.prepared_at)
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
