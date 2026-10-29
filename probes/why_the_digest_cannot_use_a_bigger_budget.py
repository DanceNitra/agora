"""Why the digest's recall is FLAT from a 5 percent budget to a 50 percent one.

The budget curve measured it: byte-matched, head-and-tail truncation keeps the answer on 47.8
percent of tasks at a 20 percent budget while the digest keeps 30.4, and the digest does not move
at all as the budget grows. A strategy that cannot spend what it is given is a product defect, not
a benchmark result, so this takes the flatness apart.

It calls no model. Every number here is a substring check or a length.

TWO CAUSES, measured separately, and each with its own lever:

  THE WINDOW. A digest section is `_title(chunk)` plus `chunk[:PREVIEW]`, 240 characters of a
  chunk's HEAD. With `CHUNK_BYTES = 4096` that window covers under 6 percent of a chunk, and 0 of
  23 answers fall inside it. Shrinking chunks to 256 bytes puts 22 of 23 inside. So at the shipped
  chunk size the digest cannot show a mid-chunk line at ANY budget, which is the flatness.

  THE RANKING. Coverable is not kept: with 256-byte chunks, 22 of 23 answers sit in a window the
  digest could show, and it keeps 10. The rest lose because the answer's chunk has to be ranked
  into the sections the budget pays for.

A CORRECTION TO MY OWN WORK, which is why the offsets are computed the way they are. The first
version of this measurement took the answer's offset as `position % CHUNK_BYTES` and reported 0 of
23 in the head window at every chunk size, which refuted the window explanation. That arithmetic
assumes chunks start at fixed multiples of CHUNK_BYTES. They do not: `chunks_capped` splits on LINE
boundaries first. Computed against the real chunk, the window explanation holds and predicts the
direction of the measured recall. The theory was right and the test of it was wrong.

The lever this suggests is that chunk size should follow the budget rather than being a constant:
a larger budget should buy finer chunks, not more previews of the same coarse ones. Measured, that
takes recall from 30.4 to 43.5 percent at the same byte count, which closes most of the gap to
truncation's 47.8 without reaching it.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULT = Path(__file__).with_suffix(".result.json")
BUDGET_FRACTION = 0.20
CHUNK_SIZES = (4096, 1024, 512, 256)

sys.argv = [sys.argv[0]]
_spec = importlib.util.spec_from_file_location(
    "curve", HERE / "at_which_budget_do_the_strategies_diverge.py")
_cv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cv)

from inspeximus import context_saver as cs     # noqa: E402


def with_chunk_size(limit):
    """`chunks_capped`'s limit is a DEFAULT ARGUMENT, bound at import.

    Patching the module constant `CHUNK_BYTES` therefore changes nothing, and a sweep that patched
    it would report that chunk size has no effect. The default itself has to be replaced.
    """
    orig = cs.chunks_capped.__defaults__
    cs.chunks_capped.__defaults__ = (limit,)
    return orig


def main() -> int:
    tasks, corpus = _cv._ab.build_tasks(60, 20261029, _cv._ab.EDGE, _cv._ab.MAX_CHARS, "public")
    cut = [t for t in tasks if len(t["output"]) > max(200, int(len(t["output"]) * BUDGET_FRACTION))]
    if not cut:
        print("no task needs cutting: %s" % corpus)
        return 1

    top, preview = cs.TOP, cs.PREVIEW
    rows = {}
    try:
        for limit in CHUNK_SIZES:
            orig = with_chunk_size(limit)
            try:
                cs.TOP, cs.PREVIEW = 60, 240       # ask for every section the chunks allow
                chunk_counts, lens, kept, in_window, found = [], [], 0, 0, 0
                for t in cut:
                    budget = max(200, int(len(t["output"]) * BUDGET_FRACTION))
                    chunks = cs.chunks_capped(t["output"])
                    chunk_counts.append(len(chunks))
                    for c in chunks:                # the answer's offset in ITS OWN chunk, never
                        i = c.find(t["answer"])      # position % CHUNK_BYTES: chunks split on lines
                        if i >= 0:
                            found += 1
                            in_window += 1 if i < cs.PREVIEW else 0
                            break
                    dig = _cv.digest_at(t["output"], t["intent"], budget)
                    lens.append(len(dig))
                    kept += 1 if t["answer"] in dig else 0
                chunk_counts.sort()
                lens.sort()
                rows[str(limit)] = {
                    "median_chunks_per_output": chunk_counts[len(chunk_counts) // 2],
                    "median_digest_bytes": lens[len(lens) // 2],
                    "answers_located_in_a_chunk": found,
                    "answers_inside_the_240_char_head_window": in_window,
                    "coverable_pct": round(100.0 * in_window / max(found, 1), 1),
                    "digest_kept": kept,
                    "digest_kept_pct": round(100.0 * kept / len(cut), 1),
                }
            finally:
                cs.chunks_capped.__defaults__ = orig
    finally:
        cs.TOP, cs.PREVIEW = top, preview

    out = {
        "measured": "2026-10-29",
        "what": "why the digest's recall does not rise with the budget. No model is called.",
        "corpus": corpus, "tasks_that_had_to_be_cut": len(cut),
        "budget_fraction": BUDGET_FRACTION,
        "preview_chars": 240,
        "truncation_at_this_budget_pct": 47.8,
        "by_chunk_size": rows,
        "controls": {
            "the_chunk_limit_is_a_default_argument_so_the_constant_is_not_the_lever": True,
            "the_offset_is_measured_in_the_real_chunk_not_by_modulo": True,
        },
    }
    RESULT.write_text(json.dumps(out, indent=1), encoding="utf-8")

    print("%d tasks, budget %d%% of the output, preview 240 chars, truncation keeps 47.8%%\n"
          % (len(cut), round(BUDGET_FRACTION * 100)))
    print("  %-12s %8s %9s %12s %10s" % (
        "CHUNK_BYTES", "chunks", "digest B", "coverable", "kept"))
    for limit in CHUNK_SIZES:
        r = rows[str(limit)]
        print("  %-12d %8d %9d %11.1f%% %9.1f%%" % (
            limit, r["median_chunks_per_output"], r["median_digest_bytes"],
            r["coverable_pct"], r["digest_kept_pct"]))
    print("\nresult: %s" % RESULT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
