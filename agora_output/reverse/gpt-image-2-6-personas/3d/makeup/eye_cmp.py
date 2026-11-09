"""Eye close-up sheet: p6 on top, then each named render (frame) below. Usage: eye_cmp.py out.png label=path ..."""
import sys
from PIL import Image, ImageDraw
p6 = Image.open('beauty/depesa_p6.png').convert('RGB').crop((330, 330, 900, 520)).resize((1140, 380), Image.LANCZOS)
rows = [('p6 (predloha)', p6)]
for a in sys.argv[2:]:
    lab, path = a.split('=', 1)
    rows.append((lab, Image.open(path).convert('RGB').crop((300, 490, 780, 650)).resize((1140, 380), Image.LANCZOS)))
W = Image.new('RGB', (1140, len(rows) * 410), 'black'); d = ImageDraw.Draw(W)
for i, (l, im) in enumerate(rows):
    W.paste(im, (0, i * 410 + 30)); d.text((10, i * 410 + 8), l, fill='white')
W.save(sys.argv[1])
