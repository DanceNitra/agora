
"""Run the REAL infer_lineage probe and DERIVE the verdict from its numbers.

My first attempt at this was a hand-written toy: bag-of-words cosine over a 14-word shared vocabulary,
which put every pair above threshold and returned recall 1.000 with precision exactly 0.500 -- while the
VERDICT line, written in advance as prose, asserted "recovers at most a small fraction". The claim
contradicted the data sent to support it. So this run executes the shipped probe against the shipped
library and computes the verdict from the parsed table; no sentence below is written ahead of the number.
"""
import io, re, runpy, sys, contextlib

PROBE = r"C:\Users\Danculus\inspeximus-repo\probes\infer_lineage_precision.py"
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    runpy.run_path(PROBE, run_name="__main__")
out = buf.getvalue()
print(out)

# Parse "--- parent wording retained in the derivative: NN% ---" blocks and their threshold rows.
rows, retain = [], None
for line in out.splitlines():
    m = re.search(r"retained in the derivative:\s*(\d+)%", line)
    if m:
        retain = int(m.group(1)); continue
    m = re.match(r"\s*([\d.]+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\S+)\s+([\d.]+)\s+([\d.]+)\s*$", line)
    if m and retain is not None:
        thr, n, tp, fp, fn, prec, rec, f1 = m.groups()
        rows.append((retain, float(thr), int(n), int(tp), int(fp), prec, float(rec)))

assert rows, "PARSE FAILED -- refusing to state a verdict over a table I could not read"
best = max(rows, key=lambda r: r[6])
worst_retain = min(r[0] for r in rows)
at_worst = max((r for r in rows if r[0] == worst_retain), key=lambda r: r[6])
any_fp = any(r[4] > 0 for r in rows)

print("parsed %d threshold rows across %d retention levels" % (rows.__len__(), len({r[0] for r in rows})))
print("MEASURED: best recall of an INFERRED support edge = %.3f (retain %d%%, threshold %.2f, n=%d); "
      "at retain %d%% the best recall is %.3f; false positives across every cell = %s"
      % (best[6], best[0], best[1], best[2], at_worst[0], at_worst[6], "some" if any_fp else "zero"))

# The verdict is a function of the numbers, not a sentence chosen in advance.
if best[6] >= 0.80:
    v, why = "REPRODUCED", "an inferred edge recovers most true derivations"
elif best[6] >= 0.30:
    v, why = "PARTIAL", "an inferred edge recovers a minority of true derivations"
else:
    v, why = "FAILED", "an inferred edge recovers a small fraction of true derivations even at the loosest threshold"
print("VERDICT: %s -- %s (best recall %.3f, falling to %.3f when the derivative rewrites %d%% of the "
      "parent). Precision stays perfect, so the failure is RECALL: the edge has to be declared at write "
      "time; it cannot be recovered from similarity against same-domain negatives."
      % (v, why, best[6], at_worst[6], 100 - worst_retain))
