"""
The Laboratory — simulation as the third channel of evidence.

The system reads (literature) and watches (live data); now it COMPUTES. When a claim or a
falsifier needs numbers — a Monte Carlo, a decay curve, statistics over Agora's own ledgers —
Claude writes a small script and this runner executes it deterministically: in
agora_output/lab, with a hard timeout, stdout capped, results recorded to a ledger with
source "simulation". Scripts are written ONLY by Claude (who already maintains the codebase),
never by the flash model — the trust boundary stays exactly where it already was.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path

LAB_DIR = Path(__file__).resolve().parents[3] / "agora_output" / "lab"
_STORE = Path(__file__).resolve().parents[2] / ".lab.json"
_TIMEOUT = 60
_OUT_CAP = 10_000


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


def run_experiment(name: str, code: str) -> dict:
    """Persist + execute one experiment script; record the outcome in the lab ledger."""
    slug = re.sub(r"[^a-z0-9]+", "-", (name or "experiment").lower()).strip("-")[:50]
    eid = uuid.uuid4().hex[:6]
    LAB_DIR.mkdir(parents=True, exist_ok=True)
    path = LAB_DIR / f"{time.strftime('%Y%m%d-%H%M%S')}_{slug}.py"
    path.write_text(code, encoding="utf-8")
    t0 = time.time()
    try:
        r = subprocess.run([sys.executable, "-X", "utf8", str(path)],
                           cwd=str(LAB_DIR), capture_output=True, text=True,
                           timeout=_TIMEOUT, encoding="utf-8", errors="replace")
        ok = r.returncode == 0
        output = (r.stdout or "")[:_OUT_CAP] + (("\n[stderr] " + r.stderr[:1500]) if (not ok and r.stderr) else "")
    except subprocess.TimeoutExpired:
        ok, output = False, f"[timeout after {_TIMEOUT}s]"
    rec = {"id": eid, "name": (name or slug)[:120], "script": str(path),
           "ok": ok, "seconds": round(time.time() - t0, 1),
           "output": output.strip()[:_OUT_CAP], "source": "simulation", "ts": time.time()}
    items = _load()
    items.append(rec)
    _save(items[-100:])
    return rec


def recent(n: int = 10) -> list:
    return _load()[-n:]


def format_lab(n: int = 6) -> str:
    items = _load()[-n:]
    if not items:
        return "🧫 _The laboratory is dark — no experiments run yet._"
    lines = [f"🧫 *The Laboratory* — {len(_load())} experiments on record"]
    for x in reversed(items):
        head = (x["output"].splitlines() or [""])[0][:80]
        lines.append(f"{'✅' if x['ok'] else '❌'} {x['name'][:48]} _({x['seconds']}s)_")
        if head:
            lines.append(f"   `{head}`")
    return "\n".join(lines)
