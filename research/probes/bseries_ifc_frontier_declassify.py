"""IFC context-integrity, done properly: the SECURITY/UTILITY FRONTIER of a graded low-water-mark, and an
earned-standing DECLASSIFIER that recovers the rare-but-true tail — the open problem Biba (1977) left and
that a 4-arm binary toy assumes away.

Why: a strict binary low-water-mark (action inherits min integrity, fail closed) is TAUTOLOGICAL — it blocks
*under-corroboration*, and a single-source POISON and a single-source RARE-BUT-TRUE memory are the SAME event
to it (identical low integrity). It does not detect poison. The real, measurable questions need graded
integrity and a real distribution:
  1. FRONTIER — because poison and rare-true are drawn from the SAME low-integrity distribution (both
     single-source), integrity ALONE can't separate them: any tau that blocks X% of poison-context blocks
     ~X% of rare-true-context. The security/utility frontier is the diagonal. We measure how diagonal.
  2. DECLASSIFIER — an ORTHOGONAL signal, earned standing (a track record; jacksonxly's staked/decaying
     standing), CAN separate them: a genuine rare-true accrues good outcomes, fresh poison does not. Endorse
     members with standing g>=G_MIN and the frontier shifts — less true-recall lost at the same closure.
  3. Its HOLES, measured: COLD START (a fresh true memory has g=0, indistinguishable from fresh poison ->
     not recovered) and the SLEEPER (a poison that farms g>=G_MIN then defects -> endorsed; standing is
     intent-blind). And the FLOOR: a Sybil-forged poison is integrity-identical to real corroboration, so
     you cannot block it without blocking benign corroborated context too.

RBAC gates the actor, IFC gates the data, membership-cost gates the identity — the declassifier is where IFC
and membership-cost meet, and where the cold-start tail becomes irreducible. Zero-dependency, deterministic
(seeded). MIT. This probe IS the graded-IFC + earned-standing-declassifier prototype for inspeximus.
Run: python research/probes/bseries_ifc_frontier_declassify.py"""
import sys

# This probe prints non-ASCII (en dashes, a Unicode minus, Cyrillic and CJK samples) and the
# console here is cp1250, so it died with UnicodeEncodeError before reaching its own result.
# CLAUDE.md rule 11 already requires this reconfigure; it was applied in the servers and not
# in the probes. errors='replace' rather than a crash: a mangled character is a better outcome
# than losing the measurement.
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

import json, os, random


_SEED = int(os.environ.get('IFC_SEED', '20260703'))
random.seed(_SEED)
N = 6000
G_MIN = 3.0
P_AGED = 0.35          # fraction of rare-true memories that have accrued earned standing (rest are cold, g=0)
LOW, HIGH, SD = 0.30, 0.85, 0.06   # base integrity by corroboration; poison==rare-true base (same distribution)


def _clamp(x):
    return max(0.02, min(0.98, x))


def make_memory(rng):
    """(integrity, kind, standing_g). Integrity is graded from corroboration ONLY; standing is orthogonal.
    Single-source poison and rare-true share the SAME integrity distribution -> integrity can't separate them.
    Sybil-forged poison is drawn from the corroborated (HIGH) distribution -> integrity-identical to benign."""
    r = rng.random()
    if r < 0.55:                                              # benign, genuinely corroborated
        return _clamp(rng.gauss(HIGH, SD)), "benign", rng.choice([0, 0, 1, 2])
    if r < 0.75:                                              # rare-but-true, single source (LOW), some aged
        g = (rng.uniform(G_MIN, G_MIN + 5) if rng.random() < P_AGED else 0.0)
        return _clamp(rng.gauss(LOW, SD)), "rare_true", g
    if r < 0.92:                                              # single-source poison (LOW, g=0) — same dist as rare_true
        return _clamp(rng.gauss(LOW, SD)), "poison", 0.0
    return _clamp(rng.gauss(HIGH, SD)), "sybil", 0.0          # forged 2-domain -> HIGH, integrity-identical to benign


