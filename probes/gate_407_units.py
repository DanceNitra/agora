"""Gate the reply to @pjt222 on pjt222/agent-almanac#407.

Same design as the #82056 gate, for the same reasons: nothing asserts that the draft SAYS
something -- every check reads a value OUT of the draft and compares it against a source
the draft did not write. Every claim is anchored to one site. Coverage requires that every
number in the draft be consumed by a check or named as a reference.

The extra risk here is that the draft quotes ANOTHER PERSON'S issue and code back at him.
Those quotations are checked against the live issue body with whitespace normalised, and a
paraphrase that drifts is a failure, not a rounding.
"""
from __future__ import annotations
import hashlib, json, os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "agora_output", "drafts", "reply_agent_almanac_407_units.md")
P = lambda n: os.path.join(ROOT, "probes", n)  # noqa: E731
REPO, ISSUE = "pjt222/agent-almanac", 407
MIRROR = ("https://raw.githubusercontent.com/chauncygu/collection-claude-code-source-code/"
          "b934603b2800374b315b25061bbeffb40ab6ab26/original-source-code/src/memdir/memdir.ts")
_c: dict = {}


def gh(*a):
    if a not in _c:
        _c[a] = subprocess.run(["gh", "api", *a], capture_output=True, text=True,
                               encoding="utf-8", errors="replace").stdout.strip()
    return _c[a]


def ws(s):
    return re.sub(r"\s+", " ", s).strip()


class G:
    def __init__(s, d):
        s.d, s.rows, s.spans = d, [], []

    def ck(s, ok, label, detail=""):
        s.rows.append((bool(ok), label, detail))

    def at(s, pat, label, exp, tol=0.0, n=1):
        ms = list(re.finditer(pat, s.d))
        if len(ms) != 1:
            return s.ck(False, label, f"matched {len(ms)} sites, needs 1")
        m = ms[0]
        s.spans.append((m.start(), m.end()))
        got = [float(m.group(i + 1).replace(",", "")) for i in range(n)]
        e = [float(x) for x in (exp if isinstance(exp, (list, tuple)) else [exp])]
        s.ck(len(got) == len(e) and all(abs(g - v) <= tol for g, v in zip(got, e)),
             label, f"draft={got} source={e}")

    def eat(s, pat):
        for m in re.finditer(pat, s.d, re.M):
            s.spans.append((m.start(), m.end()))

    def cover(s):
        loose = [m.group(0) for m in re.finditer(r"\d[\d,]*(?:\.\d+)?", s.d)
                 if not any(a <= m.start() < b for a, b in s.spans)]
        s.ck(not loose, "every number in the draft is covered",
             f"uncovered={loose}" if loose else "")


