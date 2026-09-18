#!/usr/bin/env python3
"""Render public/og-card.png, the homepage's 1200 x 630 share image, from the live Crucible ledger.

The card that sat here from 2026-07-12 carried the product's old name and counts frozen at
render time; a stale image is what LinkedIn, X and Slack show for the whole site, and nobody
reads an image in a review. This script reads the counts from public/crucible/crucible.json so
the card cannot disagree with the ledger, and the deploy gate can compare the two.

    python tools/og_card.py            write public/og-card.png
    python tools/og_card.py --check    exit 1 when the card's recorded counts differ from the ledger

Design: the storefront's paper and ink, the serif wordmark, one mono line. No gradients, no
glow, no icons (owner rule).
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
CARD = ROOT / "public" / "og-card.png"
STAMP = ROOT / "public" / "og-card.json"
LEDGER = ROOT / "public" / "crucible" / "crucible.json"
W, H = 1200, 630
PAPER, INK, SOFT, ACC, LINE = "#fbf9f4", "#1b1a17", "#54514a", "#0a8f68", "#e6e1d6"


def counts() -> dict:
    d = json.loads(LEDGER.read_text(encoding="utf-8"))
    items = d if isinstance(d, list) else next((v for v in d.values() if isinstance(v, list)), [])
    c = collections.Counter((i.get("verdict") or i.get("status") or "?") for i in items)
    return {"tested": len(items), "reproduced": c.get("REPRODUCED", 0), "failed": c.get("FAILED", 0)}


def _font(names: list[str], size: int) -> ImageFont.FreeTypeFont:
    for n in names:
        for d in (Path("C:/Windows/Fonts"), Path.home() / "AppData/Local/Microsoft/Windows/Fonts"):
            p = d / n
            if p.exists():
                return ImageFont.truetype(str(p), size)
    return ImageFont.load_default(size)


def render(c: dict) -> Image.Image:
    im = Image.new("RGB", (W, H), PAPER)
    dr = ImageDraw.Draw(im)
    serif = _font(["georgia.ttf", "times.ttf"], 132)
    serif_s = _font(["georgia.ttf", "times.ttf"], 44)
    mono = _font(["consola.ttf", "cour.ttf"], 26)
    dr.text((80, 130), "Agora", font=serif, fill=INK)
    dr.text((84, 300), "Agent-memory research", font=serif_s, fill=INK)
    dr.text((84, 352), "that ships receipts.", font=serif_s, fill=INK)
    dr.line([(80, 440), (1120, 440)], fill=LINE, width=2)
    line1 = f"inspeximus  \u00b7  {c['tested']} claims tested, {c['reproduced']} reproduced, {c['failed']} failed"
    line2 = "every design rule ships a measured receipt"
    dr.text((84, 466), line1, font=mono, fill=SOFT)
    dr.text((84, 506), line2, font=mono, fill=SOFT)
    dr.rectangle([(1040, 466), (1120, 474)], fill=ACC)
    return im


def main() -> int:
    c = counts()
    if "--check" in sys.argv:
        if not STAMP.exists():
            print("og-card: no stamp; run tools/og_card.py"); return 1
        s = json.loads(STAMP.read_text(encoding="utf-8"))
        if s != c:
            print(f"og-card: card says {s}, ledger says {c}; run tools/og_card.py"); return 1
        print("og-card: counts match the ledger"); return 0
    render(c).save(CARD, optimize=True)
    STAMP.write_text(json.dumps(c), encoding="utf-8")
    print(f"wrote {CARD} {c}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
