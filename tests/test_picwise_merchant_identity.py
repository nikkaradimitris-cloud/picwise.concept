"""Which shop an offer is from, named the same way whatever network delivered it.

Owner point, 2026-10-12: Trustpilot can supply a shop's reliability, but that shop
arrives through Awin today and through another network tomorrow, or directly. So the
identity a reliability score hangs on must survive the network, and the only thing
that does is the shop's own domain -- which is also the key Trustpilot's public
Business Units API is itself queried by.

These tests pin the three ways that goes wrong: reading the network's redirect instead
of the shop's link, merging two storefronts of one brand, and claiming to know a shop
when the feed only gave a redirect.

URLs here are the real shapes the first feed used, with local test hosts where a
fixture is needed.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = ROOT / "src"
for path in (HERE, ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from picwise_providers.merchant_identity import (  # noqa: E402
    is_network_host,
    is_shop_platform_domain,
    merchant_domain,
    read_merchant_identity,
)


class NetworkRedirectTests(unittest.TestCase):
    def test_the_networks_own_redirect_never_names_the_shop(self) -> None:
        # Every row of the real feed carries this, and it is the network, not the shop.
        for url in ("https://www.awin1.com/pclick.php?p=43439483005",
                    "https://www.awin1.com/cread.php?awinmid=1",
                    "https://prf.hn/click/camref:1/destination:x",
                    "https://click.linksynergy.com/deeplink?id=1"):
            with self.subTest(url=url):
                self.assertTrue(is_network_host(url))
                self.assertEqual(merchant_domain({"product_url": url}), "")

    def test_the_merchants_own_link_is_preferred_over_the_redirect(self) -> None:
        row = {
            "aw_deep_link": "https://www.awin1.com/pclick.php?p=43439483005",
            "merchant_deep_link": "https://boxed2me.co.uk/products/nedis-cable",
        }
        self.assertEqual(merchant_domain(row), "boxed2me.co.uk")

    def test_a_row_with_only_a_redirect_does_not_claim_to_know_the_shop(self) -> None:
        # Reporting a shop PicWise cannot name would misattribute every rating hung
        # on it, so the honest answer is that it does not know.
        identity = read_merchant_identity(
            {"aw_deep_link": "https://www.awin1.com/pclick.php?p=1",
             "merchant_name": "Some Shop"},
            network_key="awin",
        )
        self.assertFalse(identity.known)
        self.assertEqual(identity.reliability_key, "")
        self.assertEqual(identity.name, "Some Shop")

    def test_a_shop_host_is_not_a_network_host(self) -> None:
        for host in ("boxed2me.co.uk", "www.tooled-up.com", "cerqular.com"):
            with self.subTest(host=host):
                self.assertFalse(is_network_host(host))


class DomainAsTheKeyTests(unittest.TestCase):
    def test_the_same_shop_through_two_networks_is_one_key(self) -> None:
        # The point of keying on the domain: a second network's feed inherits every
        # reliability fact already collected, instead of starting the shop again.
        through_awin = read_merchant_identity(
            {"merchant_deep_link": "https://boxed2me.co.uk/products/x",
             "aw_deep_link": "https://www.awin1.com/pclick.php?p=1",
             "merchant_name": "Boxed2me"},
            network_key="awin",
        )
        through_another = read_merchant_identity(
            {"merchant_deep_link": "https://www.boxed2me.co.uk/products/y",
             "merchant_name": "Boxed 2 Me Ltd"},
            network_key="tradedoubler",
        )
        self.assertEqual(through_awin.reliability_key, through_another.reliability_key)
        self.assertNotEqual(through_awin.network_key, through_another.network_key)

    def test_two_storefronts_of_one_brand_stay_apart(self) -> None:
        # "Plusshop IE" and "Plusshop UK" are two shops with two reputations, and the
        # merchant name alone would have merged or split them by accident.
        ireland = merchant_domain({"merchant_deep_link": "https://ie.plusshop.com/p/1"})
        britain = merchant_domain({"merchant_deep_link": "https://uk.plusshop.com/p/1"})
        self.assertNotEqual(ireland, britain)
        self.assertEqual(ireland, "ie.plusshop.com")

    def test_www_and_a_port_do_not_change_the_key(self) -> None:
        for url in ("https://www.tooled-up.com/a", "https://tooled-up.com/a",
                    "https://www2.tooled-up.com/a", "https://tooled-up.com:443/a"):
            with self.subTest(url=url):
                self.assertEqual(merchant_domain({"merchant_deep_link": url}), "tooled-up.com")

    def test_a_shop_on_a_platform_subdomain_is_flagged(self) -> None:
        # Still one shop and still ratable, but its key belongs to the platform: if it
        # moves to its own name the reliability collected has to move with it.
        identity = read_merchant_identity(
            {"merchant_deep_link": "https://tluxyit.myshopify.com/products/a"}
        )
        self.assertEqual(identity.reliability_key, "tluxyit.myshopify.com")
        self.assertTrue(is_shop_platform_domain(identity.reliability_key))
        self.assertFalse(is_shop_platform_domain("boxed2me.co.uk"))


class EmptyInputTests(unittest.TestCase):
    def test_nothing_in_gives_nothing_claimed(self) -> None:
        for row in ({}, None, {"merchant_deep_link": ""}, {"merchant_deep_link": "   "}):
            with self.subTest(row=row):
                identity = read_merchant_identity(row)
                self.assertFalse(identity.known)
                self.assertEqual(identity.reliability_key, "")


if __name__ == "__main__":
    unittest.main()
