"""The server's health, read on the server and printed for the daily work (owner,
2026-11-16, choosing among the proposals for the daily work: «Έλεγχος προσφορών,
ταχύτητας και πόρων: κάθε μέρα, αν οι προσφορές ανανεώνονται, αν το site απαντά γρήγορα,
αν η μνήμη και ο δίσκος του διακομιστή φτάνουν. Ειδοποίηση μόνο αν ξεπεράσουν το όριο»).

`.github/workflows/server-health.yml` sends this file to the server every morning and runs
it there with sudo (`python3 - < print_health.py`), so this commit's code runs, not the
release's. It only reads: the site's service, the night's preparation (its public note and
its journal's line of peak memory and length), the offers' and the photos' files and their
services, the AI layer's spend, the server's memory and disk. The workflow's log is public,
like the repository: it prints counts, times and shops' names, which the site shows
anyway; never a secret, a link or a visitor's search.

The last lines say which limit was passed, each "over the limit: ...", or "within every
limit". The daily report tells only those (docs/PICWISE_DAILY_WORK.md):
- the site's service is not active;
- the night's preparation failed, or the catalogue the site answers from was prepared more
  than `MAX_AGE_HOURS` ago (the site stops showing products at 30 hours), or a shop was
  lost or shrank to less than half;
- the offers were fetched more than `MAX_AGE_HOURS` ago, or their last fetch failed;
- the photos were checked more than `MAX_AGE_HOURS` ago, or their last check failed;
- the site's memory and the preparation's peak together over `MAX_NIGHT_MEMORY_GB` (both
  run at night), or less than `MIN_AVAILABLE_GB` of memory available now;
- the preparation took more than `MAX_PREPARE_MINUTES`;
- less than `MIN_FREE_DISK_GB` of disk free;
- yesterday's AI spend at the day's cap (the service then asks nothing more that day);
- the shops' checks (`docs/PICWISE_CHECKS_RULES.md`, 7 and 11), once they run: their last
  round failed; no night recorded for more than a day; a round most shops did not answer;
  a brake that held the cuts (a shop's, the whole night's, the cutting stopped); a reading
  of Awin that waits for the owner's word. The shops that cannot be checked are printed
  with their day (on day 4 a shop leaves): for the report, not a limit.

The standard library only: the server's own python3 runs it, outside the site's packages.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

SHARED = Path("/srv/picwise/shared")
PREPARED_NOTE = SHARED / "public" / "prepared.json"
OFFERS_FILE = SHARED / "offers" / "offers.json"
PHOTOS_FILE = SHARED / "photos" / "gone.json"
SPEND_DIR = Path("/srv/picwise/assist/spend")
CHECKS_NOTE = SHARED / "checks" / "note.json"
# The AI's category of the products not asked yet (the checks' rules 5.5, 7.6), its morning's note.
SHELVES_NOTE = Path("/srv/picwise/assist/shelves/night.json")
# The question "is it the kind itself" (docs/PICWISE_KIND_ITSELF_RULES.md), its morning's note.
ITSELF_NOTE = Path("/srv/picwise/assist/itself/night.json")
# The quality meter (the same rules, section 9): its day's note.
METER_NOTE = Path("/srv/picwise/assist/meter/day.json")
# The wrong cards of the 40 searches printed, at most.
METER_WRONG_PRINTED = 15
# The checks' rules, 5.6.2 (owner, 22/11: «Σε 3 μέρες»): a shop that cannot be checked leaves on its day 4.
CHECKS_OUT_ON_DAY = 4
SITE_USER = "picwise"

MAX_AGE_HOURS = 30.0
# 24 GB on the server (OVHcloud VPS-4); the rest for the system and the other services.
# 19 since 2026-11-19 (owner: «Ανέβασε το όριο του server από τα 18 στα 19»), then 20 the same
# evening (owner: «Όχι δεν θα μειώσεις τα 12 και θα τα κάνεις 11 θα προσθέσεις το ένα gigabyte
# και θα τα κάνεις 20»).
MAX_NIGHT_MEMORY_GB = 20.0
MIN_AVAILABLE_GB = 4.0
MAX_PREPARE_MINUTES = 30.0
MIN_FREE_DISK_GB = 20.0
# The AI layer's cap, `picwise_ai.service.DAILY_CAP_USD`.
AI_DAILY_CAP_USD = 1.00

_PREPARE_LINE = re.compile(r"^prepare_catalogue: peak memory (\d+) KB, ([\d.]+) s$")
_GB = 1024 * 1024 * 1024

# Runs a command and returns its output ("" when it fails).
Run = Callable[[list[str]], str]


def run(command: list[str]) -> str:
    try:
        done = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def hours_since(stamp: object, now: datetime) -> float | None:
    try:
        then = datetime.fromisoformat(str(stamp))
    except ValueError:
        return None
    if then.tzinfo is None:
        then = then.replace(tzinfo=timezone.utc)
    return (now - then).total_seconds() / 3600


def _age(hours: float | None) -> str:
    if hours is None:
        return "at an unreadable time"
    return f"{hours:.1f} h ago" if hours < 48 else f"{hours / 24:.1f} days ago"


def _shop(entry: object) -> str:
    """A shop of the preparation's `intake_change`: its name, and its rows when it shrank."""
    if isinstance(entry, dict):
        return f"{entry.get('shop')}: {entry.get('rows_before')} -> {entry.get('rows')} rows"
    return str(entry)


