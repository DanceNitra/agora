"""What did our memory edits remove while the index was over the cap, or right after the reminder?

anthropics/claude-code#91188, @vshulcz 2026-09-23 (comment 5792422954): walk the transcripts for
Edit/Write/MultiEdit calls on memory files, diff old against new, classify the removed lines
(prose, bullets, dated notes, links, rule-shaped never/always/must/only). His index never crossed the
threshold, so none of his 38 removed lines came from a threshold-triggered trim. Ours crossed it.

Read-only on the store and the transcripts. Scope: ~/.claude/projects/C--Users-Danculus-agora/**/*.jsonl
(main sessions and subagents). Three instruments, because the first one turned out to be nearly blind:

  1. EDIT WALK (his method). Edit/MultiEdit/Write on memory/*.md. Removed lines = multiset
     difference old minus new. A Write is diffed against toolUseResult.originalFile when present;
     a create removes nothing. State of the index at the moment of the edit comes from the harness's
     own records, never from text that quotes them:
       after_reminder  an attachment of type hook_additional_context carrying "The memory index at
                       MEMORY.md is ..., approaching the ... read limit" earlier in the same transcript,
                       with no human prompt in between
       over_cap        the latest index observation in that transcript says over: the session's loader
                       attachment (type "instructions") carried "WARNING: MEMORY.md is ... Only part of
                       it was loaded", or a later reminder reported a size above the limit
     originalFile is null on every MEMORY.md edit in this store, so the pre-edit size is never exact.

  2. LOADER SNAPSHOTS. The instructions attachment carries the MEMORY.md the loader delivered, once per
     session start, from every session. It sees trims made by scripts through Bash, which record no
     old_string. Parallel sessions interleave, so a row (its linked slug, or the line when it has none)
     is judged once, by its LAST sighting, and counts as removed only if it is absent from today's
     MEMORY.md. Its state is that of the snapshot it was last seen in.

  3. THE REMINDER-TRIGGERED TRIM, REPLAYED. After a reminder, the Bash commands that rewrote
     MEMORY.md are re-run on a scratch copy of the pre-trim backup the session itself made, and the
     result must equal the byte count the session printed at the time. Each removed line is then
     labelled moved_to_archive_verbatim / shortened_in_place / other, and for a shortened line the
     words that left are listed, including whether a never/always/must/only left with them.

Needed again, for every removed rule-shaped line or row, AFTER its removal, in any transcript:
  readmitted  its slug comes back in a later loader snapshot, or a later tool call writes it into MEMORY.md
  looked_up   a later tool_use input names the slug (Read, Grep, Bash, recall ...)
  cited       later assistant prose names the slug
A line with no slug is keyed by its first 60 characters.

    python -X utf8 probes/what_our_over_cap_index_edits_removed.py [--self-test]
"""
from __future__ import annotations

import collections
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.expanduser("~/.claude/projects/C--Users-Danculus-agora")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "what_our_over_cap_index_edits_removed.result.json")
LINE_CAP, UNIT_CAP, LIMIT_KB = 200, 25000, 24.4

REMINDER = re.compile(r"The memory index at MEMORY\.md is ([\d.]+) ?(KB|lines), approaching the [\d.]+ ?(KB|-line) read limit")
LOADER_WARN = re.compile(r"WARNING: MEMORY\.md is .{0,60}?Only part of it was loaded", re.S)
MEMFILE = re.compile(r"[\\/]\.claude[\\/]projects[\\/]C--Users-Danculus-agora[\\/]memory[\\/]([^\\/]+\.md)$", re.I)
MEMDIR_CD = "cd /c/Users/Danculus/.claude/projects/C--Users-Danculus-agora/memory"
RULE = re.compile(r"\b(never|always|must|only)\b", re.I)
DATED = re.compile(r"\b20\d\d-\d\d-\d\d\b|\b\d\d-\d\d\b")
LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)|\[\[([^\]]+)\]\]")
SLUG = re.compile(r"\(([A-Za-z0-9_.\-]+)\.md\)|\[\[([A-Za-z0-9_.\-]+)\]\]")
# Coarse on purpose: a Bash command that names MEMORY.md and writes anything is a CANDIDATE index write.
WRITES = re.compile(r"\.write\(|write_text\(|open\([^)]*['\"][wa]|sed -i|>>?\s*\S*MEMORY\.md|\b(cp|mv)\b[^;&|]*MEMORY\.md")


