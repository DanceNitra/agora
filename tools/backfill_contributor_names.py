"""Backfill orphaned contributor attribution in `collective_knowledge`.

WHAT WENT WRONG
---------------
`DUNGEON_AGENT_IDS` (server/agora/api/dungeon.py:22) lists only SIX of the eight
dungeon agents -- Artificer Rooke and Cartographer Wren were never added. The
promote path does:

    npc_id = DUNGEON_AGENT_IDS.get(body["npc"]) or body["npc"]   # agent_os_api.py:322

so for those two agents the lookup misses and `npc_id` falls back to the literal
NAME string. `_contribute_to_collective` (agent_os.py:1172) then resolves the
display name with `_get_npc_name(npc_id)`, which queries
`dungeon_npcs WHERE npc_id=?` -- a UUID column. A name never matches a UUID, the
lookup returns None, and the row is stored as:

    contributor_id   = 'Artificer Rooke'   (should be the UUID)
    contributor_name = ''                  (should be the name)

Both agents exist correctly in `dungeon_npcs` (...006 Rooke, ...008 Wren) and in
`NPC_UUIDS`; only the dungeon.py map was short. This tool repairs the DATA. The
source fix belongs in dungeon.py and is NOT part of this script -- running this
tool does not stop the defect from producing new orphans.

WHY IT MATTERS
--------------
`contributor_name` is the attribution field the rest of the brain actually reads:
`_mastery_record(r["contributor_name"] or "", ...)` (agent_os_api.py:647) and the
hypothesis-induction credit line `"by": (r["contributor_name"] or "?").strip()`
(hypothesis_induction.py:105). With an empty name, Rooke's and Wren's ~3,000
contributions earn them no mastery and no credit -- they read as anonymous work.

MEASURED ON THE LIVE BRAIN DB (server/agora.db, read-only, 2026-07-31)
----------------------------------------------------------------------
17,467 rows total in `collective_knowledge`
(discovery 10,431 | retracted 6,700 | hypothesis 335 | observation 1)

contributor_name distribution, knowledge_type='discovery':
    'King Aldric'       4321
    ''                  1417
    'High Priest Orin'  1072
    'Sergeant Voss'      961
    'Dame Elara'         919
    'Sage Mira'          918
    'Shadow Kael'        823

contributor_id on the rows whose contributor_name is empty:
    'Cartographer Wren' 1590   (discovery 726 + retracted 864)
    'Artificer Rooke'   1417   (discovery 691 + retracted 726)
    'claude'              10   (hypothesis 9 + observation 1)

So 3,007 rows across `discovery` and `retracted` hold an agent NAME where every
other row holds a UUID. Those 3,007 are what this tool repairs. There are ZERO
rows with a UUID contributor_id and an empty name, and the 326 'agora-scientist'
/ 'Hypothesis Engine' rows are a named non-agent writer and are already correct.

The 10 'claude' rows are a separate, benign non-agent writer. They are REPORTED
and never touched -- there is no canonical UUID to map them to, and inventing one
would be a fabrication, not a repair.

SAFETY
------
  * Dry run by default, and the dry run opens the DB READ-ONLY, so it cannot write
    even against the live brain. Writing requires an explicit --apply.
  * --apply refuses on either of two independent signals: the target IS a brain DB
    (by file identity, or the .../server/agora.db shape -- not a path string
    comparison, which a git worktree defeats), or an exclusive lock on it cannot be
    taken because something has it open. Stop the brain on :8000 first, point --db
    at a copy, or pass --allow-live. No invocation touches the brain by accident.
  * A timestamped, VERIFIED backup is taken before any write, via the sqlite3
    backup API rather than a file copy. This is not pedantry: the live DB runs in
    WAL mode and its -wal sidecar was 28 MB at the time of writing, so
    `shutil.copy2` of the .db alone would silently omit every commit still in the
    WAL and restore a stale database. The snapshot is written to a .partial name
    and renamed only after PRAGMA quick_check and a row-count match, so a failed
    copy cannot leave a truncated file wearing a valid backup name.
  * A sanity ceiling (--max-rows, default 5000) refuses the run if it is about to
    rewrite more rows than the defect can explain. A repair that touches more rows
    than expected is a bug, not a repair.
  * The UPDATEs run in ONE transaction, rolled back if the rows actually changed
    do not match the rows planned (a concurrent writer).
  * The name -> UUID map is READ from server/agora/agent_os/agent_os.py by AST
    parse, never hardcoded here, and is then cross-checked against the DB's own
    `dungeon_npcs` table. A disagreement aborts the run.

USAGE
-----
    python tools/backfill_contributor_names.py                     # dry run, live DB, read-only
    python tools/backfill_contributor_names.py --db copy.db        # dry run against a copy
    python tools/backfill_contributor_names.py --db copy.db --apply
    python tools/backfill_contributor_names.py --apply             # the real repair, brain stopped

Exit codes: 0 = ok, 2 = refused (ceiling / conflict / open DB), 1 = error.
"""

