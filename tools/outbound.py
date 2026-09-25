"""One command for one outbound text, from an empty folder to a sent comment.

WHY. On 2026-09-24 a single page of text cost millions of tokens: every step (render, receipt, log,
stamp, SVG, footer, show, post) was composed by hand inside a session whose context was 94% full,
so each small turn re-read the whole conversation. The owner set the budget at under 100k tokens
per text, gate included. Everything that does not need judgment is therefore this file, and costs
no tokens. The only model work left is writing the draft and ONE gate subagent (see
.claude/skills/outbound/SKILL.md).

    python tools/outbound.py new    SLUG --thread owner/repo#N --sign github|edrn [--kind issue|pr]
    python tools/outbound.py check  SLUG      # deterministic lint, 0 tokens
    python tools/outbound.py gate   SLUG [--go] # budget line; --go runs the stripped gate and receipts
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


GATE_PROMPT = """You are the outbound gate for ONE text: {draft}
Thread: {thread}. Signature rule: {sign}. Do not change the signature line.

Invoke these three skills with the Skill tool, IN THIS ORDER, each exactly once. The args of every
Skill call MUST contain the full draft path above, or the receipt cannot be recorded.
1. Skill `verify-claims`, args: "inline, no subagents: {draft}". Check every number and named fact
   against the files the draft cites. Fix or cut anything not confirmed.
2. Skill `stress-claim`, args: "inline, no subagents: {draft}". One pass on the argument.
3. Skill `humanizer`, args: "{draft}". Last, because it only touches wording. Keep every fact and
   number, no em dashes.
Edit the draft in place with Edit. Do not spawn agents, do not use the web, do not post anything.

Then answer in plain text, at least 250 characters, exactly these lines:
VERIFY: <CONFIRMED n/n, or what was fixed>
REDTEAM: <PUBLISH / REFRAME / KILL> <the single most damaging finding>
HUMANIZER: <what changed, or nothing>"""

GATE_FLAGS = ["--output-format", "json", "--strict-mcp-config",
              "--setting-sources", "project", "--tools", "Read,Edit,Skill",
              "--allowedTools", "Read", "Edit", "Skill", "--permission-mode", "acceptEdits"]


def _projects_dir():
    slug = re.sub(r"[:\\/]", "-", os.path.abspath(ROOT))   # C:\Users\x\agora -> C--Users-x-agora
    return os.path.join(os.path.expanduser("~/.claude/projects"), slug)


def cmd_gate(a):
    """Run the gate as ONE stripped `claude -p` call, then record the three receipts from its own
    transcript. Measured 2026-09-25 on a one-word prompt: a default `claude -p` starts at 93,402
    tokens of context, this flag set at 27,617, because it drops the MCP tool schemas, the settings
    hooks and their injected context. The r91188 gate subagent started at 89,393 and ended at 153k.
    """
    meta = _meta(a.slug)
    draft = os.path.join(_dir(a.slug), "draft.md")
    fails = [n for ok, n, _ in lint(a.slug) if not ok and not n.startswith("WARN ")]
    if fails:
        raise SystemExit("REFUSED: `check` fails (%s). Fix the draft first." % "; ".join(fails))
    if not a.go:
        print("BUDGET: 1 stripped `claude -p` gate call, model sonnet, about 30-60k tokens.")
        print("Tell the owner that line, wait for his yes, then run: "
              "python tools/outbound.py gate %s --go" % a.slug)
        return 0
    empty = os.path.join(_dir(a.slug), "nomcp.json")
    with io.open(empty, "w", encoding="utf-8") as fh:
        fh.write('{"mcpServers":{}}')
    prompt = GATE_PROMPT.format(draft=draft, thread=meta["thread"], sign=meta["sign"])
    # On Windows `claude` is claude.CMD, which subprocess cannot start without the full path, and a
    # .CMD runs through cmd.exe, which breaks a multi-line argument at the newline and rewrites %, ^
    # and ". So the path comes from shutil.which and the prompt goes in on stdin, never on argv.
    import shutil
    exe = shutil.which("claude")
    if not exe:
        raise SystemExit("REFUSED: the claude CLI is not on PATH.")
    # Project settings are needed: with --setting-sources "" the project skills do not load and
    # every Skill call returns "Unknown skill" (measured 2026-09-25, both gate runs on r91188).
    # Their hooks are switched off instead, because they inject context into every turn.
    nohooks = os.path.join(_dir(a.slug), "nohooks.json")
    with io.open(nohooks, "w", encoding="utf-8") as fh:
        fh.write('{"disableAllHooks": true}')
    cmd = [exe, "-p", "--model", a.model, *GATE_FLAGS, "--mcp-config", empty, "--settings", nohooks]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", input=prompt, timeout=1800)
    raw = r.stdout or ""
    try:
        res = json.loads(raw[raw.index("{"):])
    except Exception:
        raise SystemExit("gate call returned no JSON (rc %d):\n%s\n%s"
                         % (r.returncode, raw[-800:], r.stderr[-800:]))
    u = res.get("usage", {})
    total_in = u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0) + u.get("cache_read_input_tokens", 0)
    tp = os.path.join(_projects_dir(), res.get("session_id", "") + ".jsonl")
    log = {"model": a.model, "session_id": res.get("session_id"), "transcript": tp, "turns": res.get("num_turns"),
           "input_tokens_all_turns": total_in, "output_tokens": u.get("output_tokens"),
           "usd_equivalent": res.get("total_cost_usd"), "draft_sha256": _sha(draft),
           "result": res.get("result", "")}
    with io.open(os.path.join(_dir(a.slug), "gate.json"), "w", encoding="utf-8") as fh:
        json.dump(log, fh, indent=1)
    print(res.get("result", ""))
    print("\ngate cost: %s input tokens over %s turns, %s output (gate.json)"
          % (total_in, res.get("num_turns"), u.get("output_tokens")))
    found = (res.get("result") or "").strip()
    env = dict(os.environ, CLAUDE_TRANSCRIPT_PATH=tp)
    bad = 0
    for sk in ("verify", "redteam", "humanizer"):
        rc = subprocess.run([PY, os.path.join(ROOT, "tools", "humanizer_receipt.py"), "record", draft,
                             "--skill", sk, "--in-session", "--found", found, "--wording-is-final"],
                            cwd=ROOT, env=env).returncode
        bad += rc != 0
    if bad:
        print("RECEIPTS: %d of 3 refused; read the lines above. Do not work around them." % bad)
        return 1
    print("RECEIPTS: 3 of 3 recorded from %s" % tp)
    return 0


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
    # Repeated as the LAST line on purpose. owner_spoke.py anchors the approval on the harness
    # record of this exact line, and on r91188 a `| tail` cut the copy send_approved prints first,
    # so the owner's first "posli" was refused.
    print("sha256 : %s" % sha)
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
    for name in ("check", "show"):
        sub.add_parser(name).add_argument("slug")
    p = sub.add_parser("gate"); p.add_argument("slug"); p.add_argument("--go", action="store_true")
    p.add_argument("--model", default="sonnet", help="sonnet or opus; gate.json records which, to compare")
    p = sub.add_parser("seal"); p.add_argument("slug"); p.add_argument("--inputs", nargs="*", default=[])
    p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("post"); p.add_argument("slug"); p.add_argument("--sha", required=True)
    p = sub.add_parser("status"); p.add_argument("slug", nargs="?")
    a = ap.parse_args(argv)
    return globals()["cmd_" + a.cmd](a) or 0


if __name__ == "__main__":
    sys.exit(main())
