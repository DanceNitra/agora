"""230 entries, 200 lines, 25,000 bytes. The best index is the best one that FITS.

WHY THIS EXISTS. Today's two deployments improved the index and pushed it out of the window that
loads it: 230 entries a session could reach this morning, 134 now. The measured gain survived, at a
third of its reported size, while 96 memories became unreachable. Neither deployment checked the
constraint, because neither knew it existed.

THE CONSTRAINT, from Claude Code's own documentation: "The first 200 lines of MEMORY.md, or the first
25KB, whichever comes first, are loaded at the start of every conversation. Content beyond that
threshold is not loaded." MEMORY_ARCHIVE.md is a topic file and is never loaded at startup at all.

WHAT IS MEASURED. Layouts that satisfy BOTH caps, scored on the same held-out queries with the same
fixed denominator, against two baselines that bracket the day: this morning's crowded index (fits,
weak lines) and tonight's written index (strong lines, 96 entries past the cut).

    S0  this morning, crowded                     fits      the baseline the day has to beat
    S1  tonight, written lines                    OVER      what is deployed right now
    S2  written lines, truncated to fit bytes     fits      keeps every entry reachable
    S3  S2 + pairing from the back to fit lines   fits      the owner's own grouping, restored
                                                            only as far down as the cap forces

CONTROLS:
  * FEASIBILITY IS ASSERTED, NOT ASSUMED. Every layout is measured against both caps as bytes on
    disk, and an infeasible layout is reported as infeasible rather than scored quietly.
  * EVERY ENTRY MUST SURVIVE. A layout that reaches its budget by losing entries is rejected: the
    link set must be identical to the live file's, in order.
  * THE DENOMINATOR IS FIXED and never shrinks. An entry past the cut is a miss, not a removed row.
  * TWO REGISTERS, because one flatters whichever layout shares its voice.
  * TRUNCATE, DO NOT REGENERATE. Measured earlier today: a line cut to seven words retrieves better
    (0.758) than one written to seven (0.667) -- asked for brevity the model generalises, and
    specifics are what a query matches. So the shortening here is a cut, and costs no model calls.

Run: python probes/an_index_that_fits_the_window_beats_a_better_one_that_does_not.py
"""
from __future__ import annotations

import json
import math
import pathlib
import re
import sys
from collections import Counter

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:                                                      # noqa: BLE001
    pass

MEM = pathlib.Path(r"C:\Users\Danculus\.claude\projects\C--Users-Danculus-agora\memory")
HERE = pathlib.Path(__file__).parent
OUT = HERE / "an_index_that_fits_the_window_beats_a_better_one_that_does_not.result.json"
QA = HERE / "can_the_right_memory_be_selected_from_one_index_line.result.json"
QB = HERE / "the_winning_index_line_was_written_by_the_query_writer.queries.json"

LIVE = MEM / "MEMORY.md"
MORNING = MEM / "MEMORY.md.bak-20260819-precrowdfix"
ARCHIVE = MEM / "MEMORY_ARCHIVE.md"

LINE_CAP = 200
BYTE_CAP = 25000

STOP = set("""a an the and or but if then than that this those these is are was were be been being am do does
did have has had i you he she it we they them his her its our their my your of in on at to for with from by as
into over under about after before between during without within not no nor so such can could would should may
might must will shall there here when where which who whom what why how all any both each few more most other
some only own same too very just also us one two""".split())
TOK = re.compile(r"[a-z][a-z0-9_-]{2,}")


SPLIT_FILENAMES = False                     # set per scoring pass; see the instrument control


def toks(s):
    if SPLIT_FILENAMES:
        # A file name is a sentence to a reader and one opaque token to this regex. Under
        # this pass it is read the way a model reads it, so a thin layout is not credited
        # by accident with hiding its meaning where the instrument could not look.
        s = s.replace(".md", " ").replace("-", " ").replace("_", " ")
    return [t for t in TOK.findall(s.lower()) if t not in STOP]


