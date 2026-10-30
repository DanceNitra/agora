"""Compose the step-03 concept sheet in the layout seen in the video at 35.8 s and 37.5 s.

Title block, a large hero view, five angle views, colour swatches and a row of detail close-ups,
on white with an orange frame. Needs Pillow: run it with C:\\ComfyUI\\venv\\Scripts\\python.exe.

Usage: python compose_sheet.py [build/03_sheet dir]
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

SRC = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\Danculus\agora\agora_output\reverse\blender_spider_xCkjVUtVDEw\build\03_sheet"
HERO = "hero_refine_04_s18223.png"
VIEWS = [("front.png", "FRONT VIEW"), ("side.png", "SIDE VIEW"), ("rear_three_quarter.png", "REAR THREE QUARTER"),
         ("low_angle.png", "LOW ANGLE VIEW"), ("high_angle.png", "HIGH ANGLE VIEW")]
DETAILS = [("detail_sensor.png", "SENSOR CLUSTER"), ("detail_joint.png", "SHOULDER JOINT"),
           ("detail_foot.png", "FOOT / CONTACT TIP"), ("detail_underside.png", "UNDERSIDE DETAIL"),
           ("detail_rear.png", "REAR BODY")]
SWATCHES = [(226, 96, 28), (24, 24, 26), (168, 170, 172)]

ORANGE = (240, 110, 20)
INK = (40, 40, 42)
MUTED = (130, 130, 134)
PAPER = (246, 244, 240)
W, H = 3200, 2240
FONT = r"C:\Windows\Fonts\arial.ttf"
BOLD = r"C:\Windows\Fonts\arialbd.ttf"


def spaced(draw, xy, text, font, fill, gap):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + gap


def fit(path, w, h):
    im = Image.open(os.path.join(SRC, path)).convert("RGB")
    r = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    left, top = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((left, top, left + w, top + h))


def main():
    sheet = Image.new("RGB", (W, H), (18, 18, 20))
    d = ImageDraw.Draw(sheet)
    d.rectangle([30, 30, W - 30, H - 30], fill=ORANGE)
    d.rectangle([42, 42, W - 42, H - 42], fill=PAPER)
    title, sub, label = ImageFont.truetype(FONT, 76), ImageFont.truetype(FONT, 26), ImageFont.truetype(BOLD, 24)

    spaced(d, (90, 80), "QUAD WALKER", title, INK, 14)
    spaced(d, (94, 178), "EXPLORATION ROBOT", sub, MUTED, 9)
    d.line([(860, 122), (1180, 122)], fill=(200, 200, 200), width=2)

    sheet.paste(fit(HERO, 1600, 1066), (90, 240))
    spaced(d, (100, 1330), "HERO VIEW", label, INK, 6)
    spaced(d, (100, 1364), "THREE QUARTER", ImageFont.truetype(FONT, 20), MUTED, 5)

    tw, th, x0, y0 = 680, 453, 1755, 90
    slots = [(x0 + c * (tw + 30), y0 + r * (th + 70)) for r in range(3) for c in range(2)]
    for (path, name), (x, y) in zip(VIEWS, slots):
        sheet.paste(fit(path, tw, th), (x, y))
        spaced(d, (x + 6, y + th + 14), name, label, INK, 5)

    sx, sy = slots[5]
    for i, c in enumerate(SWATCHES):
        cx = sx + 200 + i * 130
        d.ellipse([cx - 45, sy + 160, cx + 45, sy + 250], fill=c)
    spaced(d, (sx + 186, sy + 290), "COLOR & MATERIAL", label, INK, 5)
    spaced(d, (sx + 150, sy + 326), "SATIN ORANGE / GRAPHITE / BRUSHED METAL", ImageFont.truetype(FONT, 18), MUTED, 3)

    dw, dh, dy = 586, 390, 1730
    for i, (path, name) in enumerate(DETAILS):
        x = 90 + i * (dw + 20)
        sheet.paste(fit(path, dw, dh), (x, dy))
        spaced(d, (x + 6, dy + dh + 14), name, label, INK, 5)

    out = os.path.join(SRC, "concept_sheet.png")
    sheet.save(out)
    sheet.resize((W // 2, H // 2), Image.LANCZOS).save(os.path.join(SRC, "concept_sheet_preview.jpg"), quality=88)
    print(out)


if __name__ == "__main__":
    main()
