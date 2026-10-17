"""Shared pieces for the local product fixtures the provider tests build.

Owner rule (2026-10-12): a product PicWise shows always carries availability, a
price, an image and a description. The description is part of what makes a product
showable, so a fixture product without one is not a product the platform would ever
display, and a test built on one would pin behaviour that cannot happen.

`fixture_description` gives a fixture row a description long enough to clear
`picwise_providers.product_description.DESCRIPTION_MIN_CHARS`. It deliberately names
no product and no kind of product: a description is one of the fields the search
ranks on, so text mentioning the product would hand every fixture row free merchant
evidence for its own kind and quietly change what the ranking tests measure. The one
sentence is identical on every row, which is what keeps it neutral. A test that wants
a row to carry particular free text passes it as `detail`, and only that row has it.
"""
from __future__ import annotations

_ENGLISH = (
    "Local test data, written here in full sentences so that the row carries the "
    "availability, price, image and description PicWise requires of everything it "
    "shows a buyer. Not a real listing and not for sale."
)
_GREEK = (
    "Δεδομένα τοπικού test, γραμμένα εδώ σε πλήρεις προτάσεις ώστε η γραμμή να έχει τη "
    "διαθεσιμότητα, την τιμή, την εικόνα και την περιγραφή που απαιτεί το PicWise από "
    "ό,τι δείχνει σε αγοραστή. Δεν είναι πραγματική καταχώριση."
)


def fixture_description(detail: str = "", *, greek: bool = False) -> str:
    """A description long enough for the row to be shown, naming no product.

    `detail` is kept as the lead sentence, so a row that already said what it was
    there to test still says it, and a test that needs particular words in merchant
    free text puts them there.
    """
    lead = " ".join(str(detail or "").split())
    body = _GREEK if greek else _ENGLISH
    return f"{lead} {body}".strip() if lead else body
