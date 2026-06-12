"""
Replication + hypothesis test: Miller (1957) "Some effects of intermittent silence" —
random typing (a monkey hitting letter keys + space) produces Zipf's law, therefore Zipf's
law in language carries no linguistic significance.

Two-part test:
 (1) REPLICATE: does random typing produce an (approximately) power-law rank-frequency curve
     with exponent near -1? (Miller's mathematical claim — expected to hold roughly.)
 (2) SEVERE TEST of the INFERENCE ("therefore Zipf carries no linguistic information"):
     random typing's rank-frequency is NOT smooth — all words of the same length are
     equiprobable, so the curve is a STAIRCASE of plateaus, while real language is smooth.
     We quantify: (a) local-slope variance (staircase detector), (b) number of distinct
     frequency values among the top-R ranks vs a smooth Zipf sample.

If (1) holds but (2) cleanly separates random typing from smooth-Zipf text, then Miller's
math REPRODUCES while the famous inference FAILS: Zipf's *fine structure* does discriminate
language from noise. (Ferrer-i-Cancho & Elvevag 2010 argue this empirically; we make the
minimal computational version.)

Hypothesis (Linguistics <-> Statistics bridge): the discriminating statistic between
"random-typing Zipf" and "linguistic Zipf" is the plateau structure, measurable as the
fraction of tied adjacent ranks among the top R words. Falsifier: if random typing's tie
fraction matches a smooth-Zipf corpus of the same size, the discriminator is dead and
Miller's deflationary inference stands whole.
"""
import numpy as np
from collections import Counter

rng = np.random.default_rng(20260612)

# ---------- (1) random typing corpus ----------
ALPHA = 26
P_SPACE = 0.18          # Miller's setup: space with fixed prob, letters uniform
N_CHARS = 3_000_000

chars = rng.random(N_CHARS)
# build words: runs of letters separated by spaces
letters = rng.integers(0, ALPHA, N_CHARS)
words = []
cur = []
for i in range(N_CHARS):
    if chars[i] < P_SPACE:
        if cur:
            words.append(tuple(cur)); cur = []
    else:
        cur.append(letters[i])
if cur: words.append(tuple(cur))
counts = np.array(sorted(Counter(words).values(), reverse=True), dtype=float)
n_words = counts.sum()
R = min(2000, len(counts))
ranks = np.arange(1, R + 1)
freqs = counts[:R] / n_words

# fit exponent on log-log (top decades)
lo, hi = 0, R
slope, intercept = np.polyfit(np.log(ranks[lo:hi]), np.log(freqs[lo:hi]), 1)
print("=== (1) Miller's mathematical claim: random typing -> Zipf-like power law ===")
print(f"  corpus: {int(n_words)} words, {len(counts)} types; fitted rank-freq exponent = {slope:.3f}")
print(f"  (Zipf's law for language: exponent ~ -1.0)")
math_ok = -1.6 < slope < -0.6
print(f"  approximate power law? {'YES' if math_ok else 'NO'}")

# ---------- (2) the fine-structure discriminator ----------
def tie_fraction(c, R):
    """Fraction of adjacent top-R ranks with EQUAL counts (plateau/staircase signal)."""
    c = c[:R]
    return float(np.mean(c[1:] == c[:-1]))

def local_slope_var(c, R):
    f = c[:R] / c.sum()
    r = np.arange(1, R + 1)
    ls = np.diff(np.log(f)) / np.diff(np.log(r))
    return float(np.var(ls))

# smooth-Zipf synthetic "language" corpus of the SAME size and type count
V = len(counts)
zipf_p = 1.0 / np.arange(1, V + 1)
zipf_p /= zipf_p.sum()
lang_counts = np.array(sorted(rng.multinomial(int(n_words), zipf_p), reverse=True), dtype=float)
lang_counts = lang_counts[lang_counts > 0]

Rtop = 500
tf_rand = tie_fraction(counts, Rtop)
tf_lang = tie_fraction(lang_counts, Rtop)
lv_rand = local_slope_var(counts, Rtop)
lv_lang = local_slope_var(lang_counts, Rtop)
print("\n=== (2) Fine structure: staircase vs smooth (top", Rtop, "ranks) ===")
print(f"  tie fraction (adjacent equal counts):  random typing = {tf_rand:.3f}   smooth-Zipf = {tf_lang:.3f}")
print(f"  local log-log slope variance:          random typing = {lv_rand:.4f}   smooth-Zipf = {lv_lang:.4f}")
sep = tf_rand > 2 * tf_lang
print(f"  discriminator separates the two? {'YES' if sep else 'NO'} "
      f"(tie-fraction ratio {tf_rand/max(tf_lang,1e-9):.1f}x)")

print("\n=== Verdict ===")
if math_ok and sep:
    print("SPLIT VERDICT: Miller's MATH reproduces (random typing yields an approximate power law,")
    print(f"exponent {slope:.2f}), but his famous INFERENCE fails: the rank-frequency FINE STRUCTURE")
    print(f"separates random typing from smooth linguistic Zipf decisively (tie fraction {tf_rand:.2f}")
    print(f"vs {tf_lang:.2f}, {tf_rand/max(tf_lang,1e-9):.0f}x). Zipf's law alone is weak evidence;")
    print("Zipf's fine structure is informative. The deflationary conclusion was an overreach.")
elif math_ok:
    print("REPRODUCED in full: random typing matches smooth Zipf even in fine structure - Miller's")
    print("deflationary inference stands; the proposed discriminator is dead.")
else:
    print("FAILED: random typing does not produce an approximate power law under Miller's setup.")
