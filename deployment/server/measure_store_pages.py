"""Measure a few pages of the look at the home page as a store in a browser (task H5;
docs/PICWISE_HOME_STORE_SPEC.md, 5.12, 5.15, 9): the phone's measures by a browser, not by
reading styles, and Google's three on the home page.

    python3 deployment/server/measure_store_pages.py PAGES_DIR

Run by .github/workflows/server-look-home-store.yml on GitHub's runner, never on the
server: the pages are the ones the look drew on the server's data
(deployment/server/look_home_store.py), served here from a folder beside the repository's
own `assets`. **No shop, and nothing but this folder, is asked**: every request to another
host is refused, so a product's photo is an empty box of its own size (a search's largest
paint, a shop's photo, is therefore not measured here; the home page's pictures are the
site's own drawings and are).

For each page at 390x844 and 360x640 (a phone) and 1280x800: what is tapped under 48 px or
nearer than 8 px to the next, words under 12 px, anything wider than the screen, a picture
of the site that did not load, an error of a script. For the home page on a phone four
times slower than the runner and on a slow 4G line (Lighthouse's phone): the first paint,
the largest paint, the layout's shift, and how long a tap takes to be answered.
"""
from __future__ import annotations

import functools
import http.server
import os
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
PORT = 8791
CHROME = "/usr/bin/google-chrome"
VIEWS = (("phone 390", 390, 844, True), ("phone 360", 360, 640, True), ("computer 1280", 1280, 800, False))

COLLECT = r"""
() => {
  const vis = (el) => { const r = el.getBoundingClientRect(); const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none'; };
  const scroller = (el) => { for (let p = el.parentElement; p; p = p.parentElement) {
    const s = getComputedStyle(p); if (/(auto|scroll)/.test(s.overflowX)) return true; } return false; };
  const targets = [...document.querySelectorAll('a, button, input, select, textarea, summary')].filter(vis).map((el, i) => {
    const r = el.getBoundingClientRect();
    return { i, own: !!el.closest('.pw-hs-head, .pw-hs-main, .pw-hs-foot, .pw-hs-strip, .pw-hs-doc, .pw-hs-offerbox, .pw-hs-oneshop'),
      label: (el.getAttribute('aria-label') || el.getAttribute('placeholder') || el.innerText || '').trim().replace(/\s+/g, ' ').slice(0, 32),
      x: r.left, y: r.top + scrollY, w: r.width, h: r.height }; });
  const texts = [];
  const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n = walk.nextNode(); n; n = walk.nextNode()) {
    const t = n.nodeValue.replace(/\s+/g, ' ').trim(); if (!t) continue;
    const el = n.parentElement; if (!el || !vis(el) || el.closest('script, style')) continue;
    const s = getComputedStyle(el); if (s.position === 'absolute' && s.clip !== 'auto') continue;
    const range = document.createRange(); range.selectNodeContents(n);
    if (![...range.getClientRects()].some(r => r.width > 0 && r.height > 0)) continue;
    texts.push({ t: t.slice(0, 28), size: parseFloat(s.fontSize) });
  }
  const wide = [...document.querySelectorAll('body *')].filter(vis).filter(el => !scroller(el)).filter(el => {
    const r = el.getBoundingClientRect(); return r.right > innerWidth + 0.5 || r.left < -0.5; }).length;
  const broken = [...document.images].filter(i => i.getAttribute('src') && i.getAttribute('src').startsWith('/') && (!i.complete || !i.naturalWidth)).length;
  return { targets, texts, wide, broken, height: document.documentElement.scrollHeight };
}
"""

# Before the page's own scripts: what Google's three measures are read from.
WATCH = r"""
window.__look = { lcp: null, cls: 0, tap: 0 };
new PerformanceObserver((l) => { for (const e of l.getEntries()) window.__look.lcp = e.startTime; }).observe({ type: 'largest-contentful-paint', buffered: true });
new PerformanceObserver((l) => { for (const e of l.getEntries()) if (!e.hadRecentInput) window.__look.cls += e.value; }).observe({ type: 'layout-shift', buffered: true });
try { new PerformanceObserver((l) => { for (const e of l.getEntries()) window.__look.tap = Math.max(window.__look.tap, e.duration); }).observe({ type: 'event', durationThreshold: 16 }); } catch (e) {}
"""
READ = r"""
() => { const out = Object.assign({ fcp: null }, window.__look);
  for (const e of performance.getEntriesByType('paint')) { if (e.name === 'first-contentful-paint') out.fcp = e.startTime; }
  return out; }
"""


