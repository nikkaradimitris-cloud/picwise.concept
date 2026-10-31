"""The read-only check of the offers Awin gives PicWise's account.

`.github/scripts/awin_offers.py`, run by `.github/workflows/awin-offers.yml` (owner,
2026-10-31: «τις προσφορές στα καταστήματα πρέπει να τις τραβήξουμε»). Pinned here,
on answers written as Awin's documentation describes them (no token was at hand): every
page is read, the live UK offers of every advertiser asked for; the answer's shape is
printed without its values; the offers are counted by type, code and end date; PicWise's
shops are found among the advertisers by name; the token, the account's id and every
voucher code stay out of the log; missing secrets read nothing and fail nothing; a
refusal fails the run.

Every advertiser, shop and offer is fictional.
"""
from __future__ import annotations

import importlib.util
import io
import os
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".github" / "scripts" / "awin_offers.py"
_spec = importlib.util.spec_from_file_location("awin_offers", SCRIPT)
offers_check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(offers_check)

TOKEN = "tok-secret-0123456789"
PUBLISHER = "987654"
NOW = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)


def _offer(number: int, advertiser: tuple[int, str, bool], *, kind: str = "promotion", code: str = "",
           end: str = "2026-11-30T23:59:59Z") -> dict:
    ident, name, joined = advertiser
    offer = {
        "promotionId": number,
        "type": kind,
        "advertiser": {"id": ident, "name": name, "joined": joined},
        "title": f"Fictional offer {number}",
        "description": "Local test data.",
        "startDate": "2026-10-01T00:00:00Z",
        "endDate": end,
        "url": "https://fixture.example.invalid/offer",
    }
    if code:
        offer["voucher"] = {"code": code, "exclusive": True}
    return offer


FIXTURON = (101, "Fixturon Partner Program", True)
TESTLINE = (202, "Testline UK", False)
ELSEWHERE = (303, "Nowhere Shop Ltd", True)


class _Awin:
    """Answers POSTs page by page, recording what was asked."""

    def __init__(self, pages: list[list[dict]], status: int = 200) -> None:
        self.pages = pages
        self.status = status
        self.calls: list[tuple[str, dict, str]] = []

    def __call__(self, url: str, body: dict, token: str) -> tuple[int, object]:
        self.calls.append((url, body, token))
        if self.status != 200:
            return self.status, {"error": f"denied for {token}", "publisher": PUBLISHER}
        page = body["pagination"]["page"]
        items = self.pages[page - 1] if page <= len(self.pages) else []
        return 200, {"data": items, "pagination": {"page": page, "pageSize": body["pagination"]["pageSize"]}}


NOTE = {
    "prepared": True,
    "intake": {
        "shops": [
            {"shop": "Fixturon Partner Program", "rows": 900, "shown": 750},
            {"shop": "Testline", "rows": 40, "shown": 12},
            {"shop": "Sampleware", "rows": 10, "shown": 10},
        ]
    },
}


def _run(awin: _Awin, note: object = NOTE, env: dict | None = None) -> tuple[int, str]:
    saved = {key: os.environ.get(key) for key in ("AWIN_API_TOKEN", "AWIN_PUBLISHER_ID")}
    os.environ.update(env if env is not None else {"AWIN_API_TOKEN": TOKEN, "AWIN_PUBLISHER_ID": PUBLISHER})
    for key in ("AWIN_API_TOKEN", "AWIN_PUBLISHER_ID"):
        if env is not None and key not in env:
            os.environ.pop(key, None)
    out = io.StringIO()
    try:
        with redirect_stdout(out):
            original = offers_check.time.sleep
            offers_check.time.sleep = lambda _seconds: None
            try:
                code = offers_check.main([], post=awin, note=note)
            finally:
                offers_check.time.sleep = original
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    return code, out.getvalue()


