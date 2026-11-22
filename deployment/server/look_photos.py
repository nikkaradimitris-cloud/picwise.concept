"""A look at what the photos' check would leave out with the checks' switch on, before the
«ανέβασε» of the checks (the checks' rules 5.4; task 7): read-only.

    python3 deployment/server/look_photos.py --bundle > look.py     # on GitHub's runner
    python3 - < look.py                                            # on the server, as the site's user

The owner, 2026-11-21, of a photo that does not answer one night: «Αμέσως, για κάθε λόγο».
With the switch on, `deployment/server/check_photos.py` leaves out any photo that fails, not
only a link to nothing (404, 410), and the deployment itself starts that check
(`deploy.sh`): what it finds is off the site within the hour, behind its brakes. So this
look counts first, on the server, what it would find:

- what the night's check holds today (`photos.sqlite3`, opened read-only): how many photos
  of the catalogue it read, called gone, or could not read. The ones it could not read are
  asked first by the strict check, and any that still fails is left out;
- then it asks a sample as the strict check asks: every photo the check could not read (up
  to a limit) and a few photos of each shop, each once (HEAD, then a GET of one byte where
  the HEAD is refused or says the photo is no image or empty), and says what the strict
  check would call each, with its brakes.

The release in use does not carry the strict check yet, so `--bundle` puts this commit's
`check_photos.py` in the file sent to the server, loaded there as the release's own file
would be. Nothing is written: the database is opened read-only, no list is written, and
the workflow's unit can write nowhere under /srv. Printed: counts, HTTP statuses, content
types and shop names only; never an address.
"""
import json
import random
import sqlite3
import sys
import threading
import time
import types
from collections import Counter
from pathlib import Path

AS_IF = "/srv/picwise/current/deployment/server/check_photos.py"
DB = "/srv/picwise/shared/photos/photos.sqlite3"
UNREAD_LIMIT = 6000
A_SHOP = 40
BUDGET_SECONDS = 600.0
LISTED = 25
SEED = 20261122


def bundle() -> str:
    """This file with this commit's `check_photos.py` in front of it, as one program."""
    here = Path(__file__).resolve()
    source = (here.parent / "check_photos.py").read_text(encoding="utf-8")
    return f"CHECK_PHOTOS_SOURCE = {json.dumps(source)}\n" + here.read_text(encoding="utf-8")


def load_check_photos(source: str) -> types.ModuleType:
    module = types.ModuleType("check_photos")
    module.__file__ = AS_IF
    sys.modules["check_photos"] = module
    exec(compile(source, AS_IF, "exec"), module.__dict__)
    return module


def shares(counts: Counter, total: int, listed: int = LISTED) -> str:
    return ", ".join(f"{name} {count:,}" for name, count in counts.most_common(listed)) or "none" if total else "none"


