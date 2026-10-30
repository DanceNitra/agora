"""Screenshot a local copy of the inspeximus homepage at desktop and mobile widths.

Usage: python shoot.py <folder> <label>
Serves <folder> on a free port, captures a hero shot and a full page (reduced motion,
so scroll-scrubbed panels render stacked), and reports horizontal overflow.
"""
import functools
import http.server
import socketserver
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

folder, label = Path(sys.argv[1]).resolve(), sys.argv[2]
out = Path(__file__).parent / "shots"
out.mkdir(exist_ok=True)

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
handler = functools.partial(Quiet, directory=str(folder))
httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
port = httpd.server_address[1]
threading.Thread(target=httpd.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{port}/index.html"

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge")
    for name, w, h in (("desktop", 1440, 900), ("mobile", 390, 844)):
        ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=1)
        page = ctx.new_page()
        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(2500)
        page.screenshot(path=str(out / f"{label}_{name}_hero.png"))
        ctx.close()
        ctx = browser.new_context(viewport={"width": w, "height": h}, reduced_motion="reduce")
        page = ctx.new_page()
        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(1500)
        for y in range(0, page.evaluate("document.body.scrollHeight"), 600):
            page.evaluate(f"window.scrollTo(0,{y})"); page.wait_for_timeout(60)
        page.wait_for_timeout(1500); page.evaluate("window.scrollTo(0,0)")
        overflow = page.evaluate(
            "() => [document.documentElement.scrollWidth, innerWidth,"
            " [...document.querySelectorAll('body *')].filter(e => e.getBoundingClientRect().right > innerWidth + 1)"
            ".slice(0, 5).map(e => e.tagName + '.' + e.className)]"
        )
        print(label, name, "scrollWidth/innerWidth:", overflow[0], overflow[1], "overflowing:", overflow[2])
        page.screenshot(path=str(out / f"{label}_{name}_full.png"), full_page=True)
        ctx.close()
    browser.close()
httpd.shutdown()
