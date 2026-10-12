"""Which shop an offer comes from, named the same way whatever network delivered it.

Owner point (2026-10-12): a shop's reliability is a real criterion -- the third, after
the product's rating and its availability -- and Trustpilot can supply it. But that
shop will arrive through Awin today and through some other network tomorrow, or
directly. So the reliability of a shop must not live inside a feed.

It lives here instead, keyed on the shop's own **domain**, which is the one thing that
does not change with the network:

- Trustpilot's public Business Units API is itself keyed by domain, so the key PicWise
  stores is the key the lookup already needs.
- A shop joined through two networks is one shop, so it is rated once and not twice,
  and a second network's feed inherits every reliability fact already collected.
- A network's own name for a merchant does not: "Plusshop IE" and "Plusshop UK" are
  two rows and `ie.plusshop.com` and `uk.plusshop.com` two storefronts, while the
  merchant name alone would have merged or split them by accident.

The domain is read from the **merchant's own link**, never from the network's
redirect: `aw_deep_link` points at `awin1.com`, which is the network and not the shop.

Nothing here rates a shop. It says which shop an offer is from, so that a rating can
be attached to it later, and reports honestly when the feed does not say.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.parse import urlsplit

# The columns that carry the merchant's own URL, in the order they are trusted. A
# network redirect is never one of them.
MERCHANT_URL_KEYS = ("merchant_deep_link", "merchant_url", "product_url", "url", "link")
# Hosts belonging to affiliate networks rather than to shops. A URL on one of these
# names the network, so it cannot identify the shop.
NETWORK_HOSTS = (
    "awin1.com",
    "awin.com",
    "zenaps.com",
    "prf.hn",
    "tradedoubler.com",
    "clickserve.dartsearch.net",
    "anrdoezrs.net",
    "dpbolvw.net",
    "jdoqocy.com",
    "kqzyfj.com",
    "tkqlhce.com",
    "linksynergy.com",
    "webgains.com",
    "daisycon.io",
    "affilae.com",
    "partner-ads.com",
    "adtraction.com",
    "adservice.com",
    "impact.com",
    "go.skimresources.com",
    "shareasale.com",
)
_WWW_RE = re.compile(r"^www\d*\.")
# A shop on a marketplace's own subdomain is still that shop, but a bare marketplace
# host is not a shop PicWise can rate on its own behalf.
_SHOP_PLATFORM_SUFFIXES = (".myshopify.com",)


@dataclass(frozen=True)
class MerchantIdentity:
    """The shop an offer is from, and the key its reliability is stored under."""

    domain: str = ""
    name: str = ""
    network_key: str = ""

    @property
    def known(self) -> bool:
        """Did the feed say which shop this is, in a way that survives the network?"""
        return bool(self.domain)

    @property
    def reliability_key(self) -> str:
        """The key a shop's reliability is stored and looked up under."""
        return self.domain

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "name": self.name,
            "network_key": self.network_key,
            "known": self.known,
            "reliability_key": self.reliability_key,
        }


def _host_of(url: Any) -> str:
    text = " ".join(str(url or "").split())
    if not text:
        return ""
    if "//" not in text:
        text = f"//{text}"
    host = urlsplit(text).netloc.lower()
    host = host.split("@")[-1].split(":")[0]
    return _WWW_RE.sub("", host).strip(".")


def is_network_host(host: Any) -> bool:
    """Is this host an affiliate network's redirect rather than a shop?"""
    name = _host_of(host) if "/" in str(host or "") else str(host or "").strip().lower()
    name = _WWW_RE.sub("", name).strip(".")
    if not name:
        return False
    return any(name == known or name.endswith(f".{known}") for known in NETWORK_HOSTS)


def merchant_domain(row: Mapping[str, Any] | None) -> str:
    """The shop's own domain, or "" when the feed only gave a network redirect."""
    raw = row if isinstance(row, Mapping) else {}
    for key in MERCHANT_URL_KEYS:
        host = _host_of(raw.get(key))
        if host and not is_network_host(host):
            return host
    return ""


def read_merchant_identity(
    row: Mapping[str, Any] | None,
    *,
    name: str = "",
    network_key: str = "",
) -> MerchantIdentity:
    """Which shop this offer is from, independent of the network that delivered it."""
    raw = row if isinstance(row, Mapping) else {}
    shop_name = " ".join(str(name or raw.get("merchant_name") or "").split())
    return MerchantIdentity(
        domain=merchant_domain(raw),
        name=shop_name,
        network_key=" ".join(str(network_key or raw.get("provider_key") or "").split()),
    )


def is_shop_platform_domain(domain: Any) -> bool:
    """A shop hosted on a shop platform's own subdomain, such as `*.myshopify.com`.

    Still one shop and still ratable, but worth telling apart: the domain is the
    platform's, so a shop that later moves to its own name changes key, and the
    reliability collected under the old one has to move with it.
    """
    host = _WWW_RE.sub("", str(domain or "").strip().lower()).strip(".")
    return any(host.endswith(suffix) for suffix in _SHOP_PLATFORM_SUFFIXES)
