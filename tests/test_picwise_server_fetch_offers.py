"""The nightly fetch of the Awin offers of PicWise's own shops.

`deployment/server/fetch_offers.py`, run by picwise-offers.service (owner, 2026-11-01:
«Οκ να φέρνει τις προσφορές των δικών μας καταστημάτων»). Pinned here, on answers shaped
as Awin's first real answer was (run 41226304997): the shops are the advertisers of the
downloaded feed, by id; Awin is asked only for their offers, in groups, page by page,
each offer once; only offers live now by their own dates are kept, with a code and a
link only where Awin gives them; the file is replaced whole, and kept when a read
fails; the printed lines carry counts and shop names only, never a code, a title, the
token or the account's id; no token fetches nothing and fails nothing. The deployment
installs the service and its timer and writes the token from GitHub's secrets.

Every shop, offer and code is fictional.
"""
from __future__ import annotations

import csv
import gzip
import importlib.util
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "deployment" / "server" / "fetch_offers.py"
_spec = importlib.util.spec_from_file_location("fetch_offers", SCRIPT)
fetch = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fetch)

TOKEN = "tok-secret-0123456789"
NOW = datetime(2026, 11, 1, 5, 5, tzinfo=timezone.utc)


def _feed(folder: Path, rows: list[tuple[str, str]], *, name: str = "picwise_awin_feed_abc.bin") -> Path:
    path = folder / name
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["aw_product_id", "product_name", "merchant_id", "merchant_name", "search_price"])
    for index, (ident, shop) in enumerate(rows):
        writer.writerow([f"p{index}", f"Fixture product {index}", ident, shop, "9.99"])
    path.write_bytes(gzip.compress(buffer.getvalue().encode("utf-8")))
    return path


def _offer(number: int, advertiser: int, name: str, *, joined: bool = False, code: str | None = None,
           start: str = "2026-10-01T00:00:00", end: str = "2026-12-31T23:59:59", kind: str = "voucher") -> dict:
    return {
        "promotionId": number, "type": kind,
        "advertiser": {"id": advertiser, "name": name, "joined": joined},
        "title": f"Fictional offer {number}" + (f" with code {code}" if code else ""),
        "description": "Local test data.", "terms": "Fictional terms.",
        "startDate": start, "endDate": end, "status": "active",
        "url": None if not joined else "https://fixture.example.invalid/shop",
        "urlTracking": None if not joined else "https://fixture.example.invalid/track?offer=1",
        "dateAdded": "2026-10-01T00:00:00", "campaign": "", "regions": {"all": True}, "categories": [],
        "voucher": {"code": code if joined else None, "exclusive": False, "attributable": True},
    }


class _Awin:
    def __init__(self, offers: list[dict], status: int = 200) -> None:
        self.offers = offers
        self.status = status
        self.bodies: list[dict] = []

    def __call__(self, url: str, body: dict, token: str) -> tuple[int, object]:
        self.bodies.append(body)
        if self.status != 200:
            return self.status, {"error": f"denied for {token}"}
        wanted = set(body["filters"]["advertiserIds"])
        mine = [offer for offer in self.offers if offer["advertiser"]["id"] in wanted]
        page, size = body["pagination"]["page"], body["pagination"]["pageSize"]
        return 200, {"data": mine[(page - 1) * size: page * size],
                     "pagination": {"page": page, "pageSize": size, "total": len(mine)}}


def _accounts(*ids: int):
    def get(url: str, token: str) -> tuple[int, object]:
        return 200, {"userId": 1, "accounts": [
            {"accountId": ident, "accountName": f"Account {ident}", "accountType": "publisher"} for ident in ids
        ]}
    return get


def _run(folder: Path, awin: _Awin, *, env: dict | None = None, get=None) -> tuple[int, str]:
    saved = {key: os.environ.get(key) for key in ("AWIN_API_TOKEN", "AWIN_PUBLISHER_ID")}
    for key in saved:
        os.environ.pop(key, None)
    os.environ.update(env if env is not None else {"AWIN_API_TOKEN": TOKEN, "AWIN_PUBLISHER_ID": "555777"})
    out = io.StringIO()
    original = fetch.time.sleep
    fetch.time.sleep = lambda _seconds: None
    try:
        with redirect_stdout(out):
            code = fetch.main(
                ["--feed-cache-dir", str(folder), "--out", str(folder / "offers" / "offers.json")],
                post=awin, get=get or _accounts(555777), now=NOW,
            )
    finally:
        fetch.time.sleep = original
        for key, value in saved.items():
            os.environ.pop(key, None)
            if value is not None:
                os.environ[key] = value
    return code, out.getvalue()