def props(line: str) -> dict:
    return {"rule": bool(RULE.search(line)), "dated": bool(DATED.search(line)),
            "link": bool(LINK.search(line)), "bullet": line.lstrip().startswith(("- ", "* "))}


def classify(line: str) -> str:
    """First match, rule > dated > link > bullet > prose. props() gives each property on its own."""
    p = props(line)
    return next((k for k in ("rule", "dated", "link", "bullet") if p[k]), "prose")


def slugs(line: str) -> list:
    return sorted({a or b for a, b in SLUG.findall(line)} - {"MEMORY", "MEMORY_ARCHIVE"})


def removed_lines(old: str, new: str) -> list:
    left = collections.Counter(new.replace("\r\n", "\n").split("\n"))
    out = []
    for line in old.replace("\r\n", "\n").split("\n"):
        if left[line] > 0:
            left[line] -= 1
        elif line.strip():
            out.append(line)
    return out


def flat(o) -> str:
    return json.dumps(o, ensure_ascii=False)


def is_prompt(rec: dict) -> bool:
    """A human turn. A tool_result record is never one, even when it carries a text block."""
    if rec.get("type") != "user" or rec.get("isMeta") or "toolUseResult" in rec:
        return False
    c = (rec.get("message") or {}).get("content")
    if isinstance(c, str):
        return not c.startswith("<")
    if not isinstance(c, list) or any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c):
        return False
    return any(isinstance(b, dict) and b.get("type") == "text" and not str(b.get("text", "")).startswith("<") for b in c)


def scan(streams) -> dict:
    """streams: iterable of (name, records). Returns the evidence of all three instruments."""
    ev = {k: [] for k in ("edits", "bash", "bash_all", "reminders", "loads", "later")}
    for name, records in streams:
        armed, index_over, results, pending, mine = False, None, {}, [], []
        for rec in records:
            ts = rec.get("timestamp") or ""
            tur = rec.get("toolUseResult")
            if rec.get("type") == "user" and isinstance(tur, dict):
                for b in (rec.get("message") or {}).get("content") or []:
                    if isinstance(b, dict) and b.get("type") == "tool_result":
                        results[b.get("tool_use_id")] = tur
            a = rec.get("attachment") if rec.get("type") == "attachment" else None
            if isinstance(a, dict) and a.get("type") == "hook_additional_context":
                m = REMINDER.search(flat(a.get("content")))
                if m:
                    armed = True
                    index_over = float(m.group(1)) > (LIMIT_KB if m.group(2) == "KB" else LINE_CAP)
                    ev["reminders"].append({"t": ts, "file": name, "text": m.group(0)})
                continue
            if isinstance(a, dict) and a.get("type") == "instructions":
                for fl in a.get("files") or []:
                    if MEMFILE.search(str(fl.get("path", ""))) and str(fl.get("path")).endswith("MEMORY.md"):
                        c = str(fl.get("content", ""))
                        index_over = bool(LOADER_WARN.search(c))
                        ev["loads"].append({"t": ts, "file": name, "warned": index_over, "content": c})
                continue
            if is_prompt(rec):
                armed = False
                continue
            if rec.get("type") != "assistant":
                continue
            for b in (rec.get("message") or {}).get("content") or []:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "text":
                    ev["later"].append((ts, "cited", b.get("text") or "", None))
                if b.get("type") != "tool_use":
                    continue
                inp = b.get("input") or {}
                ev["later"].append((ts, "looked_up", flat(inp), b.get("id")))
                cmd = str(inp.get("command", "")) if b.get("name") == "Bash" else ""
                if cmd:
                    mine.append({"t": ts, "file": name, "id": b.get("id"), "cmd": cmd})
                    if "MEMORY.md" in cmd and WRITES.search(cmd):
                        ev["bash"].append({"t": ts, "file": name, "after_reminder": armed, "index_over": index_over,
                                           "cmd": cmd[:160]})
                m = MEMFILE.search(str(inp.get("file_path", "")))
                if not m or b.get("name") not in ("Edit", "Write", "MultiEdit"):
                    continue
                target = m.group(1)
                kind = "index" if target == "MEMORY.md" else "archive" if target.startswith("MEMORY_ARCHIVE") else "topic"
                if b.get("name") == "Write":
                    parts = [(None, str(inp.get("content", "")))]
                else:
                    es = inp.get("edits") if b.get("name") == "MultiEdit" else [inp]
                    parts = [(str(e.get("old_string", "")), str(e.get("new_string", ""))) for e in es or []]
                pending.append({"t": ts, "file": name, "id": b.get("id"), "tool": b.get("name"), "target": target,
                                "kind": kind, "after_reminder": armed, "index_over": index_over, "parts": parts})
        for x in mine:
            tr = results.get(x["id"])
            x["result"] = str(tr.get("stdout", "")) if isinstance(tr, dict) else ""
        ev["bash_all"] += mine
        for e in pending:
            tur = results.get(e["id"]) or {}
            orig = tur.get("originalFile") if isinstance(tur.get("originalFile"), str) else None
            created = tur.get("type") == "create"
            gone, recoverable = [], True
            for old, new in e.pop("parts"):
                if old is None:
                    if orig is not None:
                        gone += removed_lines(orig, new)
                    elif not created:
                        recoverable = False
                else:
                    gone += removed_lines(old, new)
            e.update(recoverable=recoverable, created=created, removed=gone)
            ev["edits"].append(e)
    return ev