from __future__ import annotations

import argparse
import ast
import os
import re
import sqlite3
import sys
import urllib.parse
from datetime import datetime
from pathlib import Path

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB = os.path.join(REPO_ROOT, "server", "agora.db")
AGENT_OS_SOURCE = os.path.join(REPO_ROOT, "server", "agora", "agent_os", "agent_os.py")

# The defect can explain at most ~3,007 rows. Anything materially larger means the
# selector is matching something we did not intend -- refuse rather than rewrite.
DEFAULT_MAX_ROWS = 5000

# Rows are orphaned when the display name is missing. NULL and '' are both storable
# (the column defaults to ''), so every selector uses this one clause.
# The explicit character set matters: SQL TRIM() strips only U+0020, while Python's
# str.strip() also strips tab/newline/CR. With the bare TRIM, a contributor_name of
# '\t' rendered as "(empty)" in the table but was INVISIBLE to the planner -- never
# repaired, never listed as skipped, and the tool still reported "Repair complete".
# Both ends must agree on what empty means.
_BLANKS = "char(32)||char(9)||char(10)||char(13)"
EMPTY_NAME = ("(contributor_name IS NULL OR "
              "LENGTH(TRIM(contributor_name, %s)) = 0)" % _BLANKS)

_UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
                      r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


class Refused(Exception):
    """A guard tripped. Not a crash -- an intentional stop, reported as exit 2."""


# ---------------------------------------------------------------- name -> uuid

def load_npc_uuids(source_path: str) -> dict:
    """Read NPC_UUIDS out of agent_os.py by AST parse.

    Parsed rather than imported on purpose: `import agora.agent_os.agent_os` runs
    the package __init__ chain and needs the server's dependencies, which a repair
    tool must not require. Parsed rather than copied on purpose too -- a hardcoded
    map here would drift from the real one exactly when it matters.
    """
    if not os.path.exists(source_path):
        raise Refused("cannot read the canonical agent map: %s does not exist" % source_path)
    with open(source_path, "r", encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=source_path)

    node = None
    for stmt in tree.body:  # module level only -- do not pick up a local shadow
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name) and target.id == "NPC_UUIDS":
                    node = stmt.value
        elif isinstance(stmt, ast.AnnAssign):  # NPC_UUIDS: dict = {...}
            if isinstance(stmt.target, ast.Name) and stmt.target.id == "NPC_UUIDS":
                node = stmt.value
    if node is None:
        raise Refused("no module-level NPC_UUIDS assignment found in %s" % source_path)

    try:
        mapping = ast.literal_eval(node)
    except (ValueError, SyntaxError) as exc:
        raise Refused("NPC_UUIDS in %s is not a literal we can evaluate: %s" % (source_path, exc))

    if not isinstance(mapping, dict) or not mapping:
        raise Refused("NPC_UUIDS in %s is not a non-empty dict" % source_path)
    for name, uuid_value in mapping.items():
        if not isinstance(name, str) or not isinstance(uuid_value, str):
            raise Refused("NPC_UUIDS holds a non-string entry: %r -> %r" % (name, uuid_value))
        if not name.strip():
            raise Refused("NPC_UUIDS holds an empty agent name -- refusing to guess")
        if not _UUID_RE.match(uuid_value):
            raise Refused("NPC_UUIDS maps %r to %r, which is not a UUID" % (name, uuid_value))
    if len(set(mapping.values())) != len(mapping):
        raise Refused("NPC_UUIDS maps two agents to the same UUID -- refusing to guess")
    return mapping


