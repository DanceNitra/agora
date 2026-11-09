"""Look library: named base looks (from the NotebookLM trend catalogue and the @luvpauli breakdown) and a
deterministic generator of variants (intensity x lip palette x eye palette x blush palette).

A look is {"id", "name", "family", "source", "layers": [...]} in the format of paint.paint().
"""
import itertools
import json

# ---- palettes (sRGB) ------------------------------------------------------------------------------
LIP = {
    "nude_brown": ([150, 96, 80], [120, 72, 60]),     # (fill, liner)
    "rose": ([176, 88, 92], [128, 66, 64]),
    "brick_rose": ([150, 62, 58], [110, 48, 44]),
    "classic_red": ([170, 30, 38], [130, 22, 30]),
    "berry": ([120, 34, 62], [90, 26, 46]),
    "espresso": ([96, 54, 44], [70, 40, 34]),
    "pink_frost": ([214, 150, 160], [160, 100, 100]),
    "taupe_mauve": ([176, 96, 108], [112, 70, 62]),   # rose-mauve fill, brown-taupe liner (audit 11-09: was ashy grey)
}
EYE = {
    "warm_brown": ([196, 150, 112], [120, 80, 56]),    # (lid, depth)
    "espresso": ([150, 108, 84], [60, 40, 32]),
    "pink_peach": ([236, 178, 168], [198, 120, 112]),
    "smoky_grey": ([170, 166, 170], [56, 54, 60]),
    "copper": ([210, 138, 90], [140, 70, 40]),
    "icy_silver": ([226, 230, 238], [150, 156, 170]),
    "white_pink": ([246, 236, 236], [226, 150, 160]),
}
BLUSH = {
    "pink": [236, 96, 140], "peach": [240, 150, 120], "terracotta": [196, 104, 80],
    "berry": [180, 70, 100], "rosy_mauve": [200, 120, 130],
}
CONTOUR_WARM, CONTOUR_COOL = [150, 100, 76], [128, 102, 92]
WHITE, BLACK, BROWN_LINER = [250, 248, 246], [16, 12, 12], [62, 40, 30]


def L(zone, color=None, opacity=0.5, blend="normal", rough=0.0, glitter=0.0, keep_l=None, **params):
    d = {"zone": zone, "opacity": opacity, "blend": blend, "params": params}
    if keep_l is not None:
        d["keep_l"] = keep_l
    if color is not None:
        d["color"] = list(color)
    if rough:
        d["rough"] = rough
    if glitter:
        d["glitter"] = glitter
    return d


def skin(finish="satin", conceal=0.35, tzone=0.2):
    """finish: matte (+rough) | satin | dewy (-rough) | glass (--rough)"""
    r = {"matte": 0.12, "satin": 0.0, "dewy": -0.12, "glass": -0.22}[finish]
    out = [L("foundation", opacity=0.0, rough=r, soft=0.4, even=0.35),
           L("conceal_undereye", [236, 200, 176], conceal, "color", soft=0.35)]
    if tzone:
        out.append(L("conceal_tzone", [236, 204, 182], tzone, "color", soft=0.35))
    return out


def sculpt(temp="warm", strength=0.3, nose=False, jaw=True):
    c = CONTOUR_WARM if temp == "warm" else CONTOUR_COOL
    out = [L("contour_cheek", c, strength, "multiply"), L("contour_temple", c, strength * 0.7, "multiply")]
    if jaw:
        out.append(L("contour_jaw", c, strength * 0.6, "multiply"))
    if nose:
        out.append(L("contour_nose", c, strength * 0.8, "multiply", soft=0.06))
    return out


