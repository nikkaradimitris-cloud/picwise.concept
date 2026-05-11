from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from picwise_app import run_local_server  # noqa: E402


def main() -> None:
    host = "127.0.0.1"
    port = 8016
    try:
        server = run_local_server(host=host, port=port)
    except OSError as error:
        print(f"Failed to start Picwise local app on http://{host}:{port}: {error}")
        print("Stop any existing run_picwise_app.py process and retry.")
        raise SystemExit(1) from error
    print(f"Picwise local app running on http://{host}:{port}")
    print(
        "Routes: GET /health, GET /, GET /demo?q=power+bank+20000mah+for+iphone, "
        "GET /search?q=power+bank, GET /results?q=power+bank, GET /picwise-reference, "
        "GET /private-beta-readiness, GET /best/{slug}, GET /sitemap-buying-pages.xml"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down local app.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