def dungeon_roster(con: sqlite3.Connection) -> dict:
    """{npc_name: npc_id} from the DB's own roster, or None if the table is absent.

    The absence test is an explicit sqlite_master lookup rather than catching
    OperationalError off the SELECT: that except clause also swallowed "no such
    column" and "database is locked" and reported both as "no such table", which
    silently disabled this whole safety check on any schema drift.
    """
    if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND "
                       "name='dungeon_npcs'").fetchone():
        return None

    roster, ambiguous = {}, set()
    for npc_id, npc_name in con.execute("SELECT npc_id, npc_name FROM dungeon_npcs"):
        if npc_name is None:
            continue
        key = str(npc_name).strip()
        if key in roster and roster[key] != str(npc_id):
            ambiguous.add(key)
        roster[key] = str(npc_id)
    if ambiguous:
        raise Refused("dungeon_npcs maps %s to more than one npc_id -- the roster is "
                      "ambiguous, refusing to guess which is canonical"
                      % ", ".join(repr(a) for a in sorted(ambiguous)))
    return roster


def crosscheck_dungeon_npcs(name_to_uuid: dict, roster: dict) -> list:
    """Compare the code's map against the DB's own roster.

    Returns findings; the caller decides which abort. A MISSING table is only a
    warning -- the code map, not the DB, is the authority for the mapping itself.
    """
    if roster is None:
        return ["WARNING: no dungeon_npcs table in this DB -- map not cross-checked"]

    problems = []
    for name, uuid_value in sorted(name_to_uuid.items()):
        db_id = roster.get(name)
        if db_id is None:
            problems.append("WARNING: %r is in NPC_UUIDS but not in dungeon_npcs" % name)
        elif db_id != uuid_value:
            problems.append("CONFLICT: %r is %s in NPC_UUIDS but %s in dungeon_npcs"
                            % (name, uuid_value, db_id))
    return problems


def assert_plan_resolvable(plan: dict, roster: dict) -> None:
    """Every UUID we are about to WRITE must resolve back through dungeon_npcs.

    This is the whole point of the repair: `_get_npc_name` looks the row up by
    npc_id afterwards. Writing an id the roster cannot resolve would just relocate
    the defect. Scoped to the agents actually in the plan -- an agent missing from
    the roster that we are not writing stays a warning, not an abort.
    """
    if roster is None:
        return
    unresolvable = [(i["name"], i["uuid"]) for i in plan["by_name"] + plan["by_uuid"]
                    if roster.get(i["name"]) != i["uuid"]]
    if unresolvable:
        raise Refused(
            "the repair would write %d contributor_id(s) that dungeon_npcs cannot "
            "resolve: %s.\n         That moves the defect instead of fixing it."
            % (len(unresolvable), ", ".join("%s -> %s" % u for u in unresolvable)))


# ------------------------------------------------------------------- planning

def distribution(con: sqlite3.Connection) -> dict:
    """{contributor_name: {knowledge_type: rows}} -- the before/after table.

    Counts must ACCUMULATE, not assign. SQL groups on the raw contributor_name
    while this groups on the stripped one, so two SQL groups can collapse into one
    Python key ('King Aldric' and 'King Aldric '). Assigning made the second
    silently replace the first: measured on a fixture, one stray single-space row
    erased ten rows from the printed totals. That table is the only thing the
    operator judges the plan by, and the only verification of the write.
    """
    dist = {}
    for name, ktype, count in con.execute(
            "SELECT COALESCE(contributor_name, ''), COALESCE(knowledge_type, ''), COUNT(*) "
            "FROM collective_knowledge GROUP BY 1, 2"):
        bucket = dist.setdefault(str(name).strip(), {})
        key = str(ktype)
        bucket[key] = bucket.get(key, 0) + count
    return dist


