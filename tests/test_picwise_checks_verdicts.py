"""The verdicts of the checks' rules, section 5, and the brakes of section 7.

Each row of the rules' tables (`docs/PICWISE_CHECKS_RULES.md`) is a test named after its
section: the page (5.1), stock (5.2), price (5.3 and 7.5), the photo (5.4), the shop (5.6),
and the brakes (7.1 to 7.6) with their numbers. Code without a network: what a shop's
answer means is decided here, never by the bot (rules 14).

Every row is local test data: fictional shops and brands, `.invalid` hosts.
"""
from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_checks import brakes  # noqa: E402
from picwise_checks.page_reader import NOTHING, Offer, PageRead  # noqa: E402
from picwise_checks.verdicts import (  # noqa: E402
    ANOTHER_PRODUCT, ANOTHER_SITE, BY_ADDRESS, BY_CODE, BY_VARIANT, FAILED, GONE, ID_SHARED, MOVED, NO_ANSWER,
    NOT_A_PRODUCT_PAGE, NOT_CHECKED, NOT_READ, NOT_UNDERSTOOD, PASSED, PRICE_FAR_APART, REFUSED, TIE_CODE,
    TIE_ONE_PRICE, TIE_VARIANT, PageAnswer, Row, ShopNight, awin_out, feed_is_old, page_verdict, photo_verdict,
    photos_refused, price_verdict, shop_checkable, shop_reads_pages, stock_reading, tie,
)

ADDRESS = "https://shop.invalid/products/zentra-kettle?variant=111"
ROW = Row(key="Shop\x1f1", shop="Shop", product_id="1", address=ADDRESS, title="Zentra Kettle 1.7L White",
          price=24.99, gtin="05012345678900", skus=frozenset({"ZK-17"}), handle="zentra-kettle", variant="111")
READ = PageRead(how="json-ld", name="Zentra Kettle 1.7L White",
                offers=(Offer(price=24.99, currency="GBP", availability="instock", sku="ZK-17", gtin="05012345678900"),),
                gtins=frozenset({"05012345678900"}), skus=frozenset({"ZK-17"}))


def _ok(**changes) -> PageAnswer:
    return PageAnswer(**{"status": 200, "final_url": ADDRESS, "read": READ, **changes})


