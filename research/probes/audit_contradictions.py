"""Does contradictions() say "none" when it cannot look?

It is documented as SIMILARITY-GATED: it compares memories that are related, and relatedness needs an
embedder. A store with no embedder therefore has nothing it considers related — so the honest question
is whether an empty result distinguishes "no contradictions exist" from "I could not relate anything".

My pass-4 probe was wrong: I planted two records under the SAME KEY, which is a supersession the store
resolves correctly, so there was no live conflict to find. This plants a real one — two unkeyed,
simultaneously-active statements of opposite polarity — and runs it with and without an embedder.
"""
import sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\Danculus\inspeximus-repo")
from inspeximus import Inspeximus  # noqa: E402

PAIRS = [
    ("the cache layer is enabled in production", "the cache layer is not enabled in production"),
    ("the deploy script targets the main branch", "the deploy script does not target the main branch"),
    ("the auth service requires two-factor login", "the auth service does not require two-factor login"),
]


def toy_embed(text: str):
    """A deterministic bag-of-words embedder — enough for similarity gating, no network."""
    rng = np.random.default_rng(0)
    dim = 64
    v = np.zeros(dim)
    for w in text.lower().split():
        h = abs(hash(w)) % dim
        v[h] += 1.0
    n = np.linalg.norm(v)
    return list(v / n) if n else list(v)


for label, embed in (("NO embedder", None), ("with an embedder", toy_embed)):
    st = Inspeximus(path=None, embed=embed)
    for a, b in PAIRS:
        st.remember(a, source={"doc": "team-a"})
        st.remember(b, source={"doc": "team-b"})
    found = st.contradictions()
    print(f"{label:18s}: {len(st.items)} records, contradictions() -> {len(found)} flagged")
    for f in found[:3]:
        pair = f.get("pair") or f.get("memories") or f
        print(f"     {str(pair)[:120]}")

print("\n=== the question ===")
st_none = Inspeximus(path=None)
for a, b in PAIRS:
    st_none.remember(a)
    st_none.remember(b)
r = st_none.contradictions()
print(f"a store with three planted polarity conflicts and NO embedder reports: {len(r)} contradictions")
print("if that is 0 while the embedder case is >0, an empty list means 'could not look', not 'none' —")
print("and nothing in the return distinguishes the two.")
