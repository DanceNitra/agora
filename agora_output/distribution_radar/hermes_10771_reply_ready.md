# NousResearch/hermes-agent #10771 (Auto Dream / memory consolidation) — reply DRAFT (GATED)
# Owner approves before I post (as DanceNitra). Value-first; references our published, auditable result.
# We've already commented twice here credibly; this 3rd adds NEW measured info, not a re-plug.

---
On "what should the consolidation pass trust" (and @konsisumer's grouping — agreed these are facets of one problem: a memory that can't reliably tell *current from stale* or *right from wrong*).

One measurement that changed how we run our nightly consolidation judge: **a small model's own confidence is nearly useless for knowing when it's wrong.** We tested confidence-vs-correctness (AUROC — does higher confidence actually mean more often right?) on a contamination-free task across capability tiers:

- qwen2.5:7b (weak) **0.50**, qwen3-coder:30b (mid) **0.54** — a coin flip
- claude-sonnet-4-6 (frontier) **0.903** — genuinely knows when it's about to be wrong (it put ~2% confidence on its wrong answers)

Implication for Auto Dream: if the consolidation judge (the model deciding "is this a contradiction / is this stale / can this be pruned") is a cheap local model, **it cannot self-gate on its own confidence** — it will merge or prune the wrong things while feeling certain. What held up for us is to make the gate **corroboration-based, not confidence-based**: promote/retire on independent corroboration (distinct, entity-resolved sources, so an attacker or a feedback loop can't mint fake confirmations), and escalate genuinely ambiguous pairs to a stronger model rather than letting the cheap judge decide alone.

That also reinforces the state-toggle point upthread: a supersede is a *structural* event (same subject + relation, new value) resolvable by a deterministic key with **no model judgment at all** — exactly the kind of decision you don't want a coin-flip-confident model making by similarity.

Single-file runnable probes for all of this, with raw data so you can re-check or run them on your own models — eviction (two-tier), corroboration/sybil poisoning, supersession, and the confidence-vs-correctness measurement: https://github.com/DanceNitra/agora/tree/main/mnemo/probes
Writeup of the confidence result: https://dancenitra.github.io/agora/public/posts/can-an-llm-trust-its-own-confidence.html
---