def needed_again(line: str, t0: str, ev: dict, by_text: bool = False) -> dict:
    """Loader snapshots are NOT used for readmission: an attachment's timestamp is not the time the file
    was read (a snapshot stamped 16:48 on 09-24 carries the index as it was before the 16:46 trim)."""
    keys = [line.strip().lstrip("-* ").strip()[:60]] if by_text or not slugs(line) else slugs(line)
    hit = {"readmitted": [], "looked_up": [], "cited": []}
    today = read(os.path.join(ROOT, "memory", "MEMORY.md"))
    if not by_text and any(k in today for k in keys):
        hit["readmitted"].append("in today's MEMORY.md")
    for ts, ch, text, _ in ev["later"]:
        if ts <= t0 or not any(k in text for k in keys):
            continue
        if ch == "looked_up" and "MEMORY.md" in text and ('"new_string"' in text or '"content"' in text or ".write(" in text):
            hit["readmitted"].append(ts)
        else:
            hit[ch].append(ts)
    return {"keys": keys, **{k: {"n": len(v), "first": min(v) if v else None} for k, v in hit.items()}}


def edit_walk(ev: dict) -> dict:
    groups = collections.defaultdict(collections.Counter)
    rules = []
    for e in ev["edits"]:
        state = "after_reminder" if e["after_reminder"] else "over_cap" if e["index_over"] else \
                "under_cap" if e["index_over"] is False else "unknown"
        g = e["kind"] + "|" + state
        c = groups[g]
        c["edits"] += 1
        c["shrinking_edits"] += bool(e["removed"])
        c["writes_unrecoverable"] += not e["recoverable"]
        for line in e["removed"]:
            c["removed_lines"] += 1
            c["first:" + classify(line)] += 1
            for k, v in props(line).items():
                c["has:" + k] += v
            if classify(line) == "rule":
                rules.append({"t": e["t"], "target": e["target"], "group": g, "line": line[:220],
                              "needed_again": needed_again(line, e["t"], ev, by_text=e["kind"] != "index")})
    return {"groups": {k: {kk: vv for kk, vv in v.items() if vv} for k, v in sorted(groups.items())}, "rule_lines": rules}


def read(path: str) -> str:
    try:
        return open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return ""


def snapshot_rows(ev: dict, memdir: str) -> list:
    archive, today = read(os.path.join(memdir, "MEMORY_ARCHIVE.md")), read(os.path.join(memdir, "MEMORY.md"))
    snaps = sorted(ev["loads"], key=lambda x: x["t"])
    last = {}
    for i, sn in enumerate(snaps):
        for line in LOADER_WARN.split(sn["content"])[0].replace("\r\n", "\n").split("\n"):
            if line.strip() and not line.startswith(("> WARNING", "#")):
                for key in slugs(line) or [line]:
                    last[key] = (i, line)
    rows = []
    for key, (i, line) in last.items():
        if key in today:
            continue
        nxt = next((sn["t"] for sn in snaps[i + 1:] if key not in sn["content"]), None)
        rem = any(snaps[i]["t"] < r["t"] <= (nxt or "9999") for r in ev["reminders"])
        rows.append({"key": key, "line": line, "last_seen": snaps[i]["t"], "gone_by": nxt,
                     "state": "over_cap" if snaps[i]["warned"] else "after_reminder" if rem else "under_cap",
                     "fate": "archived" if key in archive else "gone"})
    return rows


