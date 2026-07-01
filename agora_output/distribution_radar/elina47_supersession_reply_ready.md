# Elina-Seed #47 reply — supersession runnable reference + §7 scenario drop-in
# GATED: owner approved 2026-06-29 conditional on measurements verifying 100%.
# Verified today by RE-RUNNING the probes: AUROC 0.613, stale cosine 41.7% -> SRO 0.0% (REPRODUCED);
# operating-point 42/67/100; elina_adapter demo OK. Post via gh as DanceNitra on deepseek-launch-community/Elina-Seed#47.
# Numbers below are the re-run values (24 facts, 10/24 contradiction>=dupe).

---
@qingkong66 — here's the runnable reference. Single file, cloud-free (needs numpy + a local `nomic-embed-text`):

https://github.com/DanceNitra/agora/blob/main/mnemo/probes/supersession_replication.py

It does two things on 24 `(subject, relation, old→new)` facts:

- **Replicates the blind spot.** For each fact it scores the *contradiction* (the updated value) and an honest *rephrase* (a restatement of the original) by cosine to the original, then asks "can low similarity flag a supersession?" → **AUROC 0.61** (near the ~0.59 in the literature; 0.5 is chance). Why it fails: a contradiction often sits *closer* in embedding space than an honest rephrase — here, contradictions were as-similar-or-more than the rephrase in **10/24** cases. A similarity store genuinely can't tell "updated" from "restated."
- **Measures the gap.** A pure cosine top-1 store serves the **stale** value **41.7%** of the time. A deterministic `(subject, relation)` supersession key drops that to **0%** — but I want to be precise: that 0% is *by construction*, not an empirical win. The key retires the old value on write, so the stale record is simply never a candidate. That's exactly the point — supersession should be deterministic bookkeeping, not something you hope similarity (or an LLM call) gets right.

**For §7 — a supersession scenario to add.** It's orthogonal to the corroboration scenarios (a fact can be well-corroborated *and* stale), so it needs its own mechanism, not just `source`:

> **Scenario S — supersession.** A durable fact `(subject, relation) = value_A` is later asserted as `value_B` by a trusted source.
> *Expected:* `value_B` becomes current; `value_A` is retired (kept as history, not deleted). A query for `(subject, relation)` returns `value_B`.
> *Mechanism:* a `(subject, relation)` key; the newest write for that key is current, regardless of embedding similarity or recall frequency. No threshold, no model call.
> *Compose with corroboration:* `value_B` still needs ≥2 distinct sources to be *durable*; until then it's current-but-tentative, and `value_A` stays as the last durable value.

So beyond `source`, the record model needs one more derivable thing: a `(subject, relation)` key (even a coarse one works). Happy to fold this into your spec wording, or you add the section and I'll validate it against the probe above — either form works for me.
---
