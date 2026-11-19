"""The aisle of Google's taxonomy an Awin-format row belongs to, read from its own words.

Owner, 2026-11-19: the Awin-format feeds come back, and the catalogue must fill its
categories evenly («να γεμίσουμε ομοιόμορφα τις κατηγορίες»), with the cap of 15% and a
most a category keeps (`catalogue_balance.cap_limits`). The cap counts a product in the
first two levels of Google's shelves (`catalogue_cap.category_of`); a feed in Awin's own
format has none (measured 19/11, run 44555880488: no `google_product_category`; Awin's own
`category_name`, 246 names, on 509,038 of 1,172,167 rows; the shop's `merchant_category` on
973,206, and `merchant_product_category_path` on 420,733). Without an aisle every such row
would count in one group, "the shops' own categories", and the cap would cut most of them.

So each row's category words, the most specific first (the shop's path, then Awin's name,
then the shop's category), are read against the rules below, in their order, the first
that fits giving the aisle; a row none fits keeps its words as they are. Only the second
link's rows are read so (`awin_adapter.merge_feeds`): the first link's Google shelves are
untouched. A rule never names a service: tickets, experiences and vouchers fit none, and
the eligibility rules decide on them as before.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from functools import lru_cache
from typing import Any

# The row's category columns, the most specific first.
CATEGORY_COLUMNS = ("merchant_product_category_path", "category_name", "merchant_category")

# (words, aisle): a word matches at its start ("tyre" matches "tyres"); a rule written
# with commas holds whole phrases instead ("laptop bag", never every bag); the first rule
# that fits wins, so the narrower come before the broader.
_RULES: tuple[tuple[str, str], ...] = (
    ("tyre tire wheel alloy", "Vehicles & Parts > Vehicle Parts & Accessories"),
    ("car vehicle motorsport motorcycle motorbike automotive 4x4 exhaust", "Vehicles & Parts > Vehicle Parts & Accessories"),
    ("laptop bag,laptop case,laptop sleeve", "Electronics > Electronics Accessories"),
    ("printer ink toner cartridge scanner", "Electronics > Print, Copy, Scan & Fax"),
    ("network hub switch router modem wifi", "Electronics > Networking"),
    ("monitor television tv projector", "Electronics > Video"),
    ("laptop notebook desktop computers pc workstation tablet", "Electronics > Computers"),
    ("headset headphone earphone earbud speaker audio microphone hifi", "Electronics > Audio"),
    ("gaming console xbox playstation nintendo", "Electronics > Video Game Console Accessories"),
    ("phone mobile smartphone", "Electronics > Communications"),
    ("camera lens tripod", "Cameras & Optics > Cameras"),
    ("cpu processor motherboard graphics memory ssd drive computer keyboard mice mouse peripheral webcam "
     "cable charger adapter usb gadget electronic battery", "Electronics > Electronics Accessories"),
    ("lighting lamp light bulb led chandelier", "Home & Garden > Lighting"),
    ("drill saw sander grinder spanner wrench plier screwdriver hammer tool", "Hardware > Tools"),
    ("plumbing tap shower bathroom toilet basin radiator", "Hardware > Plumbing"),
    ("electrical socket switchgear wiring", "Hardware > Power & Electrical Supplies"),
    ("screw fixing fastener nail bolt adhesive sealant", "Hardware > Hardware Accessories"),
    ("paint decorating skirting flooring timber building splashback sheeting", "Hardware > Building Materials"),
    ("workwear safety glove", "Business & Industrial > Work Safety Protective Gear"),
    ("diy hardware", "Hardware > Tools"),
    ("flower plant bouquet", "Home & Garden > Plants"),
    ("garden lawn bbq barbecue grill outdoor heating", "Home & Garden > Lawn & Garden"),
    ("mattress bed", "Furniture > Beds & Accessories"),
    ("sofa", "Furniture > Sofas"),
    ("chair", "Furniture > Chairs"),
    ("table desk", "Furniture > Tables"),
    ("furniture wardrobe cabinet shelving", "Furniture > Cabinets & Storage"),
    ("kitchen cookware kettle toaster appliance cook dining", "Home & Garden > Kitchen & Dining"),
    ("security cctv alarm", "Home & Garden > Business & Home Security"),
    ("cleaning household", "Home & Garden > Household Supplies"),
    ("bedding duvet pillow towel curtain blind", "Home & Garden > Linens & Bedding"),
    ("decor home interior mirror rug", "Home & Garden > Decor"),
    ("footwear shoe trainer boot sandal slipper", "Apparel & Accessories > Shoes"),
    ("jewellery jewelry watch ring necklace bracelet earring cufflink", "Apparel & Accessories > Jewelry"),
    ("handbag wallet purse", "Apparel & Accessories > Handbags, Wallets & Cases"),
    ("luggage suitcase backpack", "Luggage & Bags > Suitcases"),
    ("baby clothes,babywear,baby clothing", "Apparel & Accessories > Clothing"),
    ("baby nursery toddler", "Baby & Toddler > Nursing & Feeding"),
    ("toy puzzle lego doll", "Toys & Games > Toys"),
    ("fitness gym exercise workout yoga", "Sporting Goods > Exercise & Fitness"),
    ("sport cycling bike helmet camping fishing golf", "Sporting Goods > Outdoor Recreation"),
    ("clothing accessories,clothing accessory", "Apparel & Accessories > Clothing Accessories"),
    ("clothing clothes shirt t-shirt trouser jean suit dress jacket coat sock top knitwear apparel wear",
     "Apparel & Accessories > Clothing"),
    ("fragrance perfume", "Health & Beauty > Personal Care"),
    ("cosmetic skincare skin makeup beauty nail hair bodycare body", "Health & Beauty > Personal Care"),
    ("vitamin supplement nutrition protein health", "Health & Beauty > Health Care"),
    ("wine beer spirit drink beverage cocktail tea coffee", "Food, Beverages & Tobacco > Beverages"),
    ("food chocolate sweet snack confectionery", "Food, Beverages & Tobacco > Food Items"),
    ("pet dog cat aquatic aquarium", "Animals & Pet Supplies > Pet Supplies"),
    ("book", "Media > Books"),
    ("dvd blu-ray film", "Media > DVDs & Videos"),
    ("music vinyl", "Media > Music & Sound Recordings"),
    ("card stationery office paper", "Office Supplies > General Office Supplies"),
    ("craft art hobby sewing knitting", "Arts & Entertainment > Hobbies & Creative Arts"),
)


def _compile(words: str) -> re.Pattern[str]:
    phrases = [phrase.strip() for phrase in words.split(",")] if "," in words else words.split()
    alternatives = "|".join(
        r"\s+".join(re.escape(part) for part in phrase.split())
        for phrase in sorted(set(phrases), key=len, reverse=True)
        if phrase
    )
    return re.compile(rf"(?<![a-z0-9])(?:{alternatives})", re.IGNORECASE)


_COMPILED = tuple((_compile(words), aisle) for words, aisle in _RULES)


# Owner, 2026-11-19: «πρέπει να κλωνοποιήσουμε τους κανόνες και στο δεύτερο feed»: an
# Awin-format row is given the deepest shelf of Google's taxonomy its words name, in the
# place a Google-format row has it (`google_product_category`), so every rule that reads a
# shelf reads it alike ("Paint Kettle" on a shelf of tools is no kettle; "Feed Tyres" on a
# shelf of printer accessories is an accessory). First a shelf whose own name is the row's
# category ("Printer Consumables", "Laptops", "Hubs & Switches"), then these, then the
# aisles above.
_DEEPER: tuple[tuple[str, str], ...] = (
    # The parts and accessories of a thing first, before the thing's own name (live 19/11:
    # "Kettle Leads" went to the kitchen, "Feed Tyres" of printers to cars' tyres, "Paint
    # Kettles" to a shelf where the title's kettle stood unchallenged).
    ("lead,leads,cable,cables,adapter,adapters,adaptor,adaptors,connector,connectors,extension lead,extension leads",
     "Electronics > Electronics Accessories > Cables"),
    ("feed tyre,feed tyres,feed tire,feed tires,feed roller,feed rollers,pick roller,pick rollers,pickup roller,"
     "pickup rollers,fuser,fusers,drum unit,drum units,maintenance kit,maintenance kits,printer part,printer parts,"
     "printer spare,printer spares,printer accessories",
     "Electronics > Print, Copy, Scan & Fax > Printer, Copier & Fax Machine Accessories"),
    ("drill bit,drill bits,screwdriver bit,screwdriver bits,router bit,router bits,saw blade,saw blades,hole saw,"
     "hole saws,holesaw,holesaws,chisel,chisels,collet,collets,tool accessories,power tool accessories,pilot drill,pilot drills",
     "Hardware > Tool Accessories"),
    ("paint,paints,painting,decorating,decorator,paint kettle,paint kettles,paint brush,paint brushes",
     "Hardware > Building Consumables > Painting Consumables"),
    ("antenna,antennas,aerial,aerials", "Electronics > Video"),
    ("kettle,kettles,electric kettle,electric kettles", "Home & Garden > Kitchen & Dining > Kitchen Appliances > Electric Kettles"),
    ("kitchen appliance,kitchen appliances,small appliance,small appliances", "Home & Garden > Kitchen & Dining > Kitchen Appliances"),
    ("tyre tyres tire tires", "Vehicles & Parts > Vehicle Parts & Accessories > Motor Vehicle Parts > Motor Vehicle Wheel Systems > Motor Vehicle Tires"),
    ("car part,car parts,motorsport,exhaust,4x4,motor vehicle", "Vehicles & Parts > Vehicle Parts & Accessories > Motor Vehicle Parts"),
    ("laptop bag,laptop case,laptop sleeve,peripheral,peripherals,webcam,webcams", "Electronics > Electronics Accessories > Computer Accessories"),
    ("printer consumable,printer consumables,ink,toner,cartridge,cartridges", "Electronics > Print, Copy, Scan & Fax > Printer, Copier & Fax Machine Accessories > Printer Consumables"),
    ("printer,printers,all-in-one printers,scanner,scanners", "Electronics > Print, Copy, Scan & Fax > Printers, Copiers & Fax Machines"),
    ("monitor,monitors", "Electronics > Video > Computer Monitors"),
    ("mice,mouse", "Electronics > Electronics Accessories > Computer Components > Input Devices > Mice & Trackballs"),
    ("cpu,cpus,processor,processors,motherboard,motherboards,graphics card,graphics cards,computer case,computer cases,"
     "computer component,computer components,ssd,hard drive,hard drives,memory", "Electronics > Electronics Accessories > Computer Components"),
    ("dvd,dvds,blu-ray", "Media > DVDs & Videos"),
    ("skincare,skin care", "Health & Beauty > Personal Care > Cosmetics > Skin Care"),
    ("fragrance,fragrances,perfume,perfumes", "Health & Beauty > Personal Care > Cosmetics > Perfume & Cologne"),
    ("watch,watches", "Apparel & Accessories > Jewelry > Watches"),
    ("cleaning", "Home & Garden > Household Supplies > Household Cleaning Supplies"),
    ("power tool,power tools,hand tool,hand tools,garden tool,garden tools,diy", "Hardware > Tools"),
)


def _leaf_key(name: str) -> str:
    words = " ".join(str(name or "").lower().replace("&", "and").replace("'", "").split())
    return words[:-1] if words.endswith("s") else words


@lru_cache(maxsize=1)
def _leaves() -> dict[str, str]:
    """Google's shelves by their own last name, the shallowest kept for a name used twice."""
    try:
        from picwise_nlu.concept_understanding import _TAXONOMY_PATH

        lines = _TAXONOMY_PATH.read_text(encoding="utf-8").splitlines()
    except (OSError, ImportError):
        return {}
    found: dict[str, str] = {}
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        found.setdefault(_leaf_key(line.split(" > ")[-1]), line)
    return found


