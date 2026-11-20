"""Whether a release can read the prepared catalogue in place, told without loading it
(owner, 2026-11-20, of three remedies put to them: «κάνε μόνο το ένα», this one: when a
deployment's preparation fails, the site stays on the release it runs, so that it is never
left without products).

On 2026-11-20 a deployment's preparation was killed for memory, and the deployment then
restarted the site with code that refuses the file in place (a prepared file is read only
by the code that wrote it, `prepared_catalogue.code_fingerprint`): the site showed no
product for 80 minutes. `deploy.sh` now runs this file with the new release's own code,
after the deployment's preparation and before the site is restarted:

    python3 <release>/deployment/server/prepared_state.py <prepared file>

`deploy.sh` also runs it before the preparation, with `--within-hours 24`, to prepare the
catalogue again only when the change concerns it (owner, 2026-11-20: «από ποια αλλαγή δεν
αφορά τον κατάλογο γιατί πρέπει να περιμένουμε μισή ώρα?»): "fresh" then also means
prepared within that many hours.

It prints one line, the state first, as the site's own check names them
(`prepared_catalogue.check_prepared_catalogue`): "fresh" (this release reads it), "too_old",
"other_code" (written by other code), "other_format", "unreadable", or "missing"; then the
time the file was prepared, when known. Only the file's first bytes are read as text (the
writer puts its format, version, code and time first); the rest is decompressed in small
pieces and dropped, so that a file cut short reads as "unreadable" and no catalogue is
held in memory beside the site and the preparation.
"""
from __future__ import annotations

import argparse
import gzip
import re
import sys
import zlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

RELEASE = Path(__file__).resolve().parents[2]
if str(RELEASE / "src") not in sys.path:
    sys.path.insert(0, str(RELEASE / "src"))

from picwise_providers import prepared_catalogue  # noqa: E402  (this release's own rules)

HEAD_BYTES = 4096
PIECE_BYTES = 1 << 20
_FIELDS = {
    "format": re.compile(r'"format":\s*"([^"]*)"'),
    "version": re.compile(r'"version":\s*(-?\d+)'),
    "code": re.compile(r'"code":\s*"([^"]*)"'),
    "prepared_at": re.compile(r'"prepared_at":\s*"([^"]*)"'),
}


def read_head(path: Path) -> dict[str, str] | None:
    """The file's own first fields, or None when it is not a whole gzip file."""
    try:
        with gzip.open(path, "rb") as stream:
            head = stream.read(HEAD_BYTES).decode("ascii", errors="replace")
            while stream.read(PIECE_BYTES):
                pass
    except (OSError, EOFError, zlib.error):
        return None
    # Only what comes before the first object inside it: the writer's own first fields.
    head = head.split('"feed_status"', 1)[0]
    found: dict[str, str] = {}
    for name, pattern in _FIELDS.items():
        match = pattern.search(head)
        if match is not None:
            found[name] = match.group(1)
    return found


def state_of(path: Path, *, now: datetime | None = None, within_hours: float | None = None) -> tuple[str, str]:
    """The file's state for this release, in the order the site checks it, and the time
    it was prepared ("" when not known). With `within_hours`, a file prepared longer ago
    than that, or than the site's own limit, is "too_old"."""
    if not path.is_file():
        return "missing", ""
    head = read_head(path)
    if head is None:
        return "unreadable", ""
    if head.get("format") != prepared_catalogue._FORMAT or head.get("version") != str(prepared_catalogue._VERSION):
        return "other_format", ""
    if head.get("code") != prepared_catalogue.code_fingerprint():
        return "other_code", head.get("prepared_at", "")
    text = head.get("prepared_at", "")
    try:
        prepared_at = datetime.fromisoformat(text)
    except ValueError:
        return "unreadable", ""
    if prepared_at.tzinfo is None:
        return "unreadable", ""
    limit = prepared_catalogue.prepared_catalogue_age_limit()
    if within_hours is not None:
        limit = min(limit, timedelta(hours=within_hours))
    if (now or datetime.now(timezone.utc)) - prepared_at > limit:
        return "too_old", text
    return "fresh", text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--within-hours", type=float, help="fresh only when prepared within these hours")
    parser.add_argument("path", type=Path, help="the prepared file")
    args = parser.parse_args(argv)
    state, prepared_at = state_of(args.path, within_hours=args.within_hours)
    print(f"{state} {prepared_at}".strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