def replay_reminder_trim(ev: dict) -> dict:
    """The compaction that followed a reminder, replayed byte for byte from the session's own backup."""
    backup_cp = re.compile(r"cp MEMORY\.md (\S+MEMORY\.md\.bak)")
    for r in ev["reminders"]:
        cmds = [b for b in ev["bash_all"] if b["file"] == r["file"] and b["t"] > r["t"] and MEMDIR_CD in b["cmd"]]
        m = next((backup_cp.search(b["cmd"]) for b in cmds if backup_cp.search(b["cmd"])), None)
        writes = [b for b in cmds if "python - <<'EOF'" in b["cmd"] and "os.replace" in b["cmd"]]
        if not m or not writes:
            continue
        backup = re.sub(r"^/c/", "C:/", m.group(1))
        if not os.path.exists(backup):
            return {"found": True, "replayed": False, "why": "backup gone: " + backup}
        work = tempfile.mkdtemp(prefix="replay_trim_")
        try:
            shutil.copy(backup, os.path.join(work, "MEMORY.md"))
            shutil.copy(backup.replace("MEMORY.md.bak", "MEMORY_ARCHIVE.md.bak"), os.path.join(work, "MEMORY_ARCHIVE.md"))
            logged = None
            for b in writes:
                body = b["cmd"].split("python - <<'EOF'\n", 1)[1].rsplit("\nEOF", 1)[0]
                subprocess.run([sys.executable, "-X", "utf8", "-"], input=body, text=True, cwd=work,
                               capture_output=True, encoding="utf-8")
                n = re.search(r"(\d{4,6}) bytes", b["result"])
                logged = int(n.group(1)) if n else logged
            pre = read(backup)
            post, arch = read(os.path.join(work, "MEMORY.md")), read(os.path.join(work, "MEMORY_ARCHIVE.md"))
        finally:
            shutil.rmtree(work, ignore_errors=True)
        post_lines = post.split("\n")
        today_lines = read(os.path.join(ROOT, "memory", "MEMORY.md")).split("\n")
        lines = []
        for line in removed_lines(pre, post):
            ks = slugs(line)
            now = next((l for l in post_lines if ks and ks[0] in l), None)
            if line in arch:
                fate = "moved_duplicate_pointer" if now else "moved_to_archive_verbatim"
            else:
                fate = "shortened_in_place" if now else "other"
            words = [w for w in re.findall(r"[A-Za-z'][A-Za-z'-]*", line) if fate == "shortened_in_place" and
                     not re.search(r"\b%s\b" % re.escape(w), now, re.I)]
            rule_gone = [w for w in words if RULE.fullmatch(w)]
            today = next((l for l in today_lines if ks and ks[0] in l), "")
            lines.append({"line": line, "fate": fate, "class": classify(line), "props": props(line), "now": now,
                          "words_gone": words, "rule_word_gone": rule_gone,
                          "rule_word_back_today": [w for w in rule_gone if re.search(r"\b%s\b" % w, today, re.I)],
                          "needed_again": needed_again(line, writes[-1]["t"], ev)
                          if RULE.search(line) and fate in ("moved_to_archive_verbatim", "other") else None})
        return {"found": True, "replayed": True, "reminder": r, "backup": backup, "scripts": [b["t"] for b in writes],
                "pre_bytes": len(pre.encode()), "pre_lines": len(pre.split("\n")),
                "post_bytes": len(post.encode()), "post_lines": len(post_lines), "logged_post_bytes": logged,
                "replay_matches_logged_bytes": logged == len(post.encode()),
                "by_fate": dict(collections.Counter(l["fate"] for l in lines)),
                "by_fate_first_class": {f: dict(collections.Counter(l["class"] for l in lines if l["fate"] == f))
                                        for f in sorted({l["fate"] for l in lines})},
                "rule_shaped_by_fate": dict(collections.Counter(l["fate"] for l in lines if l["props"]["rule"])),
                "rule_words_gone_in_shortening": [(l["rule_word_gone"], l["rule_word_back_today"], l["line"][:70])
                                                  for l in lines if l["rule_word_gone"]],
                "moved_rule_lines_needed_again": {
                    k: sum(1 for l in lines if l["needed_again"] and l["needed_again"][k]["n"])
                    for k in ("readmitted", "looked_up", "cited")} | {
                    "of": sum(1 for l in lines if l["needed_again"])},
                "lines": lines}
    return {"found": False}


