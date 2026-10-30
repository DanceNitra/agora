"""Does Claude Code's own compaction summary already carry what a PreCompact snapshot would add?

Question (plan P1, agora_output/strategy/inspeximus_plans/reverse_context-mode_2026-10-19.md, step 5.1):
for every real compaction in our transcripts, take the facts a context-mode style snapshot restores
and check whether the summary Claude Code wrote at that boundary already contains them.

Ground truth per compaction, from the transcript segment between the previous boundary and this one:
  last_prompt  : the last real user prompt before the boundary
  files_last10 : the last 10 distinct files written by Edit/Write/MultiEdit/NotebookEdit
  open_errors  : failing tool results among the last 30 tool results, with no success of the same
                 tool afterwards in the segment
  corrections  : user prompts that read as a correction or a standing rule

Matching is lexical and deterministic. Two controls guard it:
  positive : the ground truth appended to the summary must score 1.0 on every axis
  negative : the same ground truth matched against ANOTHER session's summary must score low;
             a high negative score means the matcher credits generic words, not content

Run: python -X utf8 probes/compact_summary_vs_ground_truth.py
Writes probes/compact_summary_vs_ground_truth.result.json. No model call, no network.
"""
import glob
import json
import os
import re
import sys
import time
import unicodedata

ROOT = os.path.expanduser("~/.claude/projects")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "compact_summary_vs_ground_truth.result.json")
WRITE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
CORRECTION = re.compile(
    r"\b(nie\s+\w+\s*,?\s*ale|nerob|nikdy|vzdy|vždy|odteraz|zakazujem|prestan|nepouzivaj|"
    r"don'?t|never|always|instead|stop\s+\w+ing|from now on)\b", re.I)
STOP = set("""that this with from have will your what when then than they them were been into also only
just more some such each which there their about would could should other these those very here
mas mame toto tento tato tieto este aj ale ako alebo lebo preto potom teraz treba moze mozem bude
budeme som sme ste nie ano len uz tak tam tu ked kde ktory ktora ktore pre pri pod nad bez cez""".split())


def norm(s):
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def tokens(s):
    return {t for t in re.findall(r"[a-z0-9_][a-z0-9_.\-/]{3,}", norm(s)) if t not in STOP}


def coverage(item_tokens, summary_tokens):
    if not item_tokens:
        return None
    return len(item_tokens & summary_tokens) / len(item_tokens)


def text_of(content):
    if isinstance(content, str):
        return content
    out = []
    for x in content or []:
        if isinstance(x, dict) and x.get("type") == "text":
            out.append(x.get("text", ""))
    return "\n".join(out)


def is_real_prompt(r):
    if r.get("type") != "user" or r.get("isMeta") or r.get("isSidechain") or r.get("isCompactSummary"):
        return False
    c = r.get("message", {}).get("content")
    if isinstance(c, list) and any(isinstance(x, dict) and x.get("type") == "tool_result" for x in c):
        return False
    t = re.sub(r"<system-reminder>.*?</system-reminder>", "", text_of(c), flags=re.S)
    # A paste is someone else's text (a handoff, a log); the owner's own words are what a snapshot
    # must keep. Without this cut a 3,000-word handoff counted as one "correction" no summary can hold.
    t = re.sub(r"<pasted_content[^>]*>.*?</pasted_content>", "", t, flags=re.S).strip()
    if not t or t.startswith(("<command-", "<local-command", "[Request interrupted", "<task-notification",
                              "<side-sessions-event", "<ci-monitor-event", "Caveat:")):
        return False
    return t


def segments(path):
    """Yield (summary_text, segment_rows, meta) for each compaction in one transcript."""
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    pass
    start = 0
    for i, r in enumerate(rows):
        if r.get("isCompactSummary"):
            b = i
            while b > start and rows[b].get("subtype") != "compact_boundary":
                b -= 1
            meta = rows[b].get("compactMetadata") or {} if rows[b].get("subtype") == "compact_boundary" else {}
            yield text_of(r["message"]["content"]), rows[start:b], meta, r.get("version")
            start = i + 1


def ground_truth(seg):
    prompts, writes, results, uses = [], [], [], {}
    for r in seg:
        if r.get("isSidechain"):
            continue
        p = is_real_prompt(r)
        if p:
            prompts.append(p)
        c = r.get("message", {}).get("content")
        if not isinstance(c, list):
            continue
        for x in c:
            if not isinstance(x, dict):
                continue
            if x.get("type") == "tool_use":
                uses[x.get("id")] = (x.get("name"), x.get("input") or {})
                if x.get("name") in WRITE_TOOLS:
                    fp = (x.get("input") or {}).get("file_path") or (x.get("input") or {}).get("notebook_path")
                    if fp:
                        writes.append(fp.replace("\\", "/"))
            elif x.get("type") == "tool_result":
                name, inp = uses.get(x.get("tool_use_id"), (None, {}))
                results.append((name, inp, bool(x.get("is_error")), text_of(x.get("content"))))
    files = []
    for fp in reversed(writes):
        if fp not in files:
            files.append(fp)
    files = files[:10]
    tail = results[-30:]
    open_errors = []
    for k, (name, inp, err, body) in enumerate(tail):
        if err and not any(n == name and not e for n, _, e, _ in tail[k + 1:]):
            what = inp.get("command") or inp.get("file_path") or inp.get("pattern") or json.dumps(inp)[:200]
            open_errors.append({"tool": name, "what": str(what)[:300], "error": body.strip().split("\n")[0][:200]})
    corrections = [p for p in prompts if len(p) <= 500 and CORRECTION.search(norm(p))][-5:]
    return {"last_prompt": prompts[-1] if prompts else None, "files_last10": files,
            "open_errors": open_errors, "corrections": corrections}


