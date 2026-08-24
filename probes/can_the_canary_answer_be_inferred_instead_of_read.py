"""The negative control our cap probe never had: is a "correct" canary READ, or RECONSTRUCTED?

`probes/is_the_cap_counted_in_bytes_or_utf16_units.py` asks the model for the last CANARY-Lnnnn it
can see and treats the answer as an observation of what loaded. It has no arm in which a correct
answer is impossible to guess, so "correct" cannot be separated from "the model computed a
plausible line number". The gap is real: our canaries are `CANARY-L0198` on line 198 of a 200-line
file, and 198 is derivable from the documented cap and the line width without reading anything.
Conceded publicly on anthropics/claude-code#82056 (comment 5387316542) before it was fixed here.

Two arms, and the second is the one that decides.

  ABSENT   200 lines of filler carrying NO canary token at all. The only correct answer is that
           there is none. Any CANARY-Lnnnn in the reply is fabricated outright: no read of any
           kind can produce it. Catches gross invention, does not catch inference.

  SHUFFLED 200 lines whose canary tokens are a fixed PERMUTATION of the line numbers, so the token
           on line N is not N. A model that reads its context returns the token actually sitting at
           the cut. A model reasoning "cap 25,000 over 126 units a line, so 198" returns L0198,
           which on this fixture sits somewhere else entirely. The two hypotheses produce different
           strings, which is what a control has to do.

The permutation is seeded and written into the receipt, so the expected token is checkable rather
than trusted. Both arms are the same size in UTF-16 units, so the cut lands in the same place.
Tools are disabled through the same allowlist the main probe uses, and every arm repeats, because
one answer cannot tell a read from an invention: a guarded session has returned 214, 242, 246, 248
and 250 on a 200-line file.

NEITHER ARM IS OUR DESIGN, and a skeptic pass found that before this was posted anywhere.
ABSENT is the closed-book baseline, standard and named: Liu et al., TACL 2024, "In the closed-book
setting, models are not given any documents in their input context, and must rely on their
parametric memory" (arXiv 2307.03172). SHUFFLED is corpus substitution / counterfactual context:
Longpre, Perisetla, Chen, Ramesh, DuBois, Singh, "Entity-Based Knowledge Conflicts in Question
Answering", EMNLP 2021 (arXiv 2109.05052), which replaces the answer inside the context so that
reading and reconstructing produce different strings. Identical logic. Comparing a canary against
equally-random non-inserted sequences is Carlini et al., USENIX Security 2019. No new name is owed
to us for any of it.

WHAT THIS CONTROL DOES NOT ESTABLISH, stated because it is easy to overread a green run:

  * `CUT` is HARDCODED at 198, not measured here. The arm asks whether the reply is `perm[CUT-1]`,
    so it presumes the cut position it then validates against. It shows the answer was not computed
    from the cap arithmetic; it does not independently establish where the cut is.
  * "the last token you can SEE" is the recency-favoured position. Echoing the final surviving line
    of a context requires no comprehension of any cap, so a pass here is consistent with a model
    that understands nothing about truncation and simply repeats what it last saw.
  * The seed was screened on FIXTURE GEOMETRY (distance from the inferable answer, zero fixed
    points) before any model was called, never on the model's answers. Said in those words on
    purpose: screening on the outcome would be a forking path, and this was not that.

Run only with an explicit go-ahead: 2 arms x (1 init + TRIALS) `claude -p` sessions.
"""
from __future__ import annotations

import json
import os
import random
import re
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import is_the_cap_counted_in_bytes_or_utf16_units as U  # noqa: E402

TRIALS = 3
# Chosen, not arbitrary: this seed puts a token 138 away from the cut and has no fixed points, so
# no plausible arithmetic lands on the right answer by accident. The first seed I tried put L0195
# on line 198, three away from the inferred 198 and inside the band a slightly different
# calculation (floor vs ceil, 126 vs 127 units) would produce. A control whose correct answer sits
# next to the wrong one is not a control.
SEED = 20260846
LINES, WIDTH = 200, 125
CUT = 198          # the last line the main probe measures as loaded, on this geometry
ASK_ABSENT = ("Respond with only: LAST=<the last CANARY-Lnnnn token you can see, or NONE if there "
              "is no such token> || WARNING=<verbatim any truncation notice, else NO-INDICATOR>")
_t0 = time.time()


def permutation() -> list[int]:
    """Line i (1-based) carries token number perm[i-1]. Fixed seed, recorded in the receipt."""
    labels = list(range(1, LINES + 1))
    random.Random(SEED).shuffle(labels)
    return labels


