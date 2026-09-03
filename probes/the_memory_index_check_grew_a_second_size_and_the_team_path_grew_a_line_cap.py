"""What does the memory-index reminder actually measure, on the build shipping today?

WHY. On anthropics/claude-code#91188 @tonydzi read CLI 2.1.202 on macOS and reported three things:
`sizeBytes` is fed by `n.length` on the personal path and `stat().size` on the team path, so one
field carries two different quantities; `promptIndexMaxBytes` never reaches the personal path; and
the team path passes no `lineCap`, so a team index is judged on bytes alone. Those were true of the
build he read. This reads the build shipping now and reports what changed, because a finding about a
vendor's internal shape goes stale without an announcement, and we have been burned by that before.

WHAT THIS FOUND, and the point of the probe is that all of it is re-runnable:
  * Both memory-index call sites now push the SAME shape, and it carries TWO size dimensions rather
    than one: rawSizeBytes against surfaceCap, and splicedSizeBytes against spliceCap.
  * The team path DOES pass a lineCap, conditionally. @tonydzi's third finding does not reproduce
    here.
  * `sizeBytes` still exists elsewhere in the binary with many different sources (`.length`, `.size`,
    `.bytes`, literals), so the class he identified is real and wider than the two sites he read.

CONTROLS, because every expensive day here has been an instrument that could not see its target:
  * A POSITIVE CONTROL ON THE READER. `strings` returns ZERO for "MEMORY.md" on this binary, which
    is present: the tool is blind to it. Any search here must first find a known-present needle, or
    the run is void. This control is not decoration; it caught exactly that, live.
  * A DELIMITER CONTROL, and it exists because it caught me twice. Reading the site with a
    brace-stopping pattern (`[^}]{0,220}`) reports NO lineCap at either site; reading the same
    bytes with a fixed-width window finds it at both. The `}` closing the inner call truncates the
    match before the field. So the probe runs BOTH readers and refuses unless they disagree,
    because if they ever agree the lesson is untested and the control is decoration. My first two
    attempts put this control on the wrong field and on the wrong axis, and both times it refused
    its own run rather than reporting a number.
  * PIN THE BUILD. The version and byte size are recorded in the receipt. A claim about a minified
    identifier is worthless without them, and this binary changed under us twice in one day.
  * NAME-INDEPENDENCE. The probe asserts on FIELD NAMES that are semantic (`rawSizeBytes`,
    `spliceCap`, `lineCap`), never on minified locals, because those differ per build and per
    platform. Where a local is quoted it is reported as build-local.
"""
from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "the_memory_index_check_grew_a_second_size_and_the_team_path_grew_a_line_cap.result.json")

BIN = os.path.expandvars(
    r"%APPDATA%\npm\node_modules\@anthropic-ai\claude-code\bin\claude.exe")
INDEX = os.path.join(os.path.expanduser("~"), ".claude", "projects",
                     "C--Users-Danculus-agora", "memory", "MEMORY.md")

NEEDLE = b'label:"memory index"'
KNOWN_PRESENT = b"MEMORY.md"          # the positive control for the reader
BYTE_CAP = 25000
LINE_CAP = 200
FIRE = 0.8


def refuse(why):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why}, io.open(OUT, "w", encoding="utf-8"), indent=1)
    raise SystemExit(2)


def cli_version():
    try:
        out = subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=60)
        return (out.stdout or "").strip().split()[0]
    except Exception:                                # noqa: BLE001
        return "unknown"


