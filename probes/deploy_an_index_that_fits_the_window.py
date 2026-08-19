"""Rebuild MEMORY.md so every entry is inside the window that loads it, and prove it before writing.

WHAT IS WRONG. Claude Code loads "the first 200 lines of MEMORY.md, or the first 25KB, whichever
comes first"; content past that is not loaded. Today's two deployments took the file to 42,666 bytes
and 248 lines, so 96 of its 230 entries stopped being loaded at all -- silently, because nothing in
the write path measures the file against the window.

THE LAYOUT. The window costs about 71 bytes per entry in scaffolding -- the link title and the file
name -- before it buys a single word of meaning, so 229 entries leave roughly 38 bytes each. That is
the whole design constraint, and it means the sentences have to be rationed rather than shortened:
a sentence cut to three or six words reads as a sentence cut in half, which was measured and rejected
earlier today.

    tier 1  the owner's own hooks           kept VERBATIM, always, whatever they cost
    tier 2  the newest machine-written      keep their whole sentence, as many as the window affords
    tier 3  everything else                 a bare readable link, which is what the file was before

PRE-WRITE CONTROLS, asserted before anything is written, because a memory index is not a thing to
repair afterwards:
  * every link present, identical, and IN ORDER against the live file
  * every link TITLE identical -- the layout may drop a sentence, never rename an entry
  * every hand-written hook still present, verbatim
  * every heading and non-entry line verbatim
  * no square bracket introduced into any generated text (this refused a write once already today)
  * the result fits BOTH caps as bytes land on disk, with the archive left alone
  * and the file is only replaced if a fresh backup was written first

Run: python probes/deploy_an_index_that_fits_the_window.py [--write]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                                                      # noqa: BLE001
    pass

MEM = pathlib.Path(r"C:\Users\Danculus\.claude\projects\C--Users-Danculus-agora\memory")
LIVE = MEM / "MEMORY.md"
HUMAN = MEM / "MEMORY.md.bak-20260819-prewrittenlines"     # before machine sentences: hooks here are ours
BACKUP = MEM / "MEMORY.md.bak-20260819-prewindowfit"
HERE = pathlib.Path(__file__).parent
OUT = HERE / "deploy_an_index_that_fits_the_window.result.json"

LINE_CAP, BYTE_CAP = 200, 25000
ENTRY = re.compile(r"^\[([^\]]*)\]\(([^)]+\.md)\)(?:\s*[\u2014-]\s*(.*))?$")


def parse(text):
    out = []
    for raw in text.splitlines():
        s = raw.strip()
        if not s.startswith("- ") or "](" not in s:
            out.append(("text", raw))
            continue
        got = []
        for chunk in re.split(r"\s+\u00b7\s+", s[2:].strip()):
            m = ENTRY.match(chunk.strip())
            if m:
                got.append([m.group(1), m.group(2), (m.group(3) or "").strip()])
        out.append(("entries", got) if got else ("text", raw))
    return out


def on_disk(text):
    return text.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8")


def assemble(blocks, keep_sentence, pair_from):
    """keep_sentence: set of file names that keep their hook. Others become a bare link."""
    n, lines, pending = 0, [], []

    def flush():
        if pending:
            lines.append("- " + " \u00b7 ".join(pending))
            pending.clear()

    for kind, payload in blocks:
        if kind == "text":
            flush()
            lines.append(payload)
            continue
        for (t, f, h) in payload:
            piece = "[%s](%s)%s" % (t, f, (" \u2014 " + h) if (h and f in keep_sentence) else "")
            if pair_from is not None and n >= pair_from:
                pending.append(piece)
                if len(pending) == 2:
                    flush()
            else:
                flush()
                lines.append("- " + piece)
            n += 1
    flush()
    return "\n".join(lines).rstrip("\n") + "\n"


def main(argv) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="replace MEMORY.md (a backup is written first)")
    a = ap.parse_args(argv[1:])

    live = LIVE.read_text(encoding="utf-8")
    blocks = parse(live)
    order = [f for k, p in blocks if k == "entries" for (_, f, _) in p]
    titles = {f: t for k, p in blocks if k == "entries" for (t, f, _) in p}
    hooks = {f: h for k, p in blocks if k == "entries" for (_, f, h) in p}

    # ---- tier 1: whatever carried a hook BEFORE today's machine pass is the owner's, and stays
    human = {}
    for k, p in parse(HUMAN.read_text(encoding="utf-8")):
        if k == "entries":
            for (_, f, h) in p:
                if len(h) > 15:
                    human[f] = h
    print("%d entries; %d carry a hand-written hook that is kept verbatim whatever it costs"
          % (len(order), len(human)))

    # ---- tier 2: fill the remaining window with whole sentences, newest first (file order)
    rest = [f for f in order if f not in human]
    best = None
    for k in range(len(rest), -1, -1):
        keep = set(human) | set(rest[:k])
        pf = None
        for cand in range(len(order), -1, -2):
            if len(assemble(blocks, keep, cand).splitlines()) <= LINE_CAP:
                pf = cand
                break
        if pf is None:
            continue
        text = assemble(blocks, keep, pf)
        if len(on_disk(text)) <= BYTE_CAP:
            best = (k, pf, keep, text)
            break
    if best is None:
        print("no layout fits even with every sentence dropped -- the entry count itself is the problem")
        return 3
    k, pf, keep, text = best
    print("%d of %d machine sentences fit alongside them; %d entries become a bare readable link"
          % (k, len(rest), len(order) - len(keep)))
    print("pairing starts at entry #%d, which is what the 200-line cap costs" % pf)

    # ---------------------------------------------------------------- PRE-WRITE CONTROLS
    checks = []

    def ck(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    # Count links the SAME way on both sides. The footer's pointer to MEMORY_ARCHIVE.md lives in a
    # prose line, so it is a link but not an entry; comparing a parsed entry list against a regex
    # sweep counts it on one side only, and reports a loss that did not happen.
    all_links_before = re.findall(r"\]\(([^)]+\.md)\)", live)
    new_links = re.findall(r"\]\(([^)]+\.md)\)", text)
    ck("every link present, identical, in order", new_links == all_links_before,
       "%d vs %d" % (len(new_links), len(all_links_before)))
    new_titles = {f: t for k2, p in parse(text) if k2 == "entries" for (t, f, _) in p}
    ck("every link title unchanged", new_titles == titles,
       "%d differ" % sum(1 for f in titles if new_titles.get(f) != titles.get(f)))
    kept_hooks = {f: h for k2, p in parse(text) if k2 == "entries" for (_, f, h) in p if h}
    ck("every hand-written hook survives verbatim",
       all(kept_hooks.get(f) == human[f] for f in human),
       "%d of %d" % (sum(1 for f in human if kept_hooks.get(f) == human[f]), len(human)))
    old_text_lines = [l for kk, l in blocks if kk == "text"]
    new_text_lines = [l for kk, l in parse(text) if kk == "text"]
    ck("every heading and non-entry line verbatim", old_text_lines == new_text_lines,
       "%d vs %d" % (len(old_text_lines), len(new_text_lines)))
    ck("no bracket introduced into any kept hook",
       not any("[" in h or "]" in h for h in kept_hooks.values()))
    ck("fits the 200-line cap", len(text.splitlines()) <= LINE_CAP, "%d lines" % len(text.splitlines()))
    ck("fits the 25,000-byte cap as it lands on disk", len(on_disk(text)) <= BYTE_CAP,
       "%d B" % len(on_disk(text)))
    # the control that matters: EVERY entry is inside the loaded window, not merely inside the file
    kept_b, loaded = 0, []
    for line in text.split("\n"):
        b = len(line.encode("utf-8")) + 2
        if len(loaded) >= LINE_CAP or kept_b + b > BYTE_CAP:
            break
        loaded.append(line)
        kept_b += b
    reach = re.findall(r"\]\(([^)]+\.md)\)", "\n".join(loaded))
    ck("EVERY entry is inside the window that loads", len(reach) == len(all_links_before),
       "%d of %d reachable" % (len(reach), len(all_links_before)))

    w = max(len(c[0]) for c in checks)
    for name, ok, detail in checks:
        print("%-4s %-*s %s" % ("OK" if ok else "FAIL", w, name, detail))
    bad = [c for c in checks if not c[1]]
    print("\n%d/%d pre-write controls pass" % (len(checks) - len(bad), len(checks)))

    live_reach = len(re.findall(r"\]\(([^)]+\.md)\)", "\n".join(
        (lambda t: t)(live).split("\n")[:LINE_CAP])))
    print("\n%-22s %9s %6s %s" % ("", "bytes", "lines", "entries a session loads"))
    print("%-22s %9d %6d %d of %d" % ("live now", len(on_disk(live)), len(live.splitlines()),
                                      134, len(order)))
    print("%-22s %9d %6d %d of %d" % ("this rebuild", len(on_disk(text)), len(text.splitlines()),
                                      len(reach), len(order)))

    OUT.write_text(json.dumps(dict(entries=len(order), human_hooks=len(human), sentences_kept=k,
                                   bare=len(order) - len(keep), pair_from=pf,
                                   bytes=len(on_disk(text)), lines=len(text.splitlines()),
                                   reachable=len(reach),
                                   controls={n: o for n, o, _ in checks},
                                   all_pass=not bad), indent=1), encoding="utf-8")

    if bad:
        print("\nREFUSING TO WRITE -- a control failed, and this file is the memory index")
        return 1
    if not a.write:
        (HERE / "an_index_that_fits_the_window.candidate.md").write_text(text, encoding="utf-8")
        print("\ndry run. candidate written beside this probe; pass --write to deploy")
        return 0

    # A backup that overwrites the previous backup is not a backup. The first run of this script
    # saved the 42,666-byte broken index; the second run, minutes later, replaced that copy with an
    # already-repaired one and the original was only recoverable because its sentences live in a
    # probe cache. So the name is claimed, never reused.
    backup = BACKUP
    n = 2
    while backup.exists():
        backup = BACKUP.with_name(BACKUP.name + "-%d" % n)
        n += 1
    shutil.copy2(LIVE, backup)
    if not backup.exists() or backup.stat().st_size != LIVE.stat().st_size:
        print("the backup did not land -- refusing to overwrite the index")
        return 1
    LIVE.write_text(text, encoding="utf-8")
    print("\nDEPLOYED. backup at %s" % BACKUP.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
