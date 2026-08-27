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
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

WIKILINK = re.compile(r"\[\[([^\]|#]+)")
TOKEN = re.compile(r"[A-Za-z][A-Za-z'\-]{2,}")
FM_TAGS = re.compile(r"tags:\s*\[(.*?)\]", re.S)
DATE_TITLE = re.compile(r"^\d{4}[-_]\d{2}[-_]\d{2}")   # daily notes → noisy to cross-link
# AutoLinker's OWN machine output (and other dated machine reports) is not knowledge — never scan,
# suggest, or link it. These files dodge DATE_TITLE (their date is at the END of the name), which is
# how they used to become 1000+-link mega-hubs that cross-referenced each other.
MACHINE_REPORT = re.compile(r"^(autolinker_(report|pending)|quality_report)", re.I)
MARK = "## Related (AutoLinker)"

# Bookkeeping the swarm writes about itself. It is text, so it scores like any other note and — being
# numerous and near-identical — it wins the similarity race and becomes a hub: measured 2026-07-21, an
# unlocked run's most-linked targets were all generated files, and a first keyword blocklist merely
# moved the problem from `orphans_*` to `Archival_Candidate_2026*`. A blocklist cannot work here; the
# structural signal can. A generator stamps a DATE into the filename and emits the same note daily, so
# a snapshot family is: several notes whose stems are identical once the date is removed. Members of
# such a family are machinery whatever they are called, and a dated one-off (a real deep-research
# report) keeps its place because it has no siblings.
# No \b around the date: in `Archival_Candidate_20260615_...` an underscore IS a word character, so
# there is no boundary between `_` and `2` and the token would never match.
_DATE_TOKEN = re.compile(r"[_\-. ]*(20\d{2}[-_.]?\d{2}[-_.]?\d{2}|20\d{2}[-_.]\d{2})(?!\d)[_\-. ]*")
_FAMILY_MIN = 2      # two same-named dated files already ARE a snapshot family, not a coincidence


def _norm_title(t: str) -> str:
    """Collapse the forms the same note is saved under (`A — B`, `A_—_B`, `A - B`) to one key, so a
    note never gains a link to another copy of ITSELF. Observed on the Breaktruth newsletters, which
    exist as a spaced title, an underscored title and a `Bridge_` prefix of the same words."""
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


def _family_key(stem: str) -> str:
    return _DATE_TOKEN.sub("_", stem).strip("_- ").lower()


# The other half of the same problem needs no heuristic at all: the swarm writes its own output into
# known folders. Everything under a dated `Agora Agents/YYYY-MM-DD/` subfolder is a machine artifact by
# construction — including near-duplicate names a date rule cannot see (`blueprint-archive-station-
# spec-request`, `request-for-blueprint-archive-station-spec`, … the same request re-phrased daily).
_AGENT_OUTPUT = re.compile(r"Agora Agents[/\\]\d{4}-\d{2}-\d{2}[/\\]")


