"""Hero + full-page shots of the 7 subpages in both copies; writes shots/sub_<page>_compare.jpg."""
import functools, http.server, socketserver, threading
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent
OUT = ROOT / "shots"
PAGES = "quickstart compare ai-act erasure audit-trail claude-code migrate-from-mem0".split()


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve(folder):
    h = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(ROOT / folder)))
    threading.Thread(target=h.serve_forever, daemon=True).start()
    return h


with sync_playwright() as pw:
    b = pw.chromium.launch(channel="msedge")
    for folder in ("original", "v2"):
        h = serve(folder)
        for w, tag in ((1440, "d"), (390, "m")):
            pg = b.new_page(viewport={"width": w, "height": 900})
            for p in PAGES:
                pg.goto(f"http://127.0.0.1:{h.server_address[1]}/{p}.html", wait_until="networkidle")
                pg.wait_for_timeout(600)
                sw = pg.evaluate("document.documentElement.scrollWidth")
                if sw > w:
                    print("OVERFLOW", folder, p, tag, sw)
                pg.screenshot(path=str(OUT / f"sub_{folder}_{p}_{tag}.png"), full_page=True)
            pg.close()
        h.shutdown()
    b.close()

for p in PAGES:
    a = Image.open(OUT / f"sub_original_{p}_d.png")
    v = Image.open(OUT / f"sub_v2_{p}_d.png")
    H = 2400  # first 2400 px of each page, side by side
    a, v = a.crop((0, 0, 1440, min(H, a.height))), v.crop((0, 0, 1440, min(H, v.height)))
    c = Image.new("RGB", (2900, H), "white")
    c.paste(a, (0, 0)); c.paste(v, (1460, 0))
    c.resize((1160, int(H * 1160 / 2900))).save(OUT / f"sub_{p}_compare.jpg", quality=82)
print("done")
