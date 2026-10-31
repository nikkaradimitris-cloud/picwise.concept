from __future__ import annotations


FOOTER_LINKS: tuple[tuple[str, str], ...] = (
    ("Home", "/"),
    ("About", "/about"),
    ("Demo", "/demo"),
    ("PicWise Reference", "/picwise-reference"),
    ("Terms", "/terms"),
    ("Privacy", "/privacy"),
    ("Cookies", "/cookies"),
    ("Affiliate Disclosure", "/affiliate-disclosure"),
    ("Contact", "/contact"),
)

# Who runs PicWise and how to reach them, given by the owner on 2026-10-31 (the
# address on the site's own domain, their choice the same day).
OPERATOR_NAME = "Nikos Karadimitris"
OPERATOR_ADDRESS = "53 N. Notara Street, Piraeus, Greece"
OPERATOR_VAT = "EL120948460"
PUBLIC_CONTACT_EMAIL = "contact.picwise@subby.cloud"
LAST_UPDATED = "31 October 2026"

SHORT_AFFILIATE_NOTICE = (
    "PicWise earns a commission from some shops, through Awin, when you buy after following "
    "one of its links. The price you pay is the same, and the commission never changes the "
    "order of the results."
)

_OPERATOR_HTML = (
    f"<p>PicWise is run by {OPERATOR_NAME}, a sole trader based in Greece.</p>"
    f"<p>Address: {OPERATOR_ADDRESS}<br>VAT number: {OPERATOR_VAT}<br>Email: {PUBLIC_CONTACT_EMAIL}</p>"
)

_WHAT_PICWISE_DOES_HTML = (
    "<p>PicWise is a product search for shoppers in the United Kingdom who already know what "
    "they want to buy. Type a product, and PicWise shows only that kind of product, only what "
    "the shops list as in stock, cheapest first: four choices, usually with one marked as the "
    "recommended pick from the middle of the prices rather than simply the cheapest, and "
    "\u201cMore\u201d for the next four.</p>"
    "<p>The prices and stock come from the shops' own product feeds, received through the Awin "
    "affiliate network and read again every night. Where a shop publishes its own catalogue, "
    "PicWise also reads it to check what is in stock.</p>"
    "<p>PicWise is not a shop. Every purchase is made on the shop's own website, under the "
    "shop's terms.</p>"
)


def _base_styles() -> str:
    return (
        "*{box-sizing:border-box;}"
        "body{margin:0;font-family:Inter,Segoe UI,Arial,sans-serif;color:#102744;background:linear-gradient(180deg,#f8fbff 0%,#f3f8ff 100%);}"
        ".pw-wrap{max-width:980px;margin:0 auto;padding:32px 20px 20px;}"
        ".pw-brand{display:inline-block;font-size:30px;font-weight:800;letter-spacing:-.03em;color:#1a4fb7;text-decoration:none;}"
        ".pw-card{margin-top:16px;background:#fff;border:1px solid #d9e7fb;border-radius:16px;padding:24px;box-shadow:0 12px 28px rgba(20,56,112,.08);}"
        ".pw-title{margin:0;font-size:34px;line-height:1.16;letter-spacing:-.02em;color:#0f2442;}"
        ".pw-intro{margin:12px 0 0;font-size:16px;line-height:1.65;color:#2c4567;}"
        ".pw-legal{max-width:760px;}"
        ".pw-legal h2{margin:24px 0 10px;font-size:20px;line-height:1.3;color:#173862;}"
        ".pw-legal p{margin:0 0 12px;font-size:15px;line-height:1.7;color:#355174;}"
        ".pw-legal ul{margin:0 0 14px 20px;padding:0;color:#355174;}"
        ".pw-legal li{margin:0 0 8px;line-height:1.6;}"
        ".pw-legal .pw-emphasis{padding:12px 14px;border:1px solid #dbe8fb;border-radius:12px;background:#f6f9ff;}"
        ".pw-footer{margin-top:18px;padding-top:14px;border-top:1px solid #dbe8fb;}"
        ".pw-footer-links{display:flex;flex-wrap:wrap;gap:8px;align-items:center;}"
        ".pw-footer-link{display:inline-flex;align-items:center;justify-content:center;padding:6px 10px;"
        "border:1px solid #d8e6fb;border-radius:999px;background:#f7faff;font-size:13px;"
        "line-height:1.2;color:#335983;text-decoration:none;white-space:nowrap;}"
        ".pw-footer-link:hover{background:#eef5ff;border-color:#cddffc;color:#24496f;}"
        ".pw-footer-disclosure{margin:10px 0 0;font-size:12px;line-height:1.5;color:#5f7ea6;max-width:760px;}"
        ".pw-footer-meta{margin:6px 0 0;font-size:12px;color:#6b86ac;}"
        "@media (max-width:760px){.pw-wrap{padding:24px 14px 16px;}.pw-title{font-size:28px;}.pw-legal h2{font-size:18px;}}"
    )


