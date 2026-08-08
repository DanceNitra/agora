"""Refuse a shipped mechanism that reads a field nothing ever writes.

WHY THIS EXISTS. On 2026-08-08 four separate defects turned out to be the same defect:

  * `tools/construction_audit.py` was built, tested, and lived "in someone's memory" instead of the
    publish path.
  * `with_warrant` existed in the library and appeared nowhere in the MCP server, so no agent could
    obtain the tier it exists to expose.
  * `strict_corroboration` counts DISTINCT VERIFIED KEYS. `attested_key` coverage across every store
    this deployment runs -- 111,264 records -- was **0.0000%**.
  * `credit_requires_warrant` counts warranted credit. `good_warranted > 0` was **0 of 60,077**.

And earlier, the same shape again: `slash(scope='source')` returned ok on 261,673 records because its
default scope resolved on a field no writer ever set.

Every one is "the code is correct and unreached". Our tests prove a mechanism WORKS GIVEN ITS INPUT.
Nothing asked whether the input ever ARRIVES. A feature whose gating field is never populated is not a
strict feature, it is an absent one -- and it reports SAFE, because a guard with no input never fires.

WHAT THIS DOES. For each mechanism below it reads the REAL stores, counts how many records carry the
field the mechanism gates on, and REFUSES when a mechanism that is presented as shipped has zero
coverage. It is deliberately pointed at production data rather than fixtures: a fixture proves the
field CAN be written, which is the very thing that was never in doubt.

Exit 1 if any mechanism is unreachable. Run it after shipping anything that reads a record field.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# (field, mechanism, what breaks when coverage is 0)
MECHANISMS = [
    ("attested_key", "strict_corroboration / distinct-verified-key corroboration",
     "`corroborated` can never be reached; every multi-source record reads `unwarranted`"),
    ("good_warranted", "credit_requires_warrant (the MINJA self-graded-outcome guard)",
     "`earned` becomes unreachable rather than un-self-gradable"),
    ("source", "slash(scope='source') and every source-scoped accountability lever",
     "the lever resolves on nothing and returns ok for every call"),
    ("key", "keyed supersession (a correction retiring the value it replaces)",
     "corrections sit BESIDE the value they correct instead of retiring it"),
]

STORES = [
    ROOT / ".inspeximus" / "coding_memory.json",
    ROOT / "server" / ".inspeximus" / "coding_memory.json",
    ROOT / "agora-game-server" / ".agent_memory" / "artificer.json",
    ROOT / "agora-game-server" / ".agent_memory" / "cartographer.json",
    ROOT / "agora-game-server" / ".agent_memory" / "king.json",
    ROOT / "agora-game-server" / ".agent_memory" / "scholar.json",
    ROOT / "agora-game-server" / ".agent_memory" / "priest.json",
    ROOT / "agora-game-server" / ".agent_memory" / "thief.json",
    ROOT / "agora-game-server" / ".agent_memory" / "guard_l.json",
    ROOT / "agora-game-server" / ".agent_memory" / "guard_r.json",
]


def _records(obj):
    if isinstance(obj, list):
        return [r for r in obj if isinstance(r, dict)]
    if isinstance(obj, dict):
        for k in ("items", "records", "memories", "data"):
            v = obj.get(k)
            if isinstance(v, list):
                return [r for r in v if isinstance(r, dict)]
    return []


def _populated(rec, field) -> bool:
    v = rec.get(field)
    if v is None or v == "" or v == [] or v == {}:
        return False
    if isinstance(v, (int, float)) and float(v) == 0.0:
        return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--allow-zero", default="",
                    help="comma-separated fields permitted to be at 0% (each needs a reason in review)")
    a = ap.parse_args()
    allow = {x.strip() for x in a.allow_zero.split(",") if x.strip()}

    counts = {f: 0 for f, _, _ in MECHANISMS}
    total = 0
    seen = 0
    for p in STORES:
        if not p.exists():
            continue
        try:
            rs = _records(json.load(io.open(p, encoding="utf-8", errors="replace")))
        except Exception as ex:
            print("UNREADABLE %s: %s" % (p.name, type(ex).__name__))
            continue
        seen += 1
        total += len(rs)
        for f in counts:
            counts[f] += sum(1 for r in rs if _populated(r, f))

    if not seen:
        print("REFUSED: no store was readable. A coverage check that reads nothing reports nothing —\n"
              "         which is the exact failure this tool exists to catch.")
        return 1

    print("stores read: %d   records: %d\n" % (seen, total))
    print("%-16s %10s %9s   %s" % ("field", "populated", "coverage", "mechanism"))
    dead = []
    for field, mech, breaks in MECHANISMS:
        n = counts[field]
        pct = 100.0 * n / total if total else 0.0
        flag = "" if n else "  <-- UNREACHABLE"
        print("%-16s %10d %8.4f%%   %s%s" % (field, n, pct, mech, flag))
        if not n and field not in allow:
            dead.append((field, mech, breaks))

    if dead:
        print("\nREFUSED — %d mechanism(s) read a field nothing in production writes:" % len(dead))
        for field, mech, breaks in dead:
            print("  * %s  (gates: %s)\n      consequence: %s" % (field, mech, breaks))
        print("\nA mechanism whose input never arrives is not strict, it is absent — and it reports SAFE.\n"
              "Ship a WRITE path for the field, or stop presenting the mechanism as available.\n"
              "To accept one deliberately: --allow-zero <field> (and say why in review).")
        return 1
    print("\nOK — every mechanism above has a real write path in production data. Necessary, not\n"
          "sufficient: coverage says the field arrives, not that the value is correct.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
