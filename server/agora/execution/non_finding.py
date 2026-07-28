"""Is this text a FINDING, or a refusal wearing one's clothes?

The guard existed in the dungeon (`mcp_server._is_refusal`) and was applied by the CALLER before it
POSTed. That is an optimisation, not a gate: `/brain/collective` accepts from any organ, so anything
reaching it by another route was never checked. A guard on the client is a guard the next client
forgets — this is the server-side one, at the choke point every path goes through.

The patterns are anchored to the start of the string, and the pipeline's output arrives WRAPPED:

    Reality: {    "answer": "The provided sources do not support the claim about deltaG..."

so the envelope has to come off first or a pattern written for exactly this sentence never fires.
Measured on 400 live discoveries: 18 were this non-finding, the anchored patterns caught 0 of them,
and unwrapping first caught 15 (83%) with no false alarm on the other 382.
"""
from __future__ import annotations

import re

_REFUSAL = re.compile(
    r"^\s*(?:i|we)\s+(?:cannot|can't|am\s+unable|are\s+unable|apologi[sz]e|am\s+sorry)"
    r"|^\s*(?:i'm|we're)\s+(?:sorry|unable)\b"
    r"|^\s*as\s+an\s+ai\b"
    r"|\bthe\s+required\s+source\s+is\s+missing\b"
    r"|\bno\s+(?:paper|source)s?\s+(?:fits|matches|(?:was|were)\s+provided)\b"
    r"|^\s*(?:none|neither)\s+of\s+the\s+(?:provided|six|cited)\b"
    r"|^\s*the\s+provided\s+(?:real\s+)?(?:paper|source|literature)s?[^.\n]{0,40}\b"
    r"(?:do(?:es)?\s+not|don't|doesn't|are\s+unrelated|is\s+unrelated)"
    r"|^\s*you\s+did\s+not\s+provide"
    r"|\bno\s+substantive\s+claim\b"
    r"|\byields\s+no\s+(?:substantive|new)\b"
    # UNANCHORED, and deliberately narrow. The three that survived the anchored patterns put the
    # refusal mid-sentence — "The joint finding is that the provided sources do not support the claim
    # about deltaG..." — so the phrase has to be matchable anywhere. It is kept specific to a
    # meta-statement ABOUT THE PROMPT'S OWN SOURCES not supporting THE CLAIM, because the general form
    # is a legitimate research finding: "Smith (2019) found the provided data do not support the
    # hypothesis" must still be accepted, and the control asserts exactly that.
    r"|\bthe\s+provided\s+(?:paper|source|literature)s?\s+(?:do(?:es)?\s+not|don't|doesn't)\s+"
    r"support\s+the\s+claim\b",
    re.I)

_ENVELOPE = re.compile(r'^(?:[^\{\n]{0,80}?)\{\s*"?\w+"?\s*:\s*"?(.*)$', re.DOTALL)


def unwrap(text: str) -> str:
    """Strip a leading `Reality: { "answer": "` style envelope so the patterns see the sentence."""
    t = (text or "").strip()
    m = _ENVELOPE.match(t)
    if m:
        t = m.group(1)
    return t.lstrip("\"' \n\t{[")


def is_non_finding(*parts: str) -> bool:
    """True when any part reads as a refusal / no-fit statement rather than a finding.

    Checked BOTH raw and unwrapped: raw so an ordinary refusal is still caught, unwrapped so the
    envelope cannot walk the text past an anchor.
    """
    for p in parts:
        if not p:
            continue
        head = p[:300]
        if _REFUSAL.search(head) or _REFUSAL.search(unwrap(p)[:300]):
            return True
    return False
