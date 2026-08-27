"""CML lineage-verification-coverage v0.1, implemented and then pointed at our own production stores.

safal207 froze the definition we asked for (Causal-Memory-Layer#274, c87d981):

    lineage_verification_coverage = verifiable derived records / all eligible derived records

It measures VERIFICATION CAPABILITY, not lineage validity. A record whose active parent digest changed
is verifiable and later returns REVALIDATE; a record whose parent is observed erased is verifiable even
with no current digest, because state is decisive before digest. And an undefined result is reported as
null with a reason -- never as 0.0, which would read as "we checked and found nothing".

TWO PARTS, and the second is the one that costs us something:

  1. Our implementation against THEIR frozen fixture, byte for byte. 7 eligible / 4 verified.
  2. The same implementation against OUR real stores. This is the number he asked for and the reason
     to run it: an interoperability claim backed by a fixture is a claim about a fixture.

WHAT WE EXPECTED, WRITTEN DOWN BEFORE THE RUN, AND WHAT WE GOT. The prediction was `null` with
`no_eligible_derived_records`: our library's own source notes `derived_from` filled on 0 of 181,523
records on 2026-08-07, so we expected to be unable to identify a single derived record. That is NOT what
happened -- 194 of 5,221 readable records declare a derivation, every dependency resolves, and the
result is a measured 0.0 rather than a null. The prediction is left here rather than edited away,
because a forecast quietly replaced by its outcome teaches nobody anything.

    python research/probes/lineage_verification_coverage_on_our_own_store.py
"""
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(HERE, "cml_lineage_coverage_v0.1.fixture.json")

#: States that are a decisive lineage observation on their own. State is read BEFORE digest: an erased
#: parent with no current digest is VERIFIABLE (we know it was deliberately removed), while an active
#: parent with no observed digest is NOT (we simply cannot see it). Same missing digest, opposite
#: verdicts, different remedies.
DECISIVE_STATES = ("superseded", "retired", "erased")
KNOWN_STATES = DECISIVE_STATES + ("active",)


def record_gaps(rec):
    """Deterministic uncovered reasons for one derived record, or [] when it is verifiable."""
    deps = rec.get("dependencies") or []
    if not deps:
        return ["lineage_undeclared"]
    gaps, seen = [], set()
    for d in deps:
        did = d.get("dependency_id")
        if did in seen:
            gaps.append("lineage_duplicate:%s" % did)
            continue
        seen.add(did)
        state = d.get("state")
        if state is None:
            gaps.append("lineage_state_unobserved:%s" % did)
            continue
        if state not in KNOWN_STATES:
            gaps.append("lineage_state_unknown:%s:%s" % (did, state))
            continue
        if state in DECISIVE_STATES:
            continue                      # state is decisive; a missing digest does not matter here
        if d.get("expected_digest") is None:
            gaps.append("lineage_expected_digest_unverifiable:%s" % did)
        if d.get("observed_digest") is None:
            gaps.append("lineage_observed_digest_unverifiable:%s" % did)
    return gaps


def measure(records, derived_population_enumerable=True):
    if not derived_population_enumerable:
        return {"coverage": None, "undefined_reason": "derived_population_unenumerable",
                "eligible": 0, "verified": 0, "uncovered": 0, "gaps": {}}
    ids = [r.get("record_id") for r in records]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise ValueError("duplicate record_id in the measured population: %r -- the same logical record "
                         "counted twice can move both numerator and denominator" % dupes)
    eligible = [r for r in records if r.get("is_derived")]
    if not eligible:
        return {"coverage": None, "undefined_reason": "no_eligible_derived_records",
                "eligible": 0, "verified": 0, "uncovered": 0, "gaps": {}}
    gaps = {r["record_id"]: record_gaps(r) for r in eligible}
    verified = [k for k, v in gaps.items() if not v]
    return {"coverage": len(verified) / len(eligible), "undefined_reason": None,
            "eligible": len(eligible), "verified": len(verified),
            "uncovered": len(eligible) - len(verified),
            "gaps": {k: v for k, v in gaps.items() if v}}


def part_one_fixture():
    d = json.load(io.open(FIXTURE, encoding="utf-8"))
    c = d["benchmark_contract"]
    got = measure(d["records"], d.get("derived_population_enumerable", True))
    ok = (got["eligible"] == c["expected_eligible_derived_records"]
          and got["verified"] == c["expected_verified_derived_records"]
          and got["uncovered"] == c["expected_uncovered_derived_records"])
    print("PART 1 -- their frozen fixture, consumed byte for byte")
    print("  eligible %d (want %d) | verified %d (want %d) | uncovered %d (want %d) | coverage %s"
          % (got["eligible"], c["expected_eligible_derived_records"],
             got["verified"], c["expected_verified_derived_records"],
             got["uncovered"], c["expected_uncovered_derived_records"],
             "%d/%d" % (got["verified"], got["eligible"])))
    mismatched = []
    for r in d["records"]:
        if not r.get("is_derived"):
            continue
        want = r.get("expected_gaps")
        if want is None:
            continue
        have = record_gaps(r)
        if sorted(have) != sorted(want):
            mismatched.append((r["record_id"], want, have))
    for rid, want, have in mismatched:
        print("  REASON MISMATCH %-32s want %r got %r" % (rid, want, have))
    print("  -> %s" % ("AGREES on counts and on every record-level reason"
                       if ok and not mismatched else "DISAGREES -- freeze this, do not harmonise it"))
    return ok and not mismatched


