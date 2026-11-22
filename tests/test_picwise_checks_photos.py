"""The photo check with the checks' switch on (`deployment/server/check_photos.py`; the
checks' rules 5.4 and 7.2 to 7.4; owner, 2026-11-21: «Αμέσως, για κάθε λόγο»).

Pinned: any failure leaves the photo's products out that night (no answer and a server
error asked once more first; no image; empty; a refusal), a 429 is our pace and no
failure, a shop whose photo host refuses 9 in 10 of 20 has them not checked; a shop's new
failures over a quarter of 20 decided are held one night (until the owner's word where it
has fewer than 20 photos read on record); a night whose new failures would leave out over
a tenth of the products cuts none. With the switch off the check is as before: only 404
and 410 are gone.

Every address is a fictional `.invalid` one; the fetch is a local stand-in.
"""
from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "deployment" / "server"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import check_photos as photos  # noqa: E402


def _photos(shop: str, count: int, *, start: int = 0, products: int = 1) -> dict[str, tuple[str, int]]:
    return {f"https://img.invalid/{shop}/{n}.jpg": (shop, products) for n in range(start, start + count)}


class StatesTests(unittest.TestCase):
    def test_rules_5_4_any_failure_with_the_switch_on(self) -> None:
        for status, state in ((200, "ok"), (206, "ok"), (404, "gone"), (410, "gone"), (0, "failed"), (503, "failed"),
                              (415, "failed"), (204, "failed"), (400, "failed"), (403, "refused"), (401, "refused"),
                              (429, "unread")):
            with self.subTest(status=status):
                self.assertEqual(photos.state_of(status, strict=True), state)

    def test_with_the_switch_off_as_before(self) -> None:
        for status, state in ((200, "ok"), (404, "gone"), (0, "unread"), (503, "unread"), (403, "unread")):
            with self.subTest(status=status):
                self.assertEqual(photos.state_of(status), state)

    def test_an_answer_that_is_no_image_or_empty(self) -> None:
        asker = photos.Asker(strict=True)
        asker._local.kind, asker._local.length = "text/html", "900"
        self.assertEqual(asker._strictly(200, "HEAD"), photos.NOT_AN_IMAGE)
        asker._local.kind, asker._local.length = "image/jpeg", "0"
        self.assertEqual(asker._strictly(200, "HEAD"), photos.EMPTY)
        asker._local.kind, asker._local.length = "image/jpeg", "1234"
        self.assertEqual(asker._strictly(200, "HEAD"), 200)
        loose = photos.Asker()
        loose._local.kind, loose._local.length = "text/html", "900"
        self.assertEqual(loose._strictly(200, "HEAD"), 200)

    def test_a_photos_type(self) -> None:
        for kind in ("", "image/webp", "IMAGE/JPEG", "binary/octet-stream", "application/octet-stream; charset=binary"):
            self.assertTrue(photos.image_type(kind), kind)
        for kind in ("text/html", "text/html; charset=utf-8", "application/json", "text/plain"):
            self.assertFalse(photos.image_type(kind), kind)

    def test_only_what_a_get_says_calls_a_photo_no_image_or_empty(self) -> None:
        class Host(photos.Asker):
            """A photo's host: what it answers a HEAD and a GET of one byte (status, type, length)."""

            def __init__(self, **answers) -> None:
                super().__init__(strict=True)
                self.answers, self.asked = answers, []

            def _ask(self, method: str, url: str) -> tuple[int, str]:
                self.asked.append(method)
                status, self._local.kind, self._local.length = self.answers[method]
                return status, ""

        url = "https://img.invalid/k.jpg"
        # A HEAD that names a page and no length, a GET that gives the photo's first byte: read.
        host = Host(HEAD=(200, "text/html", "0"), GET=(206, "image/jpeg", "1"))
        self.assertEqual((host(url), host.asked), (206, ["HEAD", "GET"]))
        self.assertEqual(photos.state_of(206, strict=True), "ok")
        # A page where the photo should be, said by the GET too: no image.
        host = Host(HEAD=(200, "text/html", "900"), GET=(200, "text/html", "900"))
        self.assertEqual((host(url), host.asked), (photos.NOT_AN_IMAGE, ["HEAD", "GET"]))
        # Nothing there: no first byte to give, or a length of 0 on the GET.
        self.assertEqual(Host(HEAD=(200, "image/jpeg", "0"), GET=(416, "", "0"))(url), photos.EMPTY)
        self.assertEqual(Host(HEAD=(200, "image/jpeg", "0"), GET=(200, "image/jpeg", "0"))(url), photos.EMPTY)
        # A photo kept without a type, and an ordinary one: one HEAD each.
        for answer in ((200, "binary/octet-stream", "5000"), (200, "image/jpeg", "1234")):
            host = Host(HEAD=answer)
            self.assertEqual((host(url), host.asked), (200, ["HEAD"]))
        # With the switch off nothing is read strictly.
        loose = Host(HEAD=(200, "text/html", "0"))
        loose.strict = False
        self.assertEqual((loose(url), loose.asked), (200, ["HEAD"]))


