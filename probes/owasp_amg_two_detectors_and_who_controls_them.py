"""Two OWASP Agent Memory Guard detectors, measured against the threat model OWASP itself defines.

OWASP added **ASI06 — Memory & Context Poisoning** to the 2026 Agentic Top 10, and its defining
property is stated plainly in the category text: *anything that writes into the agent's memory becomes
a privileged input*, and the attack is **temporally decoupled** — written today, acted on weeks later.
OWASP's own incubator defence, `agent-memory-guard` (v0.3.0-dev, `pip install agent-memory-guard`),
reports **92.5% detection at 100% precision over 55 payloads in four categories**.

This is not a test of that 92.5%. It is a test of two specific detectors against the part of ASI06
that says the attacker owns a write channel, and it is a **replicate-and-defend** run: both findings
came out of reading their source, and the control for each is their own documented behaviour.

READ FIRST, CLAIMED SECOND. The first hypothesis here was that AMG is write-time content screening
only and so cannot see a temporally decoupled attack. That was **wrong** and reading the package
killed it: AMG ships twelve detectors including `cross_task`, `privilege_escalation`, `tool_abuse`
and `excessive_autonomy`, plus a classification/promotion graph with `requires_verification`. It is a
far more serious piece of work than its README summary suggests. What follows is narrower and, I
think, real.

FINDING 1 — the self-reinforcement cool-down is reset by the attacker.
`SelfReinforcementDetector` flags rapid self-similar `AGENT_AUTHORED` writes to one key. Its docstring:
*"A separate external_tool or user_input write resets the counter (independent evidence breaks the
loop)."* In `guard.write` that reset calls `note_independent_write`, which does
`history.writes.clear()` — it empties the whole window, not one slot. Under ASI06's own threat model
the attacker holds a write channel, so interleaving one `USER_INPUT` write between agent writes should
keep the counter at zero forever.

FINDING 2 — cross-task contamination fails OPEN on an unregistered origin.
`CrossTaskContaminationDetector.inspect` returns `matched=False` when
`origin is None or self._current_task is None`. `origin` is `None` for any key written without a
`task_id`. So a write that simply omits the task id is invisible to the detector that exists to catch
it — a check reporting safe about the case it cannot see.

CONTROLS, because a probe that shows an attack succeeding proves nothing unless the same harness shows
the defence working:
  * C1: four consecutive self-similar AGENT_AUTHORED writes MUST be flagged;
  * C2: a durable key written under task A with a task_id and read under task B MUST be flagged;
  * if either control fails, the harness is wrong and the run aborts rather than reporting a finding.

Run:  python probes/owasp_amg_two_detectors_and_who_controls_them.py
"""
from __future__ import annotations
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
VENV = ("C:/Users/Danculus/AppData/Local/Temp/claude/C--Users-Danculus-agora/"
        "e6f8e2c8-b4c1-4269-a886-f10b2cd62521/scratchpad/amg/Scripts/python.exe")

