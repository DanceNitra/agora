#!/usr/bin/env python3
"""
trajectory_v3_ultra.py — 逐轮 / 超细粒度 U/D/A/H 轨迹审计（纯标准库实现）

================================================================================
一、U / D / A / H 定义
================================================================================
U（Unity / 概念一致性）
    从当前评分文本中抽取关键词（英文词 + 中文 2~4 字 n-gram，去停用词，取前 N 个）。
    对每个关键词，取出包含它的所有句子，计算句子字符 3-gram 向量的两两余弦相似度，
    求均值；只出现一次的关键词按 1.0 计；U = 所有关键词得分的均值。
D（Development / 概念位置分布）
    对每个关键词取首次出现的字符位置 p，归一化 p / len(text)，
    计算总体标准差 stdev，D = min(1.0, stdev * 2.5)。
    可用关键词首现位置少于 2 个时，D = 0.0。
A（Adversarial / 对抗性与矛盾压力）
    A = 0.6 * 含对抗标记的句子占比
        + 0.4 * min(1.0, 命中的互斥短语对数 * 0.3)
    对抗标记示例：但是 / 然而 / 不过 / 需要注意的是 / 另一方面 / however / although。
    互斥短语对为可配置的种子规则（见 CONTRADICTION_RULES）。
H（Harmony / 和谐度）
    H = λu * U + λd * D - λa * A，默认 λu = λd = 0.4，λa = 0.2。

================================================================================
二、每轮只计分一次（去重逻辑）
================================================================================
- 一个 assistant turn = 一个评分单元，只输出一行每轮分数（模式 B）。
- 该轮评分文本 = 本轮 user 内容 + 本轮 assistant 输出，绝不拼接前几轮历史。
- 模式 A 的超细轨迹只在本轮内部按字符前缀展开，不继承上一轮。
- 完全重复（user, assistant 完全相同）的 turn 会被跳过，并计入
  duplicate_history_skipped；空 turn 计入 empty_turns_skipped。
- 因此不会出现“后面的请求把历史又计一遍”的重复计分。

================================================================================
三、nik13 POC 字段要求（交付 CSV 必须逐字一致）
================================================================================
turn_id, session.id, gen_ai.input.messages, gen_ai.output.messages,
gen_ai.usage.input_tokens, gen_ai.usage.output_tokens,
gen_ai.usage.total_tokens, U, D, A, H
- session.id 使用 case 名称；
- gen_ai.input.messages / gen_ai.output.messages 为 JSON 数组字符串；
- usage 字段按字符数估算（中文≈1 token/字，英文≈4 字符/token），不为 0。

================================================================================
四、输入格式（自动探测）
================================================================================
1) JSON：顶层为 case 列表，或 {"cases": [...]}，或单个 {"messages": [...]}；
   messages 元素支持 role/content，content 可为字符串或 parts 列表。
2) 文本：按行解析，支持 "User:" / "AI:" / "Assistant:" / "用户:" / "助手:"，
   以及 "第X组：" 分组行和 "Case 1 (名称)" / "Case A1 (名称)" 分案行。

================================================================================
五、用法
================================================================================
单 case 超细轨迹 + 每轮计分：
    python trajectory_v3_ultra.py --input case_v2_01.json --char_step 10 \
        --output_traj traj.csv --output_turn turn.csv

整个测试集（文本内含 47 个 case）：
    python trajectory_v3_ultra.py --input 万象渊鉴·场域诊断测试集.txt \
        --char_step 10 --output_traj ultra_trace.csv --output_turn ultra_turn_scores.csv
"""

import argparse
import csv
import json
import math
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from statistics import pstdev
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# 可配置参数
# ---------------------------------------------------------------------------
DEFAULT_CHAR_STEP = 10          # 超细步长：每 10 个字符一个采样点
DEFAULT_MIN_CHARS = 1           # 起始采样下限（1 = 覆盖整个 turn）
DEFAULT_TOP_TERMS = 10          # 每轮参与 U/D 计算的关键词数量

LAMBDA_U = 0.4
LAMBDA_D = 0.4
LAMBDA_A = 0.2

