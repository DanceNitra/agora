"""RECALL of the server-side gate against what the store actually holds, plus false alarms.

A guard is judged by what fraction of real offenders it catches — not by whether it exists.
"""
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\Danculus\agora\server")
from agora.execution.non_finding import is_non_finding  # noqa: E402

con = sqlite3.connect(r"C:\Users\Danculus\agora\server\agora.db")
con.row_factory = sqlite3.Row
rows = con.execute("SELECT title, content FROM collective_knowledge "
                   "WHERE knowledge_type='discovery' ORDER BY created_at DESC LIMIT 400").fetchall()

MARK = ("do not support", "does not support", "none of the provided", "no source",
        "yields no substantive", "contain the specified equation")


def offender(r):
    return any(m in ((r["title"] or "") + " " + (r["content"] or "")).lower() for m in MARK)


off = [r for r in rows if offender(r)]
good = [r for r in rows if not offender(r)]
caught = [r for r in off if is_non_finding(r["title"], r["content"])]
fa = [r for r in good if is_non_finding(r["title"], r["content"])]

print(f"discoveries inspected : {len(rows)}")
print(f"non-findings present  : {len(off)}  ({len(off)/max(len(rows),1):.0%})")
print(f"caught by the gate    : {len(caught)}  RECALL {len(caught)/max(len(off),1):.1%}")
print(f"false alarms          : {len(fa)} / {len(good)}  ({len(fa)/max(len(good),1):.1%})")

if fa:
    print("\nreal findings the gate would have rejected — each must be checked by hand:")
    for r in fa[:6]:
        print(f"   ! {(r['title'] or '')[:100]}")

missed = [r for r in off if r not in caught]
if missed:
    print(f"\nstill missed ({len(missed)}) — left uncaught on purpose if widening risks real findings:")
    for r in missed[:4]:
        print(f"   - {(r['content'] or '')[:110]}")

print("\n=== CONTROL: the gate must not reject an ordinary finding ===")
ok_samples = [
    "Measured: centering the corpus mean before cosine lifts recall@10 by 0.04 on LoCoMo (n=419).",
    "The provided sources support the claim that BM25 is a strong baseline (Thakur et al. 2021).",
    "Smith (2019) reviewed VR applications in episodic memory and found no effect on consolidation.",
    # the sentence the unanchored pattern must NOT swallow: a real finding about real data
    "Smith (2019) found that the provided data do not support the hypothesis of spaced repetition.",
    "Our replication shows the cited sources do not support a 40% effect; the true value is 12%.",
]
for s in ok_samples:
    print(f"   {'REJECTED (bad!)' if is_non_finding(s) else 'accepted      '}  {s[:88]}")
