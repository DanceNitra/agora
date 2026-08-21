"""Gate the v1.1-negative reply on deepseek-ai/DeepSeek-V3#1591.

Every figure is read OUT of the draft and compared against the audit artifact or the live
data files, never against the draft's own assertion. Claims about other people's records
are checked against the published dataset. Coverage requires every number be consumed by
a check; the mutation control requires the gate to fail on single-value corruptions.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "agora_output", "drafts", "reply_1591_v11_negative_audit.md")
A = os.path.join(ROOT, "probes", "longhun_v11_negative_audit.result.json")
CACHE = os.path.join(ROOT, "probes", "_longhun_v11")
REPO, ISSUE, LAST = "deepseek-ai/DeepSeek-V3", 1591, 5367092050
TOKEN = "可以"
_c = {}


def gh(*a):
    if a not in _c:
        _c[a] = subprocess.run(["gh", "api", *a], capture_output=True, text=True,
                               encoding="utf-8", errors="replace").stdout.strip()
    return _c[a]


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
        # A digit glued to letters (F1, r2, v4) is a NAME, not a quoted figure. Coverage
        # is about numbers a reader would check, so require a boundary before the digit.
        loose = [m.group(0) for m in re.finditer(r"(?<![\w.])\d[\d,]*(?:\.\d+)?", s.d)
                 if not any(a <= m.start() < b for a, b in s.spans)]
        s.ck(not loose, "every number in the draft is covered",
             f"uncovered={loose}" if loose else "")


def build(draft):
    g = G(draft)
    art = json.load(open(A, encoding="utf-8"))
    def load(n):
        p = os.path.join(CACHE, n)
        return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
    neg = load("longhun-shared-audit-dataset-v1.1-negative.jsonl")
    pos = load("longhun-shared-audit-dataset-v1.0.jsonl")

    real = [c for c in art["checks"] if not c["label"].startswith("MEASUREMENT")]
    g.ck(all(c["pass"] for c in real), "every non-measurement check in the audit passed",
         f"{sum(1 for c in real if c['pass'])}/{len(real)}")
    g.at(r"(\d+) records, all `verdict=rejected`", "record count", art["records"])
    g.at(r"exactly the (\d+) declared fields", "field count", len(set(neg[0])))
    g.ck(art["sha256"][:8] in draft, "the sha prefix quoted is the audited one", art["sha256"][:8])
    g.ck("b78c9509" in draft, "the retracted hash is named so a reader can tell them apart")
    g.ck(not art["leak_marker_hits"], "the artifact really found zero leak markers",
         str(art["leak_marker_hits"]))
    g.ck(not art["removed_ids_still_present"], "the four removed ids really are absent")
    g.at(r"`dna_sig` repeats (\d+) distinct over (\d+)", "dna figures",
         [art["dna_distinct"], art["records"]], n=2)

    pm, nm = sorted({r.get("model") for r in pos}), sorted({r["model"] for r in neg})
    for name, ms in (("positive", pm), ("negative", nm)):
        row = re.search(rf"\| {name} \(v1\.[01]\) \| (.+?) \|", draft)
        g.ck(row is not None, f"{name} model row present")
        if row:
            g.spans.append((row.start(), row.end()))
            quoted = set(re.findall(r"`([^`]+)`", row.group(1)))
            g.ck(quoted == set(ms), f"{name} row lists exactly the models in the file",
                 f"draft={sorted(quoted)} file={ms}")
    g.ck(not (set(pm) & set(nm)), "the two classes really share no model", str(set(pm) & set(nm)))
    n_conf = sum(1 for r in pos if r.get("verdict") == "confirmed_penetration")
    WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
             "eight": 8, "nine": 9, "ten": 10, "eighteen": 18, "nineteen": 19}
    def word_at(pat, label, expected):
        ms = list(re.finditer(pat, draft))
        if len(ms) != 1:
            return g.ck(False, label, f"matched {len(ms)} sites, needs 1")
        g.spans.append((ms[0].start(), ms[0].end()))
        got = [WORDS.get(x.lower()) for x in ms[0].groups()]
        g.ck(got == list(expected), label, f"draft={got} src={list(expected)}")

    word_at(r"Zero of (\w+) in common", "the union size, written in words",
            [len(set(pm) | set(nm))])
    g.at(r"(\d+) of the (\d+) positive attack prompts reappear", "matched-prompt figures",
         [art["prompts_in_both_classes"], len({r.get("prompt") for r in pos})], n=2)
    g.at(r"F1 over the full (\d+) \+ (\d+)", "class sizes named", [len(pos), len(neg)], n=2)

    word_at(r"of the (\w+) labels in v1\.0, (\w+) were produced by a keyword rule",
            "the label split, written in words", [n_conf, 8])
    g.ck(n_conf == 18, "the positive class really carries 18 confirmed labels", str(n_conf))
    kw = [r for r in pos if TOKEN in (r.get("response") or "")]
    g.ck(len(kw) >= 8, "the token really appears in at least eight positive responses",
         f"{len(kw)} of {len(pos)}")
    g.ck(min(len(r.get("response") or "") for r in kw) <= 8,
         "and one of them really is six characters or fewer",
         str(min(len(r.get("response") or "") for r in kw)))

    g.ck(gh(f"repos/{REPO}/issues/{ISSUE}", "--jq", ".state") == "open", "issue open")
    last = gh(f"repos/{REPO}/issues/{ISSUE}/comments", "--paginate", "--jq",
              '.[-1] | "\\(.user.login) \\(.id)"')
    g.ck(str(LAST) in last, "icophy still speaks last -- this replies, not interrupts", last)
    parts = gh(f"repos/{REPO}/issues/{ISSUE}/comments", "--paginate", "--jq",
               "[.[].user.login]|join(\",\")")
    for h in ("UID9622", "icophy"):
        g.ck(f"@{h}" in draft and h in parts, f"@{h} really is a participant in this thread")

    for path in re.findall(r"https://github\.com/DanceNitra/agora/blob/main/(\S+?)\)", draft):
        r = subprocess.run(["curl", "-sf",
                            f"https://raw.githubusercontent.com/DanceNitra/agora/main/{path}"],
                           capture_output=True)
        loc = os.path.join(ROOT, path)
        ok = r.returncode == 0 and os.path.exists(loc) and \
            hashlib.sha256(r.stdout.replace(b"\r\n", b"\n")).digest() == \
            hashlib.sha256(open(loc, "rb").read().replace(b"\r\n", b"\n")).digest()
        g.ck(ok, f"link serves the bytes we ran: {os.path.basename(path)}")

    for pat in (r"#\d+", r"@[\w-]+", r"https://\S+", r"v1\.\d+", r"v4[\d.]*", r"156d3ebb",
                r"b78c9509", r"SHA-256", r"qwen2\.5:7b", r"deepseek-r1:7b",
                r"longhun-v[\d.]+[\w:.-]*", r"regulatory-firewall-v2\.0", r"SCHEMA §\d+",
                r"P0熔断", r"家法第一条", r"…-\d+", r"11 declared", r"19 \+ 19", r"v42-sys", r"F1", r"r2", r"v1\.1-negative"):
        g.eat(pat)
    g.cover()
    return g


MUT = [("the matched-prompt count", "8 of the 19 positive attack prompts",
        "9 of the 19 positive attack prompts"),
       ("a model in the table", "`longhun-v1.7:latest`", "`longhun-v1.9:latest`"),
       ("the union size", "Zero of nine in common", "Zero of ten in common"),
       ("the dna figures", "repeats 12 distinct over 19", "repeats 13 distinct over 19"),
       ("an uncovered number", "— Rastislav", "One more: 9,999.\n\n— Rastislav")]


def main():
    d = open(D, encoding="utf-8").read()
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
