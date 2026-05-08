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
    server = run_local_server(host=host, port=port)
    print(f"Picwise local app running on http://{host}:{port}")
    print("Routes: GET /health, GET /demo?q=power+bank+20000mah+for+iphone, GET /picwise-reference")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down local app.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
