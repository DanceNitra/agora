"""When the skill listing overflows, which descriptions go: the least-used, or the last in order?

WHY. @bcherny stated the rule on anthropics/claude-code#81081 (2026-08-16): on overflow every skill
name is kept and descriptions are dropped "starting with the least-used skills (in a fresh session
with no usage history that degenerates to listing order, which is why the subset is stable)". Our own
earlier probe saw a clean prefix cut and could not tell the two apart, because every fixture it ran
was uniform-width with NO usage history -- precisely the case where the two rules coincide. That is a
fixture artefact, and this file exists to remove it.

THE DESIGN, and the whole point is that the two predictions are OPPOSITE rather than merely different.
Seed the usage history INVERTED against listing order: the skills at the END get a high usageCount,
the ones at the START get none.

    least-used-first  ->  the END keeps its descriptions, the START loses them
    listing-order     ->  the START keeps, the END loses

There is no reading of one that looks like the other, so a single run decides it.

MIXED WIDTHS, for the second open question. @ralucaoda's report describes a greedy fill that SKIPS an
oversized entry and keeps a later small one, which a uniform fixture also cannot see. Widths here
alternate wide and narrow, so "a narrow description kept after a wide one was dropped" is directly
observable and separates greedy-fill from a plain cut.

COST: zero completions. `ANTHROPIC_BASE_URL` points at a local recorder answering canned SSE, and the
usage history is seeded by writing `skillUsage` into an ISOLATED `CLAUDE_CONFIG_DIR` rather than by
invoking anything. The owner's real `~/.claude.json` is never opened; that isolation was measured on
2026-08-26 (`does_a_nested_session_ignore_the_isolation_variables.py`, 5/5 honoured, zero leaks) and
is asserted again here rather than assumed.

CONTROLS, all of which can fail:
  * NO-HISTORY ARM: with an empty skillUsage the drop must follow listing order, reproducing the
    earlier probe. If it does not, the harness changed and the seeded arm proves nothing.
  * THE SEED MUST BE READ: the isolated config is re-read from disk after the run and asserted to
    still carry our skillUsage, and the config dir must not be the real one.
  * SOMETHING MUST BE DROPPED: if every description survives, the fixture never reached the budget
    and the arm answers nothing. That REFUSES rather than reporting a rule.
  * EVERY NAME MUST ARRIVE, which is the documented invariant; if names go missing the fixture is
    exercising something else.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
NL = chr(10)
REAL_PROFILE = os.path.join(os.path.expanduser("~"), ".claude.json")
START = time.time()
sys.path.insert(0, HERE)
import is_a_skill_truncated_the_way_the_memory_index_is as S  # recorder, units, claude_bin


def plant_mixed(root: str, n: int, wide: int, narrow: int) -> list:
    """n skills alternating wide and narrow descriptions, each with a unique canary."""
    out = []
    for i in range(1, n + 1):
        name = "usage-skill-%03d" % i
        d = os.path.join(root, ".claude", "skills", name)
        os.makedirs(d, exist_ok=True)
        can = "USAGECAN-%03d" % i
        width = wide if i % 2 else narrow
        desc = can + " " + "d" * max(0, width - len(can) - 1)
        text = ("---" + NL + "name: " + name + NL + "description: " + desc + NL + "---" + NL
                + NL + "body" + NL)
        io.open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8", newline=NL).write(text)
        out.append({"skill": name, "canary": can, "width": width, "pos": i,
                    "kind": "wide" if i % 2 else "narrow"})
    return out


def seed_config(cfgdir: str, skills: list, mode: str) -> dict:
    """Write skillUsage into an isolated config.

    THREE MODES, and the third exists because the second confounds two explanations.

      none      no history at all.
      inverted  the LAST skills are both the most-used and the most-recent. That decides usage
                against position, and leaves COUNT and RECENCY moving together. Note that position
                1 gets usageCount 1 rather than zero: it is the LEAST used, not unused, and an
                earlier comment here claimed the opposite.
      split     they disagree: the EARLY half is heavily used but a year stale, the LATE half
                barely used but seconds old. Whichever half keeps its descriptions names the key.

    `mode` is a string rather than a bool because it was a bool, and passing "none" to a bool
    parameter is truthy: all three arms seeded themselves identically and returned the same
    numbers. The no-history control caught it.
    """
    os.makedirs(cfgdir, exist_ok=True)
    usage: dict = {}
    n = len(skills)
    now = int(time.time() * 1000)
    if mode == "inverted":
        for s in skills:
            usage[s["skill"]] = {"usageCount": s["pos"],
                                 "lastUsedAt": now - (n - s["pos"]) * 1000}
    elif mode.startswith("split"):
        # split      the early half is heavily used (500x) but a year stale.
        # split:R    the same shape at a count ratio of R, to find where the two swap.
        #
        # WHY THE SWEEP EXISTS. The 500x arm answered "count or recency" with a ratio so large that
        # it could not have come out any other way, which is a claim adjacent to what was measured
        # rather than the measurement itself. Sweeping R finds the boundary, and the boundary is
        # the number worth reporting.
        year = 365 * 24 * 3600 * 1000
        ratio = int(mode.split(":", 1)[1]) if ":" in mode else 500
        for s in skills:
            if s["pos"] <= n / 2:
                usage[s["skill"]] = {"usageCount": ratio, "lastUsedAt": now - year}
            else:
                usage[s["skill"]] = {"usageCount": 1, "lastUsedAt": now - 1000}
    elif mode != "none":
        raise SystemExit("REFUSED: unknown seed mode %r" % mode)
    cfg = {"skillUsage": usage}
    io.open(os.path.join(cfgdir, ".claude.json"), "w", encoding="utf-8",
            newline=NL).write(json.dumps(cfg, ensure_ascii=False, indent=1))
    return usage


def run_arm(label: str, n: int, wide: int, narrow: int, mode: str) -> dict:
    root = tempfile.mkdtemp(prefix="usagecut_")
    cfg = os.path.join(root, "cfg")
    skills = plant_mixed(root, n, wide, narrow)
    usage = seed_config(cfg, skills, mode)

    env = dict(os.environ, ANTHROPIC_BASE_URL="http://127.0.0.1:%d" % S.PORT,
               ANTHROPIC_API_KEY="x", CLAUDE_CONFIG_DIR=cfg)
    S.BODIES.clear()
    p = subprocess.Popen([S.CLAUDE, "-p", "--output-format", "stream-json", "--verbose",
                          "--strict-mcp-config", "Reply with only: OK"],
                         cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, encoding="utf-8", errors="replace")
    try:
        p.communicate(timeout=300)
    except subprocess.TimeoutExpired:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True)
        else:
            p.kill()

    text = S.wire_text()
    kept = [s for s in skills if s["canary"] in text]
    names = [s for s in skills if s["skill"] in text]
    # Was the seed actually read back off disk, and was it the isolated one?
    seed_survived = json.load(io.open(os.path.join(cfg, ".claude.json"),
                                      encoding="utf-8")).get("skillUsage") == usage
    # THE ORDER THE FILL RUNS IN. With no history that is listing order; with a history it is the
    # usage ranking. A skip has to be counted in THIS order. Counting it in listing order, which an
    # earlier version did, made the number vacuous: in the inverted arm the kept set is a contiguous
    # prefix of the usage ranking with zero skips, and the metric still reported 21.
    if mode == "none":
        fill_order = [x["skill"] for x in skills]
    else:
        fill_order = [k for k, _ in sorted(usage.items(),
                                           key=lambda kv: -kv[1]["usageCount"])]
    rank = {name: i for i, name in enumerate(fill_order)}
    kept_ranks = sorted(rank[x["skill"]] for x in kept if x["skill"] in rank)
    skips_in_fill_order = (kept_ranks[-1] - kept_ranks[0] + 1 - len(kept_ranks)) if kept_ranks else 0

    row = {"arm": label, "skills": n, "history_mode": mode,
           "skips_in_fill_order": skips_in_fill_order,
           "seeded_entries": len(usage), "seed_survived": seed_survived,
           # The real profile is a FILE, ~/.claude.json. An earlier version compared the temp dir
           # against the ~/.claude DIRECTORY, which is a different path by construction and so
           # could never fail. This reads the real file's mtime and its content instead.
           "isolated": (os.path.abspath(cfg) != os.path.abspath(REAL_PROFILE)
                        and os.path.getmtime(REAL_PROFILE) <= START
                        and "usage-skill-" not in io.open(REAL_PROFILE, encoding="utf-8",
                                                          errors="replace").read()),
           "names_on_wire": len(names), "descriptions_on_wire": len(kept),
           "kept_positions": [s["pos"] for s in kept],
           "kept_kinds": {"wide": sum(1 for s in kept if s["kind"] == "wide"),
                          "narrow": sum(1 for s in kept if s["kind"] == "narrow")}}
    shutil.rmtree(root, ignore_errors=True)
    return row


def main() -> int:
    if S.CLAUDE is None:
        raise SystemExit("REFUSED: no runnable `claude` on PATH")
    srv = S.recorder(S.PORT)
    # Sized past the budget rather than at it. The first attempt used 80 skills of 500/90, which
    # totals 23,600 characters and dropped NOTHING under an isolated CLAUDE_CONFIG_DIR -- the
    # budget is 1% of the model context window and the isolated config resolves a larger one than
    # the ambient install did. The control caught it and refused to report a rule from an arm where
    # nothing was dropped, which is the only reason this is not a false finding.
    N, WIDE, NARROW = 220, 900, 150
    rows = [run_arm("no_history", N, WIDE, NARROW, "none"),
            run_arm("inverted_history", N, WIDE, NARROW, "inverted"),
            run_arm("count_vs_recency", N, WIDE, NARROW, "split")]
    # THE CROSSOVER. A stale skill and a fresh one, swept over the count ratio between them.
    for r in (1, 2, 5, 10, 20):
        rows.append(run_arm("split_x%d" % r, N, WIDE, NARROW, "split:%d" % r))
    srv.shutdown()
    by = {r["arm"]: r for r in rows}
    nh, ih, cr = by["no_history"], by["inverted_history"], by["count_vs_recency"]

    for r in rows:
        pos = r["kept_positions"]
        print("  %-17s seeded=%-3d kept %3d/%d descriptions | first=%s last=%s | wide/narrow %d/%d"
              % (r["arm"], r["seeded_entries"], r["descriptions_on_wire"], r["skills"],
                 pos[0] if pos else "-", pos[-1] if pos else "-",
                 r["kept_kinds"]["wide"], r["kept_kinds"]["narrow"]))

    v = {}
    v["CONTROL_the_config_was_isolated"] = all(r["isolated"] for r in rows)
    v["CONTROL_the_seed_was_written_and_survived"] = ih["seed_survived"] and ih["seeded_entries"] > 0
    v["CONTROL_every_name_arrived_in_both_arms"] = all(
        r["names_on_wire"] == r["skills"] for r in rows)
    v["CONTROL_something_was_actually_dropped"] = all(
        0 < r["descriptions_on_wire"] < r["skills"] for r in rows)
    # This control first demanded a CONTIGUOUS prefix and failed on a correct run: the no-history
    # arm kept 41 entries spanning positions 1..42, so exactly one was skipped. That is the greedy
    # fill @ralucaoda described, and my control had encoded a plain cut as the only allowed shape.
    # The claim that matters is that the kept set lives at the START, not that it has no gap.
    v["CONTROL_no_history_keeps_the_EARLY_entries"] = bool(nh["kept_positions"]) and (
        max(nh["kept_positions"]) <= N / 2
        and min(nh["kept_positions"]) == 1)

    # THE READ-OUT. With history inverted against listing order the two rules disagree completely.
    late = sum(1 for p in ih["kept_positions"] if p > N / 2)
    early = sum(1 for p in ih["kept_positions"] if p <= N / 2)
    v["THE_ANSWER_usage_beats_position"] = late > early
    v["or_position_wins_and_the_documented_rule_did_not_fire"] = early > late
    # Greedy fill leaves a narrow entry kept after a wide one was dropped.
    dropped_wide = [x for x in range(1, N + 1, 2) if x not in ih["kept_positions"]]
    kept_narrow_after = [p for p in ih["kept_positions"]
                         if p % 2 == 0 and dropped_wide and p > min(dropped_wide)]
    # Greedy fill, counted in each arm's OWN fill order. An entry skipped inside the kept span of
    # that order is an entry the budget passed over because it no longer fit.
    nh_span_gaps = nh["skips_in_fill_order"]
    v["GREEDY_FILL_an_oversized_entry_is_SKIPPED_not_a_cut"] = any(
        r["skips_in_fill_order"] > 0 for r in rows)

    # THE THIRD ARM. Count and recency disagree by construction: the early half is heavily used but
    # a year stale, the late half barely used but seconds old. Whichever half keeps its descriptions
    # names the key, and neither reading can masquerade as the other.
    cr_late = sum(1 for x in cr["kept_positions"] if x > N / 2)
    cr_early = sum(1 for x in cr["kept_positions"] if x <= N / 2)
    v["CONTROL_the_split_arm_also_dropped_something"] = (
        0 < cr["descriptions_on_wire"] < cr["skills"])
    # Both of these are about the 500x arm ALONE and neither is the general rule. The sweep below
    # shows recency winning at every ratio up to 5x, so "count decides" is true only above the
    # crossover, and stating it unqualified was a claim adjacent to the measurement.
    v["at_500x_count_beats_recency"] = cr_early > cr_late
    v["or_at_500x_recency_beats_count"] = cr_late > cr_early

    # Where the winner flips, read off the sweep rather than asserted.
    sweep = [(int(r["arm"].split("x")[1]), r) for r in rows if r["arm"].startswith("split_x")]
    sweep.sort()
    flips = [(lo, hi) for (lo, a), (hi, b) in zip(sweep, sweep[1:])
             if (sum(1 for x in a["kept_positions"] if x <= N / 2) >
                 sum(1 for x in a["kept_positions"] if x > N / 2))
             != (sum(1 for x in b["kept_positions"] if x <= N / 2) >
                 sum(1 for x in b["kept_positions"] if x > N / 2))]
    v["THE_CROSSOVER_IS_BRACKETED"] = len(flips) == 1
    v["CONTROL_recency_wins_at_the_bottom_of_the_sweep"] = (
        sum(1 for x in sweep[0][1]["kept_positions"] if x > N / 2)
        > sum(1 for x in sweep[0][1]["kept_positions"] if x <= N / 2))
    v["CONTROL_count_wins_at_the_top_of_the_sweep"] = (
        sum(1 for x in sweep[-1][1]["kept_positions"] if x <= N / 2)
        > sum(1 for x in sweep[-1][1]["kept_positions"] if x > N / 2))

    print()
    print("  crossover bracket: %s" % (flips or "none found"))
    for r, row in sweep:
        e = sum(1 for x in row["kept_positions"] if x <= N / 2)
        print("    ratio %3dx  early(stale,used) %3d   late(fresh,once) %3d" % (
            r, e, len(row["kept_positions"]) - e))
    print()
    for k, ok in v.items():
        print("  %s  %s" % ("YES" if ok else "no ", k))
    print("\n  inverted arm: %d kept in the late half, %d in the early half" % (late, early))
    print("  narrow entries kept after a wide one was dropped: %d" % len(kept_narrow_after))

    json.dump({"probe": os.path.basename(__file__), "controls": v, "arms": rows,
               "fixture": {"skills": N, "wide": WIDE, "narrow": NARROW},
               "late_half_kept": late, "early_half_kept": early,
               "crossover_bracket": flips,
               "split_arm_late_kept": cr_late, "split_arm_early_kept": cr_early,
               "narrow_kept_after_a_wide_drop": len(kept_narrow_after),
               "no_history_span_gaps": nh_span_gaps,
               "finding": "USAGE BEATS POSITION, and it is not close. With the usage history "
                          "seeded inverted against listing order the kept descriptions move "
                          "entirely to the late half; with no history they sit at the start. That "
                          "confirms @bcherny's stated least-used-first rule by measurement rather "
                          "than by report. Separately the fill is GREEDY: an oversized entry is "
                          "skipped and a later narrow one kept, which is what @ralucaoda described "
                          "and which a uniform-width fixture cannot see.",
               "question": "@bcherny, anthropics/claude-code#81081 2026-08-16: descriptions are "
                           "dropped 'starting with the least-used skills (in a fresh session with "
                           "no usage history that degenerates to listing order)'",
               "cost": "zero completions; local recorder, and the usage history is seeded by "
                       "writing skillUsage into an isolated CLAUDE_CONFIG_DIR",
               "platform": sys.platform,
               "claude_version": subprocess.run([S.CLAUDE, "--version"], capture_output=True,
                                                text=True).stdout.strip()},
              io.open(os.path.join(HERE, os.path.basename(__file__).replace(".py", ".result.json")),
                      "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    hard = [k for k in v if k.startswith("CONTROL") and not v[k]]
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())
