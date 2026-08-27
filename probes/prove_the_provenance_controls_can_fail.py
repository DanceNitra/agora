# -*- coding: utf-8 -*-
"""Prove the controls in the provenance probe can FAIL, by breaking it on purpose.

A control that passes tells you nothing on its own. It has to be shown failing on the defect it
exists to catch, and every mutation here is one we actually shipped or nearly shipped.

    1  addressable accepts any http/https prefix   the defect @perseus-computing reported on r/RAG
    2  addressable says yes to everything          the degenerate version of the same
    3  retrieves says yes to everything            passes a 200-only check
    4  retrieves says no to everything             passes a 404-only check, AND WE HAD THIS ONE:
                                                   a bare `except Exception` over a missing import
                                                   returned False for every locator on earth, and
                                                   its answer was zero, which is also our headline
    5  raw_source ignores dict-valued sources      takes our published coverage from 90% to 0.00%,
                                                   and the OLD fixture stayed green through it,
                                                   because it used strings while every record in
                                                   the real corpus is a dict
    6  raw_source prefers `doc` unconditionally    a record with a dead doc and a live uri reports
                                                   the dead one
    7  record_locators looks only at `source`      this is how the published post came to say that
                                                   nothing resolves, while every sourced record in
                                                   the coding store carried meta.files paths that
                                                   do
    8  git_pair_audit reads the working copy       "the file is on my disk now" standing in for
                                                   "the file was in that commit", which is the same
                                                   confusion the whole thread is about. The control
                                                   passed this until a third row was added, because
                                                   a path in HEAD is also on disk and a path absent
                                                   everywhere is absent in both

Run:  python -X utf8 probes/prove_the_provenance_controls_can_fail.py
"""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "a_provenance_field_at_100_percent_with_one_distinct_value.py")

spec = importlib.util.spec_from_file_location("prov", TARGET)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

EXPECT = m.CONTROL_EXPECT
ORIG = {n: getattr(m, n) for n in ("addressable", "retrieves", "raw_source", "record_locators")}


def disagreements():
    """Run the probe's own control fixture and return what its controls would report."""
    c, why = m.control()
    if c is None:
        return None, why
    return {k: (EXPECT[k], c[k]) for k in EXPECT if c[k] != EXPECT[k]}, ""


def _doc_first(rec):
    """raw_source as it was: `doc` outranks every other key, live or dead."""
    s = rec.get("source")
    if s is None:
        s = (rec.get("meta") or {}).get("source")
    if isinstance(s, dict):
        s = s.get("doc") or s.get("uri") or s.get("path") or json.dumps(s, sort_keys=True)
    return s.strip() if isinstance(s, str) and s.strip() else None


def _string_only(rec):
    """raw_source with the dict branch removed."""
    s = rec.get("source")
    return s.strip() if isinstance(s, str) and s.strip() else None


def _source_field_only(rec):
    """record_locators scoped to the `source` field, which is what the published probe did."""
    s = rec.get("source")
    if isinstance(s, str):
        return [s]
    if isinstance(s, dict):
        return [v for v in s.values() if isinstance(v, str)]
    return []


MUTATIONS = [
    ("addressable = the reported bug (any http/https prefix)",
     {"addressable": lambda loc, bases=(): os.path.isabs(loc) and os.path.exists(loc)
      or str(loc).startswith(("http://", "https://"))}),
    ("addressable = always True",
     {"addressable": lambda loc, bases=(): True}),
    ("retrieves = always True",
     {"retrieves": lambda loc, bases=(), timeout=5.0: True}),
    ("retrieves = always False",
     {"retrieves": lambda loc, bases=(), timeout=5.0: False}),
    ("raw_source ignores dict-valued sources", {"raw_source": _string_only}),
    ("raw_source prefers doc unconditionally", {"raw_source": _doc_first}),
    ("record_locators reads only the source field", {"record_locators": _source_field_only}),
]


def _working_copy_audit(items, repo=None, public_ref="origin/main"):
    """git_pair_audit that ignores the sha and asks the working copy instead.

    This is the mutation that matters most, because it is the SAME confusion the whole thread is
    about, one level up: "the file is on my disk now" standing in for "the file was in that commit".
    Until a third row was added, git_pair_control passed this: a path in HEAD is also on disk, and a
    path absent everywhere is absent in both, so neither of the first two rows could separate them.
    """
    root = repo or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pairs = ok = recs = full = 0
    shas = set()
    for r in items:
        m = r.get("meta") if isinstance(r, dict) else None
        if not isinstance(m, dict):
            continue
        files = m.get("files")
        if isinstance(files, str):
            files = [files]
        if not (isinstance(m.get("sha"), str) and isinstance(files, list) and files):
            continue
        shas.add(m["sha"].strip())
        recs += 1
        hit = 0
        for f in files:
            pairs += 1
            if os.path.exists(os.path.join(root, f)):
                ok += 1
                hit += 1
        full += hit == len(files)
    return {"records_with_pair": recs, "records_fully_resolved": full, "pairs": pairs,
            "pairs_in_tree": ok, "distinct_shas": len(shas), "shas_are_commits": len(shas),
            "shas_public": len(shas), "public_ref": public_ref}


def git_pair_row():
    """The git-pair control, checked in both directions like every other row here."""
    clean_ok, clean_why = m.git_pair_control()
    if clean_ok is None:
        return None, "shipped: NOT ATTEMPTED (%s)" % clean_why
    orig = m.git_pair_audit
    try:
        m.git_pair_audit = _working_copy_audit
        mut_ok, mut_why = m.git_pair_control()
    finally:
        m.git_pair_audit = orig
    if mut_ok is None:
        return False, "mutated: NOT ATTEMPTED (%s), so nothing was tested" % mut_why
    return (bool(clean_ok) and not mut_ok), "clean=%s mutated=%s %s" % (clean_ok, mut_ok, mut_why)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    print("%-56s %-8s %s" % ("mutation", "verdict", "which control caught it"))
    print("-" * 116)

    bad, why = disagreements()
    if bad != {}:
        print("%-56s %-8s %s" % ("none (the shipped code)", "FAIL", bad or why))
        print("\nFAIL -- the unmutated probe does not pass its own control, so nothing below means")
        print("        anything. Fix that first.")
        return 1
    print("%-56s %-8s %s" % ("none (the shipped code)", "PASS", "-"))

    caught = 0
    total_extra = [0]
    for label, patch in MUTATIONS:
        for name, fn in patch.items():
            setattr(m, name, fn)
        try:
            bad, why = disagreements()
        finally:
            for name, fn in ORIG.items():
                setattr(m, name, fn)
        hit = bool(bad)
        caught += hit
        print("%-56s %-8s %s" % (label, "caught" if hit else "MISSED", bad or why or "-"))

    gok, gwhy = git_pair_row()
    if gok is None:
        print("%-56s %-8s %s" % ("git_pair_audit reads the working copy", "SKIP", gwhy))
    else:
        caught += bool(gok)
        total_extra[0] = 1
        print("%-56s %-8s %s"
              % ("git_pair_audit reads the working copy", "caught" if gok else "MISSED", gwhy))

    print("-" * 116)
    print("%d of %d mutations caught" % (caught, len(MUTATIONS) + total_extra[0]))
    if caught != len(MUTATIONS) + total_extra[0]:
        print("A mutation nothing caught means the control is decorative on that axis.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
