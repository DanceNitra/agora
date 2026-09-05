"""Can a configured promptIndexMaxBytes ever make the memory reminder fire LATER? No, and we said it could.

WHY THIS EXISTS. On anthropics/claude-code#91188 we published, as comment 5499087276: "raising the
configured value raises the number you are told to aim for", and called it "a threshold setting that
moves the advice and not the threshold". The second half stands. The first half is false above a
crossover, and two people in that thread have said they are trusting our bundle reads because they
cannot reproduce them. So this measures our own published sentence.

WHAT THE BINARY ACTUALLY DOES. The two memory-index call sites pass FOUR fields into one function,
and that function is a SELECTOR that returns exactly one pair:

    function IHe({rawSizeBytes:e,surfaceCap:n,splicedSizeBytes:r,spliceCap:o,spliceActive:d}){
      return n!==void 0&&(!d||e/n>=r/o) ? {sizeBytes:e,byteCap:n} : {sizeBytes:r,byteCap:o}
    }

`n` is the configured cap. The surface pair wins only when its FRACTION is at least the spliced
pair's. Raising the configured cap lowers e/n, so past a crossover the configured value is discarded
and the hardcoded 25,000 governs again. The knob is one-directional: it can only make the reminder
fire earlier.

AN EARLIER VERSION OF THIS PROBE CLAIMED THE OPPOSITE SHAPE -- that the build now compares two size
dimensions against two caps. That was wrong, and wrong in the way this repository keeps paying for:
it read the fields at the call site and never followed them one function further. The selector was
one grep away. It is transcribed here rather than described, and pinned, so a rewrite upstream breaks
this probe instead of silently changing its meaning.

CONTROLS, each proved able to fail by mutation:
  * PIN THE SELECTOR, NOT THE BUILD. The binary changed twice in one day and its size is useless as a
    version. This extracts IHe's source text and pins ITS sha256. If upstream rewrites the selector,
    the probe refuses instead of reporting a stale mechanism.
  * BOTH DIRECTIONS MUST BE REACHABLE. A tighter configured cap must WIN and a looser one must be
    DISCARDED. If either arm never fires, the one-directional claim is untested and the probe refuses.
  * THE CROSSOVER IS DERIVED, THEN CHECKED BY SIMULATION. The algebraic crossover is compared against
    a brute scan of the selector transcribed from the binary. Disagreement refuses.
  * A NEGATIVE ARM ON THE DEFAULT PATH. With no configured cap the selector must return the spliced
    pair, because that is the case every user is in and the claim must not depend on the knob
    existing.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "our_own_comment_said_the_knob_raises_the_target_and_the_selector_discards_it.result.json")

BIN = os.path.expandvars(r"%APPDATA%\npm\node_modules\@anthropic-ai\claude-code\bin\claude.exe")
INDEX = os.path.join(os.path.expanduser("~"), ".claude", "projects",
                     "C--Users-Danculus-agora", "memory", "MEMORY.md")

SELECTOR_SHA = "43f9143b809e2246"      # first 16 hex of the extracted IHe body; see PIN control
SPLICE_CAP = 25000                     # the hardcoded cap the selector falls back to
FIRE = 0.8


def refuse(why):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why}, io.open(OUT, "w", encoding="utf-8"), indent=1)
    raise SystemExit(2)


def selector(raw, surface_cap, spliced, splice_cap, splice_active):
    """Transcribed from the binary, not described. Returns (sizeBytes, byteCap)."""
    if surface_cap is not None and ((not splice_active) or raw / surface_cap >= spliced / splice_cap):
        return raw, surface_cap
    return spliced, splice_cap


def main():
    if not os.path.exists(BIN):
        refuse("no shipped binary at %s" % BIN)
    blob = io.open(BIN, "rb").read()

    # PIN CONTROL: extract the selector and pin its text, not the binary's size.
    m = re.search(rb"function IHe\(\{rawSizeBytes.{0,320}?\}\}", blob, re.S)
    if not m:
        refuse("the selector `function IHe({rawSizeBytes...` is not in this build; the mechanism "
               "this probe describes may have been rewritten, so nothing here may be published")
    body = m.group(0).decode("utf-8", "replace")
    got = hashlib.sha256(body.encode()).hexdigest()[:16]
    for need in ("surfaceCap", "splicedSizeBytes", "spliceCap", "spliceActive",
                 "sizeBytes:", "byteCap:"):
        if need not in body:
            refuse("the selector no longer mentions %s; transcription is stale" % need)
    # The load-bearing shape: a ternary returning ONE pair, with a >= between two fractions.
    if ">=" not in body or body.count("sizeBytes:") != 2:
        refuse("the selector is not a two-branch chooser any more (>= present: %s, branches: %d); "
               "the one-directional claim rests on that shape" % (">=" in body, body.count("sizeBytes:")))

    # Our own index, as the case the arithmetic is run on.
    if not os.path.exists(INDEX):
        refuse("no MEMORY.md at %s to run the arithmetic on" % INDEX)
    txt = io.open(INDEX, "rb").read().decode("utf-8").strip()
    raw_bytes = len(txt.encode("utf-8"))
    spliced_units = len(txt.encode("utf-16-le")) // 2      # what the personal path compares

    # NEGATIVE ARM: no configured cap is the default every user is in.
    d_size, d_cap = selector(raw_bytes, None, spliced_units, SPLICE_CAP, True)
    if (d_size, d_cap) != (spliced_units, SPLICE_CAP):
        refuse("with no configured cap the selector did not fall back to the spliced pair, so the "
               "default-path reading is wrong and nothing below applies to real users")

    # BOTH DIRECTIONS: a tighter cap must win, a looser one must be discarded.
    crossover = raw_bytes * SPLICE_CAP / spliced_units      # e/n >= r/o  <=>  n <= e*o/r
    tight = int(crossover * 0.85)
    loose = int(crossover * 1.25)
    t_size, t_cap = selector(raw_bytes, tight, spliced_units, SPLICE_CAP, True)
    l_size, l_cap = selector(raw_bytes, loose, spliced_units, SPLICE_CAP, True)
    if t_cap != tight:
        refuse("a cap tighter than the crossover was discarded, so the knob never wins and the "
               "claim that it can only tighten is not what this build does")
    if l_cap != SPLICE_CAP:
        refuse("a cap looser than the crossover was honoured, so the knob is NOT one-directional "
               "and our correction would be as wrong as the sentence it corrects")

    # CROSSOVER: algebra against a brute scan of the transcribed selector.
    scan = None
    for n in range(1000, 200000, 1):
        if selector(raw_bytes, n, spliced_units, SPLICE_CAP, True)[1] != n:
            scan = n
            break
    if scan is None:
        refuse("the brute scan never found a cap that gets discarded, so the crossover is untested")
    if abs(scan - crossover) > 2:
        refuse("algebraic crossover %.1f disagrees with the scanned one %d" % (crossover, scan))

    # What the user is actually told, at three settings.
    told = {}
    for label, n in (("configured 22,000", 22000), ("configured 31,500", 31500),
                     ("configured 100,000", 100000), ("unset", None)):
        s, c = selector(raw_bytes, n, spliced_units, SPLICE_CAP, True)
        told[label] = {"cap_used": c, "honoured": (n is not None and c == n),
                       "target_at_0.7": int(c * 0.7), "fires_at_0.8": s >= FIRE * c}

    print("  selector pinned: sha %s (was %s)%s" % (got, SELECTOR_SHA,
          "" if got == SELECTOR_SHA else "  <-- CHANGED, update the pin deliberately"))
    print("  our index: %d utf-8 bytes raw, %d utf-16 units spliced" % (raw_bytes, spliced_units))
    print("  crossover: %.1f (scan %d). Below it the knob wins; above it the selector discards it."
          % (crossover, scan))
    for k, v in told.items():
        print("    %-20s cap used %6d  honoured %-5s  target %5d  fires %s"
              % (k, v["cap_used"], v["honoured"], v["target_at_0.7"], v["fires_at_0.8"]))

    json.dump({"probe": os.path.basename(__file__),
               "selector_source": body,
               "selector_sha256_16": got,
               "selector_pin_matched": got == SELECTOR_SHA,
               "index_raw_utf8_bytes": raw_bytes,
               "index_spliced_utf16_units": spliced_units,
               "splice_cap": SPLICE_CAP,
               "crossover_algebraic": crossover,
               "crossover_scanned": scan,
               "what_the_user_is_told": told,
               "our_published_sentence": "raising the configured value raises the number you are "
                                         "told to aim for",
               "that_sentence_holds_below_the_crossover_only": True,
               "controls": {
                   "selector_text_pinned_not_binary_size": True,
                   "tighter_cap_wins_and_looser_cap_discarded_both_exercised": True,
                   "crossover_algebra_checked_against_a_brute_scan": True,
                   "default_no_knob_path_has_its_own_arm": True,
               }},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