class Rules51ThePageTests(unittest.TestCase):
    def verdict(self, answer: PageAnswer, *, reads: bool = True, row: Row = ROW, shared: bool = False):
        return page_verdict(row, answer, shop_reads_pages=reads, shared_id=shared)

    def test_200_with_the_product_read_on_it_passes(self) -> None:
        self.assertEqual(self.verdict(_ok()).state, PASSED)
        self.assertEqual(self.verdict(_ok()).by, BY_CODE)

    def test_found_in_a_shopify_catalogue_read_that_night_passes(self) -> None:
        shopify = PageRead(how="shopify", offers=(Offer(price=24.99, variant="111", availability="instock"),))
        verdict = self.verdict(PageAnswer(in_catalogue=True, read=shopify))
        self.assertEqual((verdict.state, verdict.by), (PASSED, BY_VARIANT))
        bare = self.verdict(PageAnswer(in_catalogue=True, read=shopify), row=Row(key="k", shop="Shop", product_id="1",
                                                                                 address="https://shop.invalid/p"))
        self.assertEqual(bare.by, BY_ADDRESS)

    def test_404_and_410_are_gone(self) -> None:
        for status in (404, 410):
            with self.subTest(status=status):
                self.assertEqual(self.verdict(PageAnswer(status=status)).reason, GONE)

    def test_nothing_or_a_5xx_is_no_answer(self) -> None:
        for answer in (PageAnswer(status=0, error="timeout"), PageAnswer(status=500), PageAnswer(status=503)):
            with self.subTest(answer=answer):
                verdict = self.verdict(answer)
                self.assertEqual((verdict.state, verdict.reason), (FAILED, NO_ANSWER))

    def test_a_redirect_to_a_page_with_no_product_is_moved(self) -> None:
        for final in ("https://shop.invalid/", "https://shop.invalid/collections/kettles", "https://shop.invalid/search?q=k"):
            with self.subTest(final=final):
                verdict = self.verdict(PageAnswer(status=200, final_url=final, redirected=True, read=NOTHING))
                self.assertEqual((verdict.state, verdict.reason), (FAILED, MOVED))

    def test_a_redirect_to_another_product_whose_codes_differ_is_moved(self) -> None:
        other = PageRead(how="json-ld", name="Zentra Kettle 1.7L White",
                         offers=(Offer(price=30.0, gtin="05099999999999"),), gtins=frozenset({"05099999999999"}))
        verdict = self.verdict(PageAnswer(status=200, final_url="https://shop.invalid/products/other", redirected=True,
                                          read=other))
        self.assertEqual(verdict.reason, MOVED)

    def test_a_redirect_with_no_codes_is_moved_only_when_the_title_is_not_alike(self) -> None:
        row = Row(key="k", shop="Shop", product_id="1", address="https://shop.invalid/p/a", title="Orla Toaster 2 Slice")
        alike = PageRead(how="json-ld", name="Orla Toaster 2 Slice Black", offers=(Offer(price=20.0),))
        unlike = PageRead(how="json-ld", name="Garden Hose 30m", offers=(Offer(price=20.0),))
        moved = "https://shop.invalid/p/b"
        self.assertEqual(self.verdict(PageAnswer(status=200, final_url=moved, redirected=True, read=alike), row=row).state,
                         PASSED)
        self.assertEqual(self.verdict(PageAnswer(status=200, final_url=moved, redirected=True, read=unlike), row=row).reason,
                         MOVED)

    def test_a_redirect_to_another_address_of_the_same_product_passes(self) -> None:
        renamed = self.verdict(_ok(final_url="https://shop.invalid/products/zentra-kettle-white", redirected=True))
        self.assertEqual((renamed.state, renamed.by), (PASSED, BY_CODE))
        # The same page reached through a collection, with "www." and a slash, is no redirect at all.
        through_collection = self.verdict(_ok(final_url="https://www.shop.invalid/collections/k/products/zentra-kettle/",
                                              redirected=True))
        self.assertEqual((through_collection.state, through_collection.by), (PASSED, BY_CODE))

    def test_200_with_no_product_is_not_a_product_page_only_where_the_reader_reads_the_shop(self) -> None:
        self.assertEqual(self.verdict(_ok(read=NOTHING), reads=True).reason, NOT_A_PRODUCT_PAGE)
        unread = self.verdict(_ok(read=NOTHING), reads=False)
        self.assertEqual((unread.state, unread.reason), (NOT_CHECKED, NOT_READ))

    def test_a_page_whose_every_variant_has_another_gtin_is_another_product(self) -> None:
        other = PageRead(how="json-ld", name="Zentra Kettle", offers=(Offer(price=24.99, gtin="05000000000017"),
                                                                     Offer(price=24.99, gtin="05000000000024")))
        self.assertEqual(self.verdict(_ok(read=other)).reason, ANOTHER_PRODUCT)
        some_without = PageRead(how="json-ld", name="Zentra Kettle", offers=(Offer(price=24.99, gtin="05000000000017"),
                                                                            Offer(price=24.99)))
        self.assertEqual(self.verdict(_ok(read=some_without)).state, PASSED)

    def test_an_id_another_product_shares_fails_on_our_own_side(self) -> None:
        self.assertEqual(self.verdict(_ok(), shared=True).reason, ID_SHARED)

    def test_a_refusal_a_challenge_or_another_site_is_not_checked(self) -> None:
        for answer, reason in ((PageAnswer(status=401), REFUSED), (PageAnswer(status=403), REFUSED),
                               (PageAnswer(status=429), REFUSED), (PageAnswer(status=200, challenge=True), REFUSED),
                               (PageAnswer(status=0, elsewhere=True), ANOTHER_SITE),
                               (PageAnswer(status=400), NOT_UNDERSTOOD)):
            with self.subTest(answer=answer):
                verdict = self.verdict(answer)
                self.assertEqual((verdict.state, verdict.reason), (NOT_CHECKED, reason))

    def test_a_title_alone_never_fails_a_product_at_its_own_address(self) -> None:
        unlike = PageRead(how="json-ld", name="Completely Different Words", offers=(Offer(price=24.99),))
        row = Row(key="k", shop="Shop", product_id="1", address=ADDRESS, title="Zentra Kettle 1.7L White")
        verdict = self.verdict(_ok(read=unlike), row=row)
        self.assertEqual((verdict.state, verdict.by), (PASSED, BY_ADDRESS))


