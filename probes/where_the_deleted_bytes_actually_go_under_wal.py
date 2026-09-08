"""A DELETE moves the bytes; it does not remove them. Under WAL, neither VACUUM nor a checkpoint alone.

WHY THIS EXISTS. A reply to a collaborator was about to say "a DELETE leaves the secret in the
database until a VACUUM". That sentence is wrong twice for the client under discussion, and the
severe-test rule says a claim ships only with a runnable measurement, so here it is.

The client sets `PRAGMA journal_mode=WAL` and `PRAGMA synchronous=FULL`. Under those settings the
payload never reaches the main database file at all while the WAL is unchecked, and the two obvious
remedies each fix half the problem:

  DELETE only                  the rows are gone from every query, and every copy is in the -wal
  DELETE + VACUUM              still in the -wal. A vacuum rewrites the database, not the log.
  DELETE + checkpoint          now in the .db instead. The checkpoint MOVED it into the durable file.
  DELETE + VACUUM + checkpoint gone from both

So a caller who runs one of them and checks with a query gets a clean answer and a file that still
holds the data. That is the failure this probe exists to name, and it is the same shape as the check
that motivated it: `still_recoverable` runs a SELECT, so it reports a row gone while the bytes stay
on disk.

CONTROLS, because a byte-counting probe is easy to write blind:
  * a POSITIVE control on every arm: the canary must be present BEFORE the delete, or the arm proves
    nothing and is reported void rather than passing;
  * a NEGATIVE control: a string never written anywhere must count zero, or the counter is matching
    something other than what it claims;
  * `-shm` is counted too, so "we only looked where we expected it" cannot hide a copy;
  * and the row count is asserted to reach zero, so an arm that failed to delete cannot pass as one
    that deleted cleanly.

WHAT THIS DOES NOT SHOW. One filesystem, one SQLite build, one page size, and payloads small enough
to live in the b-tree rather than on overflow pages. `secure_delete` is measured as a fifth arm
because it changes the answer, and it is off by default.
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
    return {k: v.count(needle) for k, v in files_of(p).items()}


def arm(label, steps, secure_delete=False):
    """One deletion strategy, with its own positive control."""
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
    negative = sum(counts(p, NEVER).values())
    c.execute("DELETE FROM producer_outbox")
    c.commit()
    for st in steps:
        c.execute(st)
        c.commit()
    after = counts(p)
    left = c.execute("SELECT COUNT(*) FROM producer_outbox").fetchone()[0]
    c.close()

    return {"arm": label, "steps": steps, "secure_delete": secure_delete,
            "positive_control": sum(before.values()) > 0, "negative_control": negative,
            "rows_after": left, "before": before, "after": after,
            "residue": sorted(k for k, v in after.items() if v)}


def main():
    arms = [
        arm("DELETE only", []),
        arm("DELETE + VACUUM", ["VACUUM"]),
        arm("DELETE + wal_checkpoint(TRUNCATE)", ["PRAGMA wal_checkpoint(TRUNCATE)"]),
        arm("DELETE + VACUUM + checkpoint", ["VACUUM", "PRAGMA wal_checkpoint(TRUNCATE)"]),
        arm("secure_delete + DELETE + both", ["VACUUM", "PRAGMA wal_checkpoint(TRUNCATE)"], True),
    ]
    print("\n  %-36s %-28s %s" % ("arm", "copies left", "where"))
    for a in arms:
        print("  %-36s %-28s %s"
              % (a["arm"], "db=%(db)d wal=%(-wal)d shm=%(-shm)d" % a["after"],
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
    check("DELETE_alone_leaves_every_copy_in_the_wal",
          by["DELETE only"]["after"]["-wal"] > 0 and by["DELETE only"]["after"]["db"] == 0,
          by["DELETE only"]["after"])
    check("VACUUM_does_not_touch_the_wal",
          by["DELETE + VACUUM"]["after"]["-wal"] > 0,
          "a vacuum rewrites the database, not the log")
    check("A_CHECKPOINT_ALONE_MOVES_IT_INTO_THE_DATABASE",
          by["DELETE + wal_checkpoint(TRUNCATE)"]["after"]["db"] > 0
          and by["DELETE + wal_checkpoint(TRUNCATE)"]["after"]["-wal"] == 0,
          by["DELETE + wal_checkpoint(TRUNCATE)"]["after"])
    check("only_vacuum_AND_checkpoint_clears_both",
          not by["DELETE + VACUUM + checkpoint"]["residue"],
          by["DELETE + VACUUM + checkpoint"]["after"])
    check("secure_delete_also_clears_it",
          not by["secure_delete + DELETE + both"]["residue"])

    out = {"probe": os.path.basename(__file__), "pragmas": ["journal_mode=WAL", "synchronous=FULL"],
           "rows": ROWS, "arms": arms, "checks": checks, "all_passed": ok,
           "note": "One filesystem, one SQLite build, one page size, payloads small enough to stay "
                   "in the b-tree. secure_delete is off by default and changes the answer."}
    path = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(out, indent=1))
    print("\n  %s   receipt: %s" % ("all checks passed" if ok else "FAILED", os.path.basename(path)))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
