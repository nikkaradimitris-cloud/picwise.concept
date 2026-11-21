"""One Python file that runs the checks' bot on the server from stdin, with the checks'
package of this commit, which the release in use does not carry yet: for a look before
the «ανέβασε» of the checks (task 7), never to stand in for a deployment.

    python3 .github/scripts/bundle_checks.py --dry --sample 10 --minutes 20 > bundle.py

Everything after the script's name is given to the bot. The bundle holds
`src/picwise_checks/*.py` and `deployment/bot/shop_checks_bot.py` as text, loads the
package from it, and runs the bot as the release's own file would run, so that it finds
the release's `picwise_providers`, `shop_catalogue_test` and `print_programmes`.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "src" / "picwise_checks"
BOT = ROOT / "deployment" / "bot" / "shop_checks_bot.py"
# Where the bot would be in the release in use: its own paths are worked out from it.
AS_IF = os.environ.get("CHECKS_BUNDLE_AS_IF") or "/srv/picwise/current/deployment/bot/shop_checks_bot.py"
# The package's modules in the order their imports need.
ORDER = ("page_reader", "verdicts", "brakes", "ledger", "rows")

LOADER = r'''
import json, sys, types

def _load(name, source):
    module = types.ModuleType(name)
    module.__package__ = "picwise_checks"
    module.__file__ = "<bundle>/" + name.replace(".", "/") + ".py"
    if name == "picwise_checks":
        module.__path__ = []
    sys.modules[name] = module
    exec(compile(source, module.__file__, "exec"), module.__dict__)
    if name != "picwise_checks":
        setattr(sys.modules["picwise_checks"], name.rsplit(".", 1)[1], module)
    return module

for _name, _source in MODULES:
    _load(_name, _source)
sys.argv = ["shop_checks_bot.py"] + ARGV
exec(compile(BOT_SOURCE, AS_IF, "exec"), {"__name__": "__main__", "__file__": AS_IF})
'''


def bundle(arguments: list[str]) -> str:
    modules = [("picwise_checks", (PACKAGE / "__init__.py").read_text(encoding="utf-8"))]
    for name in ORDER:
        modules.append((f"picwise_checks.{name}", (PACKAGE / f"{name}.py").read_text(encoding="utf-8")))
    known = {f"picwise_checks.{path.stem}" for path in PACKAGE.glob("*.py") if path.stem != "__init__"}
    missing = known - {name for name, _source in modules}
    if missing:
        raise SystemExit(f"modules not in ORDER: {sorted(missing)}")
    return (
        f"MODULES = json.loads({json.dumps(json.dumps(modules))})\n"
        f"BOT_SOURCE = json.loads({json.dumps(json.dumps(BOT.read_text(encoding='utf-8')))})\n"
        f"ARGV = {json.dumps(arguments)}\n"
        f"AS_IF = {json.dumps(AS_IF)}\n"
        "import json\n" + LOADER
    )


if __name__ == "__main__":
    sys.stdout.write("import json\n" + bundle(sys.argv[1:]))
