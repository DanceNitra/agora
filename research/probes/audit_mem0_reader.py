"""What does mem0 actually return? The live harness scored n=0 -- it could not read the answers.

Every one of eight cases came back "no opinion": neither the retired value string nor the corrected one
appeared in what mem0 served. That is not a result about mem0, it is a broken reader, and "stale=0.000
over n=0" is a rate with no denominator -- exactly the shape of number this project refuses to publish.

mem0 extracts FACTS with an LLM rather than storing raw text, so the served memory is a reformulation and
a substring test for "db-old-07" can miss a memory that says the same thing. Before any number about mem0
goes anywhere, print what it really returns for one case, at each step.
"""
import os
import sys
import time
import warnings

warnings.filterwarnings("ignore")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))

_env = {}
for line in open(os.path.join(HERE, "..", "..", "server", ".env"), encoding="utf-8", errors="ignore"):
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        _env[k.strip()] = v.strip().strip('"')

from mem0 import Memory  # noqa: E402

cfg = {"llm": {"provider": "openai",
               "config": {"model": "deepseek-v4-flash", "temperature": 0.1,
                          "openai_base_url": "https://ollama.com/v1",
                          "api_key": _env.get("AGORA_API_KEY", "")}},
       "embedder": {"provider": "ollama",
                    "config": {"model": "nomic-embed-text",
                               "ollama_base_url": "http://localhost:11434"}},
       "vector_store": {"provider": "qdrant",
                        "config": {"collection_name": f"reader_{int(time.time())}",
                                   "embedding_model_dims": 768, "on_disk": False}}}
mem = Memory.from_config(cfg)
uid = f"reader-{int(time.time())}"

steps = [("write   ", "alice's primary database host is db-old-07"),
         ("correct ", "alice's primary database host is now db-new-12"),
         ("echo    ", "just so it is on record, alice keeps the primary database on the host db-old-07")]

for label, msg in steps:
    res = mem.add(msg, user_id=uid)
    rows = res.get("results", res) if isinstance(res, dict) else res
    print(f"{label} {msg}")
    for r in (rows or []):
        print(f"          add -> event={r.get('event')!r}  memory={r.get('memory')!r}")

print("\nsearch('alice primary database host'):")
res = mem.search("alice primary database host", filters={"user_id": uid}, limit=5)
rows = res.get("results", res) if isinstance(res, dict) else res
for r in (rows or []):
    print(f"   score={r.get('score')!r}  memory={r.get('memory')!r}")

print("\nget_all:")
allm = mem.get_all(filters={"user_id": uid})
rows = allm.get("results", allm) if isinstance(allm, dict) else allm
for r in (rows or []):
    print(f"   {r.get('memory')!r}")

print("\nDoes either literal appear anywhere above? old='db-old-07' new='db-new-12'.")
print("If mem0 stores a reformulation, the reader must compare on the VALUE as mem0 renders it,")
print("or the cell is unmeasurable and must be reported as unmeasurable -- not as 0.000 over n=0.")