# ---------------------------------------------------------------- controls

MEM = "C:\\Users\\Danculus\\.claude\\projects\\C--Users-Danculus-agora\\memory\\MEMORY.md"
REM = {"type": "attachment", "timestamp": "2099-01-01T00:00:01Z", "attachment": {"type": "hook_additional_context",
       "content": ["The memory index at MEMORY.md is 24.3KB, approaching the 24.4KB read limit. Compact it."]}}
PLANTED = "- [Never trust a quoted reminder](planted-never-rule.md) you must check"


def _edit(tid="T1", ts="2099-01-01T00:00:02Z"):
    return {"type": "assistant", "timestamp": ts, "message": {"content": [{"type": "tool_use", "id": tid, "name": "Edit",
            "input": {"file_path": MEM, "old_string": PLANTED + "\nkeep", "new_string": "keep"}}]}}


def _result(tid="T1"):
    return {"type": "user", "timestamp": "2099-01-01T00:00:03Z", "toolUseResult": {"originalFile": None},
            "message": {"content": [{"type": "tool_result", "tool_use_id": tid, "content": "ok"}]}}


def self_test() -> list:
    quoted = {"type": "user", "timestamp": "2099-01-01T00:00:01Z", "message": {"content": [{"type": "tool_result",
              "tool_use_id": "q", "content": "The memory index at MEMORY.md is 24.3KB, approaching the 24.4KB read limit."}]}}
    textful_result = {"type": "user", "timestamp": "2099-01-01T00:00:01Z", "toolUseResult": {},
                      "message": {"content": [{"type": "tool_result", "tool_use_id": "z", "content": "x"},
                                              {"type": "text", "text": "hook output"}]}}
    reread = {"type": "assistant", "timestamp": "2099-01-02T00:00:00Z", "message": {"content": [{"type": "tool_use",
              "id": "T2", "name": "Read", "input": {"file_path": "...\\memory\\planted-never-rule.md"}}]}}
    prompt = {"type": "user", "timestamp": "2099-01-01T00:00:01Z", "message": {"content": "next"}}
    over = {"type": "attachment", "timestamp": "2099-01-01T00:00:00Z", "attachment": {"type": "instructions", "files": [
            {"path": MEM, "content": "- a\n> WARNING: MEMORY.md is 25.1KB (limit: 24.4KB) - index entries are too long. "
                                     "Only part of it was loaded"}]}}
    checks = []
    ev = scan([("planted", [REM, _edit(), _result(), reread])])
    w = edit_walk(ev)
    g = w["groups"].get("index|after_reminder", {})
    checks.append(("planted rule removal seen after a reminder, classified rule",
                   g.get("first:rule") == 1 and g.get("has:link") == 1))
    checks.append(("planted rule is looked up again later",
                   bool(w["rule_lines"]) and w["rule_lines"][0]["needed_again"]["looked_up"]["n"] == 1))
    ev = scan([("q", [quoted, _edit(), _result()])])
    checks.append(("a quoted reminder is not a reminder", not ev["reminders"] and not ev["edits"][0]["after_reminder"]))
    ev = scan([("p", [REM, prompt, _edit(), _result()])])
    checks.append(("a human prompt ends the reminder's reach", not ev["edits"][0]["after_reminder"]))
    ev = scan([("t", [REM, textful_result, _edit(), _result()])])
    checks.append(("a tool result carrying text is not a human prompt", ev["edits"][0]["after_reminder"]))
    ev = scan([("o", [over, _edit(), _result()])])
    checks.append(("a loader WARNING marks the index over the cap", ev["edits"][0]["index_over"] is True))
    checks.append(("classifier first-match order", [classify(x) for x in
                   ["plain words", "- a bullet", "see [x](y.md)", "on 2026-09-04", "you must"]] ==
                   ["prose", "bullet", "link", "dated", "rule"]))
    return checks


