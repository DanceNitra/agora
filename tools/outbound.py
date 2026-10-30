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
    python tools/outbound.py status [SLUG]    # where every text stands; "sent" is read from the thread

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
PREGATE = os.path.join(ROOT, "agora_output", "pregate")
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
    """The gh command that publishes this text.

    A text that OPENS a pull request is not a comment on one. Without this branch the command came
    out as `gh pr comment <thread>`, which would have posted a catalog submission into an unrelated
    issue in the same repository -- the thread that only exists so the pregate has prior statements
    to compare against. `creates` says the destination does not exist yet; send_approved already
    recognises `gh pr create` and runs its new-thread gate instead of the repeat check.
    """
    repo, num = _thread_parts(meta["thread"])
    c = meta.get("creates") or {}
    if c:
        missing = [k for k in ("repo", "title", "head", "base") if not c.get(k)]
        if missing:
            raise SystemExit("REFUSED: meta.creates is missing %s" % ", ".join(missing))
        return ["gh", meta.get("kind", "pr"), "create", "--repo", c["repo"],
                "--title", c["title"], "--head", c["head"], "--base", c["base"]]
    return ["gh", meta.get("kind", "issue"), "comment", num, "--repo", repo]


def _pregate(slug):
    """Run tools/pregate.py on the draft, so send_approved finds a receipt for every figure.

    send_approved refuses a draft whose distinctive figures no pregate run on this thread has
    seen; on r91188 the only receipt was an older claims file from the same thread, and the post
    was refused. The draft itself is the claims file, as it was for the agmi PR.
    """
    meta = _meta(slug)
    out = os.path.join(PREGATE, "outbound_%s.json" % slug)
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
    add("author receipt binds the draft", *_quiet(sa._the_gate, p))
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
            try:
                hit = live_match(meta["thread"], stdin)
            except LiveReadFailed:
                hit = None
            if hit:
                out[-1] = ("SENT", out[-1][1], "this exact text is already %s" % hit[1])
    return out


class LiveReadFailed(RuntimeError):
    """gh could not read a thread, so nothing can be said about whether a text went out."""


def _gh_list(path):
    """Every item of one paginated GET, as (id, html_url, login, body). Read-only by construction.

    The argv names `--method GET` and carries no field, input or header flag, so it cannot write;
    tests/test_outbound.py asserts that shape. Raises LiveReadFailed when gh exits non-zero, so an
    unreadable thread is never reported as a thread without our text.
    """
    cmd = ["gh", "api", "--method", "GET", path, "--paginate",
           "--jq", ".[] | [.id, .html_url, .user.login, .body] | @json"]
    r = subprocess.run(cmd, capture_output=True, timeout=120)
    if r.returncode != 0:
        raise LiveReadFailed("gh api %s exited %d: %s" % (
            path, r.returncode, r.stderr.decode("utf-8", "replace").strip()[-160:]))
    return [tuple(json.loads(ln)) for ln in r.stdout.decode("utf-8").splitlines() if ln.strip()]


_LOGIN = []


def _our_login():
    """The account gh posts as, read once per process with a GET."""
    if not _LOGIN:
        r = subprocess.run(["gh", "api", "--method", "GET", "user", "--jq", ".login"],
                           capture_output=True, timeout=60)
        login = r.stdout.decode("utf-8", "replace").strip()
        if r.returncode != 0 or not login:
            raise LiveReadFailed("gh api user exited %d" % r.returncode)
        _LOGIN.append(login)
    return _LOGIN[0]


def live_match(thread, payload, cache=None):
    """(id, html_url) of the live text by our account whose body is PAYLOAD byte for byte, or None.

    Compared by sha256, with no normalisation: measured 2026-09-28, all six texts that went out
    match their draft.sealed.md exactly, so a looser comparison would only add false positives.
    Two places can hold a text we sent: a comment on THREAD, and the body of an issue or PR our
    account opened in the same repository. lantern-outcome-questions is the second kind: its meta
    thread is a closed PR, and it went out as the new issue Lantern-svg/lantern#2. Raises
    LiveReadFailed when a read fails.
    """
    repo, num = _thread_parts(thread)
    want = hashlib.sha256(payload).hexdigest()
    me = _our_login()
    cache = {} if cache is None else cache
    for path in ("repos/%s/issues/%s/comments" % (repo, num),
                 "repos/%s/issues?creator=%s&state=all" % (repo, me)):
        if path not in cache:
            cache[path] = _gh_list(path)
        for cid, url, login, body in cache[path]:
            if login == me and hashlib.sha256((body or "").encode("utf-8")).hexdigest() == want:
                return cid, url
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