class Health:
    def __init__(self, now: datetime) -> None:
        self.now = now
        self.lines: list[str] = []
        self.over: list[str] = []

    def say(self, line: str) -> None:
        self.lines.append(line)

    def limit(self, passed: bool, what: str) -> None:
        if passed:
            self.over.append(what)


# When the checks' night of the day is due (UTC): recorded at 03:05, with a margin.
CHECKS_DUE = (3, 30)


# The checks' bots (their rules 22 and 23; owner, 2026-11-25: «μην αγνοείς τους 4 κλώνους»;
# 2026-11-26: «8 bot αντί για 4», «Όριο μνήμης: 1,8 GB για κάθε bot»): how many, the switch in the
# release the site runs, each bot's limit of memory and the slice's for all of them together.
CHECKS_CLONES = 8
CLONES_SWITCH = Path("/srv/picwise/current/data/checks_clones.json")
BOT_MEMORY_MAX_GB = 1843 / 1024
BOTS_MEMORY_MAX_GB = 11.0
# A bot, or the bots together, this near their limit pass a limit of the report (the stable day,
# the checks' rules 23.6).
NEAR_THE_LIMIT = 0.9


def checks_bots(path: Path | None = None) -> tuple[int, list[int]]:
    """How many bots the shops are split into, and those switched on (data/checks_clones.json; the
    checks' rules 23), as the bots read it; (8, []) when it cannot be read."""
    try:
        words = json.loads((path or CLONES_SWITCH).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return CHECKS_CLONES, []
    if not isinstance(words, dict):
        return CHECKS_CLONES, []
    clones = words.get("clones")
    clones = clones if isinstance(clones, int) and not isinstance(clones, bool) and 1 <= clones <= 64 else CHECKS_CLONES
    bots = words.get("bots") if isinstance(words.get("bots"), list) else []
    return clones, sorted({number for number in bots
                           if isinstance(number, int) and not isinstance(number, bool) and 1 <= number <= clones})


def unit_numbers(unit: str, runner: Run, names: tuple[str, ...]) -> dict[str, str]:
    """`systemctl show` of a unit: the properties `names`, as systemd writes them."""
    shown = runner(["systemctl", "show", unit, "-p", ",".join(names)])
    found = {}
    for line in shown.splitlines():
        name, _, value = line.partition("=")
        if name in names:
            found[name] = value.strip()
    return found


def _gb(value: str) -> float | None:
    """A byte count as systemd shows it ("[not set]", "infinity" or a number), in GB."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number / 1024 ** 3 if 0 <= number < 2 ** 62 else None


def last_result(unit: str, runner: Run) -> str:
    """How a service that runs and ends ended its last run: "success", "exit-code", ..."""
    shown = runner(["systemctl", "show", unit, "-p", "Result", "--value"]).strip()
    return shown or "unknown"


def look_at_site(check: Health, runner: Run) -> None:
    active = runner(["systemctl", "is-active", "picwise-web"]).strip() or "unknown"
    since = runner(["systemctl", "show", "-p", "ActiveEnterTimestamp", "--value", "picwise-web"]).strip()
    release = os.path.basename(os.path.realpath("/srv/picwise/current"))
    check.say(f"site: {active}, since {since or 'unknown'}; release {release}")
    check.limit(active != "active", f"the site's service is {active}")


def look_at_preparation(check: Health, runner: Run) -> float | None:
    """The night's preparation; its peak memory in GB, when its line was found."""
    note = read_json(PREPARED_NOTE)
    if note is None:
        check.say("prepared: no note")
        check.limit(True, "the preparation's note cannot be read")
    else:
        if note.get("prepared") is True:
            hours = hours_since(note.get("prepared_at"), check.now)
            check.say(
                f"prepared: {note.get('products')} products, {note.get('shops')} shops, "
                f"prepared {_age(hours)} ({note.get('prepared_at')})"
            )
            check.limit(hours is None or hours > MAX_AGE_HOURS, f"the catalogue was prepared {_age(hours)}")
        else:
            # A failed night's note carries no time of its own: the site answers from the
            # file before it until that one is 30 hours old.
            check.say(f"prepared: NOT, {note.get('reason')}; note written {note.get('written_at')}")
            check.limit(True, f"the night's preparation failed ({note.get('reason')})")
        change = note.get("intake_change")
        if isinstance(change, dict) and change.get("compared_with"):
            parts = {key: [_shop(entry) for entry in change.get(key) or []] for key in ("gone", "shrunk", "new")}
            check.say(
                "shops since the preparation before: "
                + "; ".join(f"{key} {len(found)}" + (f" ({', '.join(found)})" if found else "") for key, found in parts.items())
            )
            check.limit(bool(parts["gone"] or parts["shrunk"]), "a shop was lost or shrank to less than half")
        elif isinstance(change, dict):
            check.say("shops since the preparation before: not compared")
        memory = note.get("memory")
        if isinstance(memory, dict):
            check.say(
                f"catalogue memory: {memory.get('nights')} nights, {memory.get('new_tonight')} new tonight, "
                f"{memory.get('price_changed_tonight')} prices changed tonight, {memory.get('gone_since')} gone since"
            )
        notes = note.get("price_notes")
        if isinstance(notes, dict):
            check.say(
                f"price notes: {notes.get('down')} down, {notes.get('up')} up, "
                f"{notes.get('same')} same, {notes.get('watch')} watched"
            )
    journal = runner(["journalctl", "-u", "picwise-prepare.service", "-o", "cat", "--no-pager", "--since", "-26h"])
    found = [m for m in (_PREPARE_LINE.match(line.strip()) for line in journal.splitlines()) if m]
    if not found:
        check.say("preparation, the last in 26 h: no line of its memory")
        return None
    peak_gb = int(found[-1].group(1)) * 1024 / _GB
    minutes = float(found[-1].group(2)) / 60
    check.say(f"preparation, the last in 26 h: peak memory {peak_gb:.1f} GB, {minutes:.1f} minutes")
    check.limit(minutes > MAX_PREPARE_MINUTES, f"the preparation took {minutes:.0f} minutes")
    return peak_gb


def look_at_offers(check: Health, runner: Run) -> None:
    result = last_result("picwise-offers.service", runner)
    offers = read_json(OFFERS_FILE)
    if offers is None:
        check.say(f"offers: none fetched yet; the last fetch: {result}")
        check.limit(True, "no offers file")
        return
    shops = offers.get("shops") if isinstance(offers.get("shops"), dict) else {}
    live = sum(len(shop.get("offers") or []) for shop in shops.values() if isinstance(shop, dict))
    hours = hours_since(offers.get("fetched_at"), check.now)
    check.say(
        f"offers: {live} live from {len(shops)} of the {offers.get('shops_in_feed')} shops in the feed, "
        f"fetched {_age(hours)}; the last fetch: {result}"
    )
    # The fetch's own lines, which take the token and the publisher out (fetch_offers._redact).
    journal = runner(["journalctl", "-u", "picwise-offers.service", "-o", "cat", "--no-pager", "--since", "-26h"])
    said = [line.strip() for line in journal.splitlines() if line.startswith("offers: ")]
    if said:
        check.say(f"offers, the last fetch said: {said[-1]}")
    check.limit(hours is None or hours > MAX_AGE_HOURS, f"the offers were fetched {_age(hours)}")
    check.limit(result not in ("success", "unknown"), f"the last fetch of the offers ended: {result}")


def look_at_photos(check: Health, runner: Run) -> None:
    result = last_result("picwise-photos.service", runner)
    photos = read_json(PHOTOS_FILE)
    if photos is None:
        check.say(f"photos: not checked yet; the last check: {result}")
        return
    hours = hours_since(photos.get("checked_at"), check.now)
    gone = photos.get("gone") or []
    check.say(f"photos gone: {len(gone)} of {photos.get('photos')}, checked {_age(hours)}; the last check: {result}")
    check.limit(hours is None or hours > MAX_AGE_HOURS, f"the photos were checked {_age(hours)}")
    check.limit(result not in ("success", "unknown"), f"the last check of the photos ended: {result}")


def _counts(counts: object) -> str:
    return ", ".join(f"{name} {count:,}" for name, count in sorted((counts or {}).items())) if isinstance(counts, dict) else ""


def look_at_checks(check: Health, runner: Run) -> None:
    """The shops' checks: the bot's note of its night (`CHECKS_NOTE`, counts and shop names
    only) and what the preparation applied of it (the public note's `checks`)."""
    prepared = read_json(PREPARED_NOTE) or {}
    applied = prepared.get("checks") if isinstance(prepared.get("checks"), dict) else {}
    note = read_json(CHECKS_NOTE)
    # The bots switched on (their rules 23): each its own day; with every one on the night is the
    # recording's, else the bot alone's.
    clones, bots = checks_bots()
    every = len(bots) == clones
    result = last_result("picwise-checks-record.service" if every else "picwise-checks.service", runner)
    problems = look_at_bots(check, runner, clones, bots, note) if bots else []
    if note is None:
        check.say("checks: no night recorded yet" + (f"; the last round: {result}" if result != "unknown" else ""))
        check.limit(result not in ("success", "unknown", ""), f"the checks' last round ended: {result}")
        return
    night = str(note.get("night") or "")
    # The bot records the night at 03:05 UTC under that morning's date (the preparation of
    # 04:17 reads it): from 03:30 UTC today's night is due, before it yesterday's. Until 24/11
    # a night was missed only a day later (the night of 24/11, its round ended by an error,
    # read as within every limit that morning).
    due = check.now.date() - timedelta(days=0 if (check.now.hour, check.now.minute) >= CHECKS_DUE else 1)
    try:
        late = (due - datetime.fromisoformat(night).date()).days
    except ValueError:
        late = None
    check.say(f"checks, the night of {night or 'no date'}: {note.get('shops_asked', 0)} shops asked; the last round: {result}")
    check.limit(result not in ("success", "unknown", ""), f"the checks' last round ended: {result}")
    check.limit(late is None or late > 0, f"the checks recorded no night since {night or 'ever'}")
    if note.get("ours"):
        check.say("checks: the round was ours, fewer than half of the shops answered at all; nothing recorded")
        check.limit(True, "the checks' round was ours: fewer than half of the shops answered (rules 7.1)")
        return
    rule = note.get("shop_rule") if isinstance(note.get("shop_rule"), dict) else {}
    if rule.get("on"):
        # The rule of how many of a shop's products pass, as the bot asked under it (section 19).
        nights = int(rule.get("pass_nights") or 0)
        # 21: a pass counts for the day it was made, three nights while a shop is not asked whole.
        counts_for = (f"{nights} nights" if nights != 1 else
                      "the day it was made, 3 nights while its shop is not asked whole")
        check.say(f"checks, how many of a shop's products pass: on; a pass counts for {counts_for}; "
                  f"at most {int(rule.get('most_asked_of_a_shop') or 0):,} asked of a shop; "
                  + (f"at most {int(rule['most_shown_of_a_shop']):,} shown of a shop; "
                     if rule.get("most_shown_of_a_shop") and rule.get("most_shown_of_a_shop") != rule.get("most_asked_of_a_shop")
                     else "")
                  + 
                  f"{rule.get('shops_at_once')} shops at once, pages read on "
                  + (f"{rule['processes']} processes" if rule.get("processes") else "the bot's own process"))
        if nights == 1 and "round_hours" in rule:
            whole = bool(rule.get("whole_round"))
            check.say(f"checks, the round asked {float(rule.get('round_hours') or 0):.1f} hours"
                      + (" (all day)" if whole else " (NOT all day: shops not asked all their products keep them)")
                      + f"; shops asked whole {int(rule.get('asked_whole') or 0):,}"
                      + (f"; not whole: {', '.join(str(name) for name in rule.get('not_whole') or [])}"
                         if rule.get("not_whole") else ""))
            check.limit(not whole, "the checks' round did not ask all day (rules 21): its products stay as they were")
    failed = note.get("failed") if isinstance(note.get("failed"), dict) else {}
    check.say(f"checks: decided {note.get('decided', 0):,}, passed {note.get('passed', 0):,}, "
              f"failed {sum(failed.values()):,}" + (f" ({_counts(failed)})" if failed else "")
              + f"; cut tonight {note.get('cut_tonight', 0):,}, back {note.get('back_tonight', 0):,}"
              + (f"; held: {_counts(note.get('held'))}" if note.get("held") else ""))
    braked = [str(name) for name in note.get("braked_shops") or []]
    if braked:
        check.say("checks, a shop's brake held its cuts: " + ", ".join(braked))
    check.limit(bool(braked), "a shop's brake held the checks' cuts: " + ", ".join(braked) + " (rules 7.2)")
    check.limit(bool(note.get("night_brake")), "the whole night's brake held: nothing new cut (rules 7.4)")
    check.limit(bool(note.get("stopped")), "the checks' cutting stopped until the owner's word (rules 7.4)")
    cannot = note.get("cannot_be_checked") if isinstance(note.get("cannot_be_checked"), dict) else {}
    for name, entry in sorted(cannot.items()):
        why, day = (list(entry) + ["", 0])[:2] if isinstance(entry, (list, tuple)) else (str(entry), 0)
        day = int(day or 0)
        leaves = ("; leaves tomorrow" if day == CHECKS_OUT_ON_DAY - 1
                  else "; out" if day >= CHECKS_OUT_ON_DAY else f"; leaves on day {CHECKS_OUT_ON_DAY}")
        check.say(f"checks, cannot be checked: {name}: {why}, day {day}{leaves}")
    stable_day(check, note, rule, late, problems)
    awin = note.get("awin") if isinstance(note.get("awin"), dict) else {}
    newly = [f"{entry[0]} ({entry[1]})" for entry in awin.get("newly_out") or [] if isinstance(entry, (list, tuple)) and len(entry) > 1]
    if newly:
        check.say("checks, out by Awin's reading tonight: " + ", ".join(newly))
    proposed = [f"{entry[0]} ({str(entry[1]).replace('Awin: ', '')}, {int(entry[2] or 0):,} products)"
                for entry in awin.get("would_be_out_if_proposed") or [] if isinstance(entry, (list, tuple)) and len(entry) > 2]
    if proposed:
        check.say("checks, not out while the Proposed rule waits for the owner's yes (rules 5.6.3): " + ", ".join(proposed))
    old_feed = note.get("old_feed_would_wait") if isinstance(note.get("old_feed_would_wait"), dict) else {}
    if old_feed.get("products"):
        most = ", ".join(f"{entry[0]} {int(entry[1]):,}" for entry in old_feed.get("most") or []
                         if isinstance(entry, (list, tuple)) and len(entry) > 1)
        check.say(f"checks, the Proposed rule of a feed over 7 days old would not show {int(old_feed['products']):,} "
                  f"products of {int(old_feed.get('shops') or 0)} shops (rules 5.6.4; waits for the owner's yes)"
                  + (f": {most}" if most else ""))
    if awin.get("waits"):
        check.say(f"checks, a reading of Awin waits for the owner's word: {int(awin.get('products') or 0):,} products")
    check.limit(bool(awin.get("waits")), "a reading of Awin that would put many shops out waits for the owner's word (rules 5.6.3)")
    if applied.get("applied"):
        check.say(f"checks applied by the preparation: {len(applied.get('shops_out') or {})} shops out "
                  f"({int(applied.get('products_of_shops_out') or 0):,} products), {int(applied.get('cut') or 0):,} products cut, "
                  f"{int(applied.get('price_from_site') or 0):,} at the price of the shop's own page")
        waiting = applied.get("not_shown_until_checked_by_reason")
        if applied.get("not_shown_until_checked"):
            check.say(f"checks, not shown until checked: {int(applied.get('not_shown_until_checked') or 0):,} products"
                      + (f" ({_counts(waiting)})" if isinstance(waiting, dict) and waiting else "")
                      + f"; at the cap's gate {int(applied.get('held_by_the_gate') or 0):,}, "
                      f"named for the bot's next night {int(applied.get('candidates') or 0):,}")
    elif applied:
        check.say(f"checks applied by the preparation: none ({applied.get('why')})")
    shops = applied.get("shop_cap") if isinstance(applied.get("shop_cap"), dict) else {}
    if shops.get("applied"):
        # How many of a shop's products pass (the checks' rules 19.7.3): per shop over the most,
        # its products a card can show, kept by step, left out, candidates.
        check.say(f"checks, how many of a shop's products pass (at most {int(shops.get('limit') or 0):,}): "
                  f"{int(shops.get('capped_shops') or 0)} shops over it, {int(shops.get('cut') or 0):,} products left out, "
                  f"candidates {int(shops.get('candidates') or 0):,}")
        for entry in shops.get("shops") or []:
            if isinstance(entry, dict):
                steps = entry.get("kept_by_step") if isinstance(entry.get("kept_by_step"), dict) else {}
                check.say(f"checks, {entry.get('shop')}: {int(entry.get('kept') or 0):,} of {int(entry.get('products') or 0):,}"
                          + (f" ({_counts({name: count for name, count in steps.items() if count})})" if steps else "")
                          + f"; waiting at the gate {int(entry.get('waiting_at_the_gate') or 0):,}")
    elif shops.get("error"):
        check.say(f"checks, how many of a shop's products pass: NOT WORKED OUT ({shops.get('error')})")
    check.limit(bool(shops.get("error")), "how many of a shop's products pass was not worked out last night: "
                                          f"every shop's products went on to the category cap ({shops.get('error')})")
    if applied.get("gate_off"):
        check.say(f"checks, the cap's gate did not stand last night: {applied.get('gate_off')}")
    check.limit(bool(applied.get("gate_off")), "the checks' gate did not stand last night: new products entered unchecked "
                                               f"({applied.get('gate_off')})")
    category = applied.get("category") if isinstance(applied.get("category"), dict) else {}
    if category:
        check.say(f"checks, the category: {int(category.get('no_category') or 0):,} products with none"
                  + (" HELD by its brake" if category.get("held_by_its_brake") else "")
                  + f", {int(category.get('not_asked_yet') or 0):,} not asked yet")
    check.limit(bool(category.get("held_by_its_brake")),
                "the category's brake held: too many products with none in one night, none cut (rules 5.5, 7.4)")
    shelves = read_json(SHELVES_NOTE)
    if shelves is not None:
        stopped = str(shelves.get("stopped") or "")
        check.say(f"checks, the AI's categories on {shelves.get('night')}: {int(shelves.get('asked') or 0):,} asked, "
                  f"{int(shelves.get('answered') or 0):,} answered ({int(shelves.get('no_line_fits') or 0):,} no line "
                  f"fits), {int(shelves.get('refused') or 0):,} refused, {int(shelves.get('left') or 0):,} left; "
                  f"${float(shelves.get('cost_usd') or 0):.2f}" + (f"; stopped: {stopped}" if stopped else ""))
        check.limit("budget" in stopped, f"the AI's categories stopped at the night's brake of $10 ({stopped})")


# The stable day (the checks' rules 23.6; the brief the owner gave on 26/11): the failures of a
# usual day, as a share of the products decided (25/11: 1,490 of 121,416, 1.2%), and twice it the
# most a stable day has; the server's own clock of how long it has been up.
USUAL_FAILED_SHARE = 0.012
UPTIME = Path("/proc/uptime")
# The round's hours, UTC: from 05:30 the day before the night until 03:05 (the bots' `--until`).
ROUND_STARTS = (5, 30)
ROUND_ENDS = (3, 5)


def stable_day(check: Health, note: dict, rule: dict, late: int | None, problems: list[str]) -> None:
    """One line: whether the night just recorded was a stable day (the checks' rules 23.6): the
    round asked all day; the night recorded on time; the server not started again during the
    round; every shop asked whole but those that cannot be checked; no bot started again or near
    its memory's limit; the failures near a usual day's; no shop newly unable to be checked. The
    site's speed is the workflow's own line (its four searches from outside). Said, no limit of
    its own: each of its parts that is one passes its own."""
    if not rule.get("on") or int(rule.get("pass_nights") or 0) != 1:
        return  # Only under the rule of the day (21), which the stable day is measured against.
    night = str(note.get("night") or "")
    try:
        ends = datetime.fromisoformat(night).replace(hour=ROUND_ENDS[0], minute=ROUND_ENDS[1], tzinfo=timezone.utc)
    except ValueError:
        return
    starts = (ends - timedelta(days=1)).replace(hour=ROUND_STARTS[0], minute=ROUND_STARTS[1])
    try:
        up = float(UPTIME.read_text(encoding="utf-8").split()[0])
        booted = check.now - timedelta(seconds=up)
    except (OSError, ValueError, IndexError):
        booted = None
    cannot = note.get("cannot_be_checked") if isinstance(note.get("cannot_be_checked"), dict) else {}
    newly = sorted(name for name, entry in cannot.items()
                   if isinstance(entry, (list, tuple)) and len(entry) > 1 and int(entry[1] or 0) == 1)
    not_whole = [str(name) for name in rule.get("not_whole") or [] if str(name) not in cannot]
    failed = sum((note.get("failed") or {}).values()) if isinstance(note.get("failed"), dict) else 0
    decided = int(note.get("decided") or 0)
    share = failed / decided if decided else 0.0
    parts = [
        ("the round asked all day", bool(rule.get("whole_round"))),
        ("the night recorded on time", late == 0),
        ("the server up all the round" + (f" (started {booted:%d/%m %H:%M} UTC)" if booted is not None and starts <= booted <= ends else ""),
         booted is None or not (starts <= booted <= ends)),
        (f"every shop asked whole but those that cannot be checked" + (f" (not: {', '.join(not_whole[:10])})" if not_whole else ""),
         not not_whole),
        ("no bot started again or near its memory's limit" + (f" (not: {', '.join(problems)})" if problems else ""),
         not problems),
        (f"the failures {share:.1%} of {decided:,} decided (usual {USUAL_FAILED_SHARE:.1%})",
         share <= 2 * USUAL_FAILED_SHARE),
        ("no shop newly unable to be checked" + (f" (new: {', '.join(newly)})" if newly else ""), not newly),
    ]
    check.say(f"checks, the stable day of {night} (rules 23.6): "
              + ("YES" if all(ok for _what, ok in parts) else "NO") + "; "
              + "; ".join(f"{what}: {'yes' if ok else 'NO'}" for what, ok in parts))


def look_at_bots(check: Health, runner: Run, clones: int, bots: list[int], note: dict | None) -> list[str]:
    """The checks' bots switched on (their rules 23): each one's last day, how many times systemd
    started it again, its memory now and its peak against its limit; the bots' memory together
    against their slice's; and, from the night's note, each one's day as it kept it. A bot that
    ended badly, was started again, or came near its memory's limit passes a limit: a day of it is
    no stable day (the rules 23.6)."""
    problems: list[str] = []
    check.say(f"checks, the bots: {len(bots)} of {clones} on ({', '.join(str(number) for number in bots)})"
              + ("; the bot alone asks the others' shops and records the night" if len(bots) < clones else
                 "; the night recorded from their days"))
    for number in bots:
        unit = f"picwise-checks@{number}.service"
        shown = unit_numbers(unit, runner, ("Result", "NRestarts", "MemoryCurrent", "MemoryPeak", "ActiveState"))
        ended = shown.get("Result") or last_result(unit, runner)
        restarts = int(shown.get("NRestarts") or 0) if str(shown.get("NRestarts") or "0").isdigit() else 0
        now, peak = _gb(shown.get("MemoryCurrent", "")), _gb(shown.get("MemoryPeak", ""))
        check.say(f"checks, bot {number}: {shown.get('ActiveState') or 'unknown'}, its last day: {ended}; "
                  f"started again by systemd {restarts} times"
                  + (f"; memory {now:.2f} GB" if now is not None else "")
                  + (f", its peak {peak:.2f} GB of {BOT_MEMORY_MAX_GB:.1f}" if peak is not None else ""))
        for passed, what in ((ended not in ("success", "unknown", ""), f"the checks' bot {number} ended: {ended}"),
                             (restarts > 0, f"the checks' bot {number} was started again {restarts} times (its memory's limit?)"),
                             (peak is not None and peak >= NEAR_THE_LIMIT * BOT_MEMORY_MAX_GB,
                              f"the checks' bot {number} came near its memory's limit ({peak or 0:.2f} GB of "
                              f"{BOT_MEMORY_MAX_GB:.1f})")):
            check.limit(passed, what)
            if passed and f"bot {number}" not in problems:
                problems.append(f"bot {number}")
    together = unit_numbers("picwisebots.slice", runner, ("MemoryCurrent", "MemoryPeak"))
    now, peak = _gb(together.get("MemoryCurrent", "")), _gb(together.get("MemoryPeak", ""))
    if now is not None or peak is not None:
        check.say(f"checks, the bots together: memory {now or 0:.2f} GB, their peak {peak or 0:.2f} GB of "
                  f"{BOTS_MEMORY_MAX_GB:.0f}")
    near = peak is not None and peak >= NEAR_THE_LIMIT * BOTS_MEMORY_MAX_GB
    check.limit(near, f"the checks' bots together came near their memory's limit ({peak or 0:.2f} GB of "
                      f"{BOTS_MEMORY_MAX_GB:.0f})")
    if near:
        problems.append("the bots together")
    rule = (note or {}).get("shop_rule") if isinstance((note or {}).get("shop_rule"), dict) else {}
    for entry in rule.get("bots") or []:
        if isinstance(entry, dict):
            name = "the bot alone" if not entry.get("bot") else f"bot {entry.get('bot')}"
            check.say(f"checks, the night's day of {name}: {int(entry.get('shops') or 0)} shops, "
                      f"{float(entry.get('hours') or 0):.1f} hours, started {int(entry.get('starts') or 0)} times, "
                      f"peak {int(entry.get('peak_mb') or 0):,} MB (its reading {int(entry.get('read_peak_mb') or 0):,} MB)")
    return problems


def look_at_itself(check: Health) -> None:
    """The question "is it the kind itself" (docs/PICWISE_KIND_ITSELF_RULES.md, 7 and 10):
    what the preparation read of its answers (the public note's `itself`) and what the
    morning's asking did (`ITSELF_NOTE`): counts and kinds' names only. Nothing is said
    while a release without it runs."""
    prepared = read_json(PREPARED_NOTE) or {}
    applied = prepared.get("itself") if isinstance(prepared.get("itself"), dict) else None
    if applied is not None and not applied.get("applied"):
        check.say(f"kind itself: its answers are not read ({applied.get('why')})")
    elif applied is not None:
        left = _counts(applied.get("left_by_answer"))
        check.say(f"kind itself: {int(applied.get('products_with_a_second_reading') or 0):,} products read twice; "
                  f"{int(applied.get('left_a_kind') or 0):,} left a kind" + (f" ({left})" if left else "")
                  + f", {int(applied.get('came_back') or 0):,} came back; "
                  f"{int(applied.get('products_with_a_question_waiting') or 0):,} wait for an answer, "
                  f"{int(applied.get('products_to_ask_again') or 0):,} to ask again; "
                  f"changed of what was shown the night before {int(applied.get('changed_of_what_was_shown') or 0):,}")
        held = [entry for entry in applied.get("held_by_a_kinds_brake") or [] if isinstance(entry, dict)]
        names = ", ".join(f"{entry.get('kind')} {int(entry.get('products') or 0):,} (since {entry.get('since')})" for entry in held)
        if held:
            check.say(f"kind itself, a kind's brake holds: {names}")
        check.limit(bool(held), f"a kind's brake holds answers to \"is it the kind itself\" until the owner's word: {names} (rules 7.3)")
        night = str(applied.get("held_by_the_nights_brake") or "")
        if night:
            check.say(f"kind itself, the night's brake holds since {night}: {int(applied.get('held_as_shown') or 0):,} products stay as shown")
        check.limit(bool(night), f"the night's brake holds every new answer to \"is it the kind itself\" since {night}, "
                                 "until the owner's word (rules 7.4)")
        stood = str(applied.get("brakes") or "")
        if stood and stood != "stood":
            check.say(f"kind itself, its brakes: {stood}")
        check.limit(bool(stood) and stood != "stood",
                    "the brakes of \"is it the kind itself\" had no night before to hold against (expected only on the "
                    "first night its answers are read)")
        check.limit(bool(applied.get("shown_not_kept")),
                    "what the catalogue shows was not kept for the next night's brakes of \"is it the kind itself\"")
    asked = read_json(ITSELF_NOTE)
    if asked is not None:
        stopped = str(asked.get("stopped") or "")
        first = asked.get("first") if isinstance(asked.get("first"), dict) else {}
        second = asked.get("second") if isinstance(asked.get("second"), dict) else {}
        check.say(f"kind itself, the AI's answers on {asked.get('night')}: {int(asked.get('named') or 0):,} questions named; "
                  f"first reading {int(first.get('answered') or 0):,} of {int(first.get('asked') or 0):,} asked, "
                  f"second {int(second.get('answered') or 0):,} of {int(second.get('asked') or 0):,}; "
                  f"{int(asked.get('left') or 0):,} left; ${float(asked.get('cost_usd') or 0):.2f}"
                  + (f"; stopped at {stopped}" if stopped else ""))
        check.limit("limit" in stopped, f"the asking of \"is it the kind itself\" stopped at the night's brake of $5 ({stopped})")
        check.limit("cannot be read" in stopped, "the answers file of \"is it the kind itself\" cannot be read: nothing was asked")


def look_at_categories(check: Health) -> None:
    """The categories' list (docs/PICWISE_CATEGORY_SWITCHES.md): what the night's preparation
    did with it (the public note's `categories`): its switch, what it closed or would close of
    the products a card can show, the products the AI has given no category yet. Counts only;
    nothing is said while a release without it runs."""
    prepared = read_json(PREPARED_NOTE) or {}
    note = prepared.get("categories") if isinstance(prepared.get("categories"), dict) else None
    if note is None:
        return
    if note.get("products") is None:
        check.say(f"categories: the list decided nothing ({note.get('why') or note.get('error') or 'no note'})")
        return
    applied = bool(note.get("applied"))
    shops = ", ".join(f"{item.get('shop')} {int(item.get('closed') or 0):,}"
                      for item in (note.get("closed_by_shop") or [])[:5])
    check.say(f"categories: {'applied' if applied else 'the switch off'}; of {int(note['products']):,} products a card "
              f"can show {int(note.get('closed') or 0):,} {'closed' if applied else 'would be closed'}, "
              f"{int(note.get('open') or 0):,} open, {int(note.get('undecided') or 0):,} with no category from the AI yet"
              + (f"; most closed: {shops}" if shops else ""))


def _percent(share: object) -> str:
    return f"{100 * float(share):.1f}%" if isinstance(share, (int, float)) else "none judged"


def look_at_meter(check: Health) -> None:
    """The quality meter (docs/PICWISE_KIND_ITSELF_RULES.md, 9): the day's note of
    `picwise-meter.service` (`METER_NOTE`): the cards right of those judged, beside the day
    before; the wrong cards by title and shop. Nothing is said before its first day."""
    note = read_json(METER_NOTE)
    if note is None:
        return
    searches = note.get("searches") if isinstance(note.get("searches"), dict) else {}
    kinds = note.get("kinds") if isinstance(note.get("kinds"), dict) else {}
    week = note.get("kinds_week") if isinstance(note.get("kinds_week"), dict) else {}
    before = note.get("before") if isinstance(note.get("before"), dict) else None
    day = str(note.get("day") or "")
    right, wrong = int(searches.get("yes") or 0), int(searches.get("no") or 0)
    check.say(f"quality on {day or 'no date'}, the 40 searches: {right:,} of {right + wrong:,} cards right "
              f"({_percent(searches.get('share'))}); {int(searches.get('unsure') or 0):,} cannot be told, "
              f"{int(searches.get('not_judged') or 0):,} not judged"
              + (f"; the day before ({before.get('day')}) {_percent(before.get('share'))}" if before else "; no day before"))
    kinds_right, kinds_wrong = int(kinds.get("yes") or 0), int(kinds.get("no") or 0)
    check.say(f"quality, the day's {int(kinds.get('of_the_day') or 0)} kinds: {kinds_right:,} of {kinds_right + kinds_wrong:,} "
              f"cards right ({_percent(kinds.get('share'))}); the last {int(week.get('days') or 0)} days' kinds "
              f"{_percent(week.get('share'))}; {int(note.get('judged_today') or 0):,} cards judged today, "
              f"${float(note.get('cost_usd') or 0):.2f}"
              + (f"; stopped at {note.get('stopped')}" if note.get("stopped") else ""))
    listed = [card for card in note.get("wrong") or [] if isinstance(card, dict) and card.get("part") == "search"]
    for card in listed[:METER_WRONG_PRINTED]:
        check.say(f"quality, wrong for \"{card.get('q')}\": {str(card.get('title') or '')[:90]} "
                  f"({card.get('shop')}, {card.get('price')}): {card.get('why')}")
    try:
        late = (check.now.date() - datetime.fromisoformat(day).date()).days
    except ValueError:
        late = None
    check.limit(late is None or late > 1, f"the quality meter recorded no day since {day or 'ever'}")
    if note.get("fell") and before:
        check.limit(True, f"the quality of the 40 searches fell {float(note.get('fell_points') or 0):.1f} points from the day "
                          f"before: {_percent(before.get('share'))} to {_percent(searches.get('share'))}")
    check.limit("limit" in str(note.get("stopped") or ""), f"the quality meter stopped at its day's $2 ({note.get('stopped')})")
    check.limit(int(searches.get("pages_failed") or 0) > 0,
                f"the quality meter could not read {int(searches.get('pages_failed') or 0)} of the 40 searches' pages")


def site_memory_gb(proc: Path = Path("/proc"), user: str = SITE_USER) -> float:
    """What the site's processes hold in memory (the user it runs as)."""
    try:
        import pwd

        uid = pwd.getpwnam(user).pw_uid
    except (ImportError, KeyError):
        return 0.0
    total_kb = 0
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            status = (entry / "status").read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        fields = dict(line.split(":", 1) for line in status.splitlines() if ":" in line)
        # The effective user, as `ps -u` counts it (server-deploy.yml's "memory of the site").
        if fields.get("Uid", "").split()[1:2] == [str(uid)] and "VmRSS" in fields:
            total_kb += int(fields["VmRSS"].split()[0])
    return total_kb * 1024 / _GB


def memory_available_gb(meminfo: Path = Path("/proc/meminfo")) -> tuple[float, float]:
    """The server's memory, in all and available now."""
    try:
        fields = dict(line.split(":", 1) for line in meminfo.read_text(encoding="utf-8").splitlines() if ":" in line)
        total = int(fields["MemTotal"].split()[0]) * 1024 / _GB
        available = int(fields["MemAvailable"].split()[0]) * 1024 / _GB
    except (OSError, KeyError, ValueError, IndexError):
        return 0.0, 0.0
    return total, available


def look_at_resources(check: Health, peak_gb: float | None) -> None:
    total, available = memory_available_gb()
    site = site_memory_gb()
    load = " ".join(Path("/proc/loadavg").read_text(encoding="utf-8").split()[:3]) if Path("/proc/loadavg").exists() else "?"
    check.say(f"server memory: {total:.1f} GB, {available:.1f} GB available now; load {load} on {os.cpu_count()} cores")
    check.say(f"memory of the site: {site:.1f} GB")
    check.limit(0 < total and available < MIN_AVAILABLE_GB, f"only {available:.1f} GB of memory available")
    if peak_gb is not None:
        night = site + peak_gb
        check.say(f"memory at night, the site and the preparation together: {night:.1f} GB")
        check.limit(night > MAX_NIGHT_MEMORY_GB, f"the site and the preparation together need {night:.1f} GB")
    disk = shutil.disk_usage("/")
    free_gb = disk.free / _GB
    check.say(f"disk: {free_gb:.0f} GB free of {disk.total / _GB:.0f} GB")
    check.limit(free_gb < MIN_FREE_DISK_GB, f"only {free_gb:.0f} GB of disk free")


def look_at_ai(check: Health) -> None:
    yesterday = (check.now - timedelta(days=1)).date().isoformat()
    for day, name in ((yesterday, "yesterday"), (check.now.date().isoformat(), "today so far")):
        spend = read_json(SPEND_DIR / f"{day}.json") or {}
        spent = float(spend.get("spent_usd") or 0.0)
        check.say(f"AI spend {name}: ${spent:.2f} in {int(spend.get('calls') or 0)} calls")
        if name == "yesterday":
            check.limit(spent >= AI_DAILY_CAP_USD, f"the AI spent its whole day's cap yesterday (${spent:.2f})")


def main(*, now: datetime | None = None, runner: Run = run) -> int:
    check = Health((now or datetime.now(timezone.utc)).astimezone(timezone.utc))
    look_at_site(check, runner)
    peak_gb = look_at_preparation(check, runner)
    look_at_offers(check, runner)
    look_at_photos(check, runner)
    look_at_checks(check, runner)
    look_at_itself(check)
    look_at_categories(check)
    look_at_meter(check)
    look_at_resources(check, peak_gb)
    look_at_ai(check)
    for line in check.lines:
        print(line)
    if check.over:
        for what in check.over:
            print(f"over the limit: {what}")
    else:
        print("within every limit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
