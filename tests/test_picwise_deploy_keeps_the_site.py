"""A deployment never leaves the site without products (owner, 2026-11-20, of three remedies
put to them after the day's two deployments whose preparations were killed for memory:
«κάνε μόνο το ένα»).

On 2026-11-20 a deployment's preparation was killed, and the deployment then restarted the
site with code that refuses the prepared file in place (a file is read only by the code
that wrote it, `prepared_catalogue.code_fingerprint`): no product for 80 minutes.
`deploy.sh` now asks, after the preparation and before the site is restarted, whether the
new release can read the catalogue in place (`deployment/server/prepared_state.py`, which
reads the file's first fields without loading the catalogue). If not, the site stays on the
release it runs, not restarted, with that release's units, and the deployment fails.
Pinned here: the state of real prepared files and of broken ones, as the site's own check
names them; and the deployment's step itself, run in bash with its services stubbed, both
ways.

Then (owner, the same day: «ότι αφορά τον κατάλογο okay από ποια αλλαγή δεν αφορά τον
κατάλογο γιατί πρέπει να περιμένουμε μισή ώρα?»): a deployment prepares the catalogue
again only when the change concerns it: the new release would not read the file in place,
the preparation's own script or service changed, or the file is a day old or more. Pinned
too, by running that step in bash, each way.

Every product here is local test data (`.invalid` links).
"""
from __future__ import annotations

