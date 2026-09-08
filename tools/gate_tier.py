"""How heavy does the gate have to be for THIS draft? Read the draft, not the mood.

WHAT THIS IS NOT. It is not a way to skip a skill. All three receipts are still required for every
outbound message, and nothing here can waive one. It decides a narrower question: whether each skill
has to run as a SUBAGENT PANEL or can run through the Skill tool in this session.

WHY. A red-team panel is five agents and a verify pass is four, so the full frame costs several
hundred thousand tokens. That is the right price for a claim carrying measured numbers into someone
else's issue tracker. It is the wrong price for a note saying a merge conflict is resolved, and on
2026-09-08 the owner stopped exactly that: "prestan pustat agentov na jednoriadkovu odpoved".

THE RULE, and it only ever moves upward from LIGHT on evidence in the text:

  a number            any digit outside a version, a date or an issue reference. A figure is the
                      thing we have published wrong before, so it pulls verify to the panel.
  a citation          a URL, a DOI, an arXiv id, or a quoted sentence. Someone else's words are
                      checked against their source, never against our memory of it.
  a claim about       an @mention, or a possessive naming a third party's code. Saying what someone
  someone else        else's system does is where a wrong sentence costs a relationship.
  length              over LIGHT_MAX_WORDS. A long message has room to assert something the short
                      rules did not catch.

Anything that trips a rule goes FULL. A draft that trips nothing asserts only facts about our own
repository that the reader can refresh and see, and gets LIGHT.

THE FAILURE MODE THIS CANNOT SEE, stated because it is the one that will bite. It reads surface
features, so a claim written entirely in prose, with no digit and no name, reads as LIGHT. The
backstop is that LIGHT still runs all three skills; it lowers the depth of the pass, never its
existence.

Usage:
    python tools/gate_tier.py drafts/x.md
    python tools/gate_tier.py drafts/x.md --json
"""
import argparse
import io
import json
import os
import re
import sys

LIGHT_MAX_WORDS = 120

# A version, a date, an issue or PR reference, and a time. These are addresses, not measurements:
# "PR 10649" and "2026-09-08" carry no claim that a verifier could check against a source.
# `(?<!\w)` rather than `\b` at the front: `\b` needs a word character on its left, so it never
# matched `#233` after a space and every issue reference leaked through as a figure.
NOT_A_FIGURE = re.compile(
    r"""(?<!\w)(?:
        v\d+(?:\.\d+)+ | \d+\.\d+\.\d+  # v0.6, 1.2.3. A TWO-part decimal is NOT treated as a
                                        # version: the first draft of this line swallowed "63.9%"
                                        # as one, and a percentage is the figure class we have
                                        # published wrong before.
      | \d{4}-\d{2}-\d{2}               # 2026-09-08
      | \d{1,2}:\d{2}                   # 09:00
      | \#\d+                           # #10649
      | (?:PR|issue|pull\ request)\s+\d+
    )\b""", re.X | re.I)

CITATION = re.compile(r"https?://|\barXiv:\s*\d|\b10\.\d{4,}/|\bdoi\b", re.I)
MENTION = re.compile(r"(?<![\w/])@[A-Za-z0-9][\w-]{1,38}\b")
QUOTED = re.compile(r'"[^"]{25,}"')
# "your client", "his store", "their normalizer": a sentence about someone else's software.
THIRD_PARTY_POSSESSIVE = re.compile(
    r"\b(?:your|his|her|their|its)\s+(?:\w+\s+){0,2}"
    r"(?:client|server|store|library|repo|repository|code|implementation|normali[sz]er|parser|"
    r"index|adapter|schema|api|endpoint|queue|pipeline|model|system|tool)\b", re.I)


def classify(text):
    """(tier, reasons). LIGHT only when nothing fires."""
    # Collapse whitespace first: a wrapped draft splits "your client" across a line break, and the
    # trigger then reported itself as the two-line string "your\nclient".
    text = " ".join(text.split())
    stripped = NOT_A_FIGURE.sub(" ", text)
    reasons = []
    figs = sorted(set(re.findall(r"\b\d[\d,.]*%?", stripped)))
    if figs:
        reasons.append(("a number", "verify", ", ".join(figs[:6])))
    cites = CITATION.findall(text)
    if cites:
        reasons.append(("a citation", "verify", "%d found" % len(cites)))
    who = sorted(set(MENTION.findall(text)))
    if who:
        reasons.append(("names a person", "redteam", ", ".join(who[:6])))
    tp = sorted({m.strip() for m in THIRD_PARTY_POSSESSIVE.findall(text)})
    if tp:
        reasons.append(("a claim about someone else's software", "redteam", "; ".join(tp[:4])))
    q = QUOTED.findall(text)
    if q:
        reasons.append(("quotes someone", "verify", "%d quotation(s)" % len(q)))
    words = len(text.split())
    if words > LIGHT_MAX_WORDS:
        reasons.append(("length", "both", "%d words, over %d" % (words, LIGHT_MAX_WORDS)))
    return ("FULL" if reasons else "LIGHT"), reasons


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("draft")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if not os.path.isfile(a.draft):
        print("REFUSED: %s does not exist." % a.draft)
        return 1
    text = io.open(a.draft, encoding="utf-8").read()
    tier, reasons = classify(text)

    if tier == "FULL":
        skills = {"humanizer": "in-session", "redteam": "in-session", "verify": "in-session"}
        for _, which, _ in reasons:
            for k in (("redteam", "verify") if which == "both" else (which,)):
                skills[k] = "SUBAGENT PANEL"
    else:
        skills = {k: "in-session" for k in ("humanizer", "redteam", "verify")}

    if a.json:
        print(json.dumps({"draft": a.draft, "tier": tier, "words": len(text.split()),
                          "reasons": [{"trigger": t, "raises": w, "detail": d}
                                      for t, w, d in reasons],
                          "skills": skills}, indent=1))
        return 0

    print("  %s  %s  (%d words)" % (tier, os.path.basename(a.draft), len(text.split())))
    for t, w, d in reasons:
        print("    %-40s raises %-8s %s" % (t, w, d))
    if not reasons:
        print("    nothing fired: no figure, no citation, no third party, within the length bound")
    print()
    for k in ("humanizer", "redteam", "verify"):
        print("    %-10s %s" % (k, skills[k]))
    print("\n  All three receipts are still required. This decides depth, never whether a skill runs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
