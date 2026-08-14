"""
The Press — the company's storefront.

The engine produces results that die in the vault: a measured phase-diagram for causal
inference, a graded AI×biology bridge, failed replications when they come. The Press turns the
best of them into polished standalone posts in the public repo's `public/posts/` — every piece
carries its falsifier and its accountability line, because publishing claims without exposure
is marketing, and we are not a marketing department. Strictly gated: Claude drafts, the owner
approves from Telegram, only then does anything leave the machine.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".press.json"
AGORA_REPO = Path(__file__).resolve().parents[3]
POSTS_REL = "public/posts"
_REPO_URL = "https://github.com/DanceNitra/agora/blob/main"


def _load() -> list:
    try:
        return json.loads(_STORE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(items: list) -> None:
    try:
        _STORE.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def _slug(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9 -]", "", (text or "")).strip().lower()
    return re.sub(r"[ _]+", "-", s)[:60] or "post"


def _derive_desc(body: str) -> str:
    """First real paragraph of the piece → the post's SEO/og description + index excerpt."""
    for para in (body or "").split("\n\n"):
        t = para.strip()
        if not t or t[0] in "#|>":
            continue
        t = re.sub(r"[*`#>\[\]]", "", t).replace("\n", " ").strip()
        if len(t) > 40:
            return t[:200]
    return (body or "").strip()[:200]


def save_piece(title: str, body: str, source_note: str = "", *, body_sk: str = "",
               desc: str = "", desc_sk: str = "", title_sk: str = "") -> dict:
    """Store Claude's polished piece; the caller proposes the gated 'press' action around it.
    Bilingual EN+SK: pass body_sk (and optionally desc/desc_sk/title_sk) so publish_piece renders
    the SK version too — the site's standing requirement is that public posts are EN+SK."""
    rec = {"id": uuid.uuid4().hex[:6], "title": (title or "")[:160], "body": (body or "")[:12000],
           "source": (source_note or "")[:160], "status": "draft", "ts": time.time()}
    if body_sk:
        rec["body_sk"] = body_sk[:12000]
    if desc:
        rec["desc"] = desc[:300]
    if desc_sk:
        rec["desc_sk"] = desc_sk[:300]
    if title_sk:
        rec["title_sk"] = title_sk[:160]
    items = _load()
    items.append(rec)
    _save(items[-60:])
    return rec


def covered_titles() -> list[str]:
    return [x.get("title", "") for x in _load()]