class Rules53PriceTests(unittest.TestCase):
    def test_tied_by_the_variant_its_address_names(self) -> None:
        read = PageRead(how="shopify", offers=(Offer(price=10.0, variant="110"), Offer(price=12.0, variant="111")))
        offer, how = tie(ROW, read, feed_rows_one_price=False)
        self.assertEqual((offer.price, how), (12.0, TIE_VARIANT))

    def test_tied_by_a_code(self) -> None:
        row = Row(key="k", shop="S", product_id="1", address="https://shop.invalid/p", skus=frozenset({"zk-17"}))
        read = PageRead(how="json-ld", offers=(Offer(price=9.0, sku="XX"), Offer(price=11.0, sku="ZK17")))
        offer, how = tie(row, read, feed_rows_one_price=False)
        self.assertEqual((offer.price, how), (11.0, TIE_CODE))

    def test_one_price_ties_only_when_the_feed_has_one_row_or_one_price_for_the_address(self) -> None:
        row = Row(key="k", shop="S", product_id="1", address="https://shop.invalid/p")
        read = PageRead(how="json-ld", offers=(Offer(price=15.0), Offer(price=15.0)))
        self.assertEqual(tie(row, read, feed_rows_one_price=True)[1], TIE_ONE_PRICE)
        self.assertEqual(tie(row, read, feed_rows_one_price=False), (None, ""))

    def test_a_reading_not_tied_changes_nothing(self) -> None:
        row = Row(key="k", shop="S", product_id="1", address="https://shop.invalid/p", price=84.99)
        sizes = PageRead(how="json-ld", offers=(Offer(price=54.99), Offer(price=84.99)))
        self.assertEqual(tie(row, sizes, feed_rows_one_price=True), (None, ""))
        self.assertIsNone(price_verdict(row, None))

    def test_pounds_only(self) -> None:
        row = Row(key="k", shop="S", product_id="1", address="https://shop.invalid/p")
        euros = PageRead(how="json-ld", offers=(Offer(price=15.0, currency="EUR"),))
        self.assertEqual(tie(row, euros, feed_rows_one_price=True), (None, ""))

    def test_rules_7_5_a_price_under_half_or_over_twice_is_far_apart(self) -> None:
        for site, state in ((12.0, FAILED), (12.5, PASSED), (49.98, PASSED), (50.0, FAILED), (26.99, PASSED)):
            with self.subTest(site=site):
                verdict = price_verdict(ROW, Offer(price=site))
                self.assertEqual(verdict.state, state)
                if state == FAILED:
                    self.assertEqual(verdict.reason, PRICE_FAR_APART)


class Rules52StockTests(unittest.TestCase):
    def test_the_tied_offers_word(self) -> None:
        self.assertEqual(stock_reading(ROW, READ, Offer(price=1.0, availability="outofstock")), "sold out")
        self.assertEqual(stock_reading(ROW, READ, Offer(price=1.0, availability="preorder")), "sold out")

    def test_with_no_variant_named_sold_out_only_when_every_offer_says_so(self) -> None:
        row = Row(key="k", shop="S", product_id="1", address="https://shop.invalid/p")
        mixed = PageRead(how="json-ld", offers=(Offer(price=1.0, availability="outofstock"),
                                                Offer(price=1.0, availability="instock")))
        gone = PageRead(how="json-ld", offers=(Offer(price=1.0, availability="outofstock"),
                                               Offer(price=1.0, availability="soldout")))
        self.assertEqual(stock_reading(row, mixed, None), "in stock")
        self.assertEqual(stock_reading(row, gone, None), "sold out")
        self.assertEqual(stock_reading(ROW, gone, None), "")


class Rules54PhotoTests(unittest.TestCase):
    def test_any_failure_fails_that_night(self) -> None:
        for status, kind, length, state in ((200, "image/jpeg", 1234, PASSED), (200, "", None, PASSED),
                                            (200, "text/html", 900, FAILED), (200, "image/png", 0, FAILED),
                                            (404, "", None, FAILED), (410, "", None, FAILED), (0, "", None, FAILED),
                                            (503, "", None, FAILED), (403, "", None, FAILED), (400, "", None, FAILED),
                                            (429, "", None, NOT_CHECKED)):
            with self.subTest(status=status, kind=kind):
                self.assertEqual(photo_verdict(status, kind, length).state, state)

    def test_a_photo_host_that_refuses_nine_in_ten_of_twenty(self) -> None:
        self.assertTrue(photos_refused(20, 18))
        self.assertFalse(photos_refused(20, 17))
        self.assertFalse(photos_refused(19, 19))