class BrakesTests(unittest.TestCase):
    def test_a_photo_host_that_refuses_nine_in_ten_is_not_checked(self) -> None:
        catalogue = _photos("Alpha", 20)
        answers = {url: (403 if n < 18 else 200) for n, url in enumerate(catalogue)}
        states, brakes = photos.strict_states(catalogue, answers, {})
        self.assertEqual(brakes["hosts_refusing"], ["Alpha"])
        self.assertEqual(sum(1 for state in states.values() if state == "unread"), 18)
        few = {url: (403 if n < 2 else 200) for n, url in enumerate(catalogue)}
        states, _brakes = photos.strict_states({**catalogue, **_photos("Big", 1000)}, few,
                                               {url: ("ok", 0) for url in catalogue})
        self.assertEqual(sum(1 for state in states.values() if state == "failed"), 2)

    def test_7_2_a_shops_new_failures_over_a_quarter_are_held(self) -> None:
        catalogue = {**_photos("Alpha", 40), **_photos("Big", 2000)}
        before = {url: ("ok", 0) for url in catalogue}
        alpha = [url for url in catalogue if "/Alpha/" in url]
        answers = {url: (503 if n < 11 else 200) for n, url in enumerate(alpha)}
        states, brakes = photos.strict_states(catalogue, answers, before)
        self.assertEqual(brakes["braked_shops"], ["Alpha"])
        self.assertEqual(sum(1 for state in states.values() if state == "held"), 11)
        again, _brakes = photos.strict_states(catalogue, {url: 503 for url in alpha[:11]},
                                              {**before, **{url: ("held", 0) for url in alpha[:11]}})
        self.assertEqual(set(again.values()), {"failed"})

    def test_7_2_fewer_than_twenty_read_on_record_waits_for_the_owner(self) -> None:
        catalogue = {**_photos("Alpha", 20), **_photos("Big", 2000)}
        alpha = [url for url in catalogue if "/Alpha/" in url]
        answers = {url: (404 if n < 6 else 200) for n, url in enumerate(alpha)}
        states, _brakes = photos.strict_states(catalogue, answers, {})
        self.assertEqual(sum(1 for state in states.values() if state == "held for the owner"), 6)
        held = {url: ("held for the owner", 0) for url in alpha[:6]}
        still, _brakes = photos.strict_states(catalogue, {url: 404 for url in alpha[:6]}, held)
        self.assertEqual(set(still.values()), {"held for the owner"})
        cut, _brakes = photos.strict_states(catalogue, {url: 404 for url in alpha[:6]}, held, owner_cut={"Alpha"})
        self.assertEqual(set(cut.values()), {"gone"})

    def test_7_4_a_night_that_would_leave_out_over_a_tenth_cuts_none(self) -> None:
        catalogue = {**_photos("A", 5), **_photos("B", 5)}
        answers = {url: (404 if url.endswith(("0.jpg", "1.jpg")) else 200) for url in catalogue}
        states, brakes = photos.strict_states(catalogue, answers, {url: ("ok", 0) for url in catalogue})
        self.assertTrue(brakes["night_brake"])
        self.assertNotIn("gone", states.values())


class NightTests(unittest.TestCase):
    def _night(self, catalogue, statuses, *, strict: bool) -> tuple[list[str], dict]:
        asked: list[str] = []

        def fetch(url: str) -> int:
            asked.append(url)
            values = statuses[url]
            return values.pop(0) if isinstance(values, list) and len(values) > 1 else (
                values[0] if isinstance(values, list) else values)

        with tempfile.TemporaryDirectory() as folder:
            db = photos.open_db(Path(folder) / "photos.sqlite3")
            out = Path(folder) / "gone.json"
            photos.run(catalogue, db, out, fetch, workers=1, strict=strict)
            written = json.loads(out.read_text(encoding="utf-8"))
            db.close()
        return asked, written

    def test_strict_no_answer_asked_again_and_a_page_for_a_photo_left_out(self) -> None:
        catalogue = {**_photos("Alpha", 3), **_photos("Big", 200)}
        urls = list(catalogue)
        statuses = {url: 200 for url in catalogue}
        statuses[urls[0]] = [503, 200]
        statuses[urls[1]] = 415
        statuses[urls[2]] = [0, 0]
        asked, written = self._night(catalogue, statuses, strict=True)
        self.assertEqual(asked.count(urls[0]), 2)
        self.assertEqual(sorted(written["gone"]), sorted([urls[1], urls[2]]))

    def test_with_the_switch_off_only_404_and_410_are_gone(self) -> None:
        catalogue = _photos("Alpha", 3)
        urls = list(catalogue)
        _asked, written = self._night(catalogue, {urls[0]: 404, urls[1]: 503, urls[2]: 200}, strict=False)
        self.assertEqual(written["gone"], [urls[0]])


if __name__ == "__main__":
    unittest.main()
