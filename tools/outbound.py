"""One command for one outbound text, from an empty folder to a sent comment.

WHY. On 2026-09-24 a single page of text cost millions of tokens: every step (render, receipt, log,
stamp, SVG, footer, show, post) was composed by hand inside a session whose context was 94% full,
so each small turn re-read the whole conversation. The owner set the budget at under 100k tokens
per text, gate included. Everything that does not need judgment is therefore this file, and costs
no tokens. The only model work left is writing the draft and ONE gate subagent (see
.claude/skills/outbound/SKILL.md).

    python tools/outbound.py new    SLUG --thread owner/repo#N --sign github|edrn [--kind issue|pr]
    python tools/outbound.py check  SLUG      # deterministic lint, 0 tokens
    python tools/outbound.py gate   SLUG      # prints the one gate-subagent prompt
    python tools/outbound.py seal   SLUG --inputs FILE... [--dry-run]
    python tools/outbound.py show   SLUG      # render paths + hash for the owner
    python tools/outbound.py post   SLUG --sha HASH
    python tools/outbound.py status [SLUG]    # where every text stands, and the next command

Each text lives in agora_output/outbound/SLUG/: draft.md (body, no seal), claims.py (reads
AGORA_INPUT_DIR), meta.json, and after `seal` draft.sealed.md. Nothing here sends anything
except `post`, and `post` goes through tools/send_approved.py with all of its guards.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import io
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, "agora_output", "outbound")
PY = sys.executable

SIGNATURES = {
    "github": "Rastislav. Written with AI assistance and reviewed by a human before sending.",
    "edrn": "Rastislav Drahoš, Agora Research OS",
}

CLAIMS_TEMPLATE = '''"""Every figure in outbound text SLUG, recomputed from its source files.

Each claim reads the value from an input file AND checks the draft states it, so a figure that
drifts in either place fails. tools/recompute_receipt.py runs this and mutates the inputs, so read
inputs only from AGORA_INPUT_DIR. The draft itself must be one of the inputs, named draft.md.
"""
import io
import os

D = os.environ["AGORA_INPUT_DIR"]


def text(name):
    try:
        return io.open(os.path.join(D, name), encoding="utf-8", errors="replace").read()
    except Exception:
        return ""


body = text("draft.md")


def claim(cid, ok, desc, stated):
    ok = bool(ok) and all(s in body for s in stated)
    print("CLAIM %s %s %s" % (cid, "PASS" if ok else "FAIL", desc))


# claim("id", <value from an input> == <expected>, "what it checks", ["the phrase the draft states"])
'''


def _dir(slug):
    return os.path.join(BASE, slug)


def _meta(slug):
    with io.open(os.path.join(_dir(slug), "meta.json"), encoding="utf-8") as fh:
        return json.load(fh)


def _sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _run(cmd, **kw):
    print("$ " + " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=ROOT, **kw).returncode


def _thread_parts(thread):
    m = re.fullmatch(r"([\w.-]+/[\w.-]+)#(\d+)", thread or "")
    if not m:
        raise SystemExit("REFUSED: --thread must look like owner/repo#123, got %r" % thread)
    return m.group(1), m.group(2)


def cmd_new(a):
    d = _dir(a.slug)
    if os.path.exists(d):
        raise SystemExit("REFUSED: %s exists; pick a new slug or continue with `status %s`." % (d, a.slug))
    _thread_parts(a.thread)
    os.makedirs(d)
    meta = {"slug": a.slug, "thread": a.thread, "kind": a.kind, "sign": a.sign,
            "created": _dt.date.today().isoformat()}
    with io.open(os.path.join(d, "meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1)
    with io.open(os.path.join(d, "draft.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n\n" + SIGNATURES[a.sign] + "\n")
    with io.open(os.path.join(d, "claims.py"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(CLAIMS_TEMPLATE.replace("SLUG", a.slug))
    print("created %s\nnext: write draft.md and claims.py, then `outbound.py check %s`" % (d, a.slug))


def lint(slug):
    """Deterministic checks. Returns a list of (ok, name, detail)."""
    meta = _meta(slug)
    body = io.open(os.path.join(_dir(slug), "draft.md"), encoding="utf-8").read()
    out = []
    out.append((not re.search("[—–]| -- ", body), "no em or en dash", ""))
    sig = SIGNATURES[meta["sign"]]
    out.append((body.rstrip().endswith(sig), "ends with the %s signature" % meta["sign"], sig))
    if meta["sign"] == "github":
        bad = sorted({c for c in body if ord(c) > 127})
        out.append((not bad, "pure ASCII (gh mangles non-ASCII)", "".join(bad)))
    else:
        out.append(("AI assistance" not in body, "no AI disclosure in the EDRN thread", ""))
    out.append(('alt="Inspeximus seal"' not in body, "draft.md carries no seal (seal adds it)", ""))
    prose = re.sub(r"```.*?```", "", body, flags=re.S)
    long_s = [s for s in re.split(r"(?<=[.!?])\s+|\n", prose) if len(s.split()) > 40]
    out.append((not long_s, "WARN no sentence over 40 words", (long_s[0][:60] + "...") if long_s else ""))
    out.append((len(body.split()) <= 600, "WARN 600 words or fewer", "%d words" % len(body.split())))
    tells = subprocess.run([PY, os.path.join(ROOT, "tools", "humanizer_tells.py"),
                            os.path.join(_dir(slug), "draft.md")],
                           cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out.append((tells.returncode == 0, "humanizer_tells scan (a scanner, not the skill)",
                (tells.stdout or tells.stderr).strip().splitlines()[-1:] and
                (tells.stdout or tells.stderr).strip().splitlines()[-1] or ""))
    return out


def cmd_check(a):
    res = lint(a.slug)
    for ok, name, detail in res:
        tag = "PASS" if ok else ("WARN" if name.startswith("WARN ") else "FAIL")
        print("%s  %s%s" % (tag, name.replace("WARN ", ""), ("  [%s]" % detail) if detail and not ok else ""))
    bad = sum(1 for ok, n, _ in res if not ok and not n.startswith("WARN "))
    print("\n%d of %d checks failed" % (bad, len(res)) if bad else "\nall %d checks pass" % len(res))
    return 1 if bad else 0


GATE_PROMPT = """You are the outbound gate for ONE text. Budget: finish in as few turns as possible.
Draft: {draft}
Thread: {thread}. Signature rule: {sign}.
Claims recompute (already run, deterministic): `python tools/outbound.py seal {slug} --dry-run` output is
in the parent's message if relevant; do not re-run heavy scripts.

