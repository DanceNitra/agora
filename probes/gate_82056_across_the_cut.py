"""Gate the reply to @yacb2 on anthropics/claude-code#82056 before it is sent.

Two defects in my own gates produced this design, and both are worth stating because the
gate is where they hide.

1. The gate on the previous send asserted that one of MY OWN sentences appeared in the
   draft. A check like that cannot disagree with me: it certified a mistranslation 25/25
   and would have gone on doing so. So nothing here asserts the draft SAYS something --
   every check reads a value OUT of the draft and compares it to a source the draft did
   not write.

2. The first version of THIS gate passed 63/63 and then passed its own mutant. Its checks
   were set-membership -- "does 5627 appear anywhere in the draft" -- and the draft quotes
   the plateau three times, so corrupting one occurrence left the value in the set. Worse,
   `v2.1.238` put "238" into that set and silently vouched for our entry count. Set
   membership is weaker than the property it stands for. Every claim here is therefore
   ANCHORED: read from its own sentence, by a pattern that matches that site alone.

Plus the control the second defect argued for: COVERAGE. Every number in the draft must be
consumed by some check or named in an explicit whitelist of references. A number nobody
checked is the one that will be wrong.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEM = os.path.join(os.path.expanduser("~"), ".claude", "projects", "C--Users-Danculus-agora", "memory")
DRAFT = os.path.join(ROOT, "agora_output", "drafts", "reply_82056_yacb2_across_the_cut.md")
COST = os.path.join(ROOT, "probes", "the_cost_curve_across_the_truncation_boundary.result.json")
WARN = os.path.join(ROOT, "probes", "the_warning_the_session_is_already_given.result.json")
WCOST = os.path.join(ROOT, "probes", "what_the_truncation_warning_itself_costs.result.json")
CROWD = os.path.join(ROOT, "probes", "uncrowding_the_index_moved_62_queries_up_and_11_down.result.json")

REPO, ISSUE, LAST_THEIRS = "anthropics/claude-code", 82056, 5358978892
_gh_cache: dict[tuple[str, ...], str] = {}


def gh(*args: str) -> str:
    if args not in _gh_cache:
        _gh_cache[args] = subprocess.run(["gh", "api", *args], capture_output=True, text=True,
                                         encoding="utf-8", errors="replace").stdout.strip()
    return _gh_cache[args]


def num(s: str) -> float:
    return float(s.replace(",", "").replace(" ", ""))


def numbers_in(text: str) -> set[str]:
    return {x.replace(",", "") for x in re.findall(r"[\d,]+\.?\d*", text)}


class Gate:
    def __init__(self, draft: str):
        self.draft = draft
        self.rows: list[tuple[bool, str, str]] = []
        self.spans: list[tuple[int, int]] = []

    def check(self, ok: bool, label: str, detail: str = "") -> None:
        self.rows.append((bool(ok), label, detail))

    def at(self, pattern: str, label: str, expect, tol: float = 0.0, groups: int = 1) -> None:
        """Read the value(s) at ONE anchored site and compare against `expect`.

        The pattern must match exactly once. Absent, or ambiguous because the same wording
        occurs twice, is a failure -- not a silent pass on whichever hit came first.
        """
        ms = list(re.finditer(pattern, self.draft))
        if len(ms) != 1:
            self.check(False, label, f"pattern matched {len(ms)} sites, needs exactly 1")
            return
        m = ms[0]
        self.spans.append((m.start(), m.end()))
        got = [num(m.group(i + 1)) for i in range(groups)]
        exp = [float(x) for x in (expect if isinstance(expect, (list, tuple)) else [expect])]
        ok = len(got) == len(exp) and all(abs(gv - ev) <= tol for gv, ev in zip(got, exp))
        self.check(ok, label, f"draft={got} source={exp}")

    def consume(self, pattern: str) -> None:
        for m in re.finditer(pattern, self.draft, re.M):
            self.spans.append((m.start(), m.end()))

    def coverage(self) -> None:
        loose = [m.group(0) for m in re.finditer(r"\d[\d,]*(?:\.\d+)?", self.draft)
                 if not any(a <= m.start() < b for a, b in self.spans)]
        self.check(not loose, "every number in the draft is covered by a check",
                   f"uncovered={loose}" if loose else "")


def build(draft: str) -> Gate:
    g = Gate(draft)
    cost = json.load(open(COST, encoding="utf-8"))
    wjson = json.load(open(WARN, encoding="utf-8"))
    warn = {r["label"]: r for r in wjson["rows"]}
    wverd = wjson["verdicts"]
    wc = json.load(open(WCOST, encoding="utf-8"))
    crowd = json.load(open(CROWD, encoding="utf-8"))
    valid = [r for r in cost["rows"] if r.get("valid")]

    def delta(sweep, b):
        s = {r["delta_vs_median"] for r in valid if r["sweep"] == sweep and r["index_bytes"] == b}
        return s.pop() if len(s) == 1 else None

    def fit(sweep, xs):
        ys = [delta(sweep, x) for x in xs]
        sl = (ys[-1] - ys[0]) / (xs[-1] - xs[0])
        return sl, ys[0] - sl * xs[0]

    s_line, i_line = fit("line", (3000, 6000, 9000, 12000))
    s_byte, i_byte = fit("byte", (8000, 16000, 24000))

    # --- the two cost tables, cell by anchored cell -----------------------------------------
    g.at(r"\| 60 \| ([\d,]+) . ([\d,]+) \| ([\d,]+) . ([\d,]+) \| ([\d.]+) \|",
         "line sweep row: sizes, deltas, rate",
         [3000, 12000, delta("line", 3000), delta("line", 12000), round(s_line, 3)],
         tol=0.0005, groups=5)
    g.at(r"\| 60 \| ([\d,]+) / ([\d,]+) / ([\d,]+) \| \*\*([\d,]+) / ([\d,]+) / ([\d,]+)\*\*",
         "line plateau row: three sizes, three deltas",
         [15000, 18000, 24000, delta("line", 15000), delta("line", 18000), delta("line", 24000)],
         groups=6)
    g.at(r"\| 400 \| ([\d,]+) . ([\d,]+) \| ([\d,]+) . ([\d,]+) \| ([\d.]+) \|",
         "byte sweep row: sizes, deltas, rate",
         [8000, 24000, delta("byte", 8000), delta("byte", 24000), round(s_byte, 3)],
         tol=0.0005, groups=5)
    g.at(r"\| 400 \| ([\d,]+) / ([\d,]+) / ([\d,]+) \| \*\*([\d,]+) / ([\d,]+) / ([\d,]+)\*\*",
         "byte plateau row: three sizes, three deltas",
         [32000, 40000, 56000, delta("byte", 32000), delta("byte", 40000), delta("byte", 56000)],
         groups=6)
    for sweep, bs in (("line", (15000, 18000, 24000)), ("byte", (32000, 40000, 56000))):
        vals = {delta(sweep, b) for b in bs}
        g.check(len(vals) == 1 and None not in vals, f"{sweep} plateau is flat IN THE ARTIFACT",
                f"{sorted(v for v in vals if v is not None)}")

    # --- the prose restating the fit -----------------------------------------------------------
    g.at(r"([\d.]+) at 60 B/line, ([\d.]+) at 400 B/line, intercept (\d+) and (\d+)",
         "slopes and intercepts as stated in prose",
         [round(s_line, 3), round(s_byte, 3), round(i_line), round(i_byte)], tol=0.0005, groups=4)
    g.at(r"The ([\d.]+)× between the two is content", "content ratio between the sweeps",
         round(s_line / s_byte, 2), tol=0.005)

    # --- membership: the cut, the crossover, the shape table -------------------------------------
    g.at(r"inclusive at exactly ([\d,]+)", "byte cap inclusivity", 25000)
    g.at(r"cross at \*\*(\d+) bytes per line\*\*", "crossover width", 25000 / 200)
    g.at(r"Below (\d+) B/line you are line-bound", "crossover restated", 25000 / 200)

    shape = re.findall(r"^\| (\d+) \| ([\d,]+) B / (\d+) lines \| (\d+) \| ([\d–-]+) \|",
                       draft, re.M)
    g.check(len(shape) == 6, "shape table has six rows", f"found={len(shape)}")
    for bpl, fb, fl, pred, meas in shape:
        b = int(bpl)
        rows = [r for r in valid if r["sweep"] == "shape" and r["bytes_per_line"] == b]
        art = {r["canary_last_line"] for r in rows}
        g.check(int(pred) == min(200, 25000 // b), f"predicted cut at {b} B/line",
                f"draft={pred} min(200,25000/{b})={min(200, 25000 // b)}")
        g.check(any(str(v) in meas for v in art), f"measured cut at {b} B/line vs artifact",
                f"draft={meas} artifact={sorted(art)}")
        g.check(any(r["index_bytes"] == int(fb.replace(",", "")) and r["index_lines"] == int(fl)
                    for r in rows), f"file shape at {b} B/line vs artifact", f"{fb} B / {fl} lines")
    g.consume(r"^\| \d+ \| [\d,]+ B / \d+ lines \| \d+ \| [\d–-]+ \|")

    # --- the warning's own price, from its own artifact --------------------------------------------
    w1 = wc["B_201x60_cut"]["delta"] - wc["A_200x60_fits"]["delta"]
    w2 = wc["D_202x125_cut"]["delta"] - wc["C_200x125_fits"]["delta"]
    g.at(r"step at the crossing is (\d+) tokens", "warning price in the heading", w1)
    g.at(r"(\d+)×(\d+) against (\d+)×(\d+) loads identical content — ([\d,]+) bytes both — and differs by \+(\d+)\.",
         "first held-identical pair", [201, 60, 200, 60, wc["A_200x60_fits"]["bytes"], w1], groups=6)
    g.at(r"(\d+)×(\d+) against (\d+)×(\d+) loads identical content — ([\d,]+) bytes both — and differs by \+(\d+) again",
         "second held-identical pair", [202, 125, 200, 125, wc["C_200x125_fits"]["bytes"], w2], groups=6)
    g.check(w1 == w2, "both pairs price the warning the same", f"{w1} / {w2}")
    g.check(wc["A_200x60_fits"]["warn"] is False and wc["C_200x125_fits"]["warn"] is False
            and wc["B_201x60_cut"]["warn"] and wc["D_202x125_cut"]["warn"],
            "warning state of the four arms is what the argument needs", "")

    # --- the closing arithmetic ----------------------------------------------------------------------
    g.at(r"`(\d+) \+ ([\d.]+) × ([\d,]+) \+ (\d+) = ([\d,]+)` against ([\d,]+) measured, and ([\d,]+) against ([\d,]+)",
         "plateau prediction, both sweeps",
         [round(i_line), round(s_line, 4), 12000, w1, round(i_line + s_line * 12000 + w1),
          delta("line", 24000), round(i_byte + s_byte * 24800 + w2), delta("byte", 56000)],
         tol=0.00005, groups=8)

    # --- the advice defect -----------------------------------------------------------------------------
    t5, t5b = warn["T5_advice_max_200x200"], warn["T5b_consistent_200x125"]
    g.at(r"Two hundred entries at (\d+) chars is ([\d,]+) bytes, and a (\d+)×(\d+) index measures truncated at entry (\d+)",
         "the advice arithmetic and its measured truncation point",
         [200, 40000, 200, 200, t5["last_visible_entry"]], groups=5)
    g.at(r"(\d+)×(\d+) is ([\d,]+) bytes exactly and loads whole", "the consistent width fits",
         [200, 125, t5b["file_bytes"]], groups=3)
    g.check(t5["has_warning"] and not t5b["has_warning"], "artifact agrees on which one truncates",
            f"200x200 warn={t5['has_warning']}, 200x125 warn={t5b['has_warning']}")
    g.check(all(wverd.values()), "the warning probe's own controls all passed", str(wverd))
    g.at(r"(\d+) is the width at which they do", "the width named at the end", 25000 / 200)

    # --- our own store, re-measured now ------------------------------------------------------------------
    raw = open(os.path.join(MEM, "MEMORY.md"), "rb").read().decode("utf-8")
    er = re.compile(r"\[([^\]]+)\]\(([^)]+\.md)\)")
    n_entries = len(er.findall(raw))
    n_lines = len(raw.split("\n")) - (1 if raw.endswith("\n") else 0)
    co = [l for l in raw.split("\n") if len(er.findall(l)) > 1]
    g.at(r"(\d+) entries deliberately packed back onto (\d+) lines, (\d+) of which carry two",
         "our index as it stands right now", [n_entries, n_lines, len(co)], groups=3)
    g.check(n_lines <= 200 and len(raw.encode()) <= 25000,
            "our own index still fits the window we are lecturing about",
            f"{n_lines} lines / {len(raw.encode())} bytes")

    # --- the un-crowding history, from the backups and the probe --------------------------------------------
    pre = open(os.path.join(MEM, "MEMORY.md.bak-20260819-precrowdfix"), "rb").read()
    post = open(os.path.join(MEM, "MEMORY.md.bak-20260819-prewrittenlines"), "rb").read()
    pre_l = len(pre.decode("utf-8").split("\n")) - 1
    post_l = len(post.decode("utf-8").split("\n")) - 1
    g.at(r"recall@3 from ([\d.]+) to ([\d.]+) on (\d+) queries \((\d+) better, (\d+) worse\)",
         "the un-crowding gain, from its own probe",
         [round(crowd["before"]["r3"], 3), round(crowd["after"]["r3"], 3), crowd["n_queries"],
          crowd["paired"]["better"], crowd["paired"]["worse"]], tol=0.0005, groups=5)
    g.at(r"from (\d+) lines to (\d+)", "the line growth, from the two backups on disk",
         [pre_l, post_l], groups=2)
    g.check(abs(len(pre) - len(post)) < 100, "and it really was byte-neutral",
            f"{len(pre)} -> {len(post)} bytes")

    # --- numbers that belong to other people ----------------------------------------------------------------
    theirs = gh(f"repos/{REPO}/issues/comments/{LAST_THEIRS}", "--jq", ".body")
    prev = gh(f"repos/{REPO}/issues/comments/5352555064", "--jq", ".body")
    ours = gh(f"repos/{REPO}/issues/comments/5354197113", "--jq", ".body")
    g.at(r"All four of yours are ([\d,]+)–([\d,]+) bytes", "his index size range", [335, 11206],
         groups=2)
    g.check({"335", "11206"} <= numbers_in(theirs + prev), "that range is in his own comments", "")
    g.at(r"so your ([\d.]+) and my proxy's ([\d.]+)", "his slope and our proxy rate",
         [0.435, 0.265], tol=0.0005, groups=2)
    g.check("0.435" in numbers_in(theirs) and "0.265" in numbers_in(ours),
            "each is quoted from its own author", "")
    g.at(r"same effect as the ([\d.]+)–([\d.]+)× I measured", "our vocabulary spread",
         [1.22, 1.69], tol=0.0005, groups=2)
    g.check({"1.22", "1.69"} <= numbers_in(ours), "that spread is in our own earlier comment", "")
    g.at(r"spared you the (\d+) false zeros", "his false-zero count", 24)
    g.at(r"You have (\d+) distinct indexes", "his index count", 21)
    g.check("24" in numbers_in(prev) and "21" in numbers_in(theirs), "both counts are his", "")

    # --- attribution of the prior art ---------------------------------------------------------------------------
    for n, who in ((56786, "benlemus"), (57574, "bcnboy"), (65430, "GraceAtwood")):
        api = gh(f"repos/{REPO}/issues/{n}", "--jq", ".user.login")
        m = re.search(rf"@([\w-]+) [^.#]{{0,60}}#{n}", draft)
        g.check(m is not None and m.group(1).lower() == api.lower() == who.lower(),
                f"#{n} attributed to its real author", f"draft={m.group(1) if m else None} api={api}")

    # --- links, taken FROM the draft and compared byte for byte -------------------------------------------------
    for path in re.findall(r"https://github\.com/DanceNitra/agora/blob/main/(\S+?)\)", draft):
        r = subprocess.run(["curl", "-sf",
                            f"https://raw.githubusercontent.com/DanceNitra/agora/main/{path}"],
                           capture_output=True)
        loc = os.path.join(ROOT, path)
        ok = r.returncode == 0 and os.path.exists(loc) and \
            hashlib.sha256(r.stdout.replace(b"\r\n", b"\n")).digest() == \
            hashlib.sha256(open(loc, "rb").read().replace(b"\r\n", b"\n")).digest()
        g.check(ok, f"link serves the bytes we ran: {os.path.basename(path)}", "")

    # --- the room ------------------------------------------------------------------------------------------------
    g.check(gh(f"repos/{REPO}/issues/{ISSUE}", "--jq", ".state") == "open", "issue still open")
    last = gh(f"repos/{REPO}/issues/{ISSUE}/comments", "--paginate", "--jq",
              '.[-1] | "\\(.user.login) \\(.id)"')
    g.check(str(LAST_THEIRS) in last, "they still speak last", f"last={last}")
    ver = subprocess.run([shutil.which("claude") or "claude", "--version"],
                         capture_output=True, text=True).stdout.split()[0]
    g.check(f"v{ver}" in draft, "version string matches the installed CLI", f"cli={ver}")

    # --- references that are names, not measurements ---------------------------------------------------------------
    # sites the coverage control found unchecked on the first run -- each now anchored
    line_cap = max(r["canary_last_line"] for r in valid if r["sweep"] == "line")
    g.at(r"you get (\d+) entries whatever they weigh", "the line cap, as the draft restates it",
         line_cap)
    g.at(r"the line cap cut it at (\d+) anyway", "the line cap in our own history", line_cap)
    g.at(r"on one side of (\d+) only", "crossover in the conclusion sentence", 25000 / 200)
    advice = re.search(r'\*"([^"]+)"\*', draft)
    measured_warnings = [r["warning"] for r in wjson["rows"] if r.get("has_warning")]
    g.check(advice is not None and any(advice.group(1) in w for w in measured_warnings),
            "the advice we quote is verbatim in a warning we actually measured",
            f"quoted={advice.group(1)[:60] if advice else None!r}")
    if advice:
        g.spans.append((advice.start(), advice.end()))

    g.consume(r"@[\w-]+")
    g.consume(r"#\d+")
    g.consume(r"v\d+\.\d+\.\d+")
    g.consume(r"`min\(200 lines, 25,000 bytes\)`")
    g.consume(r"200-line / 25KB")
    g.consume(r"ask 3")
    g.consume(r"every Nth line")
    g.coverage()
    return g


MUTATIONS = [
    ("a plateau figure", "5,627 / 5,627 / 5,627", "5,627 / 5,628 / 5,627"),
    ("a sweep endpoint", "1,574 → 5,564", "1,574 → 5,565"),
    ("the fitted slope", "0.443 at 60 B/line", "0.453 at 60 B/line"),
    ("a measured cut", "| 150 | 36,000 B / 240 lines | 166 | 166 |",
                       "| 150 | 36,000 B / 240 lines | 166 | 170 |"),
    ("the warning price", "differs by +63 again", "differs by +64 again"),
    ("our entry count", "238 entries deliberately", "239 entries deliberately"),
    ("an attribution", "@bcnboy quotes", "@benlemus quotes"),
    ("the crossover", "cross at **125 bytes per line**", "cross at **135 bytes per line**"),
    ("someone else's number", "so your 0.435 and my proxy's", "so your 0.445 and my proxy's"),
    ("the un-crowding gain", "0.208 to 0.325 on 120", "0.208 to 0.335 on 120"),
    ("an uncovered number added", "— Rastislav", "One more figure: 9,999.\n\n— Rastislav"),
]


def main() -> int:
    draft = open(DRAFT, encoding="utf-8").read()
    g = build(draft)
    print(f"=== GATE: reply to #{ISSUE} ===\n")
    for ok, label, detail in g.rows:
        print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))
    passed = sum(1 for ok, _, _ in g.rows if ok)
    print(f"\n{passed}/{len(g.rows)} checks pass")

    caught, missed = [], []
    for label, a, b in MUTATIONS:
        mut = draft.replace(a, b, 1)
        if mut == draft:
            missed.append(f"{label}: pattern not present, mutation not applied")
            continue
        fails = [l for ok, l, _ in build(mut).rows if not ok]
        (caught if fails else missed).append(f"{label} -> {fails[0] if fails else 'NOT CAUGHT'}")
    print(f"\nmutation control: {len(caught)}/{len(MUTATIONS)} corruptions caught")
    for c in caught:
        print(f"  caught: {c}")
    for m in missed:
        print(f"  MISSED: {m}")

    ok_all = passed == len(g.rows) and not missed
    print("\nVERDICT:", "READY (owner approval still required to send)" if ok_all else "NOT READY")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
