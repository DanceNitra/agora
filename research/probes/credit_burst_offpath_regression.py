"""OFF-PATH REGRESSION for credit_burst_window — against the PRE-CHANGE code, not against itself.

The library's canonical suite is not in this working tree, so "tests are green" cannot be asserted
here. This checks the thing that actually matters for an opt-in flag: with the flag unset, does the
NEW code produce bit-identical state to the OLD code on a script that exercises the credit surface?

The comparison arm is the previous committed version of inspeximus.py, extracted from git into a
temp package and imported separately. Comparing the new code against itself with the flag set to
None would be an arm that cannot fail — the same defect this whole workstream keeps catching.
"""
import copy
import json
import os
import subprocess
import sys
import tempfile
import importlib.util

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
NEW = os.path.join(REPO, "inspeximus_pypi", "inspeximus", "inspeximus.py")
REL = "inspeximus_pypi/inspeximus/inspeximus.py"
VOLATILE = {"id", "ts", "iso", "last", "vec", "credit_seen",
            "valid_from", "last_access"}   # wall-clock fields differ between the two runs


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod.Inspeximus


def old_source():
    """HEAD's version of the file — the code before this change."""
    out = subprocess.run(["git", "-C", REPO, "show", f"HEAD:{REL}"],
                         capture_output=True)
    if out.returncode != 0:
        raise SystemExit("could not read HEAD version: " + out.stderr.decode()[:300])
    d = tempfile.mkdtemp()
    p = os.path.join(d, "old_inspeximus.py")
    with open(p, "wb") as f:
        f.write(out.stdout)
    return p


def normalize(items):
    out = []
    for r in sorted(items, key=lambda x: x.get("text", "")):
        c = {k: v for k, v in copy.deepcopy(r).items() if k not in VOLATILE}
        for edge in ("links", "derived_from"):
            if c.get(edge):
                c[edge] = len(c[edge])
        out.append(c)
    return out


def script(Klass):
    m = Klass(os.path.join(tempfile.mkdtemp(), "s.json"))
    ids = []
    for i in range(12):
        r = m.remember(f"fact {i}: the {i} service drains its queue before a rollback", tags=["ops"])
        ids.append(r["id"] if isinstance(r, dict) else r)
    rets = []
    for _ in range(6):
        hits = [h["id"] for h in m.recall("rollback drain the queue", k=4)]
        rets.append(sorted(m.credit(hits, True).keys()))
    for _ in range(4):
        hits = [h["id"] for h in m.recall("service rollback", k=3)]
        rets.append(sorted(m.credit(hits, False).keys()))
    rets.append(sorted(m.credit(ids[:3], True, weight=2.0).keys()))
    rets.append(sorted(m.credit(ids[3:5], False, warrant="ticket-9").keys()))
    m.recall("queue", k=5)
    return normalize(m.items), rets


def main():
    New = load(NEW, "insp_new")
    Old = load(old_source(), "insp_old")

    new_items, new_rets = script(New)
    old_items, old_rets = script(Old)

    same_state = new_items == old_items
    same_api = new_rets == old_rets
    print(f"records compared                 : {len(new_items)}")
    print(f"OFF-path state == pre-change     : {'PASS' if same_state else 'FAIL'}")
    print(f"OFF-path credit() return shape   : {'PASS' if same_api else 'FAIL'}")
    if not same_state:
        for x, y in zip(new_items, old_items):
            if x != y:
                print("  new:", json.dumps(x, ensure_ascii=False)[:300])
                print("  old:", json.dumps(y, ensure_ascii=False)[:300])
                break

    # Sanity: the harness must be able to SEE a difference when one exists.
    m = New(os.path.join(tempfile.mkdtemp(), "s.json"))
    m.credit_burst_window = 3600
    r = m.remember("burst target", tags=["x"])
    rid = r["id"] if isinstance(r, dict) else r
    m.credit([rid], False)
    m.credit([rid], False)
    bad = float({x["id"]: x for x in m.items}[rid]["bad"])
    detects = (bad == 1.0)
    print(f"harness detects a real change ON : {'PASS' if detects else 'FAIL'} (bad={bad}, expect 1.0)")

    ok = same_state and same_api and detects
    print("\nRESULT:", "OK" if ok else "REGRESSION")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
