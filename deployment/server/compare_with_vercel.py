"""Compare the site on PicWise's server with the live site on Vercel, page by page.

    python3 deployment/server/compare_with_vercel.py --server http://127.0.0.1:18016

Run by .github/workflows/server-deploy.yml after a deployment, through an SSH tunnel to
the server's private port. The server is asked as the live site's host over HTTPS
(`Host`, `X-Forwarded-Proto`), so its pages carry the same links. Public pages only:
nothing is written anywhere and no "/out/" link is opened, since that counts as a click
on the shop. Prints, per page, the answer of each site and how they differ; exits 1 only
when the server fails to answer a page.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
import urllib.error
import urllib.request

LIVE_SITE = "https://picwise.subby.cloud"
LIVE_HOST = "picwise.subby.cloud"
PATHS = (
    "/",
    "/terms",
    "/privacy",
    "/cookies",
    "/affiliate-disclosure",
    "/contact",
    "/robots.txt",
    "/health",
    "/suggest.json",
    "/sitemap-buying-pages.xml",
    "/no-such-page",
    "/demo",
    "/search?q=kettle",
    "/private-beta-readiness",
    "/prepared.json",
)
HEADERS = ("content-type", "x-robots-tag", "cache-control")
USER_AGENT = "PicWise-server-compare/1 (GitHub Actions; the owner's own check)"
DIFF_LINES = 12


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def fetch(url: str, headers: dict[str, str]) -> tuple[int, dict[str, str], str]:
    """(status, the compared headers, body); status 0 when nothing answered."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **headers})
    try:
        with _OPENER.open(request, timeout=120) as response:
            status, raw_headers, body = response.status, response.headers, response.read()
    except urllib.error.HTTPError as error:
        status, raw_headers, body = error.code, error.headers, error.read()
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        return 0, {}, f"no answer: {type(error).__name__}"
    kept = {name: str(raw_headers.get(name) or "") for name in HEADERS}
    return status, kept, body.decode("utf-8", "replace")


def comparable_lines(body: str, content_type: str) -> list[str]:
    """The body split so that a difference shows as a few lines: JSON by key, HTML by tag."""
    if "json" in content_type:
        try:
            return json.dumps(json.loads(body), indent=1, sort_keys=True, ensure_ascii=False).splitlines()
        except ValueError:
            pass
    return re.sub(r">\s*<", ">\n<", body).splitlines()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--server", required=True, help="the server's site, e.g. http://127.0.0.1:18016")
    parser.add_argument("--live", default=LIVE_SITE)
    args = parser.parse_args(argv)
    server_headers = {"Host": LIVE_HOST, "X-Forwarded-Proto": "https"}
    same = 0
    server_failed = 0
    for path in PATHS:
        live = fetch(args.live + path, {})
        server = fetch(args.server + path, server_headers)
        print(f"=== {path}")
        for label, (status, headers, body) in (("live  ", live), ("server", server)):
            shown = ", ".join(f"{name}: {value}" for name, value in headers.items() if value)
            print(f"  {label} {status} {len(body):>7} chars  {shown}")
        if server[0] == 0 or server[0] >= 500:
            server_failed += 1
        # Vercel adds headers of its own (a cache rule, for one), so they are named, and
        # a page counts as the same when its answer and its content are.
        for name in HEADERS:
            if live[1].get(name, "") != server[1].get(name, ""):
                print(f"  header {name} differs")
        if live[0] == server[0] and live[2] == server[2]:
            same += 1
            print("  content the same")
            continue
        content_type = server[1].get("content-type", "") or live[1].get("content-type", "")
        diff = [
            line
            for line in difflib.unified_diff(
                comparable_lines(live[2], content_type),
                comparable_lines(server[2], content_type),
                "live",
                "server",
                n=0,
                lineterm="",
            )
            if not line.startswith(("---", "+++", "@@"))
        ]
        print(f"  {len(diff)} lines differ (- live, + server); the first {min(DIFF_LINES, len(diff))}:")
        for line in diff[:DIFF_LINES]:
            print("    " + (line if len(line) <= 200 else line[:200] + " ..."))
    print(f"=== {same} of {len(PATHS)} pages with the same answer and content; the server failed {server_failed}")
    return 1 if server_failed else 0


if __name__ == "__main__":
    sys.exit(main())