def score(gt, summary):
    st = tokens(summary)
    sn = norm(summary)
    out = {}
    lp = gt["last_prompt"]
    out["last_prompt"] = coverage(tokens(lp), st) if lp else None
    if gt["files_last10"]:
        hits = [os.path.basename(f).lower() in sn for f in gt["files_last10"]]
        out["files_last10"] = sum(hits) / len(hits)
    else:
        out["files_last10"] = None
    errs = [coverage(tokens(e["what"]) | tokens(e["error"]), st) for e in gt["open_errors"]]
    errs = [e for e in errs if e is not None]
    out["open_errors"] = sum(1 for e in errs if e >= 0.5) / len(errs) if errs else None
    cors = [coverage(tokens(c), st) for c in gt["corrections"]]
    cors = [c for c in cors if c is not None]
    out["corrections"] = sum(1 for c in cors if c >= 0.5) / len(cors) if cors else None
    return out


def gt_as_text(gt):
    parts = [gt["last_prompt"] or ""] + gt["files_last10"] + gt["corrections"]
    parts += [e["what"] + " " + e["error"] for e in gt["open_errors"]]
    return "\n".join(parts)


def mean(xs):
    xs = [x for x in xs if x is not None]
    return (round(sum(xs) / len(xs), 3), len(xs)) if xs else (None, 0)


def main():
    t0 = time.time()
    files = sorted(glob.glob(os.path.join(ROOT, "*", "*.jsonl")))
    cases = []
    for n, path in enumerate(files, 1):
        try:
            with open(path, encoding="utf-8") as fh:
                if '"isCompactSummary":true' not in fh.read():
                    continue
        except OSError:
            continue
        for summary, seg, meta, ver in segments(path):
            gt = ground_truth(seg)
            cases.append({"file": os.path.relpath(path, ROOT), "version": ver, "summary_chars": len(summary),
                          "trigger": meta.get("trigger"), "summary": summary, "gt": gt})
        print(f"[{n}/{len(files)}] {len(cases)} compactions, {time.time() - t0:.1f}s", file=sys.stderr, flush=True)

    axes = ["last_prompt", "files_last10", "open_errors", "corrections"]
    for i, c in enumerate(cases):
        c["score"] = score(c["gt"], c["summary"])
        c["positive"] = score(c["gt"], c["summary"] + "\n" + gt_as_text(c["gt"]))
        other = next((o for o in cases[i + 1:] + cases[:i] if o["file"] != c["file"]), None)
        c["negative"] = score(c["gt"], other["summary"]) if other else {a: None for a in axes}

    agg = {}
    for a in axes:
        agg[a] = {"real": mean([c["score"][a] for c in cases]),
                  "positive_control": mean([c["positive"][a] for c in cases]),
                  "negative_control": mean([c["negative"][a] for c in cases])}
    lp_low = sorted((c for c in cases if c["score"]["last_prompt"] is not None),
                    key=lambda c: c["score"]["last_prompt"])[:8]
    files_missed = []
    for c in cases:
        sn = norm(c["summary"])
        files_missed += [f for f in c["gt"]["files_last10"] if os.path.basename(f).lower() not in sn]
    result = {
        "measured": time.strftime("%Y-%m-%d %H:%M"),
        "compactions": len(cases),
        "transcripts": len({c["file"] for c in cases}),
        "summary_chars_median": sorted(c["summary_chars"] for c in cases)[len(cases) // 2] if cases else None,
        "summary_has_transcript_pointer": sum("read the full transcript at" in c["summary"] for c in cases),
        "aggregate_mean_and_n": agg,
        "lowest_last_prompt": [{"file": c["file"], "cov": round(c["score"]["last_prompt"], 2),
                                "prompt": c["gt"]["last_prompt"][:300]} for c in lp_low],
        "files_missed_sample": files_missed[:25],
        "files_missed_total": len(files_missed),
        "open_errors_missed_sample": [
            {"file": c["file"], **e} for c in cases for e in c["gt"]["open_errors"]
            if (coverage(tokens(e["what"]) | tokens(e["error"]), tokens(c["summary"])) or 0) < 0.5][:15],
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: result[k] for k in ("compactions", "transcripts", "summary_chars_median",
                                             "summary_has_transcript_pointer", "aggregate_mean_and_n",
                                             "files_missed_total")}, indent=1))


if __name__ == "__main__":
    main()