def load(path: str):
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                yield json.loads(line)
            except ValueError:
                continue


def main() -> int:
    checks = self_test()
    for n, ok in checks:
        print("control %-62s %s" % (n, "PASS" if ok else "FAIL"))
    if not all(ok for _, ok in checks) or "--self-test" in sys.argv:
        return 0 if all(ok for _, ok in checks) else 1
    files = sorted(glob.glob(os.path.join(ROOT, "**", "*.jsonl"), recursive=True))
    ev = scan((os.path.relpath(f, ROOT), load(f)) for f in files)

    # Planted control on the REAL pipeline: one real transcript plus one planted reminder-and-trim.
    ev2 = scan([(os.path.relpath(f, ROOT), load(f)) for f in files[:1]] + [("planted", [REM, _edit("P1"), _result("P1")])])
    live = edit_walk(ev2)["groups"].get("index|after_reminder", {}).get("first:rule", 0) == 1
    blind = not ev["edits"] or not ev["reminders"] or not ev["loads"]
    print("control %-62s %s" % ("planted removal found when mixed into a real transcript", "PASS" if live else "FAIL"))
    print("control %-62s %s" % ("real scan saw edits, reminders and loader snapshots", "FAIL" if blind else "PASS"))

    walk = edit_walk(ev)
    rows = snapshot_rows(ev, os.path.join(ROOT, "memory"))
    by_state = collections.defaultdict(collections.Counter)
    snap_rules = []
    for r in rows:
        c = by_state[r["state"] + "|" + r["fate"]]
        c["rows"] += 1
        c["first:" + classify(r["line"])] += 1
        for k, v in props(r["line"]).items():
            c["has:" + k] += v
        if classify(r["line"]) == "rule":
            snap_rules.append({**r, "line": r["line"][:220],
                               "needed_again": needed_again(r["line"], r["gone_by"] or r["last_seen"], ev)})
    trim = replay_reminder_trim(ev)
    after_each = []
    for r in ev["reminders"]:
        acts = [e for e in ev["edits"] if e["file"] == r["file"] and e["t"] > r["t"] and e["after_reminder"]]
        bs = [b for b in ev["bash"] if b["file"] == r["file"] and b["t"] > r["t"] and b["after_reminder"]]
        after_each.append({"reminder": r["t"], "file": r["file"][:8], "text": r["text"],
                           "edits_before_next_prompt": len(acts), "bash_writes_before_next_prompt": len(bs)})
    out = {"scope": ROOT, "transcripts": len(files),
           "edits_to_memory_files": len(ev["edits"]),
           "by_kind": dict(collections.Counter(e["kind"] for e in ev["edits"])),
           "reminders": len(ev["reminders"]), "after_each_reminder": after_each,
           "bash_index_write_candidates": len(ev["bash"]),
           "loader_snapshots": len(ev["loads"]), "loader_snapshots_over_cap": sum(l["warned"] for l in ev["loads"]),
           "snapshot_span": [min(l["t"] for l in ev["loads"]), max(l["t"] for l in ev["loads"])],
           "edit_walk": walk["groups"], "edit_walk_rule_lines": walk["rule_lines"],
           "snapshot_rows_removed_by_state": {k: {kk: vv for kk, vv in v.items() if vv} for k, v in sorted(by_state.items())},
           "snapshot_rule_rows_removed": snap_rules,
           "reminder_triggered_trim": trim,
           "controls": {n: ok for n, ok in checks} | {"planted_in_real_stream": live, "real_scan_not_blind": not blind}}
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    short = {k: v for k, v in out.items() if k not in ("edit_walk_rule_lines", "snapshot_rule_rows_removed",
                                                         "reminder_triggered_trim", "controls", "scope")}
    short["reminder_triggered_trim"] = {k: v for k, v in trim.items() if k not in ("lines", "reminder")}
    print(json.dumps(short, indent=1))
    print("receipt:", OUT)
    return 0 if live and not blind and trim.get("replay_matches_logged_bytes") else 1


if __name__ == "__main__":
    sys.exit(main())
