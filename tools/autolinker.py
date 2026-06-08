#!/usr/bin/env python3
"""
AutoLinker — Vault Cross-Reference Engine.

Implemented from the Vault Company night-cycle spec (King Aldric, 2026-06-08),
which addresses the gap Shadow Kael's research brief flagged: orphan notes weaken
the knowledge graph. It scans an Obsidian vault and suggests bidirectional
[[wikilinks]] between conceptually similar notes that aren't yet linked.

Method: tf-idf term weighting + SPARSE cosine similarity via an inverted index,
so it scales to thousands of notes (the naive O(n²) in the spec is replaced by
"only compare notes that share meaningful terms"). Standard library only.

Usage:
    python autolinker.py --vault "C:/Users/Danculus/my-second-brain" \
        --out "C:/Users/Danculus/my-second-brain/04 Resources/Concepts/Agora Agents"
"""
from __future__ import annotations

import argparse
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

WIKILINK = re.compile(r"\[\[([^\]|#]+)")
TOKEN = re.compile(r"[A-Za-z][A-Za-z'\-]{2,}")
FM_TAGS = re.compile(r"tags:\s*\[(.*?)\]", re.S)
DATE_TITLE = re.compile(r"^\d{4}[-_]\d{2}[-_]\d{2}")   # daily notes → noisy to cross-link
MARK = "## Related (AutoLinker)"

STOPWORDS = set("""
the a an and or but if then else of to in on at by for with from into over under
is are was were be been being do does did has have had will would can could should
this that these those it its he she they them his her their our your you we i me my
as not no yes so than too very just also about above below up down out off again
more most some any all each few other such only own same can may might must shall
what which who whom whose where when why how here there once both either neither
note notes vault concept idea ideas content via using used use within without across
""".split())


