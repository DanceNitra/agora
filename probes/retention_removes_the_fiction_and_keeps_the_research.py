"""Does the retention policy delete the fiction, and does it leave the research alone?

WHY. The policy pruned artifacts by TYPE, keeping 'research', 'writing' and 'analysis'. The
auto-task generator stamps its output with exactly those types, so the clause meant to preserve
research was preserving 42,866 fantasy artifacts, "Decode the rune tablet" among them 4,227 times.
`tasks` and `events` were not in the policy at all and held every row back to 2026-06-12.

This is a two-sided manipulation check, run on a COPY. The live database is never touched.
  * INTENDED CHANGE: auto-task artifacts, task rows and event rows older than the window are gone.
  * NO UNINTENDED CHANGE: every knowledge table keeps its exact row count, and a REAL artifact
    older than the window survives.
  * THE CONTROL CAN FIRE: a synthetic real artifact is planted beyond the window before the run.
    If the prune took it, the policy is over-broad and this probe must fail. Without the plant, a
    policy that deleted everything would still pass the knowledge-table check, because artifacts
    are not a knowledge table.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import uuid

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SERVER = os.path.join(ROOT, "server")
LIVE = os.path.join(SERVER, "agora.db")
OUT = os.path.join(HERE, "retention_removes_the_fiction_and_keeps_the_research.result.json")
sys.path.insert(0, SERVER)

KNOWLEDGE = ("collective_knowledge", "research_findings", "agent_memories", "quests",
             "agent_identities")


def refuse(why):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    raise SystemExit(2)


def counts(db):
    c = sqlite3.connect(db)
    out = {}
    for t in list(KNOWLEDGE) + ["tasks", "events", "artifacts"]:
        try:
            out[t] = c.execute('select count(*) from "%s"' % t).fetchone()[0]
        except Exception:
            out[t] = None
    out["artifacts_from_tasks"] = c.execute(
        "select count(*) from artifacts where storage_path like 'tasks/task-%'").fetchone()[0]
    out["artifacts_real"] = c.execute(
        "select count(*) from artifacts where storage_path not like 'tasks/task-%' "
        "or storage_path is null").fetchone()[0]
    out["planted_control"] = c.execute(
        "select count(*) from artifacts where id=?", (PLANT,)).fetchone()[0]
    c.close()
    return out


PLANT = "probe_control_" + uuid.uuid4().hex[:12]


def main():
    if not os.path.isfile(LIVE):
        refuse("no agora.db, so this check would pass by pruning nothing")
    tmp = os.path.join(tempfile.mkdtemp(prefix="retention_probe_"), "agora.db")
    print("  copying the live database (%.0f MB) ..." % (os.path.getsize(LIVE) / 1048576))
    shutil.copy2(LIVE, tmp)

    # Plant the control: a REAL artifact, far older than the window, that must survive.
    c = sqlite3.connect(tmp)
    c.execute("insert into artifacts (id, agent_id, title, artifact_type, storage_path, "
              "mime_type, size_bytes, content, metadata, created_at) values "
              "(?,?,?,?,?,?,?,?,?, '2026-01-01 00:00:00')",
              (PLANT, "probe", "a real research artifact from long ago", "research",
               "vault/notes/real-note.md", "text/markdown", 10, "x", "{}"))
    c.commit()
    c.close()

    before = counts(tmp)
    if not before["artifacts_from_tasks"]:
        refuse("the copy contains no auto-task artifacts, so the intended change cannot be observed")
    if not before["planted_control"]:
        refuse("the control artifact was not planted, so an over-broad prune would go unnoticed")

    from agora.execution import db_retention
    from pathlib import Path
    db_retention._DB = Path(tmp)
    result = db_retention.prune(days=14, vacuum=False)
    after = counts(tmp)

    print()
    print("  %-26s %10s %10s %10s" % ("table", "before", "after", "removed"))
    for k in ("tasks", "events", "artifacts", "artifacts_from_tasks", "artifacts_real"):
        b, a = before[k], after[k]
        print("  %-26s %10s %10s %10s" % (k, b, a, (b - a) if b is not None else "?"))

    print()
    print("  KNOWLEDGE tables, which must not move:")
    moved = []
    for t in KNOWLEDGE:
        b, a = before[t], after[t]
        flag = "" if b == a else "   <-- CHANGED"
        if b != a:
            moved.append(t)
        print("  %-26s %10s %10s%s" % (t, b, a, flag))
    if moved:
        refuse("the prune changed knowledge table(s): %s" % ", ".join(moved))

    print()
    if after["planted_control"] != 1:
        refuse("the CONTROL artifact was deleted. It is a real artifact (storage_path "
               "'vault/notes/...'), older than the window, and the policy took it, so the policy is "
               "over-broad and would delete real work")
    print("  CONTROL: the planted real artifact, dated 2026-01-01, SURVIVED the prune")

    removed_fiction = before["artifacts_from_tasks"] - after["artifacts_from_tasks"]
    if removed_fiction <= 0:
        refuse("no auto-task artifact was removed, so the intended change did not land")
    print("  INTENDED: %d auto-task artifacts, %d task rows and %d event rows removed"
          % (removed_fiction, before["tasks"] - after["tasks"], before["events"] - after["events"]))

    size_before = os.path.getsize(tmp)
    sqlite3.connect(tmp).execute("VACUUM")
    print()
    print("  file after VACUUM: %.0f MB, down from %.0f MB live"
          % (os.path.getsize(tmp) / 1048576, os.path.getsize(LIVE) / 1048576))

    json.dump({"script": os.path.basename(__file__),
               "before": before, "after": after, "prune_result": result,
               "live_mb": round(os.path.getsize(LIVE) / 1048576, 1),
               "pruned_vacuumed_mb": round(os.path.getsize(tmp) / 1048576, 1),
               "controls": {"knowledge_tables_unchanged": True,
                            "real_artifact_survived": True,
                            "fiction_actually_removed": removed_fiction}},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("  written: %s" % OUT)
    shutil.rmtree(os.path.dirname(tmp), ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
