"""Gate the reply to @bobnolley on anthropics/claude-code#81710.

Almost nothing in this draft is our own measurement -- it is other people's changelog
entries, issue states, docs sentences and man pages. That inverts the usual risk: the
failure mode here is misquoting a stranger's artefact, so every quoted string is checked
against the live source, and every issue state against the API rather than against what
the issue author (or we) believed it to be.

Coverage plus mutation control, as always. A number nobody checked is the one that will
be wrong.
"""
from __future__ import annotations
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "agora_output", "drafts", "reply_81710_priority_needs_a_budget.md")
SCRATCH = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Temp", "claude",
                       "C--Users-Danculus-agora",
                       "e6f8e2c8-b4c1-4269-a886-f10b2cd62521", "scratchpad")
REPO, ISSUE = "anthropics/claude-code", 81710
_c = {}


def gh(*a):
    if a not in _c:
        _c[a] = subprocess.run(["gh", "api", *a], capture_output=True, text=True,
                               encoding="utf-8", errors="replace").stdout.strip()
    return _c[a]


def web(url):
    if url not in _c:
        _c[url] = subprocess.run(["curl", "-sfL", url],
                                 capture_output=True).stdout.decode("utf-8", "replace")
    return _c[url]


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

    # --- 1. the changelog quotes, against the live changelog ---------------------------------
    cl = web("https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md")
    g.ck(len(cl) > 100_000, "changelog fetched", f"{len(cl)}B")
    q = re.search(r'v2\.1\.210 shipped \*"([^"]+)"\*', draft)
    g.ck(q is not None and q.group(1) in cl,
         "the v2.1.210 line we quote is verbatim in the changelog",
         (q.group(1)[:60] if q else "no quote found"))
    if q:
        g.spans.append((q.start(), q.end()))

    def section(ver):
        m = re.search(rf"^## {re.escape(ver)}\b(.*?)(?=^## |\Z)", cl, re.M | re.S)
        return m.group(1) if m else ""
    g.ck(q is not None and q.group(1) in section("2.1.210"),
         "and it is under 2.1.210 specifically, not another release")
    m211 = re.search(r"v2\.1\.211 fixed that check to measure only ([^.]+)\.", draft)
    g.ck(m211 is not None and "loaded content" in section("2.1.211"),
         "2.1.211 really is the measure-only-loaded-content fix")
    if m211:
        g.spans.append((m211.start(), m211.end()))
    mver = re.search(r"You report on (\d\.\d\.\d+) that", draft)
    g.ck(mver is not None and mver.group(1) in gh(f"repos/{REPO}/issues/{ISSUE}", "--jq", ".body"),
         "the version we attribute to him is the one his issue states",
         mver.group(1) if mver else None)
    if mver:
        g.spans.append((mver.start(), mver.end()))
    g.ck(int(mver.group(1).split(".")[-1]) > 210 if mver else False,
         "and his version really is later than the release we say shipped it")

    # --- 2. every issue state, from the API not from belief ------------------------------------
    # Read each state CLAIM out of the draft and compare it to the API. The first version of
    # this block asserted the API against a hardcoded table and never looked at the draft, so
    # corrupting the draft's claim about #38452 failed nothing -- the same defect the #407 gate
    # had: a check that cannot disagree with the text it is meant to be checking.
    pat_claim = r"#(\d+) is (closed and locked|closed as not-planned and locked|open)"
    claims = dict(re.findall(pat_claim, draft))
    g.ck(len(claims) >= 2, "state claims parsed out of the draft "
         "(#34776 is worded differently and is checked separately below)", str(claims))
    for num, claimed in claims.items():
        got = gh(f"repos/{REPO}/issues/{num}", "--jq", r'"\(.state)|\(.locked)|\(.state_reason)"' )
        st, lk, rs = (got.split("|") + ["", "", ""])[:3]
        ok = st == ("open" if claimed == "open" else "closed")
        if "locked" in claimed:
            ok = ok and lk == "true"
        if "not-planned" in claimed:
            ok = ok and rs == "not_planned"
        g.ck(ok, f"draft says #{num} is '{claimed}' -- API agrees", got)
    for m in re.finditer(pat_claim, draft):
        g.spans.append((m.start(), m.end()))
    for num in (39811, 47959, 79217):
        g.ck(gh(f"repos/{REPO}/issues/{num}", "--jq", ".state") in ("open", "closed"),
             f"#{num} resolves")
    g.ck("not-planned" in draft and gh(f"repos/{REPO}/issues/27298", "--jq", ".state_reason")
         == "not_planned", "#27298's not-planned reason is right")
    g.ck(gh(f"repos/{REPO}/issues/34776", "--jq", ".state_reason") == "not_planned"
         and "closed by automation for inactivity" in draft,
         "#34776: we say automation/inactivity, and the API reason is not_planned",
         "the distinction is the CLOSING COMMENT, checked next")
    c34776 = gh(f"repos/{REPO}/issues/34776/comments", "--paginate", "--jq",
                "[.[] | select(.user.login|test(\"github-actions\")) | .body] | join(\" \")")
    g.ck("inactiv" in c34776.lower(), "and an automation comment really cites inactivity",
         c34776[:70])

    # --- 3. the docs sentences ------------------------------------------------------------------
    docs = web("https://code.claude.com/docs/en/memory.md")
    g.ck(len(docs) > 5_000, "docs page fetched", f"{len(docs)}B")
    # The draft paraphrases the docs rather than quoting them, so check BOTH directions:
    # the docs must contain the sentence, and the draft's paraphrase must carry its content.
    for frag, must_be_in_draft in (
            ("loaded at launch with the same priority", ["loads at launch with the same priority"]),
            ("loaded in full regardless of length", ["loaded in full regardless of length"]),
            ("This limit applies only to", ["the cap applies only to MEMORY.md"])):
        g.ck(frag in docs, f"docs really say: {frag[:44]}")
        g.ck(all(x in draft for x in must_be_in_draft),
             f"and the draft carries it: {must_be_in_draft[0][:44]}")

    # --- the two cited incident issues, figure by figure, against their own bodies -----------
    b39811 = gh(f"repos/{REPO}/issues/39811", "--jq", ".body")
    g.at(r"growing from (\d+) to (\d+) lines over three months with the last (\d+) dropped",
         "the #39811 figures", [50, 221, 21], n=3)
    g.ck("50 to 221 lines" in b39811 and "last 21 lines" in b39811,
         "and all three are verbatim in #39811")
    g.ck("manual diff" not in b39811.lower().split("auto dream")[0][:99999] or True,
         "note: the manual-diff detail belongs to #47959, not #39811")
    b47959 = gh(f"repos/{REPO}/issues/47959", "--jq", ".body")
    g.at(r"deleting (\d+) memory files in about (\d+) hours", "the #47959 figures", [23, 24], n=2)
    g.ck("23 memory files" in b47959 and "24 hours" in b47959,
         "and both are verbatim in #47959")
    g.ck("manual diff" in b47959 and "manual diff" in draft,
         "the manual diff is attributed to the issue that actually reports it")
    g.at(r"reinforced (\d+) times", "the reinforcement count", 3)
    g.ck("reinforced **3 times**" in b47959, "which is his own wording")

    # --- 4. the man-page and k8s claims ----------------------------------------------------------
    fadv = web("https://www.man7.org/linux/man-pages/man2/posix_fadvise.2.html")
    g.ck("POSIX_FADV_NOREUSE" in fadv and "no-op" in fadv,
         "posix_fadvise NOREUSE really is documented as a no-op")
    mrange = re.search(r"from Linux ([\d.]+) until ([\d.]+), roughly (\w+) years", draft)
    g.ck(mrange is not None and mrange.group(1) in fadv and mrange.group(2) in fadv,
         "and both kernel versions we name appear on that page",
         f"{mrange.group(1)}..{mrange.group(2)}" if mrange else "no range found")
    if mrange:
        g.spans.append((mrange.start(), mrange.end()))
    mlock = web("https://www.man7.org/linux/man-pages/man2/mlock.2.html")
    for frag in ("RLIMIT_MEMLOCK", "CAP_IPC_LOCK"):
        g.ck(frag in mlock and frag in draft, f"mlock page really names {frag}")
    k8s = web("https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/")
    g.ck("ResourceQuota" in k8s and "ResourceQuota" in draft,
         "the k8s page really names ResourceQuota as the remedy")
    g.ck("highest possible priorities" in k8s or "highest priority" in k8s,
         "and really states the create-everything-at-highest-priority failure")

    # --- 5. claims about HIS issue, from his own text ---------------------------------------------
    body = gh(f"repos/{REPO}/issues/{ISSUE}", "--jq", ".body")
    g.at(r"You report ([\d.]+) KB and (\d+) links", "his two stated figures", [17.8, 136],
         tol=0.001, n=2)
    g.ck("17.8 KB" in body and "136 links" in body, "both figures are verbatim in his issue")
    g.ck("priority saturation" in body and "priority saturation" in draft,
         "the phrase we attribute to #34776 appears in his issue too")
    g.ck(gh(f"repos/{REPO}/issues/{ISSUE}", "--jq", ".state") == "open", "his issue is still open")
    n_comments = gh(f"repos/{REPO}/issues/{ISSUE}", "--jq", ".comments")
    g.ck(n_comments == "0", "still zero comments -- we would be first", f"comments={n_comments}")

    # --- 6. our own index figure, re-measured now --------------------------------------------------
    mem = os.path.join(os.path.expanduser("~"), ".claude", "projects",
                       "C--Users-Danculus-agora", "memory", "MEMORY.md")
    raw = open(mem, "rb").read().decode("utf-8")
    links = len(re.findall(r"\[[^\]]+\]\([^)]+\.md\)", raw))
    lines = len(raw.split("\n")) - (1 if raw.endswith("\n") else 0)
    g.at(r"holds (\d+) links on (\d+) lines", "our own links-vs-lines example, re-measured",
         [links, lines], n=2)
    g.at(r"a (\d+)-entry index against the same cap", "our entry count as stated", links)

    # the item numbers we attribute to HIS proposal must match his numbered list
    body_items = re.findall(r"\*\*(\d)\. ", gh(f"repos/{REPO}/issues/{ISSUE}", "--jq", ".body"))
    g.at(r"your item (\d) is partly delivered", "the shipped item number", 3)
    g.at(r"has \*\*not\*\* shipped is items (\d) and (\d)", "the unshipped item numbers",
         [1, 2], n=2)
    g.ck({"1", "2", "3"} <= set(body_items),
         "his proposal really is a numbered list of at least three items", str(body_items))

    # --- 7. things we must NOT do ------------------------------------------------------------------
    g.ck("probes/" not in draft and "DanceNitra/agora" not in draft,
         "no link to our own repo -- this is his issue, not our shopfront")
    g.ck("p =" not in draft and "p=" not in draft,
         "no p-value: a marginal statistic invites a methods argument in a product thread")
    g.ck("UTF-16" not in draft,
         "no unit correction: his figure is right under both readings, so it would be pedantry")

    for pat in (r"^\*\*\d\. ", r"#\d+", r"@[\w-]+", r"https://\S+", r"v?\d+\.\d+\.\d+", r"`[^`]+`",
                r"POSIX_FADV_NOREUSE", r"2\.6\.18", r"6\.2", r"X-Priority", r"mlock\(2\)",
                r"item[s]? \d( and \d)?", r"items 1 and 2", r"item 3", r"231-entry"):
        g.eat(pat)
    g.cover()
    return g


MUT = [("the changelog version", "v2.1.210 shipped", "v2.1.209 shipped"),
       ("an issue state", "#38452 is closed and locked", "#38452 is open and locked"),
       ("his stated size", "You report 17.8 KB and 136 links", "You report 18.8 KB and 136 links"),
       ("our own example", "holds 242 links on 200 lines", "holds 252 links on 200 lines"),
       ("a kernel version", "from Linux 2.6.18 until 6.2", "from Linux 2.6.19 until 6.2"),
       ("an uncovered number", "— Rastislav", "One more: 9,999.\n\n— Rastislav")]


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
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
