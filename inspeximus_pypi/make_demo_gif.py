from PIL import Image, ImageDraw, ImageFont
import os

W, H = 800, 500
BG = (20, 23, 31)
FG = (236, 233, 226)
AMBER = (255, 180, 84)
GREEN = (100, 200, 100)
RED = (220, 80, 80)
BLUE = (127, 168, 201)
DIM = (155, 160, 173)

frames = []

def make_frame(lines, title=""):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    # title
    d.text((40, 30), title, fill=AMBER, font=ImageFont.load_default())
    # code lines
    y = 90
    for text, color in lines:
        d.text((40, y), text, fill=color, font=ImageFont.load_default())
        y += 40
    return img

# Frame 1: remember
frames.append(make_frame([
    ("$ python demo.py", FG),
    (">>> m.remember(\"The sky is blue.\", key=\"sky\")", FG),
    ("", FG),
    ("[stored] sky = blue", GREEN),
], "inspeximus — remember"))

# Frame 2: correct
frames.append(make_frame([
    ("$ python demo.py", FG),
    (">>> m.remember(\"The sky is now green.\", key=\"sky\")", FG),
    ("", FG),
    ("[superseded] sky: blue -> green", AMBER),
    ("[current] sky = green", GREEN),
], "inspeximus — correct"))

# Frame 3: revert
frames.append(make_frame([
    ("$ python demo.py", FG),
    (">>> m.revert(\"sky\")", FG),
    ("", FG),
    ("[reverted] sky: green -> blue", AMBER),
    ("[current] sky = blue", GREEN),
], "inspeximus — revert"))

# Frame 4: recall
frames.append(make_frame([
    ("$ python demo.py", FG),
    (">>> m.recall(\"what color is the sky?\")", FG),
    ("", FG),
    ("[recall] sky = blue", GREEN),
    ("[echo_guard] old value blocked", BLUE),
], "inspeximus — recall"))

# Frame 5: audit
frames.append(make_frame([
    ("$ python demo.py", FG),
    (">>> m.history(\"sky\")", FG),
    ("", FG),
    ("[history]", AMBER),
    ("  1. blue (stored)", FG),
    ("  2. green (superseded)", FG),
    ("  3. blue (reverted)", FG),
], "inspeximus — audit"))

# Save GIF
out = os.path.join("inspeximus_pypi", "demo.gif")
frames[0].save(out, save_all=True, append_images=frames[1:], duration=1500, loop=0)
print(f"GIF saved: {out}")