def make_shuffled(perm: list[int]) -> str:
    out = []
    for i in range(1, LINES + 1):
        head = f"- [E{i:04d}](e-{i:04d}.md) CANARY-L{perm[i - 1]:04d} "
        out.append(head + "x" * max(0, WIDTH - len(head)))
    return "\n".join(out) + "\n"


def make_absent() -> str:
    """Same geometry, no canary anywhere. `entry NNNN ` is the same width as `CANARY-LNNNN `
    minus one, and the filler absorbs the difference, so both arms are identical in size."""
    out = []
    for i in range(1, LINES + 1):
        head = f"- [E{i:04d}](e-{i:04d}.md) entry {i:04d} "
        out.append(head + "x" * max(0, WIDTH - len(head)))
    return "\n".join(out) + "\n"


def arm(root: str, name: str, text: str, ask: str) -> list[dict]:
    cwd = os.path.join(root, name)
    os.makedirs(cwd, exist_ok=True)
    store, _, offered, _ = U.run(cwd, "Reply with only: INIT")
    if offered:
        raise SystemExit(f"REFUSED: {len(offered)} tools offered; a disk read could answer this")
    if not store:
        raise SystemExit("REFUSED: store not resolved, so nothing here would be evidence")
    os.makedirs(store, exist_ok=True)
    with open(os.path.join(store, "MEMORY.md"), "wb") as f:
        f.write(text.encode("utf-8"))
    U.CREATED.append(store)
    out = []
    for t in range(1, TRIALS + 1):
        _, ans, off2, used = U.run(cwd, ask)
        head = (ans or "").split("WARNING")[0]
        m = (re.search(r"LAST\s*=\s*\**\s*CANARY-L(\d{4})", head)
             or re.search(r"CANARY-L(\d{4})", head))
        out.append({"arm": name, "trial": t, "token": int(m.group(1)) if m else None,
                    "said_none": bool(re.search(r"LAST\s*=\s*\**\s*NONE", head, re.I)),
                    "tools_offered": len(off2), "tool_uses": used, "answer": (ans or "")[:200]})
        print(f"[{time.time() - _t0:6.1f}s]   {name:9s} {t}/{TRIALS} "
              f"token={out[-1]['token']} none={out[-1]['said_none']}", flush=True)
    return out


def main() -> int:
    U.CLAUDE = U.claude_bin()
    root = tempfile.mkdtemp(prefix="canaryctl_")
    perm = permutation()
    expected = perm[CUT - 1]          # what a READER must return on the shuffled arm
    print(f"  shuffled fixture: line {CUT} carries CANARY-L{expected:04d}, "
          f"and L{CUT:04d} sits on line {perm.index(CUT) + 1}")

    rows = arm(root, "absent", make_absent(), ASK_ABSENT)
    rows += arm(root, "shuffled", make_shuffled(perm), U.ASK)
    ab = [r for r in rows if r["arm"] == "absent"]
    sh = [r for r in rows if r["arm"] == "shuffled"]

    v = {
        "no_tools_were_offered": all(r["tools_offered"] == 0 for r in rows),
        "no_tool_was_called": all(not r["tool_uses"] for r in rows),
        # ABSENT: naming any canary is invention, full stop.
        "absent_arm_invents_nothing": all(r["token"] is None for r in ab),
        # SHUFFLED: the discriminator. Reading gives `expected`; inferring gives the line number.
        "shuffled_arm_returns_the_token_that_is_there": all(r["token"] == expected for r in sh),
        "shuffled_arm_did_not_return_the_line_number": all(r["token"] != CUT for r in sh),
    }
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "can_the_canary_answer_be_inferred_instead_of_read.result.json")
    prev = []
    if os.path.exists(out):
        try:
            prev = json.load(open(out, encoding="utf-8")).get("runs", [])
        except Exception:
            prev = []
    this = {"claude_version": U.subprocess.run([U.CLAUDE, "--version"], capture_output=True,
                                               text=True).stdout.strip(),
            "seed": SEED, "cut_line": CUT, "token_at_cut": expected,
            "line_holding_the_cut_number": perm.index(CUT) + 1,
            "verdicts": v, "rows": rows}
    removed, left = U.cleanup()
    v["every_fixture_store_was_removed"] = not left
    this["verdicts"] = v
    json.dump({"probe": "can_the_canary_answer_be_inferred_instead_of_read",
               "permutation": perm, "verdicts": v, "rows": rows, "runs": prev + [this]},
              open(out, "w", encoding="utf-8"), indent=2)
    print(f"  fixture stores removed: {removed}   still present: {len(left)}")
    print("\n=== VERDICTS ===")
    for k, val in v.items():
        print(f"  {'YES' if val else 'no '}  {k}")
    print(f"\nwrote {out}")
    return 0 if all(v.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
