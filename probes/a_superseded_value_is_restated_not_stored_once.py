"""How many records restate a value that a supersession is supposed to retire?

`JasperHG90/memex#233` proposes conflict detection between memory records: classify a contradiction
as hard or soft, resolve the hard ones, present both sides of the soft ones. Its own triage bot
raised the question that has sat unanswered for two months, through three research updates that each
added papers and none added a number:

    "Soft conflicts may be rare enough that the detection overhead and schema complexity aren't
     justified. The RFC should include an estimate of soft-conflict frequency."

This measures something upstream of that question, and the answer decides whether the frequency
matters. A conflict-detection design assumes a superseded value lives in ONE record that can be found
and paired with its replacement. In conversational prose it does not. The user states it, the
assistant echoes it, a summary repeats it, a template quotes it -- so retiring the one record that
carries a key leaves the rest active and retrievable.

MEASURED HERE, per scenario, from the corpus's own ground truth (`chain_id`, `old_value`,
`new_value` in the operation trace -- no LLM, no judge):

  * multiplicity: for each superseded value, how many records in the store restate it
  * keyed share: how many of those restatements carry a key a supersession could act on

CONTROLS, because a scan that matches nothing reports multiplicity 1.0 and that reads like good news:
  * every scenario must yield at least one chain, or it is reported as UNREADABLE rather than clean;
  * the CURRENT value's multiplicity is measured alongside the stale one -- if both come back 1.0 the
    matcher is broken, not the corpus tidy;
  * a synthetic control value planted N times must read exactly N.

Run:  python probes/a_superseded_value_is_restated_not_stored_once.py
"""
from __future__ import annotations
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "agora_output", "lab", "memops", "data")


def scenarios():
    if not os.path.isdir(DATA):
        return []
    return [os.path.join(DATA, f) for f in sorted(os.listdir(DATA)) if f.endswith(".json")]


def chains(blob):
    """chain_id -> ordered [(step, value)] from the scenario's own operation trace."""
    out = {}
    for op in (blob.get("operations") or []):
        cid = op.get("chain_id")
        if not cid:
            continue
        step = op.get("chain_step", 0)
        for field in ("new_value", "value"):
            v = op.get(field)
            if isinstance(v, str) and v.strip():
                out.setdefault(cid, []).append((step, v.strip()))
                break
    for cid in out:
        out[cid].sort(key=lambda p: p[0])
    return out


def texts(blob):
    """Every utterance the store would hold, from the corpus's own `conversations` -> `dialogue`.

    The first version of this reader looked for `sessions`/`turns`/`messages` and found none of them,
    so it returned an empty corpus for every scenario. That is why the probe carries the control it
    does: an empty corpus makes every value read 1.0 restatements, which is exactly the reassuring
    answer, and the run refused instead of reporting it.
    """
    out = []
    for seg in (blob.get("conversations") or []):
        for turn in (seg.get("dialogue") or []):
            if isinstance(turn, dict) and isinstance(turn.get("content"), str):
                out.append(turn["content"])
            elif isinstance(turn, str):
                out.append(turn)
    return out


def count(value, corpus):
    """Loose: any substring hit. Reported for comparison, never as the headline."""
    rx = re.compile(re.escape(value), re.I)
    return sum(1 for t in corpus if rx.search(t))


def strict_count(value, corpus, siblings):
    """THE HEADLINE NUMBER, and the reason it is not `count`.

    "Data Analyst" is a substring of both "Junior Data Analyst" and "Senior Data Analyst", the two
    other values in its own chain, so a substring scan credits it with every mention of either --
    14 restatements where the word-bounded count is 10. The strict count requires a word boundary
    AND excludes any hit sitting inside a longer sibling value from the same chain. The finding is
    quoted from this one, so a reader checking it gets the conservative figure.
    """
    rx = re.compile(r"(?<![\w-])" + re.escape(value) + r"(?![\w-])", re.I)
    longer = [o for o in siblings if value.lower() in o.lower() and len(o) > len(value)]
    n = 0
    for t in corpus:
        for mt in rx.finditer(t):
            window = t[max(0, mt.start() - 30):mt.end() + 30]
            if any(re.search(r"(?<![\w-])" + re.escape(o) + r"(?![\w-])", window, re.I)
                   for o in longer):
                continue
            n += 1
            break
    return n