def render_public_footer() -> str:
    links = "".join(
        f'<a class="pw-footer-link" href="{href}">{label}</a>' for label, href in FOOTER_LINKS
    )
    return (
        '<footer class="pw-footer">'
        f'<nav class="pw-footer-links" aria-label="PicWise public footer links">{links}</nav>'
        f'<p class="pw-footer-disclosure">{SHORT_AFFILIATE_NOTICE}</p>'
        '<p class="pw-footer-meta">&copy; 2026 PicWise. All rights reserved.</p>'
        "</footer>"
    )


def render_branded_not_found_page() -> str:
    return (
        "<!doctype html>"
        '<html lang="en"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Page not found — PicWise</title>"
        '<meta name="description" content="Page not found on PicWise. Return to the home page and continue comparing options with clear informational guidance.">'
        f"<style>{_base_styles()}</style></head><body>"
        '<main class="pw-wrap">'
        '<a class="pw-brand" href="/" aria-label="PicWise home">PicWise</a>'
        '<section class="pw-card pw-legal">'
        '<h1 class="pw-title">Page not found — PicWise</h1>'
        '<p class="pw-intro">The page you requested could not be found.</p>'
        '<p><a href="/">Return to PicWise home</a></p>'
        "</section>"
        f"{render_public_footer()}"
        "</main></body></html>"
    )


def _render_legal_page(*, title: str, meta_description: str, heading: str, intro: str, sections: str) -> str:
    return (
        "<!doctype html>"
        '<html lang="en"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{title}</title>"
        f'<meta name="description" content="{meta_description}">'
        f"<style>{_base_styles()}</style></head><body>"
        '<main class="pw-wrap">'
        '<a class="pw-brand" href="/" aria-label="PicWise home">PicWise</a>'
        '<section class="pw-card pw-legal">'
        f'<h1 class="pw-title">{heading}</h1>'
        f'<p class="pw-intro">{intro}</p>'
        f"{sections}"
        "</section>"
        f"{render_public_footer()}"
        "</main></body></html>"
    )


