# Memory-poison durability — corroboration-gated graduation makes a hit-and-run poison transient

Receipts behind the post
[*When should AI memory trust a new fact? Corroboration, measured*](https://dancenitra.github.io/agora/public/posts/memory-poison-resistance-measured.html).
A **measured property of one engine (inspeximus)** on **synthetic scenarios** — not a new attack or defense. The
threat (memory poisoning) is prior art: AgentPoison (Chen et al., NeurIPS 2024, arXiv:2407.12784), MINJA
(arXiv:2503.03704), OWASP **ASI06 "Memory & Context Poisoning."** No public memory benchmark (LoCoMo, LongMemEval,
BEAM) scores poison *durability* — they grade retrieval — which is the small gap this probe fills for our engine.

## The mechanism

inspeximus decays recall weight per type: **episodic** fast (7-day half-life), **semantic** slow (180-day). A memory
"graduates" episodic→semantic on enough recall value. The bug: graduation accepted a **self-assertable** `source`
string as corroboration, so a recall-pumped poison could graduate to the durable tier. The fix: graduation now
requires **earned** corroboration (a credit-loop outcome, not self-assertable, or ≥2 independent links) — a
self-sourced poison stays episodic and fades.

## Result (`inspeximus_poison_prop_scaled_result.json`, n=40; identical in semantic & lexical)

Poison pumped to value 8 (graduate threshold 5), attack stops, truth is a fresh episodic memory. Corruption =
poison out-ranks truth. Wilson 95% CIs shown (they are NOT free of noise at n=40):

| days after attack stops | OLD guard (poison graduated) | NEW guard (stays episodic) |
|---|---|---|
| 0–7 | 100% | 100% |
| 14 | 100% | 52% (CI 37–67%) |
| 21 | 100% | **0% (CI 0–9%)** |
| 30–90 | 100% (never fades) | 0% |

**Read it honestly — this is a parameter readout, not a discovered constant.** The fade time is `d* = τ½ ·
log₂(V_pump / V_truth)` — with the 7-day episodic half-life, pump 8, truth ~1, that is `7·log₂(8) = 21 days`,
i.e. **~3 episodic half-lives.** Change the half-life and the fade time scales with it. The probe's own docstring
*predicts* "2–3 weeks" before running: this **confirms that two already-established mechanisms compose as
expected** — the graduation gate (prior work) plus two-tier decay (prior work) — it is a sanity check, not an
independent empirical property. The whole OLD-vs-NEW gap is arithmetic once you fix which decay tier the poison
lands in (180-day vs 7-day).

## Sustained attacker (`inspeximus_poison_continuous_result.json`, **n=15**, NOT 40)

Fraction of a 90-day window the poison out-ranks the truth when it re-pumps every P days:

| attacker re-pumps | OLD guard | NEW guard |
|---|---|---|
| once, then stops | 100% | **transient** (0.39, CI 0.20–0.64; →0 by day 21) |
| every 30 days | 100% | 0.72 (CI 0.48–0.89) |
| every 14 days | 100% | 0.99 |
| every 7 days / continuous | 100% | 1.00 |

This is spaced-repetition arithmetic: re-pump interval ÷ half-life sets everything (re-pump each half-life → never
drops below 50% → "100%").

## Honest limits (and where the real lever is)

- **Decay is a hit-and-run blast-radius cap, not a live-attacker defense.** A continuously re-pumping attacker
  (≈ weekly) keeps the poison on top under either tier — that is the realistic threat, and this does not touch it.
  A poisoned entry also fires on the *next* matching query; a 3-week fade does nothing about immediate blast.
- For a **live** attacker the right levers are read-time **influence-gating** (`recall(..., influence_only=True)` —
  gate what drives an *action*, not what's stored) plus `monitor`/`slash`/`spend_irreversible` (the source-keyed
  accountability stack). Decay only bounds a one-shot poke's persistence.
- **Write-friction caveat:** most legitimate high-value facts arrive once from a single source; requiring ≥2
  sources / an outcome for *durability* trades friction on honest single-shot writes to slow poison — a property
  to co-ship, not a primary control.
- Synthetic, one engine, n=40 (fade) / n=15 (sustained), no cross-product benchmark of other products.

## Run it

```bash
python exp_inspeximus_poison_propagation.py   # the fade curve (n=40, semantic + lexical), writes *_result.json here
python exp_inspeximus_poison_continuous.py    # the sustained-attacker table (n=15)
```
Cloud-free (local embeddings / lexical fallback), pure inspeximus retrieval mechanics, no LLM.

MIT-licensed. Part of Agora / inspeximus (https://github.com/DanceNitra/inspeximus).
