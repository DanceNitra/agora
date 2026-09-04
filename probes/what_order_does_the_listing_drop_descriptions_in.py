"""In what ORDER does the skill listing give up descriptions on a real install?

WHY. anthropics/claude-code#81081. @somarakis's reproduction of 2026-08-31 excludes two candidate
rules on the personal tier: not a greedy fill in alphabetical order (his 2nd entry drops, his
longest entry near the end of the alphabet survives) and not a per-description length cap (shortest
dropped 51 chars, longest kept 1,116). He is left with the open half of the question -- what DOES
select the survivors -- and offered to run a measurement.

@bcherny stated the rule on 2026-08-16: on overflow every name is kept and descriptions go
"starting with the least-used skills (in a fresh session with no usage history that degenerates to
listing order)". Our own probe of 2026-08-26 confirmed that on SYNTHETIC skills with a SEEDED
history. Neither measurement has ever been run against a real install, where most skills have never
been invoked at all and are therefore tied.

THIS FILE READS THE DROP ORDER DIRECTLY. `SLASH_COMMAND_TOOL_CHAR_BUDGET` is the documented knob.
Sweeping it downward over one unchanged install and recording, at each step, which names have lost
their description yields the ranking itself rather than an inference about it. The budget at which
a skill first drops IS its rank.

THE OBSERVATION THAT MADE THIS NECESSARY. On this machine, one CLI build, one unchanged set of
files: an interactive session showed four of 77 skills name-only, and a scripted session showed all
77 with descriptions. So the dropped set is not a property of the skills, and no directory diff can
see the variable. The four were `stitch-utilities:stitch-loop`, `stitch-utilities:taste-design`,
`init` and `security-review`. If the sweep drops those four first, it has reproduced the
interactive session's budget from the outside.

WHAT THE FOUR ALREADY RULE OUT, before any sweep, on our own install:
  * NOT LENGTH. `init` at 59 characters is the SHORTEST description of the 77 and it drops, while
    `claude-api` at 1,070 is the longest and survives. That is @somarakis's finding on a second
    tier and a second operating system.
  * NOT LISTING POSITION. Positions 64 and 65 drop while 66 through 75 survive.
  * NOT USAGE COUNT ALONE. All four have no `skillUsage` entry, but so do 54 others that survive.
    58 of the 77 have never been invoked, so on a real install "least-used first" is a rule about a
    large tie, and the tiebreak is the whole question.

READ FROM THE WIRE, NOT FROM THE MODEL. ANTHROPIC_BASE_URL points at a local recorder answering
canned SSE; the listing is read from the request body and no completion is bought.

CONTROLS, each of which can fail, and each REFUSES rather than reporting a number:
  * THE KNOB MUST BITE: the largest budget must drop nothing and the smallest must drop something.
    If both ends agree, the environment variable is not the knob and the sweep measures nothing.
  * MONOTONIC: the dropped set must only grow as the budget shrinks. A name that drops and returns
    means the selection is not a function of the budget, which is itself the finding and is
    reported rather than smoothed.
  * NAMES ARE INVARIANT: all 77 names must be present in every arm. That is the documented
    guarantee, and if names go missing the fixture is exercising something else.
  * PARSER POSITIVE CONTROL: the four stitch-utilities SKILL.md files parse to non-empty
    descriptions on disk before anything is measured.
  * ISOLATION: the real ~/.claude.json must not be written; mtime and size are read either side.
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import time

# A redirected stdout is block-buffered, so a run that prints one line per arm produced a
# ZERO-BYTE file for its whole five minutes and could not be told from a wedged one.
sys.stdout.reconfigure(line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import is_a_skill_truncated_the_way_the_memory_index_is as S
import which_skills_lose_their_description_on_this_install as W

NL = chr(10)
OUT = os.path.join(HERE, "what_order_does_the_listing_drop_descriptions_in.result.json")
START = time.time()
# The four this machine's interactive session delivered name-only, recorded before the sweep ran.
INTERACTIVE_DROPPED = ["stitch-utilities:stitch-loop", "stitch-utilities:taste-design",
                       "init", "security-review"]
# Coarse, then fine around the first-drop boundary, which the coarse pass located between 30,000
# and 24,000. Every budget is run REPS times: a set that moves between runs is noise, and a finding
# built on one run of each would not know the difference.
BUDGETS = [60000, 30000, 27000, 26600, 26500, 26400, 26300, 26200, 26000, 25500, 25000,
           24000, 21000, 18000, 14000, 9000, 3000]
REPS = 3


def refuse(why: str):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why}, io.open(OUT, "w", encoding="utf-8"), indent=1)
    raise SystemExit(2)


def capture(cfg: str, budget: int) -> dict:
    env = dict(os.environ, ANTHROPIC_BASE_URL="http://127.0.0.1:%d" % S.PORT,
               ANTHROPIC_API_KEY="x", CLAUDE_CONFIG_DIR=cfg,
               SLASH_COMMAND_TOOL_CHAR_BUDGET=str(budget))
    S.BODIES.clear()
    p = subprocess.Popen([S.CLAUDE, "-p", "--output-format", "stream-json", "--verbose",
                          "--strict-mcp-config", "Reply with only: OK"],
                         cwd=W.PROJECT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, encoding="utf-8", errors="replace")
    try:
        p.communicate(timeout=420)
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True)
    if not S.BODIES:
        return {}
    return {"wire": W.wire_system_text(S.BODIES[-1]), "model": json.loads(S.BODIES[-1]).get("model") or ""}


def main() -> int:
    disk = W.enumerate_disk()
    names = sorted(disk, key=len, reverse=True)
    for n in W.STITCH:
        recs = disk.get(n) or []
        if not recs or not all(r["description"] for r in recs):
            refuse("parser control: %s did not parse to a non-empty description on disk" % n)

    usage = json.load(io.open(W.REAL_PROFILE, encoding="utf-8")).get("skillUsage") or {}

    def uc0(n):
        e = usage.get(n)
        return (e.get("usageCount") if isinstance(e, dict) else e) or 0
    mt_before = (os.path.getmtime(W.REAL_PROFILE), os.path.getsize(W.REAL_PROFILE))

    cfg = tempfile.mkdtemp(prefix="skilldrop_cfg_")
    srv = S.recorder(S.PORT)
    arms, order, model = [], [], ""
    try:
        W.build_cfg(cfg)
        nondet = []
        for b in BUDGETS:
            reps = []
            for _ in range(REPS):
                cap = capture(cfg, b)
                if not cap:
                    refuse("budget %d produced no request body" % b)
                model = cap["model"]
                lines = W.listing_lines(cap["wire"])
                if len(lines) < 20:
                    refuse("budget %d: listing not found on the wire (%d entries)"
                           % (b, len(lines)))
                ent = []
                for i, ln in enumerate(lines):
                    n, d, _ = W.split_entry(ln, names)
                    ent.append({"pos": i + 1, "name": n, "chars": len(d)})
                reps.append(ent)
            sets = {frozenset(e["name"] for e in r if e["chars"] == 0) for r in reps}
            if len(sets) != 1:
                nondet.append({"budget": b, "distinct_sets": len(sets)})
            entries = reps[0]
            if not arms:
                top_entries = entries
            dropped = [e["name"] for e in entries if e["chars"] == 0]
            kept_chars = sum(e["chars"] for e in entries)
            arms.append({"budget": b, "entries": len(entries), "dropped": len(dropped),
                         "dropped_names": dropped, "delivered_desc_chars": kept_chars,
                         "deterministic_over_%d_runs" % REPS: len(sets) == 1,
                         "positions": {e["name"]: e["pos"] for e in entries}})
            print("budget=%-6d entries=%-4d kept=%-4d dropped=%-4d delivered_chars=%-6d det=%s"
                  % (b, len(entries), len(entries) - len(dropped), len(dropped), kept_chars,
                     len(sets) == 1))
    finally:
        srv.shutdown()
    mt_after = (os.path.getmtime(W.REAL_PROFILE), os.path.getsize(W.REAL_PROFILE))

    # --- controls -------------------------------------------------------------
    if arms[0]["dropped"] != 0:
        refuse("the top budget %d already drops %d: no unconstrained baseline"
               % (arms[0]["budget"], arms[0]["dropped"]))
    if arms[-1]["dropped"] == 0:
        refuse("the bottom budget %d drops nothing: SLASH_COMMAND_TOOL_CHAR_BUDGET is not the knob"
               % arms[-1]["budget"])
    n_entries = {a["entries"] for a in arms}
    if len(n_entries) != 1:
        refuse("the listing changed length across arms: %s -- names are supposed to be invariant"
               % sorted(n_entries))
    non_monotone = []
    for i in range(1, len(arms)):
        gone = set(arms[i - 1]["dropped_names"]) - set(arms[i]["dropped_names"])
        if gone:
            non_monotone.append({"from_budget": arms[i - 1]["budget"],
                                 "to_budget": arms[i]["budget"], "returned": sorted(gone)})

    # --- the baseline table, from the unconstrained arm ---
    baseline_table = [{"pos": e["pos"], "name": e["name"], "desc_chars": e["chars"],
                       "usage_count": uc0(e["name"]),
                       "on_disk": e["name"] in disk,
                       "ever_drops": None}
                      for e in top_entries]
    rendered_chars = sum(len(e["name"]) + (2 if e["chars"] else 0) + e["chars"] + 3
                         for e in top_entries)

    # --- the ranking: the budget at which each name first loses its description ---
    first_drop = {}
    for a in arms:
        for n in a["dropped_names"]:
            first_drop.setdefault(n, a["budget"])
    order = sorted(first_drop, key=lambda n: (-first_drop[n], arms[0]["positions"].get(n, 0)))

    def uc(n):
        e = usage.get(n)
        return (e.get("usageCount") if isinstance(e, dict) else e) or 0

    ranked = [{"rank": i + 1, "name": n, "drops_at_budget": first_drop[n],
               "listing_pos": arms[0]["positions"].get(n),
               "usage_count": uc(n),
               "desc_chars_on_wire": next((e for a in arms for e in [None]), None)}
              for i, n in enumerate(order)]
    for r in ranked:
        r.pop("desc_chars_on_wire", None)

    for row in baseline_table:
        row["ever_drops"] = row["name"] in first_drop
        row["drops_at_budget"] = first_drop.get(row["name"])

    first4 = [r["name"] for r in ranked[:4]]
    reproduces = first4 == INTERACTIVE_DROPPED or set(first4) == set(INTERACTIVE_DROPPED)

    res = {
        "probe": os.path.basename(__file__),
        "when_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "claude_version": subprocess.run([S.CLAUDE, "--version"], capture_output=True,
                                         text=True).stdout.strip(),
        "platform": sys.platform, "model_on_wire": model,
        "method": "SLASH_COMMAND_TOOL_CHAR_BUDGET swept downward over one unchanged install; the "
                  "listing is read from the request body; zero completions bought",
        "listing_entries": arms[0]["entries"],
        "skills_with_usage_history": sum(1 for n in arms[0]["positions"] if uc(n) > 0),
        "skills_never_invoked": sum(1 for n in arms[0]["positions"] if uc(n) == 0),
        # THE BASELINE TABLE, so no per-entry figure quoted anywhere rests on a scratch script.
        # A verifier found two numbers in a draft (a rendered-listing total, and one skill's
        # description length) that appeared in no receipt at all. Both were real; neither was
        # checkable. Anything a reader might want to confirm belongs here.
        "baseline_table": baseline_table,
        "baseline_rendered_listing_chars": rendered_chars,
        "baseline_description_chars": arms[0]["delivered_desc_chars"],
        "sweep": [{k: v for k, v in a.items() if k != "positions"} for a in arms],
        "drop_ranking": ranked,
        "interactive_session_dropped": INTERACTIVE_DROPPED,
        "interactive_session_caveat": (
            "READ THIS BEFORE USING THE TWO FIELDS BELOW. The interactive set was read from a "
            "session's own prompt, which is the model reporting what it can see; every other "
            "number in this file is read from the request body. The two sides are also not the "
            "same listing: the interactive one carries five entries this one does not. So a "
            "mismatch here is expected and is NOT evidence about the selection rule."),
        "sweep_first_four": first4,
        "sweep_reproduces_interactive_session": reproduces,
        "controls": {
            "knob_bites": True,
            "reps_per_budget": REPS,
            "every_budget_deterministic": not nondet,
            "non_deterministic_budgets": nondet,
            "top_budget_drops_nothing": arms[0]["dropped"] == 0,
            "bottom_budget_drops": arms[-1]["dropped"],
            "names_invariant_across_arms": len(n_entries) == 1,
            "monotone": not non_monotone,
            "non_monotone_steps": non_monotone,
            "parser_positive_control": "PASS",
            "real_profile_untouched": mt_before == mt_after,
        },
        "elapsed_s": round(time.time() - START, 1),
    }
    json.dump(res, io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(NL + "drop ranking (earliest to go last):")
    for r in ranked[:25]:
        print("  %2d. %-40s drops_at=%-6d pos=%-3s usage=%d"
              % (r["rank"], r["name"], r["drops_at_budget"], r["listing_pos"], r["usage_count"]))
    print(NL + "first four to go: %s" % first4)
    print("interactive session dropped: %s" % INTERACTIVE_DROPPED)
    print("reproduces: %s" % reproduces)
    print(NL + "MONOTONE IN THE BUDGET: %s" % (not non_monotone))
    for step in non_monotone:
        print("  budget %d -> %d  RESTORED: %s"
              % (step["from_budget"], step["to_budget"], ", ".join(step["returned"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