def plan_repair(con: sqlite3.Connection, name_to_uuid: dict) -> dict:
    """Group every orphaned row by contributor_id and decide what to do with each.

    Exact GROUP BY counts, no LIKE guessing -- the counts printed here are the
    counts the UPDATEs later assert on.
    """
    uuid_to_name = {v: k for k, v in name_to_uuid.items()}

    by_name = []    # contributor_id holds an agent NAME  -> set both columns
    by_uuid = []    # contributor_id holds an agent UUID  -> set the name only
    untouched = []  # neither -- reported, never written  (e.g. 'claude')

    rows = con.execute(
        "SELECT contributor_id, COUNT(*) FROM collective_knowledge "
        "WHERE " + EMPTY_NAME + " GROUP BY contributor_id ORDER BY 2 DESC").fetchall()

    for contributor_id, count in rows:
        cid = "" if contributor_id is None else str(contributor_id)
        if cid in name_to_uuid:
            by_name.append({"contributor_id": cid, "name": cid,
                            "uuid": name_to_uuid[cid], "rows": count})
        elif cid in uuid_to_name:
            # The same orphan class in the opposite shape: a correct UUID that never
            # got its display name. Zero such rows exist today; handled here so a
            # second variant of this defect does not need a second tool.
            by_uuid.append({"contributor_id": cid, "name": uuid_to_name[cid],
                            "uuid": cid, "rows": count})
        else:
            untouched.append({"contributor_id": cid, "rows": count})

    plan = {"by_name": by_name, "by_uuid": by_uuid, "untouched": untouched}
    plan["to_change"] = sum(i["rows"] for i in by_name) + sum(i["rows"] for i in by_uuid)

    # Per-knowledge_type breakdown, so the projected 'after' table is a real
    # projection: an orphan's rows are spread across `discovery` and `retracted`
    # and they move to the agent's name in exactly that proportion.
    for item in by_name + by_uuid + untouched:
        item["type_split"] = {
            str(ktype): count for ktype, count in con.execute(
                "SELECT COALESCE(knowledge_type, ''), COUNT(*) FROM collective_knowledge "
                "WHERE " + EMPTY_NAME + " AND contributor_id = ? GROUP BY 1",
                (item["contributor_id"],))}
    return plan


def project_after(before: dict, plan: dict) -> dict:
    """Compute the post-repair distribution from the exact plan counts.

    A NEGATIVE residual is not cosmetic and is never swallowed: it means the plan
    claims to move more rows of a type than the empty bucket holds, i.e. the
    `before` read and the `plan` read saw different snapshots (a concurrent
    writer). Deleting it, as an earlier version did, hid the disagreement and
    printed a TOTAL that no longer conserved.
    """
    after = {name: dict(types) for name, types in before.items()}
    empty = after.setdefault("", {})
    for item in plan["by_name"] + plan["by_uuid"]:
        target = after.setdefault(item["name"], {})
        for ktype, count in item["type_split"].items():
            target[ktype] = target.get(ktype, 0) + count
            empty[ktype] = empty.get(ktype, 0) - count

    negative = {k: v for k, v in empty.items() if v < 0}
    if negative:
        raise Refused("the projected result went negative %r -- the distribution read and "
                      "the plan read disagree, which means something else is writing to "
                      "this DB. Re-run when it is quiet." % negative)

    for ktype in [k for k, v in list(empty.items()) if v == 0]:
        del empty[ktype]
    if not empty:
        after.pop("", None)
    return after


# -------------------------------------------------------------------- display

def ascii_cell(value) -> str:
    """Force a cell to ASCII, escaping anything else.

    The table's own borders were always ASCII, but the CELLS are contributor names
    and ids read from the database, and this console is cp1250: a single em dash in
    a name raised UnicodeEncodeError. That would abort the dry run before it printed
    the plan and -- worse -- abort the AFTER table which prints AFTER the commit,
    leaving the repair applied but unverified. Escaping happens before the width
    measurement so widths and output cannot disagree.
    """
    return str(value).encode("ascii", "backslashreplace").decode("ascii")


def render_table(headers: list, rows: list) -> str:
    """Minimal ASCII table."""
    headers = [ascii_cell(h) for h in headers]
    rows = [[ascii_cell(c) for c in row] for row in rows]
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    rule = "+" + "+".join("-" * (w + 2) for w in widths) + "+"

    def line(cells):
        parts = [" " + (c.ljust(widths[i]) if i == 0 else c.rjust(widths[i])) + " "
                 for i, c in enumerate(cells)]
        return "|" + "|".join(parts) + "|"

    out = [rule, line(headers), rule]
    out.extend(line(r) for r in rows)
    out.append(rule)
    return "\n".join(out)


def knowledge_types(dist: dict) -> list:
    seen = set()
    for types in dist.values():
        seen.update(types)
    ordered = [k for k in ("discovery", "retracted", "hypothesis", "observation") if k in seen]
    ordered.extend(sorted(seen - set(ordered)))
    return ordered


