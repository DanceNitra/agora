"""
The Annals — autobiographical memory.

The organism has an excellent NOW and measured trends, but no episodic past: nothing can
answer "what did you do yesterday?". The Annals compose a deterministic daily chronicle from
the system's real traces — repo commits, artifacts landed in the vault, predictions made and
resolved, exams graded, actions decided, interview exchanges — written as one idempotent
vault note per day. Weekly, Claude reads the last seven days and writes a narrative
retrospective. The system gains a life it can remember.
"""
from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path

_SERVER = Path(__file__).resolve().parents[2]
AGORA_REPO = _SERVER.parent


def _today_bounds(day: str = "") -> tuple[float, float, str]:
    day = day or time.strftime("%Y-%m-%d")
    t0 = time.mktime(time.strptime(day, "%Y-%m-%d"))
    return t0, t0 + 86400, day


def _commits(day: str) -> list[str]:
    try:
        r = subprocess.run(["git", "-C", str(AGORA_REPO), "log",
                            f"--since={day} 00:00", f"--until={day} 23:59",
                            "--pretty=%s"], capture_output=True, text=True, timeout=15)
        return [ln.strip()[:90] for ln in r.stdout.splitlines() if ln.strip()][:20]
    except Exception:
        return []


def _artifacts(vault_path: str, day: str) -> list[str]:
    root = Path(vault_path) / "04 Resources/Concepts/Agora Agents"
    out = []
    if not root.is_dir():
        return out
    for p in root.rglob("*.md"):
        try:
            head = p.read_text(encoding="utf-8", errors="replace")[:700]
        except Exception:
            continue
        if re.search(rf"^created:\s*{day}", head, re.M):
            m = re.search(r"^title:\s*(.+)$", head, re.M)
            out.append((m.group(1).strip().strip('"') if m else p.stem)[:90])
    return out[:25]


def _ledger_events(path: Path, t0: float, t1: float, ts_key: str = "ts") -> list[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    items = data if isinstance(data, list) else sum(
        (v if isinstance(v, list) else [] for v in data.values()), [])
    return [x for x in items if isinstance(x, dict) and t0 <= x.get(ts_key, 0) < t1]


def compose_day(vault_path: str, day: str = "") -> dict:
    """One day's chronicle from the system's real traces. Deterministic."""
    t0, t1, day = _today_bounds(day)
    preds = _ledger_events(_SERVER / ".predictions.json", t0, t1, "made_ts")
    resolved = _ledger_events(_SERVER / ".predictions.json", t0, t1, "resolved_ts")
    actions = _ledger_events(_SERVER / ".actions.json", t0, t1)
    exams = [e for e in _ledger_events(_SERVER / ".exams.json", t0, t1, "graded_ts")
             if e.get("score") is not None]
    interview = _ledger_events(_SERVER / ".interview.json", t0, t1)
    labs = _ledger_events(_SERVER / ".lab.json", t0, t1)
    return {"day": day,
            "commits": _commits(day),
            "artifacts": _artifacts(vault_path, day),
            "predictions_made": [p.get("theme", "")[:60] for p in preds],
            "predictions_resolved": [f"{p.get('theme', '')[:40]} → {p.get('status')}"
                                     for p in resolved],
            "actions": [f"{a.get('kind')}: {a.get('title', '')[:50]} [{a.get('status')}]"
                        for a in actions][:10],
            "exams": [f"{e['score']}/{e['max']}" for e in exams],
            "interview": [q.get("question", "")[:70] for q in interview],
            "experiments": [x.get("name", "")[:60] for x in labs]}


def chronicle_text(d: dict) -> str:
    """The day as a vault note body."""
    L = [f"> The system's own record of {d['day']} — composed from real traces, no narration.", ""]

    def sec(title, rows):
        if rows:
            L.append(f"## {title}")
            L.extend(f"- {r}" for r in rows)
            L.append("")
    sec(f"Shipped ({len(d['commits'])} commits)", d["commits"])
    sec("Artifacts landed in the vault", d["artifacts"])
    sec("Predictions made", d["predictions_made"])
    sec("Predictions resolved", d["predictions_resolved"])
    sec("Actions", d["actions"])
    sec("Exams graded", d["exams"])
    sec("Interview", d["interview"])
    sec("Lab experiments", d["experiments"])
    if len(L) == 2:
        L.append("_A quiet day — no traces recorded._")
    return "\n".join(L)


def format_annals(d: dict) -> str:
    """Telegram-sized day summary."""
    bits = []
    for key, label in (("commits", "commits"), ("artifacts", "artifacts"),
                       ("predictions_made", "predictions"), ("predictions_resolved", "resolved"),
                       ("exams", "exams"), ("experiments", "lab runs")):
        if d.get(key):
            bits.append(f"{len(d[key])} {label}")
    head = f"📜 *Annals {d['day']}*: " + (", ".join(bits) if bits else "a quiet day")
    tail = "\n".join(f"• {c}" for c in d.get("commits", [])[:6])
    return head + ("\n" + tail if tail else "")
