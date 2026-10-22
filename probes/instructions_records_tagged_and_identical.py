"""Are the `instructions` records that omit a memory index tagged, and are the files they omit unchanged around them?

Asked on anthropics/claude-code#82056 (pjt222, 2026-10-22, answering our 5870005304):
  (a) for the 14 records that omit the index and sit between two deliveries of it: are the copies before and after identical?
  (b) for the 21 records written after the user CLAUDE.md existed that name the index but not the user file: is each one tagged
      (has a `reason`), and does each listed file differ from its previous copy in the same transcript?
Same reader as instructions_records_without_the_index.py, extended with file content. Reads only; writes the receipt beside this file.

WHAT IT CANNOT SHOW. That the request lacked a file. A record is a list of files, not the request body.
Copies are compared inside one transcript; a file never listed earlier has no previous copy and is counted as "first".
"""
import collections
import datetime as dt
import glob
import hashlib
import json
import os

BASE = os.path.join(os.path.expanduser("~"), ".claude", "projects")


def h(s):
    return hashlib.sha256((s or "").encode("utf-8", "replace")).hexdigest()[:16]


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
        files = {str(f.get("path")): (f.get("type", "?"), h(f.get("content"))) for f in (att.get("files") or [])}
        out.append({"ts": d.get("timestamp", ""), "version": d.get("version"), "reason": att.get("reason"), "files": files,
                    "index": any(p.endswith("MEMORY.md") for p in files)})
    return out


def last_copy(recs, upto, path, before=True):
    rng = range(upto - 1, -1, -1) if before else range(upto + 1, len(recs))
    for j in rng:
        if path in recs[j]["files"]:
            return recs[j]["files"][path]
    return None


def main():
    user_md = os.path.join(os.path.expanduser("~"), ".claude", "CLAUDE.md")
    user_since = dt.datetime.fromtimestamp(os.stat(user_md).st_ctime, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M")
    a = collections.Counter()
    b = collections.Counter()
    untagged_detail = []
    seen_index = 0
    total = 0
    versions = collections.Counter()
    for proj in glob.glob(os.path.join(BASE, "*")):
        has_index = os.path.exists(os.path.join(proj, "memory", "MEMORY.md"))
        for path in glob.glob(os.path.join(proj, "*.jsonl")):
            recs = records(path)
            seen_index += sum(r["index"] for r in recs)
            total += len(recs)
            versions.update(r["version"] for r in recs)
            for i, r in enumerate(recs):
                # (a) records that omit the index, bracketed by deliveries of it
                if has_index and not r["index"] and any(x["index"] for x in recs[:i]) and any(x["index"] for x in recs[i + 1:]):
                    a["records"] += 1
                    a["tagged" if r["reason"] else "untagged"] += 1
                    ip_before = next((p for x in reversed(recs[:i]) for p in x["files"] if p.endswith("MEMORY.md")), None)
                    cb = last_copy(recs, i, ip_before, True) if ip_before else None
                    ca = last_copy(recs, i, ip_before, False) if ip_before else None
                    a["index_copies_identical" if cb == ca else "index_copies_differ"] += 1
                    for p, (_, hh) in list(r["files"].items()):
                        prev = last_copy(recs, i, p, True)
                        a["listed_file_first" if prev is None else "listed_file_changed" if prev[1] != hh else "listed_file_unchanged"] += 1
                # (b) after the user file existed: names the index, not the user file
                if r["ts"] > user_since and r["index"] and not any(t == "User" for t, _ in r["files"].values()):
                    b["records"] += 1
                    b["tagged" if r["reason"] else "untagged"] += 1
                    b["reason_" + str(r["reason"])] += 1
                    if not r["reason"]:
                        untagged_detail.append({"version": r["version"], "sole_record_in_transcript": len(recs) == 1, "day": r["ts"][:10]})
                    for p, (_, hh) in r["files"].items():
                        prev = last_copy(recs, i, p, True)
                        b["listed_file_first" if prev is None else "listed_file_changed" if prev[1] != hh else "listed_file_unchanged"] += 1
    assert seen_index > 0, "control failed: the reader found no record that carries an index"
    res = {"user_claude_md_ctime_utc": user_since, "a_bracketed_omitting_index": dict(a), "b_after_user_file_index_without_user": dict(b),
           "b_untagged_without_user_detail": untagged_detail, "records_total": total, "builds_first": min(versions, key=lambda v: tuple(int(x) for x in v.split("."))), "builds_last": max(versions, key=lambda v: tuple(int(x) for x in v.split("."))), "control_records_with_index": seen_index}
    json.dump(res, open(__file__[:-3] + ".result.json", "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
