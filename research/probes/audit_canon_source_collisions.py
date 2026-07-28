"""How lossy is the erasure-attribution canonicalisation, on source strings people actually write?

The ambiguity guard compares _canon_source(subject) against every other source's canonical form and
REFUSES when two collide. That is the right design. But its severity depends entirely on how often
distinct subjects collide: a tight canonicalisation makes the guard a rare safety net, a lossy one makes
it fire on the common path -- and over MCP the only way past it deletes the third party too.

Observed in passing while probing the MCP erasure gaps: 'crm.example.com/Alice' canonicalises to
'crmexample'. Path gone, TLD gone. This measures whether that generalises.

NOT a claim that the guard is wrong. The guard is what stops the over-deletion. The question is whether
the guard's own precondition -- that a collision means genuinely ambiguous identity -- holds.
"""
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\Danculus\inspeximus-repo")
from inspeximus import Inspeximus  # noqa: E402

canon = Inspeximus._canon_source

#: source strings in the shapes the docstrings themselves use, plus ordinary ones
CASES = [
    # the docstring's own example pair -- SHOULD collide (same host, two people)
    ("crm.example.com/alice", "crm.example.com/bob", "same host, different person"),
    # different companies entirely -- MUST NOT collide
    ("crm.example.com/alice", "crm.example.org/alice", "different TLD"),
    ("crm.example.com/alice", "crm.example.co.uk/alice", "different country domain"),
    ("support.acme.com/ticket/1", "billing.acme.com/invoice/1", "different subdomain+path"),
    # the case-and-punctuation family the guard is FOR -- SHOULD collide
    ("User_42", "user-42", "case + punctuation variant"),
    # plain document names -- MUST NOT collide
    ("q3-forecast.pdf", "q4-forecast.pdf", "different quarter"),
    ("notes/2026-07-27.md", "notes/2026-07-28.md", "different day"),
    ("contract-v1", "contract-v2", "different version"),
    ("employee/1001", "employee/1002", "different employee id"),
    ("gdpr-request-114", "gdpr-request-115", "different DSAR"),
]

print(f"{'A':30s} {'B':30s} {'canon(A)':18s} {'canon(B)':18s} collide?")
wrong = []
for a, b, why in CASES:
    ca, cb = canon(a), canon(b)
    hit = ca == cb
    should = why in ("same host, different person", "case + punctuation variant")
    flag = "" if hit == should else "   <-- UNEXPECTED"
    if hit != should:
        wrong.append((a, b, why, ca))
    print(f"{a:30s} {b:30s} {ca:18s} {cb:18s} {str(hit):5s}{flag}")

print(f"\ncanonicalisations that merge subjects a human would call distinct: {len(wrong)}")
for a, b, why, ca in wrong:
    print(f"   {why}: {a!r} + {b!r} -> {ca!r}")

# what information survives canonicalisation at all
print("\n=== what does canonicalisation keep? ===")
for s in ["crm.example.com/Alice", "support.acme.com/ticket/1", "notes/2026-07-27.md",
          "employee/1001", "User_42", "Rastislav Drahos"]:
    print(f"   {s!r:32s} -> {canon(s)!r}")

# how many DISTINCT subjects a realistic store collapses into how many canonical buckets
pool = [f"crm.example.com/{n}" for n in ("alice", "bob", "carol", "dave")] + \
       [f"support.acme.com/ticket/{i}" for i in range(1, 5)] + \
       [f"employee/{1000+i}" for i in range(4)]
buckets = defaultdict(list)
for s in pool:
    buckets[canon(s)].append(s)
print(f"\n=== {len(pool)} distinct sources -> {len(buckets)} canonical buckets ===")
for k, v in sorted(buckets.items()):
    mark = "  COLLIDING" if len(v) > 1 else ""
    print(f"   {k!r:20s} <- {len(v)} source(s){mark}")
print("\nEvery source in a colliding bucket is a subject whose DSAR the guard refuses, and whose only")
print("MCP-reachable escape (allow_ambiguous=True) erases the whole bucket.")
