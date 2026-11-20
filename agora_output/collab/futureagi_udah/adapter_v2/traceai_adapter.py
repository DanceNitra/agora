"""traceAI -> V10 U/D/A/H adapter. Reads a traceAI export and scores each turn once with trajectory_v3_ultra.py.

This file only converts. All scoring is done by `trajectory_v3_ultra.py`, imported and called
unchanged: each new turn becomes an engine `Turn`, the session becomes an engine `Case`, and
the engine's own `iter_case_rows` produces the score of each turn.

Input (`load_spans`):
- OTLP JSON as a collector or file exporter writes it (`resourceSpans` / `scopeSpans` / `spans`,
  attributes as `{"key", "value"}` lists), a JSON list of spans, or JSONL.
- `gen_ai.input.messages` / `gen_ai.output.messages` as a JSON array, as a JSON string, or as
  flattened keys (`gen_ai.input.messages.0.message.content`); the older `llm.input_messages` /
  `llm.output_messages` names too. Content can be a string or a list of parts.
- `session.id`, then `gen_ai.conversation.id`, then the trace id, groups spans into a session.
- `gen_ai.usage.*` is copied from the span; nothing is estimated.

Each turn is counted once. A chat request resends the whole history, so for each session the
spans are ordered by start time and the transcript already seen is kept. The new user messages
of a span are those after the part of its input that matches the transcript; the turn is those
messages plus the span's output. A span is skipped only when its OUTPUT repeats an output that
was already scored. A span with a new reply and no new user message (an assistant answering twice
in a row, a tool step, a retry with a different answer) is a new turn and is scored.

Output (`--out`, CSV, one row per scored turn): session.id, turn_index, span_id,
gen_ai.input.messages (the new user messages only), gen_ai.output.messages,
gen_ai.usage.input_tokens, gen_ai.usage.output_tokens, gen_ai.usage.total_tokens, U, D, A, H.
Definitions are V10 as implemented in trajectory_v3_ultra.py: U = Unity, D = Development,
A = Adversarial, H = 0.4U + 0.4D - 0.2A. Diagnostics only: no advice or generated text.

Python 3.9 or later, standard library only. Usage:
    python traceai_adapter.py trace.json --out turn_scores.csv
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from typing import Any, Dict, Iterable, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trajectory_v3_ultra as engine  # noqa: E402  (the scoring core, used unchanged)

INPUT_KEYS = ("gen_ai.input.messages", "llm.input_messages")
OUTPUT_KEYS = ("gen_ai.output.messages", "llm.output_messages")
SESSION_KEYS = ("session.id", "gen_ai.conversation.id")
COLUMNS = ["session.id", "turn_index", "span_id", "gen_ai.input.messages", "gen_ai.output.messages",
           "gen_ai.usage.input_tokens", "gen_ai.usage.output_tokens", "gen_ai.usage.total_tokens",
           "U", "D", "A", "H"]


# ---------------------------------------------------------------- reading spans

def _otlp_value(v: Dict[str, Any]) -> Any:
    if "stringValue" in v:
        return v["stringValue"]
    if "intValue" in v:
        return int(v["intValue"])
    if "doubleValue" in v:
        return float(v["doubleValue"])
    if "boolValue" in v:
        return bool(v["boolValue"])
    if "arrayValue" in v:
        return [_otlp_value(x) for x in v["arrayValue"].get("values", [])]
    if "kvlistValue" in v:
        return {kv["key"]: _otlp_value(kv["value"]) for kv in v["kvlistValue"].get("values", [])}
    return None


def _attrs(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, list):
        return {a["key"]: _otlp_value(a.get("value", {})) for a in raw if isinstance(a, dict) and "key" in a}
    return {}


def _walk(doc: Any, resource: Optional[Dict[str, Any]] = None) -> Iterable[Tuple[Dict[str, Any], Dict[str, Any]]]:
    if isinstance(doc, list):
        for item in doc:
            yield from _walk(item, resource)
    elif isinstance(doc, dict):
        if "resourceSpans" in doc:
            for rs in doc["resourceSpans"]:
                res = _attrs((rs.get("resource") or {}).get("attributes"))
                for ss in rs.get("scopeSpans", rs.get("instrumentationLibrarySpans", [])):
                    for span in ss.get("spans", []):
                        yield span, res
        elif "attributes" in doc:
            yield doc, resource or {}


def load_spans(text: str) -> List[Dict[str, Any]]:
    """Parse OTLP JSON, a JSON list of spans, or JSONL into flat span records."""
    text = text.strip()
    if not text:
        return []
    try:
        docs = [json.loads(text)]
    except json.JSONDecodeError:
        docs = [json.loads(line) for line in text.splitlines() if line.strip()]
    spans = []
    for doc in docs:
        for raw, res in _walk(doc):
            ctx = raw.get("context") or {}
            try:
                start = int(raw.get("startTimeUnixNano", raw.get("start_time", 0)))
            except (TypeError, ValueError):
                start = 0
            spans.append({"span_id": str(raw.get("spanId") or raw.get("span_id") or ctx.get("span_id") or ""),
                          "trace_id": str(raw.get("traceId") or raw.get("trace_id") or ctx.get("trace_id") or ""),
                          "start": start, "attributes": _attrs(raw.get("attributes")), "resource": res})
    return spans


# ---------------------------------------------------------------- messages

def _content(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        out = []
        for part in value:
            if isinstance(part, dict):
                out.append(str(part.get("content", part.get("text", ""))))
            else:
                out.append(str(part))
        return "\n".join(p for p in out if p)
    return json.dumps(value, ensure_ascii=False)


def _message(raw: Any) -> Optional[Dict[str, str]]:
    if not isinstance(raw, dict):
        return None
    if isinstance(raw.get("message"), dict):
        raw = raw["message"]
    role = str(raw.get("role") or raw.get("message.role") or "")
    content = raw.get("content", raw.get("parts", raw.get("message.content")))
    return {"role": role, "content": _content(content)}


def read_messages(attrs: Dict[str, Any], keys: Tuple[str, ...]) -> List[Dict[str, str]]:
    for key in keys:
        value = attrs.get(key)
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                value = [{"role": "", "content": value}]
        if isinstance(value, dict) and "messages" in value:
            value = value["messages"]
        if isinstance(value, list) and value:
            return [m for m in map(_message, value) if m is not None]
        pat = re.compile(re.escape(key) + r"\.(\d+)\.(.+)$")
        items: Dict[int, Dict[str, Any]] = {}
        for k, v in attrs.items():
            m = pat.match(k)
            if m:
                items.setdefault(int(m.group(1)), {})[m.group(2)] = v
        if items:
            return [m for m in map(_message, [items[i] for i in sorted(items)]) if m is not None]
    return []


def _fp(message: Dict[str, str]) -> str:
    raw = json.dumps([message["role"], message["content"].strip()], ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _known_prefix(seen: List[str], incoming: List[str]) -> int:
    """How many leading `incoming` messages are already in the transcript `seen`."""
    if incoming[:len(seen)] == seen:
        return len(seen)
    for start in range(1, len(seen)):           # history truncated by the client
        tail = seen[start:]
        if incoming[:len(tail)] == tail:
            return len(tail)
    known, k = set(seen), 0                      # history rewritten: skip known messages
    while k < len(incoming) and incoming[k] in known:
        k += 1
    return k


# ---------------------------------------------------------------- turns

def build_sessions(spans: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Each session's new turns, history removed and each output scored once."""
    chat = []
    for s in spans:
        inp = [m for m in read_messages(s["attributes"], INPUT_KEYS) if m["role"] != "system"]
        out = [m for m in read_messages(s["attributes"], OUTPUT_KEYS) if m["content"].strip()]
        if out:
            chat.append((s, inp, out))
    chat.sort(key=lambda t: t[0]["start"])
    sessions: Dict[str, List[Dict[str, Any]]] = {}
    transcripts: Dict[str, List[str]] = {}
    scored_outputs: Dict[str, set] = {}
    for span, inp, out in chat:
        sid = next((str(span["attributes"][k]) for k in SESSION_KEYS if span["attributes"].get(k)), None) \
            or next((str(span["resource"][k]) for k in SESSION_KEYS if span["resource"].get(k)), None) \
            or "trace:" + span["trace_id"]
        seen = transcripts.setdefault(sid, [])
        done = scored_outputs.setdefault(sid, set())
        out_key = "\n".join(_fp(m) for m in out)
        if out_key in done:                      # the same reply exported again: count it zero times
            continue
        fps = [_fp(m) for m in inp]
        new = inp[_known_prefix(seen, fps):]
        users = [m for m in new if m["role"] in ("user", "human", "")]
        usage = {k[len("gen_ai.usage."):]: v for k, v in span["attributes"].items() if k.startswith("gen_ai.usage.")}
        sessions.setdefault(sid, []).append({"span_id": span["span_id"], "users": users, "outputs": out, "usage": usage})
        done.add(out_key)
        seen.extend(_fp(m) for m in new)
        seen.extend(_fp(m) for m in out)
    return sessions