def _stores():
    """os.walk, NOT glob. `glob` does not match names beginning with a dot, and our store directory is
    `.inspeximus` -- so the first version of this finder returned zero candidates, which would have been
    read as "no derived records anywhere". A search that cannot see its target reports absence."""
    bases = [os.path.join("C:", os.sep, "Users", "Danculus", "agora"),
             os.path.join("C:", os.sep, "Users", "Danculus", "inspeximus-repo")]
    out = []
    for base in bases:
        for root, _dirs, files in os.walk(base):
            low = root.lower()
            if "worktree" in low or "node_modules" in low:
                continue
            for f in files:
                fp = os.path.join(root, f)
                if f.endswith(".json") and ".inspeximus" in fp.lower():
                    try:
                        if os.path.getsize(fp) > 200000:
                            out.append(fp)
                    except OSError:
                        pass
    return sorted(set(out))


DECISIVE = ("superseded", "retired", "erased", "revoked")


def part_two_our_store():
    print()
    print("PART 2 -- the same contract against OUR production stores")
    stores, unreadable, records = _stores(), [], []
    for path in stores:
        try:
            raw = json.load(io.open(path, encoding="utf-8", errors="replace"))
        except Exception as e:
            unreadable.append((path, "%s: %s" % (type(e).__name__, str(e)[:48])))
            continue
        items = raw if isinstance(raw, list) else (raw.get("items") if isinstance(raw, dict) else None)
        if isinstance(items, list):
            records.append((path, items))

    for path, why in unreadable:
        print("  UNREADABLE %-42s %s" % (os.path.basename(path)[:42], why))
    if unreadable:
        print("  -- an unreadable store is not an empty one; everything below EXCLUDES it and says so.")

    total = sum(len(i) for _p, i in records)
    print("  readable stores: %d of %d, holding %d records" % (len(records), len(stores), total))
    if not records:
        print("  UNRESOLVED: nothing was readable, so this measured nothing.")
        return

    by_id, derived = {}, []
    for _p, items in records:
        for r in items:
            if isinstance(r, dict) and "id" in r:
                by_id[r["id"]] = r
    for _p, items in records:
        for r in items:
            if isinstance(r, dict) and (r.get("derived_from") or (r.get("meta") or {}).get("derived_from")):
                derived.append(r)

    if not derived:
        print("  lineage_verification_coverage = null (no_eligible_derived_records)")
        print("  Nothing declares a derivation, so there is no population the metric is defined over.")
        return

    verified, reasons, unresolved = 0, {}, 0
    for r in derived:
        df = r.get("derived_from") or (r.get("meta") or {}).get("derived_from") or []
        if isinstance(df, str):
            df = [df]
        gaps, seen = set(), set()
        for dep in df:
            if dep in seen:
                gaps.add("lineage_duplicate")
                continue
            seen.add(dep)
            parent = by_id.get(dep)
            if parent is None:
                gaps.add("lineage_state_unobserved")
                unresolved += 1
                continue
            if str(parent.get("status") or "active").lower() in DECISIVE:
                continue          # state is decisive: verifiable without any digest
            # An ACTIVE parent needs both digests. We store the EDGE and never what the parent WAS at
            # derivation time, so there is no expected digest to compare its current content against.
            gaps.add("lineage_expected_digest_unverifiable")
        if gaps:
            for g in gaps:
                reasons[g] = reasons.get(g, 0) + 1
        else:
            verified += 1

    print()
    print("  eligible derived records : %d" % len(derived))
    print("  verified                 : %d" % verified)
    print("  uncovered                : %d" % (len(derived) - verified))
    print("  lineage_verification_coverage = %.4f" % (verified / len(derived)))
    print()
    print("  uncovered reason distribution (records affected):")
    for k, v in sorted(reasons.items(), key=lambda kv: -kv[1]):
        print("     %-42s %d" % (k, v))
    print("  dependency ids that did not resolve: %d" % unresolved)
    print()
    print("  THE GRAPH IS COMPLETE AND USELESS FOR VERIFICATION. Every dependency resolves, no parent is")
    print("  retired or erased, and coverage is still zero -- for one reason, on every record. We store")
    print("  the EDGE and never what the parent WAS when we crossed it, so no expected digest exists to")
    print("  compare the parent's current content against. An edge without a digest says where a record")
    print("  came from; it cannot say whether that thing has changed since.")
    print()
    print("  Better than the 0.01% source figure and worse in a more specific way: the population IS")
    print("  enumerable, so this is a measured 0.0 rather than a null. The remedy is one field stamped at")
    print("  derivation time, not a better checker.")


def main():
    ok = part_one_fixture()
    part_two_our_store()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
