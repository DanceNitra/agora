"""Does the digest's win survive the three attacks the red-team panel named?

The panel (2026-10-29) did not dispute the number. It disputed what produces it, and named a cheap
kill test. Three mechanisms could reproduce "the digest keeps more buried question terms" without
any relevance ranking working at all:

  FOOTER      `_digest` ends with "Searchable terms: <top 10>" and prefixes every section with its
              title. The scorer is a bare substring test, so an intent term printed in that footer
              scores as kept while none of its content is present. Truncation has no footer.
  SPREAD      The digest samples windows from across the whole output; truncation keeps two blocks.
              Any count of term TYPES outside the edges rewards a spread sampler, ranked or not.
  EDGE        "Buried" is defined by EDGE=400, while the rival's window is budget//2 (mean ~1060 B).
              The result is a function of that ratio, and our own digest length sets the budget.

So this re-runs the same comparison with the arms that separate those three from the claim:

  digest              as shipped.
  digest_no_footer    the "Searchable terms:" line removed. If the gap closes, the win was the footer.
  digest_content_only header, section titles and footer removed; only the previews survive. The
                      strictest version of the same attack.
  even_spread         UNRANKED. The output cut into N even slices, the head of each kept, N equal to
                      the digest's own section count, total bytes matched. If this matches the
                      digest, the win was spread sampling and not ranking.
  truncate_same_bytes the rival from the original probe, unchanged.

and sweeps EDGE over {100, 200, 400, 800, 1600} on both corpora, because a metric constant that was
never swept is a free parameter, not a definition.

Every arm is scored at the SAME byte budget, the shipped digest's own length per row, exactly as the
original probe did. A row whose output already fits the budget is skipped for every arm at once, so
no arm is diluted by rows where the arms cannot differ.

Controls:
  - the arms must differ, or one of them never ran.
  - the no-footer arms must be SMALLER than the digest; if not, the strip did nothing.
  - every buried term must be present in its own source, at every EDGE.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULT = Path(__file__).with_suffix(".result.json")
HERMES_DB = Path(os.path.expanduser("~")) / "AppData" / "Local" / "hermes" / "state.db"
PROJECTS = Path(os.path.expanduser("~")) / ".claude" / "projects"
THRESHOLD = 2000
MAX_ROWS = int(os.environ.get("PROBE_MAX_ROWS", "400"))
EDGES = (100, 200, 400, 800, 1600)

_spec = importlib.util.spec_from_file_location(
    "cc_probe", HERE / "the_digest_beats_truncation_on_a_second_corpus.py")
_cc = importlib.util.module_from_spec(_spec)
sys.argv = [sys.argv[0]]                      # both imported probes read argv at import time
_spec.loader.exec_module(_cc)
_first = _cc._first                           # the Hermes probe, already loaded by the CC probe

from inspeximus.context_saver import save     # noqa: E402

_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_\-/.]{2,}")
ARMS = ("digest", "digest_no_footer", "digest_content_only", "even_spread", "truncate_same_bytes")


def strip_footer(dig: str) -> str:
    """The digest without its 'Searchable terms:' line."""
    return "\n".join(ln for ln in dig.splitlines() if not ln.startswith("Searchable terms: "))


def content_only(dig: str) -> str:
    """Only the section previews: no header, no titles, no footer."""
    out = []
    for ln in dig.splitlines():
        if ln.startswith("- ") and " | " in ln:
            out.append(ln.split(" | ", 1)[1])
    return "\n".join(out)


def even_spread(output: str, budget: int, sections: int) -> str:
    """Unranked: N evenly spaced slices, same total bytes, same section count as the digest."""
    n = max(1, sections)
    if budget >= len(output):
        return output
    take = max(1, budget // n)
    step = max(1, len(output) // n)
    parts = [output[i * step: i * step + take] for i in range(n)]
    return "\n".join(parts)[:budget]


def digest_sections(dig: str) -> int:
    return sum(1 for ln in dig.splitlines() if ln.startswith("- "))


def hermes_rows():
    """(intent, output) for every Hermes tool result over the threshold."""
    con = sqlite3.connect("file:%s?mode=ro" % HERMES_DB.as_posix(), uri=True)
    rows = con.execute(
        "select coalesce(t.tool_name,'?'), t.content, "
        "coalesce((select a.tool_calls from messages a where a.session_id = t.session_id "
        "          and a.role='assistant' and a.tool_calls like '%'||t.tool_call_id||'%' "
        "          limit 1), '') "
        "from messages t where t.role='tool' and length(t.content) > ? order by t.id",
        (THRESHOLD,)).fetchall()
    for tool, content, args in rows:
        yield (_first.call_intent(args) or str(tool), content)


def cc_rows():
    files = sorted(PROJECTS.glob("*/*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    seen = 0
    for path in files:
        for intent, output in _cc.tool_results(path):
            yield intent, output
            seen += 1
            if seen >= MAX_ROWS:
                return


def answer_terms(intent: str, content: str) -> list[str]:
    return _first.answer_terms(intent, content)


def buried(ans, content, edge):
    edges = content[:edge] + content[-edge:]
    return [w for w in ans if w not in edges]


def run(name, rows):
    kept = {e: {a: 0 for a in ARMS} for e in EDGES}
    total = {e: 0 for e in EDGES}
    byts = {a: 0 for a in ARMS}
    baseline_bytes = n_rows = skipped_fit = missing = 0
    smaller = {"digest_no_footer": 0, "digest_content_only": 0}
    t0 = time.time()

    for intent, output in rows:
        dig = save(output, intent, without_reranker="hybrid", ranking="lexical")["text"]
        budget = len(dig)
        if len(output) <= budget:
            skipped_fit += 1                      # no arm can differ here
            continue
        n_rows += 1
        if n_rows % 50 == 0:
            print("  %s %d rows, %.1fs" % (name, n_rows, time.time() - t0), flush=True)

        arms = {
            "digest": dig,
            "digest_no_footer": strip_footer(dig),
            "digest_content_only": content_only(dig),
            "even_spread": even_spread(output, budget, digest_sections(dig)),
            "truncate_same_bytes": output[: budget // 2] + "\n...\n" + output[-(budget - budget // 2):],
        }
        for key in smaller:
            smaller[key] += 1 if len(arms[key]) < len(dig) else 0
        baseline_bytes += len(output)
        for a in ARMS:
            byts[a] += len(arms[a])

        ans = answer_terms(intent, output)
        for e in EDGES:
            bur = buried(ans, output, e)
            missing += sum(1 for w in bur if w not in output)
            total[e] += len(bur)
            for a in ARMS:
                kept[e][a] += sum(1 for w in bur if w in arms[a])

    out = {
        "rows_scored": n_rows,
        "rows_skipped_because_the_output_already_fits": skipped_fit,
        "baseline_bytes": baseline_bytes,
        "bytes_pct_of_baseline": {a: round(100.0 * byts[a] / max(baseline_bytes, 1), 1) for a in ARMS},
        "buried_terms_by_edge": {str(e): total[e] for e in EDGES},
        "kept_pct_by_edge": {
            str(e): {a: round(100.0 * kept[e][a] / max(total[e], 1), 1) for a in ARMS} for e in EDGES},
        "controls": {
            "needles_missing_from_their_own_source": missing,
            "rows_where_the_footer_strip_shortened_the_digest": smaller["digest_no_footer"],
            "rows_where_content_only_shortened_the_digest": smaller["digest_content_only"],
            "the_arms_differ_at_edge_400": len({kept[400][a] for a in ARMS}) > 1,
        },
    }
    return out


def main() -> int:
    import inspeximus
    findings = {
        "measured": "2026-10-29",
        "inspeximus": inspeximus.__version__,
        "what": "the three kill tests the red-team panel named: footer, spread, and the EDGE constant",
        "corpora": {},
    }
    findings["corpora"]["hermes"] = run("hermes", hermes_rows())
    findings["corpora"]["claude_code"] = run("claude_code", cc_rows())
    RESULT.write_text(json.dumps(findings, indent=1), encoding="utf-8")

    for cname, c in findings["corpora"].items():
        print("\n=== %s: %d rows scored, %d skipped (output already fits) ===" % (
            cname, c["rows_scored"], c["rows_skipped_because_the_output_already_fits"]))
        print("bytes %% of baseline: " + ", ".join(
            "%s %.1f" % (a, c["bytes_pct_of_baseline"][a]) for a in ARMS))
        header = "  edge  terms  " + "  ".join("%-20s" % a for a in ARMS)
        print(header)
        for e in EDGES:
            row = c["kept_pct_by_edge"][str(e)]
            print("  %4d  %5d  " % (e, c["buried_terms_by_edge"][str(e)])
                  + "  ".join("%-20s" % ("%.1f%%" % row[a]) for a in ARMS))
        print("controls: " + json.dumps(c["controls"]))
    print("\nresult: %s" % RESULT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
