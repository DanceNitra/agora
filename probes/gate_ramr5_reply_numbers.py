"""VALIDATE gate for the reply on DanceNitra/ramr#5: every figure re-derived, not recalled.

The reply reports what we verified before merging @Stratogain's five commits and what our own fix
then changed. None of it may rest on memory of a run. This gate re-derives each figure from the
artifact that main now ships, and re-runs the two controls the reply cites by name.

THE CONTROL, because a gate that cannot fail has measured nothing: after the real pass, the same
assertions run against a MUTATED copy of the artifact. If the mutated run still passes, the gate is
not reading what it claims to read.

Run:  python probes/gate_ramr5_reply_numbers.py
Exit 0 = every number in the reply is backed. Exit 1 = do not send.
"""
from __future__ import annotations
import json
import os
import re
import subprocess
import sys

RAMR = r"C:\Users\Danculus\ramr-pub"
ARTIFACT = os.path.join(RAMR, "integrity", "results", "receipt_binding.json")
CELL = os.path.join(RAMR, "integrity", "receipt_binding.py")
DRAFT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "agora_output", "drafts",
                     "reply_ramr5_stratogain.md")

SKIP_REASON = ("inspeximus 2.5.0 has witness(self) -> dict; "
               "this row needs witness(records=, bind_sources=)")


class Gate:
    def __init__(self):
        self.checks = []

    def add(self, label, ok, got, want="True"):
        self.checks.append((label, bool(ok), got, want))
        return bool(ok)

    def report(self, quiet=False):
        bad = [c for c in self.checks if not c[1]]
        if not quiet:
            for label, ok, got, want in self.checks:
                print("  %-4s %-56s got=%s" % ("ok" if ok else "FAIL", label, got))
        return not bad


