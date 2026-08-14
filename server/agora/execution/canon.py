"""
The Canon — one living book of what Agora currently believes.

Artifacts pile up (insights, hypotheses, dialectics, dossiers, papers, worldviews) and the
owner needs ONE place that holds the current best understanding. The Canon is a single vault
document that Claude MERGES (never appends) whenever enough new artifacts have landed: each
belief gets one paragraph with its status and links, organized by domain cluster. The
worldview note is a snapshot; the Canon is the textbook that keeps being rewritten — and its
history lives in git.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

_CANON_REL = "04 Resources/Concepts/Agora Agents/Canon — What Agora Currently Believes.md"
#: Note types that state a CLAIM, and are therefore candidates for the statement of belief.
#:
#: MEASURED 2026-08-01, and this is the number that matters: the old tuple matched 103 of the 3,917
#: notes in the agent directory -- 2.6% -- leaving 3,814 invisible to the curator, of which 3,082 are
#: GROUNDED and 321 of those landed in the last 30 days. Sage Mira's honest "nothing new landed" was
#: true only of a 2.6% slice: the intake was aimed at a naming convention the swarm had stopped using.
#: The types it missed are not marginal. `measured-*` is 224 notes and 224 of them are grounded;
#: `pipeline-*` is 939 with 836 grounded and its own header reads "Evidence grade: HIGH -- measured
#: result with a citation/falsifier"; `create-*` is 311 and opens "**Finding:** Vessel et al. (2012)".
#:
#: Widening is NOT the same as taking everything. The Canon is a statement of belief with a 7,000-char
#: budget, so operational note types are excluded by name below -- a digest is a LIST of other notes,
#: not a belief about the world, and admitting 462 of them would bury the curator in its own logs.
_ARTIFACT_GLOBS = ("insight*.md", "hypothesis*.md", "dialectic*.md", "dossier*.md",
                   "paper*.md", "post-mortem*.md",
                   "measured*.md", "pipeline*.md", "create*.md",
                   "lab-*.md", "bridge-*.md", "analogy-*.md", "finding*.md", "replication*.md")

#: Operational records that a glob above would otherwise sweep in. Checked against the stem, so a
#: `pipeline*` glob cannot drag in `pipeline-digest-...` by accident.
_ARTIFACT_EXCLUDE = ("vault-digest", "scout-fit", "digest-", "-digest-", "telegram-", "inbox-",
                     "session-", "handoff-", "backup-", "index-")


def canon_path(vault_path: str) -> Path:
    return Path(vault_path) / _CANON_REL


def read_canon(vault_path: str) -> str:
    p = canon_path(vault_path)
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def write_canon(vault_path: str, content: str, force: bool = False) -> str | dict:
    """Replace the Canon wholesale (Claude supplies the merged text). Stamps updated:.

    A SHRINK BOUND guards it, because the only check was `len(content) < 200` at the endpoint — an
    absolute constant never compared against the document it replaces. It cannot tell a complete
    ~7,000-character merge from a model that emitted the header and the first cluster and stopped.
    Empty is caught by the 200 floor; truncated-at-500 is not, and truncated is the likelier of the
    two (CLAUDE.md records this deployment's reasoning tier returning success-shaped partial
    content under a tight cap). A 500-character reply would have replaced ~93% of the accumulated
    Canon — and the stamp below writes a fresh `updated:`, so the next intake would not re-offer
    what had just been lost.

    The organ path is separately protected by a Lab gate. The exposed path is Claude working the
    "merge into Canon" inbox task, where this is the whole defence.
    """
    p = canon_path(vault_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        prev = p.read_text(encoding="utf-8") if p.exists() else ""
    except Exception:
        prev = ""
    if prev and not force and len(content) < 0.6 * len(prev):
        return {"error": "refused: the merge is %d chars against an existing %d (%.0f%%). A Canon "
                         "merge does not shrink by a third unless the model stopped early. Pass "
                         "force=true if the shrink is deliberate."
                         % (len(content), len(prev), 100.0 * len(content) / len(prev))}
    if prev:
        # Keep the outgoing version beside the file. Recovery should not depend on a push having
        # happened: safe_vault_push sees a truncated Canon as an ordinary modification, so the
        # 0-deletion guard passes and only git log would hold the good text.
        try:
            p.with_suffix(p.suffix + ".prev").write_text(prev, encoding="utf-8")
        except Exception:
            pass
    today = time.strftime("%Y-%m-%d %H:%M")
    if not content.lstrip().startswith("---"):
        content = (f"---\ntitle: Canon — What Agora Currently Believes\n"
                   f"tags: [agora, canon, claude-synthesis]\nupdated: {today}\n---\n\n" + content)
    elif re.search(r"^updated:", content[:600], re.M):
        content = re.sub(r"^updated:.*$", f"updated: {today}", content, count=1, flags=re.M)
    else:
        content = re.sub(r"^---\s*$", f"---\nupdated: {today}", content, count=1, flags=re.M)
    p.write_text(content, encoding="utf-8")
    return str(p)


def _canon_updated_ts(vault_path: str) -> float:
    """Start of the day the Canon was last updated.

    A SAME-DAY DEAD ZONE, measured 2026-08-01. This returned 23:59 of the update date while an
    artifact's `created:` line is stamped at 12:00 of its own date, so `ts > cutoff` was False for
    every artifact produced on the day the Canon was merged -- and stayed False forever, because both
    timestamps are frozen to fixed times of day rather than to the moment anything happened. That is
    not "not yet eligible", it is permanently invisible, and it targets precisely the artifacts whose
    arrival triggered the merge in the first place.

    Measured on the live vault: `insight-grounding-breaks-the-wall-aggregation-cannot.md`, created
    2026-07-31, excluded by a Canon updated 2026-07-31. The daily artifact supply is 1-3, so a
    dead zone one day wide eats a meaningful share of the swarm's output, and Sage Mira reported an
    honest "nothing new landed" while it sat there.

    Re-offering an already-merged artifact is safe: the plan's admit branch measures containment
    against the standing bullets and routes a restatement to `judgment`, never back to `admit`.
    """
    text = read_canon(vault_path)
    m = re.search(r"^updated:\s*(\d{4})-(\d{2})-(\d{2})", text[:600], re.M)
    if not m:
        return 0.0
    return time.mktime((int(m.group(1)), int(m.group(2)), int(m.group(3)), 0, 0, 0, 0, 0, -1))


#: The headings our own agents actually write. This was `The insight|Hypothesis|Answer` and nothing
#: else, so a note headed "## The finding" -- the Theory Engine's own wording -- yielded an EMPTY core
#: and was then graded ungrounded on its title alone. Same one-surface-form failure the falsifier
#: detector already made ("falsifier" is not a substring of "falsification"), one file over.
_CORE_HEADINGS = re.compile(
    r"^#{1,3}\s*(?:the\s+)?(insight|finding|result|answer|hypothesis|claim|conclusion|thesis)\b[^\n]*\n"
    r"(.+?)(?=\n#{1,3}\s|\Z)", re.DOTALL | re.IGNORECASE | re.MULTILINE)

#: A Lab id or a structured MEASURED:/VERDICT: line. The colon and the case are load-bearing: a first
#: cut accepted a bare case-insensitive "measured" and immediately matched "fully-measured thesis" in
#: a note carrying no receipt at all, which would have promoted an ungrounded artifact to grounded.
#: A receipt detector that accepts prose ABOUT being measured is worse than none, because it turns
#: the gate into decoration while still reporting that it ran.
_RECEIPT_OWN = re.compile(
    r"^.{0,200}?(?:\b[Ll]ab\s+[0-9a-f]{6}\b|(?:^|\s)MEASURED:|(?:^|\s)VERDICT:).{0,200}$",
    re.MULTILINE)


def _core_of(text: str) -> str:
    """The note's substance: its finding section, or the first real paragraph as a fallback."""
    m = _CORE_HEADINGS.search(text or "")
    if m:
        return re.sub(r"\s+", " ", m.group(2)).strip()[:500]
    # No recognised heading is not the same as no content. Take the first substantive paragraph
    # rather than handing the grader a bare title and letting it conclude "no receipt".
    for para in (text or "").split("\n\n"):
        t = re.sub(r"\s+", " ", re.sub(r"^---.*?---", "", para, flags=re.DOTALL)).strip()
        if len(t) > 80 and not t.startswith(("#", "|", ">", "created:", "title:")):
            return t[:500]
    return ""