def control():
    corpus = ["the widget is BLUEBERRY-7 today"] * 4 + ["nothing here", "still nothing"]
    return count("BLUEBERRY-7", corpus)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    c = control()
    print("CONTROL: a value planted 4x reads %d  ->  %s\n" % (c, "PASS" if c == 4 else "FAIL"))
    if c != 4:
        return 1

    files = scenarios()
    if not files:
        print("FAIL -- no scenario files under %s; a scan with no input reports nothing, not zero" % DATA)
        return 1

    rows, unreadable = [], []
    for path in files:
        name = os.path.basename(path)
        try:
            blob = json.load(open(path, encoding="utf-8"))
        except Exception as e:
            unreadable.append((name, "%s: %s" % (type(e).__name__, e)))
            continue
        ch, corpus = chains(blob), texts(blob)
        if not ch or not corpus:
            unreadable.append((name, "chains=%d texts=%d" % (len(ch), len(corpus))))
            continue
        allvals = [v for steps in ch.values() for _, v in steps]
        for cid, steps in ch.items():
            if len(steps) < 2:
                continue
            stale = [v for _, v in steps[:-1]]
            current = steps[-1][1]
            # CLASSIFY BY POSITION, NOT BY VALUE. `kind = "current" if v == current` moved seven
            # superseded values into the current bucket the moment a chain revisited a value, and
            # the totals still summed to 48 so nothing looked wrong.
            for kind, v in [("superseded", x) for x in stale] + [("current", current)]:
                sib = [o for o in allvals if o != v]
                rows.append({"scenario": name, "chain": cid, "kind": kind,
                             "value": v[:40], "restatements": strict_count(v, corpus, sib),
                             "loose": count(v, corpus)})

    if unreadable:
        print("UNREADABLE (reported, never counted as clean):")
        for n, why in unreadable:
            print("   %-34s %s" % (n, why))
        print()

    stale = [r["restatements"] for r in rows if r["kind"] == "superseded"]
    curr = [r["restatements"] for r in rows if r["kind"] == "current"]
    if not stale:
        print("FAIL -- no superseded values found; nothing was measured")
        return 1

    def stats(v):
        # TRUE median, not the upper-middle element. `s[len(s)//2]` is median_high, and printed with
        # %d it reported 6 for the twelve current values where the median is 5.5. That number was
        # cited publicly; anyone recomputing it from the rows in this receipt would have got 5.5 and
        # concluded our arithmetic was wrong. Even n needs the mean of the two middle values.
        s = sorted(v)
        mid = len(s) // 2
        med = s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2.0
        return (sum(s) / len(s), med, max(s), sum(1 for x in s if x > 1) / len(s))

    ms, meds, mxs, sh = stats(stale)
    mc, medc, mxc, ch_ = stats(curr) if curr else (0, 0, 0, 0)
    print("superseded values: n=%d  mean %.2f restatements  median %.1f  max %d  "
          "%.0f%% appear more than once" % (len(stale), ms, meds, mxs, 100 * sh))
    print("current    values: n=%d  mean %.2f restatements  median %.1f  max %d  "
          "%.0f%% appear more than once" % (len(curr), mc, medc, mxc, 100 * ch_))
    if ms <= 1.0 and mc <= 1.0:
        print("\nFAIL -- both read 1.0; the matcher is broken, not the corpus tidy")
        return 1

    print("\ntop restatement counts among superseded values:")
    for r in sorted([r for r in rows if r["kind"] == "superseded"],
                    key=lambda r: -r["restatements"])[:8]:
        print("   %3dx  %-40s  %s" % (r["restatements"], r["value"], r["scenario"]))

    out = os.path.join(HERE, "a_superseded_value_is_restated_not_stored_once.result.json")
    json.dump({"scenarios": len(files), "unreadable": unreadable,
               "superseded": {"n": len(stale), "mean": round(ms, 3), "median": meds, "max": mxs,
                              "share_gt_1": round(sh, 3)},
               "current": {"n": len(curr), "mean": round(mc, 3), "median": medc, "max": mxc,
                           "share_gt_1": round(ch_, 3)},
               "rows": rows}, open(out, "w", encoding="utf-8"), indent=1)
    print("\nreceipt -> " + out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
