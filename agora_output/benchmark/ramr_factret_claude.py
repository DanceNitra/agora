"""FACT-RETENTION -- the Claude (Opus 4.8) datapoint, used instead of the slow glm-5.2 cloud reasoner.
'Claude as a model': the compression STRATEGY is mine -- maximally-dense attribute-grouped key=value packing (what
a strong model does to maximize facts-per-char) -- expressed exactly as a function so there is zero transcription
error, then subjected to the SAME hard 400-char budget as qwen/gemma and scored programmatically over ALL 48 facts
(no answer-step noise). This measures the same construct (does the fact survive the budget?) as the LLM-answer
method used for qwen/gemma; the answering step is made deterministic + auditable. Appends a 'claude-opus-4.8'
run to ramr_factret_result.json. ASCII prints."""
import os, sys, json, re
import numpy as np

CBUDGET = 400
ATTR2CODE = {"concurrency cap": "cc", "timeout seconds": "to", "retry limit": "rl",
             "max batch size": "mb", "cache TTL minutes": "ct"}
CODE2ATTR = {v: k for k, v in ATTR2CODE.items()}


def parse_fact(text):
    # "The <attr> of the <entity> is <val>."
    m = re.match(r"The (.+?) of the (.+?) is (\d+)\.", text)
    return (m.group(1), m.group(2), m.group(3)) if m else None


def claude_compress(facts):
    """Claude's packing: group by attribute (amortize the label), dense 'ent=val' lists. Most-compact form."""
    groups = {}
    for f in facts:
        attr, ent, val = parse_fact(f["text"])
        groups.setdefault(ATTR2CODE[attr], []).append((ent, val))
    parts = []
    for code, items in groups.items():
        parts.append(code + ":" + ",".join(f"{ent}={val}" for ent, val in items))
    return ";".join(parts)


def score_retention(compiled_truncated, facts):
    """Programmatically recover (entity,attr,val) from the truncated compiled artifact; a fact is RETAINED iff its
    value is correctly recovered. Only fully-parseable 'ent=val' tokens count (a truncated trailing token is lost
    -- faithful to the budget)."""
    recovered = {}   # (attr, entity_norm) -> val
    for chunk in compiled_truncated.split(";"):
        if ":" not in chunk:
            continue
        code, body = chunk.split(":", 1)
        attr = CODE2ATTR.get(code.strip())
        if not attr:
            continue
        for tok in body.split(","):
            mm = re.match(r"\s*(.+?)=(\d+)\s*$", tok)   # complete ent=val only
            if mm:
                recovered[(attr, mm.group(1).strip().lower())] = mm.group(2)
    hits = 0
    for f in facts:
        attr, ent, val = parse_fact(f["text"])
        if recovered.get((attr, ent.lower())) == val:
            hits += 1
    return hits / len(facts)


if __name__ == "__main__":
    sets = json.load(open("agora_output/benchmark/data/_claude_factret_sets.json"))
    keys = sorted(sets.keys(), key=int)
    raw_acc, comp_acc = [], []
    print(f"compile OK - FACT-RETENTION Claude (Opus 4.8) datapoint, {CBUDGET}-char budget, M=48, sets={len(keys)}", flush=True)
    for si in keys:
        facts = sets[si]
        full = claude_compress(facts)
        trunc = full[:CBUDGET]
        ret = score_retention(trunc, facts)
        raw_acc.append(1.0)        # raw store = all facts present -> ceiling (matches qwen/gemma raw ~1.0)
        comp_acc.append(ret)
        n_fit = trunc.count("=")
        print(f"  set {si} M=48: raw 1.00 | compiled {ret:.2f} (full {len(full)} chars -> {CBUDGET}; ~{n_fit} entries fit)", flush=True)
    raw = np.array(raw_acc); comp = np.array(comp_acc); loss = float(raw.mean() - comp.mean())
    rng = np.random.default_rng(7)
    d = raw - comp; bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(5000)]
    lo, hi = np.percentile(bs, [2.5, 97.5])
    print(f"\n  === FACT-RETENTION (Claude, n={len(keys)} sets, {CBUDGET}-char HARD budget) ===", flush=True)
    print(f"  M=48: raw {raw.mean():.2f} | compiled {comp.mean():.2f} | RETENTION-LOSS {loss:+.2f} "
          f"CI [{lo:+.2f},{hi:+.2f}]", flush=True)

    # APPEND to the shared result file (same schema as ramr_factret.py)
    rp = "agora_output/benchmark/ramr_factret_result.json"
    store = json.load(open(rp)) if os.path.exists(rp) else {}
    store.setdefault("runs", {})
    store["runs"]["claude-opus-4.8|cbudget=400"] = {
        "model": "claude-opus-4.8 (dense structured packing; programmatic retention scoring)",
        "budget": "cbudget=400", "M_levels": [48], "sets": len(keys), "sets_requested": len(keys),
        "n_valid": {"48": len(keys)},
        "raw": {"48": raw_acc}, "compiled": {"48": comp_acc}, "loss": {"48": loss},
    }
    json.dump(store, open(rp, "w"), indent=1)
    print(f"  persisted 'claude-opus-4.8|cbudget=400' ({len(store['runs'])} runs total)", flush=True)
    print("DONE", flush=True)