_DEEPER_COMPILED = tuple((_compile(words), shelf) for words, shelf in _DEEPER)


def _shelf_of_part(part: str) -> tuple[str, bool]:
    """A piece's shelf, and whether it is precise: a shelf of that very name or one of
    the rules above (True), or only an aisle (False)."""
    shelf = _leaves().get(_leaf_key(part))
    if shelf:
        return shelf, True
    for pattern, shelf in _DEEPER_COMPILED:
        if pattern.search(part):
            return shelf, True
    return aisle_for(part), False


def shelf_detail(text: str) -> tuple[str, bool]:
    """The deepest Google shelf the words name, read from the most specific piece of a
    shop's path first ("Printer Parts > Feed Tyres": "Feed Tyres"), the whole words last;
    and whether it is precise."""
    words = " ".join(str(text or "").split())
    if not words:
        return "", False
    pieces = [piece.strip() for piece in re.split(r"[>/|]", words)[::-1] if piece.strip()]
    for part in pieces + ([words] if len(pieces) != 1 else []):
        shelf, precise = _shelf_of_part(part)
        if shelf:
            return shelf, precise
    return "", False


def shelf_for(text: str) -> str:
    return shelf_detail(text)[0]


def row_shelf_detail(raw: Mapping[str, Any]) -> tuple[str, bool]:
    """The Google shelf of an Awin-format row, from its most specific category column that
    names one, and whether it is precise; ("", False) when the row has Google's own or none
    fits."""
    if str(raw.get("google_product_category") or "").strip():
        return "", False
    for column in CATEGORY_COLUMNS:
        shelf, precise = shelf_detail(str(raw.get(column) or ""))
        if shelf:
            return shelf, precise
    return "", False


def row_shelf(raw: Mapping[str, Any]) -> str:
    return row_shelf_detail(raw)[0]


def aisle_for(text: str) -> str:
    """The aisle the words fit, or "" when none fits."""
    words = " ".join(str(text or "").split())
    if not words:
        return ""
    for pattern, aisle in _COMPILED:
        if pattern.search(words):
            return aisle
    return ""


def row_aisle(raw: Mapping[str, Any]) -> str:
    """The aisle of an Awin-format row: its most specific category column that fits."""
    if str(raw.get("google_product_category") or "").strip():
        return ""
    for column in CATEGORY_COLUMNS:
        aisle = aisle_for(str(raw.get(column) or ""))
        if aisle:
            return aisle
    return ""