import gzip
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (HERE, ROOT / "src", ROOT / "deployment" / "server"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import prepared_state  # noqa: E402
import test_picwise_prepared_catalogue as prepared_tests  # noqa: E402
from picwise_providers import prepared_catalogue  # noqa: E402

DEPLOY = ROOT / "deployment" / "server" / "deploy.sh"


def _write(path: Path, payload: dict) -> None:
    path.write_bytes(gzip.compress(json.dumps(payload, ensure_ascii=True).encode("ascii")))


def _payload(**change) -> dict:
    payload = {
        "format": prepared_catalogue._FORMAT,
        "version": prepared_catalogue._VERSION,
        "code": prepared_catalogue.code_fingerprint(),
        "prepared_at": datetime.now(timezone.utc).isoformat(),
        "feed_status": {"code": "not the file's own"},
        "products": [],
    }
    payload.update(change)
    return payload


class RealFileTests(prepared_tests._PreparedMixin, unittest.TestCase):
    def test_a_file_this_code_wrote_is_fresh_as_the_site_reads_it(self) -> None:
        self._write_feed(prepared_tests._feed_rows())
        self._prepare()
        state, prepared_at = prepared_state.state_of(self.prepared_path)
        self.assertEqual(state, "fresh")
        self.assertEqual(prepared_catalogue.check_prepared_catalogue(self.prepared_path).state, "fresh")
        self.assertTrue(prepared_at)

    def test_a_file_cut_short_is_unreadable(self) -> None:
        self._write_feed(prepared_tests._feed_rows())
        self._prepare()
        data = self.prepared_path.read_bytes()
        self.prepared_path.write_bytes(data[: len(data) // 2])
        self.assertEqual(prepared_state.state_of(self.prepared_path), ("unreadable", ""))
        self.assertEqual(prepared_catalogue.check_prepared_catalogue(self.prepared_path).state, "unreadable")


class StateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = Path(tempfile.mkdtemp())
        self.path = self.folder / "catalogue.json.gz"

    def test_each_state_as_the_site_names_it(self) -> None:
        cases = {
            "fresh": _payload(),
            "other_code": _payload(code="0" * 64),
            "too_old": _payload(prepared_at=(datetime.now(timezone.utc) - timedelta(hours=31)).isoformat()),
            "other_format": _payload(version=prepared_catalogue._VERSION + 1),
        }
        for expected, payload in cases.items():
            with self.subTest(expected):
                _write(self.path, payload)
                self.assertEqual(prepared_state.state_of(self.path)[0], expected)
                if expected != "fresh":
                    # Decided by the site before it reads the catalogue itself; "fresh" is
                    # compared on a file the real writer wrote (RealFileTests), since this
                    # one carries no catalogue.
                    self.assertEqual(prepared_catalogue.check_prepared_catalogue(self.path).state, expected)

    def test_only_the_files_own_first_fields_are_read(self) -> None:
        # A "code" inside a later object is not the file's: the file has none of its own.
        payload = _payload()
        del payload["code"]
        payload["feed_status"] = {"code": prepared_catalogue.code_fingerprint()}
        _write(self.path, payload)
        self.assertEqual(prepared_state.state_of(self.path)[0], "other_code")

    def test_no_file_or_not_a_gzip_file(self) -> None:
        self.assertEqual(prepared_state.state_of(self.path), ("missing", ""))
        self.path.write_bytes(b"not a gzip file")
        self.assertEqual(prepared_state.state_of(self.path), ("unreadable", ""))

    def test_the_command_prints_the_state_and_the_time(self) -> None:
        when = datetime.now(timezone.utc).isoformat()
        _write(self.path, _payload(prepared_at=when))
        done = subprocess.run(
            [sys.executable, str(ROOT / "deployment" / "server" / "prepared_state.py"), str(self.path)],
            capture_output=True, text=True, check=False, cwd=str(self.folder),
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout.strip(), f"fresh {when}")
        wrong = subprocess.run(
            [sys.executable, str(ROOT / "deployment" / "server" / "prepared_state.py")],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(wrong.returncode, 2)

    def test_within_hours_a_day_old_file_is_too_old_for_a_deployment(self) -> None:
        when = datetime.now(timezone.utc) - timedelta(hours=25)
        _write(self.path, _payload(prepared_at=when.isoformat()))
        self.assertEqual(prepared_state.state_of(self.path)[0], "fresh")  # the site still reads it
        self.assertEqual(prepared_state.state_of(self.path, within_hours=24)[0], "too_old")
        self.assertEqual(prepared_state.state_of(self.path, within_hours=26)[0], "fresh")
        done = subprocess.run(
            [sys.executable, str(ROOT / "deployment" / "server" / "prepared_state.py"), "--within-hours", "24",
             str(self.path)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertTrue(done.stdout.startswith("too_old "))


class DeployStepTests(unittest.TestCase):
    """The deployment's step, cut from deploy.sh and run in bash: `python3`, `install` and
    `systemctl` are stubbed; the release folders and the `current` link are real."""

    def setUp(self) -> None:
        text = DEPLOY.read_text(encoding="utf-8")
        start = text.index('echo "== the catalogue in place, as this release reads it"')
        end = text.index("systemctl enable --now picwise-prepare.timer", start)
        self.step = text[start:end]
        self.app = Path(tempfile.mkdtemp()) / "app"
        for release in ("old", "new"):
            (self.app / "releases" / release / "deployment" / "server").mkdir(parents=True)
        (self.app / "releases" / "old" / "deployment" / "server" / "picwise-web.service").write_text("old unit\n")
        os.symlink("releases/new", self.app / "current")
        self.log = self.app / "calls.log"

    def _run(self, state: str, previous: str = "releases/old") -> subprocess.CompletedProcess:
        script = "\n".join(
            [
                "set -euo pipefail",
                f"APP='{self.app}'",
                'RELEASE="$APP/releases/new"',
                'SHARED="$APP/shared"',
                f"PREVIOUS='{previous}'",
                f"python3() {{ echo '{state}'; }}",
                f"install() {{ echo \"install $*\" >> '{self.log}'; }}",
                f"systemctl() {{ echo \"systemctl $*\" >> '{self.log}'; }}",
                self.step,
                'echo "this release went in"',
            ]
        )
        return subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=False)

    def _current(self) -> str:
        return os.readlink(self.app / "current")

    def _calls(self) -> str:
        return self.log.read_text() if self.log.exists() else ""

    def test_a_release_that_reads_the_catalogue_goes_in(self) -> None:
        done = self._run("fresh 2026-11-20T10:19:40+00:00")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("this release went in", done.stdout)
        self.assertEqual(self._current(), "releases/new")
        self.assertEqual(self._calls(), "")

    def test_a_release_that_cannot_read_it_leaves_the_site_on_the_one_it_runs(self) -> None:
        for state in ("other_code 2026-11-20T04:33:55+00:00", "too_old", "unreadable", "missing", ""):
            with self.subTest(state):
                os.remove(self.app / "current")
                os.symlink("releases/new", self.app / "current")
                done = self._run(state)
                self.assertEqual(done.returncode, 1)
                self.assertNotIn("this release went in", done.stdout)
                self.assertIn("the site stays on releases/old, not restarted", done.stderr)
                self.assertEqual(self._current(), "releases/old")
                calls = self._calls()
                self.assertIn(f"install -m 644 {self.app}/releases/old/deployment/server/picwise-web.service", calls)
                # A unit the old release has not is left as it is.
                self.assertNotIn("picwise-prepare.timer", calls)
                self.assertEqual(calls.count("install -m 644"), 1)
                self.assertIn("systemctl daemon-reload", calls)
                self.assertNotIn("restart", calls)
                self.log.unlink()

    def test_with_no_release_before_it_the_release_goes_in(self) -> None:
        done = self._run("missing", previous="")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("no release before this one to stay on", done.stdout)
        self.assertEqual(self._current(), "releases/new")

    def test_the_step_puts_back_every_unit_the_services_step_installs(self) -> None:
        text = DEPLOY.read_text(encoding="utf-8")
        services = text[text.index('echo "== services"'):text.index("systemctl daemon-reload")]
        installed = set(re.findall(r"picwise-[a-z-]+\.(?:service|timer)", services))
        put_back = set(re.findall(r"picwise-[a-z-]+\.(?:service|timer)", self.step.split("UNITS=", 1)[1].split('"')[1]))
        # 13, the checks' service and timer (2026-11-21, docs/PICWISE_CHECKS_RULES.md), the
        # AI's category of the products not asked yet (22/11, the checks' rules 5.5), and the
        # AI's answer to "is it the kind itself" (22/11, docs/PICWISE_KIND_ITSELF_RULES.md 8.2).
        self.assertEqual(len(installed), 19)
        self.assertEqual(put_back, installed)

    def test_the_step_comes_after_the_preparation_and_before_the_site_restarts(self) -> None:
        text = DEPLOY.read_text(encoding="utf-8")
        prepare = text.index("systemctl start picwise-prepare.service")
        step = text.index('echo "== the catalogue in place, as this release reads it"')
        restart = text.index("systemctl restart picwise-web.service")
        offers = text.index("systemctl start picwise-offers.service")
        self.assertLess(prepare, step)
        self.assertLess(step, offers)
        self.assertLess(step, restart)
        self.assertIn('prepared_state.py" "$SHARED/prepared/catalogue.json.gz"', text)


class PrepareOnlyWhenNeededTests(unittest.TestCase):
    """The deployment's preparation step, cut from deploy.sh and run in bash: `python3`,
    `systemctl` and `journalctl` are stubbed; the two releases' files are real."""

    def setUp(self) -> None:
        text = DEPLOY.read_text(encoding="utf-8")
        start = text.index('echo "== the catalogue, prepared as a Vercel build prepares it')
        end = text.index('echo "== the catalogue in place, as this release reads it"', start)
        self.step = text[start:end]
        self.app = Path(tempfile.mkdtemp()) / "app"
        for release in ("old", "new"):
            folder = self.app / "releases" / release
            (folder / "tools").mkdir(parents=True)
            (folder / "deployment" / "server").mkdir(parents=True)
            (folder / "tools" / "prepare_catalogue.py").write_text("the preparation\n")
            (folder / "deployment" / "server" / "picwise-prepare.service").write_text("[Service]\n")
        self.log = self.app / "calls.log"

    def _run(self, state: str, previous: str = "releases/old") -> str:
        script = "\n".join(
            [
                "set -euo pipefail",
                f"APP='{self.app}'",
                'RELEASE="$APP/releases/new"',
                'SHARED="$APP/shared"',
                f"PREVIOUS='{previous}'",
                f"python3() {{ echo \"python3 $*\" >> '{self.log}'; echo '{state}'; }}",
                f"systemctl() {{ echo \"systemctl $*\" >> '{self.log}'; }}",
                f"journalctl() {{ echo \"journalctl $*\" >> '{self.log}'; }}",
                self.step,
            ]
        )
        done = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=False)
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout

    def _prepared(self) -> bool:
        return "systemctl start picwise-prepare.service" in (self.log.read_text() if self.log.exists() else "")

    def test_a_change_that_does_not_concern_the_catalogue_is_not_prepared_again(self) -> None:
        said = self._run("fresh 2026-11-20T10:17:27+00:00")
        self.assertFalse(self._prepared())
        self.assertIn("not prepared again: the change does not concern the catalogue", said)
        calls = self.log.read_text()
        self.assertIn("prepared_state.py --within-hours 24", calls)
        self.assertIn("shared/prepared/catalogue.json.gz", calls)

    def test_a_change_of_the_rules_or_a_day_old_file_is_prepared_again(self) -> None:
        for state in ("other_code 2026-11-20T10:17:27+00:00", "too_old 2026-11-19T04:17:00+00:00", "missing",
                      "unreadable", ""):
            with self.subTest(state):
                self._run(state)
                self.assertTrue(self._prepared())
                self.log.unlink()

    def test_a_change_of_the_preparation_itself_is_prepared_again(self) -> None:
        for name in ("tools/prepare_catalogue.py", "deployment/server/picwise-prepare.service"):
            with self.subTest(name):
                changed = self.app / "releases" / "new" / name
                kept = changed.read_text()
                changed.write_text(kept + "changed\n")
                self._run("fresh 2026-11-20T10:17:27+00:00")
                self.assertTrue(self._prepared())
                changed.write_text(kept)
                self.log.unlink()

    def test_with_no_release_before_it_the_catalogue_is_prepared(self) -> None:
        self._run("fresh 2026-11-20T10:17:27+00:00", previous="")
        self.assertTrue(self._prepared())


if __name__ == "__main__":
    unittest.main()