def print_distribution(title: str, dist: dict) -> None:
    ktypes = knowledge_types(dist)
    rows = []
    for name in sorted(dist, key=lambda n: (-sum(dist[n].values()), n)):
        types = dist[name]
        rows.append([name or "(empty)", sum(types.values())]
                    + [types.get(k, 0) for k in ktypes])
    rows.append(["TOTAL", sum(sum(t.values()) for t in dist.values())]
                + [sum(t.get(k, 0) for t in dist.values()) for k in ktypes])
    print("\n" + title)
    print(render_table(["contributor_name", "rows"] + ktypes, rows))


def print_plan(plan: dict) -> None:
    if plan["by_name"] or plan["by_uuid"]:
        rows = [[i["contributor_id"], i["rows"], i["uuid"], i["name"]] for i in plan["by_name"]]
        rows += [[i["contributor_id"], i["rows"], "(unchanged)", i["name"]] for i in plan["by_uuid"]]
        print("\nREPAIR PLAN -- orphaned rows (contributor_name is empty):")
        print(render_table(["contributor_id (current)", "rows",
                            "contributor_id (new)", "contributor_name (new)"], rows))
    else:
        print("\nREPAIR PLAN -- nothing to repair: no orphaned row maps to a known agent.")

    if plan["untouched"]:
        rows = []
        for item in plan["untouched"]:
            cid = item["contributor_id"]
            # A padded id ('Artificer Rooke ') is skipped for safety, but calling it
            # "not a dungeon agent" would be false and would lead an operator to
            # dismiss a real orphan. Name the actual reason.
            reason = ("looks like a padded agent name -- inspect by hand"
                      if cid.strip() and cid.strip() != cid
                      else "left alone -- not a dungeon agent")
            rows.append([cid or "(empty)", item["rows"], reason])
        print("\nREPORTED, NOT TOUCHED -- empty name, but no canonical agent to map to:")
        print(render_table(["contributor_id", "rows", "action"], rows))


# ---------------------------------------------------------------------- write

def is_live_brain_db(db_path: str) -> bool:
    """Is this the brain's own database, however it was reached?

    NOT a normcase comparison against DEFAULT_DB: that constant is derived from
    __file__, so a copy of this script in a git worktree resolves it to a path that
    does not exist, the check silently never fires, and the guard degrades from two
    signals to one exactly where an operator is least likely to notice. Identity via
    samefile, plus a shape test so the .../server/agora.db layout is recognised no
    matter which checkout, symlink, subst drive or UNC path leads to it.
    """
    try:
        if os.path.exists(DEFAULT_DB) and os.path.samefile(db_path, DEFAULT_DB):
            return True
    except OSError:
        pass
    path = Path(db_path)
    return path.name == "agora.db" and path.parent.name == "server"


def is_open_elsewhere(db_path: str) -> bool:
    """True if another connection currently holds this database.

    The obvious test -- "are the -wal/-shm sidecars present?" -- is WRONG, and was
    measured wrong: a read-only connection (this tool's own dry run) leaves them
    behind, because it lacks the write access needed to checkpoint and unlink them.
    That made a plain dry-run-then-apply refuse itself.

    The accurate probe is to ask for the exclusive lock we would need anyway. In
    WAL mode `locking_mode = EXCLUSIVE` has to take over the shared-memory index,
    so it fails with SQLITE_BUSY if ANY other connection has the file open, even an
    idle reader. Measured on a copy of the live DB: leftover sidecars with no
    holder -> acquires the lock; one idle open reader -> "database is locked".

    The probe is exact for WAL (which is how the brain DB runs). Under a rollback
    journal an idle connection holds no lock and would go undetected, which is why
    the live-path check below is kept as an independent second signal.
    """
    try:
        con = sqlite3.connect(db_path, timeout=0)
    except sqlite3.Error:
        return True  # cannot even open it -- treat as in use
    try:
        con.execute("PRAGMA locking_mode = EXCLUSIVE")
        con.execute("BEGIN IMMEDIATE")
        con.rollback()
        return False
    except sqlite3.Error:
        return True
    finally:
        con.close()  # releases the exclusive lock immediately


