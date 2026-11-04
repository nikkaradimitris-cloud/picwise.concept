"""The live site's photos and offers, read as a visitor's browser reads them (read-only).

The owner, 2026-11-01, of a search on picwise.subby.cloud: «έχω παρατηρήσει ότι και σε
άλλα προϊόντα η εικόνα είναι χαλασμένη», and «το recommended όταν υπάρχει προσφορά πρέπει
να δείχνει την προσφορά». The session that wrote this cannot reach the site or the shops'
image hosts; GitHub's runner can.

For each search: the page's cards (role, price, shop, title, offer), then each card's photo
fetched as a browser on the site fetches it: an http:// address over https (browsers move
a photo to https, and block it when it is not there), with the site as Referer. A photo
that fails is fetched again without a Referer, to tell a dead link from one a shop refuses
to other sites. Printed: per search, its cards; then, per shop and per image host, how many
photos load and why the others do not, with a few examples.

Nothing changes anywhere: it only reads public pages and public product photos.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import unicodedata
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

# The searches the deployment prints, then searches that reach the shops whose offers
# remain after 2026-11-01 (Gardenista, Game Over, Ready Steady Bed, Cottsbury, Finediam,
# Optimum Nutrition), and bags, where the owner saw a broken photo.
SEARCHES = (
    "tv", "laptop", "headphones", "kettle", "mouse", "keyboard", "phone charger", "camera",
    "speaker", "smartwatch", "vacuum cleaner",
    "bean bag", "bean bag chair", "gaming bean bag", "garden cushion", "cushion cover",
    "outdoor cushion", "garden furniture", "pillow", "duvet cover", "bedding",
    "diamond necklace", "diamond earrings", "protein powder", "creatine", "bag", "craft bag",
    # Owner, 2026-11-03: «Στα tablets .. tablet... Βγάζει και χάπια».
    "tablet", "tablets", "ipad", "android tablet", "vitamin tablets",
)
# What the search box suggests as these are typed (owner, 2026-11-03: «έλεγξε αν υπάρχουν
# προτάσεις κατά την πληκτρολόγηση»), matched as the box matches them.
TYPED = ("ta", "tab", "tabl", "ke", "lap", "hea", "mou", "be", "ga", "κα", "βρ", "ακ")
SHOWN = 12
BROWSER = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0.0.0 Safari/537.36"
)
TIMEOUT = 12
EXAMPLES = 3

_CARD = re.compile(r'<article class="pw-card([^"]*)" data-choice-id="[^"]*">(.*?)</article>', re.S)


@dataclass
class Card:
    search: str
    recommended: bool
    role: str
    price: str
    shop: str
    title: str
    offer: str
    image: str


@dataclass
class Photo:
    url: str
    ok: bool = False
    why: str = ""
    without_referer: str = ""
    cards: list[Card] = field(default_factory=list)


def _text(fragment: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def _first(pattern: str, text: str) -> str:
    found = re.search(pattern, text, re.S)
    return _text(found.group(1)) if found else ""


def page_cards(search: str, page: str) -> list[Card]:
    """The cards of a search page, in order."""
    cards = []
    for match in _CARD.finditer(page):
        classes, inner = match.groups()
        image = re.search(r'<img class="pw-product-image" src="([^"]*)"', inner)
        cards.append(Card(
            search=search,
            recommended="recommended" in classes,
            role=_first(r'class="pw-role-label">(.*?)</p>', inner),
            price=_first(r'class="pw-price">(.*?)</p>', inner),
            shop=_first(r'class="pw-card-shop">(.*?)</p>', inner).removesuffix(" via Awin"),
            title=_first(r'class="pw-card-title">(.*?)</h2>', inner),
            offer=_first(r'<div class="pw-card-offer">(.*?)</div>', inner),
            image=html.unescape(image.group(1)) if image else "",
        ))
    return cards


def browser_address(url: str) -> str:
    """Where a browser on an https page fetches a photo: an http:// one over https."""
    return "https://" + url[len("http://"):] if url.lower().startswith("http://") else url