class BM25:
    def __init__(self, docs, k1=1.5, b=0.75):
        self.k1, self.b = k1, b
        self.ids = list(docs)
        self.tf = {i: Counter(toks(docs[i])) for i in self.ids}
        self.len = {i: sum(self.tf[i].values()) or 1 for i in self.ids}
        self.avg = sum(self.len.values()) / len(self.ids)
        df = Counter()
        for i in self.ids:
            df.update(self.tf[i].keys())
        n = len(self.ids)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}

    def rank(self, q):
        qt = toks(q)
        sc = []
        for i in self.ids:
            tf, dl = self.tf[i], self.len[i]
            v = 0.0
            for t in qt:
                f = tf.get(t)
                if f:
                    v += self.idf.get(t, 0.0) * f * (self.k1 + 1) / (
                        f + self.k1 * (1 - self.b + self.b * dl / self.avg))
            sc.append((v, i))
        sc.sort(key=lambda x: (-x[0], x[1]))
        return [i for _, i in sc]


def index_map(text):
    d = {}
    for raw in text.splitlines():
        for fn in re.findall(r"\]\(([^)]+\.md)\)", raw):
            d.setdefault(fn, raw.strip())
    return d


def loaded_prefix_text(text, byte_cap=BYTE_CAP, line_cap=LINE_CAP):
    """What a session assembles from this text, counting bytes as they land on disk (CRLF)."""
    kept, total = [], 0
    for line in text.split("\n"):
        b = len(line.encode("utf-8")) + 2                       # + CRLF, as the file is written
        if len(kept) >= line_cap or total + b > byte_cap:
            break
        kept.append(line)
        total += b
    return "\n".join(kept)


# ---------------------------------------------------------------- parse the live file into pieces
ENTRY = re.compile(r"^\[([^\]]*)\]\(([^)]+\.md)\)(?:\s*[\u2014-]\s*(.*))?$")


def parse(path):
    """[(kind, payload)] in file order. kind is 'text' or 'entries' (a list of (title, file, hook))."""
    out = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s.startswith("- ") or "](" not in s:
            out.append(("text", raw))
            continue
        got = []
        for chunk in re.split(r"\s+\u00b7\s+", s[2:].strip()):
            m = ENTRY.match(chunk.strip())
            if m:
                got.append((m.group(1), m.group(2), (m.group(3) or "").strip()))
        out.append(("entries", got) if got else ("text", raw))
    return out


def render(blocks, words=None, pair_from=None, full_first=0, link_text=False):
    """Assemble an index. `words` caps each hook by word count (a cut, not a rewrite);
    `pair_from` is the entry ordinal from which entries are joined two-per-line;
    `link_text` makes the sentence itself the link text, buying back the separate title."""
    n, lines = 0, []
    pending = []

    def fmt(t, f, h, ordinal=0):
        if words is not None and h and ordinal >= full_first:
            w = h.split()
            if len(w) > words:
                h = " ".join(w[:words])
        if link_text:
            # The sentence IS the link text. A separate title spends 23 bytes an entry restating
            # what the sentence already says, and the window costs 71 bytes of scaffolding per
            # entry before it buys any meaning at all.
            return "[%s](%s)" % ((h.rstrip(" .;:,-\u2014") or t) if h else t, f)
        return "[%s](%s)%s" % (t, f, (" \u2014 " + h) if h else "")

    def flush():
        if pending:
            lines.append("- " + " \u00b7 ".join(pending))
            pending.clear()

    for kind, payload in blocks:
        if kind == "text":
            flush()
            lines.append(payload)
            continue
        for (t, f, h) in payload:
            piece = fmt(t, f, h, n)
            if pair_from is not None and n >= pair_from:
                pending.append(piece)
                if len(pending) == 2:
                    flush()
            else:
                flush()
                lines.append("- " + piece)
            n += 1
    flush()
    return "\n".join(lines)


