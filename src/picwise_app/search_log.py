"""The words of the searches visitors make, kept on PicWise's own server (owner, 2026-11-07).

Asked whether the server should keep the searches visitors make, only their text, to
measure the search on real searches every week («Να κρατά ο server τις αναζητήσεις των
επισκεπτών ... μόνο το κείμενο της αναζήτησης, χωρίς IP ή άλλα στοιχεία»), the owner
answered «Ναι σε όλα». The debugging measures what was thought of; this is what buyers
really type ("iphone", which the search read as a desk phone, was in no measure).

- Kept only where `SEARCH_LOG_DIR_ENV` names a folder that exists: the server's site
  (`/srv/picwise/shared/searches`, made by `deployment/server/deploy.sh`). On Vercel and
  in tests nothing is kept, and nothing pretends to be.
- Only what a search page's own script reports once the page has loaded in a browser
  (`SEARCH_LOG_PATH`): a crawler or a link checker that runs no script adds nothing, and
  neither does "More" or the AI layer's refresh, which are no new search.
- One line per search in the day's file (`2026-11-07.jsonl`, by the UTC day):
  `{"q": "the words"}`, the words as typed, spaces collapsed, cut at
  `MAX_SEARCH_LENGTH`. No time of day, no IP address, no browser or device, no cookie.
- A day's file stops growing at `MAX_DAY_FILE_BYTES`, so no one can fill the disk; files
  older than `KEEP_DAYS` are deleted when a day's first search is kept. The privacy page
  says so (`picwise_surface.legal`, "Searches").
- Each line is one `write` to a file opened for appending, so the site's workers never
  mix their lines. A failure to write is never the visitor's: the page is already shown.
"""
from __future__ import annotations

import json
import os
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

SEARCH_LOG_DIR_ENV = "PICWISE_SEARCH_LOG_DIR"
# The address the search page's script asks, with the search's words as `q`.
SEARCH_LOG_PATH = "/searched"
MAX_SEARCH_LENGTH = 300
MAX_DAY_FILE_BYTES = 20 * 1024 * 1024
KEEP_DAYS = 365

_DAY_FILE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.jsonl$")


def search_log_directory() -> Path | None:
    """The folder searches are kept in, when the site is given one that exists."""
    raw = str(os.environ.get(SEARCH_LOG_DIR_ENV) or "").strip()
    if not raw:
        return None
    folder = Path(raw)
    return folder if folder.is_dir() else None


def search_text(query: object) -> str:
    """The words kept for a search: as typed, spaces collapsed, cut at the limit."""
    return " ".join(str(query or "").split())[:MAX_SEARCH_LENGTH].strip()


def day_file(folder: Path, day: date) -> Path:
    return folder / f"{day.isoformat()}.jsonl"


def prune_search_logs(folder: Path, today: date, *, keep_days: int = KEEP_DAYS) -> int:
    """Delete the day files older than `keep_days`; how many were deleted."""
    oldest = today - timedelta(days=keep_days)
    deleted = 0
    try:
        names = os.listdir(folder)
    except OSError:
        return 0
    for name in names:
        match = _DAY_FILE_RE.match(name)
        if not match:
            continue
        try:
            day = date.fromisoformat(match.group(1))
        except ValueError:
            continue
        if day < oldest:
            try:
                (folder / name).unlink()
                deleted += 1
            except OSError:
                continue
    return deleted


def record_search(query: object, *, now: datetime | None = None) -> bool:
    """Keep one search's words in the day's file. Whether it was kept."""
    folder = search_log_directory()
    text = search_text(query)
    if folder is None or not text:
        return False
    today = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).date()
    path = day_file(folder, today)
    try:
        size = path.stat().st_size
    except FileNotFoundError:
        size = 0
        prune_search_logs(folder, today)
    except OSError:
        return False
    line = (json.dumps({"q": text}, ensure_ascii=False) + "\n").encode("utf-8")
    if size + len(line) > MAX_DAY_FILE_BYTES:
        return False
    try:
        handle = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o640)
    except OSError:
        return False
    try:
        os.write(handle, line)
    except OSError:
        return False
    finally:
        os.close(handle)
    return True


def read_search_log(folder: Path, day: date) -> list[str]:
    """The searches kept on one day, in the order they came; a line that is not one is
    left out."""
    try:
        lines = day_file(folder, day).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    found: list[str] = []
    for line in lines:
        try:
            text = search_text(json.loads(line).get("q"))
        except (ValueError, AttributeError):
            continue
        if text:
            found.append(text)
    return found
