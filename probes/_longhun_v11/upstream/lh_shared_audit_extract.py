#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
龍魂 · 共享审计数据集提取引擎 v1.0
DNA: #龍芯⚡️丙午·丙申·癸酉·亥时-SHARED-AUDIT-EXTRACT-v1.0-UID9622
创建者: 诸葛鑫（UID9622）
License: MulanPSL v2 (https://license.coscl.org.cn/MulanPSL2)

从真实对抗流水线日志（feedback_pool.jsonl）+ 真实审计日志（audit_log.jsonl）
提取、清洗、脱敏、标准化，生成面向社区共享的推理审计数据集。

诚实原则（P0）：
  - 只输出日志中真实存在的字段，不编造 inference_time_ms / tokens_used 等未采集数据
  - 字段口径锁: request_id / timestamp / model / prompt / response / dna_sig /
    attack_category / verdict / rejection_reason / source / record_type
  - 所有 prompt/response 均来自真实运行记录，仅做 ANSI 清洗 + 敏感信息脱敏
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FB_POOL = ROOT / "11_DATA/feedback_loop/feedback_pool.jsonl"
AUDIT_LOG = ROOT / "audit_log.jsonl"
OUT_DIR = ROOT / "11_DATA/shared_datasets"
OUT_FILE = OUT_DIR / "longhun-shared-audit-dataset-v1.0.jsonl"
N_SAMPLES = 18          # 推理记录条数
N_FIREWALL = 2          # 监管防火墙记录条数
RESP_MAX = 400          # response 脱敏后最大长度（超出截断并标注）

# ANSI 转义序列清洗
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
# 疑似敏感模式（用于脱敏标注）
SENSITIVE_PATTERNS = [
    (re.compile(r"AKIA[0-9A-Z]{16}"), "<AWS_KEY_REDACTED>"),
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "<API_KEY_REDACTED>"),
    (re.compile(r"[0-9a-f]{40,}"), "<LONG_HASH_REDACTED>"),
    (re.compile(r"A2D0092CEE2E5BA87035600924C3704A8CC26D5F"), "<GPG_FINGERPRINT_REDACTED>"),
]


def clean_response(raw):
    """清洗 ANSI 转义 + 敏感脱敏 + 截断标注"""
    if not raw:
        return ""
    text = ANSI_RE.sub("", raw)
    for pat, repl in SENSITIVE_PATTERNS:
        text = pat.sub(repl, text)
    if len(text) > RESP_MAX:
        text = text[:RESP_MAX] + "...[truncated:{}chars]".format(len(raw))
    return text


def unique_records(recs):
    """按 (dna, prompt) 去重，保持顺序"""
    seen = set()
    out = []
    for r in recs:
        key = (r.get("dna", ""), r.get("prompt", ""))
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def pick_samples(recs, n):
    """挑选代表性样本：覆盖模型版本 + 攻击类别 + 响应长度梯度"""
    recs = unique_records(recs)

    def weight(r):
        cats = "|".join(r.get("category") or [])
        w = 0
        for kw in ("编码绕过", "索要内核代码", "角色扮演", "道德困境", "伪装权威", "数据泄露"):
            if kw in cats:
                w += 1
        return w

    # 按 类别覆盖 > 模型多样性 > 长度梯度 排序
    recs.sort(key=lambda r: (weight(r), -len(r.get("response") or "")))
    picked, seen_cats = [], set()
    for r in recs:
        if len(picked) >= n:
            break
        cats = tuple(sorted(r.get("category") or ["未分类"]))
        if cats not in seen_cats:
            seen_cats.add(cats)
            picked.append(r)
    # 补充长度梯度（短/中/长）
    rest = [r for r in recs if r not in picked]
    rest.sort(key=lambda r: len(r.get("response") or ""))
    short, mid, long = [], [], []
    for r in rest:
        L = len(r.get("response") or "")
        (short if L < 60 else mid if L < 200 else long).append(r)
    for bucket in (short, mid, long):
        for r in bucket:
            if len(picked) >= n:
                break
            picked.append(r)
    return picked[:n]


def to_shared(r, idx):
    """标准化为共享 schema"""
    cats = r.get("category") or []
    return {
        "request_id": "REQ-{}-{:03d}".format(r.get("dna", "unknown").replace("🐉", "")[-8:], idx),
        "timestamp": r.get("created_at", ""),
        "model": r.get("model", ""),
        "prompt": r.get("prompt", ""),
        "response": clean_response(r.get("response", "")),
        "dna_sig": r.get("dna", ""),
        "attack_category": cats if cats else ["未分类"],
        "verdict": r.get("status", ""),
        "rejection_reason": r.get("rejection_reason", ""),
        "source": r.get("source", "adversarial_pipeline"),
        "record_type": "inference",
    }


def pick_firewall(logs, n=2):
    """从审计日志提取监管防火墙 DENY 记录"""
    fw = [d for d in logs if d.get("action") == "DENY"]
    out = []
    for d in fw[:n]:
        ctx = d.get("context") or {}
        out.append({
            "request_id": "FW-{}-{:03d}".format(d.get("dna", "").split("-")[-1], len(out) + 1),
            "timestamp": d.get("timestamp", ""),
            "model": "regulatory-firewall-v2.0",
            "prompt": "[system] 权限审计请求 | domain={} scopes={}".format(
                ctx.get("domain"), ctx.get("scopes")),
            "response": d.get("reason", ""),
            "dna_sig": d.get("dna", ""),
            "attack_category": ["权限审计-" + str(d.get("audit_mark", ""))],
            "verdict": "DENY" if d.get("action") == "DENY" else "ALLOW",
            "rejection_reason": d.get("reason", ""),
            "source": "regulatory_firewall",
            "record_type": "firewall",
        })
    return out


def main():
    if not FB_POOL.exists() or not AUDIT_LOG.exists():
        print("RED 源日志不存在，中止")
        sys.exit(1)

    fb = [json.loads(l) for l in FB_POOL.read_text().splitlines() if l.strip()]
    audit = [json.loads(l) for l in AUDIT_LOG.read_text().splitlines() if l.strip()]

    picked = pick_samples(fb, N_SAMPLES)
    fw = pick_firewall(audit, N_FIREWALL)
    rows = [to_shared(r, i + 1) for i, r in enumerate(picked)] + fw

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUT_FILE.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # 校验
    read_back = [json.loads(l) for l in OUT_FILE.read_text().splitlines() if l.strip()]
    required = ["request_id", "timestamp", "model", "prompt", "response",
                "dna_sig", "attack_category", "verdict", "source", "record_type"]
    errors = []
    for r in read_back:
        for k in required:
            if k not in r:
                errors.append("缺字段 {}: {}".format(k, r.get("request_id")))
    # 无编造字段检查
    for r in read_back:
        for k in ("inference_time_ms", "tokens_used"):
            if k in r:
                errors.append("出现编造字段 {}".format(k))
    if errors:
        print("RED 校验失败:")
        for e in errors:
            print("  -", e)
        sys.exit(1)

    cats, models = set(), set()
    for r in read_back:
        cats.update(r["attack_category"])
        models.add(r["model"])
    print("OK 数据集生成: {}".format(OUT_FILE))
    print("   条数: {} (推理 {} + 防火墙 {})".format(len(read_back), len(picked), len(fw)))
    print("   模型覆盖: {}".format(sorted(models)))
    print("   类别覆盖: {}".format(sorted(cats)))
    print("   诚实声明: 未编造 inference_time_ms / tokens_used（源日志未采集）")


if __name__ == "__main__":
    main()
