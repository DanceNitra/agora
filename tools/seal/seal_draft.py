"""Seal an outbound draft in one command: render, recompute, log, seal art, footer, render again.

WHY THIS EXISTS. On 2026-09-24 session 1 sealed three texts by hand (EDRN reply, agmi PR twice), about
ten steps each, and the two failures of that evening were both ORDER and COPY failures: a render done
after sealing found `<sz sz>` stripped as an HTML tag, so the seal had to be redone (log entries 2 and
3), and a footer line was re-described from memory instead of copied from the block already sent
("preco improvizujes?"). Both are things a command does the same way every time and a person does
differently at midnight. See memory `every-outbound-text-carries-the-seal` and
`seal-format-is-the-one-already-sent`.

WHAT IT DOES, in the order the owner fixed:

  1. renders the draft through the GitHub markdown API in both themes, with GitHub's own
     #gh-light-mode-only / #gh-dark-mode-only rules, and STOPS if an HTML-looking tag in the source
     vanished from the render;
  2. runs tools/recompute_receipt.py, then writes the hash-only statement exactly as the existing
     *.log-statement.json files are written;
  3. submits it with inspeximus-repo tools/submit_to_log.py and attaches `log_entry` to the receipt;
  4. takes the last committed light/dark seal pair from DanceNitra/inspeximus docs/seal/, replaces
     ONLY the band text with the new root tail, uploads both, and checks the pinned raw URLs return
     the same bytes;
  5. appends the footer copied from the last SENT sealed text, changing only the image URLs, the
     "N of N planted errors caught" count, the root tail and the date;
  6. renders again in both themes and prints the sha256 and the screenshot paths.

WHAT IT NEVER DOES: post, comment, or open anything outward. The only writes outside this machine are
the log submission and the two SVGs in our own repo, both part of the seal. `tools/send_approved.py`
stays the only send path; this prints the command that starts it.

    python tools/seal/seal_draft.py <draft.md> <claims.py> --inputs a b c [--token T] \
        --label "agmi PR" [--dry-run]

--dry-run stops after step 2, before anything leaves the machine.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
RECEIPTS = os.path.join(ROOT, "agora_output", "recompute_receipts")
RENDERS = os.path.join(ROOT, "agora_output", "seal_drafts")
RECOMPUTE = os.path.join(ROOT, "tools", "recompute_receipt.py")
STAMP = os.path.join(HERE, "stamp.py")

HOME = os.path.expanduser("~")
INSPEXIMUS_REPO = os.environ.get("INSPEXIMUS_REPO", os.path.join(HOME, "inspeximus-repo"))
SUBMITTER_KEY = os.path.join(HOME, ".inspeximus-submitter", "submitter.secret")
SSH_IDENTITY = os.path.join(HOME, ".ssh", "inspeximus_oci")
ISSUER = "urn:agora:builder"

SEAL_REPO = "DanceNitra/inspeximus"
SEAL_DIR = "docs/seal"
# SEALS NEVER MOVE MAIN (2026-09-28). Every seal upload was a commit on inspeximus main, and two of them
# landed during the 3.15.2 and 3.15.3 releases, so `tools/release.py` refused because main had moved, and a
# release had to be rebased and re-run through CI. A seal link is pinned to its commit sha, not to a
# branch, so the SVGs live on this protected branch and the link shape does not change.
SEAL_BRANCH = "seals"
LOGIN = "DanceNitra"
API = "https://api.github.com"
RAW = "https://raw.githubusercontent.com"

# Same marks send_approved.seal_missing() looks for; a sealed draft must pass that gate.
SEAL_MARK = 'alt="Inspeximus seal"'
ROOT_MARK = "Root <code>&hellip;"
TAIL = 12

# Copied from github.com's global CSS on 2026-09-25 (the non-`auto` pair). GitHub hides the
# LINK, not the image, which is why the sent block wraps each <img> in an <a href="...#gh-...">.
GH_THEME_CSS = (
    ":root[data-color-mode=dark] .comment-body [href$=\\#gh-light-mode-only],"
    ":root[data-color-mode=light] .comment-body [href$=\\#gh-dark-mode-only]{display:none}"
)
MD_CSS = "https://cdn.jsdelivr.net/npm/github-markdown-css@5.8.1/github-markdown-%s.css"


# ----------------------------------------------------------------------------------- pure parts

def grouped(root: str) -> str:
    """The band text: the LAST twelve characters of the root in groups of four (stamp.py's rule)."""
    t = root[-TAIL:]
    return " ".join(t[i:i + 4] for i in range(0, len(t), 4))


def build_statement(receipt: dict) -> bytes:
    """The hash-only statement that goes in the log, byte for byte as the existing ones.

    Reproduces all seven *.log-statement.json files written by hand on 2026-09-22..24 from their
    receipts; the test holds that. Hashes and verdicts only: the log is public, the draft is not.
    """
    muts = receipt.get("mutations", [])
    st = {
        "draft_sha256": receipt["draft_sha256"],
        "input_sha256": [i["sha256"] for i in receipt["inputs"]],
        "kind": "agora.recompute-statement/1",
        "mutations": len(muts),
        "mutations_that_broke_a_claim": sum(1 for m in muts if m.get("claims_broken")),
        "receipt_kind": receipt["skill"] + ".recompute",
        "recorded_utc": receipt["recorded_utc"],
        "script_sha256": receipt["script_sha256"],
        "stdout_sha256": receipt["stdout_sha256"],
        "verdicts": {k: (v.get("verdict") if isinstance(v, dict) else v)
                     for k, v in receipt["claims"].items()},
    }
    return (json.dumps(st, indent=2, sort_keys=True) + "\n").encode("utf-8")


def receipt_bytes(receipt: dict) -> bytes:
    """The receipt rewritten with its log_entry, in the format the sealed receipts already use."""
    return (json.dumps(receipt, indent=1, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def log_entry(sub: dict) -> dict:
    """The receipt's `log_entry`, from submit_to_log's record, with the fields the old ones carry."""
    return {
        "inclusion_verified": sub["inclusion_verified"],
        "index": sub["index"],
        "payload_sha256": sub["payload_sha256"],
        "proof": sub["urls"]["proof"],
        "root": sub["root"],
        "statement": sub["document"],
        "statement_sha256": sub["document_sha256"],
        "submitted_utc": sub["submitted_utc"],
        "tree_size": sub["tree_size"],
    }


BAND = re.compile(r"(<text\b[^>]*>)([0-9a-f]{4} [0-9a-f]{4} [0-9a-f]{4})(</text>)")


def replace_band(svg: str, new_root: str) -> str:
    """The previous seal with ONLY its band text changed to the new root tail.

    Refuses unless the art has exactly one band, so a redrawn file with two texts, or none, stops
    here instead of producing a seal with the old tail still in it somewhere.
    """
    hits = BAND.findall(svg)
    if len(hits) != 1:
        raise ValueError("expected exactly one band <text> in the previous seal, found %d" % len(hits))
    new = grouped(new_root)
    return BAND.sub(lambda m: m.group(1) + new + m.group(3), svg)


def band_problems(old_svg: str, new_svg: str, root: str) -> list:
    """Why `new_svg` is not `old_svg` with only the band changed to `root`'s tail; [] when it is."""
    probs = []
    hits = BAND.findall(new_svg)
    if len(hits) != 1:
        return ["the new seal has %d band texts, not 1" % len(hits)]
    if hits[0][1] != grouped(root):
        probs.append("band reads %r, the root tail is %r" % (hits[0][1], grouped(root)))
    old_band = BAND.findall(old_svg)
    if len(old_band) != 1 or new_svg.replace(hits[0][1], old_band[0][1]) != old_svg:
        probs.append("something other than the band text changed")
    return probs


# The four things the footer may change. Everything else is copied, never re-described.
IMG_URL = re.compile(r"%s/%s/([0-9a-f]{40})/%s/([0-9a-f]{12})-seal-(light|dark)\.svg"
                     % (re.escape(RAW), re.escape(SEAL_REPO), re.escape(SEAL_DIR)))
COUNT = re.compile(r"(\d+) of (\d+) planted errors caught")
ROOT_TAIL = re.compile(r"(Root <code>&hellip; )([0-9a-f]{4} [0-9a-f]{4} [0-9a-f]{4})(</code>)")
DATE = re.compile(r"(sealed )(\d{4}-\d{2}-\d{2})")


def footer_of(body: str) -> str:
    """The seal block of a sent text: from the line carrying the seal image to the end."""
    lines = body.replace("\r\n", "\n").rstrip("\n").split("\n")
    at = [i for i, ln in enumerate(lines) if SEAL_MARK in ln]
    if not at:
        raise ValueError("no seal block in that text")
    block = "\n".join(lines[at[0]:]).strip()
    if ROOT_MARK not in block:
        raise ValueError("the seal block has no Root line")
    return block


def substitute_footer(footer: str, commit: str, root: str, caught: int, date: str) -> str:
    """The sent footer with ONLY image URLs, the count, the root tail and the date changed."""
    tail = root[-TAIL:]
    urls = IMG_URL.findall(footer)
    if len(urls) != 4 or sorted(u[2] for u in urls) != ["dark", "dark", "light", "light"]:
        raise ValueError("expected 4 seal URLs (2 light, 2 dark) in the sent footer, found %d" % len(urls))
    for rx, name in ((COUNT, "count"), (ROOT_TAIL, "root line"), (DATE, "date")):
        if len(rx.findall(footer)) != 1:
            raise ValueError("expected exactly one %s in the sent footer" % name)
    out = IMG_URL.sub(lambda m: "%s/%s/%s/%s/%s-seal-%s.svg"
                      % (RAW, SEAL_REPO, commit, SEAL_DIR, tail, m.group(3)), footer)
    out = COUNT.sub("%d of %d planted errors caught" % (caught, caught), out)
    out = ROOT_TAIL.sub(lambda m: m.group(1) + grouped(root) + m.group(3), out)
    out = DATE.sub(lambda m: m.group(1) + date, out)
    return out


def _mask(footer: str) -> str:
    footer = IMG_URL.sub("<URL-\\3>", footer)
    footer = COUNT.sub("<N> of <N> planted errors caught", footer)
    footer = ROOT_TAIL.sub("\\1<TAIL>\\3", footer)
    return DATE.sub("\\1<DATE>", footer)


def footer_problems(sent: str, new: str, commit: str, root: str, caught: int, date: str) -> list:
    """Why `new` is not `sent` with exactly the four allowed changes; [] when it is."""
    probs = []
    if _mask(sent) != _mask(new):
        probs.append("the footer differs from the sent one outside the four allowed fields")
    urls = IMG_URL.findall(new)
    if len(urls) != 4 or any(u[0] != commit or u[1] != root[-TAIL:] for u in urls):
        probs.append("image URLs do not all pin commit %s and tail %s" % (commit[:7], root[-TAIL:]))
    c = COUNT.findall(new)
    if c != [(str(caught), str(caught))]:
        probs.append("count reads %r, expected %d of %d" % (c, caught, caught))
    t = ROOT_TAIL.findall(new)
    if len(t) != 1 or t[0][1] != grouped(root):
        probs.append("root line does not read %s" % grouped(root))
    if [d[1] for d in DATE.findall(new)] != [date]:
        probs.append("date is not %s" % date)
    return probs


def seal_body(draft: bytes, footer: str) -> bytes:
    """The draft, a blank line, the footer, in the draft's own line endings (the agmi PR's shape)."""
    nl = b"\r\n" if b"\r\n" in draft else b"\n"
    body = draft if draft.endswith(nl) else draft + nl
    return body + nl + footer.replace("\n", nl.decode()).encode("utf-8") + nl


TAG = re.compile(r"<([A-Za-z][A-Za-z0-9-]*)(?=[\s/>])")


def vanished_tags(source: str, html: str) -> list:
    """HTML-looking tags in the source that the render dropped, as [(tag, in_source, in_render)].

    A tag either survives (`<small`) or is shown as text (`&lt;sz`); if it does neither, GitHub's
    sanitizer ate it and a reader sees a hole. That is exactly how `<sz sz>` disappeared on
    2026-09-24. Counted per tag name, so a stripped `<sz>` is caught even when another one sits in a
    code span and renders escaped.
    """
    want = {}
    for m in TAG.finditer(source):
        want[m.group(1).lower()] = want.get(m.group(1).lower(), 0) + 1
    low = html.lower()
    out = []
    for tag, n in sorted(want.items()):
        got = len(re.findall(r"<%s(?=[\s/>])" % re.escape(tag), low)) + \
            len(re.findall(r"&lt;%s(?=[\s/&])" % re.escape(tag), low))
        if got < n:
            out.append((tag, n, got))
    return out


# ------------------------------------------------------------------------------------- network

def gh_token() -> str:
    t = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if t:
        return t.strip()
    r = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        raise SystemExit("REFUSED: no GitHub token (gh auth token failed).")
    return r.stdout.strip()


def http(method: str, url: str, token: str | None = None, data=None, accept="application/vnd.github+json",
         ctype="application/json") -> bytes:
    headers = {"User-Agent": "agora-seal-draft/1", "Accept": accept}
    if token:
        headers["Authorization"] = "Bearer " + token
    body = None
    if data is not None:
        body = data if isinstance(data, bytes) else json.dumps(data).encode("utf-8")
        headers["Content-Type"] = ctype
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def api(method, path, token, data=None):
    return json.loads(http(method, API + path, token, data) or b"null")


def render_markdown(text: str, token: str, context: str | None) -> str:
    payload = {"text": text, "mode": "gfm"}
    if context:
        payload["context"] = context
    return http("POST", API + "/markdown", token, payload, accept="text/html").decode("utf-8")


def page(html: str, theme: str) -> str:
    return (
        '<!doctype html><html data-color-mode="%s"><head><meta charset="utf-8">'
        '<link rel="stylesheet" href="%s"><style>%s body{margin:0;background:%s}'
        '.markdown-body{box-sizing:border-box;max-width:780px;padding:24px}</style></head>'
        '<body><div class="markdown-body comment-body">%s</div></body></html>'
        % (theme, MD_CSS % theme, GH_THEME_CSS, "#ffffff" if theme == "light" else "#0d1117", html)
    )


def screenshots(html: str, outdir: str, stem: str) -> tuple:
    """Both themes as PNGs, plus which seal image each theme actually shows."""
    from playwright.sync_api import sync_playwright
    os.makedirs(outdir, exist_ok=True)
    paths, shown = {}, {}
    with sync_playwright() as p:
        br = p.chromium.launch()
        try:
            for theme in ("light", "dark"):
                pg = br.new_page(viewport={"width": 820, "height": 600})
                pg.set_content(page(html, theme), wait_until="networkidle", timeout=60000)
                path = os.path.join(outdir, "%s-%s.png" % (stem, theme))
                pg.screenshot(path=path, full_page=True)
                paths[theme] = path
                shown[theme] = pg.evaluate(
                    """() => [...document.querySelectorAll('img[alt="Inspeximus seal"]')]
                        .filter(i => i.offsetParent !== null && i.getClientRects().length)
                        .map(i => (i.closest('a') || {}).href || i.getAttribute('data-canonical-src') || i.src)""")
                pg.close()
        finally:
            br.close()
    return paths, shown


def render_check(text: str, token: str, context, outdir: str, stem: str) -> tuple:
    html = render_markdown(text, token, context)
    os.makedirs(outdir, exist_ok=True)
    io.open(os.path.join(outdir, stem + ".html"), "w", encoding="utf-8").write(html)
    paths, shown = screenshots(html, outdir, stem)
    return vanished_tags(text, html), paths, shown


def last_seal_pair(token: str) -> tuple:
    """(commit, tail, light_svg, dark_svg): the newest pair in docs/seal/ with both themes."""
    commits = api("GET", "/repos/%s/commits?path=%s&sha=%s&per_page=30" % (SEAL_REPO, SEAL_DIR, SEAL_BRANCH),
                  token)
    rx = re.compile(r"^%s/([0-9a-f]{12})-seal-(light|dark)\.svg$" % re.escape(SEAL_DIR))
    for c in commits:
        files = api("GET", "/repos/%s/commits/%s" % (SEAL_REPO, c["sha"]), token).get("files", [])
        tails = [m.group(1) for f in files for m in [rx.match(f["filename"])] if m]
        for tail in tails:
            try:
                pair = [http("GET", "%s/%s/%s/%s/%s-seal-%s.svg" % (RAW, SEAL_REPO, c["sha"], SEAL_DIR,
                                                                   tail, th)).decode("utf-8")
                        for th in ("light", "dark")]
            except urllib.error.HTTPError:
                continue            # the other theme was committed later; the newer commit has both
            return c["sha"], tail, pair[0], pair[1]
    raise SystemExit("REFUSED: no committed light/dark seal pair in %s/%s." % (SEAL_REPO, SEAL_DIR))


def last_sent_seal(token: str, days: int = 14) -> tuple:
    """(url, created_at, body) of the newest text WE sent that carries the seal.

    Sent means on GitHub, authored by us: an issue or PR body, or a comment. Nothing local records
    sends, and a draft on disk is exactly the thing that may never have gone out.
    """
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    q = urllib.request.quote("involves:%s updated:>=%s" % (LOGIN, since[:10]))
    items = api("GET", "/search/issues?q=%s&sort=updated&per_page=50" % q, token)["items"]
    best = None
    for it in items:
        if it["user"]["login"] == LOGIN and SEAL_MARK in (it.get("body") or ""):
            cand = (it["created_at"], it["html_url"], it["body"])
            best = max(best, cand) if best else cand
        page_n = 1
        while True:
            cs = api("GET", "%s?since=%s&per_page=100&page=%d"
                     % (it["comments_url"].replace(API, ""), since, page_n), token)
            for c in cs:
                if c["user"]["login"] == LOGIN and SEAL_MARK in (c.get("body") or ""):
                    cand = (c["created_at"], c["html_url"], c["body"])
                    best = max(best, cand) if best else cand
            if len(cs) < 100:
                break
            page_n += 1
    if not best:
        raise SystemExit("REFUSED: found no sealed text sent by %s in the last %d days; pass --last-sent."
                         % (LOGIN, days))
    return best[1], best[0], best[2]


def fetch_sent(url: str, token: str) -> tuple:
    """--last-sent: a comment (#issuecomment-N) or an issue/PR URL."""
    m = re.match(r"https://github\.com/([^/]+/[^/]+)/(?:issues|pull)/(\d+)(?:#issuecomment-(\d+))?", url)
    if not m:
        raise SystemExit("REFUSED: --last-sent must be a github.com issue, PR or comment URL.")
    if m.group(3):
        c = api("GET", "/repos/%s/issues/comments/%s" % (m.group(1), m.group(3)), token)
    else:
        c = api("GET", "/repos/%s/issues/%s" % (m.group(1), m.group(2)), token)
    if c["user"]["login"] != LOGIN:
        raise SystemExit("REFUSED: %s was written by %s, not by us." % (url, c["user"]["login"]))
    return url, c["created_at"], c["body"]


def upload(path: str, content: bytes, message: str, token: str) -> str:
    """PUT one file into the seal repo's SEAL_BRANCH; returns the new commit sha. Never overwrites a file,
    and never commits to main."""
    url = "/repos/%s/contents/%s" % (SEAL_REPO, path)
    try:
        cur = api("GET", url + "?ref=" + SEAL_BRANCH, token)
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        cur = None
    if cur is not None:
        raise SystemExit("REFUSED: %s already exists in %s; a root tail is never reused." % (path, SEAL_REPO))
    r = api("PUT", url, token, {"message": message, "content": base64.b64encode(content).decode("ascii"),
                                "branch": SEAL_BRANCH})
    return r["commit"]["sha"]


def verify_pinned(commit: str, name: str, content: bytes, tries: int = 6) -> str:
    url = "%s/%s/%s/%s/%s" % (RAW, SEAL_REPO, commit, SEAL_DIR, name)
    for i in range(tries):
        try:
            if http("GET", url) == content:
                return url
        except urllib.error.HTTPError:
            pass
        time.sleep(5 * (i + 1))
    raise SystemExit("REFUSED: %s does not return the bytes that were uploaded." % url)


# ----------------------------------------------------------------------------------------- main

def has_claims(script_src: str) -> bool:
    """True when the claims script calls claim() outside a comment."""
    return any(re.match(r"\s*claim\(", ln) for ln in script_src.splitlines()
               if not ln.lstrip().startswith("#"))


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("draft", help="the body WITHOUT the seal footer")
    ap.add_argument("script", help="the claims script (recompute_receipt runs it)")
    ap.add_argument("--inputs", nargs="+", required=True)
    ap.add_argument("--token", action="append", default=[], help="passed to recompute_receipt")
    ap.add_argument("--skill", default="verify", choices=["verify", "redteam"])
    ap.add_argument("--label", default="", help='for the seal commit messages, e.g. "agmi PR"')
    ap.add_argument("--context", default=None, help="owner/repo for the markdown render (issue links)")
    ap.add_argument("--last-sent", default=None, help="URL of the sent sealed text to copy the footer from")
    ap.add_argument("--out", default=None, help="sealed file (default <draft>.sealed.md)")
    ap.add_argument("--dry-run", action="store_true", help="stop before the log submission")
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(line_buffering=True)   # our lines and the subprocesses' stay in order

    draft = io.open(a.draft, "rb").read()
    text = draft.decode("utf-8")
    if SEAL_MARK in text:
        raise SystemExit("REFUSED: the draft already carries a seal block; pass the body without it.")
    dsha = sha(draft)
    outdir = os.path.join(RENDERS, dsha[:16])
    token = gh_token()

    # 1. RENDER FIRST. A tag the sanitizer eats changes the bytes, and bytes are what get sealed.
    print("[1/6] render the draft (GitHub markdown API, light and dark)")
    gone, shots, _ = render_check(text, token, a.context, outdir, "1-draft")
    for th, p in shots.items():
        print("    %-5s %s" % (th, p))
    if gone:
        for tag, n, got in gone:
            print("    BROKEN: <%s ...> appears %d time(s) in the source, %d in the render" % (tag, n, got))
        print("STOPPED: fix the draft (escape the tag or put it in `code`) and run again. Nothing was logged.")
        return 1

    # 2. RECOMPUTE, then the hash-only statement.
    print("[2/6] recompute_receipt")
    rpath = os.path.join(RECEIPTS, dsha[:32] + "." + a.skill + ".recompute.json")
    # Receipts are named by the draft's hash, so sealing the same bytes again (even a --dry-run)
    # overwrote the logged receipt of a text already sent. Measured 2026-09-25 on 58b45601; the
    # original was rebuilt only because the log kept its statement hash.
    if os.path.isfile(rpath) and "log_entry" in json.load(io.open(rpath, encoding="utf-8")):
        raise SystemExit("REFUSED: %s is already logged for these exact bytes. This text was sealed "
                         "before; do not seal it again." % os.path.relpath(rpath, ROOT))
    script_src = io.open(a.script, encoding="utf-8").read()
    if not has_claims(script_src):
        # A text with no figure has nothing to recompute. Owner, 2026-09-25: a five-sentence reply
        # was refused here until a claim was invented for it. The seal still logs the draft's hash
        # and time, and the footer reads "0 of 0".
        print("    no CLAIM in %s: nothing to recompute; the seal records the draft's hash and time"
              % os.path.basename(a.script))
        receipt = {"claims": {}, "draft_sha256": dsha,
                   "inputs": [{"sha256": dsha}], "mutations": [],
                   "recorded_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "script_sha256": sha(script_src.encode("utf-8")), "skill": a.skill,
                   "stdout_sha256": sha(b"")}
        # A fresh worktree has no agora_output/recompute_receipts (it is not tracked), and the write
        # raised FileNotFoundError there. recompute_receipt.py makes the folder on the other path.
        os.makedirs(RECEIPTS, exist_ok=True)
        io.open(rpath, "wb").write(receipt_bytes(receipt))
        caught = 0
    else:
        cmd = [sys.executable, "-X", "utf8", RECOMPUTE, a.draft, a.script, "--inputs"] + a.inputs + \
            sum([["--token", t] for t in a.token], []) + ["--skill", a.skill]
        r = subprocess.run(cmd, cwd=ROOT)
        if r.returncode != 0:
            print("STOPPED: recompute_receipt refused. Nothing was logged.")
            return 1
        receipt = json.load(io.open(rpath, encoding="utf-8"))
        muts = receipt["mutations"]
        caught = sum(1 for m in muts if m.get("claims_broken"))
        if caught != len(muts) or not muts:
            raise SystemExit("REFUSED: %d of %d mutations broke a claim." % (caught, len(muts)))
    spath = os.path.join(RECEIPTS, dsha[:16] + ".log-statement.json")
    statement = build_statement(receipt)
    io.open(spath, "wb").write(statement)
    print("    statement %s  sha256 %s" % (os.path.relpath(spath, ROOT), sha(statement)))
    if a.dry_run:
        print("DRY RUN: stopped before the log submission. Receipt %s" % os.path.relpath(rpath, ROOT))
        return 0

    # 3. LOG.
    print("[3/6] submit_to_log")
    subpath = os.path.join(RECEIPTS, dsha[:16] + ".log-submission.json")
    r = subprocess.run([sys.executable, os.path.join(INSPEXIMUS_REPO, "tools", "submit_to_log.py"), spath,
                        "--issuer", ISSUER, "--subject", "urn:agora:recompute:" + dsha[:16],
                        "--key", SUBMITTER_KEY, "--identity", SSH_IDENTITY, "--out", subpath])
    if r.returncode != 0 or not os.path.isfile(subpath):
        raise SystemExit("REFUSED: the log submission did not verify; see above.")
    sub = json.load(io.open(subpath, encoding="utf-8"))
    if not sub.get("inclusion_verified") or sub.get("document_sha256") != sha(statement):
        raise SystemExit("REFUSED: the log entry does not verify against this statement.")
    receipt["log_entry"] = log_entry(sub)
    io.open(rpath, "wb").write(receipt_bytes(receipt))
    root = sub["root"]
    r = subprocess.run([sys.executable, "-X", "utf8", STAMP, a.draft, "--receipt", rpath, "--format", "text"],
                       cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise SystemExit("REFUSED by stamp.py: " + (r.stdout + r.stderr).strip())
    print("    entry %d, root %s" % (sub["index"], root))

    # 4. SEAL ART: the previous pair, band text only.
    print("[4/6] seal SVGs")
    prev_commit, prev_tail, light, dark = last_seal_pair(token)
    tail = root[-TAIL:]
    label = a.label or os.path.splitext(os.path.basename(a.draft))[0]
    new = {}
    for th, old in (("light", light), ("dark", dark)):
        svg = replace_band(old, root)
        probs = band_problems(old, svg, root)
        if probs:
            raise SystemExit("REFUSED: %s seal: %s" % (th, "; ".join(probs)))
        new[th] = svg.encode("utf-8")
    commit = None
    for th in ("light", "dark"):
        commit = upload("%s/%s-seal-%s.svg" % (SEAL_DIR, tail, th), new[th],
                        "seal: %s, transparent, %s theme (%s, log entry %d)"
                        % (grouped(root), th, label, sub["index"]), token)
    for th in ("light", "dark"):
        print("    %s" % verify_pinned(commit, "%s-seal-%s.svg" % (tail, th), new[th]))
    print("    from %s (%s)" % (prev_tail, prev_commit[:7]))

    # 5. FOOTER copied from the last sent block.
    print("[5/6] footer")
    url, when, body = fetch_sent(a.last_sent, token) if a.last_sent else last_sent_seal(token)
    sent_footer = footer_of(body)
    date = dt.date.today().isoformat()
    footer = substitute_footer(sent_footer, commit, root, caught, date)
    probs = footer_problems(sent_footer, footer, commit, root, caught, date)
    if probs:
        raise SystemExit("REFUSED: footer: " + "; ".join(probs))
    sealed = seal_body(draft, footer)
    out = a.out or os.path.splitext(a.draft)[0] + ".sealed.md"
    io.open(out, "wb").write(sealed)
    print("    copied from %s (%s)" % (url, when))
    # What GitHub already drops from the SENT block is the format as it shipped, not a new break.
    # Measured 2026-09-25: <small> is stripped in all three sent seals, so those lines render at
    # body size. Changing that is the owner's call; the tool reports it and copies the block as is.
    inherited = {t for t, _, _ in vanished_tags(sent_footer, render_markdown(sent_footer, token, None))}

    # 6. RENDER AGAIN, and check each theme shows its own seal.
    print("[6/6] render the sealed text")
    gone, shots, shown = render_check(sealed.decode("utf-8"), token, a.context, outdir, "6-sealed")
    for th, p in shots.items():
        print("    %-5s %s" % (th, p))
    for t in sorted(inherited):
        print("    NOTE: GitHub strips <%s> from the sent footer too; it renders as plain text there." % t)
    bad = [(tag, n, got) for tag, n, got in gone if tag not in inherited]
    for th in ("light", "dark"):
        if len(shown[th]) != 1 or not shown[th][0].split("#")[0].endswith("-seal-%s.svg" % th):
            bad.append(("seal", th, shown[th]))
    if bad:
        print("BROKEN after sealing: %r" % bad)
        return 1
    print("")
    print("SEALED  %s" % out)
    print("sha256  %s" % sha(sealed))
    print("next    python tools/send_approved.py show %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
