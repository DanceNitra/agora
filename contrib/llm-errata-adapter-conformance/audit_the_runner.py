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

    def run(extra=None):
        r = subprocess.run([sys.executable, "-X", "utf8", RUNNER, "--pkg", a.pkg] + (extra or []),
                           capture_output=True, text=True, cwd=HERE)
        return r.returncode, r.stdout + r.stderr

    def patch_runner(old, new):
        assert old in orig_py, "the audit's own anchor is gone: %r" % old[:50]
        io.open(RUNNER, "w", encoding="utf-8", newline="\n").write(orig_py.replace(old, new))

    rows = []
    try:
        # GUARD 1 -- a crash during a mutation must not be credited as a caught mutation.
        patch_runner("        adapter.lineage_complete = lambda root: True",
                     '        raise RuntimeError("mutation cannot install")')
        rc, out = run()
        rows.append(("exception is not a caught mutation",
                     rc != 0 and "is NOT a caught mutation" in out))
        restore()

        # GUARD 2 -- the positive control must bind to the adapter INSTANCE, not a function name.
        # `sign` exists in the process (the signer) but is never called on the adapter, so a
        # name-matching tracer accepts it and an instance-bound one does not.
        fx = json.loads(orig_fx)
        fx["adapter_cases"][0]["positive_control"]["adapter_methods_required"].append("sign")
        io.open(FIXTURE, "w", encoding="utf-8", newline="\n").write(json.dumps(fx, indent=2))
        patch_runner("        self.target = target", "        self.target = None  # MUTANT")
        _, lax_out = run()
        io.open(RUNNER, "w", encoding="utf-8", newline="\n").write(orig_py)
        _, strict_out = run()
        lax_accepts = "MISSING" not in lax_out.split("complete-lineage")[0]
        strict_rejects = "MISSING ['sign']" in strict_out
        rows.append(("tracing is bound to the target instance", lax_accepts and strict_rejects))
        restore()

        # GUARD 3 -- an unbound source tree must be refused, not scored.
        rc, out = run(["--pkg-digest", "0" * 64])
        rows.append(("--pkg-digest refuses a mismatched tree",
                     rc != 0 and "does not match the declared source digest" in out))

        # GUARD 4 -- a mutation must produce the counter-result it DECLARED, not merely any failure.
        fx = json.loads(orig_fx)
        case = [c for c in fx["adapter_cases"]
                if c["id"] == "undeclared-derivative-must-not-reach-verified"][0]
        case["mutation"]["must_produce"] = {"aggregate": "this-value-can-never-occur"}
        io.open(FIXTURE, "w", encoding="utf-8", newline="\n").write(json.dumps(fx, indent=2))
        rc, out = run()
        rows.append(("must_produce is evaluated", "not as declared" in out))
        restore()

        # GUARD 5 -- a case with no normative citation must be refused rather than scored.
        fx = json.loads(orig_fx)
        fx["adapter_cases"][0]["normative"] = {}
        io.open(FIXTURE, "w", encoding="utf-8", newline="\n").write(json.dumps(fx, indent=2))
        rc, out = run()
        rows.append(("a case without a citation is refused",
                     rc != 0 and "no normative citation" in out))
        restore()

        # GUARD 6 -- a citation whose text is absent from the pinned source must be refused.
        fx = json.loads(orig_fx)
        fx["adapter_cases"][0]["normative"]["quote"] = "a sentence that appears in no source file"
        io.open(FIXTURE, "w", encoding="utf-8", newline="\n").write(json.dumps(fx, indent=2))
        rc, out = run()
        rows.append(("an invented citation is refused",
                     rc != 0 and "quoted text is not present" in out))
        restore()

        # GUARD 7 -- strict comparison: an outcome the case did not mention must still conform.
        # Removing the declared aggregate from the failing case must NOT turn it green.
        fx = json.loads(orig_fx)
        coll = [c for c in fx["adapter_cases"]
                if c["id"] == "collateral-must-survive-a-supersession"][0]
        coll["expect"].pop("aggregate", None)
        coll["expect"]["triad"] = {"preserve": "pass"}
        io.open(FIXTURE, "w", encoding="utf-8", newline="\n").write(json.dumps(fx, indent=2))
        rc, out = run()
        still_fails = "[FAIL] collateral-must-survive-a-supersession" in out
        rows.append(("dropping an expectation does not hide a failure", still_fails))
        restore()
    finally:
        restore()

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
