"""Replay the real ledger through the NEW queue guard: what would it have blocked, and does it starve?

A guard that blocks duplicates is only half the question. The other half -- the one that decides whether
this is shippable -- is how much LEGITIMATE work it would have refused. Skipping is cheap at queue time
(the scanner takes the next candidate) but a guard that refuses most of the pipeline starves it, and this
codebase has been starved by an over-eager filter before.

Method: walk the ledger in chronological order, asking the new guard about each entry as if it had just
been proposed, against only the entries that preceded it. Report every block with its reason.
"""
import json
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "server"))

from agora.execution.replication import already_covered  # noqa: E402

entries = json.loads((ROOT / "server" / ".replications.json").read_text(encoding="utf-8"))
if isinstance(entries, dict):
    entries = entries.get("items") or []
entries = sorted(entries, key=lambda r: r.get("ts") or 0)
print(f"replaying {len(entries)} ledger entries in chronological order\n")

kept, blocked = [], []
for r in entries:
    why = already_covered(r.get("claim", ""), kept)
    (blocked if why else kept).append((r, why) if why else r)

print(f"WOULD KEEP  : {len(kept)}")
print(f"WOULD BLOCK : {len(blocked)}\n")
by_reason = {}
for r, why in blocked:
    kind = ("family" if "textbook family" in why else
            "restatement" if "restates" in why else "identical")
    by_reason.setdefault(kind, []).append((r, why))
for kind, rows in sorted(by_reason.items(), key=lambda x: -len(x[1])):
    print(f"--- {kind}: {len(rows)} ---")
    for r, why in rows:
        print(f"   [{r.get('outcome')}] lab={r.get('lab_id') or '?'}")
        print(f"      {r.get('claim','')[:88]}")
        print(f"      reason: {why[:96]}")

kept_outcomes = {}
for r in kept:
    kept_outcomes[r.get("outcome")] = kept_outcomes.get(r.get("outcome"), 0) + 1
print(f"\nsurviving ledger would be: {kept_outcomes}  (total {len(kept)})")
print("\nSTARVATION CHECK: the guard runs at CANDIDATE time against a pool of papers, so a block costs one")
print("candidate, not one cycle. It starves only if it refuses nearly everything; here it refuses")
print(f"{len(blocked)/max(1,len(entries)):.0%} of what was historically accepted.")
