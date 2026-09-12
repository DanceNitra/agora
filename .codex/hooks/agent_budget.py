"""No subagent launches until the owner has seen its cost and said yes. Wired, not remembered.

WHAT HAPPENED. 2026-09-02 I launched NINE subagents, about 1.6M tokens, and never once told the
owner what they would cost or waited for a go-ahead. He ran out of credits mid-session with ten
emails he could not paste. His words: *"zapracuj na tom aby si nikdy nezopakoval takuto vec!!! NIKDY"*.

THE RULE ALREADY EXISTED and was already PERMANENT, in his words from 2026-08-21: state what it is,
why, how many units of work, the unit cost and the TOTAL first, then WAIT. It lived in the memory
store, which is exactly where a rule goes to be broken, because a rule you have to recall is one you
break while thinking about something else. The humanizer receipt had this same history: said three
times, broken three times, fixed only when it became a file on disk that refuses.

WHAT THIS CHECKS. Every brief must carry a BUDGET line naming the totals and quoting the owner's own
approval. The quote is then looked for in the LIVE SESSION TRANSCRIPT, in a record the harness marked
`origin.kind == "human"`, arriving AFTER the assistant message that stated the budget. That ordering
is the whole point: cost first, then the human, then the launch.

WHY THE QUOTE CANNOT BE FAKED THE WAY A FLAG CAN. `--humanizer-skill-ran` was once a bare flag, which
is exactly as strong as remembering, and it got passed on a draft whose skeptic never ran. A quote is
different: the hook does not take my word that the owner approved, it goes and finds his words in a
file the harness writes and I do not. If I invent an approval, there is nothing to find.

IT FAILS CLOSED, like its sibling. A guard that exits 0 when its own parse breaks is the defect this
repository keeps paying for.

WHAT IT DOES NOT DO. It does not price the work, judge the task, or count tokens. It asks one
question: did a human say yes, after seeing a number. Everything else is my job.
"""
from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))

SUBAGENT_TOOLS = ("Task", "Agent")
BUDGET_RE = re.compile(r"BUDGET:\s*(?P<body>[^\n]*)", re.I)
# Two characters, not four. The owner approves with "ok" more often than with a sentence, and a
# four-character floor blocked a launch he had just authorised. What makes a short quote safe is not
# its length: it is the ORDER check below, which requires the words to arrive after the assistant
# message that named the cost. A long invented quote fails; a two-letter real one passes.
QUOTE_RE = re.compile(r'Owner approved:\s*"(?P<quote>[^"]{2,300})"', re.I)

TEMPLATE = (
    'BUDGET: <n> agents, ~<tokens> tokens total, <what it buys>. '
    'Owner approved: "<paste his exact words>"'
)


def _norm(s):
    return " ".join((s or "").split()).lower()


def block(msg):
    sys.stderr.write(msg + "\n")
    raise SystemExit(2)


def _helpers():
    """Reuse owner_spoke's transcript reader rather than write a second one that can drift."""
    if REPO not in sys.path:
        sys.path.insert(0, REPO)
    from tools.owner_spoke import _transcripts, _ts, _text_of, _origin_kind, assistant_texts
    return _transcripts, _ts, _text_of, _origin_kind, assistant_texts


def approval_for(quote, transcript=None):
    """(ok, why). True when a human said `quote` AFTER an assistant message stating a BUDGET."""
    _transcripts, _ts, _text_of, _origin_kind, assistant_texts = _helpers()
    paths = [transcript] if transcript else _transcripts()
    if not paths:
        return False, "no session transcript found, so no approval can be verified"

    want = _norm(quote)
    # Newest first, and NEVER give up on the first transcript that merely contains the words. A short
    # approval ("ano sprav to") matches old sessions too, and returning early on one of those blocked
    # a launch the owner had actually approved -- the guard's own false negative, caught on its first
    # live use. Evaluate every transcript and fail only when none satisfies BOTH conditions.
    try:
        paths = sorted(paths, key=lambda q: os.path.getmtime(q), reverse=True)
    except Exception:                                # noqa: BLE001
        pass
    reasons = []
    for p in paths:
        # When did I last state a budget?
        stated = [t for t, txt in assistant_texts(p) if "budget:" in (txt or "").lower()]
        human = []
        with open(p, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except Exception:                    # noqa: BLE001
                    continue
                msg = r.get("message") or {}
                if msg.get("role") == "user" and _origin_kind(r) == "human":
                    human.append((_ts(r.get("timestamp")), _text_of(msg)))

        hits = [(t, txt) for t, txt in human if want and want in _norm(txt)]
        if not hits:
            continue
        if not stated:
            reasons.append("a transcript has the words but never stated a BUDGET")
            continue
        first_budget = min(stated)
        if any(t and first_budget and t > first_budget for t, _ in hits):
            return True, "approved after the cost was stated"
        reasons.append("the words appear only BEFORE the budget was stated there")
    if reasons:
        return False, "; ".join(sorted(set(reasons)))
    return False, "no human message in any session transcript contains those words"


def main():
    try:
        raw = sys.stdin.read()
        d = json.loads(raw) if raw.strip() else {}
    except Exception as e:                            # noqa: BLE001
        block("agent_budget: could not read the hook payload (%r). Blocking, because a guard that "
              "fails open is the defect it exists to prevent." % e)

    if (d.get("tool_name") or d.get("tool") or "") not in SUBAGENT_TOOLS:
        return 0

    ti = d.get("tool_input") or {}
    prompt = (ti.get("prompt") or "") + "\n" + (ti.get("description") or "")

    if not BUDGET_RE.search(prompt):
        block(
            "agent_budget: BLOCKED. This brief carries no BUDGET line.\n"
            "  The owner's PERMANENT rule: say what it is, how many units, the unit cost and the\n"
            "  TOTAL, then WAIT for his go-ahead. On 2026-09-02 nine agents ran without it and he\n"
            "  lost the rest of his session.\n"
            "  Add, in the brief:\n    " + TEMPLATE
        )

    m = QUOTE_RE.search(prompt)
    if not m:
        block(
            "agent_budget: BLOCKED. The BUDGET line names no owner approval.\n"
            "  Quote his exact words, verbatim, so the hook can find them in the transcript:\n"
            '    Owner approved: "<his words>"\n'
            "  If he has not answered yet, that is the answer: do not launch."
        )

    quote = m.group("quote")
    try:
        ok, why = approval_for(quote)
    except Exception as e:                            # noqa: BLE001
        block("agent_budget: the approval check itself failed (%r). Blocking rather than passing." % e)

    if not ok:
        block(
            "agent_budget: BLOCKED. Could not verify that approval.\n"
            "  Reason: " + why + "\n"
            "  Quoted: " + quote[:120] + "\n"
            "  The quote has to be the owner's own words from THIS session, sent after you told him\n"
            "  the total. Inventing one is the failure this hook exists for."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