# 与 thinkcheck_harmony.config.ADVERSARIAL_MARKERS 对齐，并补充英文
ADVERSARIAL_MARKERS = [
    "但是", "然而", "不过", "尽管", "需要注意的是", "必须指出",
    "与此相反", "另一方面", "存在风险", "有待商榷",
    "but", "however", "although", "though", "on the other hand",
    "that said", "may not", "might not", "cannot be guaranteed", "it depends",
]

# 互斥短语对：同一评分单元内同时出现即视为一次矛盾命中
CONTRADICTION_RULES = [
    ("original card", "store credit"),
    ("payment card", "store credit"),
    ("原路退回", "账户余额"),
    ("全额", "手续费"),
    ("free of charge", "service fee"),
]

SENTENCE_SPLIT_RE = re.compile(r"[。！？；!?;\n]+")
CJK_RUN_RE = re.compile(r"[\u4e00-\u9fff]{2,}")
WORD_RE = re.compile(r"[A-Za-z][A-Za-z\-]{2,}")

GROUP_RE = re.compile(r"^第[一二三四五六七八九十百]+组[：:]\s*(.*)$")
CASE_RE = re.compile(
    r"^Case\s+([A-Za-z]?\d+)\s*(?:[（(](.*?)[）)]|[：:]\s*(.*))?$"
)
TURN_RE = re.compile(r"^(User|AI|Assistant|用户|助手)\s*[：:]\s?(.*)$")

CHINESE_STOP = {
    "我们", "你们", "他们", "这个", "那个", "这些", "那些", "可以", "如果",
    "因为", "所以", "但是", "还是", "就是", "已经", "现在", "应该", "需要",
    "什么", "没有", "自己", "一个", "不是", "不能", "不会", "以及", "进行",
}
ENGLISH_STOP = {
    "the", "and", "for", "with", "that", "this", "you", "your", "will", "can",
    "have", "has", "are", "was", "were", "from", "not", "but", "all", "any",
    "our", "it", "is", "to", "of", "in", "on", "at", "be", "as", "or", "please",
    "would", "could", "should", "there", "their", "them", "they", "been",
    "into", "than", "then", "when", "what", "which", "who", "about", "just",
}

TRACE_COLUMNS = [
    "step", "turn_id", "char_pos", "U", "D", "A", "H",
    "U_diff", "D_diff", "A_diff", "H_driven_by", "cumul_A", "D_volatility",
]
TURN_COLUMNS = [
    "turn_id", "session.id",
    "gen_ai.input.messages", "gen_ai.output.messages",
    "gen_ai.usage.input_tokens", "gen_ai.usage.output_tokens",
    "gen_ai.usage.total_tokens",
    "U", "D", "A", "H",
]


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------
@dataclass
class Turn:
    index: int
    user: str = ""
    assistant: str = ""
    user_start: int = 0
    assistant_start: int = 0
    assistant_end: int = 0

    @property
    def turn_id_suffix(self) -> str:
        return f"T{self.index:02d}"


@dataclass
class Case:
    case_id: str
    name: str
    group: str
    turns: List[Turn] = field(default_factory=list)
    raw_id: str = ""
    source_path: str = ""


# ---------------------------------------------------------------------------
# 文本工具
# ---------------------------------------------------------------------------
def split_sentences(text: str) -> List[str]:
    return [s.strip() for s in SENTENCE_SPLIT_RE.split(text) if s.strip()]


def extract_terms(text: str, top_n: int = DEFAULT_TOP_TERMS) -> List[str]:
    """英文词 + 中文 2~4 字 n-gram，按频次与长度排序取前 top_n。"""
    candidates: Counter = Counter()
    for word in WORD_RE.findall(text):
        lowered = word.lower()
        if lowered not in ENGLISH_STOP:
            candidates[lowered] += 1
    for run in CJK_RUN_RE.findall(text):
        for size in (2, 3, 4):
            for i in range(len(run) - size + 1):
                gram = run[i:i + size]
                if gram not in CHINESE_STOP:
                    candidates[gram] += 1
    ranked = sorted(
        candidates.items(),
        key=lambda kv: (kv[1] * max(1, len(kv[0]) - 1), len(kv[0])),
        reverse=True,
    )
    return [term for term, _ in ranked[:top_n]]


