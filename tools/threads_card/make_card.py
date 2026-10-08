"""Render a Threads card (1080x1350 PNG) and a phone mockup for one campaign post.

The card repeats only sentences that are already in the post text, so it adds no claim.
The seal band shows the tail given by --band; the real band is the log root tail after sealing.
"""
import argparse, html, pathlib, re, subprocess, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "seal"))
from seal_draft import replace_band  # noqa: E402

FONTS = ("https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700"
         "&family=JetBrains+Mono:wght@400;500;600&display=swap")

CARD = """<!doctype html><meta charset=utf-8><link rel=stylesheet href="{fonts}">
<style>
*{{margin:0;box-sizing:border-box}}
body{{width:1080px;height:1350px;background:#0a0a0b;color:#e9edf2;font-family:'Space Grotesk',sans-serif;
 padding:104px 96px 96px;display:flex;flex-direction:column;position:relative;overflow:hidden}}
.eyebrow{{font-family:'JetBrains Mono',monospace;font-size:36px;letter-spacing:.06em;color:#38f2d6;text-transform:uppercase;line-height:1.35;margin-bottom:72px}}
.eyebrow span{{color:#8a909c}}
h1{{font-size:{h1}px;line-height:1.04;text-wrap:balance;font-weight:600;letter-spacing:-.025em;margin-top:auto}}
p{{font-size:54px;line-height:1.3;color:#8a909c;margin-top:48px;max-width:880px;margin-bottom:72px}}
p b{{color:#e9edf2;font-weight:500}}
.code{{font-family:'JetBrains Mono',monospace;font-size:38px;line-height:1.6;background:#131418;border:2px solid rgba(255,255,255,.09);border-radius:20px;padding:30px 36px;margin-bottom:72px;color:#e9edf2;white-space:pre}}
.code i{{color:#38f2d6;font-style:normal}}
.foot{{margin-top:auto;padding-top:0;display:flex;align-items:center;gap:44px;border-top:2px solid rgba(255,255,255,.09);padding-top:64px;}}
.seal{{width:250px;height:auto;flex:none}}
.word{{font-size:72px;font-weight:600;letter-spacing:-.02em}}
.tag{{font-family:'JetBrains Mono',monospace;font-size:38px;color:#8a909c;margin-top:14px}}
</style>
<div class=eyebrow>{eyebrow}</div>
<h1>{headline}</h1>
<p>{body}</p>{code}
<div class=foot><img class=seal src="data:image/svg+xml;base64,{seal}"><div>
<div class=word>inspeximus</div><div class=tag>Memory with receipts.</div></div></div>"""

PHONE = """<!doctype html><meta charset=utf-8><style>
*{{margin:0;box-sizing:border-box}}
body{{width:390px;background:{bg};color:{fg};font:15px/1.4 -apple-system,'Segoe UI',Roboto,sans-serif;padding:12px 0}}
.post{{display:flex;gap:10px;padding:12px 14px;border-bottom:1px solid {line}}}
.av{{width:36px;height:36px;border-radius:50%;background:#0a0a0b;flex:none;display:grid;place-items:center;border:1px solid {line}}}
.av img{{width:26px}}
.n{{font-weight:600}} .n span{{color:{mut};font-weight:400;margin-left:6px}}
.t{{white-space:pre-wrap;margin-top:2px}}
.img{{margin-top:10px;width:100%;border-radius:10px;border:1px solid {line};display:block}}
.topic{{color:{mut};font-size:13px;margin-top:2px}}
.act{{display:flex;gap:22px;color:{mut};font-size:13px;margin-top:10px}}
</style><div class=post><div class=av><img src="data:image/svg+xml;base64,{seal}"></div><div style="min-width:0">
<div class=n>inspeximus<span>&rsaquo; {topic} &middot; 1m</span></div>
<div class=t>{text}</div><img class=img src="{card}">
<div class=act><span>&#9825;</span><span>&#9711;</span><span>&#8635;</span><span>&#10148;</span></div></div></div>"""


def shoot(html_path, png, w, h, scale=1.0, full=False):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        pg = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=scale)
        pg.goto(pathlib.Path(html_path).resolve().as_uri()); pg.wait_for_timeout(1500)
        pg.screenshot(path=str(png), full_page=full); b.close()


def main():
    import base64
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--eyebrow", required=True); ap.add_argument("--headline", required=True)
    ap.add_argument("--body", required=True); ap.add_argument("--band", required=True)
    ap.add_argument("--seal", required=True, help="dark seal SVG to take the art from")
    ap.add_argument("--h1", type=int, default=116)
    ap.add_argument("--topic", required=True)
    ap.add_argument("--code", action="append", default=[], help="one command line, must be in the post")
    a = ap.parse_args()
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    text = pathlib.Path(a.text).read_text(encoding="utf-8")
    for s in [a.headline, re.sub(r"<[^>]+>", "", a.body)] + a.code:
        if s not in text:
            sys.exit("card sentence not in the post text: %r" % s)
    seal = replace_band(pathlib.Path(a.seal).read_text(encoding="utf-8"), a.band)
    s64 = base64.b64encode(seal.encode()).decode()
    (out / "card.html").write_text(CARD.format(fonts=FONTS, eyebrow=a.eyebrow, headline=html.escape(a.headline),
                                              body=a.body, seal=s64, h1=a.h1,
                                              code=('<div class=code>' + '\n'.join('<i>$</i> ' + html.escape(c) for c in a.code) + '</div>') if a.code else ''), encoding="utf-8")
    shoot(out / "card.html", out / "card.png", 1080, 1350)
    for mode, bg, fg, mut, line in (("dark", "#101010", "#f3f5f7", "#777", "#2a2a2a"),
                                    ("light", "#ffffff", "#000000", "#999", "#e5e5e5")):
        f = out / ("phone_%s.html" % mode)
        f.write_text(PHONE.format(topic=html.escape(a.topic), bg=bg, fg=fg, mut=mut, line=line, seal=s64, text=html.escape(text),
                                  card="card.png"), encoding="utf-8")
        shoot(f, out / ("phone_%s.png" % mode), 390, 844, scale=3, full=True)
    print("ok", out)


if __name__ == "__main__":
    main()
