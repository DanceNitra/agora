# separation_law — runnable probe

Public, self-contained receipts for the post
**["The same classical tradeoff in four AI-memory mechanisms — and where it breaks"](https://dancenitra.github.io/agora/public/posts/adaptation-corruption-separation-law.html)**.

## What the post claims (and what it does NOT)

On a shared signal stream, fast adaptation to genuine change and boundedness against adversarial
corruption are coupled for any single aggregation rule; the escape is a **fast channel + a
corroboration-gated slow channel + a persistence selector**, which turns the tradeoff into a
detection-latency floor; the escape is valid iff the corruption burst `B` is shorter than the
selector delay `d`.

This is **not a discovery** — it is a classical result that agent memory inherits:

- the coupling is Grossberg's **stability–plasticity dilemma** (1980);
- the fast/slow-gated escape is **Complementary Learning Systems** (McClelland, McNaughton & O'Reilly
  1995 — fast hippocampus + slow neocortex + a consistency gate);
- the two-tier cache instance is the **ARC** replacement cache (Megiddo & Modha, USENIX FAST 2003,
  shipped in ZFS);
- the delay/false-alarm floor is **CUSUM optimality** (Page 1954 introduced it; Lorden 1971 proved
  *asymptotic* minimaxity; Moustakides 1986 proved *exact* optimality);
- the `B < d` boundary is **transient change detection** (Guépié, Fillatre & Nikiforov, *Sequential
  Analysis* 2012).

Our contribution is the cross-mechanism measurement in one place, a pre-registered fifth (trust)
instance, and the NAB-16 real-data asymmetry — not the architecture.

## Files

- **`separation_law.py`** — pure-numpy, no data files, no cloud. Reproduces every *simulation* number:
  - `[A]` trust frontier + two-channel + latency floor (fast 0.1/1.00, slow ~13, two-channel 2.5/0.04)
  - `[B]` CUSUM red-team: naive EWMA **6.1**, two-channel **2.5**, CUSUM **2.4** (two-channel is near-optimal)
  - `[C]` boundary `false-distrust(B, d)` — escape holds while `B < d`, jumps to 1.00 at `B ≥ d`
  - `[D]` regime sweep — the naive/CUSUM advantage is **up to ~2.5×** in a subtle+noisy regime and
    **reverses to < 1** (naive marginally better) in the easy regime; it is regime-dependent, not universal
  - `[E]` consolidation — a bounded gate stays ~0.5 while a single EWMA reaches **~22 at a 150× spike**
    (the honest lesson is *use a bounded-influence + persistence rule*, which is the two-channel form)

  ```
  python separation_law.py
  ```

- **`nab_asymmetry.py`** — the real-data half (16 NAB streams). Needs a checkout of the public
  [Numenta Anomaly Benchmark](https://github.com/numenta/NAB):

  ```
  git clone https://github.com/numenta/NAB
  NAB_DIR=/path/to/NAB python nab_asymmetry.py
  ```

  Prints the per-stream table (e.g. ASG misconfiguration **0 vs 1181** false alarms) and the asymmetry:
  no sustained-change stream is better served by the naive point detector (0/6); every naive win is on
  a transient spike. The converse is *not* clean — so it is an asymmetry, not a biconditional. The
  script also flags the metric confound (min-false-alarm-events favors the accumulating detector) and
  the two degenerate streams, per our own audit.

## Honest limits

- The four "mechanisms" share one generative structure (step-change vs isolated spike); the unification
  is real but lives partly in the experiment design.
- best-of-N is a **selection-pressure analog** (cap `N ≈ 1/h`), not a temporal fast/slow channel.
- Every result assumes a **detector-oblivious adversary**. A detector-aware attacker who sets
  `B = d − ε` and can probe `d` turns the fixed floor into a Stackelberg equilibrium — the open frontier.