def render_terms_page() -> str:
    sections = (
        "<h2>Who runs PicWise</h2>"
        f"{_OPERATOR_HTML}"
        "<h2>What PicWise is</h2>"
        f"{_WHAT_PICWISE_DOES_HTML}"
        "<h2>Information only</h2>"
        "<p>PicWise's results, its recommended pick and its labels are information to help you decide.</p>"
        "<p class=\"pw-emphasis\">A PicWise recommendation does not mean an option is guaranteed to be the best, cheapest, most suitable, safest, highest quality, or most cost-effective choice. PicWise may be wrong because data, terms, availability, market conditions, and user needs can change or be incomplete. Users remain responsible for their final decision.</p>"
        "<h2>Purchases happen on the shops' websites</h2>"
        "<p>PicWise does not sell products directly and provides no checkout, payments, shipping, returns, warranties or customer support. All of these belong to the shop you buy from, the external seller/provider, under its own terms.</p>"
        "<p>Prices, stock, delivery times and offers can change after PicWise last read them. Check the details on the shop's website before you buy.</p>"
        "<h2>Links to shops and commission</h2>"
        "<p>Links from PicWise to shops go through the Awin affiliate network. When you buy after following one, the shop may pay PicWise a commission through Awin. The price you pay is the same, and the commission never changes the order of the results or the recommended pick. See the <a href=\"/affiliate-disclosure\">Affiliate Disclosure</a>.</p>"
        "<h2>What PicWise compares</h2>"
        "<p>PicWise compares physical products sold by shops in the United Kingdom. It does not compare software or SaaS subscriptions, nor finance or insurance products; if that changes, these terms will say so first.</p>"
        "<h2>No guarantee</h2>"
        "<p>PicWise does not guarantee the cheapest price, the best product, availability, completeness, accuracy or suitability.</p>"
        "<h2>Disclaimer</h2>"
        "<p>PicWise's content may contain errors, delays, omissions or outdated information, including in the data shops send. Use of PicWise is at the user's own risk.</p>"
        "<h2>Limitation of liability</h2>"
        "<p>To the maximum extent permitted by applicable law, PicWise and its operator are not responsible for losses, damages, costs, claims, missed savings, wrong purchases, failed purchases, changed prices, unavailable products, delivery problems, returns, warranties, shop errors, seller disputes, external website issues, or decisions made based on PicWise content.</p>"
        "<p>PicWise is not responsible for the actions, terms, products, prices, data, tracking, cookies, privacy practices or customer support of shops and networks.</p>"
        "<h2>No professional advice</h2>"
        "<p>PicWise gives no professional advice: no financial advice, and no legal, tax, medical or technical advice.</p>"
        "<h2>Acceptable use</h2>"
        "<p>Do not use PicWise for unlawful, deceptive, abusive or unauthorised purposes, or in a way that harms the service or other people.</p>"
        "<h2>Intellectual property</h2>"
        "<p>PicWise's text, layout and design belong to its operator. Shop, brand and product names, and product images, belong to their owners and appear only to identify and compare products.</p>"
        "<h2>Corrections and changes</h2>"
        "<p>Shoppers and shops can ask PicWise to correct inaccurate information. PicWise may update these terms and the service over time; the date below shows the latest version.</p>"
        "<h2>Contact</h2>"
        f"<p>Email: {PUBLIC_CONTACT_EMAIL}</p>"
        f"<p>Last updated: {LAST_UPDATED}</p>"
    )
    return _render_legal_page(
        title="Terms of Use — PicWise",
        meta_description=(
            "The terms of use of PicWise, a product search that shows UK shops' products in stock, "
            "cheapest first: who runs it, links to shops, commission, and limits."
        ),
        heading="Terms of Use",
        intro="Please read these terms before using PicWise.",
        sections=sections,
    )


