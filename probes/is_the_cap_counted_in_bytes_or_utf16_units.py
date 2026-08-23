"""`MAX_ENTRYPOINT_BYTES` is not bytes. Measured from outside, three ways.

The auto-memory index cap is documented as "the first 25KB", the constant is named
MAX_ENTRYPOINT_BYTES, and the load-time warning prints `(limit: 24.4KB)`. A public mirror
of `src/memdir/memdir.ts` computes the quantity being capped as `const byteCount =
trimmed.length` -- and in JavaScript, `String.prototype.length` is UTF-16 code units.

That distinction is invisible to an ASCII fixture, which is exactly why every measurement
of this cap I had made until now was blind to it: for ASCII, bytes == code points ==
UTF-16 units, so all three hypotheses predict the same cut and the experiment decides
nothing. Three fillers separate them:

  filler      per char:  UTF-8 bytes   code points   UTF-16 units
  ASCII 'x'                    1            1             1
  CJK   '中'                    3            1             1        <- separates bytes from units
  emoji '😀'                    4            1             2        <- separates code points from units

Each arm is 200 lines of a fixed character width, with a canary on EVERY line naming its
own line number, so the cut position is read out of the model's context at single-line
resolution rather than inferred from the file.

  If the cap counts BYTES        the CJK arm (61,600 B) cuts far earlier than the ASCII arm.
  If it counts CODE POINTS       the emoji arm cuts in the same place as the CJK arm.
  If it counts UTF-16 UNITS      CJK cuts with ASCII, and emoji cuts much earlier than both.

A fourth arm (CJK at 60 chars/line) sits under every reading of the cap and must load
whole; it is the negative control that would catch an instrument that truncates for some
reason unrelated to size.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from the_cost_curve_across_the_truncation_boundary import claude_bin  # noqa: E402

ASK = ("Respond with only: LAST=<the last CANARY-Lnnnn token you can see> || "
       "WARNING=<verbatim any line saying your index was truncated or partly loaded; "
       "else NO-INDICATOR>")

CASES = {
    # label            lines  width  filler         what it separates
    "ascii_200x125":   (200, 125, "x"),           # control: all three readings coincide
    "cjk_200x125":     (200, 125, "中"),      # bytes vs units
    "cjk_200x60":      (200, 60, "中"),       # negative control: under the cap either way
    "emoji_200x125":   (200, 125, "\U0001F600"),  # code points vs units
}

# Every store this probe writes into lives under the user's REAL ~/.claude/projects/, because the
# path comes from the CLI's own init event. That is correct, and it is exactly why a fixture is
# indistinguishable from a real memory store to anything walking that directory -- @pjt222 named the
# hazard (pjt222/agent-almanac#407). Measured here 2026-08-23: ours had reached 165 of 168 slug
# directories, 24.5 MB, accumulated over weeks because nothing removed them. A cleanup that is not
# CHECKED is the same defect class this probe studies, so cleanup() re-reads the filesystem and
# reports what survived rather than assuming rmtree worked.
CREATED: list[str] = []


def cleanup(created=None):
    """Remove the fixture stores this run created; return (removed, still_present)."""
    import shutil
    targets = list(CREATED if created is None else created)
    parents = [os.path.dirname(os.path.abspath(t)) for t in targets]
    for parent in parents:
        shutil.rmtree(parent, ignore_errors=True)
    left = [p_ for p_ in parents if os.path.exists(p_)]
    return len(parents) - len(left), left


TRIALS = 3          # see the REPEAT note in main(): one answer per arm is not a measurement
CLAUDE = None
_t0 = time.time()


def log(m: str) -> None:
    print(f"[{time.time() - _t0:6.1f}s] {m}", flush=True)


# An allowlist emptied to nothing, NOT a denylist. Measured 2026-08-23 on 2.1.241:
#   (no flag)                             161 tools, 32 built-in incl. Read, Bash, Glob
#   --tools ""                            129 tools,  0 built-in -- MCP servers survive it
#   --tools "" --strict-mcp-config          0 tools,  0 built-in
#   --disallowedTools Read Bash Glob Grep 156 tools, 27 built-in -- and one of them is Task,
#                                         which spawns a sub-agent holding the full set, so the
#                                         denylist is walked around rather than enforced.
# --tools is variadic and would swallow a positional prompt; ours goes on stdin already.
NO_TOOLS = ["--tools", "", "--strict-mcp-config"]


def run(cwd: str, prompt: str) -> tuple[str | None, str | None, list[str], list[str]]:
    out = subprocess.run([CLAUDE, "-p", "--output-format", "stream-json", "--verbose"] + NO_TOOLS,
                         cwd=cwd, input=prompt, capture_output=True, text=True,
                         encoding="utf-8", errors="replace", timeout=900).stdout or ""
    store = ans = None
    offered: list[str] = []
    used: list[str] = []
    for line in out.splitlines():
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("type") == "system" and d.get("subtype") == "init":
            store = (d.get("memory_paths") or {}).get("auto")
            offered = list(d.get("tools") or [])
        elif d.get("type") == "assistant":
            for blk in ((d.get("message") or {}).get("content") or []):
                if isinstance(blk, dict) and blk.get("type") == "tool_use":
                    used.append(str(blk.get("name")))
        elif d.get("type") == "result":
            ans = str(d.get("result") or "")
    return store, ans, offered, used


def make(n_lines: int, width_chars: int, filler: str) -> str:
    lines = []
    for i in range(1, n_lines + 1):
        head = f"- [E{i:04d}](e-{i:04d}.md) CANARY-L{i:04d} "
        lines.append(head + filler * max(0, width_chars - len(head)))
    return "\n".join(lines) + "\n"


def main() -> int:
    global CLAUDE
    CLAUDE = claude_bin()
    root = tempfile.mkdtemp(prefix="unitprobe_")
    log(f"workspace={root}")
    rows = []
    for label, (n, w, ch) in CASES.items():
        cwd = os.path.join(root, label)
        os.makedirs(cwd, exist_ok=True)
        store, _, offered, _ = run(cwd, "Reply with only: INIT")  # the store is READ, never built
        if offered:
            # Rule 12: a check that cannot see its target reports SAFE. If the environment hands
            # this session ANY tool, the answer below may be a file read and the probe must not
            # pretend otherwise -- refuse rather than measure something else.
            raise SystemExit(f"REFUSED: {len(offered)} tools offered despite {NO_TOOLS}: "
                             f"{offered[:8]} -- the disk-read path is open, so no answer here is "
                             f"evidence about the model's own context")
        if not store:
            rows.append({"label": label, "error": "store not resolved"})
            continue
        text = make(n, w, ch)
        os.makedirs(store, exist_ok=True)
        path = os.path.join(store, "MEMORY.md")
        # BYTES, not text mode. Python text mode rewrites line endings, which silently destroys
        # any arm whose EOL is the variable under test -- @pjt222 pins this in memcap-fixture.py.
        # Ours pinned newline explicitly, which was correct but relied on remembering to; bytes
        # cannot be got wrong by a later edit.
        with open(path, "wb") as f:
            f.write(text.encode("utf-8"))
        CREATED.append(store)
        # REPEAT. One answer per arm is not a measurement: with tools fully disabled a guarded
        # session still fabricated a canary (246, in a 200-line file) in 1 of 9 trials on
        # 2026-08-23 -- see a_probe_with_tools_enabled_can_answer_from_disk.result.json. A single
        # trial cannot tell a read from an invention, so take the mode and record the spread.
        answers, seen, used, offers = [], [], [], []
        for _ in range(TRIALS):
            _, ans_i, offered_i, used_i = run(cwd, ASK)
            used += used_i
            offers.append(len(offered_i))     # every trial, not just the last one
            h_i = (ans_i or "").split("WARNING")[0]
            mi = (re.search(r"LAST\s*=\s*\**\s*CANARY-L(\d{4})", h_i)
                  or re.search(r"CANARY-L(\d{4})", h_i))   # anchored first: a reply that lists
            #   several canaries must not be read by whichever one happens to come first
            answers.append(int(mi.group(1)) if mi else None)
            seen.append(ans_i or "")
        # the mode, tie broken toward the earliest trial
        mode = max((a for a in answers if a is not None),
                   key=lambda x: (answers.count(x), -answers.index(x)), default=None)
        ans = next((s_ for s_, a_ in zip(seen, answers) if a_ == mode), seen[0])
        head = (ans or "").split("WARNING")[0]
        m = (re.search(r"LAST\s*=\s*\**\s*CANARY-L(\d{4})", head)
             or re.search(r"CANARY-L(\d{4})", head))
        row = {
            "label": label, "lines": n, "width_chars": w, "filler_codepoint": ord(ch[0]),
            "bytes": os.path.getsize(path),
            "code_points": len(text),
            "utf16_units": len(text.encode("utf-16-le")) // 2,
            "last_line_loaded": int(m.group(1)) if m else None,
            "warned": "NO-INDICATOR" not in (ans or "").upper(),
            "tools_offered": max(offers),
            "tools_offered_per_trial": offers,
            "tool_uses": used,
            "trials": answers,
            "unanimous": len(set(answers)) == 1 and answers[0] is not None,
            "answer": (ans or "")[:220],
        }
        rows.append(row)
        log(f"  {label:16s} trials={answers} bytes={row['bytes']:7d} cp={row['code_points']:7d} "
            f"u16={row['utf16_units']:7d} warned={row['warned']!s:5s} last={row['last_line_loaded']}")

    by = {r["label"]: r for r in rows if "error" not in r}
    v = {}
    if {"ascii_200x125", "cjk_200x125", "emoji_200x125", "cjk_200x60"} <= set(by):
        a, c, e, n = (by["ascii_200x125"], by["cjk_200x125"],
                      by["emoji_200x125"], by["cjk_200x60"])
        # THE TRAP, and why it needs two independent guards. With tools enabled a `claude -p`
        # probe can answer by READING MEMORY.md off disk instead of reporting its own context,
        # which returns the file's true last line for every arm -- a clean, self-consistent table
        # showing that truncation does not exist. Reported by @pjt222 (pjt222/agent-almanac#407,
        # 2026-08-23), whose first unrestricted batch hit exactly that. The original 2026-08-21
        # batch here did NOT fall into it -- three of four arms returned a line other than the
        # file's last, which a disk read cannot produce -- but that was luck, not design.
        # Guard 1 (by construction): the allowlist above, asserted empty at init.
        # Guard 2 (by observation): no tool_use block anywhere in the stream.
        # Guard 3 (behavioural): kept because it fails independently of both flags above.
        v["every_arm_is_unanimous_across_trials"] = all(r["unanimous"] for r in by.values())
        v["no_tools_were_offered"] = all(r.get("tools_offered") == 0 for r in by.values())
        v["no_tool_was_called"] = all(not r.get("tool_uses") for r in by.values())
        # `any` was the wrong quantifier: three of four arms could have been disk reads and this
        # still passed. The negative control is EXEMPT and cannot help here -- it loads whole, so
        # its correct answer (200) is also exactly what a disk read returns. It can never
        # discriminate, and pretending otherwise is how a control certifies the thing it misses.
        v["every_truncating_arm_reports_a_cut"] = all(
            r["last_line_loaded"] < r["lines"] for r in (a, c, e))
        v["negative_control_loads_whole"] = (n["warned"] is False
                                             and n["last_line_loaded"] == n["lines"])
        v["not_bytes__cjk_cuts_where_ascii_cuts"] = (
            c["last_line_loaded"] == a["last_line_loaded"] and c["bytes"] > 2 * a["bytes"])
        v["not_code_points__emoji_cuts_earlier_at_equal_code_points"] = (
            e["code_points"] == c["code_points"]
            and e["last_line_loaded"] < c["last_line_loaded"])
        # Was: |measured - floor(25000/units_per_line)| <= 3. Two faults, both fatal to its
        # purpose. It ASSUMED the cap is exactly 25,000 -- a documented round number, never a
        # measured one -- and its +/-3 tolerance is wider than the floor/ceil gap of 1, so it
        # passed under either reading and discriminated nothing. What the arms actually support is
        # a BRACKET: under a whole-line rule, every line reported loaded must fit and the next
        # must not. If one interval survives across arms of different widths, a single cap
        # explains them all; the interval, not 25,000, is the measured quantity.
        lo, hi = 0, 10 ** 9
        for r in by.values():
            upl = r["utf16_units"] / r["lines"]
            lo = max(lo, upl * r["last_line_loaded"])
            if r["last_line_loaded"] < r["lines"]:
                hi = min(hi, upl * (r["last_line_loaded"] + 1))
        v["a_single_cap_explains_every_arm"] = lo < hi
        v["that_cap_is_consistent_with_the_documented_25000"] = lo <= 25000 < hi
        cap_bracket = [int(lo), int(hi)]
        v["warning_reports_units_over_1024_not_kb"] = bool(
            re.search(r"is (\d+\.\d+)KB", c["answer"]) and
            abs(float(re.search(r"is (\d+\.\d+)KB", c["answer"]).group(1))
                - c["utf16_units"] / 1024) < 0.6)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "is_the_cap_counted_in_bytes_or_utf16_units.result.json")
    json.dump({"probe": "is_the_cap_counted_in_bytes_or_utf16_units",
               "claude_version": subprocess.run([CLAUDE, "--version"], capture_output=True,
                                                text=True).stdout.strip(),
               "ask": ASK, "cap_bracket_utf16_units": cap_bracket,
               "verdicts": v, "rows": rows},
              open(out, "w", encoding="utf-8"), indent=2)

    print("\n=== ROWS ===")
    print(f"{'arm':16s} {'bytes':>8} {'code pts':>9} {'utf16':>8} {'last line':>10}  warned")
    for r in rows:
        if "error" in r:
            print(f"{r['label']:16s} ERROR {r['error']}")
            continue
        print(f"{r['label']:16s} {r['bytes']:8d} {r['code_points']:9d} {r['utf16_units']:8d} "
              f"{str(r['last_line_loaded']):>10}  {r['warned']}")
    print("\n=== VERDICTS ===")
    for k, val in v.items():
        print(f"  {'YES' if val else 'no '}  {k}")
    removed, left = cleanup()
    print("")
    print(f"  fixture stores removed: {removed}   still present: {len(left)}")
    for t in left:
        print(f"    LEFT BEHIND: {t}")
    v["every_fixture_store_was_removed"] = not left
    log(f"wrote {out}")
    return 0 if all(v.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