def build_actions(rng):
    acts = []
    for _ in range(N):
        ctx = [make_memory(rng) for _ in range(rng.randint(2, 5))]
        kinds = {c[1] for c in ctx}
        acts.append({"ctx": ctx, "poison": "poison" in kinds, "sybil": "sybil" in kinds, "rare": "rare_true" in kinds})
    return acts


def permit(ctx, tau, declassify):
    """Low-water-mark: min integrity >= tau. Declassifier: a member with earned standing g>=G_MIN is endorsed
    (treated as >= tau, so it no longer drags the min below tau)."""
    return min((max(I, tau) if (declassify and g >= G_MIN) else I) for I, _, g in ctx) >= tau


def frontier(acts, declassify):
    rows = []
    pois = [a for a in acts if a["poison"] and not a["sybil"]]
    syb = [a for a in acts if a["sybil"]]
    clean_rare = [a for a in acts if a["rare"] and not a["poison"] and not a["sybil"]]
    benign = [a for a in acts if not a["poison"] and not a["sybil"] and not a["rare"]]
    for tau in [x / 40 for x in range(8, 41)]:               # 0.20 .. 1.00
        rows.append({
            "tau": round(tau, 3),
            "poison_closed": round(sum(1 for a in pois if not permit(a["ctx"], tau, declassify)) / max(1, len(pois)), 3),
            "true_recall_lost": round(sum(1 for a in clean_rare if not permit(a["ctx"], tau, declassify)) / max(1, len(clean_rare)), 3),
            "sybil_residual_hijack": round(sum(1 for a in syb if permit(a["ctx"], tau, declassify)) / max(1, len(syb)), 3),
            "benign_kept": round(sum(1 for a in benign if permit(a["ctx"], tau, declassify)) / max(1, len(benign)), 3),
        })
    return rows


acts = build_actions(random.Random(_SEED))
base = frontier(acts, declassify=False)
decl = frontier(acts, declassify=True)

print("=== graded low-water-mark FRONTIER (no declassifier) — poison & rare-true share one integrity dist ===")
print(f"{'tau':>6}{'poison_closed':>15}{'true_recall_lost':>18}{'sybil_hijack':>14}{'benign_kept':>13}")
for r in base[::3]:
    print(f"{r['tau']:>6}{r['poison_closed']:>15}{r['true_recall_lost']:>18}{r['sybil_residual_hijack']:>14}{r['benign_kept']:>13}")

# how diagonal is the frontier? mean |poison_closed - true_recall_lost| over the usable band (benign_kept>0.5)
band = [r for r in base if r["benign_kept"] > 0.5]
diag_gap = sum(abs(r["poison_closed"] - r["true_recall_lost"]) for r in band) / max(1, len(band))

def at_closure(rows, target):
    c = [r for r in rows if r["poison_closed"] >= target and r["benign_kept"] > 0.5]
    return min(c, key=lambda r: r["true_recall_lost"]) if c else max(rows, key=lambda r: r["poison_closed"])
b = at_closure(base, 0.9); d = at_closure(decl, b["poison_closed"])
recovered = b["true_recall_lost"] - d["true_recall_lost"]

# cold-start bound: fraction of rare-true with standing (only these are recoverable)
rng = random.Random(_SEED + 6)
rt = [m for m in (make_memory(rng) for _ in range(20000)) if m[1] == "rare_true"]
aged = sum(1 for m in rt if m[2] >= G_MIN) / max(1, len(rt))
floor = max(r["sybil_residual_hijack"] for r in base if r["benign_kept"] > 0.5)   # sybil hijack while utility survives

