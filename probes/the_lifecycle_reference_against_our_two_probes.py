"""Point our two erasure probes at Neeraj's offline lifecycle reference, hostilely, and record what held.

WHY. On DanceNitra/agora discussion #2 (2026-09-09) I asked for the reference so that two probes of
ours could be aimed at his sequence rather than at my own receiver: one on readable remnants under
SQLite WAL across two connection lifecycles, one on whether an erasure verdict follows from the
evidence or from a reported count. He published `lifecycle-reference-v0.1`
(yadu9989/memstrata-inspeximus-connector, research/lifecycle_reference.py, MIT) on 2026-09-20 and
said the part he most wants broken is verification bound to the operation. This is the attempt.

WHAT IS RUN. His `Coordinator.execute` on his `SQLiteTarget` fixtures inside his own
`SyntheticWorkspace`, imported from a checkout at the tag. Every arm below is a shape our probes
carry, plus three the reference invites that ours did not have:

  count arms      A deletes and reports 2 / B does not delete and reports 2 / C deletes and reports 0.
                  His coordinator never reads a count, so the arms are adapters whose `apply` does or
                  does not delete; the reported count is a field they print and nobody consults.
  lying inspect   an adapter whose `inspect` returns 0 rows without deleting. The logical check is
                  fooled; the byte probe must not be.
  lying byte probe  an adapter that overrides `byte_probe` to report 0 matches without deleting. The
                  coordinator calls the target's OWN byte probe, so this asks whether verification is
                  performed by the coordinator or delegated to the thing being verified.
  wal held open   a second connection holds a read transaction on a WAL-mode target while the erase
                  runs. `apply` runs `PRAGMA wal_checkpoint(TRUNCATE)` and raises on busy. Then the
                  reader closes and the same operation id is retried.
  weaker marker   the same operation id retried with fewer probe values (must be refused), and a NEW
                  operation id with no probe values at all (must not complete).
  no vacuum, no secure_delete  the freed-page case our WAL probe measures: does the verdict see bytes
                  that survive in the file after the row is gone?

CONTROLS. The A arm must complete (the harness can pass). The B arm must not (the harness can fail).
A marker absent from the payload must fail calibration before any deletion (his positive control).
Every file read is inside his workspace root, asserted per arm.

WHAT THIS CANNOT SHOW. Anything beyond his synthetic SQLite fixtures: no live receiver, no hardware,
no backups. A verdict of "held" here is a verdict about this reference on this machine and tag.

    python probes/the_lifecycle_reference_against_our_two_probes.py --ref <checkout of the tag>
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sqlite3
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
KEY = b"agora-probe-key-that-is-at-least-thirty-two-bytes-long"
MARKER = "AGORA-PROBE-MARKER-7f3c9e"
ABSENT = "AGORA-ABSENT-MARKER-000000"


def _load(ref):
    sys.path.insert(0, os.path.join(ref, "research"))
    import lifecycle_reference as L  # noqa: E402
    return L


def _file_has(path, marker) -> bool:
    for suffix in ("", "-wal", "-shm", "-journal"):
        p = Path(str(path) + suffix)
        if p.exists() and marker.encode("utf-8") in p.read_bytes():
            return True
    return False


def _fixture(L, ws, adapter_cls, *, wal=False, secure=True, vacuum=True, kinds=None):
    targets = tuple(L.Target(k, k) for k in sorted(kinds or L.KINDS))
    stores = {}
    for t in targets:
        kw = {"wal": wal, "secure": secure, "vacuum": vacuum}
        stores[t.name] = adapter_cls(ws, t, **kw)
    c = L.Coordinator(ws, stores, hmac_key=KEY, authorize=lambda p, r: p == "operator")
    for s in stores.values():
        s.seed(c.scope("tenant", "subject"), c.record("record"), MARKER * 50)
    req = L.Request("op-" + adapter_cls.__name__.lower(), "tenant", "subject", "erased", targets)
    return c, stores, req


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True, help="checkout of yadu9989/memstrata-inspeximus-connector at lifecycle-reference-v0.1")
    a = ap.parse_args()
    L = _load(os.path.abspath(a.ref))
    out = {"probe": os.path.basename(__file__), "tag": "lifecycle-reference-v0.1", "arms": {}, "controls": {}}

    class Deletes(L.SQLiteTarget):
        reported = 2

    class DoesNotDelete(L.SQLiteTarget):
        reported = 2

        def apply(self, action, scope_key, record_key=None):
            return None

    class DeletesReportsZero(L.SQLiteTarget):
        reported = 0

    class LyingInspect(L.SQLiteTarget):
        def apply(self, action, scope_key, record_key=None):
            return None

        def inspect(self, scope_key, record_key=None):
            return {"rows": 0, "current": 0}

    class LyingByteProbe(L.SQLiteTarget):
        def apply(self, action, scope_key, record_key=None):
            return None

        def inspect(self, scope_key, record_key=None):
            return {"rows": 0, "current": 0}

        def byte_probe(self, values):
            return {"status": "checked", "matched": 0, "files": [], "probe_hits": [False] * len(values)}

    def run(name, cls, **kw):
        with L.SyntheticWorkspace() as ws:
            c, stores, req = _fixture(L, ws, cls, **kw)
            r = c.execute(req, "operator", probe_values=(MARKER,))
            remains = {n: _file_has(s.path, MARKER) for n, s in stores.items()}
            inside = all(Path(str(s.path)).resolve().parent == ws.root for s in stores.values())
            row = {"complete": r["complete"], "state": r["state"],
                   "statuses": sorted({e["status"] for e in r["entries"].values()}),
                   "marker_still_in_any_file": any(remains.values()),
                   "reported_count_printed_by_adapter": getattr(cls, "reported", None),
                   "files_inside_workspace": inside}
            out["arms"][name] = row
            print("  %-22s complete=%-5s state=%-11s statuses=%s marker_in_file=%s"
                  % (name, row["complete"], row["state"], row["statuses"], row["marker_still_in_any_file"]))
            return row

    print("count arms (the count is printed by the adapter and consulted by nobody):")
    A = run("A_deletes_reports_2", Deletes)
    B = run("B_nodelete_reports_2", DoesNotDelete)
    C = run("C_deletes_reports_0", DeletesReportsZero)
    print("lying adapters:")
    LI = run("lying_inspect", LyingInspect)
    LB = run("lying_byte_probe", LyingByteProbe)
    print("freed pages:")
    NV = run("no_vacuum_no_secure_delete", Deletes, secure=False, vacuum=False)

    # WAL held open: a reader with an open transaction on the 'current' target during the erase.
    print("wal held open:")
    with L.SyntheticWorkspace() as ws:
        c, stores, req = _fixture(L, ws, Deletes, wal=True)
        target = stores["current"]
        reader = sqlite3.connect(target.path, isolation_level=None, timeout=0.2)
        reader.execute("BEGIN")
        reader.execute("SELECT count(*) FROM records").fetchone()      # snapshot held open
        r1 = c.execute(req, "operator", probe_values=(MARKER,))
        held = {"complete": r1["complete"], "state": r1["state"],
                "current_status": r1["entries"]["current"]["status"],
                "current_error": r1["entries"]["current"].get("error_class"),
                "marker_in_current_files": _file_has(target.path, MARKER)}
        reader.rollback(); reader.close()
        r2 = c.execute(req, "operator", probe_values=(MARKER,))          # same operation id, retried
        held["retry_after_reader_closed"] = {"complete": r2["complete"], "state": r2["state"],
                                             "marker_in_current_files": _file_has(target.path, MARKER)}
        out["arms"]["wal_held_open"] = held
        print("  during: complete=%s state=%s current=%s/%s marker_in_file=%s" % (
            held["complete"], held["state"], held["current_status"], held["current_error"], held["marker_in_current_files"]))
        print("  retry : complete=%s state=%s marker_in_file=%s" % (
            r2["complete"], r2["state"], held["retry_after_reader_closed"]["marker_in_current_files"]))

    # Weaker marker on retry, and a fresh operation with no marker.
    print("verification bound to the operation:")
    with L.SyntheticWorkspace() as ws:
        c, stores, req = _fixture(L, ws, DoesNotDelete)
        r1 = c.execute(req, "operator", probe_values=(MARKER,))
        try:
            c.execute(req, "operator", probe_values=())
            weaker = "ACCEPTED"
        except ValueError as e:
            weaker = "refused: " + str(e)
        fresh = L.Request("op-fresh-no-marker", "tenant", "subject", "erased", req.targets)
        r3 = c.execute(fresh, "operator", probe_values=())
        # an absent marker is caught inside execute, per target, and lands in the receipt
        r4 = c.execute(L.Request("op-absent", "tenant", "subject", "erased", req.targets), "operator", probe_values=(ABSENT,))
        bound = {"first_incomplete": not r1["complete"], "weaker_marker_same_op": weaker,
                 "fresh_op_no_marker_complete": r3["complete"], "fresh_op_no_marker_state": r3["state"],
                 "absent_marker_statuses": sorted({e["status"] for e in r4["entries"].values()}),
                 "absent_marker_calibration": sorted({(e.get("calibration") or {}).get("status", "-") for e in r4["entries"].values()}),
                 "absent_marker_complete": r4["complete"]}
        out["arms"]["bound_to_operation"] = bound
        for k, v in bound.items():
            print("  %s: %s" % (k, v))

    v = out["controls"]
    v["CONTROL_the_deleting_arm_completes"] = A["complete"] and not A["marker_still_in_any_file"]
    v["CONTROL_the_non_deleting_arm_is_incomplete"] = (not B["complete"]) and B["marker_still_in_any_file"]
    v["CONTROL_every_file_read_was_inside_his_workspace"] = all(r.get("files_inside_workspace", True) for r in out["arms"].values() if isinstance(r, dict))
    v["the_verdict_does_not_follow_the_count"] = C["complete"] and not B["complete"]
    v["a_lying_inspect_is_caught_by_the_byte_probe"] = not LI["complete"] and LI["marker_still_in_any_file"]
    v["a_lying_byte_probe_PASSES_while_the_bytes_remain"] = LB["complete"] and LB["marker_still_in_any_file"]
    v["freed_pages_are_seen_without_vacuum_or_secure_delete"] = (not NV["complete"]) and NV["marker_still_in_any_file"]
    v["or_freed_pages_left_nothing_readable"] = (not NV["marker_still_in_any_file"])
    v["a_held_open_wal_reader_makes_the_erase_incomplete"] = not held["complete"]
    v["and_the_retry_after_the_reader_closes_completes"] = held["retry_after_reader_closed"]["complete"] and not held["retry_after_reader_closed"]["marker_in_current_files"]
    v["a_weaker_marker_on_the_same_operation_is_refused"] = bound["weaker_marker_same_op"].startswith("refused")
    v["a_fresh_operation_with_no_marker_cannot_complete"] = not bound["fresh_op_no_marker_complete"]
    v["an_absent_marker_fails_calibration_before_purge"] = "positive_control_failed" in bound["absent_marker_calibration"] and not bound["absent_marker_complete"]
    print()
    for k, ok in v.items():
        print("  %s  %s" % ("YES" if ok else "no ", k))
    out["python"] = sys.version.split()[0]
    out["sqlite"] = sqlite3.sqlite_version
    json.dump(out, io.open(os.path.join(HERE, os.path.basename(__file__).replace(".py", ".result.json")), "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)
    hard = [k for k in v if k.startswith("CONTROL") and not v[k]]
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())
