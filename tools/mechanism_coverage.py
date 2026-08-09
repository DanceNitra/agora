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

2026-08-09 — AND THEN IT HAPPENED TO THIS TOOL. `STORES` was a hand-written literal of ten files, all
inside this repo. The one store the MCP server writes -- `~/.inspeximus/mcp_memory.json`, the store a
writer key can actually sign -- was not on it. So after 2.3.0 shipped signing and an ordinary write
was verified on disk to carry `attested_key`, this gate still printed `attested_key 0 0.0000%` over
215,023 records. That zero was structurally guaranteed: it would have printed identically whether
signing worked or not. A coverage checker blind to the writer's own store measures everything except
the thing that changed.

So the store list is no longer trusted to be complete. `_writer_store()` RESOLVES where this
deployment's MCP server writes (env, then its MCP config, then the library default), that store is
always read, and the gate REFUSES if it could not be resolved or could not be read -- rather than
reporting coverage it had no way to observe. A gate must not be able to examine its way out of its
own input.
"""
from __future__ import annotations

import argparse
import io
import json
import os
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
    ROOT / "server" / ".inspeximus_brain.json",
    ROOT / "agora-game-server" / ".inspeximus" / "coding_memory.json",
    ROOT / "agora-game-server" / ".agent_memory" / "artificer.json",
    ROOT / "agora-game-server" / ".agent_memory" / "cartographer.json",
    ROOT / "agora-game-server" / ".agent_memory" / "king.json",
    ROOT / "agora-game-server" / ".agent_memory" / "scholar.json",
    ROOT / "agora-game-server" / ".agent_memory" / "priest.json",
    ROOT / "agora-game-server" / ".agent_memory" / "thief.json",
    ROOT / "agora-game-server" / ".agent_memory" / "guard_l.json",
    ROOT / "agora-game-server" / ".agent_memory" / "guard_r.json",
]

# Where a store might live that nobody remembered to declare. Filename patterns only -- matching is a
# glob, never a parse, so this stays cheap enough to run on every invocation. These are DISCOVERED AND
# READ, not merely warned about: a list that must be edited by hand to stay complete is the defect,
# and a warning nobody acts on is the same defect with extra output. `.tombstones.json` sidecars sit
# next to real stores and are not stores.
DISCOVER = (".inspeximus/coding_memory.json", ".inspeximus_brain.json", ".agent_memory/*.json")
DISCOVER_SKIP = (".tombstones.json",)

# How many of the newest writer-store records the freshness line looks at.
FRESH_N = 100

# Fields only a NEW write can carry, so a corpus percentage is the wrong denominator for them: legacy
# records can never be retro-filled, and one populated write pins the corpus figure above zero forever.
#
# `good_warranted` was missing from this list and it cost a real misreading. On 2026-08-09 the write path
# for it shipped, and the corpus number stayed 0 of 220,415 -- which reads as "nothing writes this" when
# the truth was "every record predates the writer that can". A reviewer called that zero structurally
# guaranteed, and they were right: the same defect this tool exists to catch, inside this tool, one field
# over from where it had already been fixed. Fixing the instance is not fixing the class.
NEW_WRITE_ONLY = ("attested_key", "good_warranted")


def _writer_store():
    """The store THIS deployment's MCP server writes -- the only one a writer key can sign.

    Resolved rather than assumed, because assuming it is what produced a structurally-guaranteed zero.
    Order: explicit env, then the MCP server config that actually launches it, then the library
    default. Returns None only when none of the three yields a path at all, which the caller treats as
    a refusal — an unlocatable writer store is not an absent problem, it is an unmeasured one.
    """
    env = os.environ.get("INSPEXIMUS_PATH")
    if env:
        return Path(env)
    try:
        cfg = json.load(io.open(Path.home() / ".claude.json", encoding="utf-8", errors="replace"))
        for name, spec in (cfg.get("mcpServers") or {}).items():
            if "inspeximus" in str(name).lower():
                p = ((spec or {}).get("env") or {}).get("INSPEXIMUS_PATH")
                if p:
                    return Path(p)
    except Exception:
        pass
    default = Path.home() / ".inspeximus" / "mcp_memory.json"
    return default if default.exists() else None


def _discovered(declared):
    """Repo stores that exist and are on nobody's list — returned to be READ, not warned about.

    The hand-written literal above went stale exactly once and cost a structurally-guaranteed zero.
    Anything matching a store filename is a store; requiring a human to remember it is the failure
    mode, not the safeguard.
    """
    out = []
    for pat in DISCOVER:
        for p in ROOT.glob("**/" + pat):
            s = str(p).replace("\\", "/")
            if "/node_modules/" in s or "/.git/" in s or "/.claude/worktrees/" in s:
                continue
            if any(s.endswith(x) for x in DISCOVER_SKIP):
                continue
            if p.resolve() not in declared:
                out.append(p)
    return sorted(set(out))


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

    # The writer store is READ WHETHER OR NOT ANYONE DECLARED IT. Leaving it to the literal is the
    # defect this control exists to prevent, so the literal does not get a vote.
    writer = _writer_store()
    stores = list(STORES)
    found = _discovered({p.resolve() for p in stores})
    stores += found
    n_declared, n_found = len(STORES), len(found)
    if writer is not None and writer.resolve() not in {p.resolve() for p in stores}:
        stores.append(writer)
    writer_read = False
    writer_recs = []

    for p in stores:
        if not p.exists():
            continue
        try:
            rs = _records(json.load(io.open(p, encoding="utf-8", errors="replace")))
        except Exception as ex:
            print("UNREADABLE %s: %s" % (p.name, type(ex).__name__))
            continue
        seen += 1
        total += len(rs)
        if writer is not None and p.resolve() == writer.resolve():
            writer_read, writer_recs = True, rs
        for f in counts:
            counts[f] += sum(1 for r in rs if _populated(r, f))

    if not seen:
        print("REFUSED: no store was readable. A coverage check that reads nothing reports nothing —\n"
              "         which is the exact failure this tool exists to catch.")
        return 1

    # The control. `attested_key` can ONLY appear where a writer key signs, so a run that never opened
    # that store cannot distinguish "signing is off" from "I did not look" — and it reported the first.
    if not writer_read:
        where = str(writer) if writer is not None else "unresolvable (no env, no MCP config, no default)"
        print("REFUSED: the writer store was not read — %s\n"
              "         Every attestation field is written THERE and nowhere else, so any coverage\n"
              "         number below would describe stores that structurally cannot carry it. This is\n"
              "         the tool's own failure mode: a zero that is guaranteed rather than measured." % where)
        return 1

    print("stores read: %d of %d (%d declared, %d discovered)   records: %d   writer store: %s (%d)\n"
          % (seen, len(stores), n_declared, n_found, total, writer.name, len(writer_recs)))
    print("%-16s %10s %9s   %s" % ("field", "populated", "coverage", "mechanism"))
    dead = []
    for field, mech, breaks in MECHANISMS:
        n = counts[field]
        pct = 100.0 * n / total if total else 0.0
        flag = "" if n else "  <-- UNREACHABLE"
        print("%-16s %10d %8.4f%%   %s%s" % (field, n, pct, mech, flag))
        if not n and field not in allow:
            dead.append((field, mech, breaks))

    # A corpus percentage is the WRONG denominator for a field only new writes can carry: 215k legacy
    # records can never be retro-signed, so one signed write pins this above zero forever and the gate
    # would stay green through a signing outage. Recent coverage is the number that can still move.
    fresh = sorted((r for r in writer_recs if isinstance(r.get("ts"), (int, float))),
                   key=lambda r: r["ts"])[-FRESH_N:]
    if fresh:
        print("")
        for field in NEW_WRITE_ONLY:
            n = sum(1 for r in fresh if _populated(r, field))
            print("%-16s on the %d most recent writer-store records: %d (%.1f%%)%s"
                  % (field, len(fresh), n, 100.0 * n / len(fresh),
                     "   <-- not reaching new writes" if not n else ""))

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
