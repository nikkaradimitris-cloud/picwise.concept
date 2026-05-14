from __future__ import annotations


FOOTER_LINKS: tuple[tuple[str, str], ...] = (
    ("Home", "/"),
    ("Demo", "/demo"),
    ("PicWise Reference", "/picwise-reference"),
    ("Terms", "/terms"),
    ("Privacy", "/privacy"),
    ("Cookies", "/cookies"),
    ("Affiliate Disclosure", "/affiliate-disclosure"),
    ("Contact", "/contact"),
)

SHORT_AFFILIATE_NOTICE = (
    "PicWise may earn commissions from qualifying purchases, referrals, or provider links "
    "when affiliate or provider integrations are active."
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
        ".pw-footer-links{display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center;}"
        ".pw-footer-links a{font-size:13px;color:#3c5f8f;text-decoration:none;}"
        ".pw-footer-disclosure{margin:10px 0 0;font-size:12px;line-height:1.5;color:#5f7ea6;max-width:760px;}"
        ".pw-footer-meta{margin:6px 0 0;font-size:12px;color:#6b86ac;}"
        "@media (max-width:760px){.pw-wrap{padding:24px 14px 16px;}.pw-title{font-size:28px;}.pw-legal h2{font-size:18px;}}"
    )


def render_public_footer() -> str:
    links = "".join(f'<a href="{href}">{label}</a>' for label, href in FOOTER_LINKS)
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
        "<h2>About PicWise</h2>"
        "<p>PicWise is an informational product discovery, comparison, and buying-decision assistant. PicWise does not operate as an online store.</p>"
        "<h2>Informational purpose only</h2>"
        "<p>PicWise may highlight, rank, recommend, or compare options, but these outputs are informational only.</p>"
        "<p class=\"pw-emphasis\">A PicWise recommendation does not mean an option is guaranteed to be the best, cheapest, most suitable, safest, highest quality, or most cost-effective choice. PicWise may be wrong because data, terms, availability, market conditions, and user needs can change or be incomplete. Users remain responsible for their final decision.</p>"
        "<h2>PicWise is not an online store</h2>"
        "<p>PicWise does not sell products directly and does not provide direct sales for products or services.</p>"
        "<p>PicWise provides no checkout, no payments, no shipping, no returns, no warranties, no subscriptions, no applications, no approvals, no claims handling, and no seller/provider support.</p>"
        "<h2>External store/provider responsibility</h2>"
        "<p>All purchases, subscriptions, applications, and other actions are completed on external provider or store websites. External seller/provider terms apply.</p>"
        "<p>Prices, availability, ratings, images, delivery times, seller terms, return policies, warranties, subscription terms, provider terms, fees, rates, approval criteria, and eligibility rules may change at any time.</p>"
        "<p>Users must verify all details on the external seller/provider site before buying, subscribing, applying, or acting.</p>"
        "<h2>No guarantee</h2>"
        "<p>PicWise does not guarantee cheapest price, best product, best service, availability, completeness, accuracy, suitability, approval, rates, coverage, or eligibility.</p>"
        "<h2>External links and third-party websites</h2>"
        "<p>PicWise may include links to Amazon, Linkwise, SaaS providers, ERP providers, finance/insurance providers, merchants, affiliate networks, and other third-party websites.</p>"
        "<h2>Affiliate relationships and monetization</h2>"
        "<p>PicWise may earn commissions, referral fees, lead fees, or other compensation when affiliate/provider integrations are active. Affiliate compensation does not make PicWise the seller, provider, lender, insurer, software vendor, broker, or contracting party.</p>"
        "<h2>Physical products scope</h2>"
        "<p>PicWise may compare external product offers. External providers remain responsible for fulfillment, delivery, support, returns, and warranties.</p>"
        "<h2>SaaS / ERP / software provider scope</h2>"
        "<p>PicWise may later compare software, SaaS, ERP, business tools, subscriptions, or digital services from external providers. PicWise does not sell, operate, license, support, implement, or guarantee third-party services.</p>"
        "<p>Users must verify subscription terms, features, pricing, service levels, cancellation terms, security terms, data terms, and provider contracts directly with the provider.</p>"
        "<h2>Finance / insurance / business finance scope</h2>"
        "<p>PicWise may later provide informational comparison or referral paths for finance, insurance, loans, cards, accounts, business finance, or related providers.</p>"
        "<p>PicWise does not provide financial, insurance, tax, investment, credit, or legal advice and does not guarantee approval, rates, eligibility, coverage, premiums, loan terms, returns, risk level, or suitability.</p>"
        "<h2>Disclaimer</h2>"
        "<p>PicWise provides informational comparison, discovery, and buying-decision support only. PicWise content may contain errors, delays, omissions, outdated information, or third-party data issues.</p>"
        "<p>Use of PicWise is at the user's own risk.</p>"
        "<h2>Limitation of liability</h2>"
        "<p>To the maximum extent permitted by applicable law, PicWise and its operator are not responsible for losses, damages, costs, claims, missed savings, wrong purchases, failed purchases, rejected applications, denied coverage, changed prices, unavailable products, third-party service issues, delivery problems, returns, warranties, provider errors, seller disputes, external website issues, or decisions made based on PicWise content.</p>"
        "<p>PicWise is not responsible for actions, omissions, policies, terms, products, services, prices, availability, data, tracking, cookies, privacy practices, or customer support of external providers and networks.</p>"
        "<h2>No professional advice</h2>"
        "<p>No professional advice is provided by PicWise. PicWise does not provide legal, financial, tax, investment, insurance, medical, technical implementation, procurement, compliance, or professional advice.</p>"
        "<p>SaaS/ERP/software comparisons are informational only. Finance/insurance/business finance comparisons are informational only and no financial advice is provided.</p>"
        "<h2>User responsibility and prohibited misuse</h2>"
        "<p>Users must evaluate suitability independently and must not misuse PicWise for unlawful, deceptive, abusive, or unauthorized purposes.</p>"
        "<h2>Intellectual property</h2>"
        "<p>PicWise content, layout, and text are owned by or licensed to PicWise/operator. Third-party names, trademarks, providers, and product names belong to their respective owners and are used only for identification/comparison where applicable.</p>"
        "<h2>Corrections and changes</h2>"
        "<p>Users and providers can contact PicWise to request correction of inaccurate information or external link concerns. PicWise may update these pages and service behavior over time.</p>"
        "<h2>Contact</h2>"
        "<p>Email: contact@picwise.subby.cloud</p>"
        "<p>Last updated: May 2026</p>"
    )
    return _render_legal_page(
        title="Terms of Use — PicWise",
        meta_description=(
            "Read the PicWise Terms of Use for external provider links, comparison limits, affiliate "
            "relationships, SaaS, finance, and user responsibilities."
        ),
        heading="Terms of Use",
        intro="Please review these terms before using PicWise.",
        sections=sections,
    )


