"""
The Research Exchange — Agora publishes (gated).

Outputs so far land only in the private vault. This composes Agora's best Claude-synthesized
insights into one polished public digest and — ONLY after Rasto approves the gated `publish`
action from Telegram — commits it to the public agora repo (`public/research_digest.md`), which
is a real public URL. Publication is the strongest falsifier source there is: external readers.
"""
from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path

AGORA_REPO = Path(__file__).resolve().parents[3]            # the public DanceNitra/agora repo
OUTPUT = AGORA_REPO / "agora_output" / "public_digest.md"
PUBLIC_REL = "public/research_digest.md"
PUBLIC_URL = f"https://github.com/DanceNitra/agora/blob/main/{PUBLIC_REL}"


def _strip_private(text: str) -> str:
    """De-vault the prose for public readers: resolve [[wikilinks]] to plain text."""
    return re.sub(r"\[\[([^\]|#]+)(?:\|([^\]]+))?\]\]", lambda m: m.group(2) or m.group(1), text)


def _section(body: str, heading: str) -> str:
    m = re.search(rf"##\s*{heading}\s*\n(.+?)(?=\n##\s|\Z)", body, re.DOTALL | re.IGNORECASE)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def compose_digest(vault_path: str) -> dict:
    """Build the public digest from the vault's Claude-synthesized insights + the live
    track record. Deterministic — the quality is already in the insights."""
    src = Path(vault_path) / "04 Resources" / "Concepts" / "Agora Agents"
    insights = []
    for p in sorted(src.rglob("insight*.md")):
        try:
            body = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        tm = re.search(r"^title:\s*(.+)$", body[:600], re.M)
        title = (tm.group(1).strip() if tm else p.stem).removeprefix("Insight:").strip()
        core, fals = _section(body, "The insight"), _section(body, "Falsifier")
        if core:
            insights.append({"title": title, "core": _strip_private(core)[:900],
                             "falsifier": _strip_private(fals)[:400]})
    try:
        from agora.execution.prediction_ledger import calibration
        cal = calibration()
    except Exception:
        cal = {}
    lines = [
        "# Agora — Public Research Digest",
        f"\n_{time.strftime('%Y-%m-%d')} · synthesized by an autonomous research OS "
        "(Agora gathers the evidence; Claude writes the synthesis; every claim ships "
        "with a falsifier)._\n",
    ]
    if cal.get("total"):
        hr = f"{cal['hit_rate']:.0%}" if cal.get("hit_rate") is not None else "pending"
        lines.append(f"**Accountability:** {cal['total']} live predictions on record, "
                     f"{cal.get('resolved', 0)} resolved, hit-rate {hr}.\n")
    for i, x in enumerate(insights, 1):
        lines += [f"\n## {i}. {x['title']}", f"\n{x['core']}"]
        if x["falsifier"]:
            lines.append(f"\n**How to prove this wrong:** {x['falsifier']}")
    lines.append("\n\n---\n_Every insight above integrates three groundings: a private "
                 "knowledge vault, the published literature, and live real-world data._")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    return {"path": str(OUTPUT), "insights": len(insights), "chars": OUTPUT.stat().st_size}


def publish_digest() -> dict:
    """PUBLISH (call only from an approved gated action): copy the composed digest into the
    public repo, commit ONLY that file, push. Returns the public URL."""
    if not OUTPUT.is_file():
        return {"error": "digest not composed"}
    dst = AGORA_REPO / PUBLIC_REL
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(OUTPUT.read_text(encoding="utf-8"), encoding="utf-8")

    def _git(*args):
        return subprocess.run(["git", "-C", str(AGORA_REPO), *args],
                              capture_output=True, text=True, timeout=60)
    from agora.execution.public_repo import commit_and_push
    r = commit_and_push(AGORA_REPO, [PUBLIC_REL],
                        f"Research Exchange: public digest {time.strftime('%Y-%m-%d')}")
    if r.get("error"):
        return {"error": r["error"]}
    if r.get("note"):
        return {"url": PUBLIC_URL, "note": r["note"]}
    return {"url": PUBLIC_URL, "sha": r["sha"]}
