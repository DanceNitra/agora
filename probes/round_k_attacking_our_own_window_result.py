"""Adversarial pass on OUR OWN result, before a draft exists.

The claim under attack (probes/which_memory_files_does_a_session_actually_open.py):
"of the memories genuinely recalled across sessions, 17/25 (68%) sat below the cut the overflowing
index would have made, against a 41.5% base rate, p=0.0067 -- so the window drops the durable
reference layer, not the low-value tail."

The rule this file exists to satisfy: the skeptic runs FIRST, on the CLAIM and its MEASUREMENT, not
on prose, and before any draft is written. A literature panel cannot catch a wrong measurement --
five lenses and four citation verifiers once polished a false first sentence that a single query
killed. So every attack here is computational.

  A1 BULK-SCAN INFLATION   If the "cross-session reads" come from a handful of commands that each
                           named dozens of memory files (a grep sweep, a wholesale cat), then they
                           are one scan wearing 48 recalls' clothing. Measures files-named-per-call.
  A2 THRESHOLD TUNING      The maintenance exclusion used ">=20 writes to MEMORY.md". That is a
                           knob, and 68% could be the value it was turned to. Recomputes the result
                           across the whole threshold range including NO exclusion at all.
  A3 ORDER ASSUMPTION      The counterfactual reads entry order from MEMORY.md.bak-...prewrittenlines
                           and applies a cut rank measured on the DEPLOYED 42,666-byte file, which no
                           longer exists. That is only valid if the written-lines transform preserved
                           entry ORDER. Tests order stability across every surviving index state.
  A4 SURVIVORSHIP          Files DELETED or renamed since 08-19 cannot be recalled today and cannot
                           appear below the cut either. Checks whether the recalled set is biased by
                           what still exists.

Run:  python probes/round_k_attacking_our_own_window_result.py
"""

import json
import os
import re
import sys
from collections import Counter, defaultdict
from math import comb

HOME = os.path.expanduser("~")
STORE = os.path.join(HOME, ".claude", "projects", "C--Users-Danculus-agora")
MEMORY_DIR = os.path.join(STORE, "memory")
CURRENT_SESSION = "46de8dac-117b-4f83-a449-d7e8655b1368"
OVERFLOW = os.path.join(MEMORY_DIR, "MEMORY.md.bak-20260819-prewrittenlines")

READ_TOOLS = {"Read", "Grep", "Glob"}
WRITE_TOOLS = {"Write", "Edit", "NotebookEdit"}
AMBIGUOUS = {"Bash", "PowerShell"}
BASH_WRITE_RE = re.compile(
    r"(>>?\s*[^|]*memory|sed\s+-i|\btee\b|\bcp\b|\bmv\b|\brm\b|--write|\bdd\b|>\s*MEMORY)", re.I)
FN = re.compile(r"[A-Za-z0-9_.-]+\.md")
INDEX_ITSELF = ("MEMORY.md", "MEMORY_ARCHIVE.md")
LOST_FRACTION = 95.0 / 229.0


