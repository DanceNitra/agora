"""End-to-end proof against the RUNNING brain: does the live endpoint actually reject it?

Not "the function returns True" — a POST to the same URL the dungeon uses, then a read of the table to
confirm nothing landed. Three cases: the exact envelope shape seen in production, an ordinary refusal,
and a real finding that must still be accepted.
"""
import json
import sqlite3
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
URL = "http://127.0.0.1:8000/api/v1/agent-os/brain/collective"
DB = r"C:\Users\Danculus\agora\server\agora.db"

CASES = [
    ("the production envelope",
     'Pipeline: Artificer Rooke + High Priest Orin: Reality: {    "answer": "The provided sources do',
     '{    "answer": "The provided sources do not support the claim about deltaG(q=0.6)-deltaG(0) = '
     '0.077 N or the Lab 89ffff reference."}', False),
    ("a plain refusal",
     "I cannot complete this task without sources",
     "I cannot complete this task because no papers were provided for the claim.", False),
    ("a real finding (must be ACCEPTED)",
     "GATE-PROBE Measured: centering lifts recall@10 by 0.04 on LoCoMo",
     "Measured on LoCoMo (n=419 turns): subtracting the corpus mean before cosine lifts single-hop "
     "recall@10 from 0.31 to 0.35 (Lab probe locomo_retrieval_map).", True),
]


def count_titles(like):
    con = sqlite3.connect(DB)
    n = con.execute("SELECT COUNT(*) FROM collective_knowledge WHERE title LIKE ?",
                    (f"%{like}%",)).fetchone()[0]
    con.close()
    return n


for label, title, content, should_land in CASES:
    body = json.dumps({"npc": "thief", "title": title, "content": content,
                       "knowledge_type": "discovery"}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = json.loads(r.read())
    except Exception as e:
        resp = {"error": str(e)[:120]}
    time.sleep(0.4)
    marker = title[:40]
    landed = count_titles(marker) > 0
    ok = (landed == should_land)
    print(f"  {label:36s} -> {resp.get('status', resp)}")
    print(f"      landed in the table: {landed}   expected: {should_land}   "
          f"{'PASS' if ok else '!! FAIL'}")
    if resp.get("reason"):
        print(f"      reason: {resp['reason']}")

# clean up the accepted probe row so the corpus is not polluted by this test
con = sqlite3.connect(DB)
con.execute("DELETE FROM collective_knowledge WHERE title LIKE 'GATE-PROBE%'")
con.commit()
con.close()
print("\n  (the accepted probe row was deleted again — the test must not leave knowledge behind)")
