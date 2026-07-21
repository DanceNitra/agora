"""One script that exercises all three Agora Memory Toolkit tools end-to-end — no setup, no keys.
Run from the repo root:  python examples/toolkit_demo.py"""
import sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import inspeximus, ragfresh, nullcheck, selfref, quitkit, idcheck, goodhart, herdcheck   # noqa: E402

print("=" * 70)
print("1) mnemo — agent memory: remember, then value-ranked recall")
m = mnemo.Inspeximus(str(ROOT / "examples" / "_toolkit_demo_mem.json"))
m.remember("The deploy key rotates every 90 days; last rotated 2026-05-01.", tags=["ops"], value=3.0)
m.remember("Coffee machine is on the 3rd floor.", tags=["trivia"], value=1.0)
hits = m.recall("when does the deploy key expire", k=1)
print("   recall ->", hits[0]["text"][:60] if hits else "(none)")

print("\n2) ragfresh — vector-store triage (keep/downweight/refresh/prune)")
now = time.time(); D = 86400
items = [
    ragfresh.Item(id="fresh", updated_ts=now - 2 * D, hits=40, value=0.9),
    ragfresh.Item(id="stale_but_valuable", updated_ts=now - 300 * D, hits=20, value=0.8),
    ragfresh.Item(id="orphan", updated_ts=now - 5 * D, value=0.7, source_exists=False),
]
plan = ragfresh.triage(items, now=now, stale_days=90)
for vid, (action, _why) in plan["decisions"].items():
    print(f"   {vid:20s} -> {action}")

print("\n3) nullcheck — is this A/B result real, or noise?")
print("   +15% lift on 1k:", nullcheck.ab_test(100, 1000, 115, 1000)["verdict"])
print("   +18% lift on 10k:", nullcheck.ab_test(1000, 10000, 1180, 10000)["verdict"])

print("\n4) selfref — is your AI training on itself? (collapse + lock)")
print("   pure self-training + p=2 :", selfref.audit(external_fraction=0.0, self_trust_p=2.0)["overall_verdict"])
print("   20% real data    + p=1   :", selfref.audit(external_fraction=0.20, self_trust_p=1.0)["overall_verdict"])

print("\n5) quitkit — when to quit a depleting effort (drawdown stop)")
print("   healthy yield stream:", "QUIT" if quitkit.should_quit([1,1,1,0,1,1,0,1]*4)["quit"] else "KEEP")
print("   faded yield stream  :", "QUIT" if quitkit.should_quit([1,1,1,0,1,1,0,1]*4 + [0,0,1,0,0,0,0,0]*3)["quit"] else "KEEP")

print("\n6) idcheck — is the causal number identified, or did controls inject bias?")
_cb = idcheck.collider_bias(0.5)
print(f"   true +0.5 -> naive {_cb['naive_Y_on_X']}, but 'controlling for' a collider -> {_cb['adjusted_for_collider']}")
print("   audit verdict:", idcheck.audit({"age":"confounder","saw_ad":"collider"})["verdict"].split("—")[0].strip())

print("\n7) goodhart — how gameable is your proxy/metric?")
print("   clean proxy   (gameability 0):", f"{goodhart.fidelity(0.0)['precision']:.0%} precision")
print("   gamed proxy   (gameability 2):", goodhart.audit(2.0, 1)["verdict"].split("—")[0].strip())

print("\n8) herdcheck — will your multi-agent crowd herd?")
print("   each agent sees 0 peers (independent):", f"{herdcheck.ensemble_accuracy(0,1.0):.0%}")
print("   each agent sees 2 peers (equal weight):", herdcheck.audit(2,1.0)["verdict"].split("—")[0].strip())

print("\n" + "=" * 70)
print("All eight ran. Each has its own `python <tool>/<tool>.py` for the full measured benchmark.")
