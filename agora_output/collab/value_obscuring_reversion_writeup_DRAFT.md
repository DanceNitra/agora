# When a benchmark shortcut is actually the answer: decomposing value-obscuring reversion detection

**Working draft — Agora (DanceNitra) sections. Marat Sultanov (TAT) drafts sections 3 and his halves of 2 and 7.**
Status: our sections below are complete from committed, re-runnable artifacts. Numbers trace to probes in
github.com/DanceNitra/agora (research/probes/) and to Marat's TAT-ROOT. Framing (1, the boundary language in 6,
the title) to be finalized together.

---

## 1. The task (shared)

Agent memory has to answer a question that pure retrieval does not: when a stored fact has been corrected
(old value A, then current value B), does a later utterance *reopen the decision back to the stale value A*,
or affirm the current one? The hard case is when the utterance never names a value. "Let's go back to what
we had", "revert that", or, harder still, a coreference like "let's do what the first owner decided" carries
no value token and often no revert lexeme. A value-match or a keyword grep cannot see it; the signal is a
discourse relation plus a reference, not sentence content. This is the value-obscuring reversion problem, and
getting it wrong is a direct integrity failure: the store reopens a fact the user corrected.

## 2. The arms race (both of us; Agora's half)

We built the fixture as an adversarial ladder and audited each rung to be free of the shortcut that solved
the previous one. v2 and v3 (paraphrased reversion, then a named-value control) established that the signal
is structural, not lexical: handcrafted structural features reached F1 1.00 where object/value and cosine
baselines sat at 0.03 to 0.60, and we reproduced Marat's predictions row for row (140/140 on v3). v4 moved to
coreference: the candidate refers to an anchor by role, never by name or value. Two shortcuts slipped through
our first cuts (a literal anchor-name substring, then a template-parity artifact); both were caught by a
baseline sweep and fixed before the result stood. The naturalized v4 (v4nat) split train and heldout by
register so no test phrasing had been seen, and its six-way audit killed name, value, keyword, template, and
train-to-heldout transfer, all at F1 0.000.

## 3. The seam (Marat drafts)

*Marat's method (direct context comparison), v2/v3/v4nat results, error analysis, code and notebooks.*

## 4. The localization (Agora)

Marat's direct context comparison reached F1 0.905 (AUROC 0.964) on the v4nat heldout, against our published
audit line "cosine dead at 0.481". He was right and our audit was too narrow: it selected the comparison
lines by value-token presence, so it only ever compared the candidate against the value-bearing action lines,
never the role lines, which is exactly where a coreference signal lives. We reproduced his method
independently at F1 0.930, AUROC 1.000, identical confusion shape. His own "similarity per context line"
chart already contained both readings: role lines at roughly 0.35 mean cosine, action lines at 0.14, and a
"cosine baseline" bar at about 0.48 that is our narrow variant.

Then we asked why the method works. Shuffling the context line order drops it to F1 0.500. The old-versus-new
half of the decision was riding the fixture's fixed line order (`v4nat_decomposition_probe.py`, all measured):

| variant (v4nat heldout, n=46) | F1 | reading |
|---|---|---|
| cosine vs four lines, fixture order (Marat) | 0.930 | works, but why |
| same method, context order shuffled | 0.500 | the old/new half rode the fixed line order |
| structure-match + ledger metadata, order shuffled | 0.930 | the resolution |

## 5. The decomposition (the shared result)

The fixed line order was a stand-in for something every real memory store already has: provenance metadata,
which record set which value and in what sequence. Restore that as an explicit ledger and the method holds
with order destroyed. The task factorizes into two independent subproblems:

- **Reference resolution** (a text problem): match the candidate to the context element it refers to. This is
  where structural similarity, Marat's step, does the work.
- **Recency attribution** (a ledger problem): decide whether that referent set the old value or the current
  one. This is not a text problem at all; in a real store it is a lookup against the supersession ledger.

Neither half solves the task alone. A pure text method has to smuggle in provenance (via line order, which is
why the shuffle breaks it); a pure ledger method has nothing to attribute until the reference resolves. Marat's
structural detector and mnemo's ledger turn out to be the two halves of one detector.

The decomposition is now a shipped store method, `mnemo.classify_reversion` (0.7.14): it embeds the candidate,
scores it against the ledger's own superseded-versus-current split as a margin, attributes old/new from the
supersession ledger, and abstains when the reference does not discriminate. On a mnemo-native task
(nomic-embed-text) it reaches referenced-revert 24/24, affirm-current 22/24 (conservative: two borderline keeps
abstain, the safe direction), bare "go back" abstained 23/24, unrelated abstained 24/24 (93/96). It classifies
only and never restores; a flagged revert is a signal an authorized caller acts on through the revert channel,
so the content path still cannot flip a corrected value on its own. Abstention quality is embedder-bound,
sharper on bge-m3 per the hedge-ladder result, which is the same embedder-dependence that runs through the
whole study.

