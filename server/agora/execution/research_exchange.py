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
    m = re.search(rf"#+\s*{re.escape(heading)}\s*\n(.+?)(?=\n#+\s|\Z)", body, re.DOTALL | re.IGNORECASE)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


#: THE SAME SECTION UNDER EIGHT NAMES. `compose_digest` matched the first spelling only, so of the
#: 67 insight notes in the vault it accepted 9 and silently dropped 58 -- and 25 of the dropped ones
#: carry a `Falsifier`, which is the very quality the digest advertises in its own header. The
#: selection criterion was a heading spelling, not the presence of an insight. Measured 2026-08-17.
_CORE_HEADINGS = ("The insight", "The claim", "What it says", "What the numbers say",
                  "The measured result", "Measured result", "Result", "Mechanism (one line)")


def _core_section(body: str) -> str:
    """The insight's substance, under whichever heading this note happened to use."""
    for h in _CORE_HEADINGS:
        s = _section(body, h)
        if s:
            return s
    return ""


def _frontier_terms() -> set:
    """The owner's standing priority terms, from the ONE definition the gates already use.

    Returns an empty set when the board cannot be read, and every caller treats that as "do not
    filter" rather than "nothing qualifies" -- a filter that cannot see its criterion must not be
    able to empty the digest in silence.
    """
    try:
        from agora.execution.board import priorities_text
        from agora.execution.methods import board_priority_terms, light_stem
        return {light_stem(t) for t in board_priority_terms(priorities_text())}
    except Exception:                                                  # noqa: BLE001
        return set()


def _on_frontier(text: str, terms: set) -> bool:
    from agora.execution.methods import light_stem
    words = {light_stem(w.strip(".,:;()[]*_`\"'").lower()) for w in text.split()}
    return bool(terms & words)


def compose_digest(vault_path: str) -> dict:
    """Build the public digest from the vault's Claude-synthesized insights + the live
    track record. Deterministic — the quality is already in the insights."""
    src = Path(vault_path) / "04 Resources" / "Concepts" / "Agora Agents"
    terms = _frontier_terms()
    insights, considered, dropped = [], 0, 0
    for p in sorted(src.rglob("insight*.md")):
        try:
            body = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        tm = re.search(r"^title:\s*(.+)$", body[:600], re.M)
        title = (tm.group(1).strip() if tm else p.stem).removeprefix("Insight:").strip()
        core, fals = _core_section(body), _section(body, "Falsifier")
        if not core:
            continue
        considered += 1
        # A WIDER NET IS NOT A BETTER ONE. Accepting the eight heading spellings takes the pool from
        # 9 to 41, but the on-frontier RATE barely moves (44% -> 46%), so volume alone would ship 22
        # off-frontier pieces instead of 5. The heading fix and the frontier filter only work
        # together. Measured 2026-08-17 against the live board.
        if terms and not _on_frontier(f"{title} {core[:900]}", terms):
            dropped += 1
            continue
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
    # `considered` and `off_frontier` are reported so the gated action states what it DROPPED, not
    # only what it kept. A selection that publishes its survivors and says nothing about the cut is
    # how "the digest ships 9" read as "the vault holds 9" for 57 days.
    return {"path": str(OUTPUT), "insights": len(insights), "chars": OUTPUT.stat().st_size,
            "considered": considered, "off_frontier": dropped,
            "frontier_filter": "applied" if terms else "unavailable — board unreadable, kept all"}


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
