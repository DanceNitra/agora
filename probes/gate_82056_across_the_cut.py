"""Gate the (rewritten) reply to @yacb2 on anthropics/claude-code#82056.

Design rules earned the hard way and kept:
  * nothing asserts that the draft SAYS something -- every check reads a value OUT of the
    draft and compares it to a source the draft did not write. A gate that quoted my own
    wording once certified a mistranslation 25/25.
  * every claim is ANCHORED to its own sentence by a pattern that must match exactly one
    site. Set membership ("does 5627 appear anywhere") passed a mutant, and `v2.1.238` put
    "238" into that set and vouched for an unrelated count.
  * COVERAGE: every number in the draft must be consumed by a check or listed as a
    reference. The number nobody checked is the one that will be wrong.
"""
from __future__ import annotations
import hashlib, json, os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "agora_output", "drafts", "reply_82056_yacb2_across_the_cut.md")
P = lambda n: os.path.join(ROOT, "probes", n)  # noqa: E731
REPO, ISSUE, LAST = "anthropics/claude-code", 82056, 5358978892
MIRROR = ("https://raw.githubusercontent.com/chauncygu/collection-claude-code-source-code/"
          "b934603b2800374b315b25061bbeffb40ab6ab26/original-source-code/src/memdir/memdir.ts")
_c: dict = {}


def gh(*a: str) -> str:
    if a not in _c:
        _c[a] = subprocess.run(["gh", "api", *a], capture_output=True, text=True,
                               encoding="utf-8", errors="replace").stdout.strip()
    return _c[a]


class G:
    def __init__(s, d):
        s.d, s.rows, s.spans = d, [], []

    def ck(s, ok, label, detail=""):
        s.rows.append((bool(ok), label, detail))

    def at(s, pat, label, exp, tol=0.0, n=1):
        ms = list(re.finditer(pat, s.d))
        if len(ms) != 1:
            return s.ck(False, label, f"pattern matched {len(ms)} sites, needs 1")
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


