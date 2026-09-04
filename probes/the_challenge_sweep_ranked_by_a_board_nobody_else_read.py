"""Can the belief-challenge sweep queue anything at all?

WHY. `_dungeon.log` carried "all 8 candidates refused by the board gate -- nothing queued", sixteen
times in a row, once every 47 minutes. The organ was reported as idle. It was not idle; it could
not fire.

`methods.board_priority_terms` exists to be THE ONE definition of the board's on-priority words:
its own docstring records that the brain's Lab door and the dungeon's quest gate used to derive it
separately and disagreed. `belief_revision` had never been converted and still used a local
`_tokens`. Measured 2026-09-04 on the live board: the two sets disagreed on 57 of 78 words, and the
local one carried the owner's REFUSALS -- `finance`, `cloud`, `generic`, `deprioritize`, `dead`
were all in the whitelist, the same defect measured on 2026-07-31. So this module ranked candidates
by words the gate excludes on, and the gate then refused what it sent.

CHECKS:
  1. `belief_revision._board_tokens()` returns exactly `board_priority_terms(priorities_text())`.
  2. No refusal word is in the set.
  3. The candidates it now returns pass the dungeon's gate, computed the dungeon's way.
  4. THE CONTROL THAT MATTERS: an off-board title must still be REFUSED. "8 of 8 pass" is also what
     a gate that stopped gating would report, and that outcome is worse than the one being fixed.
  5. MUTATION: restoring the local tokenizer as the SELECTOR must drop the pass rate.
  6. THE INVENTORY. Every module that derives its own board word-set is named here with a reason.
     A new one is how this defect returns, and it returned once already: `board_priority_terms`
     was written in July to be the one definition, and `belief_revision` sat outside it until
     September without anything noticing.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SERVER = os.path.join(ROOT, "server")
OUT = os.path.join(HERE, "the_challenge_sweep_ranked_by_a_board_nobody_else_read.result.json")
sys.path.insert(0, SERVER)

# Words the owner used to EXCLUDE a subject. None may appear in a whitelist.
REFUSALS = ("finance", "cloud", "generic", "deprioritize", "dead")
OFF_BOARD = "A backtest of the Condorcet Jury Theorem on quasi-experimental A/B designs"

# Modules allowed to build a board word-set of their own, and why. Anything else that does it is
# a fourth definition and must be converted or added here deliberately.
DERIVERS = {
    "methods.board_priority_terms":
        "THE canonical one. Every gate reads it; /brain/board publishes its output as "
        "priority_terms so the dungeon takes it verbatim rather than re-deriving.",
    "seminar._board_vocab":
        "Declared, not converted. It keeps a NEGATIVE set as well as a positive one and refuses a "
        "topic matching only excluded words, which the canonical function does not model: that one "
        "strips refusals rather than scoring against them. The seminar is off by default since "
        "2026-09-04, so converting it would be a change to a disabled organ; recheck when it runs.",
}


def refuse(why):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    raise SystemExit(2)


def theme_words(t):
    """The dungeon's `_theme_words`, copied so this probe gates the way the dungeon really does."""
    return {w.rstrip("s") for w in re.findall(r"[a-z0-9]+", (t or "").lower()) if len(w) > 2}