## 6. The boundary (Agora, framing shared)

The decomposition has a clean edge. Every residual false positive, on both implementations and different
embedders (our three false positives on nomic, Marat's on his stack), is a candidate whose target role
appears in neither context role line: an unresolvable reference. There the correct behaviour is abstention,
which a confidence threshold on the reference match gives you, not a guess. And the truly value-obscuring
twin, a bare "go back" with no reference at all, stays undecidable from text: no classifier can separate a
stale echo from a deliberate reaffirm when the two are byte-identical differing only in provenance. That case
needs an authorization channel at the write path, not smarter reading, which is the direction mnemo's
authorized-revert work took separately.

## 7. Real-noise stress test (new, joint; Agora's half)

To move past a synthetic register entirely, we built a real-noise set: 2,769 records from a live mnemo store
(scanned clean for anything private) as the noise stream, with labeled correction chains planted into each
case. 100 rows, balanced. Positives are half natural reverts and half keyword-free anchored ones that defer to
the old setter by name; negatives include keyword-bearing distractors (revert vocabulary, keep decision) and
name-bearing distractors (old setter mentioned, current value kept), so neither lexeme nor mention separates.
Order is shuffled per row. A full-family shortcut audit confirms no trivial rule beats the all-positive
baseline of 0.675: keyword 0.602, position 0.600, the cosine family 0.612 to 0.675, name-token 0.627,
value-token and recency at 0.000. The intended signal is present (anchored positives resolve 26/26 by
reference) but no shortcut extracts it past the distractors.

TAT-Monitor (Marat's universal module, native all-MiniLM-L6-v2) on the set: accuracy 0.70, F1 0.722,
confusion [tn 31, fp 18; fn 12, tp 39]. Per subset it is exactly the operating envelope the set was built to
draw: revert_natural 25/25 (a revert lexeme is present, its keyword stage nails it), revert_anchored 14/26
(keyword-free by-role reverts fall to the v4 context comparison and land near chance), named_new 0/12 false
positives (the asserted-value path is clean), and keep_kw_distractor 12/12 false positives (every keep whose
wording contains a revert word trips the keyword stage). The keyword prior is a strength when a lexeme really
is a revert signal and a trap when it sits inside a keep; the distractors separate the two.

The decomposition then recovers the anchored case. TAT-Monitor's v4 splits old from new by fixed line
position (context[0], [2] as old; [1], [3] as new); on this shuffled-order set that positional assumption is
what costs the anchored recall. Swapping only that grouping for provenance (which line names the anchor that
set the old value, read from the ledger) and leaving the rest of the cascade untouched lifts revert_anchored
from 14/26 to 26/26, drops the keep and name-distractor false positives to zero, and raises overall F1 from
0.722 to 0.895 (accuracy 0.88, confusion [tn 37, fp 12; fn 0, tp 51]). The only residual false positives are
the keyword distractors, which the v1 keyword stage produces before v4 runs, so they belong to the keyword
boundary, not the reference-resolution one. This is the paper's thesis measured end to end on a third-party
detector: reference resolution is a text problem the structural method solves, old-versus-new is provenance,
and the two glued together beat either alone.

## 8. Reproducibility (Agora)

Every number above is re-runnable. Marat's notebooks, CSVs, and metrics.json are in TAT-ROOT; our fixtures,
generators, and audit probes are in the agora repo (`v4nat_decomposition_probe.py`, `build_realnoise_stress_v1.py`,
`tat_monitor_runner.py`, `hindsight_hedge_intensity_probe.py`, and the fixtures under
`agora_output/public_fixtures/`). The audit lessons are stated plainly, including the two shortcuts we shipped
and had to retract and the cosine-baseline claim we published too broadly and corrected. The point of the
paper is not a leaderboard number; it is that a task can look unsolvable to text methods, be solved by a
structural method that appears to cheat, and on inspection factorize into a text half and a provenance half
with a precisely bounded undecidable core.

---

*Shared working draft between the co-authors (Agora / DanceNitra and Marat Sultanov / TAT). Section 3 and the
co-authored halves of 2 and 7 are pending from Marat; once they land we merge and do a framing pass together.
The public / arXiv version goes through Agora's full validate -> storm -> audit -> verify gate before it ships.*
