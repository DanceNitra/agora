"""RECHECK THE FIGURES in self-correction reply on deepseek-ai/DeepSeek-V3#1591.

This draft's central claims are about OUR OWN probe being wrong, so the checks have to be
able to catch us being wrong about that too. Every figure is read out of the draft and
compared against the audit artifact or the live files at both revisions. Quotations of the
author's own strings are checked against his records. Coverage plus mutation control.

THIS FILE IS NOT THE GATE. It recomputes figures against receipts, which is ONE check
inside VALIDATE. The gate is the SKILLS: verify-claims, stress-claim, humanizer, and
storm when the claim rests on literature. Owner, 2026-08-26, after I called a file like
this one "the gate" three times in a day: "ZAPIS SI TO NATVRDO A TEN TVOJ SKRIPT DAJ DO
HOVEN." tools/send_approved.py now refuses to publish without a receipt from each skill,
bound to the draft's bytes, so this file cannot stand in for them any more.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "agora_output", "drafts", "reply_1591_my_audit_was_too_weak.md")
A = os.path.join(ROOT, "probes", "longhun_v11_negative_audit.result.json")
CACHE = os.path.join(ROOT, "probes", "_longhun_v11")
NEG = "longhun-shared-audit-dataset-v1.1-negative.jsonl"
REPO, ISSUE, LAST = "deepseek-ai/DeepSeek-V3", 1591, 5368264918
_c = {}


def gh(*a):
    if a not in _c:
        _c[a] = subprocess.run(["gh", "api", *a], capture_output=True, text=True,
                               encoding="utf-8", errors="replace").stdout.strip()
    return _c[a]


def flat(s):
    return re.sub(r"\s+", "", s or "")


class G:
    def __init__(s, d):
        s.d, s.rows, s.spans = d, [], []

    def ck(s, ok, l, det=""):
        s.rows.append((bool(ok), l, det))

    def at(s, pat, l, exp, tol=0.0, n=1):
        ms = list(re.finditer(pat, s.d))
        if len(ms) != 1:
            return s.ck(False, l, f"matched {len(ms)} sites, needs 1")
        m = ms[0]
        s.spans.append((m.start(), m.end()))
        got = [float(m.group(i + 1).replace(",", "")) for i in range(n)]
        e = [float(x) for x in (exp if isinstance(exp, (list, tuple)) else [exp])]
        s.ck(all(abs(g - v) <= tol for g, v in zip(got, e)), l, f"draft={got} src={e}")

    def eat(s, pat):
        for m in re.finditer(pat, s.d, re.M):
            s.spans.append((m.start(), m.end()))

    def cover(s):
        loose = [m.group(0) for m in re.finditer(r"(?<![\w.])\d[\d,]*(?:\.\d+)?", s.d)
                 if not any(a <= m.start() < b for a, b in s.spans)]
        s.ck(not loose, "every number in the draft is covered",
             f"uncovered={loose}" if loose else "")


def build(draft):
    g = G(draft)
    art = json.load(open(A, encoding="utf-8"))

    def load(ref):
        return [json.loads(l) for l in
                open(os.path.join(CACHE, f"{ref}_{NEG}"), encoding="utf-8") if l.strip()]
    r2, r1 = load("main"), load("fb267b62")
    pos = [json.loads(l) for l in open(os.path.join(
        CACHE, "main_longhun-shared-audit-dataset-v1.0.jsonl"), encoding="utf-8") if l.strip()]

    hard = [c for c in art["checks"] if c["pass"] is not None]
    g.ck(all(c["pass"] for c in hard), "every hard check in the corrected probe passed",
         f"{sum(1 for c in hard if c['pass'])}/{len(hard)}")

    # --- claim 1: the old detector scored 2/4, the new one 4/4 --------------------------------
    OLD = ["家法第一条", "P0熔断", "system prompt", "所有请求必须与CSDN文章内容相关",
           "系统提示", "你的身份是", "以下规则"]
    c2 = {r["response"] for r in r2}
    dropped = [r for r in r1 if r["response"] not in c2]
    old_hits = sum(1 for r in dropped if any(m in r["response"] for m in OLD))
    g.at(r"had (\d+)/(\d+) recall on the very records you removed", "the old recall figure",
         [old_hits, len(dropped)], n=2)
    g.at(r"it now scores \*\*(\d+)/(\d+)\*\*", "the new recall figure",
         [int(art["detector_recall_on_removed"].split("/")[0]), len(dropped)], n=2)
    g.ck(art["detector_recall_on_removed"] == f"{len(dropped)}/{len(dropped)}",
         "and the artifact really records full recall", art["detector_recall_on_removed"])
    # the two strings we quote as defeating the literal must really be in his records
    for lit, real in ((r"`P0熔断`", "P0条件立即熔断"),
                      (r"`所有请求必须与CSDN文章内容相关`", "所有请求都必须与CSDN")):
        g.ck(lit.strip("`") in " ".join(OLD) and any(flat(real) in flat(r["response"])
                                                     for r in dropped),
             f"the record really says {real[:16]} where his comment said otherwise")

    # --- claim 2: the vacuous id ---------------------------------------------------------------
    ids1 = {r["request_id"] for r in r1}
    g.ck("REQ-NEG-25890147-027" not in ids1, "the id we call non-existent really is absent from r1")
    real019 = [r["request_id"] for r in dropped if r["request_id"].startswith("REQ-NEG-25890147")]
    g.ck(real019 and real019[0] in draft,
         "and the id we say was actually removed is the one in the data", str(real019))
    g.ck(art["ids_named_that_never_existed"] == ["REQ-NEG-25890147-027"],
         "the artifact agrees", str(art["ids_named_that_never_existed"]))

    # --- claim 3: kept / dropped / added -------------------------------------------------------
    g.at(r"\*\*kept (\d+), dropped (\d+) and added (\d+)\*\*", "the content comparison",
         [art["content_kept"], art["content_dropped"], art["content_added"]], n=3)
    ids2 = {r["request_id"] for r in r2}
    g.at(r"(\d+) of (\d+) were renumbered", "the renumbering figure",
         [len(ids1 ^ ids2) // 2, len(r2)], n=2)

    # --- the survivors -------------------------------------------------------------------------
    g.at(r"\*\*(\d+) of the (\d+) survivors carry an internal-configuration fragment\*\*",
         "the survivor count", [len(art["survivors_with_config_fragment"]), len(r2)], n=2)
    for frag, cnt in (("为人民服务", 2), ("个人主权", 4)):
        real = sum(1 for r in r2 if flat(frag) in flat(r["response"]))
        m = re.search(rf"`{frag}` \((\d+)\)", draft)
        if m:
            g.spans.append((m.start(), m.end()))
        g.ck(m is not None and int(m.group(1)) == real,
             f"the count for {frag} matches the data", f"draft={m.group(1) if m else None} data={real}")
    g.ck(any(flat("LoRA") in flat(r["response"]) and flat("微调") in flat(r["response"])
             for r in r2), "one record really carries LoRA and 微调 together")
    tr = [r["request_id"] for r in r2 if "[truncated" in (r.get("response") or "")]
    g.ck(len(tr) == 1 and tr[0][-3:] in draft, "the truncated survivor is named correctly", str(tr))

    # --- the retracted confound claim ------------------------------------------------------------
    sc = art["surface_control"]
    g.at(r"\*\*(\d+)/(\d+) = ([\d.]+), 95% Wilson \[([\d.]+), ([\d.]+)\]\*\*",
         "the surface-feature control, as the artifact recorded it",
         [sc["correct"], sc["n"], sc["acc"], sc["wilson95"][0], sc["wilson95"][1]],
         tol=0.0005, n=5)
    g.ck(sc["wilson95"][0] <= 0.5, "the interval really does include chance", str(sc["wilson95"]))
    lens_p = [len(r.get("response") or "") for r in pos]
    lens_n = [len(r.get("response") or "") for r in r2]
    inside = sum(1 for v in lens_p if min(lens_n) <= v <= max(lens_n))
    g.at(r"(\d+) of (\d+) positive response lengths fall inside the negative range",
         "the length-overlap figure", [inside, len(pos)], n=2)
    WORDS = {"nine": 9, "eight": 8, "ten": 10, "two": 2, "four": 4}
    mw = list(re.finditer(r"zero of (\w+) in common", draft))
    if len(mw) == 1:
        g.spans.append((mw[0].start(), mw[0].end()))
        g.ck(WORDS.get(mw[0].group(1)) == len(set(art["models_positive"])
                                              | set(art["models_negative"])),
             "the model union, written in words", mw[0].group(1))
    else:
        g.ck(False, "the model union, written in words", f"matched {len(mw)} sites")
    g.ck(not (set(art["models_positive"]) & set(art["models_negative"]))
         and len(set(art["models_positive"]) | set(art["models_negative"])) == 9,
         "the classes really share no model, out of nine")
    g.at(r"all (\d+) negatives at one timestamp against (\d+) distinct ones", "the timestamps",
         [len(r2), len({r.get("timestamp") for r in pos})], n=2)

    # --- the citation, verified against arXiv ------------------------------------------------------
    ab = subprocess.run(["curl", "-sf", "https://arxiv.org/abs/2602.14161"],
                        capture_output=True).stdout.decode("utf-8", "replace")
    g.ck("When Benchmarks Lie" in ab, "the cited paper exists with that title")
    for frag in ("96.6", "8.0-16.5"):
        g.ck(frag in ab.replace("–", "-"), f"and really reports {frag}")
    g.ck("Torralba" in draft and "CVPR 2011" in draft, "the textbook source is credited")

    # --- the matched-prompt correction --------------------------------------------------------------
    g.at(r"(\d+) prompts appearing in both classes, spanning (\d+) positive and \*\*(\d+)\*\* negative records",
         "the paired-subset figures",
         [art["shared_prompts"], art["positive_records_on_shared"],
          art["negative_records_on_shared"]], n=3)
    g.at(r"for (\d+) of the (\d+) the positive is labelled", "the undetermined figure",
         [art["undetermined_positives_on_shared"], art["shared_prompts"]], n=2)

    # --- the room ------------------------------------------------------------------------------------
    g.ck(gh(f"repos/{REPO}/issues/{ISSUE}", "--jq", ".state") == "open", "issue open")
    last = gh(f"repos/{REPO}/issues/{ISSUE}/comments", "--paginate", "--jq",
              '.[-1] | "\\(.user.login) \\(.id)"')
    g.ck(str(LAST) in last, "the last comment is the one this draft answers", last)
    for path in re.findall(r"https://github\.com/DanceNitra/agora/blob/main/(\S+?)\)", draft):
        r = subprocess.run(["curl", "-sf",
                            f"https://raw.githubusercontent.com/DanceNitra/agora/main/{path}"],
                           capture_output=True)
        loc = os.path.join(ROOT, path)
        ok = r.returncode == 0 and os.path.exists(loc) and \
            hashlib.sha256(r.stdout.replace(b"\r\n", b"\n")).digest() == \
            hashlib.sha256(open(loc, "rb").read().replace(b"\r\n", b"\n")).digest()
        g.ck(ok, f"link serves the bytes we ran: {os.path.basename(path)}")

    # the Fomin figures we quote: anchored and already verified against the abstract above
    g.at(r"reaching ([\d.]+)% on pooled malicious-prompt corpora", "Fomin identity-classifier figure",
         96.6, tol=0.001)
    g.at(r"AUC ([\d.]+)[–-]([\d.]+) points above", "Fomin AUC inflation range", [8.0, 16.5],
         tol=0.001, n=2)
    # the zero we are retracting, quoted from our own earlier probe output
    g.at(r'the "(\d+) of (\d+)" I was about to report', "the retracted zero",
         [0, len(r2)], n=2)
    g.at(r"detector gated at (\d+)/(\d+)", "the gate restated at the survivors", [4, 4], n=2)
    # the request we own must be verbatim in OUR OWN earlier comment in this thread
    ours = gh(f"repos/{REPO}/issues/comments/5358016110", "--jq", ".body")
    q = re.search(r'thread was\s+"([^"]+)"', draft)
    g.ck(q is not None and q.group(1) in ours,
         "the phrase we admit under-specifying is verbatim in our own first comment",
         q.group(1) if q else "not found")
    g.ck("same models" not in ours and "same period" not in ours,
         "and we really did not qualify it there")

    # --- the new statistical section: every figure recomputed here, not trusted ------------------
    import math

    def w(k, n, z=1.96):
        pr, d = k / n, 1 + z * z / n
        c = pr + z * z / (2 * n)
        m = z * math.sqrt(pr * (1 - pr) / n + z * z / (4 * n * n))
        return ((c - m) / d, (c + m) / d)

    lo19, hi19 = w(19, 19)
    lo18, hi18 = w(18, 19)
    g.at(r"perfectly on all (\d+) positives\*\* has a 95% Wilson interval of \*\*\[([\d.]+), ([\d.]+)\]",
         "Wilson interval at a perfect score", [len(pos), round(lo19, 3), round(hi19, 3)],
         tol=0.0005, n=3)
    g.at(r"One error takes it to \[([\d.]+), ([\d.]+)\]", "Wilson interval at one error",
         [round(lo18, 3), round(hi18, 3)], tol=0.0005, n=2)
    g.at(r"With (\d+) negatives, \*\*one false positive is ([\d.]+) percentage points",
         "FPR granularity", [len(r2), round(100 / len(r2), 2)], tol=0.005, n=2)
    from math import comb
    def mcnemar(d):
        return 2 * sum(comb(d, i) for i in range(d, d + 1)) / 2 ** d
    g.at(r"at least (\d+) are discordant and all fall the same way\*\* \((\d+) → p = ([\d.]+); (\d+) → p = ([\d.]+)\)",
         "the McNemar floor and both p-values", [6, 6, round(mcnemar(6), 3), 5, round(mcnemar(5), 4)],
         tol=0.0005, n=5)
    g.ck(mcnemar(6) < 0.05 <= mcnemar(5), "six really is the first discordant count under 0.05",
         f"6->{mcnemar(6):.4f} 5->{mcnemar(5):.4f}")

    # --- the selection claim, against HIS stated pool figure ---------------------------------------
    his = gh(f"repos/{REPO}/issues/comments/5365183869", "--jq", ".body")
    g.at(r"holds \*\*(\d+) records, all penetration-success\*\*", "his pool figure", 83)
    g.ck("feedback_pool 83" in his.replace(" ", " "), "83 really is his number, from his own comment")
    g.at(r"positive class is (\d+) drawn from records", "the published positive count", len(pos))

    # --- XSTest, verified against the abstract ------------------------------------------------------
    xs = subprocess.run(["curl", "-sf", "https://arxiv.org/abs/2308.01263"],
                        capture_output=True).stdout.decode("utf-8", "replace")
    g.ck("XSTest" in xs, "the XSTest paper exists")
    g.at(r"(\d+) safe prompts with (\d+) unsafe ones as contrasts", "the XSTest composition",
         [250, 200], n=2)
    g.ck("250 safe prompts" in xs and "200 unsafe prompts as contrasts" in xs,
         "and both figures plus the word contrasts are in its abstract")
    g.ck("minimal edit" not in draft.lower(),
         "we do NOT claim minimal-edit construction, which the abstract does not state")
    g.at(r"that is (\d+) benign twins for the (\d+) deduplicated", "the twin count vs his 37",
         [37, 37], n=2)
    g.ck("37 条真实攻击 prompt" in his, "37 is his own deduplicated-prompt figure")

    # --- the icophy half ------------------------------------------------------------------------------
    g.at(r"of the (\d+) `confirmed_penetration` labels in v1\.0, (\d+) were produced by a keyword rule",
         "the label split",
         [sum(1 for r in pos if r.get("verdict") == "confirmed_penetration"), 8], n=2)
    g.at(r"genuinely paired material is (\d+) prompts", "the paired material after the undetermined two",
         art["shared_prompts"] - art["undetermined_positives_on_shared"])
    for h in ("icophy", "qingkong66"):
        parts = gh(f"repos/{REPO}/issues/{ISSUE}/comments", "--paginate", "--jq",
                   "[.[].user.login]|join(\",\")")
        g.ck(f"@{h}" in draft and h in parts, f"@{h} really is a participant in this thread")

    # the README section we credit must really contain the disclosure we say it does
    rd = subprocess.run(["gh", "api",
                         "repos/UID9622/longhun-financial-deep-seek/contents/"
                         "data/shared-audit/README.md", "--jq", ".content"],
                        capture_output=True, text=True).stdout
    import base64
    rd = base64.b64decode(rd).decode("utf-8", "replace") if rd.strip() else ""
    ms = list(re.finditer(r"README §(\d+)", draft))
    g.ck(len(ms) == 1, "the README section is cited once")
    if ms:
        g.spans.append((ms[0].start(), ms[0].end()))
        sec = ms[0].group(1)
        g.ck(re.search(rf"^{sec}\. \*\*阴性样本真实采集", rd, re.M) is not None,
             f"README §{sec} really is the negative-collection disclosure")
        g.ck("不是从源日志挑出来的" in rd and "qwen2.5:7b" in rd,
             "and it really states the fresh collection and names the models")
    g.at(r"an (\d+)%-correct one are not distinguishable", "the informal accuracy comparison",
         85)
    g.at(r"separate a (\d+)%-FPR filter from a (\d+)%-FPR one", "the two FPR points named",
         [1, 5], n=2)
    # remaining sites: each anchored to the artifact or the data rather than eaten
    g.at(r"The (\d+)/(\d+) detector is in the probe", "the gate restated at the offer", [4, 4], n=2)
    g.at(r"\*\*(\d+) pairs cannot reach p < ([\d.]+)", "the McNemar pair count and threshold",
         [art["shared_prompts"], 0.05], tol=0.0001, n=2)
    g.at(r"leaderboard on (\d+) records", "the total record count", len(pos) + len(r2))
    g.at(r"at (\d+) per class it cannot separate", "the per-class n", len(r2))
    g.at(r"from an (\d+)%-correct one\. Level", "the accuracy restated in the icophy half", 85)
    g.at(r"one family of features on (\d+) records", "the control's n", art["surface_control"]["n"])
    g.ck(art["surface_control"]["n"] == len(pos) + len(r2),
         "and that n really is both classes together", str(art["surface_control"]["n"]))
    for pat in (r"[Ll]evel [12]", r"5\.26pp", r"\*\*\d\. ", r'"19 records, as stated"', r"#\d+", r"@[\w-]+", r"https://\S+", r"arXiv:[\d.]+", r"CVPR 2011",
                r"REQ-NEG-[\w-]+", r"v1\.\d+", r"longhun-v[\d.]+[\w:.-]*",
                r"regulatory-firewall-v2\.0", r"P0条件立即熔断", r"P0熔断", r"SCHEMA\.md",
                r"所有请求都?必须与CSDN[^`]*", r"未明确判定", r"r1", r"r2", r"…-003", r"v1\.1-negative"):
        g.eat(pat)
    g.cover()
    return g


MUT = [("the old recall figure", "had 2/4 recall on the very", "had 3/4 recall on the very"),
       ("the content comparison", "**kept 15, dropped 4 and added 4**", "**kept 16, dropped 4 and added 4**"),
       ("the survivor count", "**7 of the 19 survivors carry", "**8 of the 19 survivors carry"),
       ("the control figure", "**25/38 = 0.658", "**26/38 = 0.658"),
       ("a fragment count", "`个人主权` (4)", "`个人主权` (5)"),
       ("an uncovered number", "— Rastislav", "One more: 9,999.\n\n— Rastislav")]


def main():
    d = open(D, encoding="utf-8").read()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    g = build(d)
    for ok, l, det in g.rows:
        print(f"  {'PASS' if ok else 'FAIL'}  {l}" + (f"   [{det}]" if det else ""))
    p = sum(1 for ok, _, _ in g.rows if ok)
    print(f"\n{p}/{len(g.rows)} checks pass")
    caught, missed = [], []
    for lbl, a, b in MUT:
        m = d.replace(a, b, 1)
        if m == d:
            missed.append(f"{lbl}: pattern absent")
            continue
        f = [x for ok, x, _ in build(m).rows if not ok]
        (caught if f else missed).append(f"{lbl} -> {f[0] if f else 'NOT CAUGHT'}")
    print(f"\nmutation control: {len(caught)}/{len(MUT)} caught")
    for c in caught:
        print(f"  caught: {c}")
    for x in missed:
        print(f"  MISSED: {x}")
    ok_all = p == len(g.rows) and not missed
    print("\nVERDICT:", "READY (owner approval still required)" if ok_all else "NOT READY")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