def render_privacy_page() -> str:
    sections = (
        "<h2>About PicWise and scope</h2>"
        "<p>This Privacy Policy applies to PicWise public pages and explains the basic data processing context for website operation and communication.</p>"
        "<h2>Data PicWise may process now</h2>"
        "<ul>"
        "<li>IP address</li><li>Browser/device type</li><li>Requested URLs</li><li>Timestamps</li>"
        "<li>Referrer data</li><li>Server logs</li><li>Error logs</li><li>Security logs</li>"
        "</ul>"
        "<h2>Contact data</h2>"
        "<p>If you email PicWise, your email address and message content may be used to reply.</p>"
        "<h2>Search/demo interactions</h2>"
        "<p>Search and demo interactions may be processed to show website responses. No purchase, subscription, application, or checkout is completed on PicWise.</p>"
        "<h2>What PicWise does not currently process</h2>"
        "<p>PicWise does not process checkout payments, card details, shipping fulfillment, seller customer support, direct product orders, direct SaaS subscriptions, or direct credit/insurance applications unless explicitly implemented later.</p>"
        "<h2>Hosting and technical providers</h2>"
        "<p>Hosting and server infrastructure may process technical logs for operation and reliability.</p>"
        "<h2>External provider and affiliate links</h2>"
        "<p>After leaving PicWise, Amazon, Linkwise, SaaS providers, ERP providers, finance/insurance providers, affiliate networks, merchants, and other external sellers may process data under their own policies.</p>"
        "<h2>Cookies and browser storage</h2>"
        "<p>See <a href=\"/cookies\">/cookies</a> for the full Cookie Policy. Cookies, browser storage, and related technologies may be used for essential operation and may expand when integrations are active.</p>"
        "<h2>Pixels and tracking</h2>"
        "<p>Non-essential pixels or tracking should only be activated with consent where required. Provider and affiliate tracking configurations are in progress.</p>"
        "<h2>Affiliate/referral tracking</h2>"
        "<p>When integrations become active, links may include tracking parameters, affiliate IDs, referral IDs, lead IDs, or network tracking fields.</p>"
        "<h2>Legal basis</h2>"
        "<p>Legal basis may include legitimate interests for operation, security, debugging, fraud prevention, and service improvement; consent where required for non-essential cookies/pixels/analytics; communication necessity for contact requests; and legal obligations where applicable.</p>"
        "<h2>Data retention</h2>"
        "<p>Logs and contact emails are retained only as long as reasonably needed for operation, security, communication, legal, or dispute purposes.</p>"
        "<h2>User rights</h2>"
        "<p>Where applicable, users may request access, correction, deletion, restriction, objection, portability, and withdrawal of consent.</p>"
        "<h2>EEA / UK users</h2>"
        "<p>PicWise recognizes privacy rights for users in the European Economic Area (EEA), GDPR contexts, and the United Kingdom.</p>"
        "<h2>US / international users</h2>"
        "<p>Privacy rights may vary by location. Users can contact PicWise about privacy requests.</p>"
        "<h2>Children</h2>"
        "<p>PicWise is not directed to children under 13.</p>"
        "<h2>International transfers and security</h2>"
        "<p>External providers and infrastructure may operate in different countries. PicWise uses reasonable security measures but no system can provide an absolute guarantee.</p>"
        "<h2>Automated decisions</h2>"
        "<p>PicWise may provide informational ranking/comparison outputs, but users should verify provider terms before acting. PicWise does not claim regulated automated credit or insurance decisions.</p>"
        "<h2>Changes and contact</h2>"
        "<p>PicWise may update this policy as the service evolves.</p>"
        "<p>Email: contact@picwise.subby.cloud</p>"
        "<p>Last updated: May 2026</p>"
    )
    return _render_legal_page(
        title="Privacy Policy — PicWise",
        meta_description=(
            "Learn how PicWise handles basic technical data, contact requests, provider links, cookies, "
            "pixels, affiliate tracking, and privacy rights."
        ),
        heading="Privacy Policy",
        intro="This page explains how PicWise handles privacy-related data.",
        sections=sections,
    )