def publish_piece(pid: str) -> dict:
    """PUBLISH (call only from an approved gated action): write the piece into public/posts/,
    commit ONLY that file, push. Returns the public URL."""
    items = _load()
    rec = next((x for x in items if x.get("id") == pid), None)
    if not rec or rec.get("status") not in ("draft", "proposed"):
        return {"error": "no publishable piece"}
    slug = _slug(rec["title"])
    date = time.strftime("%Y-%m-%d")
    rel_md = f"{POSTS_REL}/{date}-{slug}.md"          # markdown source archive
    dst = AGORA_REPO / rel_md
    dst.parent.mkdir(parents=True, exist_ok=True)
    footer = ("\n\n---\n*Published by [Agora](https://github.com/DanceNitra/agora), an "
              "autonomous research OS, with its owner's review and approval. Every claim above "
              "ships with the test that would kill it.*\n")
    body_md = rec["body"] + footer
    dst.write_text(body_md, encoding="utf-8")

    # Render the polished standalone HTML post + rebuild the publication index, reusing the same
    # editorial template as the hand-curated posts (English-only renders mono-lingual).
    html_rel = f"{POSTS_REL}/{slug}.html"
    rendered = False
    try:
        spec = {"slug": slug, "title": rec["title"], "desc": _derive_desc(rec["body"]),
                "date": date, "tags": "Research", "kicker": "Research", "body": body_md}
        if rec.get("body_sk"):                        # bilingual EN+SK when a Slovak version exists
            sk_footer = ("\n\n---\n*Publikované [Agorou](https://github.com/DanceNitra/agora), "
                         "autonómnym výskumným OS, so súhlasom a kontrolou majiteľa. Každé tvrdenie "
                         "vyššie prichádza s testom, ktorý by ho vyvrátil.*\n")
            spec["body_sk"] = rec["body_sk"] + sk_footer
            spec["title_sk"] = rec.get("title_sk") or rec["title"]
            spec["desc_sk"] = rec.get("desc_sk") or _derive_desc(rec["body_sk"])
            spec["kicker_sk"] = "Výskum"
            spec["tags_sk"] = "Výskum"
        tmp = AGORA_REPO / "tools" / f"_press_{pid}.json"
        tmp.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        r = subprocess.run([sys.executable, "-X", "utf8",
                            str(AGORA_REPO / "tools" / "render_post.py"), "--piece", str(tmp)],
                           capture_output=True, text=True, timeout=120)
        tmp.unlink(missing_ok=True)
        rendered = r.returncode == 0
        if not rendered:
            # FAIL CLOSED. render_post.py runs publish_gate.enforce(), which signals a construction
            # refusal by raising SystemExit(1) -- deliberately, "because a caller that forgets to
            # check a return value is exactly the failure this file exists to remove". This caller
            # turned that refusal into `rendered = False` and then committed and pushed `rel_md`
            # anyway: the gate's verdict changed the FORM of the publication (markdown instead of
            # HTML) and not WHETHER it published. A number whose probe could not have contradicted
            # it went out as raw markdown, and the owner was told "published".
            #
            # There is no safe way to tell a gate refusal from a renderer crash by exit code alone,
            # so BOTH now stop the publish. A piece that cannot be rendered is not a piece that is
            # ready to go out.
            dst.unlink(missing_ok=True)
            return {"error": ("render/gate refused (exit %d) — nothing was committed or pushed. "
                              "Fix the finding it reports, then re-propose.\n%s"
                              % (r.returncode, (r.stdout or "")[-600:]))}
    except Exception as e:
        dst.unlink(missing_ok=True)
        return {"error": f"render failed: {str(e)[:200]} — nothing was committed or pushed"}

    def _git(*args):
        return subprocess.run(["git", "-C", str(AGORA_REPO), *args],
                              capture_output=True, text=True, timeout=60)
    add = [rel_md] + ([html_rel, f"{POSTS_REL}/index.html", f"{POSTS_REL}/posts.json"]
                      if rendered else [])
    from agora.execution.public_repo import commit_and_push
    g = commit_and_push(AGORA_REPO, add, f"Press: {rec['title'][:60]}")
    if g.get("error"):
        return {"error": g["error"]}
    if g.get("note"):
        return {"error": "nothing to commit (identical piece already published?)"}
    rec["status"] = "published"
    rec["url"] = (f"https://dancenitra.github.io/agora/{html_rel}" if rendered
                  else f"{_REPO_URL}/{rel_md}")
    rec["published_ts"] = time.time()
    _save(items)
    return {"url": rec["url"], "rendered": rendered}


#: How far back a press candidate may sit. Was 7 days, which excluded all four falsifier-bearing
#: notes in the vault and admitted exactly one that had none. `covered_titles()` is what prevents
#: a re-publish; the date never was.
_PRESS_WINDOW_DAYS = 90


def _has_falsifier(text: str) -> bool:
    """THE SAME DEFINITION THE PRESS GATE USES. If the ranker had its own notion of what counts as a
    falsifier it would order candidates by a rule the consumer does not apply, which is how the
    single-head version failed in the first place -- ranked on one quantity, gated on another. Three
    copies of "grounded" already disagreed on 7 of 8 forms in this codebase; this one does not fork.
    """
    try:
        from agora.execution.grounding import has_falsifier
        return bool(has_falsifier(text or ""))
    except Exception:
        # A missing shared definition must not silently promote every note as if it qualified.
        return False