def run_artifact_checks(d, draft, g):
    wm = d["rows"]["witness_measuring"]["_diagnostics"]["S7_witness_liveness_measurable"]
    g.add("S7 state FRESH", wm["state"] == "FRESH", wm["state"])
    g.add("S7 samples_at_decision = 2", wm["samples_at_decision"] == 2, wm["samples_at_decision"])
    g.add("S7 threshold = 6.0", abs(wm["threshold"] - 6.0) < 1e-9, wm["threshold"])
    g.add("S7 max_normal_lag = 2.0", abs(wm["max_normal_lag"] - 2.0) < 1e-9, wm["max_normal_lag"])
    g.add("S7 basis derived", wm["basis"] == "derived", wm["basis"])

    r = d["reads_before_stale"]
    g.add("after our fix, content_continuity 3/3 VALID",
          r["content_continuity"] == ["VALID"] * 3, r["content_continuity"])
    g.add("after our fix, transition_continuity 3/3 VALID",
          r["transition_continuity"] == ["VALID"] * 3, r["transition_continuity"])

    g.add("S5 still splits the profiles: ledger VALID",
          d["rows"]["ledger"]["S5_returned_to_original"] == "VALID",
          d["rows"]["ledger"]["S5_returned_to_original"])
    g.add("S5 still splits the profiles: ledger+gen STALE",
          d["rows"]["ledger+gen"]["S5_returned_to_original"] == "STALE",
          d["rows"]["ledger+gen"]["S5_returned_to_original"])
    g.add("artifact exit_status 0", d["exit_status"] == 0, d["exit_status"])
    g.add("complete true on this machine", d["complete"] is True, d["complete"])
    g.add("resolved names inspeximus 2.20.0",
          d["resolved"].get("inspeximus", {}).get("version") == "2.20.0",
          d["resolved"].get("inspeximus", {}).get("version"))

    # the reply's claims about the draft's own wording
    g.add("draft cites samples_at_decision=2", "samples_at_decision=2" in draft, True)
    g.add("draft cites threshold 6.0", "threshold=6.0" in draft or "`threshold=6.0`" in draft, True)
    g.add("draft cites the skip reason verbatim", SKIP_REASON in draft, True)
    g.add("draft cites the mutation output",
          "reads: BROKEN -- transition_continuity: ['VALID', 'STALE', 'STALE']" in draft, True)
    g.add("draft says 48 tracked .py files", "48 tracked" in draft, True)
    return g


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if not os.path.exists(ARTIFACT):
        print("no artifact at %s" % ARTIFACT)
        return 1
    d = json.load(open(ARTIFACT, encoding="utf-8"))
    draft = open(DRAFT, encoding="utf-8").read()
    print("artifact: %s\ndraft: %d words\n" % (os.path.basename(ARTIFACT), len(draft.split())))

    g = run_artifact_checks(d, draft, Gate())

    # ---- LIVE CONTROL 1: the complete/unfiltered split, re-run, not recalled -------------------
    stub = os.path.join(os.environ.get("TEMP", "."), "gate_oldinsp")
    os.makedirs(os.path.join(stub, "inspeximus"), exist_ok=True)
    with open(os.path.join(stub, "inspeximus", "__init__.py"), "w", encoding="utf-8") as fh:
        fh.write('__version__ = "2.5.0"\n'
                 'class Inspeximus:\n'
                 '    def __init__(self, path=None, **kw): pass\n'
                 '    def witness(self) -> dict: return {}\n')
    env = dict(os.environ, PYTHONPATH=stub)
    subprocess.run([sys.executable, CELL], cwd=RAMR, env=env,
                   capture_output=True, text=True, timeout=600)
    stubbed = json.load(open(ARTIFACT, encoding="utf-8"))
    g.add("CONTROL stub: unfiltered stays true", stubbed["unfiltered"] is True, stubbed["unfiltered"])
    g.add("CONTROL stub: complete goes false", stubbed["complete"] is False, stubbed["complete"])
    g.add("CONTROL stub: the skip reason survives verbatim",
          stubbed["rows"]["inspeximus"].get("skipped") == SKIP_REASON,
          str(stubbed["rows"]["inspeximus"].get("skipped"))[:70])

    # ---- LIVE CONTROL 2: the reads control must FAIL when the defect is restored ---------------
    src = open(CELL, encoding="utf-8").read()
    good = '''        return sum(1 for r in self.records
                   if r["source_id"] == sid and r.get("kind") != "verify")'''
    mutant = '''        return sum(1 for r in self.records if r["source_id"] == sid) - (
            1 if any(r.get("kind") == "verify" and r["source_id"] == sid for r in self.records) else 0)'''
    if good not in src:
        g.add("CONTROL mutation anchor present", False, "anchor missing")
    else:
        try:
            with open(CELL, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(src.replace(good, mutant, 1))
            p = subprocess.run([sys.executable, CELL], cwd=RAMR, capture_output=True, text=True,
                               timeout=600)
            g.add("CONTROL mutant exits 1", p.returncode == 1, p.returncode)
            g.add("CONTROL mutant prints reads: BROKEN", "reads: BROKEN" in p.stdout,
                  next((l for l in p.stdout.splitlines() if l.startswith("reads:")), "")[:60])
        finally:
            with open(CELL, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(src)

    # ---- restore the real artifact, and assert the restore worked -------------------------------
    p = subprocess.run([sys.executable, CELL], cwd=RAMR, capture_output=True, text=True, timeout=600)
    g.add("restored: cell exits 0", p.returncode == 0, p.returncode)
    final = json.load(open(ARTIFACT, encoding="utf-8"))
    g.add("restored: complete true again", final["complete"] is True, final["complete"])
    g.add("restored: reads 3/3 under both profiles",
          all(v == ["VALID"] * 3 for v in final["reads_before_stale"].values()),
          final["reads_before_stale"])

    ok = g.report()

    # ---- THE GATE'S OWN CONTROL: perturb the artifact, the assertions must fail -----------------
    print("\nCONTROL, the gate re-run against a mutated artifact (must FAIL):")
    bad_art = json.loads(json.dumps(final))
    bad_art["rows"]["witness_measuring"]["_diagnostics"][
        "S7_witness_liveness_measurable"]["samples_at_decision"] = 3
    caught = not run_artifact_checks(bad_art, draft, Gate()).report(quiet=True)
    print("  %-4s samples_at_decision 2 -> 3 : gate %s"
          % ("ok" if caught else "FAIL", "fails" if caught else "STILL PASSES"))

    bad_draft = draft.replace(SKIP_REASON, "not installed")
    caught2 = not run_artifact_checks(final, bad_draft, Gate()).report(quiet=True)
    print("  %-4s skip reason removed from draft : gate %s"
          % ("ok" if caught2 else "FAIL", "fails" if caught2 else "STILL PASSES"))

    print("\n" + "=" * 78)
    print("VALIDATE: %s   CONTROL: %s" % ("PASS" if ok else "FAIL",
                                          "PASS" if (caught and caught2) else "FAIL"))
    print("=" * 78)
    return 0 if (ok and caught and caught2) else 1


if __name__ == "__main__":
    sys.exit(main())