def main():
    if not os.path.exists(BIN):
        refuse("no shipped binary at %s; this probe reads the product, not a description of it" % BIN)
    blob = io.open(BIN, "rb").read()

    # CONTROL 1: the reader must find something we know is there. `strings` fails this.
    if KNOWN_PRESENT not in blob:
        refuse("the positive control needle %r is absent, so the reader is blind and every negative "
               "below is void" % KNOWN_PRESENT)
    strings_blind = False
    try:
        s = subprocess.run(["strings", "-n", "4", BIN], capture_output=True, timeout=600)
        strings_blind = (KNOWN_PRESENT not in (s.stdout or b""))
    except Exception:                                # noqa: BLE001
        strings_blind = None

    # CONTROL 2: two readers over the SAME bytes. A brace-stopping pattern is what made me report
    # "no lineCap" at both sites; a fixed-width window finds it. They must disagree, or this control
    # is decoration and its lesson is untested.
    WINDOW = 400
    sites = [m.group(0) for m in re.finditer(re.escape(NEEDLE) + b".{0,%d}" % WINDOW, blob, re.S)]
    brace = [m.group(0) for m in re.finditer(re.escape(NEEDLE) + b"[^}]{0,%d}" % WINDOW, blob, re.S)]
    if not sites:
        refuse("no memory-index call site found at all; the needle %r is stale" % NEEDLE)
    fixed_sees = sum(1 for f in sites if b"lineCap" in f)
    brace_sees = sum(1 for f in brace if b"lineCap" in f)
    if fixed_sees == brace_sees:
        refuse("both readers agree (%d vs %d sites see lineCap), so the delimiter control cannot "
               "fire here and reporting it as a caught defect would be false"
               % (fixed_sees, brace_sees))
    if fixed_sees == 0:
        refuse("even the fixed-width reader finds no lineCap; the field is gone and the finding "
               "must be rewritten rather than reported")

    parsed = []
    for f in sites:
        t = f.decode("utf-8", "replace")
        parsed.append({
            "is_team_path": "team/" in t,
            "has_rawSizeBytes": "rawSizeBytes" in t,
            "has_surfaceCap": "surfaceCap" in t,
            "has_splicedSizeBytes": "splicedSizeBytes" in t,
            "has_spliceCap": "spliceCap" in t,
            "has_lineCap": "lineCap" in t,
            "has_legacy_sizeBytes_field": bool(re.search(r"\bsizeBytes:", t)),
            "has_legacy_byteCap_field": bool(re.search(r"\bbyteCap:", t)),
        })
    team = [p for p in parsed if p["is_team_path"]]
    personal = [p for p in parsed if not p["is_team_path"]]
    if not team or not personal:
        refuse("expected both a personal and a team memory-index site; found %d personal, %d team"
               % (len(personal), len(team)))

    # The three claims, each stated so it can come out false.
    both_two_sizes = all(p["has_rawSizeBytes"] and p["has_splicedSizeBytes"] for p in parsed)
    team_has_linecap = all(p["has_lineCap"] for p in team)
    legacy_gone = not any(p["has_legacy_sizeBytes_field"] or p["has_legacy_byteCap_field"]
                          for p in parsed)

    # CONTROL 3: the wider class he named is real elsewhere, or our "wider than two" claim is empty.
    sources = sorted(set(m.group(1).decode() for m in
                         re.finditer(rb"sizeBytes:([^,}]{1,30})", blob)))
    if len(sources) < 3:
        refuse("only %d distinct sizeBytes sources found, so the claim that one field carries many "
               "quantities is not supported here: %s" % (len(sources), sources))

    # Our own index on every axis, as a second data point beside his.
    idx = {}
    if os.path.exists(INDEX):
        raw = io.open(INDEX, "rb").read()
        txt = raw.decode("utf-8").strip()
        idx = {
            "disk_bytes": len(raw),
            "trimmed_utf8_bytes": len(txt.encode("utf-8")),
            "trimmed_utf16_units": len(txt.encode("utf-16-le")) // 2,
            "lines": txt.count("\n") + 1,
            "non_ascii_chars": sum(1 for c in txt if ord(c) > 127),
        }
        idx["frac_utf8_bytes"] = round(idx["trimmed_utf8_bytes"] / BYTE_CAP, 4)
        idx["frac_utf16_units"] = round(idx["trimmed_utf16_units"] / BYTE_CAP, 4)
        idx["frac_lines"] = round(idx["lines"] / LINE_CAP, 4)
        idx["binding_axis"] = max(("utf8_bytes", idx["frac_utf8_bytes"]),
                                  ("utf16_units", idx["frac_utf16_units"]),
                                  ("lines", idx["frac_lines"]), key=lambda kv: kv[1])[0]
        idx["would_fire_at_0.8"] = max(idx["frac_utf8_bytes"], idx["frac_utf16_units"],
                                       idx["frac_lines"]) >= FIRE

    ver = cli_version()
    print("  binary %s  %d bytes  cli %s" % (os.path.basename(BIN), len(blob), ver))
    print("  reader control: `strings` blind to %s = %s (grep finds it)" % (KNOWN_PRESENT.decode(), strings_blind))
    print("  delimiter control: fixed-width reader sees lineCap at %d sites, brace-stopping reader "
          "at %d -- the truncation that fooled me" % (fixed_sees, brace_sees))
    print("  memory-index sites: %d personal, %d team" % (len(personal), len(team)))
    print("  both sites carry TWO size dimensions (raw + spliced): %s" % both_two_sizes)
    print("  team site passes a lineCap: %s" % team_has_linecap)
    print("  legacy sizeBytes/byteCap fields on these sites: %s" % ("gone" if legacy_gone else "still there"))
    print("  distinct sizeBytes sources elsewhere in the binary: %d  %s" % (len(sources), sources[:8]))
    if idx:
        print("  our index: %d disk bytes | %d utf8 | %d utf16 units | %d lines | %d non-ASCII"
              % (idx["disk_bytes"], idx["trimmed_utf8_bytes"], idx["trimmed_utf16_units"],
                 idx["lines"], idx["non_ascii_chars"]))
        print("  fractions: utf8 %.3f | utf16 %.3f | lines %.3f -> binding %s, fires at 0.8: %s"
              % (idx["frac_utf8_bytes"], idx["frac_utf16_units"], idx["frac_lines"],
                 idx["binding_axis"], idx["would_fire_at_0.8"]))

    json.dump({"probe": os.path.basename(__file__),
               "binary_bytes": len(blob), "cli_version": ver,
               "reader_positive_control_passed": True,
               "strings_is_blind_to_a_present_needle": strings_blind,
               "lineCap_sites_seen_by_fixed_width_reader": fixed_sees,
               "lineCap_sites_seen_by_brace_stopping_reader": brace_sees,
               "sites": parsed,
               "both_sites_have_two_size_dimensions": both_two_sizes,
               "team_site_passes_a_line_cap": team_has_linecap,
               "legacy_sizeBytes_byteCap_gone_from_these_sites": legacy_gone,
               "distinct_sizeBytes_sources_in_binary": sources,
               "our_index": idx,
               "controls": {
                   "reader_proved_able_to_find_a_known_needle": True,
                   "two_readers_disagree_so_the_delimiter_lesson_is_tested": True,
                   "assertions_on_semantic_field_names_not_minified_locals": True,
                   "build_pinned_by_version_and_size": True,
               }},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