def render_privacy_page() -> str:
    sections = (
        "<h2>Who is responsible for your data</h2>"
        f"{_OPERATOR_HTML}"
        "<h2>What PicWise processes</h2>"
        "<p>Like any website, the server that runs PicWise keeps technical logs to work and stay secure:</p>"
        "<ul>"
        "<li>the pages requested, including the words of a search</li><li>timestamps</li>"
        "<li>browser and device type</li><li>referrer data</li>"
        "<li>IP addresses, in security logs</li><li>error logs</li>"
        "</ul>"
        "<h2>What PicWise does not do</h2>"
        "<p>PicWise has no user accounts and no sign-in. It sets no cookies of its own and uses no analytics or advertising pixels. It takes no payments, card details or orders; purchases happen on the shops' websites. It does not compare software (SaaS) or finance products, so it collects nothing for them.</p>"
        "<h2>Emails</h2>"
        "<p>If you email PicWise, your email address and message are used to reply to you.</p>"
        "<h2>Voice search (microphone)</h2>"
        "<p>Where your browser can turn speech into text, the search box shows a microphone button. Nothing is recorded unless you press it. "
        "Your browser does the listening with its own speech service, not PicWise: in Google Chrome the audio is sent to Google to be turned into text, "
        "and in Microsoft Edge and Apple Safari to Microsoft's or Apple's service, under their own privacy policies. "
        "PicWise receives only the words, as a typed search, and never the audio.</p>"
        "<h2>Hosting</h2>"
        "<p>PicWise runs on a server of OVHcloud in London, United Kingdom, which processes the technical logs above for PicWise.</p>"
        "<h2>Links to shops</h2>"
        "<p>When you follow a link to a shop, you leave PicWise. Awin (the affiliate network) and the shop then process data, including their own cookies, under their own privacy policies.</p>"
        "<h2>Cookies and browser storage</h2>"
        "<p>See the <a href=\"/cookies\">Cookie Policy</a>. PicWise sets no cookies and stores nothing in your browser.</p>"
        "<h2>Legal basis</h2>"
        "<p>Technical logs: PicWise's legitimate interest in running a working and secure website. Emails: replying to your request. If PicWise ever uses non-essential cookies, it will ask for your consent first.</p>"
        "<h2>How long data is kept</h2>"
        "<p>Technical logs are kept only as long as needed for operation and security, and emails as long as needed to answer them and for legal obligations.</p>"
        "<h2>Your rights</h2>"
        "<p>In the European Economic Area and the United Kingdom, the GDPR and the UK GDPR give you these rights. You may ask for access to, correction or deletion of your data, restrict or object to its processing, or ask for a copy, by emailing PicWise. You may also complain to a data protection authority: in Greece, where PicWise's operator is based, the Hellenic Data Protection Authority; in the United Kingdom, the Information Commissioner's Office.</p>"
        "<h2>Children</h2>"
        "<p>PicWise is not directed to children under 13.</p>"
        "<h2>Changes and contact</h2>"
        "<p>PicWise may update this policy as the service changes; the date below shows the latest version.</p>"
        f"<p>Email: {PUBLIC_CONTACT_EMAIL}</p>"
        f"<p>Last updated: {LAST_UPDATED}</p>"
    )
    return _render_legal_page(
        title="Privacy Policy — PicWise",
        meta_description=(
            "How PicWise handles data: who is responsible, the technical logs its server keeps, no cookies "
            "of its own, links to shops through Awin, and your rights."
        ),
        heading="Privacy Policy",
        intro="This page explains what data PicWise handles and why.",
        sections=sections,
    )


def render_cookies_page() -> str:
    sections = (
        "<h2>What cookies are</h2>"
        "<p>Cookies, local storage, pixels and tags are small pieces of data or code that let a website remember things on your device or measure visits.</p>"
        "<h2>PicWise's own cookies</h2>"
        "<p>None. PicWise sets no cookies and stores nothing in your browser. It needs no essential cookies to work, and uses no non-essential cookies: no analytics, no advertising, no tracking pixels or tags.</p>"
        "<h2>Cookies after you leave PicWise</h2>"
        "<p>When you follow a link to a shop, Awin, the affiliate network, and then the shop set their own cookies, so that the shop knows you came from PicWise and can pay its commission. These cookies belong to them and follow their own policies.</p>"
        "<h2>Consent</h2>"
        "<p>Because PicWise sets no non-essential cookies, it shows no consent banner. If that ever changes, PicWise will ask for your consent first, as UK and EU law require, and update this page.</p>"
        "<h2>How you can control cookies</h2>"
        "<p>Your browser's settings let you see, block and delete cookies, including those of Awin and the shops.</p>"
        "<h2>Contact</h2>"
        f"<p>Email: {PUBLIC_CONTACT_EMAIL}</p>"
        f"<p>Last updated: {LAST_UPDATED}</p>"
    )
    return _render_legal_page(
        title="Cookie Policy — PicWise",
        meta_description=(
            "PicWise sets no cookies of its own and uses no tracking pixels; Awin and the shops set their own "
            "cookies once you follow a link to a shop."
        ),
        heading="Cookie Policy",
        intro="This page explains how PicWise and the sites it links to use cookies.",
        sections=sections,
    )