def make_backup(db_path: str) -> str:
    """Consistent, VERIFIED, timestamped snapshot via the sqlite3 backup API.

    Deliberately NOT shutil.copy2: this DB runs in WAL mode with a multi-megabyte
    -wal sidecar, and copying the .db alone would produce a backup missing every
    commit still in the WAL -- a restore that silently loses recent rows is worse
    than no backup at all. (Verified: a row committed but not yet checkpointed is
    present in a backup-API snapshot.)

    Written to a .partial name and only renamed once it passes an integrity check
    and a row-count match. A 262 MB copy can fail halfway on a full disk, and a
    truncated file sitting there under a valid-looking backup name is a trap: the
    operator would reach for it precisely when it cannot help.
    """
    backup_path = "%s.backup-%s" % (db_path, datetime.now().strftime("%Y%m%d-%H%M%S"))
    if os.path.exists(backup_path):
        raise Refused("backup path already exists, refusing to overwrite: %s" % backup_path)
    partial = backup_path + ".partial"

    source = sqlite3.connect(db_path)
    try:
        try:
            dest = sqlite3.connect(partial)
            try:
                source.backup(dest)
            finally:
                dest.close()

            check = sqlite3.connect(partial)
            try:
                status = check.execute("PRAGMA quick_check").fetchone()[0]
                if status != "ok":
                    raise Refused("the backup failed its integrity check (%s)" % status)
                copied = check.execute("SELECT COUNT(*) FROM collective_knowledge").fetchone()[0]
            finally:
                check.close()
            live = source.execute("SELECT COUNT(*) FROM collective_knowledge").fetchone()[0]
            if copied != live:
                raise Refused("the backup holds %d rows but the source has %d -- "
                              "not a usable restore point" % (copied, live))
            os.replace(partial, backup_path)
        except BaseException:
            if os.path.exists(partial):
                try:
                    os.remove(partial)
                except OSError:
                    pass
            raise
    finally:
        source.close()
    return backup_path


def apply_repair(con: sqlite3.Connection, plan: dict) -> int:
    """Run every UPDATE in ONE transaction, asserting each rowcount.

    The rowcount assertion is the check that cannot quietly pass: if anything
    changed the table between planning and writing, the numbers disagree and the
    whole transaction is rolled back rather than half-applied.

    `updated_at` is deliberately left alone. This repairs WHO wrote the row, not
    the row's content, and several readers order this table by time.
    """
    changed = 0
    con.execute("BEGIN IMMEDIATE")
    try:
        for item in plan["by_name"]:
            cur = con.execute(
                "UPDATE collective_knowledge SET contributor_id = ?, contributor_name = ? "
                "WHERE contributor_id = ? AND " + EMPTY_NAME,
                (item["uuid"], item["name"], item["contributor_id"]))
            if cur.rowcount != item["rows"]:
                raise Refused("planned %d rows for %r but the UPDATE touched %d -- rolled back"
                              % (item["rows"], item["contributor_id"], cur.rowcount))
            changed += cur.rowcount

        for item in plan["by_uuid"]:
            cur = con.execute(
                "UPDATE collective_knowledge SET contributor_name = ? "
                "WHERE contributor_id = ? AND " + EMPTY_NAME,
                (item["name"], item["contributor_id"]))
            if cur.rowcount != item["rows"]:
                raise Refused("planned %d rows for %s but the UPDATE touched %d -- rolled back"
                              % (item["rows"], item["contributor_id"], cur.rowcount))
            changed += cur.rowcount
    except BaseException:
        con.rollback()
        raise
    con.commit()
    return changed


# ----------------------------------------------------------------------- main

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Repair orphaned contributor attribution in collective_knowledge. "
                    "Dry run unless --apply is given.")
    parser.add_argument("--db", default=DEFAULT_DB,
                        help="SQLite DB to inspect or repair (default: server/agora.db)")
    parser.add_argument("--apply", action="store_true",
                        help="actually write. Without this the run is read-only.")
    parser.add_argument("--allow-live", action="store_true",
                        help="override both write guards: repair the repo's server/agora.db, "
                             "and/or a DB something else has open. Stop the brain on :8000 first.")
    parser.add_argument("--max-rows", type=int, default=DEFAULT_MAX_ROWS,
                        help="sanity ceiling; refuse if more rows than this would change "
                             "(default: %d)" % DEFAULT_MAX_ROWS)
    parser.add_argument("--agent-os-source", default=AGENT_OS_SOURCE,
                        help="path to agent_os.py, the source of the canonical NPC_UUIDS map")
    return parser


def connect_readonly(db_path: str) -> sqlite3.Connection:
    """Open read-only, so a dry run cannot write even if something below is wrong.

    The URI is built by hand rather than with Path.as_uri(), which renders a UNC
    path as file://server/share/... -- SQLite reads 'server' as a URI authority and
    rejects it. quote() still percent-encodes '?' and '#' so they cannot be mistaken
    for the query separator.
    """
    encoded = urllib.parse.quote(db_path.replace("\\", "/"))
    return sqlite3.connect("file:" + encoded + "?mode=ro", uri=True)


