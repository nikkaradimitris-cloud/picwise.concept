"""Step 5 of the price-first plan, second part: the prepared feed on Vercel, every day.

`vercel.json`, `src/picwise_app/prepared_renewal.py`, the renewal route in api/index.py.
Pinned here:

- the deployment's build prepares the feed, and a feed that cannot be read never fails
  the build (`--keep-going`);
- the static folder Vercel requires is the one the build writes its note to;
- one scheduled job a day (all Vercel's free plan runs) calls the renewal route;
- every page still goes to the one Python function;
- the renewal route starts a deployment only for a call carrying CRON_SECRET, through
  the Deploy Hook, and its answer never holds the secret or the hook's link.

Served through api/index.py, the deployed entry point.
"""
from __future__ import annotations

import io
import json
import os
import shlex
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from api.index import app as wsgi_app  # noqa: E402
from picwise_app import prepared_renewal  # noqa: E402
from picwise_app.prepared_renewal import (  # noqa: E402
    CRON_SECRET_ENV,
    DEPLOY_HOOK_ENV,
    RENEWAL_PATH,
    request_prepared_feed_renewal,
)

_SECRET = "fixture-cron-secret-0123456789"
_HOOK = "https://hooks.example.invalid/v1/integrations/deploy/prj_fixture/HOOKSECRET42"


def _call(path: str, *, authorization: str | None = None, method: str = "GET") -> tuple[str, dict[str, str], str]:
    captured: dict[str, object] = {}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        captured["status"] = status
        captured["headers"] = dict(headers)

    environ: dict[str, object] = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": "",
        "wsgi.input": io.BytesIO(b""),
        "wsgi.url_scheme": "https",
    }
    if authorization is not None:
        environ["HTTP_AUTHORIZATION"] = authorization
    body = b"".join(wsgi_app(environ, start_response)).decode("utf-8")
    return str(captured["status"]), captured["headers"], body  # type: ignore[return-value]


class VercelConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))

    def test_the_build_prepares_the_feed_and_never_fails_on_it(self) -> None:
        # The old `builds` setting makes Vercel skip every build command.
        self.assertNotIn("builds", self.config)
        self.assertIsNone(self.config["framework"])
        command = shlex.split(self.config["buildCommand"])
        self.assertEqual(command[:2], ["python3", "tools/prepare_catalogue.py"])
        self.assertIn("--keep-going", command)
        # Vercel refuses an empty static folder; the build writes its note there.
        self.assertEqual(command[command.index("--static-dir") + 1], self.config["outputDirectory"])

    def test_the_shop_page_sample_has_a_last_day(self) -> None:
        # Checking shops' pages is a measurement for a few days (owner, 2026-10-18):
        # whenever the build asks for it, it also names the day it stops.
        command = shlex.split(self.config["buildCommand"])
        if "--sample-shop-pages" in command:
            until = command[command.index("--sample-until") + 1]
            self.assertRegex(until, r"^\d{4}-\d{2}-\d{2}$")

    def test_one_scheduled_renewal_a_day(self) -> None:
        crons = self.config["crons"]
        self.assertEqual(len(crons), 1)
        self.assertEqual(crons[0]["path"], RENEWAL_PATH)
        minute, hour, day, month, weekday = crons[0]["schedule"].split()
        # Vercel's free plan refuses a schedule that runs more than once a day.
        self.assertTrue(minute.isdigit() and hour.isdigit(), crons[0]["schedule"])
        self.assertEqual((day, month, weekday), ("*", "*", "*"))

    def test_every_page_goes_to_the_python_function(self) -> None:
        rewrites = self.config["rewrites"]
        self.assertEqual({rule["destination"] for rule in rewrites}, {"/api/index"})
        self.assertIn("/(.*)", [rule["source"] for rule in rewrites])

    def test_the_config_names_no_key(self) -> None:
        text = (ROOT / "vercel.json").read_text(encoding="utf-8")
        for key in (CRON_SECRET_ENV, DEPLOY_HOOK_ENV, "AWIN_FEED_URL", "apikey", "integrations/deploy"):
            self.assertNotIn(key, text)


class RenewalRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        saved = {name: os.environ.get(name) for name in (CRON_SECRET_ENV, DEPLOY_HOOK_ENV)}
        for name in saved:
            os.environ.pop(name, None)

        def restore() -> None:
            for name, value in saved.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value

        self.addCleanup(restore)
        self.posted: list[str] = []
        self.hook_answer: int | BaseException = 201

        def post(url: str) -> int:
            self.posted.append(url)
            if isinstance(self.hook_answer, BaseException):
                raise self.hook_answer
            return self.hook_answer

        patcher = patch.object(prepared_renewal, "_post_to_hook", side_effect=post)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _configure(self, *, secret: str | None = _SECRET, hook: str | None = _HOOK) -> None:
        if secret is not None:
            os.environ[CRON_SECRET_ENV] = secret
        if hook is not None:
            os.environ[DEPLOY_HOOK_ENV] = hook

    def _renew(self, authorization: str | None = f"Bearer {_SECRET}") -> tuple[str, dict[str, str], dict]:
        status, headers, body = _call(RENEWAL_PATH, authorization=authorization)
        self.assertNotIn(_SECRET, body)
        self.assertNotIn("HOOKSECRET42", body)
        self.assertNotIn("hooks.example.invalid", body)
        return status, headers, json.loads(body)

    def test_the_scheduled_call_asks_for_a_new_deployment(self) -> None:
        self._configure()
        status, headers, payload = self._renew()
        self.assertEqual(status, "200 OK")
        self.assertEqual(payload, {"status": "renewal_requested"})
        self.assertEqual(self.posted, [_HOOK])
        self.assertEqual(headers["Cache-Control"], "no-store")

    def test_a_call_without_the_secret_starts_nothing(self) -> None:
        self._configure()
        for authorization in (None, "", "Bearer", "Bearer wrong-secret", _SECRET, f"Bearer {_SECRET}x"):
            with self.subTest(authorization=authorization):
                status, _headers, payload = self._renew(authorization)
                self.assertEqual(status, "401 Unauthorized")
                self.assertEqual(payload, {"status": "unauthorized"})
        self.assertEqual(self.posted, [])

    def test_without_the_keys_in_vercel_nothing_starts(self) -> None:
        cases = {
            "no CRON_SECRET": ({"secret": None}, CRON_SECRET_ENV),
            "no hook": ({"hook": None}, DEPLOY_HOOK_ENV),
            "a hook that is not https": ({"hook": "http://hooks.example.invalid/x"}, DEPLOY_HOOK_ENV),
        }
        for name, (settings, missing) in cases.items():
            with self.subTest(case=name):
                for variable in (CRON_SECRET_ENV, DEPLOY_HOOK_ENV):
                    os.environ.pop(variable, None)
                self._configure(**settings)
                status, _headers, payload = self._renew()
                self.assertEqual(status, "503 Service Unavailable")
                self.assertEqual(payload, {"status": "not_configured", "missing": missing})
        self.assertEqual(self.posted, [])

    def test_a_hook_that_fails_is_reported_without_its_link(self) -> None:
        self._configure()
        self.hook_answer = 404
        status, _headers, payload = self._renew()
        self.assertEqual(status, "502 Bad Gateway")
        self.assertEqual(payload, {"status": "hook_refused", "http_status": 404})
        self.hook_answer = OSError(f"could not reach {_HOOK}")
        status, _headers, payload = self._renew()
        self.assertEqual(status, "502 Bad Gateway")
        self.assertEqual(payload, {"status": "hook_unreachable", "error": "OSError"})

    def test_only_a_get_reaches_the_route(self) -> None:
        self._configure()
        status, _headers, _body = _call(RENEWAL_PATH, authorization=f"Bearer {_SECRET}", method="POST")
        self.assertEqual(status, "405 Method Not Allowed")
        self.assertEqual(self.posted, [])


class HookRequestTests(unittest.TestCase):
    def test_the_hook_is_posted_to_with_no_body(self) -> None:
        captured = {}

        class _Response:
            status = 201

            def __enter__(self):
                return self

            def __exit__(self, *_exc):
                return False

        def fake_urlopen(request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return _Response()

        with patch.object(prepared_renewal, "urlopen", side_effect=fake_urlopen):
            status, payload = request_prepared_feed_renewal(
                f"Bearer {_SECRET}", env={CRON_SECRET_ENV: _SECRET, DEPLOY_HOOK_ENV: _HOOK}
            )
        self.assertEqual((status, payload), ("200 OK", {"status": "renewal_requested"}))
        request = captured["request"]
        self.assertEqual(request.full_url, _HOOK)
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.data, b"")
        self.assertLessEqual(captured["timeout"], 10.0)


if __name__ == "__main__":
    unittest.main()