Run these three skills IN ORDER, each exactly once, on the draft file, and edit the draft in place:
1. Skill `humanizer`: remove AI-writing patterns. Keep every fact and number. No em dashes.
2. Skill `verify-claims`, inline, no subagents: every number and named fact against the files the
   draft cites. Report CONFIRMED / FALSE per claim. Cut or fix anything not confirmed.
3. Skill `stress-claim`, inline, no subagents: one pass on the argument. Verdict PUBLISH / REFRAME /
   KILL with the single most damaging finding.

Do not read the thread history beyond the last 3 comments. Do not spawn agents. Do not post anything.
Return under 200 words: the three verdicts, what you changed, and the final sha256 of the draft
(python -c "import hashlib;print(hashlib.sha256(open(r'{draft}','rb').read()).hexdigest())")."""


def cmd_gate(a):
    meta = _meta(a.slug)
    draft = os.path.join(_dir(a.slug), "draft.md")
    # .claude/hooks/agent_budget.py refuses any launch whose prompt lacks these two lines, and
    # the quote must be the owner's own words, typed after this budget was shown to him.
    # On the first live run (r91188, 2026-09-25) the prompt lacked them and two launches were
    # refused before the third passed, each refusal a full turn of context.
    print("FIRST tell the owner in one line: BUDGET: 1 gate subagent, model sonnet, about 60k tokens.")
    print("Wait for his yes. Then launch ONE Agent call: subagent_type general-purpose, model sonnet,")
    print("with this prompt, pasting his reply VERBATIM (punctuation included) into the quote:\n")
    print("BUDGET: 1 gate subagent, model sonnet, about 60k tokens")
    print('Owner approved: "<his exact reply>"\n')
    print(GATE_PROMPT.format(draft=draft, thread=meta["thread"], sign=meta["sign"], slug=a.slug))
    print("\nThen record the three receipts from that run's output file (under .../tasks/):")
    for sk in ("humanizer", "verify", "redteam"):
        print("  python tools/humanizer_receipt.py record %s --skill %s --evidence <output file> "
              "--found \"<what the run found>\" --wording-is-final" % (draft, sk))


def cmd_seal(a):
    meta = _meta(a.slug)
    d = _dir(a.slug)
    fails = [n for ok, n, _ in lint(a.slug) if not ok and not n.startswith("WARN ")]
    if fails:
        raise SystemExit("REFUSED: `check` fails (%s). Fix the draft first." % "; ".join(fails))
    draft = os.path.join(d, "draft.md")
    inputs = [draft] + list(a.inputs or [])
    repo, _ = _thread_parts(meta["thread"])
    cmd = [PY, os.path.join(ROOT, "tools", "seal", "seal_draft.py"), draft,
           os.path.join(d, "claims.py"), "--inputs", *inputs, "--label", a.slug,
           "--context", repo, "--out", os.path.join(d, "draft.sealed.md")]
    if a.dry_run:
        cmd.append("--dry-run")
    return _run(cmd)


def _sealed(slug):
    p = os.path.join(_dir(slug), "draft.sealed.md")
    if not os.path.exists(p):
        raise SystemExit("REFUSED: %s does not exist; run `outbound.py seal %s` first." % (p, slug))
    return p


def _publish_cmd(meta):
    repo, num = _thread_parts(meta["thread"])
    return ["gh", meta.get("kind", "issue"), "comment", num, "--repo", repo]


def cmd_show(a):
    meta = _meta(a.slug)
    p = _sealed(a.slug)
    rc = _run([PY, os.path.join(ROOT, "tools", "send_approved.py"), "show", p,
               "--thread", "https://github.com/%s/issues/%s" % _thread_parts(meta["thread"])])
    sha = _sha(p)
    print("\nOWNER: look at the renders seal_draft printed, then answer:  posli %s" % sha[:6])
    return rc


def cmd_post(a):
    meta = _meta(a.slug)
    p = _sealed(a.slug)
    return _run([PY, os.path.join(ROOT, "tools", "send_approved.py"), "post", p, "--sha", a.sha,
                 "--thread", "https://github.com/%s/issues/%s" % _thread_parts(meta["thread"]),
                 "--", *_publish_cmd(meta)])


def _stage(slug):
    d = _dir(slug)
    draft = os.path.join(d, "draft.md")
    body = io.open(draft, encoding="utf-8").read()
    if len(body.split()) < 20:
        return "1 write", "write draft.md and claims.py"
    if any(not ok and not n.startswith("WARN ") for ok, n, _ in lint(slug)):
        return "2 check", "python tools/outbound.py check %s" % slug
    st = subprocess.run([PY, os.path.join(ROOT, "tools", "humanizer_receipt.py"), "status", draft],
                        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if "MISSING" in (st.stdout + st.stderr).upper() or st.returncode != 0:
        return "3 gate", "python tools/outbound.py gate %s" % slug
    if not os.path.exists(os.path.join(d, "draft.sealed.md")):
        return "4 seal", "python tools/outbound.py seal %s --inputs <files>" % slug
    return "5 owner", "python tools/outbound.py show %s  (then post --sha after 'posli <hash>')" % slug


def cmd_status(a):
    slugs = [a.slug] if a.slug else sorted(os.listdir(BASE)) if os.path.isdir(BASE) else []
    if not slugs:
        print("no outbound texts in %s" % BASE)
    for s in slugs:
        if not os.path.exists(os.path.join(_dir(s), "meta.json")):
            continue
        stage, nxt = _stage(s)
        print("%-40s %-9s next: %s" % (s, stage, nxt))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("new"); p.add_argument("slug"); p.add_argument("--thread", required=True)
    p.add_argument("--sign", required=True, choices=sorted(SIGNATURES))
    p.add_argument("--kind", default="issue", choices=("issue", "pr"))
    for name in ("check", "gate", "show"):
        sub.add_parser(name).add_argument("slug")
    p = sub.add_parser("seal"); p.add_argument("slug"); p.add_argument("--inputs", nargs="*", default=[])
    p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("post"); p.add_argument("slug"); p.add_argument("--sha", required=True)
    p = sub.add_parser("status"); p.add_argument("slug", nargs="?")
    a = ap.parse_args(argv)
    return globals()["cmd_" + a.cmd](a) or 0


if __name__ == "__main__":
    sys.exit(main())
