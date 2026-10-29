"""Hermes's own tool-result prune, our context saver, and the two combined, on the owner's
real Hermes transcript.

The question: a Hermes context engine built on inspeximus is only worth writing if Hermes's
built-in prune leaves something on the table. Hermes already demotes old tool results with
per-tool summarizers, so "tool output is 84% of the bytes" does not by itself justify the
work.

Two axes, because bytes alone reward the most lossy strategy. A summarizer that returns
"(8,000 chars result)" wins on bytes and loses the content, which the agent then re-runs.

  bytes     - what survives in the request.
  needles   - distinctive terms from the original that survive in what the model still sees.
              A strategy that keeps a pointer to the full text scores the needle only if the
              needle is in the text the model reads, never because the file exists.
              COVERAGE, not relevance: rare terms are spread through the output, so head and
              tail truncation scores well on it while keeping nothing the agent asked for.
              Measured 2026-10-29: truncation at the same byte budget beat the ranked digest
              60.7% to 58.4%, which is the metric failing, not the ranking.
  answers   - the terms OF THE QUESTION that are present in the output and survive the cut.
              CIRCULAR on a shell result: the intent is the command and the head of the output
              echoes it, so head-and-tail truncation scores those terms for free. Measured
              2026-10-29: truncation 80.7%, ranked digest 76.7%, on that confound.
  buried    - the same question terms, counting only those that appear NOWHERE in the first or
              last 400 bytes. Only retrieval can rescue these, and this is the number the
              engine's design turns on.

Controls, in both directions:
  - the instrument must see its target: every row above the threshold must change under
    Hermes's summarizer, or the summarizer never ran.
  - a known-lossy strategy must score ~0 needles: if Hermes's generic fallback scores
    needles, the needle check is matching boilerplate rather than content.
  - the needle extractor must produce needles that are present in the original: a needle
    missing from its own source means the extractor, not the strategy, is being measured.

Read-only on a COPY of the owner's state.db. Single process, lexical ranking (no embeddings),
about 400 rows.
"""
from __future__ import annotations

import json
import os
import random
import re
import sqlite3
import sys
import time
from pathlib import Path

HERMES = Path(r"C:\Users\Danculus\AppData\Local\hermes\hermes-agent")
DB = Path(sys.argv[1]) if len(sys.argv) > 1 else None
THRESHOLD = 2000          # the smallest output either strategy touches
NEEDLES = 5               # distinctive terms sampled per row
RESULT = Path(__file__).with_suffix(".result.json")
HYBRID = os.environ.get("PROBE_HYBRID") == "1"   # ranks with the local embedder as well
EMBED_URL = "http://127.0.0.1:11434/api/embed"   # by address: the name costs 2.1 s per call
EMBED_MODEL = "nomic-embed-text"

sys.path.insert(0, str(HERMES))
from agent.context_compressor import _summarize_tool_result  # noqa: E402

from inspeximus.context_saver import _STOP, save  # noqa: E402
import inspeximus  # noqa: E402

_WORD = re.compile(r"[A-Za-z0-9_./-]{6,}")


