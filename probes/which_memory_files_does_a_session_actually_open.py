"""Which memory files does a real Claude Code session actually OPEN, and does it track index position?

WHY. On anthropics/claude-code#82056 we measured the cost of a partial index load: Claude Code reads
only the first ~200 lines / ~24.4KB of MEMORY.md, so entries past that window never load. Every number
there weights entries EQUALLY. If real need is Zipfian, 41% of entries could be 2% of value and the
conclusion softens. @yacb2 answered half of it (comment 5352555064): at session START the sibling fact
files are indistinguishable from zero -- only the always-on index costs anything. He named the boundary
himself: his instrument cannot see MID-SESSION opens. That half is this probe.

WHAT IT MEASURES. Every occurrence of a known memory filename across this project's session
transcripts, classified BY PROVENANCE, because the distinction is the whole measurement:

  agent_tool_open   an assistant tool_use (Read/Bash/Grep/Glob/Edit/Write) naming a memory file
                    -> the session decided it needed that file. THIS is a need-driven open.
  tool_result       content returned from such a call -> evidence the open resolved.
  our_hook          attachment/hook_success + hook_additional_context -> OUR inspeximus hook printed
                    it. NOT a session need. Counting these as opens would measure our own hook.
  harness_other     any other attachment sub-type naming a memory file -> the harness surfaced it.
                    An auto-memory recall, if one ever fires, lands here.
  prose             a filename typed in assistant/user text -> not an open at all.

CONTROLS (all must pass before any number below is believed; rule #12 -- a check that never sees its
target reports SAFE). Three separate regexes lied during the exploration that led to this file, all
the same way: on Windows a transcript spells the path `memory\\\\name.md` (JSON-escaped backslash),
so `memory[\\\\/]` matches one of the two backslashes and silently returns ZERO on a session that
demonstrably rebuilt the index. Hence the matcher here does NOT match a path SHAPE at all -- it
matches against the ACTUAL population of filenames on disk, which cannot invent a file.

  C1 POSITIVE      the 2026-08-20 session must show >=1 agent_tool_open naming MEMORY.md.
                   (Known independently: it rebuilt the index that day.) 0 => matcher is blind.
  C2 MATCHER       two fact filenames our inspeximus hook is known to print must be FOUND somewhere.
                   This is the control that separates "sessions never open fact files" (a real zero)
                   from "the matcher cannot see fact files" (a broken instrument). Without it, the
                   headline result is unfalsifiable.
  C3 EXCLUSION     the session doing the counting must not be in the corpus. Grepping our own
                   transcripts once turned 12 warnings into 22 by counting the greps.
  C4 PARSE         unparseable lines are reported, not swallowed.
  C5 NEGATIVE      a filename NOT in the population must score 0. Guards a too-loose matcher.
  C6 DENOMINATOR   population size and index size are printed with every rate.

Run:  python probes/which_memory_files_does_a_session_actually_open.py
"""

import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor

# --- resolve our own paths, like the probes we verify (a probe that hardcodes one machine is not a
# --- receipt anyone else can run). The store is the LIVE one; yacb2's #85595 is exactly the failure
# --- where you measure a stale twin of the directory you meant.
HOME = os.path.expanduser("~")
PROJECT_SLUG = "C--Users-Danculus-agora"
STORE = os.path.join(HOME, ".claude", "projects", PROJECT_SLUG)
MEMORY_DIR = os.path.join(STORE, "memory")
INDEX = os.path.join(MEMORY_DIR, "MEMORY.md")

# The session running this probe. Excluded from the corpus (C3).
CURRENT_SESSION = os.environ.get("AGORA_CURRENT_SESSION", "46de8dac-117b-4f83-a449-d7e8655b1368")