def build(draft: str) -> G:
    g = G(draft)
    uj = json.load(open(P("is_the_cap_counted_in_bytes_or_utf16_units.result.json"), encoding="utf-8"))
    unit, uv = {r["label"]: r for r in uj["rows"]}, uj["verdicts"]
    step = json.load(open(P("does_the_step_track_the_warning_text.result.json"), encoding="utf-8"))
    cost = json.load(open(P("the_cost_curve_across_the_truncation_boundary.result.json"), encoding="utf-8"))
    rate = json.load(open(P("how_often_does_a_session_go_looking.result.json"), encoding="utf-8"))
    valid = [r for r in cost["rows"] if r.get("valid")]

    def dl(sw, b):
        v = {r["delta_vs_median"] for r in valid if r["sweep"] == sw and r["index_bytes"] == b}
        return v.pop() if len(v) == 1 else None

    def fit(sw, xs):
        ys = [dl(sw, x) for x in xs]
        sl = (ys[-1] - ys[0]) / (xs[-1] - xs[0])
        return sl, ys[0] - sl * xs[0]

    sl_l, ic_l = fit("line", (3000, 6000, 9000, 12000))
    sl_b, ic_b = fit("byte", (8000, 16000, 24000))

    # --- the unit table, cell by cell, against the probe that produced it ------------------
    for lbl, key in (("ASCII", "ascii_200x125"), (r"CJK \(中\)", "cjk_200x125"),
                     (r"emoji \(😀\)", "emoji_200x125")):
        r = unit[key]
        g.at(rf"\| {lbl} \| \*?\*?([\d,]+)\*?\*? \| ([\d,]+) \| \*?\*?([\d,]+)\*?\*? \| \*?\*?(\d+)\*?\*? \|",
             f"unit table row: {key}",
             [r["bytes"], r["code_points"], r["utf16_units"], r["last_line_loaded"]], n=4)
    g.ck(all(uv.values()), "the unit probe's own five controls passed", str(uv))
    g.at(r"A ([\d,]+)-byte file cuts in exactly the same place as a ([\d,]+)-byte one",
         "the two byte figures compared in prose",
         [unit["cjk_200x125"]["bytes"], unit["ascii_200x125"]["bytes"]], n=2)
    g.at(r"cuts (\d+) lines earlier", "the emoji/CJK gap",
         unit["cjk_200x125"]["last_line_loaded"] - unit["emoji_200x125"]["last_line_loaded"])
    g.at(r"reporting `([\d.]+)KB` over a file that is ([\d,]+) bytes",
         "the warning's own KB figure against the file",
         [round(unit["cjk_200x125"]["utf16_units"] / 1024, 1), unit["cjk_200x125"]["bytes"]],
         tol=0.05, n=2)
    g.at(r"holds ([\d,]+) bytes against a cap labelled (\d+)KB — ([\d.]+)×",
         "the CJK ratio, computed not asserted",
         [unit["cjk_200x125"]["bytes"], 25,
          round(unit["cjk_200x125"]["bytes"] / unit["cjk_200x125"]["utf16_units"], 1)],
         tol=0.05, n=3)
    g.at(r"emoji index loaded (\d+) of its (\d+) lines where the ASCII one loaded (\d+)",
         "emoji vs ascii membership",
         [unit["emoji_200x125"]["last_line_loaded"], unit["emoji_200x125"]["lines"],
          unit["ascii_200x125"]["last_line_loaded"]], n=3)

    # --- the reachability rate --------------------------------------------------------------
    o = rate["rows"]
    rec, tot = sum(1 for r in o if r["answered"]), len(o)
    g.at(r"answered in (\d+) of (\d+) sessions", "the recovery rate", [rec, tot], n=2)
    g.ck(all(not r["tools_used"] for r in o if not r["answered"]),
         "every failing session really used no tool")
    g.at(r"n=(\d+) on the recall figure", "n stated in the boundaries", tot)

    # --- the cost curve and the step ---------------------------------------------------------
    g.at(r"([\d,]+) tokens at ([\d,]+), ([\d,]+) and ([\d,]+) units, ([\d,]+) at ([\d,]+), ([\d,]+) and ([\d,]+)",
         "both plateaus, cell by cell",
         [dl("line", 15000), 15000, 18000, 24000, dl("byte", 32000), 32000, 40000, 56000], n=8)
    g.ck(len({dl("line", b) for b in (15000, 18000, 24000)}) == 1
         and len({dl("byte", b) for b in (32000, 40000, 56000)}) == 1,
         "both plateaus are flat IN THE ARTIFACT")
    g.at(r"\*\*\+(\d+)\*\* for `is 201 lines \(limit: 200\)`", "step, line-cap arm",
         step["steps"]["cut_201x60"])
    g.at(r"\*\*\+(\d+)\*\* for `is 202 lines and 24\.7KB`", "step, both-caps arm",
         step["steps"]["cut_202x125"])
    g.at(r"\*\*\+(\d+)\*\* for the longer `is 1005 lines and 58\.9KB`", "step, long-form arm",
         step["steps"]["cut_1005x60"])
    g.ck(len(set(step["steps"].values())) > 1, "the steps really do differ in the artifact",
         str(step["steps"]))
    for k, frag in (("cut_201x60", "is 201 lines (limit: 200)"),
                    ("cut_202x125", "is 202 lines and 24.7KB"),
                    ("cut_1005x60", "is 1005 lines and 58.9KB")):
        g.ck(frag in step["arms"][k]["warning"],
             f"quoted warning is verbatim in the artifact: {k}", step["arms"][k]["warning"][:55])
    g.at(r"([\d.]+) tokens per unit at 60-unit lines against ([\d.]+) at 400, intercept (\d+) and (\d+)",
         "slopes and intercepts", [round(sl_l, 3), round(sl_b, 3), round(ic_l), round(ic_b)],
         tol=0.0005, n=4)
    g.at(r"the ([\d.]+)× between them is content", "content ratio", round(sl_l / sl_b, 2), tol=0.005)

    # --- other people's words ------------------------------------------------------------------
    body407 = gh("repos/pjt222/agent-almanac/issues/407", "--jq", ".body")
    q = re.search(r'\*"([^"]+)"\*', draft)
    norm = lambda s: re.sub(r"[*_`]", "", s)  # noqa: E731
    g.ck(q is not None and norm(q.group(1)) in norm(body407),
         "the #407 quote is verbatim in #407", (q.group(1)[:65] if q else "no quote found"))
    g.ck(gh("repos/pjt222/agent-almanac/issues/407", "--jq", ".user.login") == "pjt222"
         and "@pjt222" in draft, "#407 attributed to its real author")
    g.ck("under ~150 characters" in body407, "#407 really reports the ~150 guidance")
    mir = subprocess.run(["curl", "-sf", MIRROR], capture_output=True).stdout.decode("utf-8", "replace")
    for frag in ("// ~125 chars/line at 200 lines", "MAX_ENTRYPOINT_BYTES",
                 "const byteCount = trimmed.length"):
        g.ck(frag in mir and frag in draft, f"mirror contains what we quote: {frag[:32]}")
    for n, who in ((56786, "benlemus"), (57574, "bcnboy"), (65430, "GraceAtwood")):
        api = gh(f"repos/{REPO}/issues/{n}", "--jq", ".user.login")
        m = re.search(rf"@([\w-]+) [^.#]{{0,60}}#{n}", draft)
        g.ck(bool(m) and m.group(1).lower() == api.lower() == who.lower(),
             f"#{n} attributed to its real author", f"draft={m.group(1) if m else None} api={api}")
    b65 = gh(f"repos/{REPO}/issues/65430", "--jq", ".body")
    g.ck("was_truncated" in b65 and "was_byte_truncated" in b65,
         "the flag names we attribute to #65430 are hers")
    theirs = gh(f"repos/{REPO}/issues/comments/{LAST}", "--jq", ".body")
    ours = gh(f"repos/{REPO}/issues/comments/5354197113", "--jq", ".body")
    nums = lambda t: {x.replace(",", "") for x in re.findall(r"[\d,]+\.?\d*", t)}  # noqa: E731
    g.at(r"so your ([\d.]+) and my proxy's ([\d.]+)", "his slope and our proxy", [0.435, 0.265],
         tol=0.0005, n=2)
    g.ck("0.435" in nums(theirs) and "0.265" in nums(ours), "each quoted from its own author")
    g.at(r"the ([\d.]+)–([\d.]+)× I measured", "our vocabulary spread", [1.22, 1.69],
         tol=0.0005, n=2)
    g.ck({"1.22", "1.69"} <= nums(ours), "that spread is in our own earlier comment")
    g.at(r"You have (\d+) distinct indexes", "his index count", 21)
    g.ck("21" in nums(theirs), "21 is his number")

    # --- links, the room, the version ------------------------------------------------------------
    for path in re.findall(r"https://github\.com/DanceNitra/agora/blob/main/(\S+?)\)", draft):
        r = subprocess.run(["curl", "-sf",
                            f"https://raw.githubusercontent.com/DanceNitra/agora/main/{path}"],
                           capture_output=True)
        loc = os.path.join(ROOT, path)
        ok = r.returncode == 0 and os.path.exists(loc) and \
            hashlib.sha256(r.stdout.replace(b"\r\n", b"\n")).digest() == \
            hashlib.sha256(open(loc, "rb").read().replace(b"\r\n", b"\n")).digest()
        g.ck(ok, f"link serves the bytes we ran: {os.path.basename(path)}")
    g.ck(gh(f"repos/{REPO}/issues/{ISSUE}", "--jq", ".state") == "open", "issue still open")
    g.ck(str(LAST) in gh(f"repos/{REPO}/issues/{ISSUE}/comments", "--paginate", "--jq",
                         '.[-1] | "\\(.user.login) \\(.id)"'), "they still speak last")
    ver = subprocess.run([shutil.which("claude") or "claude", "--version"],
                         capture_output=True, text=True).stdout.split()[0]
    g.ck(f"v{ver}" in draft, "version matches the installed CLI", ver)

    for pat in (r"#\d+", r"v\d+\.\d+\.\d+", r"`min\(200 lines, 25,000\)`", r"@[\w-]+",
                r"the first 25KB", r"limit: 24\.4KB", r"~125 chars/line at 200 lines",
                r"under ~150 characters", r"~200 chars", r"200 lines each", r"got 125",
                r"three UTF-8 bytes", r"UTF-16", r"UTF-8", r"three in the",
                r"https://\S+", r"1024", r"25KB", r"3×", r"constant 63", r"125"):
        g.eat(pat)
    g.cover()
    return g


