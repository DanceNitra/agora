"""A `claude -p` cap probe with tools enabled may answer from the FILE, not from its context.

Reported by @pjt222 (pjt222/agent-almanac#407, 2026-08-23): his first unrestricted batch returned
canary 200 for every arm -- a clean, self-consistent table showing that truncation does not exist.
This reproduces it, locates a trigger, and measures how well the mitigation holds.

The fixture is 200 lines x 125 chars of ASCII, whose cut is known independently:

    context says 198   (floor(25000 / 126 UTF-16 units per line))
    the file says 200  (its actual last line)

so a single number separates "reported its own context" from "opened the file". Three phrasings,
because our own probe escaped the trap on 2026-08-21 and the question is whether that was design.

CONTROL, and it is the whole point: the guarded configuration runs the SAME phrasings and must
never trap. A mitigation measured only where the defect is absent has measured nothing.

DISABLING TOOLS IS NECESSARY AND NOT SUFFICIENT -- the finding that outlives the fix. Measured
across 3 recorded runs, 27 guarded trials, zero tools offered and zero called, on one fixture
whose context answer is 198:

    "the last CANARY token you can SEE"   9/9 correct
    neutral wording                       2/9 correct, 2 impossible, 5 no answer at all
    "the last CANARY token in MEMORY.md"  4/9 correct, 3 impossible, 2 wrong

    15/27 correct overall. Impossible values returned: 214, 242, 246, 248, 250 -- line numbers
    that do not exist in a 200-line file, so no read of any kind produces them.

So `last line loaded` is a SELF-REPORT whose accuracy depends on how it is asked, and closing the
tool path removes one way the instrument lies, not the lying. A one-line disagreement between two
independent measurements of this cap sits well inside that noise. Offered as a reason such a
disagreement cannot be settled by self-report, not as a verdict on anyone's number.

THE DISK-READ TRAP ITSELF: 0/27 under this script, across every run recorded in `runs`. It was
observed firing before this script existed -- ad-hoc runs on the same day returned 200 with `Bash`
and `Read` calls in the stream -- but those runs have NO RECEIPT here and no rate is claimed from
them. Two consequences, and the second is the operational one: the rate is unknown, and a clean
unrestricted batch is therefore not clearance. Close the path; do not inspect it.

The mitigation is an allowlist emptied to zero, NOT a denylist. Measured on 2.1.241:

    (no flag)                             161 tools, 32 built-in incl. Read, Bash, Glob
    --tools ""                            129 tools,  0 built-in -- MCP servers SURVIVE it, so
                                          this is not enough for anyone running a filesystem MCP
    --tools "" --strict-mcp-config          0 tools,  0 built-in
    --disallowedTools Read Bash Glob Grep 156 tools, 27 built-in -- and one is Task, which spawns
                                          a sub-agent holding the full set
"""
import json
import os
import re
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import is_the_cap_counted_in_bytes_or_utf16_units as U  # noqa: E402

TRIALS = 3
CONTEXT_ANSWER, DISK_ANSWER = 198, 200
PHRASINGS = {
    "ours_you_can_see": U.ASK,
    "neutral": "Respond with only: LAST=<the last CANARY-Lnnnn token in your memory index>",
    "names_the_file": "Respond with only: LAST=<the last CANARY-Lnnnn token in MEMORY.md>",
}
_t0 = time.time()


def trial(cwd, prompt):
    _, ans, offered, used = U.run(cwd, prompt)
    m = re.search(r"CANARY-L(\d{4})", (ans or "").split("WARNING")[0])
    return {"last": int(m.group(1)) if m else None, "tools_offered": len(offered), "used": used}