def parse_note(text: str) -> tuple[list[str], str, set[str]]:
    """Return (tags, body, existing-link-targets-lowercased)."""
    body = text
    tags: list[str] = []
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            fm = text[3:end]
            body = text[end + 4:]
            m = FM_TAGS.search(fm)
            if m:
                tags = [t.strip().strip('"\'') for t in m.group(1).split(",") if t.strip()]
    links = {t.strip().lower() for t in WIKILINK.findall(body)}
    return tags, body, links


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", required=True)
    ap.add_argument("--out", default=None, help="output dir (default: vault root)")
    ap.add_argument("--threshold", type=float, default=0.18)
    ap.add_argument("--max-per-note", type=int, default=5)
    ap.add_argument("--top-terms", type=int, default=40)
    ap.add_argument("--apply", action="store_true",
                    help="insert the strong links into the notes (## Related section)")
    ap.add_argument("--apply-threshold", type=float, default=0.32)
    ap.add_argument("--orphans-only", action="store_true",
                    help="only suggest/apply for notes that currently have NO links")
    args = ap.parse_args()

    vault = Path(args.vault)
    out_dir = Path(args.out) if args.out else vault
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── 1. Scan + index ──────────────────────────────────────
    notes: dict[str, dict] = {}     # stem -> {path, tags, tf, links, title}
    skip_dirs = {".git", ".obsidian", "templates", "assets", ".trash"}
    for p in vault.rglob("*.md"):
        if any(part in skip_dirs for part in p.parts):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        tags, body, links = parse_note(text)
        # Idempotency: tokenize the note WITHOUT its own AutoLinker section, so applying
        # links doesn't drift the tf-idf vectors on re-runs.
        mi = body.find(MARK)
        core = body[:mi] if mi != -1 else body
        toks = [w.lower() for w in TOKEN.findall(core) if w.lower() not in STOPWORDS]
        # tags weigh extra (they're curated signal)
        toks += [t.lower() for t in tags for _ in range(3)]
        if len(toks) < 8:
            continue                # too thin to compare reliably
        stem = p.stem
        if stem in notes:
            stem = f"{stem}~{len(notes)}"
        notes[stem] = {"path": p, "tags": tags, "tf": Counter(toks),
                       "links": links, "title": p.stem}
    n = len(notes)
    if n < 2:
        print(f"[AutoLinker] only {n} usable notes — nothing to do."); return

    # ── 2. idf ───────────────────────────────────────────────
    df: Counter = Counter()
    for note in notes.values():
        df.update(note["tf"].keys())
    idf = {t: math.log(n / (1 + c)) for t, c in df.items()}

    # ── 3. tf-idf vectors (top terms, L2-normalised) ─────────
    vecs: dict[str, dict[str, float]] = {}
    for stem, note in notes.items():
        weights = {t: f * idf.get(t, 0.0) for t, f in note["tf"].items() if idf.get(t, 0) > 0}
        top = sorted(weights.items(), key=lambda kv: kv[1], reverse=True)[:args.top_terms]
        norm = math.sqrt(sum(w * w for _, w in top))
        vecs[stem] = {t: w / norm for t, w in top} if norm else {}

    # ── 4. inverted index ────────────────────────────────────
    inv: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for stem, vec in vecs.items():
        for term, w in vec.items():
            inv[term].append((stem, w))
    # drop ubiquitous terms (they connect everything → noise)
    for term in list(inv):
        if len(inv[term]) > max(50, n // 20):
            del inv[term]

    # ── 5. sparse cosine + candidate links ───────────────────
    suggestions: list[tuple[str, list[tuple[float, str]]]] = []
    total = 0
    for stem, vec in vecs.items():
        scores: dict[str, float] = defaultdict(float)
        for term, w in vec.items():
            for other, w2 in inv.get(term, ()):
                if other != stem:
                    scores[other] += w * w2
        note = notes[stem]
        if args.orphans_only and note["links"]:
            continue                               # only connect isolated notes
        if DATE_TITLE.match(note["title"]):
            continue                               # daily notes — skip as source
        cands = []
        for other, s in sorted(scores.items(), key=lambda kv: kv[1], reverse=True):
            if s < args.threshold:
                break
            o = notes[other]
            if DATE_TITLE.match(o["title"]):
                continue                           # don't link to daily notes
            if o["title"].lower() == note["title"].lower():
                continue                           # duplicate-named note
            # skip if already linked either direction
            if o["title"].lower() in note["links"] or note["title"].lower() in o["links"]:
                continue
            cands.append((s, other))
            if len(cands) >= args.max_per_note:
                break
        if cands:
            suggestions.append((stem, cands))
            total += len(cands)

    suggestions.sort(key=lambda kv: kv[1][0][0], reverse=True)  # strongest first

    # ── 6. report + pending ──────────────────────────────────
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    orphans = [s for s, note in notes.items() if not note["links"]]
    rep = [f"# AutoLinker Report — {day}", "",
           f"- Notes scanned: **{n}**",
           f"- Orphan notes (no outgoing links): **{len(orphans)}**",
           f"- Notes with suggestions: **{len(suggestions)}**",
           f"- Total candidate links: **{total}**",
           f"- Similarity threshold: {args.threshold}", "",
           "> Built by AutoLinker (from King Aldric's night-cycle spec). "
           "Review and add the links you agree with.", "",
           "---", ""]
    pend = [f"# AutoLinker Pending — {day}", "",
            "Tick the links to keep, then they can be applied to the notes.", ""]
    for stem, cands in suggestions:
        title = notes[stem]["title"]
        rep.append(f"## {title}")
        rep.append("| Suggested link | Score |")
        rep.append("|---|---|")
        pend.append(f"## {title}")
        for s, other in cands:
            ot = notes[other]["title"]
            rep.append(f"| [[{ot}]] | {s:.2f} |")
            pend.append(f"- [ ] [[{ot}]]")
        rep.append("")
        pend.append("")

    rep_path = out_dir / f"autolinker_report_{day}.md"
    pend_path = out_dir / f"autolinker_pending_{day}.md"
    rep_path.write_text("\n".join(rep), encoding="utf-8")
    pend_path.write_text("\n".join(pend), encoding="utf-8")

    # ── 7. (optional) apply strong links into the notes ─────
    if args.apply:
        applied_notes = applied_links = 0
        for stem, cands in suggestions:
            note = notes[stem]
            seen = set(note["links"])          # already-linked targets (lowercased)
            new = []
            for s, other in cands:
                if s < args.apply_threshold:
                    break
                ot = notes[other]["title"]
                key = ot.lower()
                if key == note["title"].lower() or key in seen:
                    continue                   # self / duplicate / already linked
                seen.add(key)
                new.append(ot)
            if not new:
                continue
            try:
                txt = note["path"].read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            block = "\n".join(f"- [[{t}]]" for t in new)
            if MARK in txt:
                txt = txt.rstrip() + "\n" + block + "\n"   # extend existing section
            else:
                txt = txt.rstrip() + f"\n\n{MARK}\n" + block + "\n"
            try:
                note["path"].write_text(txt, encoding="utf-8")
                applied_notes += 1
                applied_links += len(new)
            except Exception:
                pass
        print(f"[AutoLinker] APPLIED {applied_links} links into {applied_notes} notes "
              f"(threshold {args.apply_threshold})")

    print(f"[AutoLinker] {n} notes · {len(orphans)} orphans · "
          f"{total} candidate links across {len(suggestions)} notes")
    print(f"[AutoLinker] report : {rep_path}")
    print(f"[AutoLinker] pending: {pend_path}")
    if suggestions:
        print("[AutoLinker] strongest suggestions:")
        for stem, cands in suggestions[:8]:
            s, other = cands[0]
            print(f"    {notes[stem]['title'][:40]:40}  ->  {notes[other]['title'][:40]}  ({s:.2f})")


if __name__ == "__main__":
    main()
