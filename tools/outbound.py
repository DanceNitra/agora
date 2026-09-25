"""One command for one outbound text, from an empty folder to a sent comment.

WHY. On 2026-09-24 a single page of text cost millions of tokens: every step (render, receipt, log,
stamp, SVG, footer, show, post) was composed by hand inside a session whose context was 94% full,
so each small turn re-read the whole conversation. The owner set the budget at under 100k tokens
per text, gate included. Everything that does not need judgment is therefore this file, and costs
no tokens. The only model work is writing the draft. The author model (Opus 5.5) answers for its
content; since 2026-09-25 there is no separate gate call (see .claude/skills/outbound/SKILL.md).

    python tools/outbound.py new    SLUG --thread owner/repo#N --sign github|edrn [--kind issue|pr]
    python tools/outbound.py check  SLUG      # deterministic lint, 0 tokens
    python tools/outbound.py gate   SLUG      # author receipt: the writing model answers for it, 0 tokens
    python tools/outbound.py seal   SLUG --inputs FILE... [--dry-run]
    python tools/outbound.py show   SLUG      # render paths + hash for the owner
    python tools/outbound.py dryrun SLUG [--sha HASH] [--offline]  # every send check, nothing sent
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
    return out


def cmd_check(a):
    res = lint(a.slug)
    for ok, name, detail in res:
        tag = "PASS" if ok else ("WARN" if name.startswith("WARN ") else "FAIL")
        print("%s  %s%s" % (tag, name.replace("WARN ", ""), ("  [%s]" % detail) if detail and not ok else ""))
    bad = sum(1 for ok, n, _ in res if not ok and not n.startswith("WARN "))
    print("\n%d of %d checks failed" % (bad, len(res)) if bad else "\nall %d checks pass" % len(res))
    return 1 if bad else 0


def cmd_gate(a):
    """Record that the author model answers for this draft. Deterministic, no model call, 0 tokens.

    Owner, 2026-09-25: the separate `claude -p` gate cost 0.39 USD on a five-sentence reply with
    nothing to check, and "za content bude zodpovedat OPUS 5.5". The model that writes the draft
    verifies its own facts while writing it; this step only binds the draft's sha256 to that model.
    The free checks stay: `check` before this, the seal's figure recompute after it, and the
    owner's "posli <hash>" on the render.
    """
    draft = os.path.join(_dir(a.slug), "draft.md")
    fails = [n for ok, n, _ in lint(a.slug) if not ok and not n.startswith("WARN ")]
    if fails:
        raise SystemExit("REFUSED: `check` fails (%s). Fix the draft first." % "; ".join(fails))
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import author_receipt
    rec = author_receipt.record(draft, a.author)
    print("gate: %s answers for every fact, figure and word in %s (sha %s). No model call."
          % (rec["author"], draft, rec["draft_sha256"][:16]))
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
    if _pregate(a.slug) != 0:
        raise SystemExit("REFUSED: pregate flagged a claim (read the lines above). Fix the draft first.")
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


def _pregate(slug):
    """Run tools/pregate.py on the draft, so send_approved finds a receipt for every figure.

    send_approved refuses a draft whose distinctive figures no pregate run on this thread has
    seen; on r91188 the only receipt was an older claims file from the same thread, and the post
    was refused. The draft itself is the claims file, as it was for the agmi PR.
    """
    meta = _meta(slug)
    out = os.path.join(ROOT, "agora_output", "pregate", "outbound_%s.json" % slug)
    return _run([PY, os.path.join(ROOT, "tools", "pregate.py"), os.path.join(_dir(slug), "draft.md"),
                 "--thread", meta["thread"], "--json", out])


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
                 "--", *_publish_cmd(meta), "--body-file", p])


def _quiet(fn, *args):
    """Call one send_approved check with its printout captured. Returns (result, printout)."""
    import contextlib

    class _Buf(io.StringIO):
        def reconfigure(self, **kw):      # pregate.py reconfigures stdout when it is imported
            pass
    buf = _Buf()
    with contextlib.redirect_stdout(buf):
        try:
            res = fn(*args)
        except Exception as ex:                                     # noqa: BLE001
            res = "raised %s: %s" % (type(ex).__name__, ex)
    return res, buf.getvalue()


def dryrun_checks(slug, sha=None, offline=False):
    """Every check `send_approved.py post` runs, in its order, with nothing published.

    Returns a list of (status, name, detail). status is PASS, FAIL, SKIP or WAIT. WAIT marks the
    owner-spoke check, which cannot pass before the owner answers `show`, so it never fails a dry
    run. The checks are the send path's own functions, imported, never re-typed here, so a dry run
    cannot drift from what `post` will do.
    """
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import send_approved as sa
    import owner_spoke as osp
    meta = _meta(slug)
    p = os.path.join(_dir(slug), "draft.sealed.md")
    if not os.path.exists(p):
        return [("FAIL", "sealed file exists", "run `outbound.py seal %s` first" % slug)]
    thread = "https://github.com/%s/issues/%s" % _thread_parts(meta["thread"])
    cmd = _publish_cmd(meta) + ["--body-file", p]
    out = []

    def add(name, res, text="", wait=False):
        if res is None or res == "":
            out.append(("PASS", name, ""))
        else:
            tail = [ln.strip() for ln in text.strip().splitlines() if ln.strip()][-3:]
            why = res if isinstance(res, str) else " | ".join(tail)
            out.append(("WAIT" if wait else "FAIL", name, why))

    add("seal block present", sa.seal_missing(io.open(p, encoding="utf-8").read()))
    now = sa.digest(p)
    if sha:
        add("sha matches the approved hash", None if sha.strip().lower() == now
            else "approved %s, current %s" % (sha.strip().lower()[:12], now[:12]))
    else:
        out.append(("SKIP", "sha matches the approved hash", "no --sha; current %s" % now[:12]))
    ok, why = osp.check(now, draft=p)
    add("owner spoke after show", None if ok else why, wait=True)
    bound = sa.bind_payload(p, cmd)
    add("payload bound to the file", bound if isinstance(bound, str) else None)
    stdin = bound[1] if not isinstance(bound, str) else io.open(p, "rb").read()
    add("pregate receipts for every figure", *_quiet(sa._pregate_gate, p, thread))
    add("gate receipts (verify, redteam, humanizer)", *_quiet(sa._the_gate, p))
    add("humanizer_tells on the payload", *_quiet(sa._tells_gate, stdin.decode("utf-8", "replace"),
                                                   False, True))
    if sa._creates_a_thread(cmd):
        add("no duplicate thread", *_quiet(sa._new_thread_gate, p, cmd, False))
    elif offline:
        out.append(("SKIP", "thread open, nothing new since the draft", "--offline"))
        out.append(("SKIP", "no overlap with our prior comments", "--offline"))
    else:
        add("thread open, nothing new since the draft",
            *_quiet(sa._thread_moved_gate, p, cmd, thread, False))
        add("no overlap with our prior comments", *_quiet(sa._prior_gate, p, cmd, thread, False))
        # A text that already went out overlaps the comment it became, by construction. That is
        # the check working, not a defect in the text, so it is named SENT, and only when a
        # comment in the thread is this payload byte for byte.
        if out[-1][0] == "FAIL":
            cid = _landed_as(meta["thread"], stdin)
            if cid:
                out[-1] = ("SENT", out[-1][1], "this exact text is already comment %s" % cid)
    return out


def _landed_as(thread, payload):
    """The id of a comment in THREAD whose body is PAYLOAD byte for byte, or None."""
    repo, num = _thread_parts(thread)
    r = subprocess.run(["gh", "api", "repos/%s/issues/%s/comments" % (repo, num), "--paginate",
                        "--jq", ".[] | [.id, .body] | @json"], capture_output=True, timeout=120)
    for line in r.stdout.decode("utf-8", "replace").splitlines():
        try:
            cid, body = json.loads(line)
        except Exception:                                           # noqa: BLE001
            continue
        if body.encode("utf-8").strip() == payload.strip():
            return cid
    return None


def cmd_dryrun(a):
    res = dryrun_checks(a.slug, a.sha, a.offline)
    for st, name, why in res:
        print("%-4s  %s%s" % (st, name, ("  [%s]" % why) if why and st != "PASS" else ""))
    bad = sum(1 for st, _, _ in res if st == "FAIL")
    sent = any(st == "SENT" for st, _, _ in res)
    print("\nDRY RUN: %s%s. Nothing was published."
          % ("%d check(s) FAIL" % bad if bad else "every check passes",
             "; this text was already sent, do not post it again" if sent else ""))
    return 1 if bad else 0


def _stage(slug):
    d = _dir(slug)
    draft = os.path.join(d, "draft.md")
    body = io.open(draft, encoding="utf-8").read()
    if len(body.split()) < 20:
        return "1 write", "write draft.md and claims.py"
    if any(not ok and not n.startswith("WARN ") for ok, n, _ in lint(slug)):
        return "2 check", "python tools/outbound.py check %s" % slug
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import author_receipt
    if author_receipt.check(draft):
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
    p = sub.add_parser("gate"); p.add_argument("slug"); p.add_argument("--author", default="claude-opus-5-5")
    p = sub.add_parser("seal"); p.add_argument("slug"); p.add_argument("--inputs", nargs="*", default=[])
    p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("post"); p.add_argument("slug"); p.add_argument("--sha", required=True)
    p = sub.add_parser("dryrun"); p.add_argument("slug"); p.add_argument("--sha")
    p.add_argument("--offline", action="store_true", help="skip the two checks that read the thread")
    p = sub.add_parser("status"); p.add_argument("slug", nargs="?")
    a = ap.parse_args(argv)
    return globals()["cmd_" + a.cmd](a) or 0


if __name__ == "__main__":
    sys.exit(main())