def _char_vector(text: str) -> Counter:
    compact = re.sub(r"\s+", "", text.lower())
    if len(compact) < 3:
        return Counter(compact)
    return Counter(compact[i:i + 3] for i in range(len(compact) - 2))


def _cosine(left: Counter, right: Counter) -> float:
    if not left or not right:
        return 1.0
    dot = sum(value * right.get(key, 0) for key, value in left.items())
    norm_left = math.sqrt(sum(value * value for value in left.values()))
    norm_right = math.sqrt(sum(value * value for value in right.values()))
    if not norm_left or not norm_right:
        return 0.0
    return dot / (norm_left * norm_right)


def _marker_in(sentence: str, marker: str) -> bool:
    if marker.isascii():
        return re.search(
            r"(?<![A-Za-z])" + re.escape(marker) + r"(?![A-Za-z])",
            sentence.lower(),
        ) is not None
    return marker in sentence


# ---------------------------------------------------------------------------
# U / D / A / H
# ---------------------------------------------------------------------------
def compute_u(text: str, terms: Optional[Sequence[str]] = None) -> float:
    if terms is None:
        terms = extract_terms(text)
    sentences = split_sentences(text)
    scores: List[float] = []
    for term in terms:
        indices = [i for i, sentence in enumerate(sentences) if term in sentence]
        if len(indices) < 2:
            scores.append(1.0)
            continue
        vectors = [_char_vector(sentences[i]) for i in indices]
        similarities = [
            _cosine(vectors[a], vectors[b])
            for a in range(len(vectors))
            for b in range(a + 1, len(vectors))
        ]
        scores.append(sum(similarities) / len(similarities))
    return sum(scores) / len(scores) if scores else 1.0


def compute_d(text: str, terms: Optional[Sequence[str]] = None) -> float:
    if terms is None:
        terms = extract_terms(text)
    if not text:
        return 0.0
    positions = [
        text.find(term) for term in terms if term and text.find(term) >= 0
    ]
    if len(positions) <= 1:
        return 0.0
    normalized = [position / len(text) for position in positions]
    return min(1.0, pstdev(normalized) * 2.5)


def compute_a(text: str) -> float:
    sentences = split_sentences(text)
    if not sentences:
        return 0.0
    marker_hits = sum(
        1 for sentence in sentences
        if any(_marker_in(sentence, marker) for marker in ADVERSARIAL_MARKERS)
    )
    marker_density = marker_hits / len(sentences)
    rule_hits = sum(
        1 for first, second in CONTRADICTION_RULES
        if first in text and second in text
    )
    rule_score = min(1.0, rule_hits * 0.3)
    return min(1.0, 0.6 * marker_density + 0.4 * rule_score)


def compute_h(
    u: float,
    d: float,
    a: float,
    lambda_u: float = LAMBDA_U,
    lambda_d: float = LAMBDA_D,
    lambda_a: float = LAMBDA_A,
) -> float:
    return lambda_u * u + lambda_d * d - lambda_a * a


def score_text(text: str, top_terms: int = DEFAULT_TOP_TERMS) -> Tuple[float, float, float, float]:
    terms = extract_terms(text, top_terms)
    u = compute_u(text, terms)
    d = compute_d(text, terms)
    a = compute_a(text)
    return u, d, a, compute_h(u, d, a)


def h_driven_by(du: float, dd: float, da: float, dh: float) -> str:
    """H 变化归因：比较 U/D/A 一阶差分的绝对值。"""
    if abs(dh) < 0.001 or max(abs(du), abs(dd), abs(da)) < 0.001:
        return "均衡"
    if abs(du) >= abs(dd) and abs(du) >= abs(da):
        return "U"
    if abs(dd) >= abs(du) and abs(dd) >= abs(da):
        return "D"
    return "A"


# ---------------------------------------------------------------------------
# 输入解析
# ---------------------------------------------------------------------------
def _clean_name(name: str) -> str:
    return (name or "").strip().strip("\"'“”‘’").strip()