def arm(root, name, no_tools):
    U.NO_TOOLS = no_tools
    cwd = os.path.join(root, name)
    os.makedirs(cwd, exist_ok=True)
    store, _, _, _ = U.run(cwd, "Reply with only: INIT")
    if not store:
        raise SystemExit("REFUSED: store not resolved -- nothing here would be evidence")
    os.makedirs(store, exist_ok=True)
    with open(os.path.join(store, "MEMORY.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(U.make(200, 125, "x"))
    out = []
    for label, prompt in PHRASINGS.items():
        for i in range(TRIALS):
            r = trial(cwd, prompt)
            r.update(arm=name, phrasing=label, trial=i + 1,
                     trapped=(r["last"] == DISK_ANSWER or bool(r["used"])))
            out.append(r)
            print(f"[{time.time() - _t0:6.1f}s]   {name:9s} {label:18s} {i + 1}/{TRIALS} "
                  f"last={r['last']} used={r['used']} trapped={r['trapped']}", flush=True)
    return out


def main():
    U.CLAUDE = U.claude_bin()
    root = tempfile.mkdtemp(prefix="trapprobe_")
    rows = arm(root, "tools_on", []) + arm(root, "guarded", ["--tools", "", "--strict-mcp-config"])
    on = [r for r in rows if r["arm"] == "tools_on"]
    gd = [r for r in rows if r["arm"] == "guarded"]
    ours = [r for r in rows if r["phrasing"] == "ours_you_can_see"]
    v = {
        # THE GUARD -- these must hold in every run, and a red one is a real regression
        "guarded_arm_never_traps": not any(r["trapped"] for r in gd),
        "guarded_arm_offered_zero_tools": all(r["tools_offered"] == 0 for r in gd),
        # NOT "always reports 198". Measured 2026-08-23: one guarded trial answered 246 -- a
        # canary that does not exist in a 200-line file, with zero tools offered and none called.
        # So a guarded session cannot read the file, but it can still INVENT. That is a property of
        # the instrument, not a failure of the guard, and it is why the arms below repeat.
        "guarded_arm_never_reports_the_disk_answer": not any(r["last"] == DISK_ANSWER for r in gd),
        # the phrasing our published measurement uses must be the stable one, or the number it
        # produced was luck. This is the row that protects 198/198/115.
        "our_phrasing_answers_the_context_every_time":
            all(r["last"] == CONTEXT_ANSWER for r in ours),
    }
    # DATA, deliberately not a verdict: the trap is intermittent, so a run where it stays quiet is
    # an observation about this run, not a failure of the probe. Judge it across `runs`.
    data = {"trap_seen_in_this_run": any(r["trapped"] for r in on)}
    by_ph = {}
    for r in on:
        by_ph.setdefault(r["phrasing"], []).append(r["trapped"])

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "a_probe_with_tools_enabled_can_answer_from_disk.result.json")
    prev = []
    if os.path.exists(out):
        try:
            prev = json.load(open(out, encoding="utf-8")).get("runs", [])
        except Exception:
            prev = []
    this_run = {"claude_version": U.subprocess.run([U.CLAUDE, "--version"], capture_output=True,
                                                   text=True).stdout.strip(),
                "trap_rate_tools_on": f"{sum(r['trapped'] for r in on)}/{len(on)}",
                "trap_rate_guarded": f"{sum(r['trapped'] for r in gd)}/{len(gd)}",
                "by_phrasing_tools_on": {p: f"{sum(t)}/{len(t)}" for p, t in by_ph.items()},
                "guarded_answers": {p: [r["last"] for r in gd if r["phrasing"] == p]
                                    for p in PHRASINGS},
                "verdicts": v, "data": data, "rows": rows}
    json.dump({"probe": "a_probe_with_tools_enabled_can_answer_from_disk",
               "claude_version": U.subprocess.run([U.CLAUDE, "--version"], capture_output=True,
                                                  text=True).stdout.strip(),
               "context_answer": CONTEXT_ANSWER, "disk_answer": DISK_ANSWER,
               "trap_rate_tools_on": f"{sum(r['trapped'] for r in on)}/{len(on)}",
               "trap_rate_guarded": f"{sum(r['trapped'] for r in gd)}/{len(gd)}",
               "guarded_context_answer_rate":
                   f"{sum(r['last'] == CONTEXT_ANSWER for r in gd)}/{len(gd)}",
               "guarded_fabricated": [r for r in gd
                                      if r["last"] not in (CONTEXT_ANSWER, DISK_ANSWER)],
               "by_phrasing_tools_on": {p: f"{sum(t)}/{len(t)}" for p, t in by_ph.items()},
               "verdicts": v, "data": data, "rows": rows,
               "runs": prev + [this_run]},
              open(out, "w", encoding="utf-8"), indent=2)
    print("\n=== TRAP RATE ===")
    print(f"  tools on : {sum(r['trapped'] for r in on)}/{len(on)}")
    for p, t in by_ph.items():
        print(f"      {p:18s} {sum(t)}/{len(t)}")
    print(f"  guarded  : {sum(r['trapped'] for r in gd)}/{len(gd)}")
    fab = [r for r in gd if r["last"] not in (CONTEXT_ANSWER, DISK_ANSWER)]
    print(f"  guarded, answered {CONTEXT_ANSWER}: "
          f"{sum(r['last'] == CONTEXT_ANSWER for r in gd)}/{len(gd)}"
          + (f"   FABRICATED: {[r['last'] for r in fab]}" if fab else ""))
    print("\n=== VERDICTS ===")
    for k, val in v.items():
        print(f"  {'YES' if val else 'no '}  {k}")
    print(f"\nwrote {out}")
    return 0 if all(v.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
