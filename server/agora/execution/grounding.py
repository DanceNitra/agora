"""THE definition of "is this grounded", in one place.

WHY THIS FILE EXISTS. On 2026-07-31 the repo held SIX independent answers to "does this text carry a
citation", and they disagreed on 8 of 9 citation forms. Measured, each cell = does that definition accept
that form:

    form                    quality_gate  seminar  find_div  api_grade  self_impr  funnel
    (Smith, 2024)                Y           Y        .          Y          .        Y
    Smith (2024)                 .           .        Y          .          Y        .
    Breznau et al. (2022)        .           Y        Y          .          Y        .
    doi:10.x                     Y           Y        .          Y          Y        Y
    arXiv:2404.12967             Y           Y        .          Y          Y        Y
    [[vault note]]               .           Y        .          .          .        .
    bare "et al." (no year)      .           Y        .          .          Y        .
    MEASURED:/VERDICT:           Y           .        .          .          .        Y
    bare prose                   .           .        .          .          .        .

The two author-year regexes were MIRROR IMAGES: `quality_gate._CITES` requires the name INSIDE the
parentheses, `finding_diversity._CITE` requires it OUTSIDE. Both are standard styles and each rejected
the other's. Consequence measured over the 4,000 most recent discoveries: 2,514 (62.9%) passed the vault
door and **1,127 (28.2%) were rejected while carrying a real narrative citation** -- "Cameron et al.
(2022)", "Lemos (2010)", "Dame (2011)". Those were not empty notes. They were grounded findings thrown
away over the position of a bracket, silently, because a rejection leaves no trace.

WHAT THIS FILE DOES NOT DO. It does not flatten the six into one predicate. The modules differ in PURPOSE
and that is legitimate: the vault door wants EXTERNAL grounding (a paper or a measurement), the Seminar's
verification tier wants A CHECKABLE SOURCE (a vault link counts -- a reader can follow it), and
`finding_diversity` wants to EXTRACT the source string to measure source concentration. The defect was
never that they differ in intent; it was that they differed ACCIDENTALLY, on the same form, by regex
drift. So this module exposes the primitives separately and lets each caller compose the meaning it
actually needs -- and pins them all to one table of forms in tests/test_grounding_is_unforked.py.

A NOTE ON BARE "et al.": `seminar._SOURCE_RE` accepted "as Smith et al. showed" with no year at all.
That is not a checkable source -- there is nothing to look up. It is excluded here, which TIGHTENS the
Seminar's verified tier. That is a deliberate behaviour change, measured before it shipped.
"""

from __future__ import annotations

import re

# ── the primitives ───────────────────────────────────────────────────────────────────────────────

#: Narrative author-year: `Smith (2024)`, `Smith & Jones (2024)`, `Breznau et al. (2022)`.
_CITE_NARRATIVE = re.compile(
    r"[A-Z][A-Za-z\-]+(?:\s+(?:and|&)\s+[A-Z][A-Za-z\-]+|\s+et\s+al\.?)?\s*\((?:19|20)\d{2}[a-z]?\)")

#: Parenthetical author-year: `(Smith, 2024)`, `(Breznau et al., 2022)`.
_CITE_PAREN = re.compile(
    r"\(\s*[A-Z][A-Za-z\-]+(?:\s+(?:and|&)\s+[A-Z][A-Za-z\-]+|\s+et\s+al\.?)?,?\s*(?:19|20)\d{2}[a-z]?\s*\)")

_DOI = re.compile(r"\b10\.\d{4,9}/\S+", re.I)
_ARXIV = re.compile(r"\barxiv[:\s]*\d{4}\.\d{4,5}", re.I)
_URL = re.compile(r"https?://\S+", re.I)

#: An internal reference to one of the owner's own vault notes. Checkable by a reader, but NOT external
#: evidence -- a note citing another note is not a paper.
_VAULT_LINK = re.compile(r"\[\[.+?\]\]")

#: A Lab receipt: the 6-hex id `lab.run` mints. Evidence of a measurement having happened.
_LAB_ID = re.compile(r"\blab[:_\s-]*(?:id\s*)?[:#]?\s*([0-9a-f]{6})\b", re.I)

