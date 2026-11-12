"""The site's one font, Inter, served by the site itself (owner, 2026-11-12: to the design
proposed, its point 8 among them, «Έχεις δίκιο για αυτά»).

The pages have named Inter since May but never loaded it, so a visitor saw whatever their
device had: Roboto on the owner's phone, Segoe UI or Arial elsewhere. Now the latin part
of Inter's variable font, every weight in one file of 48,256 bytes, from the package
@fontsource-variable/inter 5.2.8, is under `assets/picwise/fonts/` with its licence (the
SIL Open Font License 1.1, `OFL.txt`, which asks that it go with the font).

It comes from the site's own address: the security policy allows nothing else
(`picwise_app.app.CONTENT_SECURITY_POLICY`, `default-src 'self'`), and no visitor's
address is given to a font service. The words show at once in the device's own font and
turn to Inter when it arrives (`font-display:swap`), so nothing waits for it; the browser
keeps it a week (`ASSET_CACHE_CONTROL`). Letters outside its range (▲, ▼) come from the
device's font.
"""
from __future__ import annotations

FONT_PATH = "/assets/picwise/fonts/inter-latin-wght-normal.woff2"
# The range the package gives this file: Latin, the £ and € signs, punctuation.
_LATIN_RANGE = (
    "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,"
    "U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD"
)
FONT_FACE_CSS = (
    "@font-face{font-family:Inter;font-style:normal;font-weight:100 900;font-display:swap;"
    f'src:url({FONT_PATH}) format("woff2");unicode-range:{_LATIN_RANGE};}}'
)
# Asked for with the page, before the style sheet finds it.
FONT_PRELOAD_HTML = f'<link rel="preload" href="{FONT_PATH}" as="font" type="font/woff2" crossorigin>'