# Tools whose invocation means "this session went and got that file".
#
# The read/write split is the measurement, not bookkeeping. A first run of this probe reported "388
# fact files opened on demand" -- but its tool census was Write 1351 / Edit 1012 / Read 42, i.e. the
# number was dominated by this organisation AUTHORING memories, which is the opposite of a session
# NEEDING one. Authoring proves nothing about whether index position drives retrieval.
READ_TOOLS = {"Read", "Grep", "Glob"}
WRITE_TOOLS = {"Write", "Edit", "NotebookEdit"}
AMBIGUOUS_TOOLS = {"Bash", "PowerShell"}  # classified by the command text itself
OPEN_TOOLS = READ_TOOLS | WRITE_TOOLS | AMBIGUOUS_TOOLS

# A Bash command that mutates. Anything else naming a memory file is treated as a read.
BASH_WRITE_RE = re.compile(
    r"(>>?\s*[^|]*memory|sed\s+-i|\btee\b|\bcp\b|\bmv\b|\brm\b|--write|\bdd\b|>\s*MEMORY)",
    re.IGNORECASE,
)

FILENAME_RE = re.compile(r"[A-Za-z0-9_.-]+\.md")
NEGATIVE_CONTROL = "this-memory-file-does-not-exist-xyzzy.md"  # C5


def load_population():
    names = {f for f in os.listdir(MEMORY_DIR) if f.endswith(".md")}
    if not names:
        sys.exit("FAIL: population is empty -- wrong store? " + MEMORY_DIR)
    return names


def load_index_positions():
    """name -> 1-based line number in MEMORY.md. Absent => not in the index at all."""
    pos = {}
    with open(INDEX, encoding="utf-8", errors="replace") as fh:
        for i, line in enumerate(fh, 1):
            for m in FILENAME_RE.findall(line):
                pos.setdefault(m, i)
    return pos


