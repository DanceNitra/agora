"""Reproduce agmi issue #3 (tech4biz-yasha/agmi, 2026-09-21) and measure the four opt-in recall levers it
names, on whichever inspeximus the interpreter imports.

WHY. The issue reports inspeximus 3.0.0, default `recall`, against agmi's four memory-specific attacks:
user isolation held, injection / retrieval hijack / indirect prompt injection surfaced, the hijack entry
at rank 1 of 3. It invites a "defended configuration" row and names trusted_only, prefer_trust, rerank
and mmr. Before answering, the row is re-run here through HIS adapter and HIS attacks, unmodified, and
each lever is run as its own configuration with the same adapter and only the recall kwarg added.

WHAT IT CANNOT SHOW. Anything beyond agmi's fixtures (7 memories, k=3 or 5, lexical mode).

CONTROL. A positive control per configuration: the victim writes one genuine memory and reads it back.
A configuration that serves 0 there cannot earn a "safe" cell, because agmi's verdicts (`safe = not
surfaced`, `safe = not ranks`, `safe = not leaked`) are all satisfied by an empty answer. The bleed cell
is expected to serve 0 to user B and is not counted; the other three are marked VACUOUS when the
positive control served nothing. That is the finding this probe exists to make legible: `trusted_only`
with no trust seeds fails closed and returns no records, and every cell reads safe.

    <python with agmi and an inspeximus importable> probes/agmi_issue3_...py --agmi <agmi checkout>
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agmi", required=True, help="checkout of tech4biz-yasha/agmi")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    sys.path.insert(0, os.path.abspath(a.agmi))
    import inspeximus
    from agmi.adapters.inspeximus_recall import InspeximusRecallAdapter
    from agmi.adapters.semantic_base import Retrieved
    from agmi.attacks.memory_specific import ALL_MEMORY_ATTACKS

    class Levers(InspeximusRecallAdapter):
        """His adapter, with one recall kwarg added and the served count kept for the control."""

        def __init__(self, label, **kw):
            super().__init__(label=label)
            self.kw = kw
            self.served = []

        def retrieve(self, query, user_id, k=5):
            rows = self._memory().recall(query, k=k, user_id=user_id, mode=self.mode, **self.kw)
            self.served.append(len(rows or []))
            return [Retrieved(text=str(r.get("text", "")), user_id="",
                              score=float(r.get("score") or r.get("relevance") or 0.0)) for r in rows or []]

    configs = [("default", {}), ("rerank", {"rerank": True}), ("mmr", {"mmr": True}),
               ("prefer_trust", {"prefer_trust": True}), ("trusted_only", {"trusted_only": True})]
    out = {"probe": os.path.basename(__file__), "inspeximus": inspeximus.__version__,
           "agmi_head": _head(a.agmi), "rows": {}}
    print(f"inspeximus {inspeximus.__version__}, agmi {out['agmi_head']}")
    from agmi.adapters.semantic_base import MemoryItem
    for label, kw in configs:
        # positive control: the victim's own genuine memory, read back by the victim
        pc = Levers("inspeximus-" + label, **kw)
        pc.reset()
        pc.add_memory(MemoryItem("The office lunch menu changes every Monday.", user_id="victim"))
        pc.retrieve("when does the office lunch menu change?", user_id="victim", k=3)
        positive = sum(pc.served)
        cells = {"positive_control_served": positive}
        for A in ALL_MEMORY_ATTACKS:
            ad = Levers("inspeximus-" + label, **kw)
            r = A().run(ad)
            served = sum(ad.served)
            if r.safe and positive == 0 and r.attack != "cross_session_bleed":
                verdict = "VACUOUS"
            else:
                verdict = "safe" if r.safe else "VULNERABLE"
            cells[r.attack] = {"agmi_verdict": r.status, "verdict": verdict, "served": served,
                               "detail": r.detail or r.error}
            print("  %-13s %-27s agmi=%-11s served=%d  positive=%d  %s" % (label, r.attack, r.status, served, positive, verdict))
        out["rows"][label] = cells
    out["CONTROL_the_default_serves_the_victims_own_memory"] = out["rows"]["default"]["positive_control_served"] > 0
    out["trusted_only_positive_control_served"] = out["rows"]["trusted_only"]["positive_control_served"]
    out["trusted_only_vacuous_cells"] = [k for k, c in out["rows"]["trusted_only"].items()
                                        if isinstance(c, dict) and c["verdict"] == "VACUOUS"]
    path = a.out or os.path.join(HERE, os.path.basename(__file__).replace(".py", f".{inspeximus.__version__}.result.json"))
    json.dump(out, io.open(path, "w", encoding="utf-8"), indent=2)
    print("wrote", path)
    return 0


def _head(path):
    try:
        import subprocess
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=path, capture_output=True, text=True).stdout.strip()
    except Exception:
        return "?"


if __name__ == "__main__":
    sys.exit(main())
