"""
falsified_digest.py - the "what we falsified" digest (roadmap #5). Every FAILED verdict in the AI-Claim
Crucible is shareable news. This diffs the ledger against what was already surfaced, writes a digest of the
NEW FAILED (+ REPRODUCED/NOT_COMPUTABLE counts), and suggests venues. GATED: it never posts - it produces
copy for the owner to review and share (and a Telegram heads-up when there is something new).

Run weekly (or after new entries):  python tools/falsified_digest.py
"""
import json, os, re, hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, "agora_output", "aiclaims", "aiclaims.json")
SEEN = os.path.join(ROOT, "agora_output", "aiclaims", "_digest_seen.json")
OUT = os.path.join(ROOT, "agora_output", "aiclaims", "falsified_digest.md")
PAGE = "https://dancenitra.github.io/agora/public/ai-claims/"
DATASET = "https://huggingface.co/datasets/Danchi17/folklore-index"
VENUES = ["Hacker News (Show HN / a comment on a relevant RAG/agent thread)",
          "r/MachineLearning, r/LocalLLaMA, r/Rag (a finding post, not a plug)",
          "X / LinkedIn (one chart + the measured number)"]


def _key(claim):
    return hashlib.sha1(claim.strip().lower().encode("utf-8")).hexdigest()[:12]


def _punchline(note):
    """First measured-ish sentence of the note (the shareable number)."""
    s = re.split(r"(?<=[.])\s", note.strip())
    for part in s:
        if re.search(r"\d", part):
            return part.strip()[:240]
    return (s[0] if s else "")[:240]


def main():
    entries = json.load(open(LEDGER, encoding="utf-8")).get("entries", [])
    seen = json.load(open(SEEN, encoding="utf-8")) if os.path.exists(SEEN) else {}
    by = {"REPRODUCED": 0, "FAILED": 0, "NOT_COMPUTABLE": 0}
    for e in entries:
        by[e.get("verdict", "")] = by.get(e.get("verdict", ""), 0) + 1
    new_failed = [e for e in entries if e.get("verdict") == "FAILED" and _key(e.get("claim", "")) not in seen]

    lines = ["# Falsified this cycle - the AI-Claim Crucible\n",
             f"Ledger now: {by['REPRODUCED']} REPRODUCED / {by['FAILED']} FAILED / {by['NOT_COMPUTABLE']} NOT_COMPUTABLE.",
             f"Public page: {PAGE}  ·  dataset: {DATASET}\n"]
    if not new_failed:
        lines.append("_No new FAILED verdicts since the last digest._")
    else:
        lines.append(f"## {len(new_failed)} new FAILED verdict(s) worth sharing\n")
        for e in new_failed:
            lines.append(f"### {e.get('claim','')[:120]}")
            lines.append(f"**FAILED.** {_punchline(e.get('note',''))}")
            lines.append("")
        lines.append("### Where to share (GATED - you post; nothing auto-sends)")
        for v in VENUES:
            lines.append(f"- {v}")
        lines.append(f"\nAngle: lead with the measured number, link the page ({PAGE}) for the runnable proof.")
    digest = "\n".join(lines)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(digest)

    # update seen
    for e in entries:
        if e.get("verdict") == "FAILED":
            seen[_key(e.get("claim", ""))] = e.get("date", "")
    json.dump(seen, open(SEEN, "w", encoding="utf-8"), indent=1)

    try:
        import sys
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print(digest)
    print(f"\n[wrote {os.path.relpath(OUT, ROOT)}; {len(new_failed)} new FAILED; GATED - not posted]")
    return new_failed


if __name__ == "__main__":
    main()