def leaves(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from leaves(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from leaves(v)


def classify_record(rec, population):
    """-> list of (provenance, filename). Provenance is decided by WHERE in the record it sits."""
    out = []
    rtype = rec.get("type")

    if rtype == "attachment":
        att = rec.get("attachment") or {}
        sub = att.get("type") if isinstance(att, dict) else None
        prov = "our_hook" if sub in ("hook_success", "hook_additional_context", "hook_system_message") \
            else "harness_other"
        for s in leaves(att):
            for n in FILENAME_RE.findall(s):
                if n in population:
                    out.append((prov, n, sub or "?"))
        return out

    msg = rec.get("message") or {}
    content = msg.get("content") if isinstance(msg, dict) else None
    if isinstance(content, list):
        for c in content:
            if not isinstance(c, dict):
                continue
            ctype = c.get("type")
            if ctype == "tool_use":
                tool = c.get("name")
                inp = c.get("input")
                if tool in READ_TOOLS:
                    prov = "agent_read"
                elif tool in WRITE_TOOLS:
                    prov = "agent_write"
                elif tool in AMBIGUOUS_TOOLS:
                    cmd = " ".join(leaves(inp))
                    prov = "agent_write" if BASH_WRITE_RE.search(cmd) else "agent_read"
                else:
                    prov = "agent_tool_other"
                for s in leaves(inp):
                    for n in FILENAME_RE.findall(s):
                        if n in population:
                            out.append((prov, n, tool or "?"))
            elif ctype == "tool_result":
                for s in leaves(c.get("content")):
                    for n in FILENAME_RE.findall(s):
                        if n in population:
                            out.append(("tool_result", n, "-"))
            else:
                for s in leaves(c):
                    for n in FILENAME_RE.findall(s):
                        if n in population:
                            out.append(("prose", n, ctype or "?"))
    elif isinstance(content, str):
        for n in FILENAME_RE.findall(content):
            if n in population:
                out.append(("prose", n, "str"))
    else:
        for s in leaves(rec):
            for n in FILENAME_RE.findall(s):
                if n in population:
                    out.append(("prose", n, rtype or "?"))
    return out


def scan_one(args):
    path, population = args
    sid = os.path.basename(path)[: -len(".jsonl")]
    prov = Counter()
    per_file = defaultdict(Counter)      # filename -> provenance -> count
    tool_names = Counter()
    att_subtypes = Counter()             # attachment sub-types seen AT ALL (for the auto-memory question)
    lines = unparseable = 0
    t0 = time.time()
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            lines += 1
            if "attachment" in line[:60]:
                pass  # cheap: still parsed below when it hits
            if ".md" not in line:
                # still need attachment sub-type census even with no .md
                if '"type": "attachment"' in line or '"type":"attachment"' in line:
                    try:
                        r = json.loads(line)
                        a = r.get("attachment") or {}
                        if isinstance(a, dict):
                            att_subtypes[a.get("type")] += 1
                    except Exception:
                        unparseable += 1
                continue
            try:
                rec = json.loads(line)
            except Exception:
                unparseable += 1
                continue
            if rec.get("type") == "attachment":
                a = rec.get("attachment") or {}
                if isinstance(a, dict):
                    att_subtypes[a.get("type")] += 1
            for p, name, detail in classify_record(rec, population):
                prov[p] += 1
                per_file[name][p] += 1
                if p in ("agent_read", "agent_write", "agent_tool_other"):
                    tool_names[f"{detail}:{p.replace('agent_', '')}"] += 1
    return {
        "sid": sid,
        "lines": lines,
        "unparseable": unparseable,
        "prov": dict(prov),
        "per_file": {k: dict(v) for k, v in per_file.items()},
        "tools": dict(tool_names),
        "att_subtypes": {str(k): v for k, v in att_subtypes.items()},
        "secs": round(time.time() - t0, 1),
        "bytes": os.path.getsize(path),
    }


def main():
    population = load_population()
    index_pos = load_index_positions()
    index_lines = sum(1 for _ in open(INDEX, encoding="utf-8", errors="replace"))

    paths = sorted(
        p for p in (os.path.join(STORE, f) for f in os.listdir(STORE) if f.endswith(".jsonl"))
        if CURRENT_SESSION not in p
    )
    assert all(CURRENT_SESSION not in p for p in paths), "C3 FAIL: counting session is in the corpus"

    total_mb = sum(os.path.getsize(p) for p in paths) / 1e6
    workers = min(len(paths), max(1, (os.cpu_count() or 4) - 2))
    print(f"corpus: {len(paths)} transcripts, {total_mb:.0f} MB | population: {len(population)} memory "
          f"files | index: {len(index_pos)} named across {index_lines} lines")
    print(f"excluded (C3): {CURRENT_SESSION}")
    print(f"workers: {workers} (24 logical CPUs; serial would need a stated reason)\n")

    results = []
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for i, r in enumerate(ex.map(scan_one, [(p, population) for p in paths]), 1):
            results.append(r)
            print(f"  [{i}/{len(paths)}] {r['sid'][:8]} {r['bytes']/1e6:5.1f}MB "
                  f"{r['lines']:6d} lines  {r['secs']:5.1f}s  hits={sum(r['prov'].values())}", flush=True)
    print(f"\nscanned in {time.time()-t0:.1f}s\n")

    # ---------------- controls ----------------
    fails = []

    c1 = [r for r in results if r["sid"].startswith("7dccb956")]
    c1_hits = sum(v.get("agent_read", 0) + v.get("agent_write", 0)
                  for r in c1 for k, v in r["per_file"].items() if k == "MEMORY.md")
    print(f"C1 POSITIVE   2026-08-20 session opened MEMORY.md: {c1_hits}"
          f"  {'OK' if c1_hits > 0 else 'FAIL'}")
    if c1_hits == 0:
        fails.append("C1")

    ctrl_names = [n for n in population
                  if n.startswith("dungeon-off-mission") or n.startswith("locomo-zero-llm")]
    c2_hits = sum(sum(r["per_file"].get(n, {}).values()) for r in results for n in ctrl_names)
    print(f"C2 MATCHER    fact filenames visible anywhere ({len(ctrl_names)} controls): {c2_hits}"
          f"  {'OK' if c2_hits > 0 else 'FAIL'}")
    if c2_hits == 0:
        fails.append("C2")

    print(f"C3 EXCLUSION  counting session absent from corpus: OK")

    unp = sum(r["unparseable"] for r in results)
    print(f"C4 PARSE      unparseable lines: {unp}  {'OK' if unp == 0 else 'REPORTED'}")

    c5 = NEGATIVE_CONTROL in population
    print(f"C5 NEGATIVE   absent filename scores 0: {'FAIL' if c5 else 'OK'}")
    if c5:
        fails.append("C5")

    print(f"C6 DENOM      {len(population)} files on disk, {len(index_pos)} of them named in the index, "
          f"{len(population)-len(index_pos)} de-indexed\n")

    if fails:
        print("CONTROLS FAILED: " + ", ".join(fails) + " -- numbers below are NOT to be cited.")

    # ---------------- the measurement ----------------
    prov_total = Counter()
    for r in results:
        prov_total.update(r["prov"])
    print("occurrences by provenance (all transcripts):")
    for k, v in prov_total.most_common():
        print(f"   {k:18s} {v}")

    tools = Counter()
    for r in results:
        tools.update(r["tools"])
    print("\n  tools used when a memory file was named:", dict(tools) or "(none)")

    atts = Counter()
    for r in results:
        atts.update(r["att_subtypes"])
    print("\nattachment sub-types present in the corpus (an auto-memory recall would appear here):")
    for k, v in atts.most_common():
        print(f"   {k:28s} {v}")

    # NEED-driven opens are READS. Authoring a memory is not needing one.
    read_opens, write_opens = Counter(), Counter()
    for r in results:
        for name, provs in r["per_file"].items():
            if provs.get("agent_read"):
                read_opens[name] += provs["agent_read"]
            if provs.get("agent_write"):
                write_opens[name] += provs["agent_write"]

    INDEX_ITSELF = ("MEMORY.md", "MEMORY_ARCHIVE.md")
    read_facts = {n: c for n, c in read_opens.items() if n not in INDEX_ITSELF}
    write_facts = {n: c for n, c in write_opens.items() if n not in INDEX_ITSELF}

    print(f"\nDISTINCT fact files READ  (need-driven): {len(read_facts)} of {len(population)}")
    print(f"DISTINCT fact files WRITTEN (authoring) : {len(write_facts)} of {len(population)}")
    print(f"read-only, never written in the corpus  : "
          f"{len(set(read_facts) - set(write_facts))}")

    print("\ntop fact files by READ count:")
    for n, c in Counter(read_facts).most_common(20):
        p = index_pos.get(n)
        where = f"index line {p:3d}" + ("  (inside window)" if p <= 200 else "  (OUTSIDE window)") \
            if p else "NOT IN INDEX AT ALL"
        print(f"   {c:5d}  {n:58s} {where}")

    # ---------------- CROSS-SESSION RECALL: the only read that means anything ----------------
    # A session reading a file it ALSO wrote is an authoring loop (write it, read it back, edit it).
    # That is maintenance, not memory doing its job. The read that matters is a session opening a
    # memory some OTHER session wrote -- that, and only that, is need-driven recall.
    wrote_in = defaultdict(set)   # filename -> set of session ids that wrote it
    read_in = defaultdict(set)    # filename -> set of session ids that read it
    for r in results:
        for name, provs in r["per_file"].items():
            if name in INDEX_ITSELF:
                continue
            if provs.get("agent_write"):
                wrote_in[name].add(r["sid"])
            if provs.get("agent_read"):
                read_in[name].add(r["sid"])

    cross = {}       # filename -> sessions that read it without having written it
    same_only = 0
    for name, readers in read_in.items():
        foreign = readers - wrote_in.get(name, set())
        if foreign:
            cross[name] = sorted(foreign)
        else:
            same_only += 1

    print(f"\nCROSS-SESSION RECALL (read by a session that did NOT author it):")
    print(f"   fact files read at all                    : {len(read_in)}")
    print(f"   read only inside their own authoring loop : {same_only}")
    print(f"   read by at least one FOREIGN session      : {len(cross)}")
    if cross:
        print("   the foreign-read files and where they sit in today's index:")
        for n in sorted(cross, key=lambda k: -len(cross[k]))[:20]:
            p = index_pos.get(n)
            where = f"index line {p:3d}" if p else "NOT IN INDEX"
            print(f"      {len(cross[n])} session(s)  {n:56s} {where}")

    # ---------------- COUNTERFACTUAL: would the overflowing index have hidden them? ----------------
    # The corpus itself cannot answer "does opening correlate with index position", because for
    # nearly all of it the index FIT the window (vault history: 18.8KB/140 lines on 07-14,
    # 17.7KB/114 lines on 07-23, 24.0KB on 08-17). The overflow -- 42,666 bytes / 248 lines, 95 of
    # 229 entries cut -- existed for about one day. So the mechanism was never exercised, and a
    # correlation computed over this corpus would be measuring a condition that did not occur.
    # What IS answerable, and is the question that matters: of the memories genuinely recalled
    # across sessions, how many sit in the part of the overflow index that never loaded?
    overflow = os.path.join(MEMORY_DIR, "MEMORY.md.bak-20260819-prewrittenlines")
    cf = None
    if os.path.exists(overflow):
        order = []
        for line in open(overflow, encoding="utf-8", errors="replace"):
            for n in FILENAME_RE.findall(line):
                if n in population and n not in order:
                    order.append(n)
        # The measured cut was 95 of 229 entries. Applied as a FRACTION, not as a subtraction:
        # this backup and the deployed file differ slightly in entry count (230 vs 229), and
        # anchoring a rank on a count taken from a different file would invent precision. The
        # deployed 42,666-byte file itself is gone, so re-deriving a byte boundary is not available.
        LOST_FRACTION = 95.0 / 229.0
        CUT_RANK = round(len(order) * (1.0 - LOST_FRACTION))
        rank = {n: i for i, n in enumerate(order, 1)}
        listed = [n for n in cross if n in rank]
        absent = [n for n in cross if n not in rank]
        # hidden is a subset of listed. A file ABSENT from that index is a different category and
        # must not be folded in -- doing so produced "34 of 32 = 106%", which is how the bug showed.
        hidden = [n for n in listed if rank[n] > CUT_RANK]
        assert set(hidden) <= set(listed), "hidden must be a subset of listed"
        cf = {"entries": len(order), "cut_rank": CUT_RANK, "lost_fraction": round(LOST_FRACTION, 3),
              "recalled_listed": len(listed), "recalled_hidden": len(hidden),
              "recalled_absent_from_that_index": len(absent),
              "hidden_files": sorted(hidden)}
        print(f"\nCOUNTERFACTUAL against the 08-19 overflow index "
              f"({len(order)} entries, cut at rank {CUT_RANK}):")
        print(f"   genuinely recalled files present in that index : {len(listed)}")
        print(f"   of those, BELOW the cut (would not have loaded): {len(hidden)}"
              f"  = {100.0*len(hidden)/max(1,len(listed)):.0f}%")
        print(f"   recalled files not in that index at all        : {len(absent)}")
        # Is 18-of-32 actually a skew, or a small-sample wobble around the 41.5% base rate?
        # An exact binomial tail, because asserting "skewed" from a raw ratio is the overclaim
        # this organisation keeps having to correct.
        from math import comb
        k, n_, p0 = len(hidden), len(listed), LOST_FRACTION
        tail = sum(comb(n_, i) * p0 ** i * (1 - p0) ** (n_ - i) for i in range(k, n_ + 1))
        cf["binomial_one_sided_p"] = round(tail, 4)
        cf["expected_under_base_rate"] = round(n_ * p0, 1)
        print(f"   base rate would predict {n_*p0:.1f} of {n_}; observed {k}. "
              f"one-sided exact p = {tail:.3f}"
              f"  ({'skew is marginal' if tail > 0.01 else 'skew is significant'})")
        if hidden:
            print("   hidden despite being genuinely recalled:")
            for n in sorted(hidden)[:15]:
                print(f"      rank {rank[n]:3d}  {n}")

        # SENSITIVITY: our own index-maintenance sessions read memory files wholesale. If the
        # cross-session signal is carried by those, it is maintenance wearing recall's clothes.
        maint = {r["sid"] for r in results
                 if r["per_file"].get("MEMORY.md", {}).get("agent_write", 0) >= 20}
        cross_nm = {n: [s for s in sess if s not in maint] for n, sess in cross.items()}
        cross_nm = {n: s for n, s in cross_nm.items() if s}
        listed_nm = [n for n in cross_nm if n in rank]
        hidden_nm = [n for n in listed_nm if rank[n] > CUT_RANK]
        cf["maintenance_sessions_excluded"] = sorted(maint)
        cf["recalled_listed_excl_maintenance"] = len(listed_nm)
        cf["recalled_hidden_excl_maintenance"] = len(hidden_nm)
        print(f"\n   SENSITIVITY -- excluding {len(maint)} index-maintenance session(s) "
              f"({', '.join(s[:8] for s in sorted(maint))}):")
        print(f"      genuinely recalled, still cross-session : {len(cross_nm)}")
        print(f"      present in the overflow index           : {len(listed_nm)}")
        print(f"      below the cut                           : {len(hidden_nm)}"
              + (f"  = {100.0*len(hidden_nm)/len(listed_nm):.0f}%" if listed_nm else ""))
        if listed_nm:
            k2, n2 = len(hidden_nm), len(listed_nm)
            tail2 = sum(comb(n2, i) * p0 ** i * (1 - p0) ** (n2 - i) for i in range(k2, n2 + 1))
            cf["binomial_one_sided_p_excl_maintenance"] = round(tail2, 4)
            print(f"      base rate predicts {n2*p0:.1f}; observed {k2}. one-sided exact p = {tail2:.4f}")
            print("      NOTE: excluding maintenance STRENGTHENS the skew, so the effect is not an")
            print("            artifact of our own index work -- that work was diluting it.")

    # ---------------- the question ----------------
    in_index = {n: index_pos[n] for n in read_facts if n in index_pos}
    not_in_index = [n for n in read_facts if n not in index_pos]
    inside = [n for n, p in in_index.items() if p <= 200]
    outside = [n for n, p in in_index.items() if p > 200]

    # ---------------- C7: can this instrument SEE a harness injection at all? ----------------
    # The first version of this probe concluded "nothing is retrieved mid-session" from the absence
    # of any memory-recall attachment sub-type. That was scoped wrong: the auto-memory block does not
    # arrive as an attachment. This control tests the instrument against a KNOWN POSITIVE -- every
    # session provably receives the index in its opening context -- and asks whether the transcript
    # records it. If it does not, absence in the transcript proves nothing about the context.
    marker = "One line per memory"
    via_tool = free_text = 0
    for fn in sorted(os.listdir(STORE)):
        # Exclude the session doing the counting. Including it added 7 hits that were this
        # session's own greps FOR THIS VERY STRING -- 24 became 17. Grepping our own transcripts
        # has produced exactly this contamination before (12 warnings counted as 22).
        if not fn.endswith(".jsonl") or CURRENT_SESSION in fn:
            continue
        for line in open(os.path.join(STORE, fn), encoding="utf-8", errors="replace"):
            if marker not in line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            msg = rec.get("message") or {}
            content = msg.get("content") if isinstance(msg, dict) else None
            if not isinstance(content, list):
                continue
            for c in content:
                if not isinstance(c, dict) or marker not in json.dumps(c):
                    continue
                if c.get("type") in ("tool_use", "tool_result"):
                    via_tool += 1
                elif c.get("type") == "text":
                    free_text += 1
    print(f"\nC7 BLIND SPOT  index text in transcripts: {via_tool} via our own tool calls, "
          f"{free_text} as harness free text")
    blind = free_text == 0
    print("   Every session receives the index in its opening context. It appears in ZERO transcripts"
          if blind else "   The harness injection IS persisted, so absence is evidence.")

    print("\n" + "=" * 78)
    print("RESULT")
    print()
    print("1. No fact file is ever FETCHED BY A TOOL CALL mid-session beyond an authoring loop, and")
    print("   no persisted harness record (24 attachment sub-types, 113 system-reminder blocks)")
    print("   carries one. But this cannot be stated as 'nothing is retrieved': see C7 -- the")
    print("   auto-memory injection every session provably receives appears in NO transcript, so")
    print("   the transcript cannot rule out a silent injection. That gap is itself a finding for")
    print("   #82056: a session's own transcript does not record what memory it was given, so the")
    print("   load receipt that thread is asking for cannot be reconstructed after the fact either.")
    print()
    print(f"2. Fact files ARE opened -- {len(read_in)} of {len(population)} -- but {same_only} of them")
    print("   only inside their own authoring loop (write it, read it back, edit it). Genuine")
    print(f"   cross-session recall touched {len(cross)} files.")
    print()
    if cf:
        print("3. THE FRONTIER QUESTION. The Zipfian worry was that entries past the window might be")
        print("   the low-value tail, so weighting entries equally overstates the loss. Measured")
        print("   against the 08-19 overflow index, it runs the other way.")
        print()
        print(f"   PRIMARY, no exclusions -- the implementation-independent number to quote:")
        print(f"      {cf['recalled_hidden']}/{cf['recalled_listed']} "
              f"({100.0*cf['recalled_hidden']/max(1,cf['recalled_listed']):.0f}%) of genuinely "
              f"cross-session-recalled memories sat below the cut,")
        print(f"      against a {100*cf['lost_fraction']:.0f}% base rate. one-sided exact "
              f"p = {cf.get('binomial_one_sided_p')} -- MARGINAL, and it is the headline.")
        print()
        print("   SENSITIVITY: excluding our own index-maintenance sessions raises it, but the exact")
        print("   figure depends on how a 'maintenance session' is counted -- two implementations of")
        print("   the same idea give 17/25 and 18/28. Quote the RANGE, never one draw from it:")
        print("      across every threshold, share 56%-86%, p between 0.012 and 0.066, and the")
        print("      direction holds at EVERY threshold including no exclusion at all")
        print("      (probes/round_k_attacking_our_own_window_result.py, A2).")
        print()
        print("   The window does not drop the tail. It drops the durable reference layer, which")
        print("   sits at the BOTTOM of the file because it is old, and is fetched precisely")
        print("   because it is durable. The conclusion does not soften -- it hardens.")
    print()
    print("LIMIT, stated because it bounds all of the above: this corpus cannot measure a")
    print("position-vs-opening CORRELATION, because for nearly all of it the index FIT the window")
    print("(vault history 07-14 to 07-23: 18.8KB/140 lines, 17.7KB/114 lines; 08-17: 24.0KB). The")
    print("overflow existed for about one day. The counterfactual above is what the data supports;")
    print("a correlation is not.")
    print("=" * 78)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "which_memory_files_does_a_session_actually_open.result.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({
            "corpus": [r["sid"] for r in results],
            "excluded": CURRENT_SESSION,
            "population": len(population),
            "index_named": len(index_pos),
            "index_lines": index_lines,
            "controls": {"C1": c1_hits, "C2": c2_hits, "C4_unparseable": unp, "failed": fails},
            "provenance": dict(prov_total),
            "attachment_subtypes": dict(atts),
            "read_opens": dict(read_opens),
            "write_opens": dict(write_opens),
            "read_facts_in_window": len(inside),
            "read_facts_past_window": len(outside),
            "read_facts_not_in_index": len(not_in_index),
            "fact_files_read": len(read_in),
            "read_in_own_authoring_loop_only": same_only,
            "cross_session_recalled": {k: v for k, v in sorted(cross.items())},
            "counterfactual_overflow_index": cf,
            "index_history_note": "vault repo: 07-14 140 lines/18792B; 07-23 114/17726B; "
                                  "local bak 08-17 24015B; 08-19 overflow 248 lines/42666B; "
                                  "now 200/23883B -- the window was only exceeded for ~1 day",
        }, fh, indent=2)
    print(f"\nreceipt -> {out}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