def eyes(lid, depth, shape="soft", liner=None, lashline=0.0, inner=None, aegyo=0.0, glitter=0.0):
    out = [L("lid", lid, 0.45, "normal", soft=0.15), L("crease", depth, 0.35, "multiply", soft=0.2)]
    if shape in ("smoky", "cut"):
        out.append(L("outer_v", depth, 0.55, "multiply", soft=0.15))
    if lashline:
        out.append(L("lower_lash", depth, lashline, "multiply", part="outer", soft=0.08))
    if aegyo:
        out.append(L("aegyo_sal", [250, 236, 236], aegyo, "screen", soft=0.06, glitter=glitter))
    elif glitter:
        out.append(L("lid", [255, 250, 250], 0.0, glitter=glitter, height=0.3))
    if liner:
        out.append(L("liner", liner.get("color", BLACK), liner.get("opacity", 0.9), "normal",
                     wing_angle=liner.get("angle", 18), wing_len=liner.get("len", 0.25),
                     outer_w=liner.get("w", 0.06), soft=liner.get("soft", 0.03), lower=liner.get("lower", False)))
    if inner:
        out.append(L("inner_corner", inner, 0.7, "screen", soft=0.05))
    return out


def blush(color, placement="apple", strength=0.35, nose=False):
    return [L("blush", color, strength, "tint", keep_l=0.95, placement=placement, nose=nose, soft=0.45)]


def glow(spots=("cheek", "nose_bridge"), strength=0.25, rough=-0.15):
    return [L("highlight", [255, 240, 226], strength, "screen", rough=rough, spots=list(spots), soft=0.12)]


def lips(fill, liner, overline=0.0, ombre=0.0, finish="satin", strength=0.85, keep_l=None):
    r = {"matte": 0.15, "satin": -0.05, "gloss": -0.3, "vinyl": -0.4}[finish]
    out = [L("lips", fill, strength, "tint", rough=r, keep_l=keep_l, overline=overline, soft=0.012)]
    if liner is not None:
        out.append(L("lip_liner", liner, 0.85, "tint", keep_l=0.7, overline=overline, soft=0.02))
    if ombre:
        light = [min(255, int(c * 1.15 + 20)) for c in fill]
        out.append(L("lip_center", light, ombre, "tint", soft=0.12))
    if finish in ("gloss", "vinyl"):
        out.append(L("lip_gloss", None, 0.0, rough=-0.25, soft=0.06))
    return out


def look(id_, name, family, source, *parts):
    return {"id": id_, "name": name, "family": family, "source": source,
            "layers": [l for p in parts for l in p]}


