"""Where do deleted bytes go, and does it matter whether the connection is still open? It does.

WHY THIS EXISTS, and why its first version was wrong. It was written to correct a sentence saying "a
DELETE leaves the secret in the database until a VACUUM". The first version reported something more
elaborate: every copy in the `-wal` sidecar, a VACUUM that does not touch it, a checkpoint that moves
the bytes into the durable file. That was measured with ONE CONNECTION HELD OPEN for the whole arm.

The client this is about never does that. Its `_connect` is a context manager that opens, acts and
closes, and closing the last WAL connection checkpoints and unlinks the `-wal`. Between operations
there is no sidecar at all. So the elaborate answer described a state that deployment never reaches,
and the plain sentence it set out to correct was right.

Both are measured here, because the gap between them IS the finding:

  HELD OPEN   what a caller sees who keeps one connection for the life of a process
  CLOSED      what a caller sees who opens and closes per operation, as that client does

CONTROLS. Every arm carries a positive control: the canary must be present before the delete, or the
arm is void rather than passing. A negative control string never written must count zero. `-shm` is
counted too, so "we only looked where we expected it" cannot hide a copy. The row count must reach
zero, so an arm that failed to delete cannot pass as one that deleted cleanly. And the closed arms
assert that no `-wal` survives, which is the property whose absence made the first version wrong.

WHAT THIS DOES NOT SHOW. One filesystem, one SQLite build, one page size, and payloads small enough
to stay in the b-tree rather than spill to overflow pages. `secure_delete` is measured because it
changes the answer and is off by default.
"""
import json
import os
import sqlite3
import sys
import tempfile

CANARY = b"jane-canary-9f3a@example.com"
NEVER = b"this-string-was-never-written-anywhere"
ROWS = 30


def files_of(p):
    return {(sfx or "db"): (open(p + sfx, "rb").read() if os.path.exists(p + sfx) else b"")
            for sfx in ("", "-wal", "-shm")}


def counts(p, needle=CANARY):
    """None where a file does not exist, which is different from zero copies in it."""
    return {(sfx or "db"): (open(p + sfx, "rb").read().count(needle)
                            if os.path.exists(p + sfx) else None)
            for sfx in ("", "-wal", "-shm")}


def arm(label, steps, secure_delete=False, close_first=True):
    """One deletion strategy, with its own positive control.

    `close_first` is the whole point. True closes the connection before the files are read, which is
    what a client that opens and closes per operation produces. False reads them with the connection
    still open, which is what the first version of this probe did and why it got the answer wrong.
    """
    p = os.path.join(tempfile.mkdtemp(prefix="wal-residue-"), "t.db")
    c = sqlite3.connect(p)
    if secure_delete:
        c.execute("PRAGMA secure_delete=ON")
    # the client's own settings
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA synchronous=FULL")
    c.execute("CREATE TABLE producer_outbox(source_id TEXT PRIMARY KEY, payload BLOB, state TEXT)")
    for i in range(ROWS):
        c.execute("INSERT INTO producer_outbox VALUES(?,?,?)",
                  ("id-%d" % i, b'{"text":"Contact is ' + CANARY + b'"}', "delivered"))
    c.commit()

    before = counts(p)
    negative = sum(v for v in counts(p, NEVER).values() if v)
    c.execute("DELETE FROM producer_outbox")
    c.commit()
    for st in steps:
        c.execute(st)
        c.commit()
    left = c.execute("SELECT COUNT(*) FROM producer_outbox").fetchone()[0]
    if close_first:
        c.close()
        after = counts(p)
    else:
        after = counts(p)
        c.close()

    return {"arm": label, "steps": steps, "secure_delete": secure_delete,
            "connection_closed_before_reading": close_first,
            "positive_control": sum(v for v in before.values() if v) > 0, "negative_control": negative,
            "rows_after": left, "before": before, "after": after,
            "wal_survived": bool(after["-wal"]),
            "residue": sorted(k for k, v in after.items() if v)}