def pick_targets(vault: str, n: int = 8) -> list:
    """SEVERAL press candidates, best first. The consumer has its OWN gates and must walk past one it
    cannot use.

    HEAD-OF-LINE BLOCKING, the fourth site of this defect today. `pick_target` scored every eligible
    note and returned only `best`, while Mira's press arm applies FOUR further gates after receiving
    it -- score floor, readable source, Lab grounding, and a stated falsifier -- and terminates the
    whole arm on the first refusal. One candidate offered, four ways to reject it.

    Worse, the ranker and the gate optimise for different things. Score weights a percentage 3x and
    the word "measured" 2x but a falsifier only 1x, so the highest-scoring note is systematically
    likely to be one WITHOUT the falsifier the press template demands. Measured 2026-08-01: Mira
    returned `idle` with "source note for 'Bridge AI Competitive Moat x Biostatistics...' has no
    falsifier" while other eligible notes sat unoffered in the same directory.

    `replication.pick_targets` already fixed exactly this shape and its docstring says what the
    single-head version cost: three agents on head-only endpoints were the three producing nothing.
    The fix was never carried here.
    """
    src = Path(vault) / "04 Resources" / "Concepts" / "Agora Agents"
    if not src.is_dir():
        return []
    covered = {t[:50].lower() for t in covered_titles()}
    # THE WINDOW WAS STARVING THE ARM, and it was never the thing preventing a re-publish --
    # `covered_titles()` is. Measured 2026-08-01 over 3,915 notes in the agent directory: 58 carry a
    # press-eligible prefix, and of those FOUR state a falsifier. All four are older than 30 days, so
    # a 7-day cutoff excluded every candidate that could pass the press gate and admitted exactly one
    # that could not. The arm reported "no falsifier" and idled, correctly, on the only note it was
    # allowed to see.
    # An unpublished measured result does not expire. Recency is kept as the last tie-break so fresh
    # work still wins among equals, rather than as a filter that hides the only publishable evidence.
    cutoff = time.time() - _PRESS_WINDOW_DAYS * 86400
    out = []
    for p in src.rglob("*.md"):
        stem = p.stem.lower()
        if not stem.startswith(("lab-", "bridge-", "analogy-", "dossier-", "dialectic-")):
            continue
        try:
            if p.stat().st_mtime < cutoff:
                continue
            text = p.read_text(encoding="utf-8", errors="replace")[:4000]
        except Exception:
            continue
        tm = re.search(r"^title:\s*[\"']?(.+?)[\"']?\s*$", text[:500], re.MULTILINE)
        title = (tm.group(1) if tm else p.stem).strip()
        if title[:50].lower() in covered:
            continue
        # measured numbers make a piece publishable, not just readable
        low = text.lower()
        score = (3 * len(re.findall(r"\d+(?:\.\d+)?\s*%", text))
                 + 2 * low.count("measured")
                 + 2 * low.count("lab ")
                 + low.count("falsifier"))
        # RANK ON WHAT THE CONSUMER REQUIRES. A note with no falsifier cannot pass the press gate at
        # any score, so ordering it above notes that can is ordering by the wrong quantity. This is a
        # tie-break, not a filter: a note without one still appears, just below every note with one,
        # so the arm can still report honestly when nothing in the vault is publishable.
        has_fals = _has_falsifier(text)
        out.append({"title": title[:140], "path": str(p), "score": score,
                    "has_falsifier": has_fals, "mtime": p.stat().st_mtime})
    out.sort(key=lambda x: (x["has_falsifier"], x["score"], x["mtime"]), reverse=True)
    return out[:max(1, int(n))]


def pick_target(vault: str) -> dict | None:
    """The strongest unpublished artifact. Kept as the head of `pick_targets` so existing callers keep
    working; a caller with its own gates must walk the list instead."""
    ts = pick_targets(vault, n=1)
    return ts[0] if ts else None


def format_press() -> str:
    items = _load()
    if not items:
        return "📰 _The press is quiet — no piece has been drafted yet._"
    pub = sum(1 for x in items if x.get("status") == "published")
    lines = [f"📰 *The Press* — {pub} published / {len(items)} drafted"]
    icon = {"draft": "📝", "proposed": "⏸️", "published": "📣"}
    for x in items[-6:][::-1]:
        lines.append(f"{icon.get(x['status'], '•')} [{x['status']}] {x['title'][:58]}")
        if x.get("url"):
            lines.append(f"    {x['url']}")
    return "\n".join(lines)
