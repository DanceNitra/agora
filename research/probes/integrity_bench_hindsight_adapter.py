"""Drive Hindsight 0.9.2 through the integrity-bench correction task, and find out what it exposes.

WHY. On 2026-08-25 the external map surfaced vectorize-io/hindsight (21k stars, "Agent Memory That
Learns") as one of 26 GitHub projects voicing our exact axis. Their own issue #2696 states the
failure inspeximus exists for, in their words: "incorrect or deprecated memories continue surfacing
in recall, compounding over time because every mention (including corrections) reinforces the
vector representation." Their maintainer closed it `not_planned` with "we already have it",
pointing at Reversible Memory Curation in 0.8.2 (2026-06-12): edit, invalidate, revert.

That is a claim on our axis from a bigger product, so the honest move is our own standing rule --
do not self-score on home fixtures, run the integrity task against them in native config and
publish whichever way it falls.

WHAT THIS FILE IS. The reachability half, built first because a benchmark cell that cannot call the
operation measures nothing. Reading their source got me three wrong answers in a row (a route scan
that found 3 of 97 routes; two absence claims from regexes that matched nothing), which is the
failure mode this repository names most often. So this CALLS the thing.

It answers, by execution rather than by grep:
  1. does the embedded server start with an OpenAI-compatible endpoint that is not OpenAI
  2. does retain -> recall work at all, so later arms have a baseline
  3. is the correction lifecycle (state=invalid, and back) reachable from a CLIENT, or only from
     the control plane -- which is the difference between an agent that can correct itself and an
     operator who must
  4. and after a correction, does the OLD value still surface in recall

COST. The embedded server needs an LLM for fact extraction on retain. This wiring run points at
Ollama cloud, which is our own credit and NOT their native config, so nothing here is a published
comparison -- it establishes that the harness can drive them. A publishable cell must re-run in
their documented native config (openai/gpt-5-mini per their README) and say so.

RUN: python research/probes/integrity_bench_hindsight_adapter.py
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))


def env_from(path: str) -> dict:
    out = {}
    if not os.path.exists(path):
        return out
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def main() -> int:
    try:
        from hindsight import HindsightClient, HindsightServer
    except ImportError:
        print("REFUSED: hindsight is not importable here. This probe must run in the venv that has "
              "`pip install hindsight-all`; it deliberately does not install anything itself.")
        return 2

    e = env_from(os.path.join(ROOT, "server", ".env"))
    key = e.get("AGORA_CHEAP_API_KEY") or e.get("OLLAMA_API_KEY") or e.get("AGORA_API_KEY") or ""
    base = "https://ollama.com/v1"
    model = "deepseek-v4-flash:0731-cloud"
    if not key:
        print("REFUSED: no API key found in server/.env; retain needs an extractor and a run "
              "without one would report an empty store as a finding")
        return 2

    v: dict = {}
    notes: list = []
    t0 = time.time()
    print(f"  starting embedded Hindsight against {base} ({model})", flush=True)

    srv = None
    try:
        srv = HindsightServer(llm_provider="openai", llm_model=model,
                              llm_api_key=key, llm_base_url=base)
        srv.__enter__()
        v["the_embedded_server_starts"] = True
        print(f"[{time.time()-t0:6.1f}s] server up at {srv.url}", flush=True)
        c = HindsightClient(base_url=srv.url)
        bank = "integrity-probe"
        try:
            c.create_bank(bank_id=bank)
        except Exception:
            pass

        # --- 2. the baseline every later arm needs -------------------------------------------
        c.retain(bank_id=bank, content="The staging database is db-3.internal.")
        time.sleep(2)
        r1 = c.recall(bank_id=bank, query="which staging database")
        blob1 = json.dumps(r1, default=str)
        v["retain_then_recall_returns_the_fact"] = "db-3" in blob1
        print(f"[{time.time()-t0:6.1f}s] baseline recall carries db-3: "
              f"{v['retain_then_recall_returns_the_fact']}", flush=True)

        # --- 3. is the lifecycle reachable from a CLIENT? -------------------------------------
        # The blog says edit / invalidate / revert. The high-level client has no update_memory,
        # and `memory` is a property rather than a call, so this asks the object itself instead
        # of asserting from a name list -- twice today a name list was wrong.
        surface = sorted(m for m in dir(c) if not m.startswith("_"))
        lifecycle = [m for m in surface
                     if any(k in m.lower() for k in
                            ("invalid", "revert", "correct", "update", "state", "edit"))]
        v["client_exposes_no_revert_by_name"] = not any(
            "revert" in m.lower() for m in surface)
        notes.append({"client_surface_size": len(surface), "lifecycle_named": lifecycle})
        print(f"[{time.time()-t0:6.1f}s] client lifecycle-ish methods: {lifecycle}", flush=True)

        # Can we reach a memory unit and set its state at all?
        mems = None
        for getter in ("list_memories", "memories"):
            f = getattr(c, getter, None)
            if f is None:
                continue
            try:
                mems = f(bank_id=bank) if callable(f) else f
                break
            except Exception as ex:                                   # noqa: BLE001
                notes.append({"getter_failed": getter, "error": str(ex)[:200]})
        v["a_memory_unit_can_be_listed"] = bool(mems)
        notes.append({"memories_repr": str(mems)[:400]})
        print(f"[{time.time()-t0:6.1f}s] memory units listable: "
              f"{v['a_memory_unit_can_be_listed']}", flush=True)

        # --- 4. the correction, and whether the old value survives it -------------------------
        c.retain(bank_id=bank, content="Correction: the staging database is now db-7.internal.")
        time.sleep(2)
        r2 = c.recall(bank_id=bank, query="which staging database")
        blob2 = json.dumps(r2, default=str)
        v["after_correction_the_new_value_is_present"] = "db-7" in blob2
        # THE MEASUREMENT THAT MATTERS, and it is their own issue's words: does the corrected-away
        # value still surface? Not scored as a verdict here -- recorded, because one case is not a
        # rate and this run is not in their native config.
        notes.append({"old_value_still_in_recall_after_correction": "db-3" in blob2,
                      "recall_after_correction": blob2[:600]})
        print(f"[{time.time()-t0:6.1f}s] after correction: db-7 present="
              f"{v['after_correction_the_new_value_is_present']}, db-3 still present="
              f"{'db-3' in blob2}", flush=True)

        # --- controls -------------------------------------------------------------------------
        v["CONTROL_recall_is_not_empty"] = bool(blob1.strip()) and len(blob1) > 20
        v["CONTROL_the_two_recalls_differ"] = blob1 != blob2

    except Exception as ex:                                           # noqa: BLE001
        notes.append({"fatal": f"{type(ex).__name__}: {ex}",
                      "trace": traceback.format_exc()[-1200:]})
        v.setdefault("the_embedded_server_starts", False)
        print(f"  FAILED: {type(ex).__name__}: {str(ex)[:200]}", flush=True)
    finally:
        if srv is not None:
            try:
                srv.__exit__(None, None, None)
            except Exception:                                         # noqa: BLE001
                pass

    for k, ok in v.items():
        print(f"  {'YES' if ok else 'no '}  {k}")
    out = os.path.join(HERE, "integrity_bench_hindsight_adapter_result.json")
    json.dump({"probe": os.path.basename(__file__), "verdicts": v, "notes": notes,
               "llm": {"base_url": base, "model": model,
                       "NOT_native_config": "their README documents openai/gpt-5-mini; this run "
                                            "uses our Ollama credit and is a wiring test only"},
               "hindsight_version": "0.9.2"},
              open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\nwrote {out}")
    return 0 if v.get("the_embedded_server_starts") else 1


if __name__ == "__main__":
    sys.exit(main())
