"""Why the same claim entered the replication ledger three times.

The queue's freshness guard is an EXACT match on the lowercased first 60 characters of the claim:

    attempted = {(r.get("claim") or "")[:60].lower() for r in _load()}
    if claim[:60].lower() in attempted: continue          # "already attempted"

A prefix-equality test standing in for "is this the same claim". It is the defect shape this codebase
keeps producing: a guard whose only job is to refuse cannot structurally see what it is asked to prevent
-- two wordings of one result share no prefix, so both are "fresh" and both cost a full replication cycle.

Worse, the RENDERER dedups better than the QUEUE does: render_crucible._dedup_ledger already compares
token overlap (_DEDUP_THR) and even keeps a list of textbook families to warn about. So the cheap check
runs after the expensive work, and until today it only warned.

This measures three things:
  1. does the current guard catch the three LinUCB entries?  (control: it must NOT -- else the diagnosis
     is wrong and the duplicates came from somewhere else)
  2. would the renderer's own token-overlap fingerprint have caught them at queue time?
  3. how many OTHER paraphrase pairs are sitting in the ledger right now
"""
import itertools
import json
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))

LEDGER = ROOT / "server" / ".replications.json"
entries = json.loads(LEDGER.read_text(encoding="utf-8"))
if isinstance(entries, dict):
    entries = entries.get("items") or entries.get("replications") or []
print(f"ledger entries: {len(entries)}\n")

import render_crucible as rc  # noqa: E402   the renderer's own fingerprint, not a reimplementation


def prefix_key(c: str) -> str:
    return (c or "")[:60].lower()


linucb = [r for r in entries if "linucb" in (r.get("claim", "") or "").lower()
          or ("regret bound" in (r.get("claim", "") or "").lower())]
print("=== 1. THE CONTROL: does the shipped guard see them as duplicates? ===")
for r in linucb:
    print(f"   {prefix_key(r.get('claim',''))!r}")
keys = [prefix_key(r.get("claim", "")) for r in linucb]
print(f"   distinct prefix keys: {len(set(keys))} of {len(keys)}  ->  "
      f"{'guard is BLIND (diagnosis holds)' if len(set(keys)) == len(keys) else 'guard would have caught them'}")

print("\n=== 2. would the renderer's token fingerprint have caught them at QUEUE time? ===")
for a, b in itertools.combinations(linucb, 2):
    ta, tb = rc._dd_tokens(a.get("claim", "")), rc._dd_tokens(b.get("claim", ""))
    j = len(ta & tb) / max(1, len(ta | tb))
    print(f"   jaccard {j:.2f}  (threshold {rc._DEDUP_THR})  "
          f"{'MERGE' if j >= rc._DEDUP_THR else 'still distinct'}")
    print(f"      A: {a.get('claim','')[:74]}")
    print(f"      B: {b.get('claim','')[:74]}")

print("\n=== 3. other paraphrase pairs already in the ledger ===")
pairs = []
for a, b in itertools.combinations(entries, 2):
    if a.get("outcome") != b.get("outcome"):
        continue
    ta, tb = rc._dd_tokens(a.get("claim", "")), rc._dd_tokens(b.get("claim", ""))
    if not ta or not tb:
        continue
    j = len(ta & tb) / len(ta | tb)
    if j >= rc._DEDUP_THR and prefix_key(a.get("claim", "")) != prefix_key(b.get("claim", "")):
        pairs.append((j, a, b))
pairs.sort(key=lambda x: -x[0])
print(f"   {len(pairs)} pair(s) the token fingerprint merges but the shipped prefix guard let through")
for j, a, b in pairs[:8]:
    print(f"   [{a.get('outcome')}] jaccard {j:.2f}")
    print(f"      {a.get('claim','')[:78]}")
    print(f"      {b.get('claim','')[:78]}")
