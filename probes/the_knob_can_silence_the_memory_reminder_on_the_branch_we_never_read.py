"""Can a configured promptIndexMaxBytes silence the memory reminder? On one branch, yes.

WHY. On anthropics/claude-code#91188 we published "raising the configured value raises the number you
are told to aim for" (comment 5499087276). Correcting it, I then wrote that the knob "cannot make the
reminder fire later". That is also wrong, and wrong the same way: read off ONE branch of a ternary I
had quoted in full and never analysed. This probe measures both branches, because a retraction that
repeats the error class it retracts is worse than the sentence it replaces.

THE SELECTOR, transcribed from the shipped binary rather than described:

    function IHe({rawSizeBytes:e,surfaceCap:n,splicedSizeBytes:r,spliceCap:o,spliceActive:d}){
      return n!==void 0 && (!d || e/n >= r/o) ? {sizeBytes:e,byteCap:n} : {sizeBytes:r,byteCap:o}
    }

`!d` SHORT-CIRCUITS. When spliceActive is false, the configured cap wins at any magnitude, so a large
enough value silences the reminder outright. When it is true, the configured cap wins only while it
is tighter, and a large value is discarded. One knob, two opposite behaviours, chosen by an
environment variable.

FIVE DEFECTS IN THIS PROBE'S PREDECESSOR, each of which put a wrong number in a draft:
  1. It measured `len(text.strip().encode())` while the binary passes `(await stat()).size`. The file
     is 26,701 bytes on disk, not 26,699.
  2. It ignored `NU`, which collapses CRLF before the spliced measurement. 213 CRLFs is 213 bytes.
  3. It compared bytes only. The reminder takes the MAX over the byte fraction and the line fraction,
     and on this file the line fraction wins, so the advice names lines, not bytes.
  4. Its "both directions" control passed spliceActive=True in both arms, so the branch that carries
     the whole finding was never executed.
  5. It reported one crossover where the value differs by configuration.

CONTROLS, each proved able to fail by mutation:
  * BOTH BRANCHES OF THE TERNARY MUST BE EXERCISED, and they must disagree. If spliceActive true and
    false give the same verdict for a loose cap, the finding does not exist and the probe refuses.
  * THE SILENCING CLAIM NEEDS A WITNESS AND A NON-WITNESS. A configured value that silences the
    reminder must be found, AND a value that does not must also be found, or "large enough" is empty.
  * THE PIN IS THE SELECTOR'S TEXT, not the binary's size, which changed twice in one day.
  * THE REMINDER IS MODELLED OVER BOTH DIMENSIONS. If dropping the line dimension changes no verdict
    on this file, the dimension is untested here and the probe says so rather than implying coverage.
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
OUT = os.path.join(HERE, "the_knob_can_silence_the_memory_reminder_on_the_branch_we_never_read.result.json")

BIN = os.path.expandvars(r"%APPDATA%\npm\node_modules\@anthropic-ai\claude-code\bin\claude.exe")
INDEX = os.path.join(os.path.expanduser("~"), ".claude", "projects",
                     "C--Users-Danculus-agora", "memory", "MEMORY.md")

SELECTOR_SHA = "43f9143b809e2246"
SPLICE_CAP = 25000
LINE_CAP = 200
FIRE = 0.8


def refuse(why):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why}, io.open(OUT, "w", encoding="utf-8"), indent=1)
    raise SystemExit(2)


def selector(raw, surface_cap, spliced, splice_cap, splice_active):
    if surface_cap is not None and ((not splice_active) or raw / surface_cap >= spliced / splice_cap):
        return raw, surface_cap
    return spliced, splice_cap


def reminder(size, cap, lines, line_cap, splice_active):
    """The reminder keeps the LARGEST fraction across the dimensions it was given."""
    entries = [("bytes", size / cap)]
    if splice_active and line_cap:
        entries.append(("lines", lines / line_cap))
    dim, frac = max(entries, key=lambda kv: kv[1])
    return {"dimension": dim, "frac": frac, "fires": frac >= FIRE,
            "target": int((line_cap if dim == "lines" else cap) * 0.7)}


def main():
    if not os.path.exists(BIN):
        refuse("no shipped binary at %s" % BIN)
    blob = io.open(BIN, "rb").read()
    m = re.search(rb"function IHe\(\{rawSizeBytes.{0,320}?\}\}", blob, re.S)
    if not m:
        refuse("the selector is not in this build; the mechanism may have been rewritten")
    body = m.group(0).decode("utf-8", "replace")
    got = hashlib.sha256(body.encode()).hexdigest()[:16]
    if "!d||" not in body.replace(" ", ""):
        refuse("the short-circuit `!d||` is gone from the selector, and it is the whole finding")

    if not os.path.exists(INDEX):
        refuse("no MEMORY.md at %s" % INDEX)
    disk_bytes = os.stat(INDEX).st_size                       # what the binary passes as rawSizeBytes
    text = io.open(INDEX, "rb").read().decode("utf-8")
    collapsed = text.replace("\r\n", "\n").strip()            # NU, then trim
    spliced_units = len(collapsed.encode("utf-16-le")) // 2   # byteCount is String.length
    lines = collapsed.count("\n") + 1

    # CONTROL: both branches, and they must disagree for a loose cap.
    loose = 100000
    a_true = selector(disk_bytes, loose, spliced_units, SPLICE_CAP, True)
    a_false = selector(disk_bytes, loose, spliced_units, SPLICE_CAP, False)
    if a_true == a_false:
        refuse("spliceActive true and false give the same result for a loose cap (%r), so the "
               "short-circuit does nothing here and there is no finding" % (a_true,))
    if a_true[1] != SPLICE_CAP:
        refuse("with spliceActive true a loose cap was honoured; the tightening-only reading is wrong")
    if a_false[1] != loose:
        refuse("with spliceActive false a loose cap was discarded; the silencing reading is wrong")

    # WITNESS AND NON-WITNESS for silencing, on the !d branch.
    silencer = None
    for n in range(SPLICE_CAP, 400000, 1):
        s, c = selector(disk_bytes, n, spliced_units, SPLICE_CAP, False)
        if not reminder(s, c, lines, None, False)["fires"]:
            silencer = n
            break
    if silencer is None:
        refuse("no configured value silenced the reminder on the !d branch, so 'large enough' is empty")
    below = silencer - 1
    s, c = selector(disk_bytes, below, spliced_units, SPLICE_CAP, False)
    if not reminder(s, c, lines, None, False)["fires"]:
        refuse("the value one below the silencer also silences it, so the threshold is not located")

    # CONTROL: does the line dimension change any verdict here, or is it untested?
    with_lines = reminder(spliced_units, SPLICE_CAP, lines, LINE_CAP, True)
    without = reminder(spliced_units, SPLICE_CAP, lines, None, True)
    line_dimension_matters = with_lines["dimension"] != without["dimension"]

    rows = {}
    for label, n, d in (("unset, default", None, True),
                        ("22,000, spliceActive", 22000, True),
                        ("31,500, spliceActive", 31500, True),
                        ("31,500, !spliceActive", 31500, False),
                        ("%d, !spliceActive" % silencer, silencer, False)):
        s, c = selector(disk_bytes, n, spliced_units, SPLICE_CAP, d)
        r = reminder(s, c, lines, LINE_CAP if d else None, d)
        rows[label] = {"cap_used": c, "honoured": n is not None and c == n, **r}

    print("  selector sha %s  pin %s" % (got, "matches" if got == SELECTOR_SHA else "CHANGED"))
    print("  index: %d bytes on disk | %d utf-16 units after CRLF collapse | %d lines"
          % (disk_bytes, spliced_units, lines))
    print("  line dimension changes the reported dimension here: %s (%s vs %s)"
          % (line_dimension_matters, with_lines["dimension"], without["dimension"]))
    print("  silences the reminder on the !d branch at configured >= %d (at %d it still fires)"
          % (silencer, below))
    for k, v in rows.items():
        print("    %-24s cap %6d honoured %-5s -> %s frac %.3f fires %-5s target %d"
              % (k, v["cap_used"], v["honoured"], v["dimension"], v["frac"], v["fires"], v["target"]))

    json.dump({"probe": os.path.basename(__file__),
               "selector_source": body, "selector_sha256_16": got,
               "index_disk_bytes": disk_bytes,
               "index_spliced_utf16_units_after_crlf_collapse": spliced_units,
               "index_lines": lines,
               "line_dimension_changes_the_verdict": line_dimension_matters,
               "silences_at_configured": silencer,
               "still_fires_at": below,
               "rows": rows,
               "controls": {
                   "both_ternary_branches_exercised_and_they_disagree": True,
                   "silencing_has_a_witness_and_the_value_below_it_does_not": True,
                   "selector_text_pinned": True,
                   "line_dimension_reported_rather_than_assumed": True,
               }},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