def _receipt_line(text: str) -> str:
    """The strongest receipt anywhere in the note: our own Lab/MEASURED line, else a real citation.

    CITATIONS COME FROM THE SHARED DETECTOR, not from a regex written here. `grounding.py` exists
    precisely because two copies of this idea were mirror images -- one demanded the author INSIDE
    the parentheses, the other OUTSIDE, and each rejected what the other accepted. A third private
    copy repeated the bug within minutes of being written: it missed "Watts (2002)" and happily
    accepted "(January 2026)" as a source. Author-year matching is not a thing to re-derive.
    """
    m = _RECEIPT_OWN.search(text or "")
    if m:
        return re.sub(r"\s+", " ", m.group(0)).strip()[:300]
    try:
        from agora.execution.grounding import citation
        return (citation(text or "") or "")[:300]
    except Exception:
        return ""


def new_artifacts_since_canon(vault_path: str) -> list[dict]:
    """Artifacts created after the Canon's last update (by frontmatter created:, mtime fallback)."""
    root = Path(vault_path) / "04 Resources/Concepts/Agora Agents"
    cutoff = _canon_updated_ts(vault_path)
    out = []
    if not root.is_dir():
        return out
    seen: set = set()
    for pattern in _ARTIFACT_GLOBS:
        for p in root.rglob(pattern):
            if p in seen:                     # the widened globs overlap; a note is one candidate
                continue
            seen.add(p)
            stem = p.stem.lower()
            if any(x in stem for x in _ARTIFACT_EXCLUDE):
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            m = re.search(r"^created:\s*(\d{4})-(\d{2})-(\d{2})", text[:800], re.M)
            ts = (time.mktime((int(m.group(1)), int(m.group(2)), int(m.group(3)), 12, 0, 0, 0, 0, -1))
                  if m else p.stat().st_mtime)
            if ts > cutoff:
                tm = re.search(r"^title:\s*(.+)$", text[:600], re.M)
                core = _core_of(text)
                # THE RECEIPT MAY NOT LIVE IN THE CORE SECTION. The consumer grades this artifact by
                # running its grounding test over `title + core`, so a Lab id sitting under "## The
                # test" or "## Status" was invisible and a fully grounded note read as having no
                # receipt at all. Carry the strongest receipt line found ANYWHERE in the note.
                out.append({"title": (tm.group(1).strip().strip('"') if tm else p.stem),
                            "kind": p.name.split("-")[0], "core": core,
                            "receipt_line": _receipt_line(text)})
    return out


