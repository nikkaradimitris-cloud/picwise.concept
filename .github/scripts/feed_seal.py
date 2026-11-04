"""A seal that proves a server holds the feed link, without the link being sent.

    AWIN_FEED_URL=... python3 .github/scripts/feed_seal.py NONCE      (GitHub's side)
    ssh picwise "sudo python3 - NONCE" < .github/scripts/feed_seal.py   (the server's side)

Prints an HMAC-SHA256 of a random nonce under the feed link: on GitHub from the
AWIN_FEED_URL secret, on the server from /etc/picwise/picwise.env, which each deployment
writes from that secret (server-deploy.yml). A read-only workflow asks for it when the
server's host key no longer matches .github/server-host-key.pin (owner's «Ναι»,
2026-10-27): a machine that seals the nonce as GitHub does holds the link, so it is the
server the deployments wrote to. Only the nonce goes to the server and only the seal
comes back; the link never travels.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import sys

_CONTEXT = b"picwise-feed-seal-v1|"
ENV_FILE = "/etc/picwise/picwise.env"


def normalized(feed: str) -> str:
    """The link as the deployment writes it: no line breaks, no spaces around it."""
    return feed.replace("\r", "").replace("\n", "").strip()


def feed_from_env_file(path: str) -> str:
    """The link from the deployment's `AWIN_FEED_URL='...'` line, or "" without one."""
    try:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("AWIN_FEED_URL="):
                    value = line[len("AWIN_FEED_URL="):].rstrip("\n")
                    if len(value) >= 2 and value[0] == value[-1] == "'":
                        value = value[1:-1]
                    return value
    except OSError:
        pass
    return ""


def seal(feed: str, nonce: str) -> str:
    return hmac.new(normalized(feed).encode("utf-8"), _CONTEXT + nonce.encode("utf-8"), hashlib.sha256).hexdigest()


def main(argv: list[str]) -> int:
    if len(argv) != 2 or not argv[1].strip():
        print("feed_seal: a nonce is needed", file=sys.stderr)
        return 2
    feed = os.environ.get("AWIN_FEED_URL")
    if feed is None:  # the server's side, where sudo clears the environment
        feed = feed_from_env_file(os.environ.get("PICWISE_ENV_FILE", ENV_FILE))
    if not normalized(feed):
        print("feed_seal: no feed link", file=sys.stderr)
        return 1
    print(seal(feed, argv[1].strip()))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