#: A measured result. Grounding by our own computation rather than by somebody else's paper.
_MEASURED = re.compile(
    r"MEASURED:|VERDICT:|\bn\s*=\s*\d|\d+(?:\.\d+)?\s*%|p\s*[<=]\s*0?\.\d{1,4}|effect size|"
    r"\bCI\b|95%|bootstrap|risk@", re.I)


# ── the composable answers ───────────────────────────────────────────────────────────────────────

def citation(text: str) -> str | None:
    """The first EXTERNAL citation in `text`, or None. Returns the match so callers that need the
    source string (source-concentration metrics) use the same detector as callers that need a boolean."""
    for rx in (_DOI, _ARXIV, _CITE_NARRATIVE, _CITE_PAREN, _URL):
        m = rx.search(text or "")
        if m:
            return m.group(0).strip()
    return None


def is_cited(text: str) -> bool:
    """Does `text` carry an external citation (paper, DOI, arXiv, URL)?"""
    return citation(text) is not None


def is_internal_ref(text: str) -> bool:
    """Does `text` point at one of the owner's own vault notes? Checkable, but not external evidence."""
    return bool(_VAULT_LINK.search(text or ""))


def lab_id(text: str) -> str | None:
    """The Lab receipt id in `text`, or None."""
    m = _LAB_ID.search(text or "")
    return m.group(1) if m else None


def is_measured(text: str) -> bool:
    """Does `text` carry a measured result or a Lab receipt, rather than a claim about one?"""
    return bool(_MEASURED.search(text or "")) or lab_id(text) is not None


#: Nouns that name a SOURCE. The refusal test anchors on these and nowhere else, because the
#: distinction that matters is between a non-answer and a null result: "no sources were found" is an
#: unanswered question, while "no significant difference was found (p=0.31)" is science, and a filter
#: that cannot tell them apart deletes our best material.
_SOURCE_NOUN = r"(?:papers?|sources?|stud(?:y|ies)|abstracts?|evidence|references?|citations?|literature)"

#: "no <up to three modifiers> <source noun> ... <verb of support>", plus the "none of the ..." form.
#: The gap for modifiers is the whole point: the previous pattern required the noun IMMEDIATELY after
#: "no", so a single adjective defeated it. Measured on the live inbox 2026-07-31: ten pending tasks
#: carried a refusal and the guard caught ONE -- every miss was of the form "No REAL sources were
#: provided". A guard with 10% recall reports safe.
_REFUSAL = re.compile(
    r"\bno(?:ne of the)?\b(?:\s+[a-z-]+){0,3}?\s+" + _SOURCE_NOUN +
    r"\b[^.\n]{0,70}?\b(?:support|provide|relate|address|mention|match|fit|confirm|ground|report|"
    r"found|exist|available)\w*"
    r"|\b(?:cannot|could not|can't) be (?:assessed|evaluated|determined|verified)\b[^.\n]{0,40}"
    r"\b(?:available|provided|existing)\b"
    r"|\bdoes not (?:support|fit|apply)\b|\b(?:are|is) unrelated\b"
    r"|\bcould not find\b|\bunable to (?:find|locate)\b|\bthe closest (?:are|is)\b"
    r"|\bnot supported by\b|\btotal mismatch\b|\bas an ai\b"
    r"|\bi (?:cannot|can't|could not|am unable)\b", re.I)


def is_refusal(text: str) -> bool:
    """Is this a NON-ANSWER dressed as research -- "no sources were provided to support the claim"?

    THE ONE DEFINITION, because the same question is asked at two doors and only one was asking it.
    `_garbage_finding` kept a private copy and used it to keep refusals out of the discovery pool;
    nothing checked the CORP -> Claude inbox path, so a refusal that could never become a finding
    still became a task. Measured 2026-07-31: 10 of 33 pending inbox tasks (30%) were refusals, nine
    of them invisible to the private copy as well.

    A null RESULT is not a refusal. See `_SOURCE_NOUN`.
    """
    return bool(_REFUSAL.search(text or ""))


def is_grounded(text: str, allow_internal: bool = False) -> bool:
    """The vault-door question: external citation OR our own measurement.

    `allow_internal=True` widens it to "a reader can check this", which is what the Seminar's
    verification tier means -- there, a [[vault note]] is a legitimate anchor.
    """
    if is_cited(text) or is_measured(text):
        return True
    return allow_internal and is_internal_ref(text)
