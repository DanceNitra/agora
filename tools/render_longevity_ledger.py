"""
render_longevity_ledger - turn longevity_ledger.json into a maintained Markdown tracker.

A living calibrated prior: edit longevity_ledger.json (add a row, or flip a status when a trial
reports) and re-run this to regenerate the tracker + the running translation rate. The headline
number IS the empirical base rate a forecaster should carry into the next longevity headline.

Usage:  python render_longevity_ledger.py          # writes agora_output/longevity_ledger.md
        python render_longevity_ledger.py --check   # print the tally only
Zero dependencies (stdlib only).
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "longevity_ledger.json")
OUT = os.path.join(HERE, "..", "agora_output", "longevity_ledger.md")

ICON = {"proven": "✅", "failed": "❌", "null_or_safety": "🟡", "pending": "⏳", "no_human_outcome": "⬜"}
LABEL = {"proven": "proven (hard endpoint)", "failed": "tested, did NOT translate",
         "null_or_safety": "human trial: safety/biomarker/null only", "pending": "human trial pending",
         "no_human_outcome": "no human outcome data (mouse/cell/observational only)"}


def tally(items):
    counts = {k: 0 for k in ICON}
    for it in items:
        counts[it["status"]] = counts.get(it["status"], 0) + 1
    return counts


def render(d):
    items = d["interventions"]
    n = len(items)
    c = tally(items)
    any_trial = c["failed"] + c["null_or_safety"] + c["pending"]
    L = []
    L.append(f"# {d['title']}")
    L.append(f"_{d['subtitle']}_")
    L.append(f"\n**Updated:** {d['updated']}  ·  **Interventions tracked:** {n}")
    L.append(f"\n## The running number\n")
    L.append(f"- **Proven human benefit on a hard clinical endpoint: {c['proven']} / {n}**")
    L.append(f"- Tested in humans and did NOT translate: {c['failed']} / {n}")
    L.append(f"- Human trial reported but safety/biomarker/null only: {c['null_or_safety']} / {n}")
    L.append(f"- Human trial pending (no hard-endpoint result yet): {c['pending']} / {n}")
    L.append(f"- No meaningful human outcome data yet: {c['no_human_outcome']} / {n}")
    L.append(f"- (Has *any* human trial reported: {any_trial} / {n})")
    L.append(f"\n## The ledger\n")
    L.append("| | Intervention | Mouse evidence | Human hard-endpoint status |")
    L.append("|---|---|---|---|")
    order = {"proven": 0, "failed": 1, "null_or_safety": 2, "pending": 3, "no_human_outcome": 4}
    for it in sorted(items, key=lambda x: order.get(x["status"], 9)):
        tag = "ITP" if it.get("itp") else ""
        nm = f"**{it['name']}**" + (f" ({tag})" if tag else "")
        L.append(f"| {ICON[it['status']]} | {nm} | {it['mouse']} | {it['human']} |")
    L.append("\n**Legend:** " + "  ·  ".join(f"{ICON[k]} {LABEL[k]}" for k in ICON))
    L.append(f"\n## Method & honest caveats\n")
    L.append(d["method"])
    L.append("\n- The headline '0 proven' reflects BOTH genuine non-translation AND the near-"
             "impossibility of decades-long human-lifespan RCTs - read it as 'no proven win yet', "
             "not 'everything fails'. Aspirin (ASPREE) is the one row that is a tested failure.")
    L.append("- This is a flagship sample, not the full ITP (~35) population; the robust claim is the "
             "pattern (0 proven; best cases are safety/biomarker/null), which only sharpens with the full list.")
    L.append("- A new positive hard-endpoint human result on ANY row (e.g. a positive TAME) would move "
             "the number and should update the prior.")
    return "\n".join(L) + "\n", c, n


def main():
    d = json.load(open(DATA, encoding="utf-8"))
    md, c, n = render(d)
    if "--check" in sys.argv:
        print(f"{n} interventions | proven {c['proven']} | failed {c['failed']} | "
              f"null/safety {c['null_or_safety']} | pending {c['pending']} | no-data {c['no_human_outcome']}")
        return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(md)
    print(f"wrote {os.path.relpath(OUT)}  ({n} interventions, {c['proven']}/{n} proven in humans)")


if __name__ == "__main__":
    main()
