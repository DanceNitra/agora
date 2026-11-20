"""Read a traceAI export and turn it into conversation turns, each counted once.

This is the U/D/A/H adapter for the Future AGI proof of concept.
It does the parsing, the turn deduplication and the U/D/A/H scores of Mirror
Abyss, chapter 13 (see the U/D/A/H section). Diagnostics only.

Input formats that `load_spans` accepts:

- OTLP JSON, as an OpenTelemetry collector or file exporter writes it:
  `{"resourceSpans": [{"scopeSpans": [{"spans": [...]}]}]}`, where each span
  carries `attributes` as a list of `{"key": ..., "value": {"stringValue": ...}}`.
- A JSON list of spans, or one span per line (JSONL), where `attributes` is a
  plain dictionary, as in the traceAI documentation examples.

Message attributes are read in every shape traceAI emits:

- `gen_ai.input.messages` as a JSON list, or as a JSON string holding that list.
- Flattened keys, such as `gen_ai.input.messages.0.message.role` and
  `gen_ai.input.messages.0.message.content`.
- The older OpenInference names `llm.input_messages` and `llm.output_messages`.

Message content can be a plain string or a list of parts
(`[{"type": "text", "content": "..."}]`).

Turn deduplication: a chat request usually resends the whole history. For each
session, spans are ordered by start time, and the adapter keeps the transcript it
has already seen. Only the messages that extend that transcript are new; the
request's output is the assistant's reply. One turn is the new input messages
plus that reply. Repeated history is never scored again.

Python 3.9 or later, standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import math
import os
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Tuple

INPUT_KEYS = ("gen_ai.input.messages", "llm.input_messages")
OUTPUT_KEYS = ("gen_ai.output.messages", "llm.output_messages")
SESSION_KEYS = ("session.id", "gen_ai.conversation.id")
USAGE_PREFIX = "gen_ai.usage."
LEGACY_USAGE = {"llm.token_count.prompt": "input_tokens", "llm.token_count.completion": "output_tokens"}


# ---------------------------------------------------------------- data model

@dataclass
class Message:
    role: str
    content: str
    tool_calls: List[Any] = field(default_factory=list)

    def fingerprint(self) -> str:
        raw = json.dumps([self.role, self.content.strip(), self.tool_calls], sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass
class Span:
    span_id: str
    trace_id: str
    start: int
    attributes: Dict[str, Any]


@dataclass
class Turn:
    session_id: str
    index: int
    span_id: str
    new_input: List[Message]
    output: List[Message]
    usage: Dict[str, Any]
    history_len: int
    notes: List[str] = field(default_factory=list)


# ---------------------------------------------------------------- loading

def _otlp_value(v: Dict[str, Any]) -> Any:
    """Decode one OTLP AnyValue."""
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


def _span(raw: Dict[str, Any]) -> Span:
    ctx = raw.get("context") or {}
    start = raw.get("startTimeUnixNano", raw.get("start_time", 0))
    try:
        start = int(start)
    except (TypeError, ValueError):
        start = 0
    return Span(
        span_id=str(raw.get("spanId") or raw.get("span_id") or ctx.get("span_id") or ""),
        trace_id=str(raw.get("traceId") or raw.get("trace_id") or ctx.get("trace_id") or ""),
        start=start,
        attributes=_attrs(raw.get("attributes")),
    )


def _walk_spans(doc: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(doc, list):
        for item in doc:
            yield from _walk_spans(item)
    elif isinstance(doc, dict):
        if "resourceSpans" in doc:
            for rs in doc["resourceSpans"]:
                for ss in rs.get("scopeSpans", rs.get("instrumentationLibrarySpans", [])):
                    yield from ss.get("spans", [])
        elif "attributes" in doc:
            yield doc


def load_spans(text: str) -> List[Span]:
    """Parse OTLP JSON, a JSON list of spans, or JSONL."""
    text = text.strip()
    if not text:
        return []
    try:
        docs = [json.loads(text)]
    except json.JSONDecodeError:
        docs = [json.loads(line) for line in text.splitlines() if line.strip()]
    return [_span(raw) for doc in docs for raw in _walk_spans(doc)]


# ---------------------------------------------------------------- messages

def _content(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):  # list of parts
        out = []
        for part in value:
            if isinstance(part, dict):
                out.append(str(part.get("content", part.get("text", ""))))
            else:
                out.append(str(part))
        return "\n".join(p for p in out if p)
    return json.dumps(value, ensure_ascii=False)


def _message(raw: Any) -> Optional[Message]:
    if not isinstance(raw, dict):
        return None
    if "message" in raw and isinstance(raw["message"], dict):  # {"message": {"role":..}}
        raw = raw["message"]
    role = raw.get("role") or raw.get("message.role") or ""
    content = raw.get("content", raw.get("parts", raw.get("message.content")))
    tools = raw.get("tool_calls") or raw.get("message.tool_calls") or []
    if isinstance(tools, str):
        try:
            tools = json.loads(tools)
        except json.JSONDecodeError:
            tools = [tools]
    return Message(role=str(role), content=_content(content), tool_calls=list(tools) if tools else [])


def _flattened(attrs: Dict[str, Any], prefix: str) -> List[Dict[str, Any]]:
    """Rebuild a list from keys like `prefix.0.message.role`."""
    pat = re.compile(re.escape(prefix) + r"\.(\d+)\.(.+)$")
    items: Dict[int, Dict[str, Any]] = {}
    for key, value in attrs.items():
        m = pat.match(key)
        if m:
            items.setdefault(int(m.group(1)), {})[m.group(2)] = value
    return [items[i] for i in sorted(items)]


def read_messages(attrs: Dict[str, Any], keys: Tuple[str, ...]) -> List[Message]:
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
        flat = _flattened(attrs, key)
        if flat:
            return [m for m in map(_message, flat) if m is not None]
    return []


def read_usage(attrs: Dict[str, Any]) -> Dict[str, Any]:
    usage = {k[len(USAGE_PREFIX):]: v for k, v in attrs.items() if k.startswith(USAGE_PREFIX)}
    for old, new in LEGACY_USAGE.items():
        if old in attrs and new not in usage:
            usage[new] = attrs[old]
    return usage


def session_of(span: Span) -> Tuple[str, Optional[str]]:
    for key in SESSION_KEYS:
        if span.attributes.get(key):
            return str(span.attributes[key]), None
    return "trace:" + span.trace_id, "no session.id; grouped by trace id"


# ---------------------------------------------------------------- turns

def _new_suffix(seen: List[str], incoming: List[str]) -> Tuple[int, Optional[str]]:
    """Return how many leading `incoming` messages are already known.

    The normal case is that `incoming` starts with the whole known transcript.
    If the client truncated or summarised history, fall back to the longest
    suffix of `seen` that `incoming` starts with, and report it.
    """
    if incoming[:len(seen)] == seen:
        return len(seen), None
    for start in range(1, len(seen)):
        tail = seen[start:]
        if incoming[:len(tail)] == tail:
            return len(tail), "history truncated by the client"
    # No overlap at the start: keep anything we have already seen anywhere out.
    known = set(seen)
    k = 0
    while k < len(incoming) and incoming[k] in known:
        k += 1
    return k, "history rewritten; matched known messages only"


def build_turns(spans: List[Span], skip_system: bool = True) -> List[Turn]:
    """Group chat spans by session and keep only the new part of each request."""
    chat = []
    for s in spans:
        inp = read_messages(s.attributes, INPUT_KEYS)
        out = read_messages(s.attributes, OUTPUT_KEYS)
        if inp or out:
            chat.append((s, inp, out))
    chat.sort(key=lambda t: t[0].start)

    transcripts: Dict[str, List[str]] = {}
    counts: Dict[str, int] = {}
    turns: List[Turn] = []
    for span, inp, out in chat:
        sid, note = session_of(span)
        if skip_system:
            inp = [m for m in inp if m.role != "system"]
        seen = transcripts.setdefault(sid, [])
        fps = [m.fingerprint() for m in inp]
        known, why = _new_suffix(seen, fps)
        new_input = inp[known:]
        notes = [n for n in (note, why) if n]
        if not new_input and not out:
            continue
        idx = counts.get(sid, 0)
        counts[sid] = idx + 1
        turns.append(Turn(session_id=sid, index=idx, span_id=span.span_id, new_input=new_input,
                          output=out, usage=read_usage(span.attributes), history_len=known, notes=notes))
        seen.extend(m.fingerprint() for m in new_input)
        seen.extend(m.fingerprint() for m in out)
    return turns


# ---------------------------------------------------------------- U/D/A/H
#
# Definitions: Mirror Abyss, chapter 13, as specified by Li Guanghao on
# 2026-11-17. Weights and thresholds are in UDAHConfig. Each feature is mapped
# to [0, 1] with the scaling of his reference implementation; those scalings
# are not in the book and are configurable for that reason.
#
# Diagnostics only: the scorer returns numbers and one boolean per turn. It
# never produces advice, fixes, or generated text.

WORD = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")
SENTENCE_END = re.compile(r"[.!?]+")

MODALS = {"might", "could", "perhaps", "may", "would", "should"}
QUALIFIERS_1 = {"somewhat", "approximately", "some", "roughly", "around"}
QUALIFIERS_2 = {("kind", "of"), ("sort", "of")}
CONDITIONALS_1 = {"if", "unless"}
CONDITIONALS_2 = {("provided", "that"), ("as", "long")}
NEGATIONS = {"not", "no", "never", "cannot", "can't", "won't", "wouldn't", "don't", "doesn't", "isn't",
             "aren't", "wasn't", "but", "however", "although", "though", "yet"}
PUNCTUATION = re.compile(r"[.,;:!?\-—()\[\]\"']")
STOPWORDS = {"the", "and", "for", "are", "but", "not", "you", "all", "any", "can", "had", "her", "was",
             "one", "our", "out", "day", "get", "has", "him", "his", "how", "its", "may", "new", "now",
             "old", "see", "two", "who", "did", "she", "let", "put", "say", "too", "use", "that", "this",
             "with", "your", "have", "from", "they", "will", "what", "just", "been", "were", "there"}


@dataclass
class UDAHConfig:
    window: int = 256           # characters
    step: int = 128             # characters
    min_tail: int = 20          # a last window shorter than this is dropped
    u_weights: Tuple[float, float, float, float] = (0.3, 0.2, 0.3, 0.2)  # M_f, Q_f, C_f, Cond_f
    d_weights: Tuple[float, float, float] = (0.4, 0.3, 0.3)              # Novelty_r, Semantic_j, Density_i
    a_weights: Tuple[float, float, float] = (0.5, 0.3, 0.2)              # NegConf, LexDiv, PuncDiv
    h_weights: Tuple[float, float, float] = (0.3, 0.3, 0.4)              # (1-U), D, A
    flip_du: float = 0.15       # flip when dU > flip_du
    flip_dd: float = -0.10      # and dD < flip_dd
    flip_dh: float = -0.08      # and dH < flip_dh
    # Scalings from the reference implementation (not in the book).
    per_word_scale: float = 10.0     # M_f, C_f: hits per word * 10
    neg_scale: float = 5.0           # NegConf: hits per word * 5
    ttr_norm: float = 0.7            # LexDiv: TTR / 0.7
    entropy_norm: float = 3.5        # PuncDiv: bits / 3.5
    first_novelty: float = 1.0       # Novelty_r with no previous window
    first_jump: float = 0.5          # Semantic_j with no previous window


def _clip(x: float) -> float:
    return max(0.0, min(1.0, x))


def _words(text: str) -> List[str]:
    return WORD.findall(text.lower())


def _count(words: List[str], singles: set, pairs: set) -> int:
    n = sum(1 for w in words if w in singles)
    n += sum(1 for a, b in zip(words, words[1:]) if (a, b) in pairs)
    return n


def _sentences(text: str) -> List[str]:
    """Sentences with their end mark kept, so a question can be recognised by its '?'."""
    out, start = [], 0
    for m in SENTENCE_END.finditer(text):
        s = text[start:m.end()].strip()
        if s:
            out.append(s)
        start = m.end()
    tail = text[start:].strip()
    if tail:
        out.append(tail)
    return out


def _bow(text: str) -> Counter:
    return Counter(w for w in _words(text) if len(w) > 2)


def features(window: str, prev_window: str, prev_words: set, cfg: UDAHConfig) -> Dict[str, float]:
    words = _words(window)
    n = max(1, len(words))
    sents = _sentences(window)
    f: Dict[str, float] = {}
    # U
    f["M_f"] = _clip(sum(1 for w in words if w in MODALS) / n * cfg.per_word_scale)
    f["Q_f"] = _clip(sum(1 for s in sents if s.endswith("?")) / max(1, len(sents)))
    f["C_f"] = _clip(_count(words, QUALIFIERS_1, QUALIFIERS_2) / n * cfg.per_word_scale)
    f["Cond_f"] = _clip(_count(words, CONDITIONALS_1, CONDITIONALS_2) / max(1, len(sents)))
    # D
    content = {w for w in words if len(w) > 2}
    if not content:
        f["Novelty_r"] = 0.0
    elif not prev_words:
        f["Novelty_r"] = cfg.first_novelty
    else:
        f["Novelty_r"] = len(content - prev_words) / len(content)
    v1, v2 = _bow(window), _bow(prev_window)
    if not v1 or not v2:
        f["Semantic_j"] = cfg.first_jump
    else:
        dot = sum(v1[w] * v2.get(w, 0) for w in v1)
        norm = math.sqrt(sum(c * c for c in v1.values())) * math.sqrt(sum(c * c for c in v2.values()))
        f["Semantic_j"] = 1.0 - dot / norm
    raw = re.findall(r"\b\w+\b", window)
    numbers = len(re.findall(r"\b\d+\b", window))
    named = len(re.findall(r"\b[A-Z][a-z]+\b", window))
    technical = sum(1 for w in raw if len(w) > 5 and w.lower() not in STOPWORDS)
    per_100 = (numbers + named + technical) / max(1, len(raw)) * 100
    f["Density_i"] = _clip(per_100 / 100)
    # A
    f["NegConf"] = _clip(sum(1 for w in words if w in NEGATIONS) / n * cfg.neg_scale)
    f["LexDiv"] = _clip((len(set(words)) / len(words)) / cfg.ttr_norm) if len(words) >= 5 else 0.0
    marks = PUNCTUATION.findall(window)
    if marks:
        counts = Counter(marks)
        ent = -sum(c / len(marks) * math.log2(c / len(marks)) for c in counts.values())
        f["PuncDiv"] = _clip(ent / cfg.entropy_norm)
    else:
        f["PuncDiv"] = 0.0
    return f


def udah(f: Dict[str, float], cfg: UDAHConfig) -> Dict[str, float]:
    wu, wd, wa, wh = cfg.u_weights, cfg.d_weights, cfg.a_weights, cfg.h_weights
    u = _clip(wu[0] * f["M_f"] + wu[1] * f["Q_f"] + wu[2] * f["C_f"] + wu[3] * f["Cond_f"])
    d = _clip(wd[0] * f["Novelty_r"] + wd[1] * f["Semantic_j"] + wd[2] * f["Density_i"])
    a = _clip(wa[0] * f["NegConf"] + wa[1] * f["LexDiv"] + wa[2] * f["PuncDiv"])
    h = wh[0] * (1 - u) + wh[1] * d - wh[2] * a
    return {"U": u, "D": d, "A": a, "H": h}


def is_flip(prev: Optional[Dict[str, float]], cur: Dict[str, float], cfg: UDAHConfig) -> bool:
    if prev is None:
        return False
    return (cur["U"] - prev["U"] > cfg.flip_du and cur["D"] - prev["D"] < cfg.flip_dd
            and cur["H"] - prev["H"] < cfg.flip_dh)


def windows(text: str, cfg: UDAHConfig) -> List[str]:
    out = [text[i:i + cfg.window] for i in range(0, len(text), cfg.step)]
    out = [w for w in out if len(w) > cfg.min_tail]
    return out or ([text] if text.strip() else [])


def turn_text(turn: Turn) -> str:
    """The new user message(s) and the reply of one turn, as one string."""
    parts = [m.content for m in turn.new_input] + [m.content for m in turn.output]
    return " ".join(p.strip() for p in parts if p and p.strip())


# ---------------------------------------------------------------- self-contradiction
#
# U/D/A/H read word-level signals, so they cannot see an assistant that states a
# policy and later states a different one. This check can. It extracts the
# assistant's COMMITMENTS, never its hedges, and compares each one with what the
# assistant committed to in earlier turns of the same session:
#
# - a number with a unit next to a policy word ("a 14-day window", "30 days ...
#   to return"), keyed by the unit; elapsed or remaining time ("it's been 8
#   days", "22 days remain") is not a commitment;
# - the polarity of a policy subject ("a full refund" vs "a full refund is no
#   longer possible"), per clause, skipping clauses with a modal or a condition.
#
# A value that differs from the most recent earlier value of the same key is reported.
# It is a small rule set, demonstrated on synthetic customer-service text; a
# general contradiction needs a judge (inspeximus check_conflict takes one as
# `incompatible=`). When inspeximus is installed its keyed check_conflict does
# the comparison; otherwise an equivalent in-file ledger does. Diagnostics only.

POLICY_WORDS = {"window", "period", "policy", "refund", "refunds", "return", "returns", "warranty",
                "guarantee", "trial", "exchange", "credit", "deadline", "limit"}
UNITS = {"day": "day", "days": "day", "week": "week", "weeks": "week", "month": "month", "months": "month",
         "year": "year", "years": "year", "hour": "hour", "hours": "hour", "%": "percent", "percent": "percent"}
NUM_WORDS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
    "seventeen eighteen nineteen twenty".split())}
NUM_WORDS.update({"thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "ninety": 90})
NUM_UNIT = re.compile(r"\b(\d+(?:\.\d+)?|" + "|".join(sorted(NUM_WORDS, key=len, reverse=True)) +
                      r")\s*-?\s*(days?|weeks?|months?|years?|hours?|%|percent)\b", re.I)
SUBJECTS = ("full refund", "refund", "return", "exchange", "store credit")
CLAUSE = re.compile(r"[,;:]|\bbut\b|\bhowever\b|[.!?](?:\s|$)", re.I)
NEGATORS = {"not", "no", "never", "cannot", "can't", "won't", "isn't", "aren't", "doesn't", "don't",
            "longer", "ineligible", "impossible", "denied", "unavailable"}
# Set phrases that contain a negator but refuse nothing.
NEG_IDIOMS = re.compile(r"\bno[\s-]+(?:questions[\s-]+asked|problem|worries|doubt|hassle|cost|charge|fee)\b", re.I)
# A number next to these words counts elapsed or remaining time; it is not a policy.
ELAPSED_BEFORE = {"been", "since", "after", "already", "past", "last"}
ELAPSED_AFTER = {"ago", "left", "remain", "remaining", "remains", "passed", "elapsed", "is", "are", "since"}
HEDGES = MODALS | CONDITIONALS_1


def _value(raw: str) -> str:
    raw = raw.lower()
    return str(NUM_WORDS[raw]) if raw in NUM_WORDS else raw


def commitments(text: str) -> List[Tuple[str, str, str]]:
    """(key, value, evidence) for each commitment in one assistant message."""
    out = []
    for clause in (c.strip() for c in CLAUSE.split(text)):
        if not clause:
            continue
        words = _words(clause)
        if HEDGES & set(words):
            continue
        for m in NUM_UNIT.finditer(clause):
            before = _words(clause[:m.start()])[-4:]
            after = _words(clause[m.end():])[:3]
            if ELAPSED_BEFORE & set(before) or ELAPSED_AFTER & set(after):
                continue
            if POLICY_WORDS & set(words):
                unit, value = UNITS[m.group(2).lower()], _value(m.group(1))
                if unit == "week":  # "two weeks" and "14 days" are the same limit
                    unit, value = "day", ("%g" % (float(value) * 7))
                out.append(("policy limit (%s)" % unit, value, clause))
        plain = NEG_IDIOMS.sub(" ", clause)
        low = " " + " ".join(_words(plain)) + " "
        for subj in SUBJECTS:
            if " %s " % subj in low:
                neg = bool(NEGATORS & set(_words(plain)))
                out.append(("%s available" % subj, "no" if neg else "yes", clause))
                break  # the longest subject in the clause speaks for it
    return out


class ClaimLedger:
    """What the assistant has committed to so far in one session."""

    def __init__(self, session_id: str, use_inspeximus: bool = True):
        self.sid, self.seen = session_id, {}
        self.store = None
        if use_inspeximus:
            try:
                import tempfile
                from inspeximus import Inspeximus  # optional; the adapter runs without it
                self._dir = tempfile.TemporaryDirectory()
                self.store = Inspeximus(os.path.join(self._dir.name, "claims.json"))
            except Exception:
                self.store = None

    def check(self, turn_no: int, claims: List[Tuple[str, str, str]]) -> List[Dict[str, Any]]:
        """Compare this turn's claims with the most recent earlier value of each key, then record them."""
        found, reported = [], set()
        for key, value, evidence in claims:
            earlier = self.seen.get(key)
            if not earlier or (key, value) in reported:
                continue
            if self.store is not None:
                hits = self.store.check_conflict(evidence, key=self.sid + "|" + key, object=value)
                clash = any(h.get("kind") == "keyed_value_change" for h in hits)
            else:
                clash = earlier[1] != value
            if clash:
                reported.add((key, value))
                found.append({"key": key, "earlier": earlier[1], "earlier_turn": earlier[0],
                              "now": value, "evidence": evidence})
        latest = {}
        for key, value, evidence in claims:
            latest[key] = (value, evidence)  # the last statement in the turn is the one that stands
        for key, (value, evidence) in latest.items():
            self.seen[key] = (turn_no, value)
            if self.store is not None:
                self.store.remember(evidence, key=self.sid + "|" + key, object=value)
        return found