def _pregate_record(slug):
    try:
        return json.load(io.open(os.path.join(PREGATE, "outbound_%s.json" % slug), encoding="utf-8"))
    except Exception:                                               # noqa: BLE001
        return {}


def _write_sent(slug, cid, url, sha):
    """Keep what the live read found in SLUG/sent.json, for the record only.

    Nothing reads this file back to decide a stage. A file in our own folder is not the
    destination: on 2026-08-18 a retraction was called unsent because of where its file sat, while
    it had been public for two days. `status` asks the thread every time.
    """
    p = os.path.join(_dir(slug), "sent.json")
    rec = {"id": cid, "url": url, "draft_sealed_sha256": sha}
    try:
        old = json.load(io.open(p, encoding="utf-8"))
        if all(old.get(k) == v for k, v in rec.items()):
            return
    except Exception:                                               # noqa: BLE001
        pass
    rec["verified_at"] = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rec["how"] = "outbound.py status: sha256 of the live body, read with gh api --method GET"
    tmp = p + ".tmp"
    with io.open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rec, fh, indent=1)
    os.replace(tmp, p)


def _stage(slug, cache=None):
    """(stage, next) for one text. The live thread decides "sent"; local files decide the rest.

    6 sent         a live comment or issue body by our account is draft.sealed.md byte for byte.
    ? gh failed    the thread could not be read, so the text is neither sent nor safe to post.
    x killed       the pregate record names an existing .DEAD copy (send_approved.record_killed).
    ! unconfirmed  a record claims a comment id, but no live text equals draft.sealed.md.
    1 to 5         the local steps: write, check, gate, seal, owner.

    Until 2026-09-28 a `sent` field in the pregate record closed a text on its own word. A file is
    not the destination, so that field now only raises "! unconfirmed" when the thread disagrees.
    """
    d = _dir(slug)
    sealed = os.path.join(d, "draft.sealed.md")
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import send_approved as sa
    if os.path.exists(sealed):
        meta = _meta(slug)
        with open(sealed, "rb") as fh:
            payload = fh.read()
        sha = hashlib.sha256(payload).hexdigest()
        try:
            hit = live_match(meta["thread"], payload, cache)
        except LiveReadFailed as ex:
            return "? gh failed", "do not post; re-run status when gh can read %s (%s)" % (
                meta["thread"], ex)
        if hit:
            _write_sent(slug, hit[0], hit[1], sha)
            return "6 sent %s" % hit[0], "nothing; draft.sealed.md sha256 %s is %s" % (sha[:12], hit[1])
    rec = _pregate_record(slug)
    dead = sa.record_killed(rec)
    if dead:
        return "x killed", "nothing; abandoned, see %s" % dead
    claimed = sa.record_sent(rec)
    if claimed:
        return "! unconfirmed", ("the pregate record says %s, but no live text by us equals "
                                 "draft.sealed.md; read %s before any post"
                                 % (claimed, _meta(slug)["thread"]))
    draft = os.path.join(d, "draft.md")
    body = io.open(draft, encoding="utf-8").read()
    if len(body.split()) < 20:
        return "1 write", "write draft.md and claims.py"
    if any(not ok and not n.startswith("WARN ") for ok, n, _ in lint(slug)):
        return "2 check", "python tools/outbound.py check %s" % slug
    import author_receipt
    if author_receipt.check(draft):
        return "3 gate", "python tools/outbound.py gate %s" % slug
    if not os.path.exists(sealed):
        return "4 seal", "python tools/outbound.py seal %s --inputs <files>" % slug
    return "5 owner", "python tools/outbound.py show %s  (then post --sha after 'posli <hash>')" % slug


def cmd_status(a):
    slugs = [a.slug] if a.slug else sorted(os.listdir(BASE)) if os.path.isdir(BASE) else []
    if not slugs:
        print("no outbound texts in %s" % BASE)
    cache = {}
    for s in slugs:
        if not os.path.exists(os.path.join(_dir(s), "meta.json")):
            continue
        stage, nxt = _stage(s, cache)
        print("%-40s %-18s next: %s" % (s, stage, nxt))


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