def render_cookies_page() -> str:
    sections = (
        "<h2>What cookies and similar technologies are</h2>"
        "<p>Cookies, local storage, pixels, and tags help websites remember context and measure performance.</p>"
        "<h2>Essential cookies / local storage</h2>"
        "<p>Essential cookies or browser storage may be used for operation, security, preferences, or session behavior where needed.</p>"
        "<h2>Non-essential cookies</h2>"
        "<p>Non-essential cookies may include analytics, performance, affiliate, conversion, marketing, personalization, or provider-tracking cookies if activated later.</p>"
        "<h2>Pixels and tags</h2>"
        "<p>Analytics pixels, affiliate pixels, conversion pixels, provider tracking tags, and remarketing tags may be used later when integrations are active.</p>"
        "<h2>Current state</h2>"
        "<p>Provider and affiliate tracking is being configured. PicWise does not currently claim that Google Analytics, Meta Pixel, Amazon pixels, Linkwise pixels, finance-provider pixels, SaaS-provider pixels, or a consent manager are active.</p>"
        "<h2>Third-party cookies after leaving PicWise</h2>"
        "<p>Amazon, Linkwise, SaaS providers, finance/insurance providers, merchants, affiliate networks, and other providers may use their own cookies/tracking under their own policies.</p>"
        "<h2>Consent and UK/EU rule</h2>"
        "<p>Non-essential cookies and pixels should only be used with consent where required by UK/EU law.</p>"
        "<h2>Cookie consent trigger rule</h2>"
        "<p>If analytics, affiliate pixels, remarketing, conversion tracking, or other non-essential tracking are added later, a consent mechanism must be added before activation where required.</p>"
        "<h2>How users can control cookies</h2>"
        "<p>Users can control cookies via browser settings and third-party provider settings where applicable.</p>"
        "<h2>Future updates and contact</h2>"
        "<p>This page will be updated when tracking/provider integrations become active.</p>"
        "<p>Email: contact@picwise.subby.cloud</p>"
        "<p>Last updated: May 2026</p>"
    )
    return _render_legal_page(
        title="Cookie Policy — PicWise",
        meta_description=(
            "Learn how PicWise may use essential cookies, browser storage, analytics cookies, pixels, "
            "affiliate tracking, and provider tracking when active."
        ),
        heading="Cookie Policy",
        intro="This page explains how PicWise approaches cookies and similar technologies.",
        sections=sections,
    )


