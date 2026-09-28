"""Which `instructions` records carry no auto-memory index, in a project that has one?

Asked on anthropics/claude-code#82056 (tonydzi, 2026-09-27): on build 2.1.266 he found records with no
`AutoMem` entry, sitting between records that delivered the same index 13 and 29 seconds apart.
This reads every transcript under ~/.claude/projects and reports the same shape on this machine.

A record is ABSENT when it names no MEMORY.md while its project has memory/MEMORY.md on disk today,
and BRACKETED when the same transcript delivered the index both before and after it.

WHAT IT CANNOT SHOW. That the prompt lacked the index. A record lists files; on this machine many
records list a subset (only the user file, or only the index), so a missing entry in the record is
not proof of a missing file in the request. Only a capture of the request body settles that.
It also cannot tell whether MEMORY.md existed at the time of an unbracketed record.

Receipt: <this file>.result.json beside it. Reads only; writes nothing under ~/.claude.
"""
import collections
import datetime as dt
import glob
import json
import os

BASE = os.path.join(os.path.expanduser("~"), ".claude", "projects")


def records(path):
    out = []
    for line in open(path, encoding="utf-8", errors="replace"):
        if '"instructions"' not in line:
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        att = d.get("attachment") or {}
        if att.get("type") != "instructions":
            continue
        files = att.get("files") or []
        out.append({"ts": d.get("timestamp", ""), "version": d.get("version"), "reason": att.get("reason"),
                    "types": sorted(f.get("type", "?") for f in files),
                    "index": any(str(f.get("path", "")).endswith("MEMORY.md") for f in files)})
    return out


def main():
    total, shapes, earliest = 0, collections.Counter(), None
    absent, bracketed, builds, reasons = 0, 0, collections.Counter(), collections.Counter()
    # Is the record a full manifest? The user-level CLAUDE.md always loads once it exists, so a record
    # written after its creation time that names the index but not the user file lists a subset.
    user_md = os.path.join(os.path.expanduser("~"), ".claude", "CLAUDE.md")
    user_since = dt.datetime.fromtimestamp(os.stat(user_md).st_ctime, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M")
    subset_after = 0
    for proj in glob.glob(os.path.join(BASE, "*")):
        has_index = os.path.exists(os.path.join(proj, "memory", "MEMORY.md"))
        for path in glob.glob(os.path.join(proj, "*.jsonl")):
            recs = records(path)
            for i, r in enumerate(recs):
                total += 1
                shapes[",".join(r["types"])] += 1
                earliest = min(earliest or r["ts"], r["ts"])
                if r["ts"] > user_since and "AutoMem" in r["types"] and "User" not in r["types"]:
                    subset_after += 1
                if r["index"] or not has_index:
                    continue
                absent += 1
                if any(x["index"] for x in recs[:i]) and any(x["index"] for x in recs[i + 1:]):
                    bracketed += 1
                    builds[r["version"]] += 1
                    reasons[r["reason"] or "untagged"] += 1
    # Control: the reader must find delivered indexes at all, else every record looks absent.
    delivered = sum(n for s, n in shapes.items() if "AutoMem" in s)
    assert delivered > 0, "no record delivered an index: the reader is not reading the records"
    res = {"records": total, "earliest_record": earliest, "records_with_index": delivered,
           "record_shapes": dict(shapes.most_common()), "absent_in_project_with_index": absent,
           "absent_and_bracketed": bracketed, "bracketed_builds": dict(builds),
           "bracketed_reasons": dict(reasons), "user_claude_md_ctime_utc": user_since,
           "records_after_it_with_index_but_no_user_file": subset_after}
    json.dump(res, open(__file__[:-3] + ".result.json", "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
