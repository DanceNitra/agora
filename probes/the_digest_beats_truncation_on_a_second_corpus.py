"""Does the digest's win over truncation reproduce on a SECOND corpus?

The Hermes probe measured one transcript: 264 tool results, 226 buried question terms, and a
win of 61.5% against 54.9%, which is about 15 terms. That is thin for a README claim, and it was
measured on the machine's own Hermes sessions. This re-runs the same metric on Claude Code
transcripts, a different harness, different tools, different output shapes.

Same metric, imported from the first probe rather than rewritten, because a second
implementation of a metric is a second thing that can be wrong:

  buried question terms - terms of the call's own arguments that appear in the output but NOWHERE
                          in its first or last 400 bytes. Head-and-tail truncation keeps those
                          edges for free, so only retrieval can rescue what is between them.

Controls:
  - every needle must be present in its own source, or the extractor is being measured.
  - the arms must differ: identical numbers mean one arm never ran.
  - results whose call carried no arguments are counted and reported, because the intent is what
    the digest ranks against. They keep the engine's own fallback, the tool's name, rather than
    dropping out of the sample: the saver refuses a large output with no intent, and excluding
    those results would bias the sample toward well-described calls.
"""
from __future__ import annotations

import importlib.util
import json
import os
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECTS = Path(os.path.expanduser("~")) / ".claude" / "projects"
MIN_CHARS = 2000
MAX_RESULTS = int(os.environ.get("PROBE_MAX_RESULTS", "400"))
RESULT = Path(__file__).with_suffix(".result.json")

_spec = importlib.util.spec_from_file_location(
    "hermes_probe", HERE / "hermes_prune_vs_our_saver_on_his_transcript.py")
_first = importlib.util.module_from_spec(_spec)
sys.argv = [sys.argv[0]]                              # the first probe reads argv at import time
_spec.loader.exec_module(_first)

from inspeximus.context_saver import save              # noqa: E402

INTENT_KEYS = ("description", "command", "query", "path", "file_path", "pattern", "prompt")


def tool_results(path: Path):
    """(intent, output) for every tool result in one Claude Code transcript."""
    calls: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return
    for line in lines:
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        msg = ev.get("message") or {}
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "tool_use":
                args = item.get("input") or {}
                intent = ""
                if isinstance(args, dict):
                    for key in INTENT_KEYS:
                        value = args.get(key)
                        if isinstance(value, str) and value.strip():
                            intent = value.strip()[:300]
                            break
                # The engine's own fallback: the tool's name. The saver refuses an output of
                # this size with no intent at all, so a result whose call names nothing would
                # otherwise drop out of the sample and bias it toward well-described calls.
                calls[str(item.get("id"))] = intent or str(item.get("name") or "tool output")
            elif item.get("type") == "tool_result":
                body = item.get("content")
                if isinstance(body, list):              # [{"type": "text", "text": ...}, ...]
                    body = "\n".join(p.get("text", "") for p in body
                                     if isinstance(p, dict) and p.get("type") == "text")
                if isinstance(body, str) and len(body) >= MIN_CHARS:
                    yield calls.get(str(item.get("tool_use_id")), ""), body


def main() -> int:
    rng = random.Random(20261029)
    files = sorted(PROJECTS.glob("*/*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        print("no Claude Code transcripts under %s" % PROJECTS)
        return 1

    arms = {k: {"bytes": 0, "buried": 0} for k in ("baseline", "digest", "truncate_same_bytes")}
    buried_total = rows = no_intent = missing_needle = 0
    t0 = time.time()

    for path in files:
        if rows >= MAX_RESULTS:
            break
        for intent, output in tool_results(path):
            if rows >= MAX_RESULTS:
                break
            rows += 1
            if rows % 25 == 0:
                print("  %d/%d results, %.1fs" % (rows, MAX_RESULTS, time.time() - t0), flush=True)
            if intent in ("", "tool output"):
                no_intent += 1
            ans = _first.answer_terms(intent, output)
            bur = _first.buried_terms(ans, output)
            missing_needle += sum(1 for w in bur if w not in output)
            buried_total += len(bur)

            dig = save(output, intent, without_reranker="hybrid", ranking="lexical")["text"]
            budget = len(dig)
            trunc = output if len(output) <= budget else (
                output[: budget // 2] + "\n...\n" + output[-(budget - budget // 2):])
            for key, visible in (("baseline", output), ("digest", dig),
                                 ("truncate_same_bytes", trunc)):
                arms[key]["bytes"] += len(visible)
                arms[key]["buried"] += _first.survived(bur, visible)

    out = {
        "measured": "2026-10-29",
        "corpus": "Claude Code transcripts under %s" % PROJECTS,
        "transcripts_available": len(files),
        "results_over_%d_chars" % MIN_CHARS: rows,
        "buried_terms_sampled": buried_total,
        "arms": {k: {
            "bytes": v["bytes"],
            "kept_pct_of_baseline": round(100.0 * v["bytes"] / max(arms["baseline"]["bytes"], 1), 1),
            "buried_terms_kept": v["buried"],
            "buried_terms_kept_pct": round(100.0 * v["buried"] / max(buried_total, 1), 1),
        } for k, v in arms.items()},
        "controls": {
            "results_whose_call_carried_no_intent": no_intent,
            "needles_missing_from_their_own_source": missing_needle,
            "the_two_arms_differ": arms["digest"]["buried"] != arms["truncate_same_bytes"]["buried"],
        },
        "hermes_corpus_for_comparison": {"digest": 61.5, "truncate_same_bytes": 54.9,
                                         "buried_terms_sampled": 226},
    }
    RESULT.write_text(json.dumps(out, indent=1), encoding="utf-8")

    print("\n%d results, %d buried terms" % (rows, buried_total))
    for k in ("digest", "truncate_same_bytes"):
        a = out["arms"][k]
        print("  %-20s %5.1f%% bytes, %5.1f%% buried terms" % (
            k, a["kept_pct_of_baseline"], a["buried_terms_kept_pct"]))
    print("controls: %d of %d results had no intent, %d needles absent from their source, "
          "arms differ: %s" % (no_intent, rows, missing_needle, out["controls"]["the_two_arms_differ"]))
    print("result: %s" % RESULT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