def _snapshot_families(stems) -> set:
    """Stems belonging to a dated snapshot family (>= _FAMILY_MIN same-name-modulo-date siblings)."""
    fams = defaultdict(list)
    for s in stems:
        if _DATE_TOKEN.search(s):
            fams[_family_key(s)].append(s)
    out = set()
    for members in fams.values():
        if len(members) >= _FAMILY_MIN:
            out.update(members)
    return out

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
    ap.add_argument("--trust-weighted", action="store_true",
                    help="gate auto-apply on the curator agent's live trust standing")
    ap.add_argument("--curator", default="Dame Elara",
                    help="which Vault-Company agent owns this curation (links → Bridge Builder)")
    ap.add_argument("--standing-gate", type=float, default=0.55,
                    help="legacy absolute gate; kept for callers, superseded by the rank gate")
    ap.add_argument("--max-notes", type=int, default=25,
                    help="how many notes one run may edit; the backlog drips instead of flooding "
                         "(a first unlocked run offered 2931 links across 763 notes at once)")
    ap.add_argument("--standing-floor", type=float, default=0.35,
                    help="absolute floor below which no curator may auto-apply, whatever its rank")
    ap.add_argument("--standing-file",
                    default=str(Path(__file__).resolve().parent.parent
                                / "agora-game-server" / "agent_standing.json"))
    ap.add_argument("--duplicates", action="store_true",
                    help="QA mode: flag near-duplicate notes into a quality report (no links)")
    # 0.97 = only near-IDENTICAL notes (true redundancy). Lower values over-flag
    # similar-but-distinct/versioned notes that still carry real value.
    ap.add_argument("--dup-threshold", type=float, default=0.97)
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
        if MACHINE_REPORT.match(p.stem):
            continue                    # skip AutoLinker's own reports / QA reports (machine spam)
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
        # content fingerprint (frontmatter + AutoLinker section excluded, whitespace/case
        # normalised) — for TRUE duplicate detection, not topic similarity
        norm = re.sub(r"\s+", " ", core).strip().lower()
        chash = hashlib.md5(norm.encode("utf-8")).hexdigest() if len(norm) > 20 else None
        notes[stem] = {"path": p, "tags": tags, "tf": Counter(toks),
                       "links": links, "title": p.stem, "chash": chash}
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
            # NOTE: suggestions are emitted as `backticks`, NOT [[wikilinks]] — this file is a review
            # artifact, not knowledge. Emitting live links here turned the report into a multi-thousand-
            # link mega-hub that polluted the vault graph and semantic index. Apply happens in-memory.
            rep.append(f"| `{ot}` | {s:.2f} |")
            pend.append(f"- [ ] `{ot}`")
        rep.append("")
        pend.append("")

    # Single rolling files (overwritten each run) instead of dated daily files — the old
    # autolinker_report_{day}.md pattern accumulated ~2 MB/day of regenerable machine output.
    rep_path = out_dir / "autolinker_report.md"
    pend_path = out_dir / "autolinker_pending.md"
    rep_path.write_text("\n".join(rep), encoding="utf-8")
    pend_path.write_text("\n".join(pend), encoding="utf-8")

    # ── 7. trust-weighted gate: the curator's standing decides auto-apply vs pending ──
    provenance = ""
    if args.trust_weighted:
        standing = {}
        try:
            sf = json.loads(Path(args.standing_file).read_text(encoding="utf-8"))
            standing = sf.get("standing", sf)
        except Exception as e:
            print(f"[AutoLinker] standing unavailable ({e}); curator assumed neutral 0.50")
        cur = float(standing.get(args.curator, 0.5))
        provenance = f"  —  curated by {args.curator} (trust {cur:.2f})"
        # The gate's INTENT is relative ("the most trustworthy curator may apply, the rest queue"),
        # but it was written as an absolute constant. _compute_standing blends hit-rate, mastery and
        # bounty into the ESS trust mean, and every blend pulls DOWNWARD, so the whole roster drifts
        # under the constant and the organ locks out permanently — measured 2026-07-21: the highest
        # standing of all eight agents was 0.476 against a 0.55 gate, i.e. curation had not applied
        # once. Gate on RANK within the live roster instead, keeping an absolute floor so a roster
        # that has genuinely collapsed still can't write.
        peers = sorted(float(v) for v in standing.values()) if standing else []
        rank_ok = True
        if len(peers) >= 4:
            median = peers[len(peers) // 2]
            rank_ok = cur >= median
        floor_ok = cur >= args.standing_floor
        if rank_ok and floor_ok:
            args.apply = True
            print(f"[AutoLinker] {args.curator} standing {cur:.2f} in the top half of the roster "
                  f"(floor {args.standing_floor}) -> AUTO-CURATING")
        else:
            args.apply = False
            why = "below the roster median" if not rank_ok else f"below the {args.standing_floor} floor"
            print(f"[AutoLinker] {args.curator} standing {cur:.2f} {why} "
                  f"-> held in PENDING for review (not enough trust)")

    # ── 7b. QA mode (Sergeant Voss): flag TRUE content duplicates (identical body) ──
    if args.duplicates:
        if args.trust_weighted and not args.apply:
            print(f"[AutoLinker] {args.curator} duplicate-flagging held to pending")
            return
        by_hash: dict = defaultdict(list)
        for stem, note in notes.items():
            if note.get("chash"):
                by_hash[note["chash"]].append(stem)
        groups = [sorted(g, key=lambda s: notes[s]["title"]) for g in by_hash.values() if len(g) > 1]
        groups.sort(key=lambda g: -len(g))
        redundant = sum(len(g) - 1 for g in groups)
        lines = [f"# Quality Report — duplicate notes — {day}", "",
                 f"- Curator: **{args.curator}**",
                 f"- Groups of IDENTICAL-content notes: **{len(groups)}**",
                 f"- Redundant copies (safe to remove, content kept elsewhere): **{redundant}**",
                 "", "Each group below is byte-for-byte the same note in multiple places.", "",
                 "---", ""]
        for g in groups:
            lines.append(f"### {notes[g[0]]['title']}  ({len(g)} copies)")
            for stem in g:
                lines.append(f"- `{notes[stem]['path'].name}`  —  `{notes[stem]['title']}`")
            lines.append("")
        qpath = out_dir / "quality_report_duplicates.md"
        qpath.write_text("\n".join(lines), encoding="utf-8")
        print(f"[AutoLinker] FLAGGED {len(groups)} true-duplicate groups "
              f"({redundant} redundant copies) -> {qpath.name}")
        return

    # ── 8. (optional) apply strong links into the notes ─────
    if args.apply:
        machinery = _snapshot_families(notes.keys())
        machinery |= {s for s, nt in notes.items()
                      if _AGENT_OUTPUT.search(str(nt["path"]))}
        print(f"[AutoLinker] {len(machinery)} notes are machine output (dated snapshot families or "
              f"agent-output folders) — excluded as link targets")
        applied_notes = applied_links = skipped_undecodable = 0
        write_failures: list[str] = []
        for stem, cands in suggestions:
            if applied_notes >= args.max_notes:
                print(f"[AutoLinker] budget reached ({args.max_notes} notes) — the rest stays "
                      f"in pending for the next run")
                break
            note = notes[stem]
            seen = set(note["links"])          # already-linked targets (lowercased)
            seen_norm = {_norm_title(l) for l in note["links"]}
            new = []
            for s, other in cands:
                if s < args.apply_threshold:
                    break
                if other in machinery:
                    continue                   # never link a real note to bookkeeping
                ot = notes[other]["title"]
                key = ot.lower()
                nk = _norm_title(ot)
                if key in seen or nk in seen_norm:
                    continue                   # duplicate / already linked
                if nk == _norm_title(note["title"]) or nk.startswith(_norm_title(note["title"])) \
                        or _norm_title(note["title"]).startswith(nk):
                    continue                   # another copy of this same note
                seen.add(key)
                seen_norm.add(nk)
                new.append(ot)
            if not new:
                continue
            # This is the only code in the repo that REWRITES the owner's pre-existing notes, and
            # it runs unattended (the standing check above sets args.apply itself). Two defects were
            # confirmed here on 2026-08-14 and both are fixed by the read/write below:
            #
            #  1. `errors="replace"` is a DECODE policy, and the decoded string was written back --
            #     so any note that is not valid UTF-8 had every offending byte permanently replaced
            #     by U+FFFD on disk. A file we cannot decode is a file we must not rewrite, so the
            #     decode is now strict and a failure SKIPS the note.
            #  2. No `newline=` on either side meant universal-newline translation in both
            #     directions: read turned CRLF into \n, write turned \n into os.linesep. On this
            #     Windows box every LF note was silently rewritten CRLF from top to bottom. That
            #     needed no bad bytes and no attacker -- it happened to every note this tool
            #     touched, and it makes the promise in MORNING_BRIEFING_2026-07-21 ("nothing else
            #     was touched, so it is a mechanical strip") untrue. `newline=""` on both sides
            #     hands the string through verbatim.
            try:
                with open(note["path"], "r", encoding="utf-8", newline="") as fh:
                    txt = fh.read()
            except (OSError, UnicodeDecodeError):
                skipped_undecodable += 1
                continue
            eol = "\r\n" if "\r\n" in txt else "\n"      # append in the file's own line ending
            block = eol.join(f"- [[{t}]]" for t in new)
            if MARK in txt:
                txt = txt.rstrip() + eol + block + eol    # extend existing section
            else:
                txt = txt.rstrip() + eol + eol + MARK + provenance + eol + block + eol
            try:
                with open(note["path"], "w", encoding="utf-8", newline="") as fh:
                    fh.write(txt)
                applied_notes += 1
                applied_links += len(new)
            except Exception as e:
                # A failed write used to vanish. write_text truncates at open, so this is exactly
                # where a note can be left empty -- it must be counted and printed, not swallowed.
                write_failures.append("%s: %s" % (note["path"].name, str(e)[:80]))
        # A silent skip and a silent write failure are both how "the tool ran fine" gets said about
        # a run that touched nothing or emptied something. Print them beside the success count.
        if skipped_undecodable:
            print(f"[AutoLinker] SKIPPED {skipped_undecodable} note(s) that are not valid UTF-8 "
                  f"-- they were left byte-for-byte alone, which is the point")
        for f in write_failures:
            print(f"[AutoLinker] WRITE FAILED (note may be truncated -- check it): {f}")
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
