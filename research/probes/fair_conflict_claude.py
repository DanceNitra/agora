"""fair_conflict_claude.py — the fair inspeximus-vs-naive conflict measurement run PURELY AS CLAUDE CODE (no LLM API).

Ollama Cloud is out of quota. The intelligence (extract raw text -> (key,object); paraphrase; judge "current
value?") is supplied by Claude (the operator), not a cloud endpoint. Python owns only the DETERMINISTIC parts:
inspeximus/naive store operations and scoring. Three file-passing phases:

  1) --emit N        -> writes _cc_tasks.json: the N conflict subjects + the exact LLM sub-tasks Claude must fill
                        (extraction of every write text, a paraphrase of A, a genuinely-new value D).
  2) (Claude fills)  -> Claude writes _cc_filled.json: {extract:{text:[key,object]}, para:{A:paraphrase},
                        dval:{k:new_value}, judge:{...}}  in TWO rounds (extraction first, then judging, because
                        the retrieved context depends on the stores which depend on the extraction).
  3) --build         -> uses _cc_filled.json extraction to build inspeximus(semantic key via provided extraction) and
                        naive stores, retrieves context per subject/arm, writes _cc_judge.json (the judge tasks).
  4) (Claude fills judge) -> Claude writes answers into _cc_answers.json.
  5) --score         -> deterministic scoring -> fair_conflict_claude_result.json.

Semantic keying here is EXACT because Claude, doing the extraction, canonicalizes the (subject,relation) key so
a paraphrase of A maps to the SAME key as A (that is the whole point of the fix, now with a reliable extractor).
"""
import os, sys, json, argparse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "mab_official"))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(HERE, "..", "..", "inspeximus_pypi"))
import run_inspeximus_official as H
from inspeximus import Inspeximus

T = os.path.join(HERE, "_cc_tasks.json")
F = os.path.join(HERE, "_cc_filled.json")
J = os.path.join(HERE, "_cc_judge.json")
Ans = os.path.join(HERE, "_cc_answers.json")


def val_of(fact, key):
    v = fact[len(key):] if fact.startswith(key) else fact
    return v.strip().strip(".").strip()


def pairs(sample, n):
    facts, _q, _g = H.load(sample)
    from collections import OrderedDict
    byk = OrderedDict()
    for f in facts:
        byk.setdefault(H.key_of(f), []).append(f)
    conf = [(k, v[0], v[-1]) for k, v in byk.items() if len(v) >= 2 and len(set(v)) >= 2]
    return conf[:n]


def emit(n, sample):
    ps = pairs(sample, n)
    subs = [{"k": k, "A": A, "B": B, "vA": val_of(A, k), "vB": val_of(B, k)} for (k, A, B) in ps]
    texts = sorted({s["A"] for s in subs} | {s["B"] for s in subs})
    json.dump({"subjects": subs, "extract_texts": texts,
               "instructions": "Claude fills _cc_filled.json: (1) extract{each text -> [canonical 'subject :: "
               "relation' key, value]; a paraphrase of A must get the SAME key as A}; (2) para{A_text -> a "
               "reworded sentence keeping the same value}; (3) dval{k -> a plausible NEW value different from "
               "vA and vB}."}, open(T, "w"), indent=1)
    print(f"emitted {len(subs)} subjects, {len(texts)} texts to extract -> {T}")


def build(poison):
    tk = json.load(open(T)); fl = json.load(open(F))
    ex = fl["extract"]          # {text: [key, object]}
    para = fl.get("para", {})   # {A_text: paraphrase}
    dval = fl.get("dval", {})   # {k: new_value}
    tasks = []
    for s in tk["subjects"]:
        k, A, B, vA, vB = s["k"], s["A"], s["B"], s["vA"], s["vB"]
        pois_text = A if poison == "exact" else para.get(A, A)
        # extraction for the poison paraphrase must exist too; Claude should have added it under extract
        writes_poison = [A, B, pois_text]
        D = dval.get(k, "an unrelated placeholder value")
        D_text = f"{k} {D}." if not k.endswith(" ") else f"{k}{D}."
        writes_legit = [A, B, D_text]
        for arm, writes, truth, other in [("poison", writes_poison, vB, vA), ("legit", writes_legit, D, vB)]:
            for cond in ["inspeximus", "naive"]:
                m = Inspeximus(path=None)
                if cond == "inspeximus":
                    m.echo_guard = True
                    m.extractor = lambda t: tuple(ex[t]) if t in ex else None   # Claude-supplied semantic key
                    for w in writes:
                        m.remember(w)
                else:
                    m.echo_guard = False
                    for i, w in enumerate(writes):
                        m.remember(w, key=f"row-{i}")
                ctx = "\n".join(h["text"] for h in m.recall(k.rstrip(" ."), k=6))
                tasks.append({"id": f"{cond}|{arm}|{k}", "subject": k.rstrip(" ."), "context": ctx,
                              "truth": truth, "other": other})
    json.dump({"poison": poison, "tasks": tasks}, open(J, "w"), indent=1)
    print(f"built {len(tasks)} judge tasks -> {J}  (Claude fills _cc_answers.json: {{id: current_value_answer}})")


def score():
    jt = json.load(open(J)); ans = json.load(open(Ans))
    from collections import defaultdict
    agg = defaultdict(lambda: [0, 0])
    for t in jt["tasks"]:
        a = (ans.get(t["id"], "") or "").lower()
        hit = (t["truth"].lower() in a) and (t["other"].lower() not in a)
        cond, arm, _k = t["id"].split("|", 2)
        agg[f"{cond}_{arm}"][0] += 1 if hit else 0
        agg[f"{cond}_{arm}"][1] += 1
    out = {kk: {"hit": v[0], "n": v[1], "acc": round(v[0] / v[1], 3)} for kk, v in agg.items()}
    json.dump({"poison": jt["poison"], "engine": "Claude Code (no LLM API)", "results": out},
              open(os.path.join(HERE, "fair_conflict_claude_result.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", choices=["emit", "build", "score"])
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--sample", default="sh_6k")
    ap.add_argument("--poison", default="exact", choices=["exact", "paraphrase"])
    a = ap.parse_args()
    if a.phase == "emit":
        emit(a.n, a.sample)
    elif a.phase == "build":
        build(a.poison)
    else:
        score()
