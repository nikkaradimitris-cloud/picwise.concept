"""The service `picwise-families`: which listings of a shop are one product, asked of
Claude Haiku 5.5 (`picwise_ai.families`; owner, 2026-11-19).

Run by `picwise-families.service`, under the AI layer's own user, from the release in
use, with the Anthropic SDK of its own virtual environment and the key in its environment
only (`/etc/picwise/assist.env`). It reads the sets the site writes after each preparation
(`family_jobs.py`) and keeps the answers in the files the site and `family_jobs.py` read.

    family_service.py --dir /srv/picwise/assist/families [--once]
"""
from __future__ import annotations

import argparse
import os
import signal
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for folder in (ROOT, ROOT / "src"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Answer which listings of a shop are one product.")
    parser.add_argument("--dir", required=True, help="the folder the site and this service share")
    parser.add_argument("--once", action="store_true", help="answer the jobs waiting now, then stop")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("no key in the environment: nothing is asked")
        return 0

    from picwise_ai.client import make_client
    from picwise_ai.families import DAILY_CAP_USD, FamilyService

    directory = Path(args.dir)
    # systemd's stop: the answers kept in memory are written before the service ends.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    print(f"answering the families of {directory}; at most ${DAILY_CAP_USD:.2f} a day")
    FamilyService(directory, client=make_client(timeout=60.0)).run(once=args.once)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