def _derive_case_id(raw_id: str, group: str, fallback_index: int) -> str:
    digits = re.sub(r"\D", "", raw_id or "")
    number = int(digits) if digits else fallback_index
    if re.search(r"V2", group, re.I):
        return f"V2-{number:02d}"
    if re.search(r"benchmark", group, re.I):
        return f"BENCH-{number:02d}"
    # Category 组内的 "A1" / "F3" 等原始编号优先决定字母
    letter = re.match(r"^([A-Za-z])", raw_id or "")
    if letter:
        return f"CAT-{letter.group(1).upper()}{number}"
    category = re.search(r"Category\s*([A-Za-z])", group, re.I)
    if category:
        return f"CAT-{category.group(1).upper()}{number}"
    return f"CASE-{fallback_index:03d}"


def finalize_case(case: Case) -> None:
    """补齐 case_id、turn 编号与字符偏移（char_pos 的基准）。"""
    if not case.case_id:
        case.case_id = _derive_case_id(case.raw_id, case.group, 1)
    if not case.name:
        case.name = case.case_id
    cursor = 0
    for index, turn in enumerate(case.turns, 1):
        turn.index = index
        turn.user_start = cursor
        cursor += len(turn.user)
        turn.assistant_start = cursor
        cursor += len(turn.assistant)
        turn.assistant_end = cursor


def parse_text_cases(text: str) -> List[Case]:
    cases: List[Case] = []
    group = ""
    current: Optional[Case] = None
    turn: Optional[Turn] = None
    last_role: Optional[str] = None

    def finish() -> None:
        nonlocal current
        if current is not None and current.turns:
            finalize_case(current)
            cases.append(current)
        current = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        match = GROUP_RE.match(line)
        if match:
            finish()
            group = match.group(1).strip()
            turn = None
            last_role = None
            continue

        match = CASE_RE.match(line)
        if match:
            finish()
            raw_id = match.group(1)
            name = _clean_name(match.group(2) or match.group(3) or "")
            current = Case(
                case_id="",
                name=name,
                group=group,
                raw_id=raw_id,
            )
            turn = None
            last_role = None
            continue

        match = TURN_RE.match(line)
        if match:
            if current is None:
                current = Case(case_id="", name="", group=group)
            role = "user" if match.group(1).lower() in ("user", "用户") else "assistant"
            content = match.group(2).strip()
            if role == "user":
                if turn is not None and turn.assistant.strip():
                    turn = None
                if turn is None:
                    turn = Turn(index=0)
                    current.turns.append(turn)
                turn.user = f"{turn.user}\n{content}".strip() if turn.user else content
            else:
                if turn is None:
                    turn = Turn(index=0)
                    current.turns.append(turn)
                turn.assistant = content
            last_role = role
            continue

        # 续行：归属当前 turn 的最后一种角色
        if turn is None:
            continue
        if last_role == "assistant":
            turn.assistant = f"{turn.assistant}\n{line}".strip()
        else:
            turn.user = f"{turn.user}\n{line}".strip() if turn.user else line

    finish()
    return cases


def _content_text(message: Dict) -> str:
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks = []
        for part in content:
            if isinstance(part, str):
                chunks.append(part)
            elif isinstance(part, dict):
                value = part.get("text") or part.get("content")
                if isinstance(value, str):
                    chunks.append(value)
        return "\n".join(chunks)
    return ""


def _messages_to_turns(messages: List[Dict]) -> List[Turn]:
    turns: List[Turn] = []
    pending_user: List[str] = []
    for message in messages:
        role = str(message.get("role", "")).lower()
        content = _content_text(message)
        if role in ("user", "human", "用户"):
            pending_user.append(content)
        elif role in ("assistant", "ai", "model", "助手"):
            turns.append(Turn(
                index=0,
                user="\n".join(pending_user).strip(),
                assistant=content.strip(),
            ))
            pending_user = []
    return turns


def _case_from_json(raw: Dict, index: int, source_path: str) -> Case:
    case_id = str(
        raw.get("case_id") or raw.get("id") or raw.get("case") or ""
    ).strip()
    group = str(raw.get("group") or raw.get("category") or "").strip()
    name = str(
        raw.get("name") or raw.get("case_name") or raw.get("title") or ""
    ).strip()
    messages = raw.get("messages") or raw.get("conversation") or []
    case = Case(
        case_id=case_id,
        name=name,
        group=group,
        turns=_messages_to_turns(messages) if isinstance(messages, list) else [],
        raw_id=case_id,
        source_path=source_path,
    )
    if not case.case_id:
        case.case_id = _derive_case_id("", group, index)
    finalize_case(case)
    return case