SHOPS = [("101", "Fixturon Store"), ("101", "Fixturon Store"), ("202", "Testline UK"), ("303", "Sampleware")]


class FetchOffersTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = Path(tempfile.mkdtemp())
        _feed(self.folder, SHOPS)
        self.offers = [
            _offer(1, 101, "Fixturon Store", joined=True, code="FIXCODE10"),
            _offer(2, 101, "Fixturon Store", joined=True, kind="promotion"),
            _offer(3, 202, "Testline UK"),
            _offer(4, 202, "Testline UK", end="2026-10-30T00:00:00"),   # ended
            _offer(5, 202, "Testline UK", start="2026-11-20T00:00:00"),  # not begun
            _offer(6, 999, "Not PicWise's shop"),
        ]

    def _document(self) -> dict:
        return json.loads((self.folder / "offers" / "offers.json").read_text(encoding="utf-8"))

    def test_only_picwise_s_shops_are_asked_for(self) -> None:
        awin = _Awin(self.offers)
        code, _out = _run(self.folder, awin)
        self.assertEqual(code, 0)
        filters = awin.bodies[0]["filters"]
        self.assertEqual(filters["advertiserIds"], [101, 202, 303])
        self.assertEqual(filters["regionCodes"], ["GB"])
        self.assertEqual(filters["status"], "active")
        self.assertEqual(filters["membership"], "all")

    def test_only_offers_live_now_by_their_own_dates_are_kept(self) -> None:
        _run(self.folder, _Awin(self.offers))
        document = self._document()
        self.assertEqual(document["shops_in_feed"], 3)
        self.assertEqual(sorted(document["shops"]), ["101", "202"])
        self.assertEqual([offer["id"] for offer in document["shops"]["202"]["offers"]], [3])
        self.assertEqual(document["fetched_at"], NOW.isoformat())

    def test_a_code_and_a_link_only_where_awin_gives_them(self) -> None:
        _run(self.folder, _Awin(self.offers))
        shops = self._document()["shops"]
        fixturon = shops["101"]
        self.assertTrue(fixturon["joined"])
        voucher = next(offer for offer in fixturon["offers"] if offer["id"] == 1)
        self.assertEqual(voucher["code"], "FIXCODE10")
        self.assertEqual(voucher["url"], "https://fixture.example.invalid/track?offer=1")
        testline = shops["202"]
        self.assertFalse(testline["joined"])
        self.assertNotIn("code", testline["offers"][0])
        self.assertNotIn("url", testline["offers"][0])

    def test_the_printed_lines_carry_counts_only(self) -> None:
        code, out = _run(self.folder, _Awin(self.offers))
        self.assertEqual(code, 0)
        self.assertIn("offers: 3 live, of 2 of the 3 shops in the feed (joined to 1 of them); with a voucher code: 1", out)
        self.assertIn("Fixturon Store  (joined)", out)
        for hidden in ("FIXCODE10", "Fictional offer", TOKEN, "555777"):
            self.assertNotIn(hidden, out)

    def test_many_offers_are_read_page_by_page_each_once(self) -> None:
        many = [_offer(1000 + index, 303, "Sampleware") for index in range(fetch.PAGE_SIZE + 5)]
        awin = _Awin(many)
        code, _out = _run(self.folder, awin)
        self.assertEqual(code, 0)
        self.assertEqual([body["pagination"]["page"] for body in awin.bodies], [1, 2])
        self.assertEqual(len(self._document()["shops"]["303"]["offers"]), fetch.PAGE_SIZE + 5)

    def test_shops_are_asked_for_in_groups(self) -> None:
        rows = [(str(1000 + index), f"Shop {index}") for index in range(fetch.IDS_PER_CALL + 3)]
        _feed(self.folder, rows, name="picwise_awin_feed_newer.bin")
        newer = self.folder / "picwise_awin_feed_newer.bin"
        os.utime(newer, (newer.stat().st_atime, newer.stat().st_mtime + 100))
        awin = _Awin([])
        code, _out = _run(self.folder, awin)
        self.assertEqual(code, 0)
        self.assertEqual([len(body["filters"]["advertiserIds"]) for body in awin.bodies], [fetch.IDS_PER_CALL, 3])

    def test_the_account_is_found_from_the_token_when_its_number_is_not_set(self) -> None:
        awin = _Awin(self.offers)
        code, out = _run(self.folder, awin, env={"AWIN_API_TOKEN": TOKEN}, get=_accounts(424242))
        self.assertEqual(code, 0)
        self.assertNotIn("424242", out)
        code, out = _run(self.folder, _Awin(self.offers), env={"AWIN_API_TOKEN": TOKEN}, get=_accounts(1, 2))
        self.assertEqual(code, 1)
        self.assertIn("set AWIN_PUBLISHER_ID", out)

    def test_a_failed_read_keeps_the_last_file(self) -> None:
        _run(self.folder, _Awin(self.offers))
        before = (self.folder / "offers" / "offers.json").read_text(encoding="utf-8")
        code, out = _run(self.folder, _Awin(self.offers, status=401))
        self.assertEqual(code, 1)
        self.assertIn("offers: not fetched (Awin's offers call answered 401); the last file kept", out)
        self.assertNotIn(TOKEN, out)
        self.assertEqual((self.folder / "offers" / "offers.json").read_text(encoding="utf-8"), before)

    def test_no_token_fetches_nothing_and_fails_nothing(self) -> None:
        awin = _Awin(self.offers)
        code, out = _run(self.folder, awin, env={})
        self.assertEqual(code, 0)
        self.assertEqual(awin.bodies, [])
        self.assertIn("offers: no Awin token in the server's secrets; nothing fetched", out)

    def test_no_downloaded_feed_says_so(self) -> None:
        empty = Path(tempfile.mkdtemp())
        code, out = _run(empty, _Awin(self.offers))
        self.assertEqual(code, 1)
        self.assertIn("offers: no downloaded feed to read PicWise's shops from", out)