def build(draft):
    g = G(draft)
    uj = json.load(open(P("is_the_cap_counted_in_bytes_or_utf16_units.result.json"), encoding="utf-8"))
    unit, uv = {r["label"]: r for r in uj["rows"]}, uj["verdicts"]
    hj = json.load(open(P("what_the_unit_hedge_costs_a_checker.result.json"), encoding="utf-8"))
    hedge, hv = {r["fixture"]: r for r in hj["rows"]}, hj["verdicts"]

    # --- the unit table -------------------------------------------------------------------
    for lbl, k in ((r"ASCII `x`", "ascii_200x125"), (r"CJK `中`", "cjk_200x125"),
                   (r"emoji `😀`", "emoji_200x125")):
        r = unit[k]
        g.at(rf"\| {lbl} \| \*?\*?([\d,]+)\*?\*? \| ([\d,]+) \| \*?\*?([\d,]+)\*?\*? \| \*?\*?(\d+)\*?\*? \|",
             f"unit table: {k}",
             [r["bytes"], r["code_points"], r["utf16_units"], r["last_line_loaded"]], n=4)
    g.ck(all(uv.values()), "unit probe's own controls passed", str(uv))
    g.at(r"is ([\d.]+)× the bytes of the ASCII one", "the CJK/ASCII byte ratio",
         round(unit["cjk_200x125"]["bytes"] / unit["ascii_200x125"]["bytes"], 1), tol=0.05)
    g.at(r"cuts (\d+) lines earlier", "emoji/CJK gap",
         unit["cjk_200x125"]["last_line_loaded"] - unit["emoji_200x125"]["last_line_loaded"])
    g.at(r"`([\d.]+)KB` over a file that is ([\d,]+) bytes", "the warning's KB vs the file",
         [round(unit["cjk_200x125"]["utf16_units"] / 1024, 1), unit["cjk_200x125"]["bytes"]],
         tol=0.05, n=2)

    # --- the hedge table ------------------------------------------------------------------
    for lbl, k in (("ASCII", "ascii_200x125"), ("CJK", "cjk_200x125"), ("emoji", "emoji_200x125")):
        r = hedge[k]
        g.at(rf"\| {lbl} \| ([\d.]+) \| ([\d.]+) \| \*?\*?([\d.]+)×\*?\*? \| (\d+) \| \*?\*?(\d+)\*?\*? \|",
             f"hedge table: {k}",
             [r["usage_407"], r["usage_true"], r["over_report_x"], r["pred_lines_407"],
              r["measured_last_line"]], tol=0.005, n=5)
    g.at(r"reports (\d+)% of cap against a real (\d+)%", "the CJK percentages in prose",
         [round(hedge["cjk_200x125"]["usage_407"] * 100),
          round(hedge["cjk_200x125"]["usage_true"] * 100)], tol=0.5, n=2)
    g.at(r"prune \*\*(\d+) lines that actually load\*\*", "the pruning figure",
         hv["worst_understatement_lines"])
    g.ck(hv["hedge_never_under_reports"], "the artifact agrees his rule never under-reports")
    g.ck(hedge["ascii_200x125"]["over_report_x"] == 1.0, "and that it is free on ASCII")

    # --- his words, against his live issue --------------------------------------------------
    body = gh(f"repos/{REPO}/issues/{ISSUE}", "--jq", ".body")
    nb = ws(body)
    for frag in ("A checker must not pick one unit",
                 "size  = max(len(raw), chars)",
                 "regardless of which unit the runtime measures",
                 "under ~150 characters",
                 "the real budget is ~166 lines, not 200",
                 "130 lines"):
        g.ck(ws(frag) in nb, f"verbatim in #407: {frag[:44]}")
    g.ck(ws("125 characters per entry") in nb, "the ~125 figure is his")
    # The checks above prove HIS issue contains those strings. They do not prove the DRAFT
    # quotes them correctly -- a mutation of the draft's copy passed all of them. So pull the
    # quotation OUT of the draft and require it in his body, which is the direction that can
    # actually disagree with me.
    for pat, what in ((r"`(size = max\([^`]+)`", "his size formula"),
                      (r"`(usage = max\(size / 25000, lines / 200\))`", "his usage formula")):
        mm = list(re.finditer(pat, draft))
        if len(mm) != 1:
            g.ck(False, f"draft quotes {what} exactly once", f"found {len(mm)}")
            continue
        g.spans.append((mm[0].start(), mm[0].end()))
        g.ck(ws(mm[0].group(1)) in nb, f"the draft's copy of {what} is verbatim in #407",
             mm[0].group(1)[:50])
    g.at(r"(\d+) lines at (\d+)–(\d+)% of the size cap with a ~([\d.]+)% byte/char divergence",
         "his own measured index, as we restate it", [130, 67, 68, 1.6], tol=0.001, n=4)
    g.ck("67–68% of the size cap" in body and "~1.6%" in body,
         "those two figures are quoted from his text")
    g.ck(gh(f"repos/{REPO}/issues/{ISSUE}", "--jq", ".user.login") == "pjt222"
         and "@pjt222" in draft, "#407 attributed to its real author")

    # --- the mirror -----------------------------------------------------------------------------
    mir = subprocess.run(["curl", "-sf", MIRROR], capture_output=True).stdout.decode("utf-8", "replace")
    for frag in ("MAX_ENTRYPOINT_BYTES", "// ~125 chars/line at 200 lines"):
        g.ck(frag in mir and frag in draft, f"mirror contains what we quote: {frag[:32]}")
    g.ck("String.prototype.length" in draft and "trimmed.length" in mir,
         "the .length claim matches the mirrored expression")

    # --- our own formula must actually be right --------------------------------------------------
    m = re.search(r"size = sum\(2 if ord\(c\) > 0xFFFF else 1 for c in text\)", draft)
    g.ck(bool(m), "the offered formula is present verbatim")
    if m:
        g.spans.append((m.start(), m.end()))
        for name, ch in (("ascii", "x"), ("cjk", chr(0x4E2D)), ("emoji", chr(0x1F600))):
            probe = "abc" + ch * 10
            calc = sum(2 if ord(c) > 0xFFFF else 1 for c in probe)
            g.ck(calc == len(probe.encode("utf-16-le")) // 2,
                 f"the offered formula reproduces UTF-16 units for {name}", str(calc))

    # --- the three additions, each against the mirror or our live file ---------------------------
    g.ck('lines after ${MAX_ENTRYPOINT_LINES} will be truncated' in mir
         and "lines after 200 will be truncated" in draft,
         "the loader's own guidance really names only the line cap")
    g.ck(not re.search(r"--print|isPrint|printMode|interactive|tty|stream-json", mir),
         "no print/interactive/tty branch in the loader we claim has none")
    live = open(os.path.join(os.path.expanduser("~"), ".claude", "projects",
                             "C--Users-Danculus-agora", "memory", "MEMORY.md"),
                encoding="utf-8").read()
    lb, lu = len(live.encode("utf-8")), len(live.encode("utf-16-le")) // 2
    g.at(r"(\d+) lines, ([\d,]+) UTF-8 bytes against ([\d,]+) units — a ([\d.]+)% divergence",
         "our own live index, re-measured now",
         [len(live.split("\n")) - (1 if live.endswith("\n") else 0), lb, lu,
          round((lb / lu - 1) * 100, 2)], tol=0.005, n=4)
    g.ck(sum(1 for c in live if ord(c) > 0xFFFF) == 0,
         "and it really has nothing outside the BMP")
    g.at(r"(\d+\.\d+)% of cap by units against (\d+\.\d+)% by bytes", "our two cap fractions",
         [round(lu / 25000 * 100, 1), round(lb / 25000 * 100, 1)], tol=0.05, n=2)

    # --- the room, links, version -------------------------------------------------------------------
    st = gh(f"repos/{REPO}/issues/{ISSUE}", "--jq", ".state")
    g.ck(st == "open", "issue still open", st)
    cs = gh(f"repos/{REPO}/issues/{ISSUE}/comments", "--paginate", "--jq", "length")
    g.ck(cs in ("0", ""), "still no comments -- we would be first", f"comments={cs}")
    for path in re.findall(r"https://github\.com/DanceNitra/agora/blob/main/(\S+?)\)", draft):
        r = subprocess.run(["curl", "-sf",
                            f"https://raw.githubusercontent.com/DanceNitra/agora/main/{path}"],
                           capture_output=True)
        loc = os.path.join(ROOT, path)
        ok = r.returncode == 0 and os.path.exists(loc) and \
            hashlib.sha256(r.stdout.replace(b"\r\n", b"\n")).digest() == \
            hashlib.sha256(open(loc, "rb").read().replace(b"\r\n", b"\n")).digest()
        g.ck(ok, f"link serves the bytes we ran: {os.path.basename(path)}")
    ver = subprocess.run([shutil.which("claude") or "claude", "--version"],
                         capture_output=True, text=True).stdout.split()[0]
    g.ck(f"v{ver}" in draft, "version matches the installed CLI", ver)

    for pat in (r"@[\w-]+", r"#\d+", r"v\d+\.\d+\.\d+", r"https://\S+", r"0xFFFF", r"25000", r"25,000",
                r"200 lines each", r"UTF-16", r"UTF-8", r"1024", r"~125 chars/line at 200 lines",
                r"~150", r"~166", r"200 will be truncated", r"lines after 200", r"~1\.6%", r"67–68%", r"130 lines", r"125 characters",
                r"usage = max\(size / 25000, lines / 200\)", r"max\(len\(raw\), chars\)"):
        g.eat(pat)
    g.cover()
    return g


MUT = [("a unit cell", "| **61,600** | 25,200 | 25,200 | **198** |",
        "| **61,600** | 25,200 | 25,200 | **196** |"),
       ("a hedge cell", "| CJK | 2.46 | 1.01 | **2.44×** | 81 | **198** |",
        "| CJK | 2.46 | 1.01 | **2.54×** | 81 | **198** |"),
       ("the pruning figure", "prune **117 lines that actually load**",
        "prune **127 lines that actually load**"),
       ("his own figure", "130 lines at 67–68%", "131 lines at 67–68%"),
       ("a quotation of his code", "max(len(raw), chars)", "max(len(raw), lines)"),
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
