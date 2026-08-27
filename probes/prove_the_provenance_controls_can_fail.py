# -*- coding: utf-8 -*-
"""Prove the controls in the provenance probe can FAIL, by breaking it on purpose.

A control that passes tells you nothing on its own; it has to be shown failing on the defect it
exists to catch. The first mutation here IS the defect @perseus-computing reported on r/RAG: an
`addressable` that accepts any http/https prefix. The control must catch it, and it does.

The last two cover the directions a fetcher fails in. Yes-to-everything passes a 200-only check,
and no-to-everything passes a 404-only check, so only a two-sided fixture kills both. No-to-
everything is not hypothetical: an earlier version of this probe had it, from a bare `except
Exception` over a missing import, and its answer was zero, which is also the headline.

Run:  python -X utf8 probes/prove_the_provenance_controls_can_fail.py
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "a_provenance_field_at_100_percent_with_one_distinct_value.py")

spec = importlib.util.spec_from_file_location("prov", TARGET)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

EXPECT = m.CONTROL_EXPECT
ORIG_ADDRESSABLE, ORIG_FETCHES = m.addressable, m.fetches


def disagreements():
    """Run the probe's own control fixture and return what the controls would report."""
    c, why = m.control()
    if c is None:
        return None, why
    return {k: (EXPECT[k], c[k]) for k in EXPECT if c[k] != EXPECT[k]}, ""


MUTATIONS = [
    ("addressable = the reported bug (any http/https prefix)",
     lambda loc: os.path.exists(loc) or str(loc).startswith(("http://", "https://")), None),
    ("addressable = always True", lambda loc: True, None),
    ("fetches = always True", None, lambda loc, timeout=5.0: True),
    ("fetches = always False", None, lambda loc, timeout=5.0: False),
]


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    print("%-54s %-8s %s" % ("mutation", "verdict", "which control caught it"))
    print("-" * 108)

    bad, why = disagreements()
    clean = bad == {}
    print("%-54s %-8s %s" % ("none (the shipped code)", "PASS" if clean else "FAIL", bad or why or "-"))
    if not clean:
        print("\nFAIL -- the unmutated probe does not pass its own control; nothing below means anything.")
        return 1

    caught = 0
    for label, a, f in MUTATIONS:
        m.addressable = a or ORIG_ADDRESSABLE
        m.fetches = f or ORIG_FETCHES
        try:
            bad, why = disagreements()
        finally:
            m.addressable, m.fetches = ORIG_ADDRESSABLE, ORIG_FETCHES
        hit = bool(bad)
        caught += hit
        print("%-54s %-8s %s" % (label, "caught" if hit else "MISSED", bad or why or "-"))

    print("-" * 108)
    print("%d of %d mutations caught" % (caught, len(MUTATIONS)))
    if caught != len(MUTATIONS):
        print("A mutation nothing caught means the control is decorative on that axis.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
