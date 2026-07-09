"""mnemo/bench/robustness.py — a runnable, backend-agnostic AGENT-MEMORY ROBUSTNESS scorecard.

Vendors self-report recall wins (LoCoMo/LongMemEval); almost nobody reports what happens when memory is
CORRECTED and then the stale value comes back. This scores exactly that, on a public labeled fixture, for
ANY memory backend behind a tiny adapter — so you can point it at mnemo, a naive store, or your own.

Dimensions (retrieval-level, no LLM needed):
  correction_persistence : after "X is A" then "correction: X is B", does recall(question) return B?  (want 1.0)
  echo_resistance        : ...then the OLD value A is re-stated (verbatim or paraphrased) — does recall
                           STILL return B (not resurrected A)?                                           (want 1.0)

An adapter is any object with:
  reset()                         -> fresh store
  store(fact_id, text, key=None)  -> ingest an assertion (key groups a (subject,relation) fact)
  recall(query, k=5) -> list[str] -> top-k assertion texts, freshest-correct first

Ships three adapters: NaiveStore (last-writer-wins recall, no supersession), Mnemo (default),
Mnemo(echo_guard=True). Add your own to benchmark mem0/Zep/etc.

DATA: agora_output/public_fixtures/contradiction_echo_detection_fixture.jsonl (MIT, MemBench-derived).
RUN:  python -m mnemo.bench.robustness      (or python mnemo/bench/robustness.py)
"""
import json, os, sys, tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "mnemo")))
from mnemo import Mnemo

FIXTURE = os.environ.get("ROBUSTNESS_FIXTURE",
                         "agora_output/public_fixtures/contradiction_echo_detection_fixture.jsonl")

# ----------------------------- adapters -----------------------------
class NaiveStore:
    """Last-writer-wins vector-ish store with NO supersession: recall ranks by lexical overlap, newest
    first on ties. Models the common 'just append and retrieve' memory."""
    name = "naive (append + recall)"
    def reset(self): self.items = []
    def store(self, fid, text, key=None): self.items.append((fid, text, key))
    def _score(self, q, text):
        qt, tt = set(q.lower().split()), set(text.lower().split())
        return len(qt & tt) / (len(qt) + 1e-9)
    def recall(self, query, k=5):
        ranked = sorted(enumerate(self.items), key=lambda it: (self._score(query, it[1][1]), it[0]), reverse=True)
        return [t for _, (_, t, _) in ranked[:k]]

class MnemoAdapter:
    def __init__(self, echo_guard=False):
        self.echo_guard = echo_guard
        self.name = f"mnemo (echo_guard={'on' if echo_guard else 'off'})"
    def reset(self):
        fd, p = tempfile.mkstemp(suffix=".json"); os.close(fd); os.remove(p)
        self.m = Mnemo(path=p); self.m.echo_guard = self.echo_guard
    def store(self, fid, text, key=None, object=None):
        self.m.remember(text, key=key, object=object)
    def recall(self, query, k=5):
        return [r["text"] for r in self.m.recall(query, k=k, mode="lexical")]

# ----------------------------- scoring -----------------------------
def load_cases():
    """Group fixture rows by fact -> (question, current_fact, stale_echoes[]). One fact per (question)."""
    by = {}
    for line in open(FIXTURE, encoding="utf-8"):
        r = json.loads(line)
        key = r["question"]
        d = by.setdefault(key, {"question": r["question"], "current": r["current_fact"],
                                "old_verbatim": None, "old_paraphrase": None})
        if r["candidate_kind"] == "stale_echo_verbatim": d["old_verbatim"] = r["candidate"]
        elif r["candidate_kind"] == "stale_echo_paraphrase": d["old_paraphrase"] = r["candidate"]
    return [c for c in by.values() if c["old_verbatim"]]

def _returns_current(recalled, current, old):
    """Did the store surface the CURRENT value above/instead of the stale one? Rank-based: current must
    appear and outrank any stale echo."""
    def firstpos(target):
        for i, t in enumerate(recalled):
            if target and target.strip() and target.strip()[:60].lower() in t.lower():
                return i
        return 10 ** 9
    return firstpos(current) < firstpos(old)

def score(adapter, cases, echo_kind):
    persist_ok, echo_ok = 0, 0
    for c in cases:
        old = c["old_verbatim"] if echo_kind == "verbatim" else (c["old_paraphrase"] or c["old_verbatim"])
        key = "fact::" + c["question"]
        # 1) assert old, then correct to current
        adapter.reset()
        _store(adapter, "a", old, key, _val(old, c))
        _store(adapter, "b", c["current"], key, _val(c["current"], c))
        if _returns_current(adapter.recall(c["question"]), c["current"], old):
            persist_ok += 1
        # 2) ...then the ECHO of the old value arrives
        _store(adapter, "e", old, key, _val(old, c))
        if _returns_current(adapter.recall(c["question"]), c["current"], old):
            echo_ok += 1
    n = len(cases)
    return persist_ok / n, echo_ok / n

def _val(text, c):
    """best-effort object token for mnemo keyed supersession: the fixture doesn't label the object, so
    use the whole assertion text as the object signature (value-preserving echoes still match)."""
    return text

def _store(adapter, fid, text, key, obj):
    try:
        adapter.store(fid, text, key=key, object=obj)   # mnemo adapter
    except TypeError:
        adapter.store(fid, text, key=key)               # naive adapter

def main():
    cases = load_cases()
    adapters = [NaiveStore(), MnemoAdapter(echo_guard=False), MnemoAdapter(echo_guard=True)]
    print(f"Agent-Memory Robustness Scorecard  (n={len(cases)} corrected facts)\n")
    print(f"{'backend':28s} {'correction':>11s} {'echo-resist':>12s} {'echo-resist':>12s}")
    print(f"{'':28s} {'persists':>11s} {'(verbatim)':>12s} {'(paraphrase)':>12s}")
    print("-" * 66)
    out = {}
    for a in adapters:
        p, ev = score(a, cases, "verbatim")
        _, ep = score(a, cases, "paraphrase")
        print(f"{a.name:28s} {p:>11.2f} {ev:>12.2f} {ep:>12.2f}")
        out[a.name] = {"correction_persists": round(p, 3),
                       "echo_resist_verbatim": round(ev, 3),
                       "echo_resist_paraphrase": round(ep, 3)}
    os.makedirs("agora_output/public_fixtures", exist_ok=True)
    json.dump(out, open("agora_output/public_fixtures/robustness_scorecard.json", "w"), indent=2)
    print("\n1.0 = the store keeps the corrected value; lower = the stale value resurfaces.")
    print("-> agora_output/public_fixtures/robustness_scorecard.json")

if __name__ == "__main__":
    main()
