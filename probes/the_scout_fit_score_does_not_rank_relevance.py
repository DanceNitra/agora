"""The Scout's `fit` score is uncorrelated with whether the issue is about agent memory at all.

Six `Scout triage` tasks sat in the Claude inbox carrying 18 leads between them, each with a `fit`
score the Scout assigned. Working them meant reading 18 issues, so the score is what decides where the
attention goes -- and the score turns out not to rank the thing it is used to rank.

Measured over all 18 leads, live from the GitHub API:

    Spearman(fit, agent-memory term density) = 0.100    n = 18

(An earlier pass reported 0.001 using a term list that counted the bare word
`provenance`. Same conclusion, different number; the receipt beside this file is the
one that counts.)

The top-scored lead in the entire queue, `neomjs/neo#16706` at **fit 14**, is an Epic about a
deployment plane that cannot recover itself and about the provenance of its own issue body. Four leads
scoring 10-12 use "memory" in the **RAM** sense and have nothing to do with us:

    openclaw/openclaw#115424   fit 11   V8 heap OOM              RAM 37 / agent 0
    openai/codex#31793         fit 10   Chromium PartitionAlloc  RAM 10 / agent 0
    memgraph/memgraph#3607     fit 12   container persistence    RAM  3 / agent 0
    gosuda/bitcoin-rs#39       fit 11   hot-path attribution     RAM  3 / agent 0

This is the same defect the external map had, one organ over: `external_library.AXIS` documents its
own repair, where the bare word `source` admitted 94 records ("fyxer or like api sourceforge?") and
inflated provenance/trust to 108 projects when only 16 said provenance or attribution. A word that
carries no concept becomes a research direction there, and an outreach target here.

THE CLASSIFIER IS A SCREEN, NOT A VERDICT, and its first version proved why. It counted the bare word
`provenance`, which scored `neomjs/neo#16706` as ours -- the issue uses it about the provenance of its
own body text. Every term below is now bound to a memory noun, and the shortlist is still read by hand
before anything is said to anyone. A proxy that ranks 18 items is allowed to be a filter; it is not
allowed to be the reason a stranger gets a comment.

CONTROLS, because a screen that finds nothing and a screen that cannot find anything look identical:
  * the RAM regex must fire on the two known-RAM issues (37 and 10 hits) -- if it reads 0 there, the
    fetch is broken rather than the corpus clean;
  * the agent regex must fire on the two known-ours issues (memex#233, AutoGPT#13458);
  * every lead must return a live state from the API; a fetch failure is reported, never counted as 0.

Run:  python probes/the_scout_fit_score_does_not_rank_relevance.py
"""
from __future__ import annotations
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LEADS = os.path.join(os.path.dirname(HERE), "agora_output", "_scout_leads.json")

RAM = re.compile(r"\b(heap|OOM|out of memory|memory leak|allocat\w*|garbage.collect|RSS|"
                 r"PartitionAlloc|malloc)\b", re.I)
AGENT = re.compile(r"\b(agent memory|persistent memory|memory (?:backend|conflict|system|layer|store)|"
                   r"context window|recall|retriev\w+|embedding|vector store|supersede\w*|"
                   r"conflict (?:detection|resolution)|forget\w*|knowledge graph|\bRAG\b)\b", re.I)

CONTROL_RAM = {"openclaw/openclaw#115424", "openai/codex#31793"}
CONTROL_OURS = {"JasperHG90/memex#233", "Significant-Gravitas/AutoGPT#13458"}


def issue_text(slug):
    owner_repo, num = slug.split("#")
    r = subprocess.run(["gh", "api", "repos/%s/issues/%s" % (owner_repo, num),
                        "--jq", '.title + " " + (.body // "")'],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError("fetch failed for %s: %s" % (slug, (r.stderr or "")[-120:]))
    return (r.stdout or "")[:8000]


def spearman(a, b):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        out = [0] * len(v)
        for pos, i in enumerate(order):
            out[i] = pos
        return out
    ra, rb = rank(a), rank(b)
    n = len(a)
    d2 = sum((x - y) ** 2 for x, y in zip(ra, rb))
    return 1 - 6 * d2 / (n * (n * n - 1))


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    leads = json.load(open(LEADS, encoding="utf-8"))
    rows = []
    for fit, task, slug, url, state, title in leads:
        body = issue_text(slug)
        rows.append({"slug": slug, "fit": fit, "task": task, "state": state,
                     "ram": len(RAM.findall(body)), "agent": len(AGENT.findall(body)),
                     "title": " ".join(title.split())[:70]})

    bad = []
    for r in rows:
        if r["slug"] in CONTROL_RAM and r["ram"] < 5:
            bad.append("control: %s reads RAM=%d, the fetch is broken" % (r["slug"], r["ram"]))
        if r["slug"] in CONTROL_OURS and r["agent"] < 3:
            bad.append("control: %s reads agent=%d, the screen cannot find its own case"
                       % (r["slug"], r["agent"]))
    if bad:
        for b in bad:
            print("FAIL " + b)
        return 1
    print("controls PASS: both RAM cases fire, both ours-cases fire\n")

    rho = spearman([r["fit"] for r in rows], [r["agent"] for r in rows])
    print("%-36s %-7s %4s %6s  %s" % ("repo#issue", "state", "RAM", "agent", "fit"))
    for r in sorted(rows, key=lambda r: -r["agent"]):
        print("%-36s %-7s %4d %6d  %3d  %s" % (r["slug"], r["state"], r["ram"], r["agent"],
                                               r["fit"], r["title"][:44]))
    print("\nSpearman(fit, agent-memory density) = %.3f   n=%d" % (rho, len(rows)))
    top_fit = max(rows, key=lambda r: r["fit"])
    top_rel = max(rows, key=lambda r: r["agent"])
    print("scout's top fit  : %s (fit %d, agent %d)" % (top_fit["slug"], top_fit["fit"], top_fit["agent"]))
    print("most on-axis     : %s (fit %d, agent %d)" % (top_rel["slug"], top_rel["fit"], top_rel["agent"]))
    ram_high = [r for r in rows if r["ram"] > r["agent"] and r["fit"] >= 10]
    print("leads scored >=10 that mean RAM: %d of %d" % (len(ram_high), len(rows)))

    out = os.path.join(HERE, "the_scout_fit_score_does_not_rank_relevance.result.json")
    json.dump({"spearman_fit_vs_relevance": round(rho, 4), "n": len(rows),
               "top_fit": top_fit["slug"], "most_on_axis": top_rel["slug"],
               "ram_sense_scored_10_plus": [r["slug"] for r in ram_high], "rows": rows},
              open(out, "w", encoding="utf-8"), indent=1)
    print("receipt -> " + out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