def embed(text):
    """One vector from the local Ollama daemon. Addressed by IP: the hostname resolves to ::1
    first and fails over on every call, which measured 2.1 s against 0.08 s."""
    import urllib.request
    body = json.dumps({"model": EMBED_MODEL, "input": text}).encode()
    req = urllib.request.Request(EMBED_URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["embeddings"][0]


def needles(text: str, rng: random.Random) -> list[str]:
    """Distinctive terms: the rarest long tokens, so boilerplate cannot satisfy them."""
    counts: dict[str, int] = {}
    for w in _WORD.findall(text):
        counts[w] = counts.get(w, 0) + 1
    rare = sorted((n, w) for w, n in counts.items() if n <= 2)
    rng.shuffle(rare)
    return [w for _, w in rare[:NEEDLES]]


def survived(ns: list[str], visible: str) -> int:
    return sum(1 for n in ns if n in visible)


def call_intent(args: str) -> str:
    """The intent the shipped hook ranks against: the call's description, else its command.

    Hermes stores the whole assistant tool_calls array on the tool row, so the fields are read
    out of it rather than off a flat dict. Other tools name their subject differently; the
    fallback order is the one a reader of the call would use.
    """
    try:
        calls = json.loads(args) if args else []
    except (json.JSONDecodeError, TypeError):
        return ""
    if isinstance(calls, dict):
        calls = [calls]
    for call in calls if isinstance(calls, list) else []:
        fn = (call or {}).get("function") or {}
        try:
            a = json.loads(fn.get("arguments") or "{}")
        except (json.JSONDecodeError, TypeError):
            a = {}
        if not isinstance(a, dict):
            continue
        for key in ("description", "command", "query", "path", "file_path", "pattern", "code"):
            v = a.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()[:300]
    return ""


EDGE = 400


def answer_terms(intent: str, content: str) -> list[str]:
    """Terms of the question that the output actually contains: what the agent came for."""
    want = {w for w in _WORD.findall(intent) if w.lower() not in _STOP}
    return sorted(w for w in want if w in content)


def buried_terms(ans: list[str], content: str) -> list[str]:
    """Question terms that live only in the middle, past what truncation keeps for free."""
    edges = content[:EDGE] + content[-EDGE:]
    return [w for w in ans if w not in edges]


def main() -> int:
    rng = random.Random(20261029)
    con = sqlite3.connect("file:%s?mode=ro" % DB.as_posix(), uri=True)
    rows = con.execute(
        # The call lives on the ASSISTANT row; the tool row carries only its id. Reading
        # tool_calls off the tool row returns '' for every row, which silently emptied the
        # intent on the first run of this probe.
        "select t.id, t.session_id, coalesce(t.tool_name,'?'), t.content, "
        "coalesce((select a.tool_calls from messages a where a.session_id = t.session_id "
        "          and a.role='assistant' and a.tool_calls like '%'||t.tool_call_id||'%' "
        "          limit 1), '') "
        "from messages t where t.role='tool' and length(t.content) > ? order by t.id",
        (THRESHOLD,)).fetchall()

    agg = {k: {"bytes": 0, "needles": 0, "answers": 0, "buried": 0} for k in
           ("baseline", "hermes", "saver", "combined", "truncate_same_bytes", "spared",
            "head_tail_plus_digest", "echo_head_plus_digest")
           + (("saver_hybrid",) if HYBRID else ())}
    needles_total = answers_total = buried_total = 0
    rows_with_answer_terms = rows_without_call_intent = rows_hybrid_reordered = 0
    unchanged_by_hermes = []
    needles_missing_from_source = 0
    fallback_rows = fallback_needles = 0
    per_tool: dict[str, dict] = {}
    t0 = time.time()

    for i, (rid, sid, tool, content, args) in enumerate(rows, 1):
        if i % 25 == 0 or i == len(rows):
            print("  %d/%d rows, %.1fs" % (i, len(rows), time.time() - t0), flush=True)
        ns = needles(content, rng)
        needles_missing_from_source += sum(1 for n in ns if n not in content)
        needles_total += len(ns)

        herm = _summarize_tool_result(tool, args, content)
        if herm == content:
            unchanged_by_hermes.append(tool)
        intent = call_intent(args)
        if not intent:
            rows_without_call_intent += 1
            row = con.execute(
                "select content from messages where session_id=? and role='user' and id<? "
                "order by id desc limit 1", (sid, rid)).fetchone()
            intent = (row[0] if row else "")[:300]
        ans = answer_terms(intent, content)
        answers_total += len(ans)
        rows_with_answer_terms += 1 if ans else 0
        bur = buried_terms(ans, content)
        buried_total += len(bur)
        lex = save(content, intent, without_reranker="hybrid", ranking="lexical")
        dig = lex["text"]
        # Combined: the saver replaces the payload at capture time, so Hermes's later prune
        # acts on the digest, not on the raw output.
        comb = _summarize_tool_result(tool, args, dig)
        # The engine we are about to write: the saver digests at capture time AND the result is
        # marked reclaimed, so Hermes's later pass spares it instead of demoting it again.
        spared = dig
        if HYBRID:
            # CONTROL for the hybrid arm: an embedder that never ran, or one whose vectors say
            # nothing, leaves the order identical to the lexical one and the arm then measures
            # lexical twice under a second name.
            h = save(content, intent, embed=embed, embed_query=embed,
                     without_reranker="hybrid", ranking="hybrid")
            hyb = h["text"]
            # Only a digest is ranked at all: passthrough and pointer modes report no ranking.
            if h["mode"] == "digest" and h.get("ranking") != "hybrid":
                raise SystemExit("CONTROL: a digest row fell back to ranking %r" % h.get("ranking"))
            rows_hybrid_reordered += 1 if h.get("order") != lex.get("order") else 0
        # Does ranking earn its keep, or is any cut of the same size as good? Head and tail,
        # which is what a truncating prune would keep.
        budget = len(dig)
        trunc = content if len(content) <= budget else (
            content[: budget // 2] + chr(10) + "..." + chr(10) + content[-(budget - budget // 2):])
        # The composite: a quarter of the budget to the head, a quarter to the tail, half to the
        # ranked digest. Truncation wins on term survival because the head of a tool result
        # carries the command echo and the first rows; ranking wins on what is buried.
        # The echo variant: spend EDGE bytes on the head, which is where a shell result repeats
        # the command, 200 on the tail, which is where the exit status sits, and the rest on the
        # ranked digest. Same total budget.
        if len(content) <= budget:
            echo = content
        else:
            head, tail = min(EDGE, budget // 3), min(200, budget // 6)
            echo = (content[:head] + chr(10) + "..." + chr(10)
                    + dig[: budget - head - tail] + chr(10) + "..." + chr(10) + content[-tail:])
        if len(content) <= budget:
            composite = content
        else:
            head, tail = budget // 4, budget // 4
            composite = (content[:head] + chr(10) + "..." + chr(10)
                         + dig[: budget - head - tail] + chr(10) + "..." + chr(10)
                         + content[-tail:])

        for key, visible in (("baseline", content), ("hermes", herm), ("saver", dig),
                             ("combined", comb), ("truncate_same_bytes", trunc), ("spared", spared),
                             ("head_tail_plus_digest", composite), ("echo_head_plus_digest", echo)) + (
                                 (("saver_hybrid", hyb),) if HYBRID else ()):
            agg[key]["bytes"] += len(visible)
            agg[key]["needles"] += survived(ns, visible)
            agg[key]["answers"] += survived(ans, visible)
            agg[key]["buried"] += survived(bur, visible)

        if herm.endswith("chars result)"):           # Hermes's generic, content-free fallback
            fallback_rows += 1
            fallback_needles += survived(ns, herm)

        t = per_tool.setdefault(tool, {"rows": 0, "baseline": 0, "hermes": 0, "saver": 0})
        t["rows"] += 1
        t["baseline"] += len(content)
        t["hermes"] += len(herm)
        t["saver"] += len(dig)

    out = {
        "measured": "2026-10-29",
        "inspeximus": inspeximus.__version__,
        "store": str(DB),
        "hybrid_arm": HYBRID,
        "ranking": "lexical (no embedder, the saver hook's own default)",
        "intent": "the tool call's own description or command, the precedence the shipped "
                  "PostToolUse hook uses (context_saver.post_tool_use_replacement)",
        "rows_over_%d_chars" % THRESHOLD: len(rows),
        "needles_sampled": needles_total,
        "answer_terms_sampled": answers_total,
        "buried_answer_terms_sampled": buried_total,
        "rows_whose_question_shares_a_term_with_the_output": rows_with_answer_terms,
        "strategies": {
            k: {
                "bytes": v["bytes"],
                "kept_pct_of_baseline": round(100.0 * v["bytes"] / agg["baseline"]["bytes"], 1),
                "needles_kept": v["needles"],
                "needles_kept_pct": round(100.0 * v["needles"] / needles_total, 1),
                "answer_terms_kept": v["answers"],
                "answer_terms_kept_pct": round(100.0 * v["answers"] / max(answers_total, 1), 1),
                "buried_terms_kept": v["buried"],
                "buried_terms_kept_pct": round(100.0 * v["buried"] / max(buried_total, 1), 1),
            } for k, v in agg.items()},
        "controls": {
            "rows_hermes_left_unchanged": len(unchanged_by_hermes),
            "needles_missing_from_their_own_source": needles_missing_from_source,
            "hermes_generic_fallback_rows": fallback_rows,
            "needles_kept_by_the_content_free_fallback": fallback_needles,
            "rows_with_no_answer_term": len(rows) - rows_with_answer_terms,
            "rows_whose_call_carried_no_intent": rows_without_call_intent,
            "rows_the_embedder_reordered": rows_hybrid_reordered if HYBRID else None,
        },
        "per_tool": {k: v for k, v in sorted(per_tool.items(), key=lambda kv: -kv[1]["baseline"])[:12]},
    }
    RESULT.write_text(json.dumps(out, indent=1), encoding="utf-8")

    s = out["strategies"]
    print("\nbytes kept, of %.2f MB baseline:" % (agg["baseline"]["bytes"] / 1e6))
    for k in ("hermes", "saver", "combined", "spared", "truncate_same_bytes",
              "head_tail_plus_digest", "echo_head_plus_digest") + (
                  ("saver_hybrid",) if HYBRID else ()):
        print("  %-20s %6.1f%% bytes, %5.1f%% needles, %5.1f%% answer terms, %5.1f%% BURIED" % (
            k, s[k]["kept_pct_of_baseline"], s[k]["needles_kept_pct"],
            s[k]["answer_terms_kept_pct"], s[k]["buried_terms_kept_pct"]))
    c = out["controls"]
    print("\ncontrols: %d rows unchanged by Hermes (want 0), %d needles absent from their source "
          "(want 0), fallback kept %d needles over %d rows (want ~0)" % (
              c["rows_hermes_left_unchanged"], c["needles_missing_from_their_own_source"],
              c["needles_kept_by_the_content_free_fallback"], c["hermes_generic_fallback_rows"]))
    print("result: %s" % RESULT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