def render_affiliate_disclosure_page() -> str:
    sections = (
        "<h2>How PicWise earns</h2>"
        "<p>PicWise works with the Awin affiliate network. Links from PicWise to shops go through Awin, and when you buy after following one, the shop may pay PicWise a commission through Awin.</p>"
        "<h2>What it does not change</h2>"
        "<p>The price you pay is the same. The commission never decides what PicWise shows or in which order: results are the kind you asked for, in stock, cheapest first, and the recommended pick is the one in the middle of the prices. Shops that pay no commission are ranked by the same rule.</p>"
        "<h2>Which shops</h2>"
        "<p>The shops on PicWise run a programme with Awin and have accepted PicWise into it. PicWise works with no other affiliate network at present; any other will be named here first.</p>"
        "<h2>What PicWise compares</h2>"
        "<p>Physical products from UK shops. PicWise has no software (SaaS), finance or insurance referral programmes.</p>"
        "<h2>Check before you buy</h2>"
        "<p>Prices, stock, delivery, returns and warranties are set by the shop. Check them on the shop's website before you buy.</p>"
        "<h2>Contact</h2>"
        f"<p>Email: {PUBLIC_CONTACT_EMAIL}</p>"
        f"<p>Last updated: {LAST_UPDATED}</p>"
    )
    return _render_legal_page(
        title="Affiliate Disclosure — PicWise",
        meta_description=(
            "How PicWise earns: a commission from shops through Awin when you buy, at no extra cost to you, "
            "never changing the order of the results."
        ),
        heading="Affiliate Disclosure",
        intro="This page explains how PicWise earns, and what that never changes.",
        sections=sections,
    )


def render_contact_page() -> str:
    sections = (
        "<h2>Email</h2>"
        f"<p>Email: {PUBLIC_CONTACT_EMAIL}</p>"
        "<h2>Who runs PicWise</h2>"
        f"{_OPERATOR_HTML}"
        "<h2>What you can write about</h2>"
        "<ul>"
        "<li>Questions about PicWise</li>"
        "<li>A price, a product or a shop shown wrongly</li>"
        "<li>Privacy and cookies</li>"
        "<li>The affiliate disclosure</li>"
        "<li>Shops that want to be on PicWise</li>"
        "</ul>"
        f"<p>Last updated: {LAST_UPDATED}</p>"
    )
    return _render_legal_page(
        title="Contact — PicWise",
        meta_description=(
            "Contact PicWise about the site, a product shown wrongly, privacy, cookies or the affiliate disclosure."
        ),
        heading="Contact",
        intro="Write to PicWise by email.",
        sections=sections,
    )


def render_about_page() -> str:
    sections = (
        "<h2>What PicWise does</h2>"
        f"{_WHAT_PICWISE_DOES_HTML}"
        "<h2>How the choices are made</h2>"
        "<ul>"
        "<li>Only the kind of product you asked for: a search for a coffee machine shows coffee machines, not filters for coffee machines.</li>"
        "<li>Only what the shop lists as in stock.</li>"
        "<li>Cheapest first, in one currency.</li>"
        "<li>A recommended pick when the prices allow one: the product in the middle of the prices, so neither the cheapest nor the dearest decides it.</li>"
        "<li>When there are fewer products, PicWise shows just those, and says so.</li>"
        "</ul>"
        "<h2>How PicWise earns</h2>"
        "<p>A commission from some shops, through Awin, when you buy after following a PicWise link. The price you pay is the same, and the commission never changes the order. See the <a href=\"/affiliate-disclosure\">Affiliate Disclosure</a>.</p>"
        "<h2>Who runs PicWise</h2>"
        f"{_OPERATOR_HTML}"
        f"<p>Last updated: {LAST_UPDATED}</p>"
    )
    return _render_legal_page(
        title="About PicWise — PicWise",
        meta_description=(
            "PicWise is a product search for UK shoppers: only the kind you asked for, in stock, cheapest first, "
            "with one recommended pick from the middle of the prices."
        ),
        heading="About PicWise",
        intro="A product search that shows only what you asked for, in stock, cheapest first.",
        sections=sections,
    )