def measures(found: dict) -> str:
    targets = found["targets"]
    small = [t for t in targets if t["w"] < 47.5 or t["h"] < 47.5]
    own_small = [t for t in small if t["own"]]
    near = 0
    own_near: list[str] = []
    for a in targets:
        for b in targets:
            if a["i"] >= b["i"]:
                continue
            ox = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
            oy = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
            if (ox > 0 and oy > 0) or (oy > 0 and 0 <= -ox < 7.5) or (ox > 0 and 0 <= -oy < 7.5):
                near += 1
                if a["own"] and b["own"]:
                    own_near.append(f"{a['label'][:16]}|{b['label'][:16]}")
    tiny = sorted({f"{t['size']:.0f}px {t['t'][:18]}" for t in found["texts"] if t["size"] < 11.99})
    line = (f"{found['height']:>6,} px tall; tapped {len(targets):>3}: under 48 px {len(small)} (the store's own {len(own_small)}), "
            f"nearer than 8 px {near} (the store's own {len(own_near)}); words under 12 px {len(tiny)}; wider than the screen "
            f"{found['wide']}; site pictures not loaded {found['broken']}")
    for label, items in (("own under 48", [f"{t['label']} {t['w']:.0f}x{t['h']:.0f}" for t in own_small]), ("own near", own_near),
                         ("under 12 px", tiny)):
        if items:
            line += f"\n        {label}: " + "; ".join(items[:6])
    return line


def main(argv: list[str]) -> int:
    pages = Path(argv[1]).resolve()
    names = sorted(p.stem for p in pages.glob("*.html"))
    if not names:
        print("no page to measure")
        return 1
    assets = pages / "assets"
    if not assets.exists():
        os.symlink(ROOT / "assets", assets)
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args: object) -> None:  # the log is the measures' alone
            return

    handler = functools.partial(Quiet, directory=str(pages))
    http.server.ThreadingHTTPServer.allow_reuse_address = True
    server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{PORT}"
    refused = [0]

    def only_here(route):  # nothing but this folder is asked: no shop, no other host
        if route.request.url.startswith(base):
            route.continue_()
        else:
            refused[0] += 1
            route.abort()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=CHROME, args=["--no-sandbox", "--no-proxy-server"])
        for name in names:
            print(f"\n{name}")
            for label, width, height, touch in VIEWS:
                context = browser.new_context(viewport={"width": width, "height": height}, has_touch=touch, is_mobile=touch)
                context.route("**/*", only_here)
                page = context.new_page()
                errors: list[str] = []
                page.on("pageerror", lambda error: errors.append(str(error)[:90]))
                page.goto(f"{base}/{name}.html")
                page.wait_for_load_state("load")
                page.evaluate("async()=>{for(let y=0;y<document.documentElement.scrollHeight;y+=500){scrollTo(0,y);await new Promise(r=>setTimeout(r,30));}scrollTo(0,0);}")
                page.wait_for_timeout(250)
                print(f"    {label:13} {measures(page.evaluate(COLLECT))}" + (f"\n        SCRIPT ERRORS: {errors[:3]}" if errors else ""))
                context.close()
        # Google's three, the home page on a phone four times slower, on a slow 4G line.
        for name in [n for n in ("home", "department_kitchen", "search_kettle") if n in names]:
            context = browser.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
            context.route("**/*", only_here)
            page = context.new_page()
            page.add_init_script(WATCH)
            session = context.new_cdp_session(page)
            session.send("Network.enable")
            session.send("Network.emulateNetworkConditions", {"offline": False, "latency": 150,
                                                              "downloadThroughput": 1.6 * 1024 * 1024 / 8,
                                                              "uploadThroughput": 750 * 1024 / 8})
            session.send("Emulation.setCPUThrottlingRate", {"rate": 4})
            page.goto(f"{base}/{name}.html")
            page.wait_for_load_state("load")
            page.wait_for_timeout(1500)
            taps = []
            # Taps that stay on the page: the month's ten opened, the first of the header's panels.
            for selector in ("#pw-tp-more", ".pw-hs-head button[aria-controls]", "details.pw-hs-of-terms summary"):
                target = page.locator(selector).first
                try:
                    if target.count() and target.is_visible():
                        target.tap(timeout=3000, no_wait_after=True)
                        taps.append(selector)
                        page.wait_for_timeout(600)
                except Exception:  # a measure only
                    pass
            vitals = page.evaluate(READ)
            size = (pages / f"{name}.html").stat().st_size
            print(f"\n{name} on a slow phone ({size / 1024:.0f} KB of page): first paint "
                  f"{(vitals['fcp'] or 0) / 1000:.2f} s, largest paint {(vitals['lcp'] or 0) / 1000:.2f} s, layout shift "
                  f"{vitals['cls']:.3f}, the slowest tap answered in {vitals['tap']:.0f} ms (tapped: {', '.join(taps) or 'nothing'})")
            context.close()
        browser.close()
    server.shutdown()
    print(f"\nrequests to other hosts refused (shops' photos and the like): {refused[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
