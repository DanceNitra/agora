"""
The Correspondent — first contact, gated.

The Salon listens; the Correspondent SPEAKS and listens to the answer. Claude composes a
sharp public post from the system's strongest belief (the claim, the evidence, the falsifier,
and an explicit "what would break this?"), and ONLY after the owner approves the gated
`outreach` action does it get posted — as a GitHub issue on the public agora repo, where real
people can reply. Replies are harvested daily and fed back as named external challenge.
The GitHub token comes from the git credential manager in-process and is never logged.
"""
from __future__ import annotations

import json
import re
import subprocess
import time
import urllib.request
import uuid
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".correspondence.json"
_REPO = "DanceNitra/agora"


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


# ── Novelty guard: stop templated outreach (same stats / same self-promo plug / copy-pasted
#    sentences across different threads) — that reads as astroturf and erodes the credibility the
#    genuine engagement was meant to build. Surfaced in the gated proposal BEFORE anything posts. ──
_PLUG_RX = re.compile(r"open[- ]?source|reference implementation|zero[- ]?dependency|\bmnemo\b", re.I)
_NUM_RX = re.compile(r"\d+(?:\.\d+)?\s?(?:x|×|%)", re.I)


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text or "") if len(s.strip()) > 25]


def _toks(s: str) -> set:
    return {w for w in re.findall(r"[a-z0-9.]+", (s or "").lower()) if len(w) > 2}