def main():
    arms = [
        # CLOSED: the lifecycle a client that opens and closes per operation actually produces.
        arm("closed: DELETE only", []),
        arm("closed: DELETE + VACUUM", ["VACUUM"]),
        arm("closed: DELETE + checkpoint", ["PRAGMA wal_checkpoint(TRUNCATE)"]),
        arm("closed: secure_delete + DELETE", [], True),
        # HELD OPEN: what the first version of this probe measured, kept so the gap is visible.
        arm("held open: DELETE only", [], close_first=False),
        arm("held open: DELETE + VACUUM", ["VACUUM"], close_first=False),
        arm("held open: DELETE + checkpoint", ["PRAGMA wal_checkpoint(TRUNCATE)"], close_first=False),
    ]
    print("\n  %-36s %-30s %s" % ("arm", "copies left", "where"))
    for a in arms:
        print("  %-36s %-30s %s"
              % (a["arm"],
                 "db=%s wal=%s shm=%s" % tuple("-" if a["after"][k] is None else a["after"][k]
                                               for k in ("db", "-wal", "-shm")),
                 ", ".join(a["residue"]) or "NONE"))

    ok, checks = True, []

    def check(name, cond, got=""):
        nonlocal ok
        ok = ok and bool(cond)
        checks.append({"check": name, "pass": bool(cond), "got": str(got)[:160]})
        print("  %-4s %-52s %s" % ("YES" if cond else "NO", name, got))

    print()
    check("CONTROL_every_arm_had_the_canary_before_deleting",
          all(a["positive_control"] for a in arms),
          [a["arm"] for a in arms if not a["positive_control"]] or "all five")
    check("CONTROL_a_string_never_written_counts_zero",
          all(a["negative_control"] == 0 for a in arms))
    check("CONTROL_every_arm_actually_emptied_the_table",
          all(a["rows_after"] == 0 for a in arms))

    by = {a["arm"]: a for a in arms}
    check("CONTROL_no_wal_survives_a_closed_connection",
          not any(a["wal_survived"] for a in arms if a["connection_closed_before_reading"]),
          "closing the last WAL connection checkpoints and unlinks the sidecar")
    check("CONTROL_a_held_open_connection_DOES_leave_one",
          any(a["wal_survived"] for a in arms if not a["connection_closed_before_reading"]),
          "so the two lifecycles are genuinely different states, not a labelling difference")

    check("CLOSED_delete_alone_leaves_the_bytes_in_the_database",
          by["closed: DELETE only"]["after"]["db"] > 0,
          by["closed: DELETE only"]["after"])
    check("CLOSED_and_a_VACUUM_clears_them",
          not by["closed: DELETE + VACUUM"]["residue"],
          by["closed: DELETE + VACUUM"]["after"])
    check("CLOSED_a_checkpoint_alone_does_not",
          by["closed: DELETE + checkpoint"]["after"]["db"] > 0,
          "a checkpoint moves the log into the database; it clears nothing")
    check("CLOSED_secure_delete_alone_also_clears_them",
          not by["closed: secure_delete + DELETE"]["residue"],
          by["closed: secure_delete + DELETE"]["after"])

    check("HELD_OPEN_gives_a_different_answer",
          by["held open: DELETE + VACUUM"]["after"]["-wal"] > 0
          and not by["closed: DELETE + VACUUM"]["residue"],
          "a VACUUM looks insufficient with the connection open and sufficient once it closes")

    out = {"probe": os.path.basename(__file__), "pragmas": ["journal_mode=WAL", "synchronous=FULL"],
           "rows": ROWS, "arms": arms, "checks": checks, "all_passed": ok,
           "note": "One filesystem, one SQLite build, one page size, payloads small enough to stay "
                   "in the b-tree. secure_delete is off by default and changes the answer. The first "
                   "version of this probe held one connection open for every arm and reported that a "
                   "VACUUM was insufficient; that state does not occur in a client that opens and "
                   "closes per operation, which is why both lifecycles are measured here."}
    path = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(out, indent=1))
    print("\n  %s   receipt: %s" % ("all checks passed" if ok else "FAILED", os.path.basename(path)))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