def base_looks():
    S = "NotebookLM Makeup Atlas d99dde93"
    return [
        look("latte", "Classic Latte", "social", S, skin("satin"), sculpt("warm", 0.32), blush(BLUSH["terracotta"], "draped", 0.3),
             glow(("cheek", "nose_bridge", "cupid")), eyes(*EYE["warm_brown"], liner={"color": BROWN_LINER, "len": 0.15, "w": 0.04}),
             lips(*LIP["nude_brown"], overline=0.01, finish="satin")),
        look("iced_latte", "Iced Latte", "social", S, skin("dewy", 0.25, 0.1), sculpt("warm", 0.25, jaw=False), blush(BLUSH["peach"], "apple", 0.3),
             glow(("cheek", "nose_bridge"), 0.3, -0.2), eyes([238, 214, 190], [170, 130, 100], liner={"color": [190, 176, 170], "len": 0.0, "w": 0.03, "lower": True}),
             lips([176, 120, 84], None, finish="gloss", strength=0.6)),
        look("pumpkin_latte", "Pumpkin Spice Latte", "social", S, skin("satin"), sculpt("warm", 0.35), blush(BLUSH["terracotta"], "apple", 0.32),
             glow(("cheek",), 0.25), eyes(*EYE["copper"], shape="smoky", liner={"color": [160, 90, 50], "len": 0.1, "w": 0.035, "lower": True}, lashline=0.4),
             lips([130, 70, 50], [100, 54, 40], finish="satin")),
        look("espresso", "Espresso", "social", S, skin("satin", 0.4, 0.25), sculpt("cool", 0.42, nose=True), blush(BLUSH["rosy_mauve"], "apple", 0.2),
             glow(("cheek", "browbone", "nose_tip", "cupid"), 0.25), eyes(*EYE["espresso"], shape="smoky", lashline=0.55,
             liner={"color": [40, 26, 20], "len": 0.3, "w": 0.07, "soft": 0.08, "lower": True}),
             lips(*LIP["espresso"], overline=0.025, ombre=0.4, finish="vinyl")),
        look("luvpauli_doll", "Douyin Doll Glam (@luvpauli)", "douyin", "TikTok 7688402180574874902", skin("satin", 0.45, 0.3),
             sculpt("cool", 0.45, nose=True), blush(BLUSH["pink"], "high", 0.32, nose=True), glow(("nose_bridge", "nose_tip"), 0.3),
             eyes(*EYE["white_pink"], shape="cut", liner={"color": BLACK, "angle": -4, "len": 0.45, "w": 0.1}, lashline=0.0, inner=WHITE, aegyo=0.25, glitter=0.9),
             lips(*LIP["taupe_mauve"], overline=0.03, ombre=0.3, finish="satin", keep_l=0.85)),
        look("douyin_aegyo", "Douyin Aegyo-sal Doll Eye", "douyin", S, skin("dewy", 0.3), sculpt("cool", 0.22, nose=True, jaw=False),
             blush([244, 160, 140], "high", 0.35), glow(("cheek", "inner_corner"), 0.3), eyes(*EYE["pink_peach"], liner={"color": BLACK, "angle": 14, "len": 0.2, "w": 0.035},
             lashline=0.3, aegyo=0.4, glitter=0.6), lips([204, 110, 120], None, ombre=0.5, finish="gloss", strength=0.7)),
        look("y2k_frost", "Y2K Frosty Glam", "y2k", S, skin("matte", 0.3), sculpt("warm", 0.28), blush(BLUSH["pink"], "apple", 0.3),
             glow(("inner_corner", "cheek"), 0.3), eyes(*EYE["icy_silver"], shape="soft", liner={"color": BLACK, "len": 0.0, "w": 0.045, "soft": 0.1, "lower": True}),
             lips(*LIP["pink_frost"], overline=0.015, finish="gloss")),
        look("y3k_silver", "Y3K Silver Glass", "y2k", S, skin("glass", 0.2, 0.0), sculpt("cool", 0.18, jaw=False), blush(BLUSH["rosy_mauve"], "lifted", 0.18),
             glow(("cheek", "browbone", "inner_corner"), 0.4, -0.3), eyes(*EYE["icy_silver"], liner={"color": [200, 206, 220], "angle": 22, "len": 0.32, "w": 0.04}),
             lips([196, 150, 156], None, finish="gloss", strength=0.5)),
        look("siren_eyes", "Siren Eyes", "social", S, skin("dewy", 0.4), sculpt("cool", 0.3), blush(BLUSH["peach"], "apple", 0.28),
             glow(("cheek", "nose_bridge", "inner_corner", "browbone"), 0.3), eyes(*EYE["smoky_grey"], shape="cut",
             liner={"color": BLACK, "angle": 20, "len": 0.38, "w": 0.06}, lashline=0.3), lips(*LIP["nude_brown"], finish="gloss")),
        look("office_siren", "Office Siren", "social", S, skin("matte", 0.35), sculpt("warm", 0.3), blush(BLUSH["rosy_mauve"], "lifted", 0.28),
             glow(("inner_corner",), 0.3), eyes(*EYE["warm_brown"], shape="smoky", liner={"color": BLACK, "angle": 16, "len": 0.25, "w": 0.06, "soft": 0.06}),
             lips(*LIP["taupe_mauve"], overline=0.01, finish="satin")),
        look("clean_girl", "Clean Girl", "social", S, skin("dewy", 0.2, 0.0), sculpt("warm", 0.0, jaw=False), blush(BLUSH["pink"], "apple", 0.22),
             glow(("cheek", "nose_bridge"), 0.2, -0.18), eyes([226, 200, 186], [180, 150, 130], liner=None), lips([196, 130, 124], None, finish="gloss", strength=0.45)),
        look("cold_girl", "Cold Girl", "social", S, skin("dewy", 0.3), sculpt("cool", 0.12, jaw=False), blush(BLUSH["pink"], "high", 0.42, nose=True),
             glow(("cheek",), 0.25), eyes([240, 214, 214], [200, 150, 150], liner=None, lashline=0.2), lips([200, 110, 118], None, finish="gloss", strength=0.55)),
        look("mob_wife", "Mob Wife", "glam", S, skin("satin", 0.4, 0.3), sculpt("warm", 0.45, nose=True), blush(BLUSH["terracotta"], "lifted", 0.3),
             glow(("cheek", "nose_bridge", "cupid"), 0.3), eyes(*EYE["espresso"], shape="smoky", liner={"color": BLACK, "angle": 18, "len": 0.36, "w": 0.08}, lashline=0.5),
             lips(*LIP["brick_rose"], overline=0.025, finish="satin")),
        look("glazed", "Glazed Skin", "skin", S, skin("glass", 0.25, 0.1), sculpt("warm", 0.15, jaw=False), blush(BLUSH["peach"], "lifted", 0.25),
             glow(("cheek", "nose_bridge", "browbone", "cupid", "chin"), 0.35, -0.3), eyes([232, 206, 190], [190, 150, 128]), lips([186, 120, 110], None, finish="gloss", strength=0.5)),
        look("old_money", "Old Money Classic Red", "glam", S, skin("satin", 0.35, 0.2), sculpt("cool", 0.28), blush(BLUSH["rosy_mauve"], "lifted", 0.22),
             glow(("cheek",), 0.2), eyes([214, 190, 170], [140, 110, 90], liner={"color": BLACK, "angle": 15, "len": 0.2, "w": 0.045}),
             lips(*LIP["classic_red"], finish="satin")),
        look("runway_90s", "Runway 90s Brown", "runway", S, skin("matte", 0.35), sculpt("cool", 0.38), blush(BLUSH["terracotta"], "lifted", 0.2),
             glow((), 0.0), eyes(*EYE["espresso"], shape="smoky", lashline=0.5, liner={"color": [50, 34, 28], "len": 0.0, "w": 0.06, "soft": 0.1, "lower": True}),
             lips(*LIP["espresso"], overline=0.015, finish="matte")),
        look("runway_bare", "Runway Bare Skin", "runway", S, skin("satin", 0.25, 0.0), sculpt("warm", 0.1, jaw=False), blush(BLUSH["peach"], "apple", 0.15),
             glow(("cheek",), 0.15, -0.1), eyes([220, 196, 180], [170, 140, 120]), lips([180, 120, 110], None, finish="satin", strength=0.35)),
        look("runway_graphic", "Runway Graphic Liner", "runway", S, skin("matte", 0.3), sculpt("cool", 0.2), blush(BLUSH["rosy_mauve"], "lifted", 0.12),
             glow((), 0.0), eyes([224, 210, 200], [150, 130, 120], liner={"color": BLACK, "angle": 28, "len": 0.5, "w": 0.08, "soft": 0.02}),
             lips([170, 120, 112], None, finish="matte", strength=0.5)),
        look("k_beauty_gradient", "K-beauty Gradient Lip", "k-beauty", S, skin("glass", 0.3, 0.1), sculpt("warm", 0.0, jaw=False), blush(BLUSH["peach"], "apple", 0.3),
             glow(("cheek", "nose_bridge"), 0.25, -0.2), eyes([238, 200, 186], [200, 150, 130], liner={"color": BROWN_LINER, "len": 0.12, "w": 0.03}, aegyo=0.25),
             lips([206, 70, 90], None, ombre=0.0, finish="gloss", strength=0.35) + [L("lip_center", [196, 40, 70], 0.7, "tint", size=0.2, soft=0.15)]),
        look("smoky_glam", "Smoky Evening Glam", "glam", S, skin("satin", 0.4), sculpt("cool", 0.38, nose=True), blush(BLUSH["rosy_mauve"], "lifted", 0.25),
             glow(("cheek", "browbone", "inner_corner"), 0.3), eyes(*EYE["smoky_grey"], shape="smoky", lashline=0.6, liner={"color": BLACK, "angle": 15, "len": 0.25, "w": 0.07, "soft": 0.1, "lower": True}),
             lips(*LIP["taupe_mauve"], overline=0.01, finish="satin")),
        look("berry_vamp", "Berry Vamp", "glam", S, skin("matte", 0.4), sculpt("cool", 0.35), blush(BLUSH["berry"], "lifted", 0.2),
             glow(("cheek",), 0.2), eyes([200, 170, 170], [90, 50, 60], shape="smoky", liner={"color": BLACK, "angle": 18, "len": 0.25, "w": 0.06}),
             lips(*LIP["berry"], overline=0.015, finish="satin")),
        look("sunkissed", "Sunkissed Bronze", "skin", S, skin("dewy", 0.25, 0.1), sculpt("warm", 0.35), blush(BLUSH["terracotta"], "high", 0.3, nose=True),
             glow(("cheek", "nose_bridge", "browbone"), 0.3, -0.2), eyes(*EYE["copper"], liner={"color": BROWN_LINER, "len": 0.15, "w": 0.04}),
             lips([170, 110, 86], None, finish="gloss", strength=0.6)),
        look("editorial_glass", "Editorial Glass Lid", "runway", S, skin("glass", 0.3, 0.1), sculpt("cool", 0.15, jaw=False), blush(BLUSH["pink"], "apple", 0.2),
             glow(("cheek",), 0.25, -0.25), eyes([236, 206, 200], [190, 150, 140]) + [L("lid", None, 0.0, rough=-0.4, height=0.5)],
             lips([186, 120, 120], None, finish="gloss", strength=0.45)),
    ]