def main() -> int:
    global SPLIT_FILENAMES
    blocks = parse(LIVE)
    live_txt = LIVE.read_text(encoding="utf-8")
    morn_txt = MORNING.read_text(encoding="utf-8")
    arch_txt = ARCHIVE.read_text(encoding="utf-8") if ARCHIVE.exists() else ""
    live_links = re.findall(r"\]\(([^)]+\.md)\)", live_txt)
    n_entries = len(live_links)

    qa_all = json.loads(QA.read_text(encoding="utf-8"))["rows"]
    pool, mpool = index_map(live_txt + "\n" + arch_txt), index_map(morn_txt + "\n" + arch_txt)
    qa = [(r["file"], r["query"]) for r in qa_all if r["file"] in pool and r["file"] in mpool]
    qb = [(k, v) for k, v in json.loads(QB.read_text(encoding="utf-8")).items()
          if k in pool and k in mpool and len(v.split()) >= 2]
    print("%d entries in the live index; denominator %d question-form / %d search-box"
          % (n_entries, len(qa), len(qb)))

    def on_disk(text):
        return text.replace("\n", "\r\n").encode("utf-8")

    def fits(text):
        return len(text.split("\n")) <= LINE_CAP and len(on_disk(text)) <= BYTE_CAP

    def fit_pairing(words, full_first):
        """The least pairing that meets the LINE cap, or None if even full pairing cannot."""
        for pf in range(n_entries, -1, -2):
            if len(render(blocks, words=words, pair_from=pf, full_first=full_first)
                   .split("\n")) <= LINE_CAP:
                return pf
        return None

    def build(words, full_first, link_text=False):
        for pf in range(n_entries, -1, -2):
            t = render(blocks, words=words, pair_from=pf, full_first=full_first, link_text=link_text)
            if len(t.splitlines()) <= LINE_CAP:
                return t
        return None

    # ------------------------------------------------------------------ candidate layouts
    cands = {"S0  this morning, crowded": morn_txt,
             "S1  tonight, written lines (LIVE)": live_txt}
    # thin: every hook cut to the same length
    for w in (3, 4, 5, 6):
        t = build(w, 0)
        if t is not None:
            cands["T%d  every hook cut to %d words" % (w, w)] = t
    # the sentence AS the link text -- no separate title to pay for
    for w in (6, 8, 10, 12, 14, 18, None):
        t = build(w, 0, link_text=True)
        if t is not None:
            cands["L%-4s the sentence IS the link, %s words" % (w or "-", w or "all")] = t
    # hybrid: the head of the file keeps its full sentence, the tail is cut hard
    tried_h, fit_h = 0, 0
    for ff in (30, 50, 70, 90):
        for w in (3, 4, 5, 6, 8):
            tried_h += 1
            t = build(w, ff)
            if t is not None and fits(t):
                cands["H%d/%d  first %d full, rest %d words" % (ff, w, ff, w)] = t
                fit_h += 1
                break
    print("hybrid layouts (full sentences for the head, hard cut for the tail): %d tried, %d fit "
          "both caps" % (tried_h, fit_h))

    # ------------------------------------------------------------------ score, twice
    results = {}
    for split in (False, True):
        SPLIT_FILENAMES = split
        tag = "file names read as words" if split else "file names opaque (as first measured)"
        print("\n=== SCORING PASS: %s ===" % tag)
        print("%-42s %8s %5s %-8s %8s %6s %6s" %
              ("layout", "bytes", "lines", "caps", "reach", "q@3", "sb@3"))
        for name, text in cands.items():
            loaded = index_map(loaded_prefix_text(text))
            bm = BM25(loaded) if loaded else None

            def r3(queries):
                if not bm:
                    return 0.0
                return sum(1 for f, q in queries
                           if f in loaded and bm.rank(q).index(f) + 1 <= 3) / len(queries)

            links = re.findall(r"\]\(([^)]+\.md)\)", text)
            row = dict(bytes=len(on_disk(text)), lines=len(text.split("\n")), fits=fits(text),
                       complete=(links == live_links or name.startswith("S0")),
                       reachable=len(loaded), questions=r3(qa), searchbox=r3(qb))
            results.setdefault(name, {})["split" if split else "opaque"] = row
            print("%-42s %8d %5d %-8s %4d/%d %6.3f %6.3f%s"
                  % (name, row["bytes"], row["lines"], "FITS" if row["fits"] else "OVER",
                     row["reachable"], n_entries, row["questions"], row["searchbox"],
                     "" if row["complete"] else "  !! ENTRIES LOST"))
    SPLIT_FILENAMES = False

    # ------------------------------------------------------------------ the instrument control
    print("\nINSTRUMENT CONTROL -- does reading file names as words change WHICH layout wins?")
    def rank_by(key):
        feas = [n for n, v in results.items()
                if v[key]["fits"] and v[key]["complete"] and not n.startswith("S0")]
        return sorted(feas, key=lambda n: -(results[n][key]["questions"] + results[n][key]["searchbox"]))
    ro, rs = rank_by("opaque"), rank_by("split")
    print("   winner, names opaque : %s" % (ro[0] if ro else "none feasible"))
    print("   winner, names as words: %s" % (rs[0] if rs else "none feasible"))
    agree = bool(ro and rs and ro[0] == rs[0])
    print("   the two readings agree: %s%s" % (agree, "" if agree else
          "  -- the choice depends on the instrument, so it is reported as a range, not a pick"))

    # ------------------------------------------------------------------ verdict
    s0 = results["S0  this morning, crowded"]["opaque"]
    s1 = results["S1  tonight, written lines (LIVE)"]["opaque"]
    print("\nWHAT IS LIVE RIGHT NOW reaches %d of %d entries and is %d B over the %d B window."
          % (s1["reachable"], n_entries, s1["bytes"] - BYTE_CAP, BYTE_CAP))
    if ro:
        win = ro[0]
        w_o, w_s = results[win]["opaque"], results[win]["split"]
        print("\nBEST FEASIBLE: %s" % win)
        print("   %-24s %-22s %-22s %s" % ("", "questions@3", "search-box@3", "entries reachable"))
        print("   %-24s %-22s %-22s %s" % ("this morning",
              "%.3f" % s0["questions"], "%.3f" % s0["searchbox"], "%d" % s0["reachable"]))
        print("   %-24s %-22s %-22s %s" % ("live now (over cap)",
              "%.3f" % s1["questions"], "%.3f" % s1["searchbox"], "%d" % s1["reachable"]))
        print("   %-24s %-22s %-22s %s" % ("this layout",
              "%.3f" % w_o["questions"], "%.3f" % w_o["searchbox"], "%d" % w_o["reachable"]))
        print("   %-24s %-22s %-22s %s" % ("  same, names as words",
              "%.3f" % w_s["questions"], "%.3f" % w_s["searchbox"], "%d" % w_s["reachable"]))
        dominates = (w_o["questions"] >= s1["questions"] and w_o["searchbox"] >= s1["searchbox"]
                     and w_o["reachable"] > s1["reachable"])
        print("\nDEPLOY: %s" % ("YES -- better on both registers AND reaches every entry"
                                if dominates else
                                "NOT AUTOMATIC -- it trades a register for reach; that is a judgement"))
        (HERE / "an_index_that_fits_the_window.candidate.md").write_text(
            cands[win], encoding="utf-8")
        print("candidate index written beside this probe for inspection before anything is deployed")
        print("\nHOW THE WINNER ACTUALLY READS -- the half no benchmark scores:")
        shown = [l for l in cands[win].splitlines() if l.startswith("- [")]
        for l in shown[3:8] + shown[len(shown) // 2:len(shown) // 2 + 3]:
            print("   %s" % l[:150])

    OUT.write_text(json.dumps(dict(results=results, n_entries=n_entries, line_cap=LINE_CAP,
                                   byte_cap=BYTE_CAP, winner_opaque=ro[:3], winner_split=rs[:3],
                                   instrument_agrees=agree), indent=1), encoding="utf-8")
    print("\nwrote %s" % OUT.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
