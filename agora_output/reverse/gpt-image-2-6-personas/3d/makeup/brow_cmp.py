"""Brow close-up sheet: p6 brows on top, each named render below. Usage: brow_cmp.py out.png label=path ..."""
import sys
from PIL import Image, ImageDraw
p6 = Image.open('beauty/depesa_p6.png').convert('RGB').crop((300, 300, 920, 470)).resize((1140, 312), Image.LANCZOS)
rows = [('p6 (predloha)', p6)]
for a in sys.argv[2:]:
    lab, path = a.split('=', 1)
    rows.append((lab, Image.open(path).convert('RGB').crop((300, 440, 780, 571)).resize((1140, 312), Image.LANCZOS)))
W = Image.new('RGB', (1140, len(rows) * 342), 'black'); d = ImageDraw.Draw(W)
for i, (l, im) in enumerate(rows):
    W.paste(im, (0, i * 342 + 30)); d.text((10, i * 342 + 8), l, fill='white')
W.save(sys.argv[1])