def render_affiliate_disclosure_page() -> str:
    sections = (
        "<h2>About affiliate links and referral links</h2>"
        "<p>PicWise may include affiliate links, referral links, or provider links when integrations are active.</p>"
        "<h2>Amazon Associates</h2>"
        '<p class="pw-emphasis">"As an Amazon Associate I earn from qualifying purchases."</p>'
        "<h2>Linkwise</h2>"
        "<p>PicWise may participate in Linkwise programs where available.</p>"
        "<h2>Other affiliate/provider networks</h2>"
        "<p>PicWise may work with other affiliate networks, merchant programs, and provider referral ecosystems.</p>"
        "<h2>SaaS / ERP / software affiliate or referral programs</h2>"
        "<p>PicWise may include SaaS, ERP, software, or digital-service referral relationships in future stages.</p>"
        "<h2>Finance / insurance / business finance referral or lead programs</h2>"
        "<p>PicWise may include finance, insurance, loans, cards, accounts, or business finance referral paths where permitted.</p>"
        "<h2>How compensation may work</h2>"
        "<p>If users click affiliate/referral/provider links and make qualifying purchases or complete qualifying actions, PicWise may earn a commission, referral fee, lead fee, or other compensation.</p>"
        "<p>This does not necessarily increase the price paid by the user.</p>"
        "<p>Affiliate relationships may influence monetization, but PicWise should aim to provide useful comparison and decision support.</p>"
        "<h2>Current state</h2>"
        "<p>Provider/affiliate integrations are being configured. PicWise does not claim live Amazon offers unless actually active.</p>"
        "<h2>External provider responsibility and user verification</h2>"
        "<p>Pricing, availability, delivery, returns, warranties, subscription terms, finance/insurance eligibility, rates, approval, and legal/provider terms are controlled by external providers/stores.</p>"
        "<p>Users should verify details on the external provider/store before buying, subscribing, applying, or acting.</p>"
        "<h2>Recommendation limitation</h2>"
        "<p>Affiliate compensation or a highlighted recommendation does not guarantee that an option is the best, cheapest, most suitable, or most cost-effective choice.</p>"
        "<h2>Disclosure placement rule</h2>"
        "<p>When live affiliate links are added, a clear affiliate disclosure must appear near affiliate link areas or in a clearly visible page/footer location.</p>"
        "<h2>Contact</h2>"
        "<p>Email: contact@picwise.subby.cloud</p>"
        "<p>Last updated: May 2026</p>"
    )
    return _render_legal_page(
        title="Affiliate Disclosure — PicWise",
        meta_description=(
            "Learn how PicWise may earn commissions from Amazon Associates, Linkwise, SaaS, finance, "
            "insurance, and other provider programs."
        ),
        heading="Affiliate Disclosure",
        intro="This page explains how affiliate and provider compensation may apply to PicWise.",
        sections=sections,
    )


def render_contact_page() -> str:
    sections = (
        "<h2>PicWise contact page</h2>"
        "<p>Email: contact@picwise.subby.cloud</p>"
        "<h2>Contact topics</h2>"
        "<ul>"
        "<li>Website questions</li>"
        "<li>Privacy questions</li>"
        "<li>Cookie/pixel questions</li>"
        "<li>Affiliate disclosure questions</li>"
        "<li>Correction requests</li>"
        "<li>Product information concerns</li>"
        "<li>SaaS/provider information concerns</li>"
        "<li>Finance/insurance provider information concerns</li>"
        "<li>External link concerns</li>"
        "<li>Legal/trust page questions</li>"
        "</ul>"
        "<p>No contact form is required at this stage.</p>"
        "<p>Last updated: May 2026</p>"
    )
    return _render_legal_page(
        title="Contact — PicWise",
        meta_description=(
            "Contact PicWise for website, privacy, affiliate disclosure, cookie, correction, or external "
            "provider questions."
        ),
        heading="Contact",
        intro="Use this page to contact PicWise for legal/trust and information concerns.",
        sections=sections,
    )
