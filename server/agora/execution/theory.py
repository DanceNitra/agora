"""
The Theory Engine — beliefs that run.

Until now a belief was prose with a falsifier. The Theory Engine makes the mechanistic ones
EXECUTABLE: Claude builds a small formal model of the claim (simulation, urn process,
bifurcation normal form...), runs it in the Lab, and the belief is stamped by what the model
does — corroborated (the mechanism produces the claimed behavior), strained (it does only
under conditions the prose didn't state), or unmodelable. A strained belief goes to the
challenge pipeline. The vault stops being a library and becomes a laboratory.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".theory.json"


def _load() -> list:
    try:
        return json.loads(_STORE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(items: list) -> None:
    try:
        _STORE.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def pick_target(vault_path: str) -> dict | None:
    """The next mechanistic belief without a theory run: must carry a Mechanism-like section
    (a simulable hint), prefer never-modeled, oldest first."""
    from agora.execution.belief_revision import list_beliefs
    done = {t.get("title") for t in _load()}
    cands = []
    for b in list_beliefs(vault_path):
        if b["belief_status"] not in ("active", "survived") or b["title"] in done:
            continue
        try:
            text = Path(b["path"]).read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if re.search(r"##\s*(Mechanism|How the groundings combine)", text, re.I):
            cands.append(b)
    if not cands:
        return None
    cands.sort(key=lambda b: Path(b["path"]).stat().st_mtime)
    return cands[0]


def record_run(title: str, path: str, verdict: str, lab_name: str, summary: str) -> dict:
    """Ledger the theory run and stamp the belief note (theory_status + date)."""
    v = (verdict or "").strip().lower()
    if v not in ("corroborated", "strained", "unmodelable"):
        return {"error": f"unknown verdict '{verdict}'"}
    rec = {"title": title[:160], "verdict": v, "lab": (lab_name or "")[:80],
           "summary": (summary or "")[:400], "ts": time.time()}
    items = _load()
    items.append(rec)
    _save(items[-100:])
    p = Path(path)
    if p.is_file():
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
            today = time.strftime("%Y-%m-%d")
            for key, val in (("theory_status", v), ("theory_date", today)):
                if re.search(rf"^{key}:", text[:1500], re.M):
                    text = re.sub(rf"^{key}:.*$", f"{key}: {val}", text, count=1, flags=re.M)
                else:
                    text = re.sub(r"^---\s*$", f"---\n{key}: {val}", text, count=1, flags=re.M)
            p.write_text(text, encoding="utf-8")
        except Exception:
            pass
    return {"status": "ok", **rec}


def format_theory() -> str:
    items = _load()
    if not items:
        return "⚙️ _No beliefs have been run as models yet._"
    icon = {"corroborated": "✅", "strained": "⚠️", "unmodelable": "⬜"}
    lines = [f"⚙️ *Theory Engine* — {len(items)} beliefs run as models"]
    for t in items[-8:]:
        lines.append(f"{icon.get(t['verdict'], '•')} {t['title'][:58]} — *{t['verdict']}*")
        if t.get("summary"):
            lines.append(f"   _{t['summary'][:90]}_")
    return "\n".join(lines)
