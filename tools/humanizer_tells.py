"""The AI tells, in ONE place, as CONSTRUCTIONS rather than words.

Every outbound gate had its own hand-typed denylist -- twelve copies at last count, each drifting
from the others. A rule you have to retype in each new gate is a rule that is wrong in half of them,
so it lives here and gets imported.

The patterns come from @jason-sachs on anthropics/claude-code#34556, who read a hundred comments and
named the tells precisely enough to be actionable. His diagnosis is sharper than the word lists we
were using, in BOTH directions:

  * "load-bearing" is a shibboleth, not a preference. Outside structural engineering ("a load-bearing
    wall") no English writer reaches for it. Ban the word.
  * "honest" is NOT the tell. `the honest X is Y` is. People are honest; sentences, claims, verdicts
    and manifests are not. Our old list banned the bare word, which is both too wide -- it would
    reject "an honest null result", a phrase we have published and stand behind -- and too narrow,
    because it says nothing about the construction that actually reads as generated.
  * "worth saying / worth noting" is ordinary English, but it belongs to persuasive speech. If three
    things in one comment are worth noting, none of them are.

Measured on our own published output the day this file was written: **137** instances of the
`the honest X` construction across 154 files in `public/`, and 314 uses of the bare word. So the
correction is ours, not only theirs.

    from tools.humanizer_tells import find_tells
    hits = find_tells(draft)          # [(tell_name, matched_text, offset), ...]
"""
from __future__ import annotations
import re

#: Words that read as generated wherever they appear.
BANNED_WORDS = (
    "however", "moreover", "furthermore", "delve", "leverage", "crucial",
    "load-bearing", "seamless", "in conclusion", "it is worth noting",
    "a testament to", "navigate the complexities", "it should be noted",
)

#: CONSTRUCTIONS, which is where most of the tell lives. A word list cannot see these.
CONSTRUCTIONS = {
    # "the honest minimum is", "the honest version of" -- an abstraction given a human virtue.
    #
    # The article is load-bearing here, and the first version of this pattern got it wrong in a way
    # its own docstring above forbids: it included `a|an`, so it rejected "an honest null result" --
    # named four paragraphs up as a phrase we have published and stand behind. Measured 2026-08-23
    # when a negative fixture for exactly that sentence failed.
    #
    # `an honest X` is a real X that happens to be honest, which is ordinary English. `THE honest X`
    # is the construction @jason-sachs described: it presupposes a single true version and awards it
    # a human virtue. Both of his examples take the definite article, and so did our own escape --
    # "that is the honest version of §2.1", sent to deepseek-ai/DeepSeek-V3#1591 on 2026-08-23.
    "the-honest-X": re.compile(
        r"\b(?:the|its|our|their|his|her|this|that)\s+honest\s+[a-z]+\b", re.I),
    # persuasive-speech emphasis, diluted by repetition
    "worth-saying": re.compile(r"\bworth\s+(?:saying|noting|stating|repeating)\b", re.I),
    # the "not X, but Y" antithesis, once per paragraph, is the rhythm people notice
    "not-X-but-Y": re.compile(
        r"\b(?:is|was|are|were)\s+not\s+\w+(?:\s+\w+){0,3},\s+(?:it|they)\s+(?:is|was|are|were)\b",
        re.I),
}

#: Constructions we REPORT but do not block on, because measured against our own sent comments they
#: do not isolate the tell they name.
#:
#: `em-dash-gloss` is the case, and it is worth keeping the reason rather than the verdict.
#: @Stratogain named his own tell as "an em-dash clause explaining the sentence I just wrote,
#: roughly once a paragraph". The regex below matches a PAIRED em-dash parenthetical, which is a
#: different thing and ordinary English. Run over the 21 comments we sent between 21 and 23 August
#: it fired four times and **all four were legitimate**: "the line stopped appearing — twelve
#: comments in a row without it — and the length doubled", "three tip vertices — the outer corners
#: — and no edge joins two of them", and a pair wrapping two Chinese record labels. A trailing-clause
#: variant (`—[^—\n]{15,}?[.!?]`) is worse in the other direction: 45 hits over the same 21
#: comments, i.e. a banner.
#:
#: So neither regex separates the construction, and a blocking check with a measured 4/4 false
#: positive rate teaches the operator to wave the gate through, which costs more than it catches.
#: What DOES track the tell is the rate: `em_dash_rate` ran 0.00-0.82 per 100 words across our
#: 22 August comments and climbed back to 1.41-1.77 in the four sent after that, which is the
#: regression a paired-parenthetical count could not see. Demoted to a number, not deleted.
REPORT_ONLY_CONSTRUCTIONS = {
    "em-dash-gloss": re.compile(r"—[^—\n]{15,}—"),
}


def find_tells(text: str, banned=BANNED_WORDS, constructions=CONSTRUCTIONS):
    """Return every hit as (name, matched_text, offset). Empty list means clean."""
    hits = []
    low = text.lower()
    for w in banned:
        start = 0
        while True:
            i = low.find(w, start)
            if i < 0:
                break
            hits.append((w, text[i:i + len(w)], i))
            start = i + 1
    for name, rx in constructions.items():
        for m in rx.finditer(text):
            hits.append((name, m.group(0), m.start()))
    return sorted(hits, key=lambda h: h[2])


def em_dash_rate(text: str) -> float:
    """Em-dashes per 100 words. Ours ran ~1.6; the humanized draft runs 0.25."""
    words = len(text.split()) or 1
    return round(100.0 * text.count("—") / words, 2)


def contraction_rate(text: str) -> float:
    """Contractions per 100 words. Zero is the strongest single tell in our own drafts."""
    words = len(text.split()) or 1
    n = sum(text.count(c) for c in ("n't", "'re", "'ve", "'ll", "'d ", "'s "))
    return round(100.0 * n / words, 2)


def report(text: str) -> str:
    hits = find_tells(text)
    lines = ["%d words | em-dashes/100w %.2f | contractions/100w %.2f"
             % (len(text.split()), em_dash_rate(text), contraction_rate(text))]
    if not hits:
        lines.append("no tells")
    for name, got, off in hits:
        lines.append("  %-14s %r  @%d" % (name, got, off))
    for name, got, off in find_tells(text, banned=(), constructions=REPORT_ONLY_CONSTRUCTIONS):
        lines.append("  [report only] %-14s %r  @%d" % (name, got, off))
    return "\n".join(lines)


def line_of(text: str, offset: int) -> int:
    """1-indexed line number, so a hit can be found in the draft rather than hunted."""
    return text.count("\n", 0, offset) + 1


def gate(text: str) -> tuple[list, str]:
    """(blocking hits, human-readable report). Empty list means nothing to acknowledge.

    Separated from `report` so a caller can decide, rather than parse prose to find out.
    """
    return find_tells(text), report(text)


if __name__ == "__main__":
    import pathlib
    import sys
    for arg in sys.argv[1:]:
        print("==", arg)
        print(report(pathlib.Path(arg).read_text(encoding="utf-8", errors="replace")))
