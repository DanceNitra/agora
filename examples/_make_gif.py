#!/usr/bin/env python3
"""Render examples/demo.gif — an animated terminal GIF of the second_brain demo, straight from its
real output. No vhs/ffmpeg/asciinema needed (Pillow only). Re-run after changing the demo."""
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
BG = (30, 30, 46); FG = (205, 214, 244); DIM = (127, 132, 156)
CYAN = (137, 220, 235); GREEN = (166, 227, 161); YELLOW = (249, 226, 175); WHITE = (235, 239, 250)

FONT_PATH = next((p for p in ["C:/Windows/Fonts/CascadiaMono.ttf", "C:/Windows/Fonts/consola.ttf",
                              "C:/Windows/Fonts/cour.ttf"] if os.path.exists(p)), None)
SIZE = 18
font = ImageFont.truetype(FONT_PATH, SIZE)
LH = SIZE + 7
PAD = 26

# Each line is a list of (text, color) segments. Grouped into reveal "steps".
S = [
 [[("$ python examples/demo.py", WHITE)]],
 [[("", FG)], [("second_brain — your notes, thinking", WHITE)],
  [("the server gives the agent retrieval + structure; the agent reasons", DIM)]],
 [[("", FG)], [("▸ relevant_notes(\"how does feedback speed up learning\")", CYAN)],
  [("  → Deliberate Practice  (Learning)   relevance ", FG), ("0.60", GREEN)],
  [("  → Expected Value       (Decisions)  relevance ", FG), ("0.20", GREEN)]],
 [[("", FG)], [("▸ find_gaps()", CYAN)],
  [("  → isolated: ", FG), ("[\"Sourdough Starter\"]", YELLOW), ("   the only note with no links", DIM)]],
 [[("", FG)], [("▸ bridge_candidates(\"Deliberate Practice\")", CYAN)],
  [("  → Habit Loops  (Habits · ", FG), ("DISTANT domain", YELLOW), (")", FG)],
  [("    both turn on \"feedback latency\" — and nothing links them", DIM)]],
 [[("", FG)], [("▸ extract_claims(\"Deliberate Practice\")", CYAN)],
  [("  → \"Feedback latency is the hidden variable…\"  ", FG), ("(line 3)", DIM)]],
 [[("", FG)], [("▸ idea_methods()  → ", CYAN), ("10 recipes to generate ideas", FG)]],
 [[("", FG)], [("The tool found the material. Your agent does the thinking.", GREEN)]],
]

# accumulate lines per frame
frames_lines = []
acc = []
for step in S:
    acc = acc + step
    frames_lines.append(list(acc))

W = 1000
H = PAD * 2 + LH * (len(acc) + 1)

def render(lines):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    # title bar dots
    for i, c in enumerate([(237, 106, 94), (245, 191, 79), (98, 197, 84)]):
        d.ellipse([PAD + i * 22, 14, PAD + 12 + i * 22, 26], fill=c)
    y = 40
    for segs in lines:
        x = PAD
        for text, color in segs:
            d.text((x, y), text, font=font, fill=color)
            x += d.textlength(text, font=font)
        y += LH
    return img

frames = [render(fl) for fl in frames_lines]
# hold the first frame a touch, the last frame long
durations = [700] + [1000] * (len(frames) - 2) + [3200]
out = HERE / "demo.gif"
frames[0].save(out, save_all=True, append_images=frames[1:], duration=durations,
               loop=0, optimize=True)
print("wrote", out, f"({out.stat().st_size//1024} KB, {len(frames)} frames, {W}x{H})")
