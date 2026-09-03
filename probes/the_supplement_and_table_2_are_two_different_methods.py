"""The supplement says it holds the data behind Table 2. Do the two agree?

WHY. The supplement's own first sentence promises "the per-edge scan data behind Table~2". Its
random-graph row for edge (8,14) reads 0.050837261219369934, and Table 2's random depth is 0.1050.
Those are the two ends of the same disagreement we spent the day resolving: 0.050837 is the
projection average in his sector and 0.1050 is one returned vector. If the supplement was built from
one file and the table from the other, a referee opening both finds the headline number contradicted
by the data appended to support it.

WHAT THIS ASKS. Which of the two files in his archive each artifact came from, decided by matching
values rather than by reading prose.

CONTROLS, each able to fail:
  * BOTH ARTIFACTS MUST PARSE TO THE RIGHT SHAPE. 14 tree rows and 27 random rows from the
    supplement, and a Table 2 with a tree row and a random row. A parser that silently returns three
    rows would report agreement it never tested.
  * THE TWO CANDIDATE SOURCES MUST DIFFER. If his full-data file and his repaired CSV agreed on
    every edge, the question is unanswerable and the probe says so rather than picking one.
  * EVERY ROW IS SCORED, not the one that motivated the question. The verdict is a count over all 41
    edges, so a single coincidence cannot carry it.
  * A MUTATION. The matcher is re-run against a deliberately altered supplement value and must fail
    to match, so a matcher that accepts anything is caught.
  * IF THE SUPPLEMENT MATCHES NEITHER FILE, that is reported as UNIDENTIFIED rather than resolved by
    elimination.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SUB = os.path.join(ROOT, "agora_output", "edrn_submission")
ARCHIVE = os.path.join(SUB, "guanghao_archive_2026-09-03")
OUT = os.path.join(HERE, "the_supplement_and_table_2_are_two_different_methods.result.json")
TOL = 5e-6


def refuse(why):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    raise SystemExit(2)


def read(path):
    for enc in ("utf-8", "utf-8-sig", "gbk", "cp1252"):
        try:
            return io.open(path, encoding=enc).read()
        except UnicodeDecodeError:
            continue
    refuse("cannot decode %s" % path)


def supplement_rows():
    """{(graph, (u,v)): (s, depth)} from the built supplement."""
    tex = read(os.path.join(SUB, "supplementary.tex"))
    out, graph = {}, None
    for line in tex.split("\n"):
        if "Per-edge scan, tree" in line:
            graph = "tree"
        elif "Per-edge scan, random" in line or "scan, random" in line:
            graph = "random"
        # `---` is how the built supplement renders an edge with no valley, and a depth can be
        # NEGATIVE. The first version of this regex accepted neither, so it silently dropped four of
        # the 27 random rows and reported a shape mismatch it had caused itself.
        m = re.match(r"\s*(\d+)--(\d+)\s*&\s*(-?[\d.]+|-{2,})\s*&\s*(-?[\d.]+|-{2,})\s*&", line)
        if m and graph:
            u, v, s, d = m.groups()
            none = lambda x: None if set(x) == {"-"} else float(x)
            out[(graph, (int(u), int(v)))] = (none(s), none(d))
    return out


def archive_rows():
    """The two candidate sources, each as {(graph, edge): depth}."""
    full, repaired = {}, {}
    for root, _d, files in os.walk(ARCHIVE):
        for f in files:
            p = os.path.join(root, f)
            if f.endswith(".txt"):
                t = read(p)
                if "=== tree" not in t or "FINAL SUMMARY" not in t:
                    continue
                graph = None
                for line in t.split("\n"):
                    if line.startswith("=== tree"):
                        graph = "tree"
                    elif line.startswith("=== random"):
                        graph = "random"
                    m = re.match(r"\s*Edge \((\d+), (\d+)\): s=([\d.]+|None), depth=([\d.]+|None)",
                                 line)
                    if m and graph:
                        u, v, _s, d = m.groups()
                        full[(graph, (int(u), int(v)))] = None if d == "None" else float(d)
            elif f.endswith(".csv"):
                for line in read(p).split("\n"):
                    # Three rows carry an EMPTY valley_depth: the edges the file marks
                    # selection_eligible=False. Reading them as absent made the row count 38 and
                    # tripped this probe's own coverage control, which is the parser reporting its
                    # own gap as the world's.
                    m = re.match(r'(tree|random),\d+,"\[(\d+), (\d+)\]",.*?,([-\d.eE+]*)\s*$', line)
                    if m:
                        g, u, v, d = m.groups()
                        repaired[(g, (int(u), int(v)))] = float(d) if d.strip() else None
    return full, repaired


def table2():
    tex = read(os.path.join(SUB, "manuscript.tex"))
    rows = {}
    for name in ("Tree", "Random"):
        m = re.search(r"^%s\s*&(.+?)\\\\" % name, tex, re.M)
        if not m:
            refuse("Table 2 has no %s row" % name)
        cells = [c.strip() for c in m.group(1).split("&")]
        nums = re.findall(r"[0-9]+\.[0-9]+", " ".join(cells[1:3]))
        rows[name.lower()] = {"position": cells[0], "single": float(nums[0])}
    return rows


def main():
    sup = supplement_rows()
    full, repaired = archive_rows()
    t2 = table2()

    n_tree = sum(1 for k in sup if k[0] == "tree")
    n_rand = sum(1 for k in sup if k[0] == "random")
    print("  supplement rows: %d tree, %d random" % (n_tree, n_rand))
    if (n_tree, n_rand) != (14, 27):
        refuse("the supplement parsed to %d and %d rows, not 14 and 27" % (n_tree, n_rand))
    print("  archive rows: full-data %d, repaired CSV %d" % (len(full), len(repaired)))
    if len(full) < 41 or len(repaired) < 41:
        refuse("a candidate source parsed to fewer than 41 rows (%d, %d)" % (len(full), len(repaired)))

    # CONTROL: the two candidates must be distinguishable.
    both = [k for k in full if k in repaired and full[k] is not None and repaired[k] is not None]
    differ = [k for k in both if abs(full[k] - repaired[k]) > TOL]
    print("  the two candidate sources differ on %d of the %d edges both report" % (len(differ), len(both)))
    if not differ:
        refuse("the two sources agree everywhere, so the supplement's origin cannot be identified")

    def score(src):
        """(hits, rows this source can be scored on). Two sources cover different rows, so each
        needs ITS OWN denominator. The first version reported both hit counts against one shared
        denominator and printed '38 of 36', which is the arithmetic telling you the report is wrong.
        """
        hit = seen = 0
        for k, (_s, d) in sup.items():
            if d is None or k not in src or src[k] is None:
                continue
            seen += 1
            if abs(d - src[k]) <= TOL:
                hit += 1
        return hit, seen

    hits_full, seen_full = score(full)
    hits_rep, seen_rep = score(repaired)
    both_cover = [k for k, (_s, d) in sup.items()
                  if d is not None and full.get(k) is not None and repaired.get(k) is not None]
    head_full = sum(1 for k in both_cover if abs(sup[k][1] - full[k]) <= TOL)
    head_rep = sum(1 for k in both_cover if abs(sup[k][1] - repaired[k]) <= TOL)
    comparable = len(both_cover)
    print("  supplement vs full-data:   %d of %d rows that file covers" % (hits_full, seen_full))
    print("  supplement vs repaired CSV: %d of %d rows that file covers" % (hits_rep, seen_rep))
    print("  head to head on the %d rows BOTH cover: full-data %d, repaired %d"
          % (comparable, head_full, head_rep))

    # CONTROL: a mutation must not match.
    k0 = next(k for k, (_s, d) in sup.items() if d is not None and k in repaired)
    mutated = dict(sup)
    mutated[k0] = (sup[k0][0], sup[k0][1] + 0.01)
    mut_hit = sum(1 for k, (_s, d) in mutated.items()
                  if d is not None and k in repaired and repaired[k] is not None
                  and abs(d - repaired[k]) <= TOL)
    if mut_hit >= hits_rep:
        refuse("a mutated supplement value still matched, so the matcher is not discriminating")
    print("  mutation control: altering one row drops the repaired-CSV match from %d to %d"
          % (hits_rep, mut_hit))

    if head_rep > head_full:
        origin = "repaired CSV (the projection average in his sector)"
    elif head_full > head_rep:
        origin = "full-data file (one returned vector)"
    else:
        origin = "UNIDENTIFIED"

    # Table 2's own numbers against the same two sources.
    t2_random = t2["random"]["single"]
    t2_tree = t2["tree"]["single"]
    deepest_full = {g: max((v for k, v in full.items() if k[0] == g and v is not None), default=None)
                    for g in ("tree", "random")}
    deepest_rep = {g: max((v for k, v in repaired.items() if k[0] == g and v is not None),
                          default=None) for g in ("tree", "random")}
    print()
    print("  Table 2 tree   %.4f | deepest in full-data %.6f | deepest in repaired %.6f"
          % (t2_tree, deepest_full["tree"], deepest_rep["tree"]))
    print("  Table 2 random %.4f | deepest in full-data %.6f | deepest in repaired %.6f"
          % (t2_random, deepest_full["random"], deepest_rep["random"]))

    sup_8_14 = sup.get(("random", (8, 14)), (None, None))[1]
    print()
    print("  SUPPLEMENT ORIGIN: %s" % origin)
    print("  supplement's (8,14) depth: %s   Table 2's random depth: %.4f"
          % (("%.15f" % sup_8_14) if sup_8_14 is not None else "absent", t2_random))
    inconsistent = sup_8_14 is not None and abs(sup_8_14 - t2_random) > TOL
    # TWO SEPARATE QUESTIONS, and the first version ran them together. Whether the numbers differ is
    # a fact about the data. Whether the supplement CLAIMS to be Table 2's data is a fact about its
    # prose, and that prose can be fixed without touching a number. Reporting the claim as though it
    # were still there after it had been rewritten would be the instrument describing yesterday.
    tex = read(os.path.join(SUB, "supplementary.tex"))
    claims_to_be_table2 = "data behind Table~2" in tex or "data behind Table 2" in tex
    declares_method = "projection average" in tex
    print("  supplement claims to be Table 2's own data: %s | declares its method: %s"
          % (claims_to_be_table2, declares_method))
    if inconsistent and claims_to_be_table2:
        print("  BLOCKING: the supplement says it is the data behind Table 2 and does not contain "
              "Table 2's number for that edge.")
    elif inconsistent:
        print("  OPEN, and it is the authors' call: the two artifacts use different conventions and "
              "the supplement now says which one it uses. Table 2 still reports the other.")

    json.dump({
        "script": os.path.basename(__file__),
        "supplement_rows": {"tree": n_tree, "random": n_rand},
        "candidate_sources_differ_on": len(differ), "of_comparable": len(both),
        "supplement_vs_full_data": {"hits": hits_full, "rows_that_file_covers": seen_full},
        "supplement_vs_repaired_csv": {"hits": hits_rep, "rows_that_file_covers": seen_rep},
        "head_to_head_on_rows_both_cover": {"rows": comparable, "full_data": head_full,
                                            "repaired_csv": head_rep},
        "mutation_control_match": mut_hit,
        "supplement_origin": origin,
        "table2": t2,
        "deepest_in_full_data": deepest_full,
        "deepest_in_repaired_csv": deepest_rep,
        "supplement_depth_for_8_14": sup_8_14,
        "table2_and_supplement_disagree_on_8_14": bool(inconsistent),
        "supplement_claims_to_be_table2_data": bool(claims_to_be_table2),
        "supplement_declares_its_method": bool(declares_method),
        "controls": {
            "shapes_asserted": True,
            "candidates_proved_distinguishable": True,
            "every_row_scored": True,
            "mutation_control_fired": mut_hit < hits_rep,
            "unidentified_is_reachable": True,
        },
    }, io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("  written: %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
