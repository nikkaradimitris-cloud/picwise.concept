"""The seal that proves the server holds the feed link, without the link being sent.

`.github/scripts/feed_seal.py`. Owner, 2026-10-27: the server's host key no longer matched
the pin, so the read-only look at the night asks the server to seal a random nonce under
the feed link, as GitHub does from its secret. Pinned here: GitHub's side (the secret as
pasted, with line breaks and spaces) and the server's side (the line the deployment
writes) give the same seal; another link or another nonce gives another; no link, no
seal (and no output); the seal never shows the link.

Every link is local test data: `.invalid` addresses.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".github" / "scripts" / "feed_seal.py"

LINK = "https://feed.invalid/datafeed/download/apikey/0123456789abcdef/fid/1/format/csv"
NONCE = "5f1c0e9a" * 8


def _environment(**extra: str) -> dict[str, str]:
    env = {name: value for name, value in os.environ.items() if name not in ("AWIN_FEED_URL", "PICWISE_ENV_FILE")}
    env.update(extra)
    return env


def _github_side(secret: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], env=_environment(AWIN_FEED_URL=secret),
        capture_output=True, text=True, check=False,
    )


def _server_side(env_file_text: str | None, *args: str) -> subprocess.CompletedProcess:
    """As the workflow runs it: the script on stdin, the nonce after "-"."""
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "picwise.env"
        if env_file_text is not None:
            path.write_text(env_file_text, encoding="utf-8")
        return subprocess.run(
            [sys.executable, "-", *args], input=SCRIPT.read_text(encoding="utf-8"),
            env=_environment(PICWISE_ENV_FILE=str(path)), capture_output=True, text=True, check=False,
        )


def _deployed(link: str) -> str:
    """The file each deployment writes (server-deploy.yml)."""
    return (
        "# The site's secrets, written by each deployment from GitHub's secrets; never in the repository.\n"
        f"AWIN_FEED_URL='{link}'\n"
    )


class FeedSealTests(unittest.TestCase):
    def test_both_sides_seal_alike(self) -> None:
        github = _github_side(f"  {LINK}\r\n", NONCE)
        server = _server_side(_deployed(LINK), NONCE)
        self.assertEqual(github.returncode, 0, github.stderr)
        self.assertEqual(server.returncode, 0, server.stderr)
        self.assertRegex(github.stdout.strip(), r"^[0-9a-f]{64}$")
        self.assertEqual(github.stdout, server.stdout)

    def test_another_link_or_nonce_another_seal(self) -> None:
        seal = _github_side(LINK, NONCE).stdout
        self.assertNotEqual(_server_side(_deployed(LINK + "0"), NONCE).stdout, seal)
        self.assertNotEqual(_github_side(LINK, NONCE[::-1]).stdout, seal)

    def test_no_link_no_seal(self) -> None:
        for result in (
            _github_side("", NONCE),
            _server_side(None, NONCE),
            _server_side("# no link written\n", NONCE),
        ):
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertIn("no feed link", result.stderr)

    def test_a_nonce_is_needed(self) -> None:
        result = _github_side(LINK)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")

    def test_the_seal_never_shows_the_link(self) -> None:
        github = _github_side(LINK, NONCE)
        server = _server_side(_deployed(LINK), NONCE)
        for result in (github, server):
            self.assertNotIn("0123456789abcdef", result.stdout + result.stderr)
            self.assertNotIn("feed.invalid", result.stdout + result.stderr)
            self.assertIsNotNone(re.fullmatch(r"[0-9a-f]{64}\n", result.stdout))


if __name__ == "__main__":
    unittest.main()