def run(args) -> int:
    db_path = os.path.abspath(args.db)
    if not os.path.exists(db_path):
        print("ERROR: no such database: %s" % db_path)
        return 1

    print("backfill_contributor_names -- %s" % ("APPLY" if args.apply else "DRY RUN"))
    print("  db            : %s" % db_path)
    print("  agent map from: %s" % os.path.abspath(args.agent_os_source))
    print("  sanity ceiling: %d rows" % args.max_rows)

    # Two INDEPENDENT signals that this is the owner's running system; either one
    # refuses. Neither alone is sufficient: the lock probe misses a non-WAL idle
    # connection, and the path check misses a live DB reached by any other path
    # (a git worktree resolves DEFAULT_DB somewhere else entirely).
    if args.apply and not args.allow_live:
        if is_live_brain_db(db_path):
            raise Refused(
                "that is the live brain DB (server/agora.db) and --allow-live was not\n"
                "         given. The brain on :8000 holds this file open. Stop it first, or\n"
                "         point --db at a copy.")
        if is_open_elsewhere(db_path):
            raise Refused(
                "the database is OPEN by another process right now (an exclusive lock\n"
                "         could not be taken). That is almost certainly a running brain.\n"
                "         Stop it first, point --db at a copy, or pass --allow-live if you\n"
                "         are certain nothing else is writing.")

    name_to_uuid = load_npc_uuids(args.agent_os_source)
    print("  known agents  : %d" % len(name_to_uuid))

    con = sqlite3.connect(db_path, timeout=30) if args.apply else connect_readonly(db_path)

    try:
        if args.apply:
            con.execute("PRAGMA busy_timeout = 30000")

        roster = dungeon_roster(con)
        problems = crosscheck_dungeon_npcs(name_to_uuid, roster)
        for problem in problems:
            print("  %s" % problem)
        if any(p.startswith("CONFLICT") for p in problems):
            raise Refused("the code's agent map disagrees with dungeon_npcs -- fix that "
                          "before repairing any row")

        before = distribution(con)
        print_distribution("BEFORE -- contributor_name distribution:", before)

        plan = plan_repair(con, name_to_uuid)
        print_plan(plan)
        # Scoped here, not at the cross-check: only the agents we are actually about
        # to write have to resolve.
        assert_plan_resolvable(plan, roster)

        print("\nrows to change: %d (ceiling %d)" % (plan["to_change"], args.max_rows))
        if plan["to_change"] > args.max_rows:
            raise Refused(
                "would rewrite %d rows, above the sanity ceiling of %d.\n"
                "         A repair that touches more rows than expected is a bug, not a\n"
                "         repair. Re-read the plan above; raise --max-rows only once every\n"
                "         line of it is genuinely intended."
                % (plan["to_change"], args.max_rows))

        if plan["to_change"] == 0:
            print("\nNothing to do -- attribution is already consistent.")
            print_distribution("AFTER -- unchanged:", before)
            return 0

        if not args.apply:
            print_distribution("AFTER (PROJECTED -- dry run, nothing was written):",
                               project_after(before, plan))
            print("\nDry run only. Re-run with --apply to write.")
            return 0

        backup_path = make_backup(db_path)
        name = os.path.basename(db_path)
        print("\nbackup written: %s" % backup_path)
        # Sidecars FIRST: a stale -wal left next to a freshly restored file would be
        # replayed onto it by the next opener, undoing the restore.
        print("  restore with: delete the %s-wal/-shm sidecars, then copy that file "
              "over %s" % (name, name))

        print("rows changed  : %d" % apply_repair(con, plan))
        print_distribution("AFTER -- contributor_name distribution:", distribution(con))

        residue = plan_repair(con, name_to_uuid)
        if residue["to_change"] != 0:
            print("\nWARNING: %d orphaned rows still map to a known agent after the repair."
                  % residue["to_change"])
            return 1
        print("\nRepair complete. Re-running is a no-op (0 rows to change).")
        return 0
    finally:
        con.close()


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run(args)
    except Refused as exc:
        print("\nREFUSED: %s" % exc)
        return 2
    except Exception as exc:  # documented as exit 1 -- report it, do not traceback
        print("\nERROR: %s: %s" % (type(exc).__name__, exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