def score_sessions(sessions: Dict[str, List[Dict[str, Any]]], top_terms: int = engine.DEFAULT_TOP_TERMS,
                   char_step: int = engine.DEFAULT_CHAR_STEP) -> List[Dict[str, Any]]:
    """Hand every session to the engine as one Case and keep the engine's per-turn rows."""
    rows = []
    for sid, turns in sessions.items():
        case = engine.Case(case_id=sid, name=sid, group="", raw_id=sid, source_path="traceai")
        case.turns = [engine.Turn(index=0, user="\n".join(m["content"] for m in t["users"]).strip(),
                                  assistant="\n".join(m["content"] for m in t["outputs"]).strip()) for t in turns]
        engine.finalize_case(case)
        scored = [r for kind, r in engine.iter_case_rows(case, char_step=char_step, top_terms=top_terms) if kind == "turn"]
        # The engine skips a turn only when its (user, assistant) pair repeats an earlier one in the case;
        # outputs are already unique here, so there is one engine row per turn, in order.
        for i, (t, r) in enumerate(zip(turns, scored), 1):
            u = t["usage"]
            total = u.get("total_tokens")
            if total is None and "input_tokens" in u and "output_tokens" in u:
                total = int(u["input_tokens"]) + int(u["output_tokens"])
            rows.append({"session.id": sid, "turn_index": i, "span_id": t["span_id"],
                         "gen_ai.input.messages": json.dumps(t["users"], ensure_ascii=False),
                         "gen_ai.output.messages": json.dumps(t["outputs"], ensure_ascii=False),
                         "gen_ai.usage.input_tokens": u.get("input_tokens", ""),
                         "gen_ai.usage.output_tokens": u.get("output_tokens", ""),
                         "gen_ai.usage.total_tokens": "" if total is None else total,
                         "U": r["U"], "D": r["D"], "A": r["A"], "H": r["H"]})
    return rows


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("trace", help="traceAI export: OTLP JSON, JSON list of spans, or JSONL")
    ap.add_argument("--out", default="turn_scores.csv", help="CSV with one row per scored turn")
    ap.add_argument("--top-terms", type=int, default=engine.DEFAULT_TOP_TERMS)
    args = ap.parse_args(argv)
    with open(args.trace, encoding="utf-8") as f:
        sessions = build_sessions(load_spans(f.read()))
    rows = score_sessions(sessions, top_terms=args.top_terms)
    with open(args.out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    print("sessions=%d turns_scored=%d -> %s" % (len(sessions), len(rows), args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
