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
- yesterday's AI spend at the day's cap (the service then asks nothing more that day).

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
SITE_USER = "picwise"

MAX_AGE_HOURS = 30.0
# 24 GB on the server (OVHcloud VPS-4); the rest for the system and the other services.
MAX_NIGHT_MEMORY_GB = 18.0
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
