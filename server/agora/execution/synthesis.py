"""
THE SYNTHESIS ORGAN — turn the pile of rigorous findings into a BODY OF WORK.

Crucible (replications), the analogy forge, and the theory ledger each accumulate individually-
rigorous, measured findings — but in parallel silos. Their value is more than the sum: many of them
share a deep skeleton (a naive statistic is wrong because of a structural feature the textbook
ignores — selection, finite-sample, a heavy multiplicative tail, correlation). This organ reads the
WHOLE rigorous corpus and asks the smart model for ONE unifying mechanism-thesis that subsumes >=3
findings, with the findings it rests on and a falsifier — or an honest "no thesis yet" (a real
non-event). Claude then verifies/develops the candidate into public work (a flagship piece).

Read-only over the existing ledgers (.replications/.analogies/.theory.json); additive; the only
state it writes is its own proposal ledger (.synthesis.json). It cannot break the running system.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_REPS = _ROOT / ".replications.json"
_ANALOGIES = _ROOT / ".analogies.json"
_THEORY = _ROOT / ".theory.json"
_STORE = _ROOT / ".synthesis.json"


def _load(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def gather_findings() -> list[dict]:
    """The rigorous corpus, normalized to {kind, label, finding}. High-signal only:
    replications with a measured note, viable analogies, theory verdicts."""
    out = []
    for r in _load(_REPS, []):
        note = (r.get("note") or "").strip()
        if r.get("outcome") in ("REPRODUCED", "FAILED") and len(note) > 30:
            out.append({"kind": "replication", "label": (r.get("claim") or "")[:70],
                        "finding": f"[{r.get('outcome')}] {note}"[:360]})
    for a in _load(_ANALOGIES, []):
        if "no " not in (a.get("outcome") or "").lower() and len((a.get("note") or "")) > 30:
            out.append({"kind": "analogy", "label": f"{a.get('mechanism')} -> {a.get('target')}",
                        "finding": (a.get("note") or "")[:360]})
    for t in _load(_THEORY, []):
        if (t.get("summary") or "").strip():
            out.append({"kind": "theory", "label": (t.get("title") or "")[:70],
                        "finding": f"[{t.get('verdict')}] {t.get('summary')}"[:360]})
    return out


def _store_proposal(p: dict) -> None:
    items = _load(_STORE, [])
    items.append(p)
    try:
        _STORE.write_text(json.dumps(items[-50:], ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def synthesis_inputs(min_findings: int = 8) -> dict:
    """The rigorous corpus, packaged for CLAUDE to synthesize. Cross-finding synthesis is the
    hardest reasoning in the system — it belongs to Claude (the smart model driving the loop), not
    a cheap/medium JSON call (which also returns empty on a task this hard). The organ's job is to
    GATHER + TRIGGER; Claude produces the thesis and writes it back via record_thesis()."""
    findings = gather_findings()
    if len(findings) < min_findings:
        return {"status": "too_few", "have": len(findings), "need": min_findings}
    corpus = "\n".join(f"- ({f['kind']}) {f['label']}: {f['finding']}" for f in findings)
    return {"status": "ok", "n_findings": len(findings), "corpus": corpus, "findings": findings}


def queue_synthesis(min_findings: int = 8) -> dict:
    """File a grand-synthesis task into Claude's inbox with the rigorous corpus attached."""
    inp = synthesis_inputs(min_findings)
    if inp["status"] != "ok":
        return inp
    from agora.execution.claude_inbox import add_task
    tid = add_task(
        "Attempt grand synthesis over the Crucible corpus: across our MEASURED findings below, "
        "find ONE non-obvious unifying MECHANISM that genuinely subsumes >=3 (the same structural "
        "skeleton across domains, not a topic label). Ship it as a flagship thesis note (tags "
        "['agora','synthesis','thesis','claude-synthesis']) with the findings it rests on + a "
        "falsifier, then POST /brain/crucible-synthesis/record. If nothing honestly unifies >=3, "
        "record honest=false (a measured non-event).\n\nCORPUS:\n" + inp["corpus"][:4000])
    return {"status": "queued", "task": tid, "n_findings": inp["n_findings"]}


_AUDIT_STOP = set((
    "the a an of to in on for and or is are was were be been being that this these those it its as by "
    "at from with which who what when where why how not no than then so such into over under more most "
    "less can could should would will may might because therefore thus hence also both each every any "
    "we our they their system across between one two via using use makes make").split())


def _atoks(s: str) -> set:
    return {w for w in re.findall(r"[a-z][a-z\-]{3,}", (s or "").lower()) if w not in _AUDIT_STOP}


def interpreter_audit(thesis: str, rests_on: list, threshold: float = 0.12) -> dict:
    """Gazzaniga's interpreter check (Breaktruth #24 / direction #5). A synthesized thesis is a story
    the 'interpreter' stitches over the findings — so audit that each ASSERTION actually traces to a
    finding it rests_on, and flag the ones that don't as CONFABULATION. Lexical, no LLM: each
    assertion's content-token overlap with the union of the rests_on text. Advisory — it flags, it
    does not block (silent suppression would be its own confabulation)."""
    support_text = []
    for x in (rests_on or []):
        if isinstance(x, dict):
            support_text.append(str(x.get("text") or x.get("claim") or x.get("title")
                                    or x.get("finding") or x.get("note") or ""))
        else:
            support_text.append(str(x))
    support_toks: set = set().union(*[_atoks(t) for t in support_text]) if support_text else set()
    assertions = []
    for s in re.split(r"(?<=[.!?])\s+", (thesis or "")):
        s = s.strip()
        if len(s) < 25:
            continue
        at = _atoks(s)
        if not at:
            continue
        overlap = len(at & support_toks) / len(at)
        assertions.append({"assertion": s[:160], "support": round(overlap, 3),
                           "grounded": overlap >= threshold})
    n = len(assertions)
    grounded = sum(1 for a in assertions if a["grounded"])
    ratio = round(grounded / n, 3) if n else 1.0
    verdict = ("grounded" if ratio >= 0.6 else
               "partly_confabulated" if ratio >= 0.3 else "largely_confabulated")
    return {"provenance_ratio": ratio, "n_assertions": n, "grounded": grounded,
            "unsupported": [a["assertion"] for a in assertions if not a["grounded"]],
            "verdict": verdict}


def record_thesis(thesis: str, rests_on: list, why: str = "", falsifier: str = "",
                  honest: bool = True, note_path: str = "") -> dict:
    """Claude writes the synthesized thesis back to the organ's ledger."""
    audit = interpreter_audit(thesis, rests_on or [])
    rec = {"ts": time.time(), "thesis": (thesis or "")[:600], "rests_on": rests_on or [],
           "why": (why or "")[:800], "falsifier": (falsifier or "")[:500],
           "note_path": note_path[:300], "honest": bool(honest) and len((thesis or "").strip()) > 20,
           "audit": audit}
    _store_proposal(rec)
    return {"status": "ok", **rec}


def format_synthesis() -> str:
    items = _load(_STORE, [])
    if not items:
        return "🧭 _The Synthesis organ has proposed no thesis yet._"
    last = items[-1]
    if not last.get("honest"):
        return "🧭 *Synthesis* — no honest unifying thesis at the last pass (a measured non-event)."
    lines = ["🧭 *Synthesis — candidate unifying thesis*", f"_{last['thesis']}_",
             f"rests on: {', '.join(last.get('rests_on', [])[:4])}"]
    if last.get("falsifier"):
        lines.append(f"falsifier: {last['falsifier'][:160]}")
    return "\n".join(lines)