def image_kind(head: bytes) -> str:
    """The picture format the first bytes name, or "" when they are not a picture."""
    if head.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if head[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    if head[4:12] in (b"ftypavif", b"ftypavis"):
        return "avif"
    if head.lstrip()[:5].lower() in (b"<?xml", b"<svg ") and b"<svg" in head[:2048].lower():
        return "svg"
    return ""


def fetch_photo(url: str, *, referer: str) -> str:
    """"" when the photo loads as a browser would show it, else why not."""
    headers = {"User-Agent": BROWSER, "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8"}
    if referer:
        headers["Referer"] = referer
    request = urllib.request.Request(browser_address(url), headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            head = response.read(65536)
            final = response.geturl()
            kind = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
    except urllib.error.HTTPError as error:
        return f"HTTP {error.code}"
    except urllib.error.URLError as error:
        reason = error.reason
        name = type(reason).__name__ if not isinstance(reason, str) else reason
        return f"no answer ({str(name)[:40]})"
    except Exception as error:  # a diagnosis: every failure is reported, none stops it
        return f"no answer ({type(error).__name__})"
    if final.lower().startswith("http://"):
        return "sent on to an http:// address"
    if not head:
        return "empty"
    if not image_kind(head):
        return f"not a picture ({kind or 'no type'})"
    return ""


def box_key(text: str) -> str:
    """The box's own `norm`: no accents, lower case, final sigma as sigma, one space."""
    decomposed = unicodedata.normalize("NFD", str(text or ""))
    plain = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", plain.lower().replace("\u03c2", "\u03c3"))


def box_suggestions(words: list[str], typed: str, limit: int = 8) -> list[str]:
    """What the box lists for `typed`: names starting with it first, then names with a
    word starting with it, eight at most (`reference.py`, `update`)."""
    q = box_key(typed).lstrip(" ")
    if not q.strip():
        return []
    starts: list[int] = []
    inner: list[int] = []
    for index, word in enumerate(words):
        if len(starts) >= limit:
            break
        key = box_key(word)
        if key.startswith(q):
            starts.append(index)
        elif len(inner) < limit and (" " + q) in key:
            inner.append(index)
    return [words[index] for index in (starts + inner)[:limit]]


def host(url: str) -> str:
    return urllib.parse.urlsplit(url).netloc.lower() or "-"


def _get(url: str) -> tuple[int, str]:
    request = urllib.request.Request(url, headers={"User-Agent": BROWSER})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as error:
        return error.code, ""
    except Exception as error:
        print(f"  could not read: {type(error).__name__}")
        return 0, ""


def summary(photos: dict[str, Photo]) -> list[str]:
    """Per shop, then per image host: photos that load, and why the others do not."""
    lines = []
    for label, key in (("shop", lambda card, photo: card.shop or "-"), ("image host", lambda card, photo: host(photo.url))):
        groups: dict[str, list[Photo]] = defaultdict(list)
        for photo in photos.values():
            for name in {key(card, photo) for card in photo.cards}:
                groups[name].append(photo)
        lines.append(f"== per {label}: photos that load (each photo once)")
        for name, own in sorted(groups.items(), key=lambda item: (-sum(not p.ok for p in item[1]), item[0])):
            failed = [photo for photo in own if not photo.ok]
            reasons = Counter(photo.why for photo in failed)
            line = f"  {name[:40]:40} {len(own) - len(failed):>3} of {len(own):>3} load"
            if failed:
                line += "; failed: " + ", ".join(f"{why} x{count}" for why, count in reasons.most_common())
                without = Counter("loads without a Referer" if not p.without_referer else p.without_referer for p in failed)
                line += " | again without a Referer: " + ", ".join(f"{why} x{count}" for why, count in without.most_common())
            lines.append(line)
    failed = [photo for photo in photos.values() if not photo.ok]
    lines.append(f"== examples of photos that fail (of {len(failed)})")
    shown: Counter[str] = Counter()
    for photo in failed:
        name = photo.cards[0].shop or "-"
        if shown[name] >= EXAMPLES:
            continue
        shown[name] += 1
        address = photo.url if len(photo.url) <= 110 else photo.url[:107] + "..."
        lines.append(f"  {name[:28]:28} | {photo.why:28} | {address}")
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--site", default="https://picwise.subby.cloud")
    args = parser.parse_args(argv)
    site = args.site.rstrip("/")
    referer = site + "/"
    photos: dict[str, Photo] = {}
    for search in SEARCHES:
        query = urllib.parse.urlencode({"q": search, "shown": str(SHOWN)})
        status, page = _get(f"{site}/search?{query}")
        cards = page_cards(search, page)
        line = _first(r'<p class="pw-query-line">(.*?)</p>', page)
        counter = _first(r'<p class="pw-counter">(.*?)</p>', page)
        print(f"=== {search}: {status}, {counter or 'no counter'}, {len(cards)} cards read | {line}")
        if "The Recommended is on offer" in page:
            print("  the page says: the Recommended is on offer")
        for card in cards:
            mark = "*" if card.recommended else " "
            offer = f" | offer: {card.offer[:70]}" if card.offer else ""
            print(f"  {mark} {card.role[:28]:28} | {card.price:>10} | {card.shop[:24]:24} | {card.title[:60]}{offer}")
            if card.image:
                photos.setdefault(card.image, Photo(card.image)).cards.append(card)
    with ThreadPoolExecutor(max_workers=8) as pool:
        for photo, why in zip(photos.values(), pool.map(lambda p: fetch_photo(p.url, referer=referer), photos.values())):
            photo.ok, photo.why = not why, why
        failed = [photo for photo in photos.values() if not photo.ok]
        for photo, why in zip(failed, pool.map(lambda p: fetch_photo(p.url, referer=""), failed)):
            photo.without_referer = why
    status, body = _get(f"{site}/suggest.json")
    try:
        words = [str(word) for word in json.loads(body).get("suggestions", [])]
    except (ValueError, AttributeError):
        words = []
    print(f"== the search box's suggestions: {status}, {len(words)} names")
    for typed in TYPED:
        print(f"  {typed!r:8} -> {box_suggestions(words, typed)}")
    plain = sum(1 for url in photos if url.lower().startswith("http://"))
    print(f"== {len(photos)} photos on the pages read ({plain} given as http://); "
          f"{sum(p.ok for p in photos.values())} load, {sum(not p.ok for p in photos.values())} do not")
    for line in summary(photos):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