def _containment(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def novelty_report(body: str, exclude_id: str | None = None) -> dict:
    """Compare a new outreach body against our already-public posts. Returns an overlap level +
    the specific repeated sentences / reused stats / reused self-promo so the owner can tailor."""
    priors = [x for x in _load() if x.get("id") != exclude_id and x.get("body")
              and x.get("status") in ("posted", "proposed", "draft")]
    new_sents = _sentences(body)
    new_tok = [_toks(s) for s in new_sents]
    new_nums = set(n.replace(" ", "") for n in _NUM_RX.findall(body or ""))
    worst_ov, worst_p = 0.0, None
    repeated: list[dict] = []
    prior_nums: set = set()
    for p in priors:
        p_tok = [_toks(s) for s in _sentences(p["body"])]
        prior_nums |= set(n.replace(" ", "") for n in _NUM_RX.findall(p["body"] or ""))
        where = f"{p.get('target_repo') or 'agora'}#{p.get('target_issue') or p.get('issue_number') or '?'}"
        dup = 0
        for i, t in enumerate(new_tok):
            if max((_containment(t, pt) for pt in p_tok), default=0.0) >= 0.6:
                dup += 1
                repeated.append({"sentence": new_sents[i][:110], "where": where})
        ov = dup / len(new_tok) if new_tok else 0.0
        if ov > worst_ov:
            worst_ov, worst_p = ov, p
    reused_stats = sorted(new_nums & prior_nums)
    reused_plug = bool(_PLUG_RX.search(body or "")) and any(_PLUG_RX.search(p["body"] or "") for p in priors)
    seen, reps = set(), []
    for r in repeated:
        if r["sentence"] not in seen:
            seen.add(r["sentence"]); reps.append(r)
    level = ("HIGH" if (worst_ov >= 0.5 or (len(reused_stats) >= 2 and reused_plug))
             else "MED" if (worst_ov >= 0.3 or reused_stats or reused_plug) else "OK")
    worst_match = (f"{worst_p.get('target_repo') or 'agora'}#"
                   f"{worst_p.get('target_issue') or worst_p.get('issue_number') or '?'}") if worst_p else None
    return {"level": level, "max_overlap": round(worst_ov, 2), "worst_match": worst_match,
            "repeated_sentences": reps[:4], "reused_stats": reused_stats, "reused_plug": reused_plug}


def format_novelty(nr: dict) -> str:
    if not nr or nr.get("level") == "OK":
        return ""
    icon = "🚨" if nr["level"] == "HIGH" else "⚠️"
    lines = [f"{icon} Novelty {nr['level']} — overlaps our earlier public posts:"]
    if nr.get("worst_match") and nr["max_overlap"] > 0:
        lines.append(f"• {int(nr['max_overlap']*100)}% sentence overlap with {nr['worst_match']}")
    if nr.get("reused_stats"):
        lines.append(f"• reused stats: {', '.join(nr['reused_stats'])}")
    if nr.get("reused_plug"):
        lines.append("• repeats the open-source/mnemo plug used before")
    if nr.get("repeated_sentences"):
        lines.append(f'• e.g. "{nr["repeated_sentences"][0]["sentence"]}…"')
    lines.append("Tailor to THEIR specific point; plug sparingly.")
    return "\n".join(lines)


def _github_token() -> str:
    """PAT from the git credential manager — same trust surface as `git push`. Never logged."""
    r = subprocess.run(["git", "credential", "fill"],
                       input="protocol=https\nhost=github.com\n\n",
                       capture_output=True, text=True, timeout=20)
    return next((l[9:] for l in (r.stdout or "").splitlines()
                 if l.startswith("password=")), "")


_our_login_cache = {"login": ""}


def our_login() -> str:
    """The GitHub account Agora posts as — so a reply that QUOTES our footer is not mistaken for
    our own comment (the bug that hid the first real zeroclaw reply). Cached; falls back to the
    repo owner."""
    if _our_login_cache["login"]:
        return _our_login_cache["login"]
    try:
        u = _api("GET", "/user")
        _our_login_cache["login"] = (u.get("login") or "DanceNitra")
    except Exception:
        _our_login_cache["login"] = "DanceNitra"
    return _our_login_cache["login"]


def _api(method: str, path: str, body: dict | None = None) -> dict:
    tok = _github_token()
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        data=json.dumps(body).encode() if body else None, method=method,
        headers={"Authorization": "token " + tok, "User-Agent": "agora-correspondent",
                 "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def save_draft(title: str, body: str, repo: str = "", issue_number: int = 0) -> dict:
    """Store Claude's composed outreach; the caller proposes the gated action around it.
    With repo+issue_number set, this is a COMMENT on an external issue, not a new issue."""
    rec = {"id": uuid.uuid4().hex[:6], "title": title[:160], "body": body[:6000],
           "status": "draft", "replies_seen": 0, "ts": time.time()}
    if repo and issue_number:
        rec["target_repo"] = repo[:80]
        rec["target_issue"] = int(issue_number)
    items = _load()
    items.append(rec)
    _save(items[-40:])
    return rec


def get_draft(corr_id: str) -> dict | None:
    return next((x for x in _load() if x.get("id") == corr_id), None)


def post_outreach(corr_id: str) -> dict:
    """POST the approved draft (called ONLY from the gated executor): a COMMENT when the draft
    targets an external repo issue, else a new issue on our public repo."""
    items = _load()
    rec = next((x for x in items if x.get("id") == corr_id), None)
    if not rec or rec.get("status") not in ("draft", "proposed"):
        return {"error": "no postable draft"}
    footer = ("\n\n---\n*Drafted by [Agora](https://github.com/DanceNitra/agora), an autonomous "
              "research OS, and posted with its owner's review and approval.*")
    if rec.get("target_repo") and rec.get("target_issue"):
        c = _api("POST", f"/repos/{rec['target_repo']}/issues/{rec['target_issue']}/comments",
                 {"body": rec["body"] + footer})
        rec["issue_url"] = c.get("html_url", "")
        rec["issue_number"] = rec["target_issue"]
    else:
        issue = _api("POST", f"/repos/{_REPO}/issues",
                     {"title": rec["title"], "body": rec["body"] + footer})
        rec["issue_number"] = issue.get("number")
        rec["issue_url"] = issue.get("html_url", "")
    rec["status"] = "posted"
    rec["posted_ts"] = time.time()
    _save(items)
    return {"status": "posted", "url": rec["issue_url"]}


def _iso_to_ts(iso: str) -> float:
    try:
        from datetime import datetime, timezone
        return datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    except Exception:
        return 0.0


def harvest_replies() -> list[dict]:
    """New comments on posted correspondences — named external challenge coming home.
    External threads (target_repo) are read from THAT repo; only comments created after our
    post count as replies, and Agora's own footer-marked comments are excluded so the loop
    never feeds on its own words."""
    items = _load()
    fresh = []
    for rec in items:
        if rec.get("status") != "posted" or not rec.get("issue_number"):
            continue
        repo = rec.get("target_repo") or _REPO
        posted = rec.get("posted_ts", 0)
        try:
            comments = _api("GET", f"/repos/{repo}/issues/{rec['issue_number']}/comments"
                            f"?per_page=100")
        except Exception:
            continue
        mine_login = our_login().lower()
        replies = [c for c in comments
                   if _iso_to_ts(c.get("created_at") or "") > posted
                   and (c.get("user") or {}).get("login", "").lower() != mine_login]
        new = replies[rec.get("replies_seen", 0):]
        for c in new:
            fresh.append({"corr_id": rec["id"], "title": rec["title"],
                          "repo": repo, "issue": rec["issue_number"],
                          "by": (c.get("user") or {}).get("login", "?"),
                          "text": (c.get("body") or "")[:500]})
        rec["replies_seen"] = len(replies)
    if fresh:
        _save(items)
    return fresh


def format_correspondence() -> str:
    items = _load()
    if not items:
        return "✉️ _No correspondence yet — the first letter is unwritten._"
    icon = {"draft": "📝", "proposed": "⏸️", "posted": "📮"}
    lines = ["✉️ *The Correspondent*"]
    for r in items[-6:]:
        lines.append(f"{icon.get(r['status'], '•')} [{r['status']}] {r['title'][:60]}")
        if r.get("issue_url"):
            lines.append(f"   {r['issue_url']} · {r.get('replies_seen', 0)} replies")
    return "\n".join(lines)
