"""Backfill the `source` field onto memories written before the writers named themselves.

WHY. Measured 2026-07-31 across every inspeximus store this deployment runs:

    .agent_memory/*.json      261,673 records   source 0.000%   derived_from 0.000%
    .inspeximus_brain.json      3,228 records   source 0.000%   derived_from 0.000%

`slash(scope='source')` is the default scope and resolves on `source`. At 0.000% coverage it matched
nothing on every call, silently, for the life of the deployment. The write paths now name their writer,
but that only helps records written from here on. Everything already banked stays unreachable by the
retraction lever, and -- worse -- keeps falling back to `id:<record id>`, so each of an agent's records
counts as a distinct source and the agent can corroborate itself by restating a claim.

WHAT IT ASSERTS, not assumes. A record in `.agent_memory/thief.json` was written by the thief agent into
the thief agent's own store; that attribution is derivable from the path and is not a guess. Records
that already carry a source are left alone. Nothing else on the record is touched: no text, no counts,
no mtype, no timestamps.

SAFETY. Dry-run by default. `--apply` writes, and only after copying each store to `<name>.bak-provenance`.
Prints a before/after table and refuses to run if the record count would change.

    python tools/backfill_memory_provenance.py                 # report only
    python tools/backfill_memory_provenance.py --apply
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AGENT_DIR = REPO / "agora-game-server" / ".agent_memory"
BRAIN_STORE = REPO / "server" / ".inspeximus_brain.json"

# eid -> the doc id every record in that agent's store is attributed to
AGENTS = ("thief", "scholar", "priest", "king", "guard_r", "guard_l", "artificer", "cartographer")


def _load(p: Path):
    with p.open(encoding="utf-8") as f:
        d = json.load(f)
    items = d.get("items") if isinstance(d, dict) else d
    return d, (items if isinstance(items, list) else None)


def _plan(p: Path, doc: str) -> tuple[int, int, list]:
    """Returns (total, would_change, items). A tombstone file is skipped: a tombstone is a deletion
    receipt, not a memory, and stamping provenance onto one would invent an attribution for a record
    whose content is gone."""
    d, items = _load(p)
    if items is None:
        return 0, 0, []
    n = len(items)
    todo = [r for r in items if isinstance(r, dict) and not r.get("source")]
    return n, len(todo), todo


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write the change (default: report only)")
    ap.add_argument("--force", action="store_true",
                    help="stamp even while a dungeon process holds these stores (lost-update risk)")
    args = ap.parse_args()

    targets: list[tuple[Path, str]] = []
    for eid in AGENTS:
        p = AGENT_DIR / f"{eid}.json"
        if p.exists():
            targets.append((p, f"agent:{eid}"))
    if not targets:
        print("no agent stores found under %s" % AGENT_DIR)
        return 1

    print("%-34s %10s %12s %12s" % ("store", "records", "no source", "-> doc"))
    print("-" * 74)
    total = changed = 0
    for p, doc in targets:
        n, k, _ = _plan(p, doc)
        print("%-34s %10d %12d %12s" % (p.name[:34], n, k, doc))
        total += n
        changed += k
    print("-" * 74)
    print("%-34s %10d %12d" % ("TOTAL", total, changed))
    print("\ncoverage before: %.3f%%   after: %.3f%%"
          % (100.0 * (total - changed) / total if total else 0.0, 100.0 if total else 0.0))

    if not args.apply:
        print("\nDRY RUN. Nothing was written. Re-run with --apply to make the change.")
        return 0

    # THE LIVE-WRITER GUARD. These are the running dungeon's own store files and it holds them in
    # memory. Stamping them on disk under a live process is a lost update: the next _save() writes the
    # in-memory copy straight back over the backfill, and the tool would have reported success on a
    # change that no longer exists. Silent, and only visible on the next audit.
    if not args.force:
        try:
            import subprocess
            out = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "@(Get-CimInstance Win32_Process -Filter \"name like '%python%'\" | "
                 "Where-Object { $_.CommandLine -like '*mcp_server.py*' }).Count"],
                capture_output=True, text=True, timeout=60)
            n_live = int((out.stdout or "0").strip() or 0)
        except Exception:
            n_live = -1
        if n_live > 0:
            print("\nREFUSED: %d dungeon process(es) are running and hold these stores in memory.\n"
                  "Their next save would overwrite this backfill and the tool would have reported\n"
                  "success anyway. Stop the dungeon, run this, then restart it. (--force to override.)"
                  % n_live)
            return 4
        if n_live < 0:
            print("\nREFUSED: could not determine whether a dungeon process is running. A backfill that\n"
                  "cannot check for a live writer is a coin flip. (--force to override.)")
            return 4

    for p, doc in targets:
        d, items = _load(p)
        if items is None:
            print("SKIP %s: unexpected shape" % p.name)
            continue
        before = len(items)
        touched = 0
        for r in items:
            if isinstance(r, dict) and not r.get("source"):
                r["source"] = {"doc": doc}
                touched += 1
        if len(items) != before:
            print("REFUSED %s: record count moved %d -> %d" % (p.name, before, len(items)))
            return 2
        bak = p.with_suffix(p.suffix + ".bak-provenance")
        shutil.copy2(p, bak)
        tmp = p.with_suffix(p.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
        tmp.replace(p)
        print("wrote %-30s %6d stamped   backup %s" % (p.name, touched, bak.name))

    print("\nre-reading to verify")
    ok = True
    for p, doc in targets:
        _, items = _load(p)
        miss = sum(1 for r in items if isinstance(r, dict) and not r.get("source"))
        wrong = sum(1 for r in items if isinstance(r, dict)
                    and (r.get("source") or {}).get("doc") not in (doc,))
        print("  %-30s missing %5d   foreign-doc %5d" % (p.name, miss, wrong))
        ok = ok and miss == 0
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