CHILD = r'''
import json, sys
import agent_memory_guard as amg
from agent_memory_guard import MemoryGuard, MemoryClass, SourceClass

out = {"version": getattr(amg, "__version__", "?")}

def fired(g, name, since):
    return any(e.detector == name for e in g.events[since:]
               if hasattr(e, "detector"))

def ev_names(g, since):
    return [getattr(e, "detector", "?") for e in g.events[since:]]

BASE = "the deployment key is stored in the ops runbook under section four"

# ---- C1 / A1 : self-reinforcement -----------------------------------------------------------
def self_reinforce(interleave):
    g = MemoryGuard()
    n0 = len(g.events)
    flagged = False
    for i in range(4):
        try:
            g.write("session.note", BASE + " " + ("and it is current " * (i + 1)),
                    source_class=SourceClass.AGENT_AUTHORED)
        except Exception as e:
            flagged = True
        if fired(g, "self_reinforcement", n0):
            flagged = True
        if interleave:
            # ONE attacker-controlled write on the SAME key, in a class that is not agent-authored
            try:
                g.write("session.note", BASE + " confirmed by the user",
                        source_class=SourceClass.USER_INPUT)
            except Exception:
                pass
    return flagged, ev_names(g, n0)

out["C1_no_interleave_flagged"], out["C1_events"] = self_reinforce(False)
out["A1_interleaved_flagged"], out["A1_events"] = self_reinforce(True)

# ---- C2 / A2 : cross-task contamination -----------------------------------------------------
def cross_task(with_task_id):
    g = MemoryGuard()
    g.set_current_task("task-A")
    if with_task_id:
        g.write("tool.result", "the invoice total is 4,120 EUR",
                source_class=SourceClass.EXTERNAL_TOOL,
                cls=MemoryClass.TOOL_OBSERVATION, task_id="task-A")
    else:
        # identical write, task_id simply omitted
        g.write("tool.result", "the invoice total is 4,120 EUR",
                source_class=SourceClass.EXTERNAL_TOOL,
                cls=MemoryClass.TOOL_OBSERVATION)
    g.set_current_task("task-B")
    n0 = len(g.events)
    try:
        g.read("tool.result")
    except Exception:
        return True, ["blocked-by-exception"], g.origin_task("tool.result")
    return fired(g, "cross_task_contamination", n0), ev_names(g, n0), g.origin_task("tool.result")

out["C2_with_task_id_flagged"], out["C2_events"], out["C2_origin"] = cross_task(True)
out["A2_no_task_id_flagged"], out["A2_events"], out["A2_origin"] = cross_task(False)

print("@@JSON@@" + json.dumps(out))
'''


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if not os.path.exists(VENV):
        print("FAIL -- the agent-memory-guard venv is missing at %s" % VENV)
        return 1

    r = subprocess.run([VENV, "-c", CHILD], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    line = next((l for l in (r.stdout or "").splitlines() if l.startswith("@@JSON@@")), None)
    if not line:
        print("FAIL -- child produced no result\nSTDOUT:\n%s\nSTDERR:\n%s"
              % ((r.stdout or "")[-1500:], (r.stderr or "")[-1500:]))
        return 1
    d = json.loads(line[len("@@JSON@@"):])

    print("agent-memory-guard %s\n" % d["version"])
    print("CONTROLS (their documented behaviour must reproduce, or this probe measures nothing)")
    print("  C1  4 self-similar AGENT_AUTHORED writes, no interleave   flagged=%s  %s"
          % (d["C1_no_interleave_flagged"], d["C1_events"]))
    print("  C2  durable key written under task-A, read under task-B   flagged=%s  origin=%r  %s"
          % (d["C2_with_task_id_flagged"], d["C2_origin"], d["C2_events"]))

    if not d["C1_no_interleave_flagged"] or not d["C2_with_task_id_flagged"]:
        print("\nABORT -- a control did not reproduce. The harness is wrong, not the package.")
        return 1
    print("  both controls reproduce.\n")

    print("ATTACKS (the same case, with the one thing ASI06 says the attacker holds)")
    print("  A1  same 4 writes + ONE interleaved USER_INPUT write      flagged=%s  %s"
          % (d["A1_interleaved_flagged"], d["A1_events"]))
    print("  A2  same cross-task read, task_id simply omitted          flagged=%s  origin=%r  %s"
          % (d["A2_no_task_id_flagged"], d["A2_origin"], d["A2_events"]))

    a1 = not d["A1_interleaved_flagged"]
    a2 = not d["A2_no_task_id_flagged"]
    print("\n" + "=" * 78)
    print("FINDING 1  cool-down defeated by an interleaved non-agent write : %s"
          % ("CONFIRMED" if a1 else "not reproduced"))
    print("FINDING 2  cross-task check fails OPEN on an absent task_id     : %s"
          % ("CONFIRMED" if a2 else "not reproduced"))
    print("=" * 78)

    out = os.path.join(HERE, "owasp_amg_two_detectors_and_who_controls_them.result.json")
    json.dump({"package_version": d["version"],
               "controls_reproduced": bool(d["C1_no_interleave_flagged"]
                                           and d["C2_with_task_id_flagged"]),
               "finding_1_cooldown_reset_by_attacker": a1,
               "finding_2_cross_task_fails_open_without_task_id": a2,
               "raw": d}, open(out, "w", encoding="utf-8"), indent=1)
    print("receipt -> " + out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
