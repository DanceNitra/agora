"""
The Board Meeting — the owner steers the whole organism, deliberately.

Strategic input has been ad-hoc chat. Weekly, Agora prepares an agenda — vitals trend, what
shipped, the decisions waiting on the owner, and PROPOSED priorities — and sends it to
Telegram. The owner replies with a few lines (`board <directives>`), and those words become
STANDING PRIORITIES injected into every heavy synthesis (worldview, insights, predictions),
so Claude reads the owner's strategy next to the evidence. Commands steer actions; the board
steers direction.
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".board.json"


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


async def prepare_agenda(db) -> dict:
    """Assemble the meeting: vitals delta, the week's output, open decisions, proposed focus."""
    from agora.execution.observatory import series
    from agora.execution.hands import pending_approvals
    from agora.execution.interview import open_question
    from agora.execution.forge import _load as forge_load
    from agora.execution.flywheel import stats as fw_stats
    from agora.execution.campaigns import list_campaigns

    vit = series(2)
    open_decisions = []
    open_decisions += [f"approve/reject `{a['id']}`: {a['title'][:50]}" for a in pending_approvals()]
    oq = open_question()
    if oq:
        open_decisions.append(f"answer the open interview question: {oq['question'][:60]}")
    open_gaps = [g for g in forge_load() if g.get("status") == "open"]

    proposed = []
    running = [c for c in list_campaigns() if c.get("status") == "running"]
    if not running:
        proposed.append("start one research campaign on a question you actually care about")
    fw = fw_stats()
    if fw.get("open", 0) > 6:
        proposed.append(f"focus the agents on closing flywheel questions ({fw['open']} open)")
    if open_gaps:
        proposed.append(f"greenlight a Forge build ({len(open_gaps)} capability gaps registered)")
    proposed.append("name the single domain that matters most to you in the coming week")

    agenda = {"id": uuid.uuid4().hex[:6], "ts": time.time(),
              "vitals_now": vit[-1] if vit else {}, "vitals_prev": vit[-2] if len(vit) > 1 else {},
              "open_decisions": open_decisions[:6], "proposed": proposed[:5],
              "directives": "", "status": "sent"}
    items = _load()
    items.append(agenda)
    _save(items[-40:])
    return agenda


def record_directives(text: str) -> dict | None:
    """The owner's reply becomes the standing priorities (until the next board)."""
    items = _load()
    for a in reversed(items):
        if a.get("status") == "sent":
            a["directives"] = (text or "").strip()[:800]
            a["status"] = "decided"
            a["decided_ts"] = time.time()
            _save(items)
            return a
    # no open agenda — record a free-standing directive set
    rec = {"id": uuid.uuid4().hex[:6], "ts": time.time(), "open_decisions": [],
           "proposed": [], "directives": (text or "").strip()[:800],
           "status": "decided", "decided_ts": time.time()}
    items.append(rec)
    _save(items[-40:])
    return rec


def priorities_text() -> str:
    """The owner's current standing priorities — injected into heavy synthesis inputs."""
    for a in reversed(_load()):
        if a.get("directives"):
            age_d = (time.time() - a.get("decided_ts", a["ts"])) / 86400
            return (f"OWNER'S STANDING PRIORITIES ({age_d:.0f}d old): {a['directives']}")
    return ""


def format_agenda(a: dict) -> str:
    v, p = a.get("vitals_now", {}), a.get("vitals_prev", {})
    lines = ["🏛 *Board meeting* — the week, and what needs you"]
    if v:
        lines.append(f"vitals: {v.get('vault_notes', '?')} notes · dead-weight "
                     f"{v.get('dead_weight_frac', 0):.1%} · flywheel {v.get('flywheel_open', '?')} open"
                     + (f" · exam {v['exam_frac']:.0%}" if v.get("exam_frac") is not None else ""))
    if a.get("open_decisions"):
        lines.append("*Waiting on you:*")
        lines += [f"  • {d}" for d in a["open_decisions"]]
    if a.get("proposed"):
        lines.append("*Proposed focus:*")
        lines += [f"  {i}. {p}" for i, p in enumerate(a["proposed"], 1)]
    lines.append("_reply:_ `board <your directives>` — they become standing priorities")
    return "\n".join(lines)


def format_board() -> str:
    """The last meeting's agenda, with "Waiting on you" RE-DERIVED at read time.

    MEASURED 2026-08-17. Three of the five decisions this endpoint listed had already been settled
    -- two rejected, one approved and executed -- and it still showed all five, because the stored
    agenda freezes `open_decisions` at the moment the meeting was prepared and this function
    replayed that snapshot. The last meeting was 1.9 days old and they run weekly, so the owner's
    steering surface can be a week behind the store it is supposed to describe, and he re-decides
    what he already decided.

    Vitals and the proposed focus stay frozen on purpose: those are honest claims ABOUT that
    meeting. "What needs you" is a claim about NOW, so it is recomputed from the same two sources
    `prepare_agenda` uses. A surface that reports a state it does not read is the defect this
    repository keeps paying for.
    """
    items = _load()
    if not items:
        return "🏛 _No board meetings yet._"
    last = dict(items[-1])                     # copy: never mutate the stored meeting
    from agora.execution.hands import pending_approvals
    from agora.execution.interview import open_question
    live = [f"approve/reject `{a['id']}`: {a['title'][:50]}" for a in pending_approvals()]
    oq = open_question()
    if oq:
        live.append(f"answer the open interview question: {oq['question'][:60]}")
    last["open_decisions"] = live
    txt = priorities_text()
    lines = [format_agenda(last)]
    if txt:
        lines.append(f"\n📌 {txt}")
    return "\n".join(lines)