class AwinOffersCheckTests(unittest.TestCase):
    def test_every_page_is_read_for_the_live_uk_offers_of_every_advertiser(self) -> None:
        full = [_offer(index, FIXTURON) for index in range(offers_check.PAGE_SIZE)]
        awin = _Awin([full, [_offer(9999, TESTLINE)]])
        code, out = _run(awin)
        self.assertEqual(code, 0)
        self.assertEqual(len(awin.calls), 2)
        url, body, token = awin.calls[0]
        self.assertEqual(url, f"https://api.awin.com/publisher/{PUBLISHER}/promotions")
        self.assertEqual(token, TOKEN)
        self.assertEqual(body["filters"]["membership"], "all")
        self.assertEqual(body["filters"]["regionCodes"], ["GB"])
        self.assertEqual(body["filters"]["status"], "active")
        self.assertEqual([call[1]["pagination"]["page"] for call in awin.calls], [1, 2])
        self.assertIn(f"== {offers_check.PAGE_SIZE + 1:,} live offers for the United Kingdom", out)

    def test_the_counts_and_the_shops_of_picwise_among_the_advertisers(self) -> None:
        awin = _Awin([[
            _offer(1, FIXTURON, kind="voucher", code="FIXCODE10"),
            _offer(2, FIXTURON, end="2026-11-03T00:00:00Z"),
            _offer(3, TESTLINE, kind="voucher", code="TESTCODE5"),
            _offer(4, ELSEWHERE, end=""),
        ]])
        report = "\n".join(offers_check.report(
            offers_check.read_offers(PUBLISHER, TOKEN, post=awin, pause=0)[0],
            None,
            offers_check.our_shops(NOTE),
            now=NOW,
        ))
        self.assertIn("by type: voucher 2, promotion 2", report)
        self.assertIn("with a voucher code: 2; ending within 7 days: 1; no end date: 1", report)
        self.assertIn("advertisers with an offer: 3", report)
        # "Fixturon Partner Program" is the shop's own name; "Testline UK" is Testline's.
        self.assertIn("== PicWise's shops with an offer: 2 of 3", report)
        self.assertIn("  Fixturon Partner Program (750 products shown): 2 offers, joined: yes", report)
        self.assertIn("  Testline (12 products shown): 1 offers, joined: no", report)
        self.assertNotIn("Nowhere Shop Ltd (", report)
        self.assertRegex(report, r"\n\s+1\s+Nowhere Shop Ltd\s+-\s+joined: yes")

    def test_the_shape_is_printed_without_the_values(self) -> None:
        code, out = _run(_Awin([[_offer(1, FIXTURON, kind="voucher", code="FIXCODE10")]]))
        self.assertEqual(code, 0)
        self.assertIn("the answer's shape: {data: [{", out)
        self.assertIn("an offer's shape: {promotionId: int, type: str, advertiser: {id: int, name: str, joined: bool}", out)
        self.assertIn("voucher: {code: str, exclusive: bool}", out)

    def test_no_secret_and_no_voucher_code_reaches_the_log(self) -> None:
        code, out = _run(_Awin([[_offer(1, FIXTURON, kind="voucher", code="FIXCODE10"),
                                 _offer(2, TESTLINE, kind="voucher", code="TESTCODE5")]]))
        self.assertEqual(code, 0)
        for secret in (TOKEN, PUBLISHER, "FIXCODE10", "TESTCODE5"):
            self.assertNotIn(secret, out)
        self.assertIn("code: yes", out)

    def test_a_refusal_fails_the_run_and_says_why_without_the_secrets(self) -> None:
        code, out = _run(_Awin([], status=401))
        self.assertEqual(code, 1)
        self.assertIn("the offers could not be read: Awin answered 401", out)
        self.assertNotIn(TOKEN, out)
        self.assertNotIn(PUBLISHER, out)

    def test_without_the_secrets_nothing_is_read_and_nothing_fails(self) -> None:
        awin = _Awin([[_offer(1, FIXTURON)]])
        code, out = _run(awin, env={})
        self.assertEqual(code, 0)
        self.assertEqual(awin.calls, [])
        self.assertIn("not in GitHub's secrets yet: AWIN_API_TOKEN, AWIN_PUBLISHER_ID; nothing read", out)

    def test_an_answer_kept_under_another_name_is_still_read(self) -> None:
        self.assertEqual(len(offers_check._items({"promotions": [_offer(1, FIXTURON)]})), 1)
        self.assertEqual(len(offers_check._items([_offer(1, FIXTURON)])), 1)
        self.assertEqual(offers_check._items({"unexpected": 1}), [])

    def test_no_shops_note_still_counts_the_offers(self) -> None:
        code, out = _run(_Awin([[_offer(1, FIXTURON)]]), note=None)
        self.assertEqual(code, 0)
        self.assertIn("== PicWise's shops with an offer: 0 of 0 (the shops could not be read)", out)

    def test_shop_names_compare_without_the_networks_words(self) -> None:
        self.assertEqual(offers_check.shop_key("Geepas Partner Program"), offers_check.shop_key("Geepas"))
        self.assertEqual(offers_check.shop_key("InStock UK"), offers_check.shop_key("Instock"))
        self.assertNotEqual(offers_check.shop_key("Fila UK"), offers_check.shop_key("Five Star Direct"))


class AwinOffersWorkflowTests(unittest.TestCase):
    def test_the_workflow_reads_only_and_passes_the_secrets_to_the_script_alone(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "awin-offers.yml").read_text(encoding="utf-8")
        self.assertIn("permissions:\n  contents: read", workflow)
        self.assertIn("AWIN_API_TOKEN: ${{ secrets.AWIN_API_TOKEN }}", workflow)
        self.assertIn("AWIN_PUBLISHER_ID: ${{ secrets.AWIN_PUBLISHER_ID }}", workflow)
        self.assertIn("python3 .github/scripts/awin_offers.py --shops-from https://picwise.subby.cloud/prepared.json", workflow)
        self.assertIn("branches: [ccr-1361f1a7-dcpo60]", workflow)
        self.assertNotIn("ssh", workflow)


if __name__ == "__main__":
    unittest.main()