class OffersDeploymentTests(unittest.TestCase):
    def test_the_service_and_its_timer_are_installed_and_run_once_by_the_deployment(self) -> None:
        deploy = (ROOT / "deployment" / "server" / "deploy.sh").read_text(encoding="utf-8")
        self.assertIn("picwise-offers.service picwise-offers.timer; do", deploy)
        self.assertIn("systemctl start picwise-offers.service ||", deploy)
        self.assertIn("systemctl enable --now picwise-offers.timer", deploy)
        self.assertIn('"$SHARED/offers"', deploy)
        service = (ROOT / "deployment" / "server" / "picwise-offers.service").read_text(encoding="utf-8")
        self.assertIn("EnvironmentFile=-/etc/picwise/picwise.env", service)
        self.assertIn("ExecStart=/usr/bin/python3 deployment/server/fetch_offers.py", service)
        self.assertIn("After=network-online.target picwise-prepare.service", service)
        self.assertIn("ReadWritePaths=/srv/picwise/shared", service)
        timer = (ROOT / "deployment" / "server" / "picwise-offers.timer").read_text(encoding="utf-8")
        self.assertIn("OnCalendar=*-*-* 05:05:00 UTC", timer)
        # The site is never given the token: only the services that need a secret read the file.
        web = (ROOT / "deployment" / "server" / "picwise-web.service").read_text(encoding="utf-8")
        self.assertNotIn("EnvironmentFile", web)

    def test_the_deployment_writes_the_token_from_github_s_secrets(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "server-deploy.yml").read_text(encoding="utf-8")
        self.assertIn("AWIN_API_TOKEN: ${{ secrets.AWIN_API_TOKEN }}", workflow)
        self.assertIn("""printf "AWIN_API_TOKEN='%s'\\n" "$token\"""", workflow)
        self.assertIn('echo "Awin token: sent"', workflow)


if __name__ == "__main__":
    unittest.main()