def score_session(turns: List[Turn], cfg: Optional[UDAHConfig] = None, detail: bool = False,
                  use_inspeximus: bool = True, contradictions: bool = False) -> List[Dict[str, Any]]:
    """Score the turns of ONE session in order.

    Windows run over each turn's text; the previous window and the set of words
    already seen carry over from turn to turn, so Novelty_r and Semantic_j see
    the conversation, never its repeated history. A turn reports the mean of its
    windows, and is a flip point if any of its windows is one.
    """
    cfg = cfg or UDAHConfig()
    prev_window, prev_words, prev_scores = "", set(), None
    ledger = ClaimLedger(turns[0].session_id if turns else "", use_inspeximus) if contradictions else None
    rows = []
    for t in turns:
        wins = []
        for w in windows(turn_text(t), cfg):
            f = features(w, prev_window, prev_words, cfg)
            s = udah(f, cfg)
            flip = is_flip(prev_scores, s, cfg)
            wins.append({**{k: round(v, 4) for k, v in s.items()}, "is_flip_point": flip,
                         **({"features": {k: round(v, 4) for k, v in f.items()}} if detail else {})})
            prev_window, prev_scores = w, s
            prev_words |= {x for x in _words(w) if len(x) > 2}
        if not wins:
            continue
        row = {"session_id": t.session_id, "turn": t.index + 1}
        for k in ("U", "D", "A", "H"):
            row[k] = round(sum(w[k] for w in wins) / len(wins), 4)
        row["is_flip_point"] = any(w["is_flip_point"] for w in wins)
        if ledger is not None:  # optional module, off by default
            claims = [c for m in t.output for c in commitments(m.content)]
            conflicts = ledger.check(t.index + 1, claims)
            row["self_contradiction"] = bool(conflicts)
            row["conflicts"] = conflicts
        if detail:
            row["windows"] = wins
        rows.append(row)
    return rows


def score_turns(turns: List[Turn], cfg: Optional[UDAHConfig] = None, detail: bool = False,
                use_inspeximus: bool = True, contradictions: bool = False) -> List[Dict[str, Any]]:
    by_session: Dict[str, List[Turn]] = {}
    for t in turns:
        by_session.setdefault(t.session_id, []).append(t)
    rows = []
    for sid in by_session:
        rows.extend(score_session(by_session[sid], cfg, detail, use_inspeximus, contradictions))
    return rows


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("trace", help="traceAI export: OTLP JSON, JSON list of spans, or JSONL")
    ap.add_argument("--keep-system", action="store_true", help="treat system messages as part of a turn")
    ap.add_argument("--detail", action="store_true", help="also print each window and its features")
    ap.add_argument("--self-contradiction", action="store_true",
                    help="optional module: report when the assistant changes a commitment from an earlier turn")
    args = ap.parse_args(argv)
    with open(args.trace, encoding="utf-8") as f:
        spans = load_spans(f.read())
    rows = score_turns(build_turns(spans, skip_system=not args.keep_system), detail=args.detail,
                       contradictions=args.self_contradiction)
    json.dump(rows, sys.stdout, ensure_ascii=False, indent=1)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
