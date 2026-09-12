from PIL import Image, ImageDraw, ImageFont
import os

W, H = 900, 600
BG = (5, 5, 6)
TEAL = (56, 242, 214)
GRAY = (146, 149, 152)
DARK_GRAY = (82, 84, 86)
FG = (236, 233, 226)
DIM = (155, 160, 173)
RED = (220, 80, 80)

frames = []

def draw_text(d, x, y, text, color=FG, size=18, bold=False):
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf", size)
    except:
        font = ImageFont.load_default()
    d.text((x, y), text, fill=color, font=font)

def draw_chat_bubble(d, x, y, w, h, color, text, text_color=FG):
    d.rounded_rectangle([x, y, x+w, y+h], radius=33, fill=color)
    draw_text(d, x+25, y+20, text, color=text_color, size=16)

def make_frame(step, title, subtitle, left_bubbles, right_bubbles, status_text, status_color):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # Header
    draw_text(d, 40, 30, "inspeximus", color=TEAL, size=24, bold=True)
    draw_text(d, 40, 62, title, color=FG, size=20, bold=True)
    draw_text(d, 40, 90, subtitle, color=DIM, size=14)

    # Left column: WITHOUT
    draw_text(d, 40, 140, "WITHOUT INSPEXIMUS", color=GRAY, size=12, bold=True)
    y = 170
    for text, color in left_bubbles:
        w = min(380, 200 + len(text) * 7)
        draw_chat_bubble(d, 40, y, w, 60, color, text)
        y += 80

    # Right column: WITH
    draw_text(d, 480, 140, "WITH INSPEXIMUS", color=TEAL, size=12, bold=True)
    y = 170
    for text, color in right_bubbles:
        w = min(380, 200 + len(text) * 7)
        draw_chat_bubble(d, 480, y, w, 60, color, text)
        y += 80

    # Status bar
    d.rounded_rectangle([40, 500, 860, 560], radius=30, fill=(20, 23, 31))
    draw_text(d, 60, 520, status_text, color=status_color, size=16, bold=True)

    # Step indicator
    draw_text(d, 40, 570, f"Step {step+1}/4", color=DIM, size=12)

    return img

# Frame 1: The problem
frames.append(make_frame(0,
    "The problem: agents remember the OLD answer",
    "Your agent stores a fact. The fact changes. The agent keeps using the old one.",
    [("I prefer dark mode.", GRAY), ("Got it. Dark mode.", DARK_GRAY)],
    [("I prefer dark mode.", TEAL), ("Got it. Dark mode.", TEAL)],
    "Both agents store: theme = dark",
    TEAL))

# Frame 2: The correction
frames.append(make_frame(1,
    "The correction: the fact changes",
    "The user updates their preference. Most memory layers just append the new fact.",
    [("Actually, light mode now.", GRAY), ("Got it. Light mode.", DARK_GRAY)],
    [("Actually, light mode now.", TEAL), ("Got it. Light mode.", TEAL)],
    "inspeximus supersedes: theme = light",
    TEAL))

# Frame 3: The recall — THE MOMENT
frames.append(make_frame(2,
    "The recall: the RIGHT answer",
    "A week later, the user asks. Without inspeximus, the agent answers WRONG.",
    [("What theme do I prefer?", GRAY), ("Dark mode.", RED)],
    [("What theme do I prefer?", TEAL), ("Light mode.", TEAL)],
    "inspeximus returns the CURRENT value — not the stale one",
    TEAL))

# Frame 4: The audit
frames.append(make_frame(3,
    "The audit: full history",
    "Every change is recorded. You can prove what happened, when, and why.",
    [("Show me the history.", GRAY), ("1. dark  2. light  3. dark", DARK_GRAY)],
    [("Show me the history.", TEAL), ("1. dark  2. light  3. dark", TEAL)],
    "Full audit trail: 3 changes, all verifiable",
    TEAL))

# Save
out = os.path.join("inspeximus_pypi", "demo.gif")
frames[0].save(out, save_all=True, append_images=frames[1:], duration=3000, loop=0)
print(f"GIF saved: {out} ({os.path.getsize(out)} bytes)")