class Rules56ShopTests(unittest.TestCase):
    def test_a_shop_that_cannot_be_checked(self) -> None:
        cases = (
            (ShopNight(own_address=False), "no address of its own"),
            (ShopNight(robots="disallowed"), "robots.txt disallows its product pages"),
            (ShopNight(robots="refused"), "robots.txt refused"),
            (ShopNight(crawl_delay=61), "crawl-delay over 60 s"),
            (ShopNight(requests=10, refused=9), "refuses the bot"),
            (ShopNight(requests=20, pages_200=10, pages_read=1), "its pages are not read"),
        )
        for night, why in cases:
            with self.subTest(why=why):
                self.assertEqual(shop_checkable(night), (False, why))

    def test_a_shop_that_can_be_checked(self) -> None:
        for night in (ShopNight(requests=10, refused=8), ShopNight(crawl_delay=60), ShopNight(catalogue_read=True),
                      ShopNight(requests=20, pages_200=10, pages_read=2), ShopNight(requests=9, pages_200=9)):
            with self.subTest(night=night):
                self.assertEqual(shop_checkable(night), (True, ""))

    def test_rules_5_1_the_reader_reads_the_shop_at_nine_in_ten(self) -> None:
        self.assertTrue(shop_reads_pages(10, 9))
        self.assertFalse(shop_reads_pages(10, 8))
        self.assertFalse(shop_reads_pages(9, 9))

    def test_awin(self) -> None:
        self.assertEqual(awin_out("joined"), "")
        self.assertEqual(awin_out("notjoined"), "")
        self.assertEqual(awin_out("pending"), "")
        self.assertEqual(awin_out("rejected"), "Awin: rejected")
        self.assertEqual(awin_out("suspended"), "Awin: suspended")
        self.assertEqual(awin_out(None), "Awin: in no list")
        self.assertEqual(awin_out("joined", "offline"), "Awin: offline")

    def test_rules_5_6_4_a_feed_over_seven_days_old(self) -> None:
        today = date(2026, 11, 30)
        self.assertFalse(feed_is_old(date(2026, 11, 23), today))
        self.assertTrue(feed_is_old(date(2026, 11, 22), today))
        self.assertFalse(feed_is_old(None, today))


class Rules7BrakesTests(unittest.TestCase):
    def test_7_1_a_round_most_shops_did_not_answer_is_ours(self) -> None:
        self.assertTrue(brakes.round_is_ours(10, 4))
        self.assertFalse(brakes.round_is_ours(10, 5))
        self.assertFalse(brakes.round_is_ours(0, 0))

    def test_7_2_a_shops_night(self) -> None:
        self.assertEqual(brakes.shop_brake(20, 5, 20), brakes.NO_BRAKE)
        self.assertEqual(brakes.shop_brake(20, 6, 20), brakes.HOLD)
        self.assertEqual(brakes.shop_brake(20, 6, 19), brakes.HOLD_FOR_OWNER)
        self.assertEqual(brakes.shop_brake(19, 19, 100), brakes.NO_BRAKE)

    def test_7_3_a_kinds_night(self) -> None:
        self.assertTrue(brakes.kind_brake(40, 11))
        self.assertFalse(brakes.kind_brake(40, 10))
        self.assertFalse(brakes.kind_brake(39, 39))

    def test_7_4_the_whole_night(self) -> None:
        self.assertTrue(brakes.night_brake(6, 3, 0, 1000))
        self.assertFalse(brakes.night_brake(6, 2, 0, 1000))
        self.assertFalse(brakes.night_brake(5, 5, 0, 1000))
        self.assertTrue(brakes.night_brake(1, 0, 101, 1000))
        self.assertFalse(brakes.night_brake(1, 0, 100, 1000))
        self.assertTrue(brakes.cutting_stopped([False, True, True]))
        self.assertFalse(brakes.cutting_stopped([True, False, True]))

    def test_7_5_a_reader_proves_itself(self) -> None:
        self.assertTrue(brakes.reader_proven([(10, 7), (10, 7)]))
        self.assertFalse(brakes.reader_proven([(10, 7), (10, 6)]))
        self.assertFalse(brakes.reader_proven([(19, 19)]))
        # Only the last 7 nights count.
        self.assertFalse(brakes.reader_proven([(100, 100)] + [(1, 0)] * 7))
        self.assertEqual(brakes.commonest_ratio([(8.71, 7.99), (21.79, 19.99), (10.0, 10.0)]), 1.09)

    def test_5_6_3_a_reading_of_awin_that_puts_many_out_waits(self) -> None:
        self.assertFalse(brakes.awin_waits(3, 10, 1000))
        self.assertTrue(brakes.awin_waits(4, 10, 1000))
        self.assertTrue(brakes.awin_waits(1, 51, 1000))

    def test_7_6_the_ai_stops_at_ten_dollars_a_night(self) -> None:
        self.assertEqual(brakes.AI_NIGHT_STOP_DOLLARS, 10.0)


if __name__ == "__main__":
    unittest.main()
