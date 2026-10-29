"""The A/B the red-team panel asked for: does the digest help a model ANSWER, or move the bytes?

Every earlier probe here measured text overlap. Overlap is not an outcome: a ranked digest can keep
a term and destroy the line it belonged to, and a digest that names a capture file can save bytes at
one call and spend more at the next. So this asks a model a question it can only answer from the
MIDDLE of a real tool output, serves that output through each strategy at the SAME byte budget, and
scores two things together:

    answered correctly, and the tokens it cost to get there.

The question never comes from the tool call's own arguments, which is what makes it a test rather
than a loop. The saver ranks against the call's arguments, because that is all a PostToolUse hook
has. Whether those arguments predict what the agent asks NEXT is the untested link, so the tasks are
split and both halves are reported:

    intent_aligned       the fact's label shares a term with the call's arguments: the saver's best case.
    intent_independent   it does not: the saver is ranking blind to the question.

ARMS, all served at the digest's own byte length for that row:

    full                 the whole output. The CEILING control.
    digest               the shipped saver.
    digest_no_footer     the same digest without its "Searchable terms:" line.
    truncate             head and tail, the rival.
    even_spread          evenly spaced slices, UNRANKED: ranking's own control.
    bytecount_only       "[tool] (N chars result)", what Hermes emits. A FLOOR control.
    no_output            the question alone. The other FLOOR control.

THE SECOND TURN IS THE POINT. Every arm may reply with exactly NEED_FULL, and then the whole output
is served and the model asked again. That is the ledger the blind-spot lens said we had only one
side of: a strategy that provokes a re-read has not saved anything, it has moved the bytes one turn
later. Tokens are counted across both turns, so the headline is tasks solved per 1000 tokens, not
accuracy.

CONTROLS, each able to fail:
  - no_output and bytecount_only must score near zero. If they do not, the question leaks its answer.
  - full must score high. If it does not, the task set or the model is broken and nothing below means
    anything.
  - every answer must be absent from the first and last EDGE bytes of its source, and unique in it.
  - the WRONG-LABEL control: one task in every batch asks for label A and is graded against another
    row's value. It must score zero.
  - every call carries a nonce and temperature 0, because a 0.0 s reply is a cache hit, not an answer.

Resumable and noisy on purpose: each (task, arm) result is appended to a JSONL as it lands, a rerun
skips what is already there, and progress prints every few tasks.

    python probes/does_the_digest_help_an_agent_answer_or_just_move_the_bytes.py --pilot
    python probes/does_the_digest_help_an_agent_answer_or_just_move_the_bytes.py --tasks 200 --workers 6
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import sqlite3
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULT = Path(__file__).with_suffix(".result.json")
LEDGER = Path(__file__).with_suffix(".ledger.jsonl")
HERMES_DB = Path(os.path.expanduser("~")) / "AppData" / "Local" / "hermes" / "state.db"
PROJECTS = Path(os.path.expanduser("~")) / ".claude" / "projects"
ENV = Path(__file__).resolve().parents[1] / "server" / ".env"

MIN_CHARS = 2000
MAX_CHARS = 40000          # a prompt cap: the `full` arm carries the whole output, so a 300 KB row
                           # would price the ceiling control out by itself. Swept, see --max-chars.
EDGE = 400                 # the window a head-and-tail cut keeps for free
MODEL = "deepseek-v4.1-flash:1017"      # pinned to a dated build; :cloud floats, 0731 is 410 Gone
MAX_TOKENS = 4000          # FLOORED, never capped: this model spends ~30 tokens thinking first
ARMS = ("full", "digest", "digest_no_footer", "truncate", "even_spread", "bytecount_only", "no_output")

_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_\-/.]{2,}")
#: `label: value` or `label = value`, value a token worth asking for.
_FACT = re.compile(r"^[ \t>|*-]*([A-Za-z][A-Za-z0-9 _.\-]{2,40}?)\s*[:=]\s*([^\s,;|]{4,60})\s*$", re.M)

#: A `label:` that is really code. `finally: s.close()` and `if a.dry_run: cmd.append(...)` both
#: match the pattern above and make a nonsense question, so these labels are refused.
_KEYWORDS = frozenset("""
try except finally else elif if while for def class return yield import from with as pass raise
assert lambda global nonlocal del await async match case switch default public private protected
static void const let var function new delete typeof interface struct enum impl fn pub use mod
""".split())

_print_lock = threading.Lock()


def env(key):
    t = ENV.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"^%s=(.*)$" % key, t, re.M)
    return m.group(1).strip() if m else ""


# ---------------------------------------------------------------- the corpora

def hermes_rows():
    """(source, tool, intent, output) for every Hermes tool result over the threshold."""
    sys.path.insert(0, str(HERE))
    from hermes_prune_vs_our_saver_on_his_transcript import call_intent
    con = sqlite3.connect("file:%s?mode=ro" % HERMES_DB.as_posix(), uri=True)
    rows = con.execute(
        "select coalesce(t.tool_name,'?'), t.content, "
        "coalesce((select a.tool_calls from messages a where a.session_id = t.session_id "
        "          and a.role='assistant' and a.tool_calls like '%'||t.tool_call_id||'%' "
        "          limit 1), '') "
        "from messages t where t.role='tool' and length(t.content) > ? order by t.id",
        (MIN_CHARS,)).fetchall()
    for tool, content, args in rows:
        yield "hermes", str(tool), (call_intent(args) or str(tool)), content


INTENT_KEYS = ("description", "command", "query", "path", "file_path", "pattern", "prompt")


def claude_rows():
    """(source, tool, intent, output) for every Claude Code tool result over the threshold."""
    for path in sorted(PROJECTS.glob("*/*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True):
        calls = {}
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            content = (ev.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for item in content:
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "tool_use":
                    a = item.get("input") or {}
                    intent = ""
                    if isinstance(a, dict):
                        for k in INTENT_KEYS:
                            v = a.get(k)
                            if isinstance(v, str) and v.strip():
                                intent = v.strip()[:300]
                                break
                    calls[str(item.get("id"))] = (str(item.get("name") or "tool"),
                                                  intent or str(item.get("name") or "tool output"))
                elif item.get("type") == "tool_result":
                    body = item.get("content")
                    if isinstance(body, list):
                        body = "\n".join(p.get("text", "") for p in body
                                         if isinstance(p, dict) and p.get("type") == "text")
                    if isinstance(body, str) and len(body) >= MIN_CHARS:
                        tool, intent = calls.get(str(item.get("tool_use_id")), ("tool", "tool output"))
                        yield "claude_code", tool, intent, body


# ---------------------------------------------------------------- the tasks

def structured(text):
    """Does this output carry meaning in its SYNTAX, where a ranked cut can destroy it?"""
    head = text.lstrip()[:400]
    if head.startswith(("{", "[")):
        return "json"
    if re.search(r"^(diff --git|@@ |--- |\+\+\+ )", text, re.M):
        return "diff"
    if "Traceback (most recent call last)" in text:
        return "traceback"
    if re.match(r"^[^\n,]{1,60}(,[^\n,]{0,60}){2,}\n[^\n,]{1,60}(,[^\n,]{0,60}){2,}", head):
        return "csv"
    return "prose"


def facts(output, edge):
    """(label, value) pairs that live in the MIDDLE and are unambiguous to grade."""
    edges = output[:edge] + output[-edge:]
    out = []
    for m in _FACT.finditer(output):
        label, value = m.group(1).strip(), m.group(2).strip()
        if len(label) < 3 or value in edges or label in edges:
            continue
        if output.count(value) != 1 or output.count(label) != 1:
            continue                                  # grading must be unambiguous
        if value.lower() in ("true", "false", "null", "none"):
            continue
        if label.lower() in _KEYWORDS or label.split()[0].lower() in _KEYWORDS:
            continue                                  # a code keyword is not a label
        out.append((label, value))
    return out


def build_tasks(limit, seed, edge, max_chars):
    """A STRATIFIED task set: both intent families, and structured shapes on purpose.

    A first version drew one fact per row at random and produced 60 of 60 intent_independent tasks
    and 4 structured ones out of 60. That measures the saver's worst case only, and says nothing
    about diffs or tracebacks, which is where a ranked cut is most likely to destroy an answer. So
    each row contributes the fact that makes it useful: an aligned one if it has any, and the set is
    filled per (family, shape) cell rather than taken in corpus order.
    """
    rng = random.Random(seed)
    rows = list(hermes_rows()) + list(claude_rows())
    rng.shuffle(rows)
    pools: dict[tuple, list] = {}
    rows_seen = skipped_no_fact = skipped_too_big = rows_with_an_aligned_fact = 0

    for source, tool, intent, output in rows:
        rows_seen += 1
        if len(output) > max_chars:
            skipped_too_big += 1
            continue
        cands = facts(output, edge)
        if not cands:
            skipped_no_fact += 1
            continue
        itokens = {w.lower() for w in _WORD.findall(intent)}

        def aligned(label):
            return any(w.lower() in itokens for w in _WORD.findall(label))

        shape = structured(output)
        hit = [c for c in cands if aligned(c[0])]
        rows_with_an_aligned_fact += 1 if hit else 0
        for family, pick in (("intent_aligned", hit),
                             ("intent_independent", [c for c in cands if not aligned(c[0])])):
            if pick:
                label, value = rng.choice(pick)
                pools.setdefault((family, shape), []).append(
                    (source, tool, intent, output, label, value))
                break                  # one task per row, so no output is reused across arms twice

    # round-robin over the (family, shape) cells, so a rare shape is not crowded out
    cells = sorted(pools, key=lambda k: (-len(pools[k]), k))
    for k in cells:
        rng.shuffle(pools[k])
    tasks, i = [], 0
    while len(tasks) < limit and any(pools[k] for k in cells):
        k = cells[i % len(cells)]
        i += 1
        if not pools[k]:
            continue
        source, tool, intent, output, label, value = pools[k].pop()
        tasks.append({
            "id": "%s-%d" % (source, len(tasks)),
            "source": source, "tool": tool, "intent": intent, "output": output,
            "label": label, "answer": value, "shape": k[1], "family": k[0],
        })
    return tasks, {"rows_seen": rows_seen, "skipped_no_gradable_fact": skipped_no_fact,
                   "skipped_over_max_chars": skipped_too_big,
                   "rows_with_an_aligned_fact": rows_with_an_aligned_fact,
                   "cells_available": {"%s/%s" % k: len(v) + sum(
                       1 for t in tasks if (t["family"], t["shape"]) == k) for k, v in pools.items()}}


# ---------------------------------------------------------------- the arms

def strip_footer(dig):
    return "\n".join(ln for ln in dig.splitlines() if not ln.startswith("Searchable terms: "))


def content_only_sections(dig):
    return sum(1 for ln in dig.splitlines() if ln.startswith("- "))


def even_spread(output, budget, sections):
    n = max(1, sections)
    if budget >= len(output):
        return output
    take = max(1, budget // n)
    step = max(1, len(output) // n)
    return "\n".join(output[i * step: i * step + take] for i in range(n))[:budget]


def views(task):
    """Every arm's visible text for one task, all at the digest's own byte budget."""
    from inspeximus.context_saver import save
    output = task["output"]
    dig = save(output, task["intent"], without_reranker="hybrid", ranking="lexical")["text"]
    budget = len(dig)
    return {
        "full": output,
        "digest": dig,
        "digest_no_footer": strip_footer(dig),
        "truncate": output if len(output) <= budget else
                    output[: budget // 2] + "\n...\n" + output[-(budget - budget // 2):],
        "even_spread": even_spread(output, budget, content_only_sections(dig)),
        "bytecount_only": "[%s] (%d chars result)" % (task["tool"], len(output)),
        "no_output": "",
    }


# ---------------------------------------------------------------- the model

PROMPT = (
    "You are given what a tool returned to an agent, possibly shortened.\n"
    "Nonce {nonce}.\n\n"
    "--- tool result ---\n{visible}\n--- end ---\n\n"
    "Question: on the line whose label is `{label}`, what is the value?\n"
    "Reply with ONLY that value, nothing else.\n"
    "If the text above does not contain it, reply with exactly NEED_FULL."
)


def ask(base, key, visible, label, nonce, timeout=240):
    body = {"model": MODEL, "temperature": 0, "max_tokens": MAX_TOKENS,
            "messages": [{"role": "user", "content": PROMPT.format(
                nonce=nonce, visible=visible or "(the tool result was not kept)", label=label)}]}
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions", data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    t0 = time.time()
    r = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    ch = r["choices"][0]
    usage = r.get("usage") or {}
    return ((ch["message"].get("content") or "").strip(),
            ch.get("finish_reason"), int(usage.get("total_tokens") or 0), time.time() - t0)


def norm(s):
    return re.sub(r"\s+", " ", (s or "")).strip().strip("`'\"").lower()


def run_one(task, arm, visible, base, key, wrong_label=False):
    """One (task, arm) cell, including the NEED_FULL second turn."""
    label = task["label"] if not wrong_label else task["_wrong_label"]
    nonce = "%s-%s-%s" % (task["id"], arm, "w" if wrong_label else "a")
    try:
        text, finish, tokens, secs = ask(base, key, visible, label, nonce)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
        return {"task": task["id"], "arm": arm, "error": "%s: %s" % (type(exc).__name__, exc)}
    asked_full = False
    if norm(text) == "need_full":
        asked_full = True
        try:
            text2, finish, more, secs2 = ask(base, key, task["output"], label, nonce + "-2")
            text, tokens, secs = text2, tokens + more, secs + secs2
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            return {"task": task["id"], "arm": arm, "asked_for_full": True,
                    "error": "%s: %s" % (type(exc).__name__, exc)}
    return {"task": task["id"], "arm": arm, "wrong_label": wrong_label,
            "source": task["source"], "tool": task["tool"], "shape": task["shape"],
            "family": task["family"], "visible_bytes": len(visible),
            "correct": norm(text) == norm(task["answer"]), "asked_for_full": asked_full,
            "tokens": tokens, "seconds": round(secs, 2), "finish": finish,
            "reply": text[:200], "expected": task["answer"][:200]}


# ---------------------------------------------------------------- the run

def done_cells():
    if not LEDGER.exists():
        return set()
    out = set()
    for line in LEDGER.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "error" not in d:
            out.add((d["task"], d["arm"], bool(d.get("wrong_label"))))
    return out


def dry_run(a):
    """Everything except the model: proves the task set and the arms before anything is sent."""
    tasks, corpus = build_tasks(a.tasks, a.seed, a.edge, a.max_chars)
    print("%d tasks  %s" % (len(tasks), corpus))
    if not tasks:
        return 1
    fam, shape, bad_edge, bad_unique = {}, {}, 0, 0
    bytes_by_arm = {k: 0 for k in ARMS}
    for t in tasks:
        fam[t["family"]] = fam.get(t["family"], 0) + 1
        shape[t["shape"]] = shape.get(t["shape"], 0) + 1
        edges = t["output"][:a.edge] + t["output"][-a.edge:]
        bad_edge += 1 if t["answer"] in edges else 0
        bad_unique += 0 if t["output"].count(t["answer"]) == 1 else 1
        v = views(t)
        for k in ARMS:
            bytes_by_arm[k] += len(v[k])
        if t is tasks[0]:
            print("\nexample task %s  tool=%s  shape=%s  family=%s" % (
                t["id"], t["tool"], t["shape"], t["family"]))
            print("  intent : %s" % t["intent"][:110])
            print("  label  : %s" % t["label"])
            print("  answer : %s" % t["answer"][:80])
            for k in ARMS:
                print("  %-17s %6d bytes | %s" % (k, len(v[k]), v[k][:70].replace(chr(10), " ")))
    print("\nfamilies: %s" % fam)
    print("shapes:   %s" % shape)
    print("bytes by arm: %s" % {k: bytes_by_arm[k] for k in ARMS})
    print("controls: answers inside the edges: %d (want 0); answers not unique: %d (want 0)"
          % (bad_edge, bad_unique))
    print("\nNOTHING WAS SENT. No model was called.")
    return 0 if (bad_edge == 0 and bad_unique == 0) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", type=int, default=200)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--seed", type=int, default=20261029)
    ap.add_argument("--edge", type=int, default=EDGE)
    ap.add_argument("--max-chars", type=int, default=MAX_CHARS)
    ap.add_argument("--pilot", action="store_true", help="12 tasks, to price the full run")
    ap.add_argument("--dry-run", action="store_true",
                    help="build the tasks and every arm's text, call no model, send nothing")
    a = ap.parse_args()
    if a.pilot:
        a.tasks = 12
    if a.dry_run:
        return dry_run(a)

    base, key = env("AGORA_API_BASE_URL"), env("AGORA_API_KEY")
    if not base or not key:
        print("no endpoint in server/.env")
        return 1

    tasks, corpus = build_tasks(a.tasks, a.seed, a.edge, a.max_chars)
    if not tasks:
        print("no gradable task built: %s" % corpus)
        return 1
    rng = random.Random(a.seed)
    for t in tasks:                                   # the wrong-label control's decoy
        t["_wrong_label"] = rng.choice([o["label"] for o in tasks if o["label"] != t["label"]] or ["none"])

    print("%d tasks (%s), %d workers, model %s" % (
        len(tasks), corpus, a.workers, MODEL), flush=True)

    already = done_cells()
    cells = []
    for t in tasks:
        v = views(t)
        for arm in ARMS:
            if (t["id"], arm, False) not in already:
                cells.append((t, arm, v[arm], False))
        if (t["id"], "full", True) not in already:
            cells.append((t, "full", v["full"], True))   # the wrong-label control, on the ceiling arm
    print("%d cells to run, %d already in the ledger" % (len(cells), len(already)), flush=True)

    t0 = time.time()
    counter = {"n": 0, "tokens": 0}

    def work(cell):
        task, arm, visible, wrong = cell
        row = run_one(task, arm, visible, base, key, wrong_label=wrong)
        with _print_lock:
            with LEDGER.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row) + "\n")
            counter["n"] += 1
            counter["tokens"] += int(row.get("tokens") or 0)
            if counter["n"] % 10 == 0 or counter["n"] == len(cells):
                print("  %d/%d cells, %d tokens, %.0fs" % (
                    counter["n"], len(cells), counter["tokens"], time.time() - t0), flush=True)
        return row

    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        list(ex.map(work, cells))

    report(tasks, corpus, a, time.time() - t0)
    return 0


def report(tasks, corpus, args, elapsed):
    rows = [json.loads(l) for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]
    ids = {t["id"] for t in tasks}
    rows = [r for r in rows if r.get("task") in ids and "error" not in r]
    errors = sum(1 for l in LEDGER.read_text(encoding="utf-8").splitlines()
                 if l.strip() and "error" in json.loads(l))

    def agg(sel):
        s = [r for r in rows if sel(r)]
        n = len(s)
        if not n:
            return None
        ok = sum(1 for r in s if r["correct"])
        tok = sum(r["tokens"] for r in s)
        return {"n": n, "correct": ok, "accuracy_pct": round(100.0 * ok / n, 1),
                "tokens": tok, "asked_for_full_pct": round(100.0 * sum(
                    1 for r in s if r.get("asked_for_full")) / n, 1),
                "solved_per_1k_tokens": round(1000.0 * ok / max(tok, 1), 3)}

    out = {
        "measured": time.strftime("%Y-%m-%d"),
        "model": MODEL, "edge": args.edge, "max_chars": args.max_chars, "seed": args.seed,
        "tasks": len(tasks), "elapsed_seconds": round(elapsed), "cells_with_errors": errors,
        "corpus": corpus,
        "by_arm": {a: agg(lambda r, a=a: r["arm"] == a and not r.get("wrong_label")) for a in ARMS},
        "by_family": {f: {a: agg(lambda r, a=a, f=f: r["arm"] == a and r["family"] == f
                                 and not r.get("wrong_label")) for a in ARMS}
                      for f in ("intent_aligned", "intent_independent")},
        "by_shape": {s: {a: agg(lambda r, a=a, s=s: r["arm"] == a and r["shape"] == s
                                and not r.get("wrong_label")) for a in ARMS}
                     for s in sorted({t["shape"] for t in tasks})},
        "controls": {
            "wrong_label_on_the_full_arm": agg(lambda r: bool(r.get("wrong_label"))),
            "no_output_must_be_near_zero": agg(lambda r: r["arm"] == "no_output"
                                               and not r.get("wrong_label")),
            "bytecount_only_must_be_near_zero": agg(lambda r: r["arm"] == "bytecount_only"
                                                    and not r.get("wrong_label")),
            "full_is_the_ceiling": agg(lambda r: r["arm"] == "full" and not r.get("wrong_label")),
        },
    }
    RESULT.write_text(json.dumps(out, indent=1), encoding="utf-8")

    print("\n%d tasks, model %s, edge %d, %.0fs, %d failed cells"
          % (len(tasks), MODEL, args.edge, elapsed, errors))
    print("  %-17s %5s %7s %9s %9s %s" % ("arm", "n", "correct", "askedfull", "tokens", "solved/1k"))
    for a in ARMS:
        r = out["by_arm"][a]
        if r:
            print("  %-17s %5d %6.1f%% %8.1f%% %9d %9.3f" % (
                a, r["n"], r["accuracy_pct"], r["asked_for_full_pct"], r["tokens"],
                r["solved_per_1k_tokens"]))
    print("\ncontrols (the first three must be near zero, the fourth high):")
    for k in ("wrong_label_on_the_full_arm", "no_output_must_be_near_zero",
              "bytecount_only_must_be_near_zero", "full_is_the_ceiling"):
        r = out["controls"][k]
        print("  %-36s %s" % (k, "n/a" if not r else "%.1f%% of %d" % (r["accuracy_pct"], r["n"])))
    print("\nresult: %s\nledger: %s" % (RESULT, LEDGER))


if __name__ == "__main__":
    raise SystemExit(main())
