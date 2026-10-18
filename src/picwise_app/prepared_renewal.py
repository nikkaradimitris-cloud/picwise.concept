"""The daily renewal of the prepared feed (step 5 of the price-first plan).

Every deployment's build prepares the feed (`vercel.json`, `tools/prepare_catalogue.py`),
so a new deployment each day gives each day its own prepared feed. Vercel's free plan
runs one scheduled job a day (`vercel.json` "crons"): it calls `RENEWAL_PATH` on the
live site, and this module asks Vercel for a new deployment through a Deploy Hook.

Both keys stay in Vercel's environment variables, never in the repository:

- `CRON_SECRET`: Vercel sends it with its scheduled call ("Authorization: Bearer ...");
  a call without it is refused, so nobody else can start deployments;
- `PICWISE_DEPLOY_HOOK_URL`: the Deploy Hook (Settings, Git, Deploy Hooks), a link that
  starts a deployment of `main` when posted to.

The answer names what happened, never a key: an error is reported by its kind only,
since its text can quote the hook's link.
"""
from __future__ import annotations

import hmac
import os
from collections.abc import Callable, Mapping
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

RENEWAL_PATH = "/cron/renew-prepared-feed"
CRON_SECRET_ENV = "CRON_SECRET"
DEPLOY_HOOK_ENV = "PICWISE_DEPLOY_HOOK_URL"
_HOOK_TIMEOUT_SECONDS = 10.0


def request_prepared_feed_renewal(
    authorization: str,
    *,
    env: Mapping[str, str] | None = None,
    post: Callable[[str], int] | None = None,
) -> tuple[str, dict[str, Any]]:
    """(HTTP status line, JSON answer) for one scheduled call to `RENEWAL_PATH`."""
    source = os.environ if env is None else env
    secret = str(source.get(CRON_SECRET_ENV) or "").strip()
    hook = str(source.get(DEPLOY_HOOK_ENV) or "").strip()
    if not secret:
        return "503 Service Unavailable", {"status": "not_configured", "missing": CRON_SECRET_ENV}
    if not hmac.compare_digest(str(authorization or "").encode("utf-8"), f"Bearer {secret}".encode("utf-8")):
        return "401 Unauthorized", {"status": "unauthorized"}
    if not hook.startswith("https://"):
        return "503 Service Unavailable", {"status": "not_configured", "missing": DEPLOY_HOOK_ENV}
    try:
        code = (post or _post_to_hook)(hook)
    except Exception as error:
        return "502 Bad Gateway", {"status": "hook_unreachable", "error": type(error).__name__}
    if 200 <= code < 300:
        return "200 OK", {"status": "renewal_requested"}
    return "502 Bad Gateway", {"status": "hook_refused", "http_status": code}


def _post_to_hook(url: str) -> int:
    request = Request(url, data=b"", method="POST")
    try:
        with urlopen(request, timeout=_HOOK_TIMEOUT_SECONDS) as response:
            return int(getattr(response, "status", 200))
    except HTTPError as error:
        error.close()
        return int(error.code)