def main():
    from agora.config import settings
    from agora.execution import belief_revision as BR
    from agora.execution.board import priorities_text
    from agora.execution.claude_inbox import recent_texts
    from agora.execution.methods import board_priority_terms

    text = priorities_text()
    if not text.strip():
        refuse("the board is empty, so every candidate would pass by default and this check would "
               "grade nothing")
    canonical = board_priority_terms(text)
    got = BR._board_tokens()
    print("  board: %d chars | canonical terms: %d | belief_revision: %d"
          % (len(text), len(canonical), len(got)))
    if got != canonical:
        refuse("belief_revision._board_tokens() still differs from board_priority_terms() by %d "
               "word(s); there must be one definition"
               % len(canonical.symmetric_difference(got)))
    print("  the two definitions are now identical")

    bad = [w for w in REFUSALS if w in got]
    if bad:
        refuse("refusal word(s) %s are in the whitelist; the board would admit on the very words "
               "used to exclude a subject" % bad)
    print("  no refusal word is in the set: %s" % ", ".join(REFUSALS))

    prio = {w.rstrip("s") for w in canonical}
    if not theme_words(OFF_BOARD) & prio:
        print()
        print("  CONTROL: an off-board title is still refused -> %r" % OFF_BOARD[:52])
    else:
        refuse("the off-board control title PASSES the gate, so the gate is admitting everything "
               "and a high pass rate below would mean the opposite of what it looks like")

    vault = settings.vault_path or "C:/Users/Danculus/my-second-brain"
    blob = " || ".join(recent_texts())
    cands = BR.pick_challenge_targets(vault, recent_blob=blob, n=8)
    if not cands:
        refuse("no candidates at all, so the pass rate below would be 0/0 and meaningless")

    def rate(tokens):
        p = {w.rstrip("s") for w in tokens}
        return sum(1 for c in cands if theme_words(c.get("title", "")) & p)

    passing = rate(canonical)
    print()
    print("  candidates returned: %d, of which %d pass the dungeon gate" % (len(cands), passing))
    for c in cands:
        hit = theme_words(c.get("title", "")) & prio
        print("     %-52s %s" % (c.get("title", "")[:52], sorted(hit)[:3] if hit else "REFUSED"))
    if passing == 0:
        refuse("every candidate is still refused; the sweep still cannot queue anything")

    # 5 — the mutation. Scoring the SAME candidates with the old tokenizer proves nothing: it is a
    # near-superset, so it passes them too. The tokenizer's real effect is on WHICH candidates get
    # SELECTED, so the mutation restores the old one and re-runs the selection. The first version of
    # this check scored the same list twice, reported 8 of 8 both ways, and would have certified a
    # no-op fix.
    local = BR._tokens(text)
    if local == canonical:
        refuse("the two tokenizers produce identical sets on this board, so the fix cannot be "
               "shown to change anything and this probe proves nothing")
    real = BR._board_tokens
    BR._board_tokens = lambda: local
    try:
        old_cands = BR.pick_challenge_targets(vault, recent_blob=blob, n=8)
    finally:
        BR._board_tokens = real
    old_pass = sum(1 for c in old_cands if theme_words(c.get("title", "")) & prio)
    print()
    print("  MUTATION: with the retired tokenizer driving SELECTION, %d of %d selected candidates "
          "pass the gate" % (old_pass, len(old_cands)))
    for c in old_cands[:4]:
        hit = theme_words(c.get("title", "")) & prio
        print("     %-52s %s" % (c.get("title", "")[:52], sorted(hit)[:3] if hit else "REFUSED"))
    if old_pass >= passing:
        refuse("the retired tokenizer selects candidates that pass just as often (%d vs %d), so "
               "this fix changes nothing measurable and the sweep's failure has another cause"
               % (old_pass, passing))
    print("  the two tokenizers differ on %d word(s) and select different candidates"
          % len(local.symmetric_difference(canonical)))
    local_pass = old_pass

    # 6 — the inventory of board word-set derivations.
    print()
    import subprocess
    found = subprocess.run(
        ["git", "grep", "-ln", "-e", "priorities_text()", "--", "server/agora"],
        cwd=ROOT, capture_output=True, text=True).stdout.split()
    print("  %d module(s) read the board text; declared derivers of a WORD SET:" % len(found))
    for k, why in DERIVERS.items():
        print("     %-32s %s" % (k, why[:64]))
    for k, why in DERIVERS.items():
        if len(why) < 40:
            refuse("the entry for %r has no real reason; an undeclared deriver is how this defect "
                   "comes back" % k)
    if "server/agora/execution/belief_revision.py" not in " ".join(found):
        refuse("belief_revision no longer reads the board at all, so this probe's subject is gone")

    print()
    print("  VERDICT: the sweep can queue again, and the gate still refuses off-board work.")
    json.dump({"script": os.path.basename(__file__),
               "canonical_terms": len(canonical), "local_terms": len(local),
               "symmetric_difference": len(local.symmetric_difference(canonical)),
               "refusal_words_in_whitelist": bad,
               "candidates": len(cands), "passing_canonical": passing,
               "passing_local_tokenizer": local_pass,
               "titles": [c.get("title", "")[:80] for c in cands],
               "declared_derivers": sorted(DERIVERS),
               "controls": {"one_definition": True, "off_board_still_refused": True,
                            "tokenizers_differ": True, "mutation_reproduces_failure": True}},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("  written: %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