def load_cases(path: str) -> List[Case]:
    """自动探测 JSON / 纯文本格式，返回 case 列表。"""
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return parse_text_cases(text)

    if isinstance(data, list):
        raw_cases = data
    elif isinstance(data, dict) and isinstance(data.get("cases"), list):
        raw_cases = data["cases"]
    elif isinstance(data, dict):
        raw_cases = [data]
    else:
        return []

    cases = [
        _case_from_json(raw, i, path)
        for i, raw in enumerate(raw_cases, 1)
        if isinstance(raw, dict)
    ]
    return [case for case in cases if case.turns]


# ---------------------------------------------------------------------------
# 采样与输出
# ---------------------------------------------------------------------------
def iter_prefix_lengths(
    total: int,
    char_step: int = DEFAULT_CHAR_STEP,
    min_chars: int = DEFAULT_MIN_CHARS,
) -> Iterator[int]:
    """生成本轮 assistant 文本的前缀长度（含完整长度，步长超细）。"""
    if total <= 0:
        return
    step = max(1, int(char_step))
    floor = max(1, int(min_chars))
    position = step
    while position < total:
        if position >= floor:
            yield position
        position += step
    yield total


def estimate_tokens(text: str) -> int:
    """中文按 1 字≈1 token，其他字符按 4 字符≈1 token 估算。"""
    if not text:
        return 0
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    other = len(text) - cjk
    return max(1, cjk + math.ceil(other / 4))


def _turn_scored_text(turn: Turn, prefix_length: int) -> str:
    assistant_part = turn.assistant[:prefix_length]
    if turn.user:
        return f"{turn.user}\n{assistant_part}".strip()
    return assistant_part.strip()