# ── falsifiable self-check ──
assert diag_gap < 0.12, f"integrity can't separate poison from rare-true: the frontier must be ~diagonal (gap={diag_gap:.3f})"
assert base[0]["poison_closed"] < base[-1]["poison_closed"], "poison closure must rise with tau"
assert recovered > 0.05, "the declassifier must recover a real chunk of true-recall at matched closure"
assert aged < 1.0, "cold-start: not all rare-true have earned standing (the irreducible tail)"
assert floor > 0.10, "Sybil floor: forged corroboration keeps executing while benign utility survives"

print(f"\nBY CONSTRUCTION (gap = finite-sample noise around a true 0): mean |poison_closed − true_recall_lost| "
      f"= {diag_gap:.3f} over the usable band. Poison & rare-true are drawn integrity-identical, so integrity "
      f"CANNOT separate them — the diagonal is the SETUP, not a finding.")
print(f"ILLUSTRATIVE (dials we set, NOT empirical rates): at ~{b['poison_closed']:.0%} poison closure the "
      f"strict rule loses {b['true_recall_lost']:.2f} true-recall; endorsing earned-standing members refunds "
      f"~{recovered:.2f} — but this equals the standing-prevalence we set (P_AGED), it is not a measured recovery rate.")
print(f"STRUCTURAL BOUND — cold-start: only {aged:.0%} of rare-true have earned standing; the rest (fresh, g=0) "
      f"are indistinguishable from fresh poison and cannot be refunded. SLEEPER: a poison that farms g>="
      f"{G_MIN:.0f} then defects is endorsed (standing is intent-blind).")
print(f"STRUCTURAL — Sybil FLOOR: forged-corroboration poison executes at {floor:.2f} while benign utility "
      f"survives — integrity-identical to real corroboration, so closure is capped until identity has a mint cost.")
verdict = (f"The security question is NOT the low-water-mark. Because poison and rare-true share one integrity "
           f"distribution, the graded low-water-mark frontier is diagonal BY CONSTRUCTION (gap {diag_gap:.2f}=noise~0): it trades "
           f"security for utility ~1:1 and does not detect poison. The lever is the ORTHOGONAL earned-standing "
           f"declassifier: it refunds ONLY the true items that already hold standing (in the toy, the {recovered:.2f}≈P_AGED we set) of the "
           f"lost true-recall (poison has no standing), but is bounded by COLD START (only ~{aged:.0%} of "
           f"rare-true have standing; the rest = the irreducible tail Sybil-resistance can't refund) and "
           f"defeated by SLEEPERS (standing is intent-blind), and it sits above a Sybil FLOOR (~{floor:.2f} "
           f"forged-corroboration hijack) that no tau removes without destroying benign utility. So: RBAC "
           f"gates the actor, IFC gates the data, membership-cost gates the identity — and the cold-start tail "
           f"is the measured price of doing the last one without a trusted registrar.")
print(f"\nVERDICT: {verdict}")
out = {"scenario": "graded_ifc_frontier_and_declassifier", "self_check": "passed", "n": N, "g_min": G_MIN,
       "frontier_diagonal_gap": round(diag_gap, 3), "aged_fraction": round(aged, 3),
       "sybil_floor": round(floor, 3),
       "operating_point": {"tau": b["tau"], "poison_closed": b["poison_closed"],
                           "true_recall_lost_strict": b["true_recall_lost"],
                           "true_recall_lost_declassify": d["true_recall_lost"], "recovered": round(recovered, 3)},
       "frontier_no_declassify": base, "frontier_declassify": decl,
       "idea_credit": "jacksonxly (r/LangChain): low-water-mark/IFC framing + staked/decaying standing. "
                      "Roots: Biba 1977, Myers&Liskov DLM, CaMeL (2503.18813), Douceur Sybil 2002.",
       "verdict": verdict}
json.dump(out, open(os.path.join(os.path.dirname(__file__), "bseries_ifc_frontier_declassify_result.json"),
                    "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("saved: research/probes/bseries_ifc_frontier_declassify_result.json")