def look(photos_module: types.ModuleType, say=print) -> int:
    catalogue = photos_module.catalogue_photos(photos_module.DEFAULT_CATALOGUE)
    products = sum(count for _shop, count in catalogue.values())
    say(f"the catalogue: {len(catalogue):,} photos of {products:,} products")

    # What the night's check holds today.
    db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        held = {url: (state, status, asked) for url, state, status, asked in
                db.execute("SELECT url, state, status, asked FROM photo")}
    finally:
        db.close()
    states: Counter = Counter()
    unread_statuses: Counter = Counter()
    unread_shops: Counter = Counter()
    unread_products = 0
    for url, (shop, count) in catalogue.items():
        state, status, _asked = held.get(url, ("never asked", 0, 0))
        states[state] += 1
        if state == "unread":
            unread_statuses[status] += 1
            unread_shops[shop or "-"] += count
            unread_products += count
    say("the night's check today, of the catalogue's photos: " + shares(states, len(catalogue)))
    say(f"could not be read: {states['unread']:,} photos of {unread_products:,} products; by the answer kept: "
        + shares(unread_statuses, states["unread"]))
    say("could not be read, products by shop: " + shares(unread_shops, states["unread"]))

    # The sample: every photo the check could not read (up to a limit), and a few of each shop.
    chooser = random.Random(SEED)
    unread = sorted(url for url in catalogue if held.get(url, ("",))[0] == "unread")
    if len(unread) > UNREAD_LIMIT:
        unread = chooser.sample(unread, UNREAD_LIMIT)
    by_shop: dict[str, list[str]] = {}
    for url, (shop, _count) in catalogue.items():
        if held.get(url, ("",))[0] != "unread":
            by_shop.setdefault(shop or "-", []).append(url)
    others: list[str] = []
    for shop in sorted(by_shop):
        urls = sorted(by_shop[shop])
        others.extend(chooser.sample(urls, min(A_SHOP, len(urls))))
    sample = unread + others
    chooser.shuffle(sample)
    say(f"asked now, as the strict check asks: {len(unread):,} the check could not read, and {len(others):,} others "
        f"({A_SHOP} a shop, {len(by_shop)} shops)")

    asker = photos_module.Asker(strict=True)
    kinds: dict[str, str] = {}
    twice: Counter = Counter()
    lock = threading.Lock()
    original = asker._ask

    def counting(method: str, url: str):
        answer = original(method, url)
        if method == "GET":
            with lock:
                twice[threading.get_ident()] += 1
        return answer

    asker._ask = counting

    def fetch(url: str) -> int:
        status = asker(url)
        with lock:
            kinds[url] = getattr(asker._local, "kind", "") or "(no type)"
        return status

    started = time.monotonic()
    answers = photos_module.ask_all(sample, fetch, workers=photos_module.WORKERS, budget_seconds=BUDGET_SECONDS)
    again = [url for url, status in answers.items() if status == 0 or 500 <= status < 600]
    left = BUDGET_SECONDS - (time.monotonic() - started)
    if again and left > 0:
        answers.update(photos_module.ask_all(again, fetch, workers=photos_module.WORKERS, budget_seconds=left))
    say(f"answered {len(answers):,} of {len(sample):,} in {time.monotonic() - started:.0f} s; a second ask (GET) "
        f"{sum(twice.values()):,} times; no answer or a server error asked once more: {len(again):,}")

    before = {url: (state, asked) for url, (state, _status, asked) in held.items()}
    # The whole catalogue's photos, as the night's check gives them: a shop's reads on record
    # and the night's tenth are counted over all of them.
    tonight, brakes = photos_module.strict_states(catalogue, answers, before)
    for name, urls in (("the ones the check could not read", [url for url in unread if url in answers]),
                       ("the others", [url for url in others if url in answers])):
        counts: Counter = Counter(tonight[url] for url in urls)
        statuses: Counter = Counter(answers[url] for url in urls if tonight[url] not in ("ok",))
        say(f"== {name}: {len(urls):,} asked: " + shares(counts, len(urls)))
        say("   not read well, by answer (0 none, 204 empty, 415 no image): " + shares(statuses, len(urls)))
        types_415: Counter = Counter(kinds.get(url, "") for url in urls if answers[url] == photos_module.NOT_AN_IMAGE)
        if types_415:
            say("   no image, by the type the host gave: " + shares(types_415, len(urls)))
        failed_shops: Counter = Counter()
        asked_shops: Counter = Counter()
        for url in urls:
            shop = catalogue[url][0] or "-"
            asked_shops[shop] += 1
            if tonight[url] in ("failed", "gone", "held", "held for the owner"):
                failed_shops[shop] += 1
        say("   failed or gone, by shop (of those asked of it): "
            + (", ".join(f"{shop} {count:,}/{asked_shops[shop]:,}" for shop, count in failed_shops.most_common(LISTED))
               or "none"))
    passing_types: Counter = Counter(kinds.get(url, "") for url in answers if tonight[url] == "ok")
    say("read well, by the type the host gave: " + shares(passing_types, len(answers), 12))
    say("the brakes on this sample: shops braked " + (", ".join(brakes["braked_shops"]) or "none")
        + "; hosts that refuse the check " + (", ".join(brakes["hosts_refusing"]) or "none")
        + f"; the night's brake {'HELD' if brakes['night_brake'] else 'not held'} (a tenth of all the products; "
          "this is a sample)")
    say("a look: nothing written")
    return 0


if __name__ == "__main__":
    if "--bundle" in sys.argv[1:]:
        sys.stdout.write(bundle())
        raise SystemExit(0)
    source = globals().get("CHECK_PHOTOS_SOURCE")
    if not source:
        raise SystemExit("run the file `--bundle` writes: this commit's check_photos.py goes with it")
    raise SystemExit(look(load_check_photos(source)))