def gather_canon_inputs(vault_path: str) -> dict:
    """Everything Claude needs to rewrite the Canon: its current text + the new artifacts."""
    return {"canon": read_canon(vault_path)[:9000],
            "new_artifacts": new_artifacts_since_canon(vault_path)[:14]}


# ── the canon ruling ledger ──────────────────────────────────────────────────────────────────────
#
# THE CURATOR'S DECISIONS LEFT NO MACHINE-READABLE TRACE. Every other organ writes its verdicts to a
# store -- Rooke to `.replications.json`, Voss to `.bounty.json`, Kael to `.scout_box.json` -- and
# the Canon, the organ CLAUDE.md calls Sage Mira's primary, wrote nowhere. A ruling that eight
# artifacts were held out for lack of a receipt, or that the statement of belief is at capacity and
# owes a written merge, existed only as prose in a discovery row.
#
# That is the same shape as the two schema gaps fixed earlier today, one step further: the bounty
# record kept its verdict and dropped the EVIDENCE, the replication record kept its verdict and
# dropped the ACTOR, and this one had no record at all. A curation decision nobody can query is a
# decision that did not happen, as far as every instrument in this repo is concerned.

_RULING_STORE = Path(__file__).resolve().parents[2] / ".canon.json"

#: Sage Mira's own declared vocabulary (organs/scholar.py ORGAN["decisive"]), not a new one.
_RULING_VERDICTS = ("merged", "rejected", "retired")


def _load_rulings() -> list:
    try:
        return json.loads(_RULING_STORE.read_text(encoding="utf-8"))
    except Exception:
        return []


def record_ruling(verdict: str, summary: str, by_agent: str = "Sage Mira",
                  evidence: str = "", held_out: int = 0, escalated: int = 0) -> dict | None:
    """Ledger one canon curation decision. verdict: merged | rejected | retired.

    `evidence` carries the Lab receipt, for the same reason `record_challenge` does: a ruling that
    cannot say what backed it is indistinguishable from one that was never grounded, and the
    acceptance gate asks for exactly that.
    """
    v = (verdict or "").strip().lower()
    if v not in _RULING_VERDICTS or len((summary or "").strip()) < 10:
        return None
    rec = {"verdict": v, "summary": (summary or "").strip()[:300],
           "by": (by_agent or "Sage Mira")[:40], "evidence": (evidence or "")[:300],
           "held_out": int(held_out or 0), "escalated": int(escalated or 0),
           "ts": time.time()}
    items = _load_rulings()
    items.append(rec)
    try:
        _RULING_STORE.write_text(json.dumps(items[-200:], ensure_ascii=False, indent=1),
                                 encoding="utf-8")
    except Exception:
        return None
    return rec
