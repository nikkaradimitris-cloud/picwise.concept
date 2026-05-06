from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path
from typing import Any
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.index import app as deployment_app  # noqa: E402
from wsgi import app as wsgi_app  # noqa: E402


def _call_wsgi(path: str, query_string: str = "") -> tuple[str, dict[str, str], str]:
    status_holder: dict[str, Any] = {}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        status_holder["status"] = status
        status_holder["headers"] = {key: value for key, value in headers}

    environ: dict[str, object] = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": path,
        "QUERY_STRING": query_string,
        "wsgi.input": io.BytesIO(b""),
        "CONTENT_LENGTH": "0",
        "SERVER_NAME": "localhost",
        "SERVER_PORT": "80",
        "wsgi.url_scheme": "https",
    }
    body_chunks = deployment_app(environ, start_response)
    body = b"".join(body_chunks).decode("utf-8")
    return status_holder["status"], status_holder["headers"], body


class DeploymentEntrypointTests(unittest.TestCase):
    def test_deployment_entrypoint_imports(self) -> None:
        self.assertTrue(callable(deployment_app))
        self.assertTrue(callable(wsgi_app))

    def test_health_route_works_through_deployment_entrypoint(self) -> None:
        status, headers, body = _call_wsgi("/health")
        self.assertEqual(status, "200 OK")
        self.assertEqual(headers["Content-Type"], "application/json; charset=utf-8")
        self.assertIn('"status": "ok"', body)
        self.assertIn('"domain_plan_primary": "picwise.subby.cloud"', body)

    def test_demo_route_works_through_deployment_entrypoint(self) -> None:
        query = "power bank 20000mah for iphone"
        status, headers, body = _call_wsgi("/demo", f"q={quote(query)}")
        self.assertEqual(status, "200 OK")
        self.assertEqual(headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn(query, body)
        self.assertIn("local_test_fixture", body)
        self.assertIn("not_production_data", body)


class DeploymentConfigAndDocsTests(unittest.TestCase):
    def test_deployment_configs_contain_no_secrets(self) -> None:
        vercel_config = (ROOT / "vercel.json").read_text(encoding="utf-8")
        env_template = (ROOT / "deployment" / "app.env.template").read_text(encoding="utf-8")
        wsgi_template = (ROOT / "deployment" / "wsgi_server.template.ini").read_text(encoding="utf-8")

        for forbidden in ("AKIA", "-----BEGIN", "PRIVATE KEY", "SECRET=", "token "):
            self.assertNotIn(forbidden, vercel_config)
            self.assertNotIn(forbidden, env_template)
            self.assertNotIn(forbidden, wsgi_template)

    def test_stage_22_doc_does_not_claim_live_proof(self) -> None:
        stage_doc = (
            ROOT / "docs" / "STAGE_22_LIVE_DEPLOYMENT_TO_PICWISE_SUBBY_CLOUD.md"
        ).read_text(encoding="utf-8")
        self.assertIn("# 22. Live deployment to picwise.subby.cloud", stage_doc)
        self.assertIn("Current stage status in this repository remains `DEPLOYMENT_READY`", stage_doc)
        self.assertIn("not `PASSED`", stage_doc)
        self.assertIn("- [ ] `https://picwise.subby.cloud/health` works", stage_doc)
        self.assertIn("- [ ] `https://picwise.subby.cloud/demo` works", stage_doc)


if __name__ == "__main__":
    unittest.main()

