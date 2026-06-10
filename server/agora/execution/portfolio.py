"""
The Portfolio — Agora's public scientific track record.

The Press publishes claims; the Portfolio publishes the receipts. It composes one evolving public
page of *accountability*: prediction calibration (with Brier vs the 0.25 coin-flip baseline),
replication outcomes (how many published claims we re-ran, and how many failed), and beliefs
revised under challenge. Credibility is earned by exposure, not assertion — so the page also
refuses to publish while the record is too thin to be honest (a 100%-at-n=2 hit-rate is a
liability, not an asset). The self-gate is the credibility.
"""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

SERVER = Path(__file__).resolve().parents[2]
AGORA_REPO = Path(__file__).resolve().parents[3]
OUTPUT = SERVER.parent / "agora_output" / "track_record.md"
PUBLIC_REL = "public/track-record.md"
PUBLIC_URL = "https://github.com/DanceNitra/agora/blob/main/public/track-record.md"
_MIN_RESOLVED = 8          # don't publish a record thinner than this — honesty gate


def _j(name, default):
    try:
        return json.loads((SERVER / name).read_text(encoding="utf-8"))
    except Exception:
        return default


def record() -> dict:
    """The accountability numbers, all from real ledgers."""
    preds = _j(".predictions.json", [])
    done = [p for p in preds if p.get("status") in ("correct", "incorrect")]
    correct = sum(1 for p in done if p["status"] == "correct")
    # Brier: forecast the called direction at stated confidence; outcome 1 if correct
    brier = (sum((1 - p.get("confidence", 0.5)) ** 2 if p["status"] == "correct"
                 else p.get("confidence", 0.5) ** 2 for p in done) / len(done)) if done else None

    oracle = _j(".oracle.json", [])
    o_open = sum(1 for x in oracle if x.get("status") == "open")
    o_done = [x for x in oracle if x.get("status") in ("resolved", "correct", "incorrect")]

    reps = _j(".replications.json", [])
    rep = {o: sum(1 for r in reps if r.get("outcome") == o)
           for o in ("REPRODUCED", "FAILED", "NOT_COMPUTABLE")}
    bounty = _j(".bounty.json", [])
    kills = sum(1 for x in bounty if x.get("kill"))

    resolved_total = len(done) + len(o_done) + sum(rep.values())
    return {"pred_total": len(preds), "pred_resolved": len(done), "pred_correct": correct,
            "pred_hit_rate": (correct / len(done)) if done else None, "brier": brier,
            "oracle_open": o_open, "oracle_resolved": len(o_done),
            "replications": rep, "belief_kills": kills,
            "resolved_total": resolved_total, "credible": resolved_total >= _MIN_RESOLVED}


def compose() -> dict:
    """Write the public track-record markdown from the ledgers. Returns the record dict."""
    r = record()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    L = ["# Agora — Public Track Record",
         f"\n_{time.strftime('%Y-%m-%d')} · the receipts behind the claims. An autonomous research "
         "OS held to its own predictions, replications, and challenges._\n"]
    L.append("## Forecasting")
    if r["pred_resolved"]:
        hr = f"{r['pred_hit_rate']:.0%}" if r["pred_hit_rate"] is not None else "—"
        L.append(f"- {r['pred_correct']}/{r['pred_resolved']} resolved predictions correct ({hr})")
        if r["brier"] is not None:
            verdict = "better than" if r["brier"] < 0.25 else "no better than"
            L.append(f"- Brier score **{r['brier']:.3f}** ({verdict} a 0.25 coin-flip baseline)")
    else:
        L.append("- no predictions resolved yet")
    L.append(f"- {r['oracle_open']} open market calls, {r['oracle_resolved']} resolved")
    L.append("\n## Replication (re-running others' published claims)")
    rp = r["replications"]
    L.append(f"- {rp['REPRODUCED']} reproduced · **{rp['FAILED']} failed** · "
             f"{rp['NOT_COMPUTABLE']} not computable")
    L.append("\n## Self-challenge")
    L.append(f"- {r['belief_kills']} of our own beliefs revised or retired under challenge")
    L.append(f"\n_Total resolved accountability items: {r['resolved_total']}._")
    OUTPUT.write_text("\n".join(L), encoding="utf-8")
    return r


def publish() -> dict:
    """PUBLISH (only from an approved gated action): copy the composed record into the public
    repo, commit ONLY that file, push."""
    if not OUTPUT.is_file():
        compose()
    dst = AGORA_REPO / PUBLIC_REL
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(OUTPUT.read_text(encoding="utf-8"), encoding="utf-8")

    def _git(*a):
        return subprocess.run(["git", "-C", str(AGORA_REPO), *a],
                              capture_output=True, text=True, timeout=60)
    _git("add", PUBLIC_REL)
    c = _git("commit", "-m", f"Track Record: update {time.strftime('%Y-%m-%d')}")
    if "nothing to commit" in (c.stdout + c.stderr):
        return {"url": PUBLIC_URL, "note": "unchanged since last publish"}
    p = _git("push", "origin", "main")
    if p.returncode != 0:
        return {"error": ("push failed: " + (p.stderr or p.stdout))[:200]}
    return {"url": PUBLIC_URL}


def format_portfolio() -> str:
    r = record()
    gate = "✅ credible to publish" if r["credible"] \
        else f"🔒 too thin to publish ({r['resolved_total']}/{_MIN_RESOLVED} resolved items)"
    rp = r["replications"]
    hr = f"{r['pred_hit_rate']:.0%}" if r["pred_hit_rate"] is not None else "—"
    brier = f" · Brier {r['brier']:.3f}" if r.get("brier") is not None else ""
    return ("📊 *Public Track Record* — " + gate + "\n"
            f"• forecasts: {r['pred_correct']}/{r['pred_resolved']} ({hr}){brier} · "
            f"{r['oracle_open']} open calls\n"
            f"• replications: {rp['REPRODUCED']}✅ {rp['FAILED']}💥 {rp['NOT_COMPUTABLE']}⏭\n"
            f"• self-challenge: {r['belief_kills']} beliefs revised under fire")