MUT = [("a unit-table cell", "| **61,600** | 25,200 | 25,200 | **198** |",
        "| **61,600** | 25,200 | 25,200 | **196** |"),
       ("a plateau figure", "5,627 tokens at 15,000", "5,628 tokens at 15,000"),
       ("a step", "**+67** for the longer", "**+68** for the longer"),
       ("the recovery rate", "answered in 3 of 6 sessions", "answered in 4 of 6 sessions"),
       ("an attribution", "@bcnboy the byte-cap", "@benlemus the byte-cap"),
       ("someone else's number", "so your 0.435 and", "so your 0.445 and"),
       ("an uncovered number", "— Rastislav", "One more: 9,999.\n\n— Rastislav")]


def main() -> int:
    d = open(D, encoding="utf-8").read()
    g = build(d)
    for ok, label, det in g.rows:
        print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{det}]" if det else ""))
    p = sum(1 for ok, _, _ in g.rows if ok)
    print(f"\n{p}/{len(g.rows)} checks pass")
    caught, missed = [], []
    for lbl, a, b in MUT:
        m = d.replace(a, b, 1)
        if m == d:
            missed.append(f"{lbl}: pattern absent, not applied")
            continue
        f = [x for ok, x, _ in build(m).rows if not ok]
        (caught if f else missed).append(f"{lbl} -> {f[0] if f else 'NOT CAUGHT'}")
    print(f"\nmutation control: {len(caught)}/{len(MUT)} caught")
    for c in caught:
        print(f"  caught: {c}")
    for m in missed:
        print(f"  MISSED: {m}")
    ok_all = p == len(g.rows) and not missed
    print("\nVERDICT:", "READY (owner approval still required)" if ok_all else "NOT READY")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
