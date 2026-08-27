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

    print("-" * 116)
    print("%d of %d mutations caught" % (caught, len(MUTATIONS)))
    if caught != len(MUTATIONS):
        print("A mutation nothing caught means the control is decorative on that axis.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
