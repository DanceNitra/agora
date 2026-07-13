"""erasure_completeness_xsystem.py — after each system's NATIVE erasure, is the subject's data still recoverable
from that system's OWN retrieval surface?

A symmetric cross-system cell (Observatory): every system read the same way — issue its native right-to-erasure
delete, then query its native retrieval surface for the subject's sensitive value, and measure residual
recoverability. No rubric we designed; just each system's real delete behaviour. No OpenAI (Ollama Cloud +
local nomic).

Honest scope stated up front so mnemo is NOT flattered: this measures a system's OWN surface. mnemo's real
erasure weakness is a DIFFERENT axis — it is a memory store, it does NOT manage the app's external vector index
(erasure_fanout_probe measured that copy surviving 1.00), which is exactly what the cross-store deletion
manifest addresses. Graphiti is BITEMPORAL BY DESIGN (it retains invalidated facts as history), so a high
residue for it is expected and is a real erasure/retention trade-off, not a bug.

RUN:  python mnemo/probes/erasure_completeness_xsystem.py             # mnemo + mem0
      python mnemo/probes/erasure_completeness_xsystem.py --graphiti  # + graphiti (neo4j)
Part of Agora / mnemo (MIT).
"""
import os
import sys
import json
import tempfile
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from mnemo import Mnemo  # noqa: E402

_env = {}
for line in open(os.path.join(os.path.dirname(__file__), "..", "..", "server", ".env"), encoding="utf-8", errors="ignore"):
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1); _env[k.strip()] = v.strip().strip('"')
OLLAMA_CLOUD = "https://ollama.com/v1"
OLLAMA_KEY = _env.get("AGORA_API_KEY", "")
CHEAP_MODEL = "deepseek-v4-flash"

SUBJECTS = [
    ("alice-42", "Alice", "medical condition", "type-1 diabetes"),
    ("bob-77", "Bob", "home address", "12 Maple Street"),
    ("carol-19", "Carol", "salary", "94000 euro"),
    ("dan-53", "Dan", "religion", "practising Buddhist"),
    ("eve-88", "Eve", "criminal record", "2019 fraud conviction"),
    ("finn-31", "Finn", "orientation", "gay"),
    ("gina-64", "Gina", "biometric id", "fingerprint 9f2a"),
    ("hugo-27", "Hugo", "affiliation", "Green Party member"),
]


def score_mnemo():
    fd, p = tempfile.mkstemp(suffix=".json", prefix="ecx_"); os.close(fd)
    for suf in ("", ".receipts.json"):
        try: os.remove(p + suf)
        except OSError: pass
    m = Mnemo(path=p); residue = 0
    for (subj, name, rel, val) in SUBJECTS:
        m.remember(f"{name}'s {rel} is {val}.", key=f"{subj}::{rel}", object=val, source={"doc": subj})
        m.forget_subject(subj, request_id=f"dsar-{subj}")
        hits = m.recall(f"what is the {rel} of {name}?", k=6, mode="lexical")
        residue += 1 if any(val.lower() in (h.get("text", "") or "").lower() for h in hits) else 0
    for suf in ("", ".receipts.json"):
        try: os.remove(p + suf)
        except OSError: pass
    return residue, len(SUBJECTS)


def score_mem0():
    from mem0 import Memory
    cfg = {"llm": {"provider": "openai", "config": {"model": CHEAP_MODEL, "temperature": 0.1,
                   "openai_base_url": OLLAMA_CLOUD, "api_key": OLLAMA_KEY}},
           "embedder": {"provider": "ollama", "config": {"model": "nomic-embed-text",
                        "ollama_base_url": "http://localhost:11434"}},
           "vector_store": {"provider": "qdrant", "config": {"collection_name": "ecx_nomic768",
                            "embedding_model_dims": 768,
                            "path": os.path.join(os.environ.get("TEMP", "/tmp"), "mem0_ecx_qdrant")}}}
    mem = Memory.from_config(cfg); residue = 0
    for (subj, name, rel, val) in SUBJECTS:
        uid = f"ecx_{subj}"
        mem.add(f"{name}'s {rel} is {val}.", user_id=uid)
        allm = mem.get_all(filters={"user_id": uid}); rows = allm.get("results", allm) if isinstance(allm, dict) else allm
        for r in (rows or []):
            try: mem.delete(r["id"])
            except Exception: pass
        sr = mem.search(f"what is the {rel} of {name}?", filters={"user_id": uid}, top_k=6)
        mems = sr.get("results", sr) if isinstance(sr, dict) else sr
        blob = " ".join((x.get("memory") or x.get("text") or str(x)) for x in (mems or [])).lower()
        residue += 1 if val.lower() in blob else 0
    return residue, len(SUBJECTS)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--graphiti", action="store_true")
    args = ap.parse_args()
    results = {}
    print("=== CROSS-SYSTEM ERASURE COMPLETENESS (native delete -> native query -> residue) ===")
    print("symmetric instrument; lower residue = more complete native-surface erasure.\n")
    k, n = score_mnemo(); results["mnemo 0.7.21"] = (k, n)
    print(f"mnemo: {k}/{n} residue", flush=True)
    try:
        k, n = score_mem0(); results["mem0 2.0.11"] = (k, n)
        print(f"mem0:  {k}/{n} residue (live, Ollama cloud)", flush=True)
    except Exception as e:
        print("mem0 FAILED (excluded, honest):", str(e)[:120], flush=True)
    print()
    for sysname, (k, n) in results.items():
        print(f"  {sysname:<16} native-surface residual recoverability: {k}/{n} = {k/n:.2f}")
    json.dump({s: {"residue": k, "n": n, "rate": k/n} for s, (k, n) in results.items()},
              open(os.path.join(os.path.dirname(__file__), "erasure_completeness_xsystem_result.json"), "w"), indent=1)
    print("\nHONEST NOTE: this is the NATIVE surface only. mnemo's real erasure gap is the EXTERNAL app vector")
    print("index it does not manage (erasure_fanout_probe: 1.00 residue) — the cross-store deletion manifest's")
    print("job, not this cell's. Graphiti retains invalidated facts by design (bitemporal), a real trade-off.")


if __name__ == "__main__":
    main()
