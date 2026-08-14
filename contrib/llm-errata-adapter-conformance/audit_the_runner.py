"""Attack the runner's own six guards and require every one of them to fire.

WHY THIS FILE EXISTS, stated plainly because the reason is not flattering. The six guards in
`run_adapter_conformance.py` were added after a maintainer review found six false-pass gaps in the
first version. Having written them, I reported them as "fixed". Two of the six had actually been
demonstrated: the citation check had caught three of our own bad citations, and the strict comparison
had flipped a case from PASS to FAIL. The other four were assertions. Nobody had broken them on
purpose to see whether they were load-bearing or decorative.

That distinction is the whole subject of this suite. A guard nobody has watched fire is indistinguishable
from a guard that cannot fire, and the fixture we ship tells other people exactly that. Shipping the
guards without this file would have been the same defect one level up.

So the audit is a file rather than something someone remembers to do. Each mutation below breaks one
guard and requires the run to notice. If any line reports DOES NOT FIRE, that guard is decorative and
the numbers this runner prints cannot be quoted until it is fixed.

    python audit_the_runner.py --pkg <dir containing the full pinned tree>
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUNNER = os.path.join(HERE, "run_adapter_conformance.py")
FIXTURE = os.path.join(HERE, "adapter-conformance.json")
RESULT = os.path.join(HERE, "audit_the_runner.result.json")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkg", required=True)
    a = ap.parse_args(argv)

    orig_py = io.open(RUNNER, encoding="utf-8").read()
    orig_fx = io.open(FIXTURE, encoding="utf-8").read()

    def restore():
        io.open(RUNNER, "w", encoding="utf-8", newline="\n").write(orig_py)
        io.open(FIXTURE, "w", encoding="utf-8", newline="\n").write(orig_fx)

    tmp_result = os.path.join(HERE, ".audit-result.json")

    def run(extra=None):
        """Run the runner into a THROWAWAY result file and return (rc, output, parsed verdicts).

        Two defects fixed here. The audit used to let the runner overwrite the published
        `adapter-conformance.result.json`, so after a clean audit the shipped artifact was the
        guard-7 MUTANT run -- and that file went out. And every guard asserted on printed text or on
        `rc != 0`, which the known-failing case supplies anyway, so the audit reported 7/7 with the
        verdict line replaced by `good = ok`: it measured that the runner NARRATES its guards, not
        that they gate anything. Guards now read the machine-readable verdict.
        """
        # DELETE IT FIRST. A run that ABORTS never writes, so a leftover file from the previous
        # guard was read as this guard's verdicts, and the three refusal guards -- which require
        # there to be no verdicts at all -- read the last successful run instead and reported
        # DOES NOT FIRE. Reading a stale artifact as if it were this run's output is the same
        # mistake this whole suite exists to catch.
        try:
            os.remove(tmp_result)
        except OSError:
            pass
        r = subprocess.run([sys.executable, "-X", "utf8", RUNNER, "--pkg", a.pkg,
                            "--result", tmp_result] + (extra or []),
                           capture_output=True, text=True, cwd=HERE)
        verdicts = {}
        try:
            doc = json.loads(io.open(tmp_result, encoding="utf-8").read())
            verdicts = {c["id"]: c for c in doc.get("cases", [])}
        except Exception:
            pass
        return r.returncode, r.stdout + r.stderr, verdicts

    def patch_runner(old, new):
        assert old in orig_py, "the audit's own anchor is gone: %r" % old[:50]
        io.open(RUNNER, "w", encoding="utf-8", newline="\n").write(orig_py.replace(old, new))

    rows = []
    C1 = "undeclared-derivative-must-not-reach-verified"
    try:
        # GUARD 1 -- a crash during a mutation must not be credited as a caught mutation.
        patch_runner("        adapter.lineage_complete = lambda root: True",
                     '        raise RuntimeError("mutation cannot install")')
        rc, out, verdicts = run()
        rows.append(("exception is not a caught mutation",
                     verdicts.get(C1, {}).get("mutation_caught") is False
                     and verdicts.get(C1, {}).get("pass") is False))
        restore()

        # GUARD 2 -- the positive control must be able to call a declared method INERT.
        # The old guard tested a name-matching tracer and stopped applying when the control became a
        # stub test; it reported DOES NOT FIRE, which is the audit working. `coverage_detail` is on
        # the adapter but the repair path never consults it, so declaring it must be caught. Then the
        # control loop is forced to mark everything load-bearing and the same case must go green,
        # which is what proves the guard is reading the control rather than the weather.
        fx = json.loads(orig_fx)
        fx["adapter_cases"][0]["positive_control"]["adapter_methods_required"].append("coverage_detail")
        io.open(FIXTURE, "w", encoding="utf-8", newline="\n").write(json.dumps(fx, indent=2))
        _, honest, _h = run()
        catches_inert = "coverage_detail" in (_h.get(C1, {}).get("methods_inert") or [])
        patch_runner("            (load_bearing if noticed else inert).append(method)",
                     "            (load_bearing).append(method)  # MUTANT: nothing is ever inert")
        _, blind, _b = run()
        misses_inert = not (_b.get(C1, {}).get("methods_inert") or [])
        rows.append(("an inert declared method is caught", catches_inert and misses_inert))
        restore()

        # GUARD 3 -- an unbound source tree must be refused, not scored.
        rc, out, verdicts = run(["--pkg-digest", "0" * 64])
        rows.append(("--pkg-digest refuses a mismatched tree",
                     rc != 0 and "does not match the declared source digest" in out and not verdicts))

        # GUARD 4 -- a mutation must produce the counter-result it DECLARED, not merely any failure.
        fx = json.loads(orig_fx)
        case = [c for c in fx["adapter_cases"]
                if c["id"] == "undeclared-derivative-must-not-reach-verified"][0]
        case["mutation"]["must_produce"] = {"aggregate": "this-value-can-never-occur"}
        io.open(FIXTURE, "w", encoding="utf-8", newline="\n").write(json.dumps(fx, indent=2))
        rc, out, verdicts = run()
        rows.append(("must_produce is evaluated",
                     verdicts.get(C1, {}).get("mutation_caught") is False))
        restore()

        # GUARD 5 -- a case with no normative citation must be refused rather than scored.
        fx = json.loads(orig_fx)
        fx["adapter_cases"][0]["normative"] = {}
        io.open(FIXTURE, "w", encoding="utf-8", newline="\n").write(json.dumps(fx, indent=2))
        rc, out, verdicts = run()
        rows.append(("a case without a citation is refused",
                     rc != 0 and "no normative citation" in out and not verdicts))
        restore()

        # GUARD 6 -- a citation whose text is absent from the pinned source must be refused.
        fx = json.loads(orig_fx)
        fx["adapter_cases"][0]["normative"]["quote"] = "a sentence that appears in no source file"
        io.open(FIXTURE, "w", encoding="utf-8", newline="\n").write(json.dumps(fx, indent=2))
        rc, out, verdicts = run()
        rows.append(("an invented citation is refused",
                     rc != 0 and "quoted text is not present" in out and not verdicts))
        restore()

        # GUARD 7 -- strict comparison: an outcome the case did not mention must still conform.
        # Removing the declared aggregate from the failing case must NOT turn it green.
        fx = json.loads(orig_fx)
        coll = [c for c in fx["adapter_cases"]
                if c["id"] == "collateral-must-survive-a-supersession"][0]
        coll["expect"].pop("aggregate", None)
        coll["expect"]["triad"] = {"preserve": "pass"}
        io.open(FIXTURE, "w", encoding="utf-8", newline="\n").write(json.dumps(fx, indent=2))
        rc, out, verdicts = run()
        still_fails = verdicts.get("collateral-must-survive-a-supersession", {}).get("pass") is False
        rows.append(("dropping an expectation does not hide a failure", still_fails))
        restore()
        # GUARD 8 -- THE ONE THIS AUDIT DID NOT HAVE, and its absence is why it certified a runner
        # that ignored its own controls. Nothing bound a guard to the VERDICT: seven guards asserted
        # on printed text or on an rc the known-failing case supplied anyway, so replacing
        # `good = ok and control_ok and mutation_caught` with `good = ok` still printed 7/7 and
        # "every one noticed". An audit that cannot notice its subject ignoring its own controls is
        # measuring narration.
        patch_runner("        good = ok and control_ok and mutation_caught",
                     "        good = ok  # MUTANT: controls no longer reach the verdict")
        fx = json.loads(orig_fx)
        fx["adapter_cases"][0]["positive_control"]["adapter_methods_required"].append("coverage_detail")
        io.open(FIXTURE, "w", encoding="utf-8", newline="\n").write(json.dumps(fx, indent=2))
        _, _o, gutted = run()
        rows.append(("the controls reach the verdict",
                     gutted.get(C1, {}).get("pass") is True
                     and bool(gutted.get(C1, {}).get("methods_inert"))))
        restore()
    finally:
        restore()
        try:
            os.remove(tmp_result)
        except OSError:
            pass

    print("AUDIT OF THE RUNNER'S OWN GUARDS\n")
    for name, ok in rows:
        print("  [%s] %s" % ("FIRES        " if ok else "DOES NOT FIRE", name))
    fired = sum(1 for _, ok in rows if ok)
    print("\n%d/%d guards fire." % (fired, len(rows)))
    io.open(RESULT, "w", encoding="utf-8", newline="\n").write(
        json.dumps({"guards": [{"guard": n, "fires": bool(o)} for n, o in rows],
                    "fired": fired, "total": len(rows)}, indent=2) + "\n")
    if fired != len(rows):
        print("A guard that does not fire is decorative. Do not quote this runner's numbers.")
        return 1
    print("Every guard was broken on purpose and every one noticed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