def leaves(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for v in o.values():
            yield from leaves(v)
    elif isinstance(o, list):
        for v in o:
            yield from leaves(v)


def scan():
    """-> per session: reads/writes, plus every individual call with the files it named."""
    pop = {f for f in os.listdir(MEMORY_DIR) if f.endswith(".md")}
    sessions = {}
    calls = []  # (sid, tool, n_files_named, frozenset(files)) for READ calls only
    for fn in sorted(os.listdir(STORE)):
        if not fn.endswith(".jsonl") or CURRENT_SESSION in fn:
            continue
        sid = fn[:-6]
        reads, writes = Counter(), Counter()
        for line in open(os.path.join(STORE, fn), encoding="utf-8", errors="replace"):
            if ".md" not in line:
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
                if not isinstance(c, dict) or c.get("type") != "tool_use":
                    continue
                tool, inp = c.get("name"), c.get("input")
                if tool in READ_TOOLS:
                    kind = "read"
                elif tool in WRITE_TOOLS:
                    kind = "write"
                elif tool in AMBIGUOUS:
                    kind = "write" if BASH_WRITE_RE.search(" ".join(leaves(inp))) else "read"
                else:
                    continue
                named = {n for s in leaves(inp) for n in FN.findall(s) if n in pop}
                if not named:
                    continue
                (reads if kind == "read" else writes).update(named)
                if kind == "read":
                    facts = named - set(INDEX_ITSELF)
                    if facts:
                        calls.append((sid, tool, len(facts), frozenset(facts)))
        sessions[sid] = {"reads": reads, "writes": writes}
    return pop, sessions, calls


def cross_set(sessions, exclude=frozenset()):
    """files read by a session that did NOT write them, ignoring excluded sessions."""
    wrote = defaultdict(set)
    read = defaultdict(set)
    for sid, d in sessions.items():
        for n in d["writes"]:
            if n not in INDEX_ITSELF:
                wrote[n].add(sid)
        for n in d["reads"]:
            if n not in INDEX_ITSELF and sid not in exclude:
                read[n].add(sid)
    return {n: sorted(s - wrote.get(n, set())) for n, s in read.items() if s - wrote.get(n, set())}


def index_order(path):
    order = []
    for line in open(path, encoding="utf-8", errors="replace"):
        for n in FN.findall(line):
            if n not in order:
                order.append(n)
    return order


def binom_tail(k, n, p):
    return sum(comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


def spearman(a, b):
    n = len(a)
    if n < 3:
        return None
    ra = {v: i for i, v in enumerate(sorted(a))}
    rb = {v: i for i, v in enumerate(sorted(b))}
    d2 = sum((ra[x] - rb[y]) ** 2 for x, y in zip(a, b))
    return 1 - 6 * d2 / (n * (n * n - 1))


def main():
    pop, sessions, calls = scan()
    order = index_order(OVERFLOW)
    rank = {n: i for i, n in enumerate(order, 1)}
    CUT = round(len(order) * (1 - LOST_FRACTION))
    print(f"corpus {len(sessions)} sessions | population {len(pop)} | overflow index {len(order)} "
          f"entries, cut at rank {CUT}\n")

    verdicts = []

    # ---------------- A1 bulk-scan inflation ----------------
    print("A1 BULK-SCAN INFLATION")
    sizes = Counter(n for _, _, n, _ in calls)
    tot_calls = len(calls)
    print(f"   read calls naming >=1 fact file: {tot_calls}")
    print("   files named per call: " + ", ".join(
        f"{k}->{v}" for k, v in sorted(sizes.items())[:12]) + (" ..." if len(sizes) > 12 else ""))
    big = [c for c in calls if c[2] >= 5]
    cross_all = cross_set(sessions)
    only_big = set()
    for _, _, _, fs in big:
        only_big |= set(fs)
    carried = {n for n in cross_all if n in only_big}
    singles = {n for _, _, k, fs in calls if k <= 2 for n in fs}
    print(f"   calls naming >=5 files: {len(big)}  (they touch {len(only_big)} distinct files)")
    print(f"   of the {len(cross_all)} cross-session files, {len(carried)} appear ONLY via such calls: "
          f"{len({n for n in carried if n not in singles})}")
    solo = len({n for n in cross_all if n in singles})
    print(f"   reachable by a call naming <=2 files (targeted read): {solo} of {len(cross_all)}")
    ok1 = solo >= 0.5 * len(cross_all)
    verdicts.append(("A1", ok1, f"{solo}/{len(cross_all)} targeted"))
    print(f"   -> {'SURVIVES' if ok1 else 'FAILS'}: the signal is {'not ' if ok1 else ''}carried by bulk scans\n")

    # ---------------- A2 threshold tuning ----------------
    print("A2 THRESHOLD TUNING (the '>=20 writes to MEMORY.md' knob)")
    print("   thr   excluded   listed  hidden   share      p")
    results = []
    for thr in (10 ** 9, 100, 50, 20, 10, 5, 1):
        maint = {sid for sid, d in sessions.items() if d["writes"].get("MEMORY.md", 0) >= thr}
        cs = cross_set(sessions, exclude=maint)
        listed = [n for n in cs if n in rank]
        hidden = [n for n in listed if rank[n] > CUT]
        if not listed:
            continue
        p = binom_tail(len(hidden), len(listed), LOST_FRACTION)
        label = "none" if thr == 10 ** 9 else str(thr)
        print(f"   {label:>4}  {len(maint):>8}   {len(listed):>6}  {len(hidden):>6}   "
              f"{100*len(hidden)/len(listed):>5.0f}%   {p:.4f}")
        results.append((label, len(listed), len(hidden), p))
    above = [r for r in results if r[2] / r[1] > LOST_FRACTION]
    ok2 = len(above) == len(results)
    verdicts.append(("A2", ok2, f"{len(above)}/{len(results)} thresholds above base rate"))
    print(f"   -> {'SURVIVES' if ok2 else 'FAILS'}: the direction "
          f"{'holds at every threshold including no exclusion' if ok2 else 'depends on the knob'}\n")

    # ---------------- A3 order assumption ----------------
    print("A3 ORDER ASSUMPTION (cut rank imported from a file that no longer exists)")
    others = sorted(f for f in os.listdir(MEMORY_DIR)
                    if f.startswith("MEMORY.md.bak-") and f != os.path.basename(OVERFLOW))
    base = index_order(OVERFLOW)
    worst = 1.0
    for o in others + ["MEMORY.md"]:
        oo = index_order(os.path.join(MEMORY_DIR, o))
        common = [n for n in base if n in set(oo)]
        if len(common) < 10:
            continue
        r1 = [base.index(n) for n in common]
        r2 = [oo.index(n) for n in common]
        rho = spearman(r1, r2)
        worst = min(worst, rho)
        print(f"   vs {o[-28:]:<30} n={len(common):>3}  rho={rho:+.3f}")
    ok3 = worst >= 0.9
    verdicts.append(("A3", ok3, f"worst rho {worst:+.3f}"))
    print(f"   -> {'SURVIVES' if ok3 else 'FAILS'}: entry order is "
          f"{'stable across every surviving index state' if ok3 else 'NOT stable -- the cut rank does not transfer'}\n")

    # ---------------- A4 survivorship ----------------
    print("A4 SURVIVORSHIP")
    gone = [n for n in order if n not in pop]
    cs = cross_set(sessions)
    print(f"   entries in the overflow index that no longer exist on disk: {len(gone)}")
    print(f"   cross-session files missing from the overflow index      : "
          f"{len([n for n in cs if n not in rank])}")
    ok4 = len(gone) <= 0.1 * len(order)
    verdicts.append(("A4", ok4, f"{len(gone)} of {len(order)} entries vanished"))
    print(f"   -> {'SURVIVES' if ok4 else 'FAILS'}\n")

    print("=" * 72)
    for name, ok, note in verdicts:
        print(f"   {name}  {'SURVIVES' if ok else 'FAILS   '}  {note}")
    failed = [v for v in verdicts if not v[1]]
    print("=" * 72)
    print("VERDICT: " + ("claim survives the adversarial pass" if not failed
                         else f"{len(failed)} attack(s) landed -- the claim must be changed before it goes out"))
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "round_k_attacking_our_own_window_result.result.json")
    json.dump({"verdicts": [{"attack": a, "survives": b, "note": c} for a, b, c in verdicts],
               "threshold_sweep": results, "cut_rank": CUT, "entries": len(order)},
              open(out, "w", encoding="utf-8"), indent=2)
    print(f"receipt -> {out}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
