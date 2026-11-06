"""The service `picwise-assist`: it answers the site's complex searches with Claude Haiku
5.5 (`docs/PICWISE_AI_LAYER_SPEC.md`, 4.5 to 4.7; `picwise_ai.service`).

Run by `picwise-assist.service`, under its own user, from the release in use, with the
Anthropic SDK of its own virtual environment (`requirements-ai.txt`) and the key in its
environment only (`/etc/picwise/assist.env`, which only systemd reads). The site never
calls the API: it writes a job to the shared folder and reads the answer this writes.

    assist_service.py --dir /srv/picwise/shared/assist [--once]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for folder in (ROOT, ROOT / "src"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Answer the site's complex searches.")
    parser.add_argument("--dir", required=True, help="the folder the site and this service share")
    parser.add_argument("--once", action="store_true", help="answer the jobs waiting now, then stop")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):
        pass
    if not os.environ.get("ANTHROPIC_API_KEY"):
        # Never a reason to fail the deployment: the page stays as it was.
        print("no key in the environment: nothing is asked")
        return 0

    from picwise_ai.client import make_client
    from picwise_ai.service import DAILY_CAP_USD, AssistService

    directory = Path(args.dir)
    print(f"answering the jobs of {directory}; at most ${DAILY_CAP_USD:.2f} a day")
    AssistService(directory, client=make_client()).run(once=args.once)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
