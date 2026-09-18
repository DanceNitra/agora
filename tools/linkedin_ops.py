#!/usr/bin/env python3
"""State for the LinkedIn operation: the queue of ready posts, the day's batch, the ledger, the limits.

The operation runs in a Claude Code session driven by a scheduled task (see
.claude/skills/linkedin-day/SKILL.md). The session reads LinkedIn through the owner's Chrome,
writes a daily batch here, the owner approves the batch with one word, and the session clicks.
This file holds what a session must not carry in its head: what was posted, to whom, when, and
how much is allowed today.

    python tools/linkedin_ops.py queue                    posts ready to go out (receipted, unposted)
    python tools/linkedin_ops.py batch new [--date D]     start today's batch file
    python tools/linkedin_ops.py batch add <kind> --target URL --author "Name" --slug S --text-file F
    python tools/linkedin_ops.py batch check [--date D]   limits + derive_post check on every item
    python tools/linkedin_ops.py batch show [--date D]    the approval card, as text
    python tools/linkedin_ops.py batch approve [--date D] --words "<the owner's exact words>"
    python tools/linkedin_ops.py posted <item-id> --url URL   record a click that happened
    python tools/linkedin_ops.py report [--days 7]        what went out, what came back
    python tools/linkedin_ops.py telegram "<text>"        one message to the owner
    python tools/linkedin_ops.py selftest

Limits (tools/linkedin_ops.py LIMITS), all per calendar day unless stated: comments on other
people's posts, own posts per week, minimum minutes between two outbound clicks, no second
comment under the same author inside 7 days. They exist because LinkedIn rate-limits accounts
and detects automation patterns; the bundle's algorithm-heuristics.md is the source.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DERIV = ROOT / "agora_output" / "derivatives"
OPS = ROOT / "agora_output" / "linkedin"
BATCHES = OPS / "batches"
LEDGER = OPS / "ledger.jsonl"
ENV = ROOT / "server" / ".env"

LIMITS = {
    "comments_per_day": 6,        # start low; the bundle's 10 to 20 is for a warmed account
    "own_posts_per_week": 2,
    "min_minutes_between_clicks": 4,
    "same_author_cooldown_days": 7,
    "comment_chars": (150, 450),   # the bundle says 200 to 350; one measured fact plus a question needs the room
    "post_chars": (700, 1900),
}
KINDS = ("comment", "reply", "post")
LINKEDIN_URL = re.compile(r"^https://www\.linkedin\.com/")


def _now() -> datetime:
    return datetime.now().astimezone()


def _day(d: str | None) -> str:
    return d or _now().strftime("%Y-%m-%d")


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _ledger() -> list[dict]:
    if not LEDGER.exists():
        return []
    return [json.loads(l) for l in LEDGER.read_text(encoding="utf-8").splitlines() if l.strip()]


def _ledger_append(row: dict) -> None:
    OPS.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _batch_path(d: str) -> Path:
    return BATCHES / f"{d}.json"


def _load_batch(d: str) -> dict:
    p = _batch_path(d)
    if not p.exists():
        sys.exit(f"no batch for {d}; run: batch new")
    return json.loads(p.read_text(encoding="utf-8"))


def _save_batch(b: dict) -> None:
    BATCHES.mkdir(parents=True, exist_ok=True)
    _batch_path(b["date"]).write_text(json.dumps(b, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------- queue

def cmd_queue(_a) -> int:
    """Derivatives whose linkedin.md carries a humanizer receipt and no posted row."""
    posted = {r.get("slug") for r in _ledger() if r.get("kind") == "post" and r.get("status") == "posted"}
    rows = []
    for d in sorted(DERIV.iterdir()) if DERIV.exists() else []:
        li = d / "linkedin.md"
        if not li.exists() or "## Post" not in li.read_text(encoding="utf-8"):
            continue
        st = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "tools" / "humanizer_receipt.py"), "status", str(li)],
                            capture_output=True, text=True, cwd=ROOT)
        ok = bool(re.search(r"^\s*YES\s+humanizer", st.stdout, re.M))
        rows.append((d.name, ok, d.name in posted))
    for slug, ok, was in rows:
        print(f"{'posted ' if was else 'READY  ' if ok else 'no-rcpt'}  {slug}")
    return 0


# ---------------------------------------------------------------- batch

def cmd_batch_new(a) -> int:
    d = _day(a.date)
    if _batch_path(d).exists() and not a.force:
        sys.exit(f"batch {d} exists; use --force to start over")
    _save_batch({"date": d, "created": _now().isoformat(), "items": [], "approved": None})
    print(f"batch {d} started: {_batch_path(d)}")
    return 0


def cmd_batch_add(a) -> int:
    d = _day(a.date)
    b = _load_batch(d)
    text = Path(a.text_file).read_text(encoding="utf-8").strip()
    if a.kind not in KINDS:
        sys.exit(f"kind must be one of {KINDS}")
    if a.kind != "post" and not LINKEDIN_URL.match(a.target or ""):
        sys.exit("a comment or reply needs --target https://www.linkedin.com/...")
    item = {
        "id": f"{d}-{len(b['items']) + 1:02d}",
        "kind": a.kind,
        "target": a.target,
        "author": a.author or "",
        "slug": a.slug,
        "text": text,
        "sha": _sha(text),
        "why": a.why or "",
        "status": "drafted",
    }
    b["items"].append(item)
    _save_batch(b)
    print(f"added {item['id']} {a.kind} -> {a.author or a.target or a.slug}")
    return 0


def _check_item(it: dict, ledger: list[dict], day: str) -> list[str]:
    errs = []
    lo, hi = LIMITS["post_chars"] if it["kind"] == "post" else LIMITS["comment_chars"]
    n = len(it["text"])
    if not lo <= n <= hi:
        errs.append(f"length {n} outside {lo}-{hi}")
    if "—" in it["text"] or "–" in it["text"]:
        errs.append("em or en dash")
    if it["kind"] != "post" and re.search(r"inspeximus", it["text"], re.I):
        errs.append("names the product in a comment on someone else's post")
    if it["kind"] != "post" and re.search(r"https?://", it["text"]):
        errs.append("a link in a comment")
    if it["kind"] == "post" and re.search(r"https?://", it["text"]):
        errs.append("a link in the post body (it belongs in the first comment)")
    m = re.match(r"\s*[^.!?\n]*([.!?])", it["text"])
    if m and m.group(1) == "?":
        errs.append("opens with a question")
    # numbers only from the named article
    if it.get("slug"):
        tmp = OPS / ".check_tmp.md"
        tmp.write_text(it["text"], encoding="utf-8")
        r = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "tools" / "derive_post.py"), "check", it["slug"], str(tmp)],
                           capture_output=True, text=True, cwd=ROOT)
        tmp.unlink(missing_ok=True)
        if r.returncode != 0:
            errs.append("derive_post: " + " ".join(r.stdout.split())[:200])
    elif re.search(r"\d", it["text"]):
        errs.append("carries a number but names no --slug to check it against")
    # cooldown on the same author
    if it["kind"] == "comment" and it.get("author"):
        since = (datetime.fromisoformat(day) - timedelta(days=LIMITS["same_author_cooldown_days"])).date()
        for r in ledger:
            if r.get("kind") == "comment" and r.get("author") == it["author"] and r.get("status") == "posted":
                if datetime.fromisoformat(r["at"]).date() >= since:
                    errs.append(f"commented under {it['author']} on {r['at'][:10]} (cooldown {LIMITS['same_author_cooldown_days']} d)")
                    break
    return errs


def cmd_batch_check(a) -> int:
    d = _day(a.date)
    b = _load_batch(d)
    ledger = _ledger()
    bad = 0
    comments = [it for it in b["items"] if it["kind"] == "comment"]
    if len(comments) > LIMITS["comments_per_day"]:
        print(f"FAIL  {len(comments)} comments > {LIMITS['comments_per_day']} per day"); bad += 1
    week_ago = (_now() - timedelta(days=7)).isoformat()
    own = sum(1 for r in ledger if r.get("kind") == "post" and r.get("status") == "posted" and r["at"] >= week_ago)
    own += sum(1 for it in b["items"] if it["kind"] == "post")
    if own > LIMITS["own_posts_per_week"]:
        print(f"FAIL  {own} own posts in 7 days > {LIMITS['own_posts_per_week']}"); bad += 1
    for it in b["items"]:
        errs = [] if it.get("status") == "posted" else _check_item(it, ledger, d)  # what went out is not re-judged
        it["check"] = errs
        print(("ok    " if not errs else "FAIL  ") + f"{it['id']} {it['kind']:7s} {it['author'] or it['slug']}" + ("" if not errs else "\n        " + "\n        ".join(errs)))
        bad += bool(errs)
    _save_batch(b)
    return 1 if bad else 0


def cmd_batch_show(a) -> int:
    d = _day(a.date)
    b = _load_batch(d)
    print(_card(b))
    return 0


def _card(b: dict) -> str:
    out = [f"LinkedIn batch {b['date']}: {len(b['items'])} items" + (f", approved {b['approved']['at'][:16]}" if b.get("approved") else ", NOT approved")]
    for it in b["items"]:
        head = f"\n[{it['id']}] {it['kind'].upper()}"
        if it["kind"] == "post":
            head += f"  (article: {it['slug']})"
        else:
            head += f"  under {it['author'] or '?'}  {it['target']}"
        if it.get("why"):
            head += f"\n  why: {it['why']}"
        if it.get("check"):
            head += "\n  CHECK FAILED: " + "; ".join(it["check"])
        out.append(head + "\n  ---\n  " + it["text"].replace("\n", "\n  ") + "\n  ---")
    return "\n".join(out)


def cmd_batch_approve(a) -> int:
    d = _day(a.date)
    b = _load_batch(d)
    if not a.words or len(a.words.strip()) < 2:
        sys.exit("--words must carry the owner's exact words")
    if any(it.get("check") for it in b["items"]) or any("check" not in it for it in b["items"]):
        sys.exit("run `batch check` and clear every FAIL before approving")
    b["approved"] = {"at": _now().isoformat(), "words": a.words}
    for it in b["items"]:
        it["status"] = "approved"
    _save_batch(b)
    print(f"batch {d} approved: {len(b['items'])} items may go out, {LIMITS['min_minutes_between_clicks']} min apart")
    return 0


# ---------------------------------------------------------------- ledger

def cmd_posted(a) -> int:
    d = a.item_id[:10]
    b = _load_batch(d)
    it = next((x for x in b["items"] if x["id"] == a.item_id), None)
    if not it:
        sys.exit(f"no item {a.item_id} in batch {d}")
    if not b.get("approved"):
        sys.exit("batch not approved; nothing may be recorded as posted")
    last = [r for r in _ledger() if r.get("status") == "posted"]
    if last:
        gap = (_now() - datetime.fromisoformat(last[-1]["at"])).total_seconds() / 60
        if gap < LIMITS["min_minutes_between_clicks"] and not a.force:
            sys.exit(f"last click {gap:.1f} min ago; wait {LIMITS['min_minutes_between_clicks']} min (or --force with a reason)")
    it["status"] = "posted"
    it["url"] = a.url
    _save_batch(b)
    _ledger_append({"at": _now().isoformat(), "id": it["id"], "kind": it["kind"], "author": it.get("author"),
                    "target": it.get("target"), "slug": it.get("slug"), "sha": it["sha"], "url": a.url, "status": "posted"})
    print(f"recorded {it['id']} posted at {a.url}")
    return 0


def cmd_report(a) -> int:
    since = (_now() - timedelta(days=a.days)).isoformat()
    rows = [r for r in _ledger() if r["at"] >= since]
    by = {}
    for r in rows:
        by[r["kind"]] = by.get(r["kind"], 0) + 1
    print(f"last {a.days} days: " + ", ".join(f"{k} {v}" for k, v in sorted(by.items())) if rows else f"last {a.days} days: nothing went out")
    for r in rows:
        print(f"  {r['at'][:16]} {r['kind']:7s} {r.get('author') or r.get('slug') or ''}  {r.get('url') or ''}")
    return 0


def telegram(text: str) -> bool:
    try:
        raw = ENV.read_text(encoding="utf-8", errors="replace")
        tok = re.search(r'TELEGRAM[_A-Z]*TOKEN\s*=\s*"?([^"\r\n]+)', raw).group(1).strip()
        chat = re.search(r'TELEGRAM[_A-Z]*CHAT[_A-Z]*ID\s*=\s*"?([^"\r\n]+)', raw).group(1).strip()
        data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
        urllib.request.urlopen("https://api.telegram.org/bot" + tok + "/sendMessage", data=data, timeout=30)
        return True
    except Exception as e:  # noqa: BLE001
        print(f"telegram failed: {e}", file=sys.stderr)
        return False


def cmd_telegram(a) -> int:
    return 0 if telegram(a.text) else 1


# ---------------------------------------------------------------- selftest

def cmd_selftest(_a) -> int:
    import tempfile
    global OPS, BATCHES, LEDGER
    with tempfile.TemporaryDirectory() as td:
        OPS, BATCHES, LEDGER = Path(td), Path(td) / "b", Path(td) / "l.jsonl"
        d = "2026-01-05"
        b = {"date": d, "created": "x", "items": [], "approved": None}
        def add(kind, text, author=None, slug=None, target="https://www.linkedin.com/posts/x"):
            author = author or f"Author{len(b['items'])}"
            b["items"].append({"id": f"{d}-{len(b['items'])+1:02d}", "kind": kind, "target": target, "author": author,
                               "slug": slug, "text": text, "sha": _sha(text), "why": "", "status": "drafted"})
        add("comment", "Fine comment, no number, no link, states one thing the author left out and asks what their stack does on delete. " * 2, author="A")
        add("comment", "Comment with a dash — in it and a link https://x.y and it names inspeximus. " * 2)
        add("comment", "Does this open with a question? Then more words to reach the minimum length of the comment body here. " * 2)
        add("comment", "Comment that carries 1,020 writes as a number but names no slug so it cannot be checked. " * 2)
        _save_batch(b)
        ledger = [{"at": "2026-01-03T09:00:00+01:00", "kind": "comment", "author": "A", "status": "posted"}]
        r = [_check_item(it, ledger, d) for it in b["items"]]
        assert any("cooldown" in e for e in r[0]) and len(r[0]) == 1, r[0]
        assert any("dash" in e for e in r[1]) and any("link" in e for e in r[1]) and any("product" in e for e in r[1]), r[1]
        assert any("question" in e for e in r[2]), r[2]
        assert any("no --slug" in e for e in r[3]), r[3]
        # approval refuses unchecked and failed batches
        try:
            cmd_batch_approve(argparse.Namespace(date=d, words="ok")); raise SystemExit("approve must refuse")
        except SystemExit as e:
            assert "FAIL" in str(e) or "check" in str(e), e
        # length and post-link rules
        assert any("length" in e for e in _check_item({"kind": "comment", "text": "short", "author": "", "slug": None}, [], d))
        assert any("first comment" in e for e in _check_item({"kind": "post", "text": "x" * 800 + " https://a.b", "author": "", "slug": None}, [], d))
    print("selftest ok: 9 checks")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest="cmd", required=True)
    s.add_parser("queue").set_defaults(fn=cmd_queue)
    bp = s.add_parser("batch"); bs = bp.add_subparsers(dest="bcmd", required=True)
    x = bs.add_parser("new"); x.add_argument("--date"); x.add_argument("--force", action="store_true"); x.set_defaults(fn=cmd_batch_new)
    x = bs.add_parser("add"); x.add_argument("kind"); x.add_argument("--date"); x.add_argument("--target"); x.add_argument("--author")
    x.add_argument("--slug"); x.add_argument("--text-file", required=True); x.add_argument("--why"); x.set_defaults(fn=cmd_batch_add)
    x = bs.add_parser("check"); x.add_argument("--date"); x.set_defaults(fn=cmd_batch_check)
    x = bs.add_parser("show"); x.add_argument("--date"); x.set_defaults(fn=cmd_batch_show)
    x = bs.add_parser("approve"); x.add_argument("--date"); x.add_argument("--words", required=True); x.set_defaults(fn=cmd_batch_approve)
    x = s.add_parser("posted"); x.add_argument("item_id"); x.add_argument("--url", required=True); x.add_argument("--force", action="store_true"); x.set_defaults(fn=cmd_posted)
    x = s.add_parser("report"); x.add_argument("--days", type=int, default=7); x.set_defaults(fn=cmd_report)
    x = s.add_parser("telegram"); x.add_argument("text"); x.set_defaults(fn=cmd_telegram)
    s.add_parser("selftest").set_defaults(fn=cmd_selftest)
    a = p.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
