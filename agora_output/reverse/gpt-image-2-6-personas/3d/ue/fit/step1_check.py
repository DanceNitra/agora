import json, sys
sys.path.insert(0, r"C:\Users\Danculus\agora\agora_output\reverse\gpt-image-2-6-personas\3d\ue\fit")
from fit_lib import *
ref = json.load(open(F + r"\ref_landmarks.json"))
c = get_coeffs(); print("n coeffs", len(c), "range", min(c), max(c))
im = capture("base"); lm = track(im, "base")
print("base curves", len(lm), "err", aligned_error(lm, ref)[0])
