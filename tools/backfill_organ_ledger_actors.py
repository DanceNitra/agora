"""Stamp the owning agent onto organ-ledger records written before the `by` field existed.

WHY. `.contradictions.json` and `.scout_box.json` recorded everything about a closed piece of work
except WHO closed it. Measured 2026-07-31 by probes/swarm_health.py: Dame Elara had ruled on 94
contradictions in the previous 24 hours and Shadow Kael on 3 scout leads, and both were scored FAIL for
"no named actor". Earlier the same day a vault-side count reported five of eight agents as producing
nothing; two of those five were in fact the busiest in the keep. The defect was attribution, not absence.

The write paths are fixed (contradictions.OWNER / scout.OWNER, with tests). This tool handles the
BACKLOG: 300 contradiction records and 58 scout records, none of which name an actor.

HOW THE OWNER IS DERIVED, AND WHY THAT IS WEAKER EVIDENCE THAN IT LOOKS. Each of these ledgers belongs
to exactly one organ and each organ to exactly one agent, so the owner is read off the ARCHITECTURE
(the module's own OWNER constant, cross-checked against repair_ledger._ORGANS) rather than off the data.
That is a real inference, not a measurement: it is correct only while the one-organ-one-owner invariant
holds, and it cannot distinguish a record that agent genuinely produced from one written by some other
path that happened to append here. It is therefore stamped as `by_inferred: true` alongside `by`, so a
later reader can tell a derived attribution from an observed one. A backfill that erases the difference
between "we know" and "we worked it out" is how a guess becomes a fact.

Contrast tools/backfill_contributor_names.py, which repairs collective_knowledge: there the true name
was physically present in the row (in contributor_id) and the repair is a measurement. Here it is not.

SAFETY: dry-run by default, --apply to write, timestamped backup first, refuses to touch a record that
already names an actor, and refuses to run if the count exceeds a sanity ceiling.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time

SERVER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server")
CEILING = 2000            # a repair that rewrites more than this is a bug, not a repair


def _owner_for(module_name: str) -> str:
    """Read the owner off the module that WRITES the ledger, then cross-check the organ map."""
    sys.path.insert(0, SERVER)
    mod = __import__("agora.execution." + module_name, fromlist=["OWNER"])
    owner = getattr(mod, "OWNER", "")
    if not owner:
        sys.exit("agora.execution.%s declares no OWNER -- refusing to guess" % module_name)
    try:
        from agora.execution import repair_ledger
        ledger = LEDGERS[module_name]["file"]
        entry = getattr(repair_ledger, "_ORGANS", {}).get(ledger)
        mapped = (entry[0] if isinstance(entry, (tuple, list)) else entry) if entry else None
        if mapped and mapped != owner:
            sys.exit("DISAGREEMENT: %s says %r, repair_ledger._ORGANS says %r for %s. Resolve the "
                     "ownership before stamping 358 records with one of them."
                     % (module_name, owner, mapped, ledger))
    except SystemExit:
        raise
    except Exception as e:                                   # pragma: no cover
        print("  note: could not cross-check the organ map (%s: %s)" % (type(e).__name__, e))
    return owner


LEDGERS = {
    "contradictions": {"file": ".contradictions.json", "ts": "ts"},
    "scout":          {"file": ".scout_box.json",      "ts": "found_ts"},
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--apply", action="store_true", help="write (default: dry run)")
    ap.add_argument("--dir", default=SERVER, help="directory holding the ledger dotfiles")
    args = ap.parse_args()

    total = 0
    plans = []
    for name, spec in LEDGERS.items():
        path = os.path.join(args.dir, spec["file"])
        if not os.path.isfile(path):
            print("SKIP %s (not found)" % spec["file"])
            continue
        owner = _owner_for(name)
        try:
            items = json.load(open(path, encoding="utf-8"))
        except Exception as e:
            sys.exit("cannot read %s: %s" % (path, e))
        if not isinstance(items, list):
            print("SKIP %s (not a list)" % spec["file"]); continue
        todo = [x for x in items if isinstance(x, dict) and not x.get("by")]
        now = time.time()
        recent = sum(1 for x in todo if (now - float(x.get(spec["ts"]) or 0)) < 86400)
        print("%-24s %4d records | %4d without an actor | %3d of those in the last 24h -> %s"
              % (spec["file"], len(items), len(todo), recent, owner))
        total += len(todo)
        plans.append((path, items, todo, owner))

    if total > CEILING:
        print("\nREFUSING: %d records to stamp exceeds the %d ceiling. A repair that rewrites more "
              "than expected is a bug." % (total, CEILING))
        return 2
    if not total:
        print("\nnothing to do -- every record already names an actor")
        return 0
    if not args.apply:
        print("\nDRY RUN: %d record(s) would be stamped with `by` + `by_inferred: true`. "
              "Re-run with --apply." % total)
        return 0

    for path, items, todo, owner in plans:
        bak = "%s.bak-%s" % (path, time.strftime("%Y%m%d-%H%M%S"))
        shutil.copy2(path, bak)                              # plain JSON, no WAL sidecar to miss
        print("  backup: %s" % os.path.basename(bak))
        for x in todo:
            x["by"] = owner
            x["by_inferred"] = True                          # derived from the organ map, not observed
        tmp = path + ".partial"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(items, fh, ensure_ascii=False)
        json.load(open(tmp, encoding="utf-8"))               # it must parse before it replaces the original
        os.replace(tmp, path)
        print("  stamped %d record(s) in %s" % (len(todo), os.path.basename(path)))
    print("\ndone. `by_inferred: true` marks these as DERIVED from the organ map, not observed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
