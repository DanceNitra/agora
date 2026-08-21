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
    # "the honest minimum is", "an honest verdict is" -- an abstraction given a human virtue.
    "the-honest-X": re.compile(
        r"\b(?:the|an|a|its|our|their|his|her|this|that)\s+honest\s+[a-z]+\b", re.I),
    # persuasive-speech emphasis, diluted by repetition
    "worth-saying": re.compile(r"\bworth\s+(?:saying|noting|stating|repeating)\b", re.I),
    # the "not X, but Y" antithesis, once per paragraph, is the rhythm people notice
    "not-X-but-Y": re.compile(
        r"\b(?:is|was|are|were)\s+not\s+\w+(?:\s+\w+){0,3},\s+(?:it|they)\s+(?:is|was|are|were)\b",
        re.I),
    # an em-dash clause explaining the sentence just written -- Stratogain's own count, and ours
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
    return "\n".join(lines)


if __name__ == "__main__":
    import pathlib
    import sys
    for arg in sys.argv[1:]:
        print("==", arg)
        print(report(pathlib.Path(arg).read_text(encoding="utf-8", errors="replace")))
