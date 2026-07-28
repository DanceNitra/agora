"""Live proof with UNIQUE titles, so the dedup guard cannot answer for the refusal gate.

The first run was inconclusive: the endpoint rejected the envelope, but with reason
"near-duplicate of a recent finding", i.e. the dedup guard fired first and the refusal gate was never
reached. Same-title rows also made my landing check read True against historical records rather than
this test's write.
"""
import json
import sqlite3
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
URL = "http://127.0.0.1:8000/api/v1/agent-os/brain/collective"
DB = r"C:\Users\Danculus\agora\server\agora.db"

CASES = [
    ("the deltaG envelope", "GATE-LIVE-1 quantised readback on lattice coupling",
     'Reality: {    "answer": "The provided sources do not support the claim about '
     'deltaG(q=0.6)-deltaG(0) = 0.077 N or the Lab 89ffff reference, and no further analysis was '
     'possible from the material supplied to either agent."}', False),
    ("mid-sentence variant", "GATE-LIVE-2 joint readback on lattice coupling",
     "The joint finding is that the provided sources do not support the claim about "
     "deltaG(q=0.6)-deltaG(0) = 0.077 N, which was the question posed to both agents in this round "
     "of the collaborative pipeline.", False),
    ("plain refusal", "GATE-LIVE-3 unable to complete the assigned analysis",
     "I cannot complete this task because no papers were provided for the claim, and I am unable to "
     "locate any relevant source in the material that was supplied to me for this round.", False),
]

for label, title, content, should_land in CASES:
    body = json.dumps({"npc": "thief", "title": title, "content": content,
                       "knowledge_type": "discovery"}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = json.loads(r.read())
    except Exception as e:
        resp = {"status": "ERROR", "reason": str(e)[:120]}
    print(f"  {label:22s} -> {resp.get('status'):9s} | {str(resp.get('reason', ''))[:64]}")

con = sqlite3.connect(DB)
n = con.execute("SELECT COUNT(*) FROM collective_knowledge WHERE title LIKE 'GATE-LIVE%'").fetchone()[0]
print(f"\n  rows that landed in the table: {n}   expected: 0   "
      f"{'PASS' if n == 0 else '!! FAIL'}")
con.execute("DELETE FROM collective_knowledge WHERE title LIKE 'GATE-LIVE%'")
con.commit()
con.close()
