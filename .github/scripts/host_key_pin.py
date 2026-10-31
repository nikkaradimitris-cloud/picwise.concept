"""The pin of PicWise's server's SSH host key, kept in the public repository.

    SERVER_SSH_KEY=... HOST_KEY="ssh-ed25519 AAAA..." python3 .github/scripts/host_key_pin.py

Prints an HMAC-SHA256 of the host key under a key derived from the deploy key (a GitHub
secret). A workflow compares it with `.github/server-host-key.pin` before it sends the
server a secret, so a secret can only reach that server. The host key itself is not
published: scan indexes tie a host key to its server's address, while this pin means
nothing without the deploy key.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import sys

_CONTEXT = b"picwise-host-key-pin-v1|"


def host_key_pin(deploy_key: str, host_key: str) -> str:
    secret = hashlib.sha256(deploy_key.replace("\r", "").strip().encode("utf-8")).digest()
    key_type_and_body = " ".join(host_key.split()[:2]).encode("utf-8")
    return hmac.new(secret, _CONTEXT + key_type_and_body, hashlib.sha256).hexdigest()


def main() -> int:
    deploy_key = os.environ.get("SERVER_SSH_KEY", "")
    host_key = os.environ.get("HOST_KEY", "")
    if not deploy_key.strip() or len(host_key.split()) < 2:
        print("host_key_pin: SERVER_SSH_KEY and HOST_KEY are needed", file=sys.stderr)
        return 2
    print(host_key_pin(deploy_key, host_key))
    return 0


if __name__ == "__main__":
    sys.exit(main())