def iter_case_rows(
    case: Case,
    char_step: int = DEFAULT_CHAR_STEP,
    min_chars: int = DEFAULT_MIN_CHARS,
    top_terms: int = DEFAULT_TOP_TERMS,
    stats: Optional[Dict[str, int]] = None,
) -> Iterator[Tuple[str, Dict[str, object]]]:
    """流式产出 (kind, row)，kind ∈ {"trace", "turn"}。

    - trace：超细轨迹（仅内部验证），每个 turn 内从自己的前缀重新累积；
    - turn：该 turn 最后一个采样点（完整 assistant 输出）的分数，每轮仅一行。
    """
    if stats is None:
        stats = {}
    for key in ("turns_scored", "duplicate_history_skipped", "empty_turns_skipped", "trace_points"):
        stats.setdefault(key, 0)

    seen_pairs = set()
    step = 0
    for turn in case.turns:
        if not turn.assistant.strip():
            stats["empty_turns_skipped"] += 1
            continue
        pair_key = (turn.user.strip(), turn.assistant.strip())
        if pair_key in seen_pairs:
            stats["duplicate_history_skipped"] += 1
            continue
        seen_pairs.add(pair_key)

        previous: Optional[Tuple[float, float, float, float]] = None
        d_values: List[float] = []
        cumulative_a = 0.0
        final_trace: Optional[Dict[str, object]] = None
        turn_id = f"{case.case_id}#{turn.turn_id_suffix}"

        for prefix_length in iter_prefix_lengths(
            len(turn.assistant), char_step, min_chars
        ):
            step += 1
            text = _turn_scored_text(turn, prefix_length)

            u, d, a, h = score_text(text, top_terms)
            cumulative_a += a
            d_values.append(d)

            if previous is None:
                delta_u = delta_d = delta_a = 0.0
            else:
                delta_u = u - previous[0]
                delta_d = d - previous[1]
                delta_a = a - previous[2]
            delta_h = h - (previous[3] if previous else h)

            trace_row: Dict[str, object] = {
                "step": step,
                "turn_id": turn_id,
                "char_pos": turn.assistant_start + prefix_length,
                "U": round(u, 4),
                "D": round(d, 4),
                "A": round(a, 4),
                "H": round(h, 4),
                "U_diff": round(delta_u, 4),
                "D_diff": round(delta_d, 4),
                "A_diff": round(delta_a, 4),
                "H_driven_by": h_driven_by(delta_u, delta_d, delta_a, delta_h),
                "cumul_A": round(cumulative_a, 4),
                "D_volatility": round(pstdev(d_values) if len(d_values) > 1 else 0.0, 4),
            }
            yield "trace", trace_row
            stats["trace_points"] += 1
            final_trace = trace_row
            previous = (u, d, a, h)

        if final_trace is None:
            continue

        stats["turns_scored"] += 1
        turn_row: Dict[str, object] = {
            "turn_id": turn_id,
            "session.id": case.name or case.case_id,
            "gen_ai.input.messages": json.dumps(
                [{"role": "user", "content": turn.user}], ensure_ascii=False
            ),
            "gen_ai.output.messages": json.dumps(
                [{"role": "assistant", "content": turn.assistant}],
                ensure_ascii=False,
            ),
            "gen_ai.usage.input_tokens": estimate_tokens(turn.user),
            "gen_ai.usage.output_tokens": estimate_tokens(turn.assistant),
            "gen_ai.usage.total_tokens": estimate_tokens(turn.user)
            + estimate_tokens(turn.assistant),
            "U": final_trace["U"],
            "D": final_trace["D"],
            "A": final_trace["A"],
            "H": final_trace["H"],
        }
        yield "turn", turn_row


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="超细粒度 U/D/A/H 轨迹审计（每轮只计分一次，纯标准库）"
    )
    parser.add_argument("--input", required=True, help="输入 JSON 或文本测试集")
    parser.add_argument("--char_step", type=int, default=DEFAULT_CHAR_STEP,
                        help="超细步长，默认 10 字符")
    parser.add_argument("--min_chars", type=int, default=DEFAULT_MIN_CHARS,
                        help="起始采样字符下限，默认 1")
    parser.add_argument("--top_terms", type=int, default=DEFAULT_TOP_TERMS,
                        help="每轮关键词数量，默认 10")
    parser.add_argument("--output_traj", default="ultra_trace.csv",
                        help="超细轨迹 CSV（内部验证）")
    parser.add_argument("--output_turn", default="ultra_turn_scores.csv",
                        help="每轮计分 CSV（交付用）")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    if not os.path.isfile(args.input):
        print(f"input not found: {args.input}", file=sys.stderr)
        return 1

    cases = load_cases(args.input)
    if not cases:
        print(f"no cases parsed from {args.input}", file=sys.stderr)
        return 1

    stats: Dict[str, int] = {}
    with open(args.output_traj, "w", encoding="utf-8-sig", newline="") as traj_file, \
            open(args.output_turn, "w", encoding="utf-8-sig", newline="") as turn_file:
        traj_writer = csv.DictWriter(traj_file, fieldnames=TRACE_COLUMNS)
        turn_writer = csv.DictWriter(turn_file, fieldnames=TURN_COLUMNS)
        traj_writer.writeheader()
        turn_writer.writeheader()

        for case in cases:
            case_stats: Dict[str, int] = {}
            for kind, row in iter_case_rows(
                case,
                char_step=args.char_step,
                min_chars=args.min_chars,
                top_terms=args.top_terms,
                stats=case_stats,
            ):
                if kind == "trace":
                    traj_writer.writerow(row)
                else:
                    turn_writer.writerow(row)
            for key, value in case_stats.items():
                stats[key] = stats.get(key, 0) + value
            print(
                f"{case.case_id:<10} {case.name[:22]:<24} "
                f"turns={case_stats.get('turns_scored', 0):<3} "
                f"points={case_stats.get('trace_points', 0):<4}"
            )

    print(
        f"cases={len(cases)} turns_scored={stats.get('turns_scored', 0)} "
        f"duplicate_history_skipped={stats.get('duplicate_history_skipped', 0)} "
        f"empty_turns_skipped={stats.get('empty_turns_skipped', 0)} "
        f"trace_points={stats.get('trace_points', 0)}"
    )
    print(f"wrote {args.output_traj} and {args.output_turn}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