INTENSITY = {"soft": 0.65, "standard": 1.0, "glam": 1.3}


def variant(base, intensity, lip_key=None, eye_key=None, blush_key=None):
    """Recolour and rescale a base look. lip/eye/blush None keeps the look's own colours."""
    k = INTENSITY[intensity]
    lay = json.loads(json.dumps(base["layers"]))
    for l in lay:
        z = l["zone"]
        if z not in ("foundation",):
            l["opacity"] = round(min(1.0, l["opacity"] * k), 3)
        if lip_key and z == "lips":
            l["color"] = LIP[lip_key][0]
        if lip_key and z == "lip_liner":
            l["color"] = LIP[lip_key][1]
        if lip_key and z == "lip_center":
            l["color"] = [min(255, int(c * 1.15 + 20)) for c in LIP[lip_key][0]]
        if eye_key and z == "lid" and "color" in l:
            l["color"] = EYE[eye_key][0]
        if eye_key and z in ("crease", "outer_v", "lower_lash"):
            l["color"] = EYE[eye_key][1]
        if blush_key and z == "blush":
            l["color"] = BLUSH[blush_key]
    parts = [base["id"], intensity] + [x for x in (lip_key, eye_key, blush_key) if x]
    return {**base, "id": "__".join(parts), "layers": lay,
            "variant": {"intensity": intensity, "lip": lip_key, "eye": eye_key, "blush": blush_key}}


def generate(limit=None):
    """Every base look x intensity x (own or swapped) lip x (own or swapped) eye palette."""
    out = []
    lips_ = [None] + list(LIP)
    eyes_ = [None] + list(EYE)
    for b in base_looks():
        for inten, lk, ek in itertools.product(INTENSITY, lips_, eyes_):
            out.append(variant(b, inten, lk, ek))
            if limit and len(out) >= limit:
                return out
    return out
