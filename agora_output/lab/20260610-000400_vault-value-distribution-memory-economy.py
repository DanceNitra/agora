
import sys, json, collections
sys.path.insert(0, r"C:/Users/Danculus/agora/server")
from agora.execution.memory_economy import score_notes
notes = score_notes(r"C:/Users/Danculus/my-second-brain")
vals = [n["value"] for n in notes]
hist = collections.Counter(vals)
n = len(vals)
print(f"notes={n} mean_value={sum(vals)/n:.2f}")
print("value histogram:", dict(sorted(hist.items())))
qs = sorted(vals)
for p in (10, 25, 50, 75, 90):
    print(f"p{p}={qs[int(n*p/100)]}")
ever = sum(1 for x in notes if x["evergreen"])
print(f"evergreen={ever} ({ever/n:.1%}) orphans={sum(1 for x in notes if x['inlinks']+x['outlinks']==0)}")
