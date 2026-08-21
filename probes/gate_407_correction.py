"""Gate the CRLF correction on pjt222/agent-almanac#407.

Every figure is read OUT of the draft and compared against the raw file, and the sentence
being retracted is compared against the comment as GitHub actually serves it -- a
correction that misquotes what it corrects is worse than the original error.
"""
from __future__ import annotations
import re, subprocess, sys, os

D = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "agora_output", "drafts", "reply_407_correction_crlf.md")
M = os.path.join(os.path.expanduser("~"), ".claude", "projects",
                 "C--Users-Danculus-agora", "memory", "MEMORY.md")
SENT = "5366900247"
rows = []


def ck(ok, label, detail=""):
    rows.append((bool(ok), label, detail))


def units(s):
    return sum(2 if ord(c) > 0xFFFF else 1 for c in s)


def main():
    d = open(D, encoding="utf-8", newline="").read()
    raw = open(M, "rb").read()
    s = raw.decode("utf-8")
    soft = open(M, encoding="utf-8").read()          # the normalising read that caused this
    b, u = len(raw), units(s)

    def at(pat, label, exp, tol=0.0, n=1):
        ms = list(re.finditer(pat, d))
        if len(ms) != 1:
            return ck(False, label, f"matched {len(ms)} sites, needs 1")
        got = [float(ms[0].group(i + 1).replace(",", "")) for i in range(n)]
        e = [float(x) for x in (exp if isinstance(exp, (list, tuple)) else [exp])]
        ck(all(abs(g - v) <= tol for g, v in zip(got, e)), label, f"draft={got} raw={e}")

    at(r"\| UTF-8 bytes on disk \| ([\d,]+) \|", "bytes vs the raw file", b)
    at(r"\| UTF-16 units \| ([\d,]+) \|", "units vs the raw file", u)
    at(r"\| divergence \| ([\d.]+)% \|", "divergence", round((b / u - 1) * 100, 2), tol=0.005)
    at(r"\| of cap, by units \| ([\d.]+)% \|", "units fraction", round(u / 25000 * 100, 1), tol=0.05)
    at(r"\| of cap, by bytes \| ([\d.]+)% \|", "bytes fraction", round(b / 25000 * 100, 1), tol=0.05)
    at(r"\| characters outside the BMP \| (\d+) \|", "astral count",
       sum(1 for c in s if ord(c) > 0xFFFF))
    at(r"so (\d+) [^ ]+ characters were deleted", "the CR count the normalising read dropped",
       u - units(soft))
    at(r"\*\*(\d+) of (\d+)\*\*: one entry had already fallen outside",
       "the live loss the byte gate missed", [238, 239], n=2)
    at(r"rebuild is (\d+) of (\d+) at ([\d,]+) units", "the rebuild figures", [239, 239, u], n=3)

    live = subprocess.run(["gh", "api", f"repos/pjt222/agent-almanac/issues/comments/{SENT}",
                           "--jq", ".body"], capture_output=True, text=True,
                          encoding="utf-8").stdout
    q = re.search(r'I gave our index as "([^"]+)"', d)
    ck(q is not None and q.group(1) in live,
       "the retracted sentence is verbatim in the comment being corrected",
       q.group(1) if q else "no quote found")
    ck('newline=""' in d, "the remedy names a real fix")
    st = subprocess.run(["gh", "api", "repos/pjt222/agent-almanac/issues/407", "--jq", ".state"],
                        capture_output=True, text=True).stdout.strip()
    ck(st == "open", "issue still open", st)
    last = subprocess.run(["gh", "api", "repos/pjt222/agent-almanac/issues/407/comments",
                           "--paginate", "--jq", '.[-1] | "\(.user.login) \(.id)"'],
                          capture_output=True, text=True).stdout.strip()
    ck(SENT in last, "ours is still the last comment -- a self-correction, not an interruption", last)

    for ok, l, det in rows:
        print(f"  {'PASS' if ok else 'FAIL'}  {l}" + (f"   [{det}]" if det else ""))
    p = sum(1 for ok, _, _ in rows if ok)
    print(f"\n{p}/{len(rows)} checks pass")
    print("VERDICT:", "READY (owner approval still required)" if p == len(rows) else "NOT READY")
    return 0 if p == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
