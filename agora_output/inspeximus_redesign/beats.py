"""Screenshot the scroll story at fixed progress points in both copies, side by side.

Usage: python beats.py   (writes shots/beats_compare.jpg and per-beat PNGs)
Progress is measured on .narrative exactly as the site's ScrollTrigger does:
start = top of .narrative at top of viewport, end = its bottom at viewport bottom.
"""
import functools
import http.server
import socketserver
import threading
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent
OUT = ROOT / "shots"
POINTS = (0.0, 0.38, 0.66, 0.92)


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def shoot(folder, label, pw):
    httpd = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(ROOT / folder)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    browser = pw.chromium.launch(channel="msedge", args=["--use-angle=d3d11", "--enable-gpu"])
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto(f"http://127.0.0.1:{httpd.server_address[1]}/index.html", wait_until="networkidle")
    page.wait_for_timeout(2500)
    span = page.evaluate(
        "() => { const n = document.querySelector('.narrative'); const r = n.getBoundingClientRect();"
        " return [r.top + scrollY, n.offsetHeight - innerHeight]; }"
    )
    files = []
    for t in POINTS:
        y = span[0] + span[1] * t
        # walk there in steps so Lenis and the scrubbed camera settle
        page.evaluate(f"window.scrollTo(0, {y})")
        page.wait_for_timeout(2500)
        f = OUT / f"beat_{label}_{int(t * 100):02d}.png"
        page.screenshot(path=str(f))
        files.append(f)
    print(label, "narrative scroll length px:", int(span[1]))
    browser.close()
    httpd.shutdown()
    return files


with sync_playwright() as pw:
    old = shoot("original", "orig", pw)
    new = shoot("v2", "v2", pw)

w, h = 720, 450
sheet = Image.new("RGB", (w * 2 + 20, (h + 20) * len(POINTS)), "white")
for i, (a, b) in enumerate(zip(old, new)):
    sheet.paste(Image.open(a).resize((w, h)), (0, i * (h + 20)))
    sheet.paste(Image.open(b).resize((w, h)), (w + 20, i * (h + 20)))
sheet.save(OUT / "beats_compare.jpg", quality=85)
