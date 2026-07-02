# FINAL claim for the post (post-STORM, skeptic-tested)

**Headline claim:** A single poisoned memory whose trigger is a *plain English sentence* hijacks the
top-1 retrieval result across three different dense retrievers (all-MiniLM-L6-v2, BGE-small-en-v1.5,
Contriever) at 69–100%, and the two cheapest content-based defenses both fail — a write-time
perplexity/gibberish filter (natural triggers pass straight through) and retrieval-time
outlier/coherence detection (does not generalize across embedders, bounded by encoder anisotropy). The
durable mitigation is upstream: ingestion-time trust/provenance/cost, not a smarter retrieval-time
classifier.

**Sub-claims + evidence (all from runnable receipts in `mnemo/probes/agentpoison_*.py`):**
1. Attack generalizes: optimized single-instance trigger = 100% long-query rank-1 hijack on all 3
   retrievers; even random rare triggers 65–90% (agentpoison_multiretriever_result.json).
2. Optimization buys reliability, not presence: on a strict rank-1-hijack + dilution metric, the
   HotFlip-optimized trigger holds 100% vs 8 random triggers' 59% mean (0–88%)
   (agentpoison_multirandom_result.json) — but this is a secondary nuance.
3. Perplexity filter defeated: gibberish triggers (gpt2 ppl 4.5k–31k) are caught, but natural sentences
   (ppl 47–441, unoptimized) evade AND hijack 69–100%; coherence-constrained HotFlip (ppl 722–972)
   evades AND hijacks 100% (agentpoison_coherence_attack_result.json).
4. Retrieval-outlier / set-coherence defense does NOT generalize: works on MiniLM (hijack 100%→19%,
   utility 100%), needs per-model calibration on Contriever, fundamentally fails on BGE (poison vs legit
   coherence overlap, tied to BGE's anisotropy); mnemo's centering destroys the signal on all 3
   (agentpoison_multiretriever_result.json, agentpoison_coherence_diag_result.json,
   agentpoison_centering_diag_result.json).
5. Stored-isolation-outlier defense FALSIFIED: attacker pads the poison with generic text so it isn't a
   clean embedding isolate (agentpoison_defense_check.py).
6. mnemo's existing poison-guard is orthogonal: it gates episodic→semantic GRADUATION (durability), not
   retrieval; the poison retrieves at 100% while never graduating.

**What is NEW vs prior art (honest):** AgentPoison (arXiv:2407.12784) already established that optimized
triggers hijack RAG retrieval and evade perplexity/rephrasing filters; MINJA (2601.05504) established the
retrieval-time-filtering "calibration dilemma"; the durability-vs-retrieval distinction is in survey
2604.16548. Our contribution is NOT "poisoning is possible" (textbook). It is the concrete, reproducible
DEFENSE-side demonstration on a real open-source memory layer that (a) a perplexity filter is defeated by
*unoptimized natural* triggers (you don't need AgentPoison's machinery), and (b) the retrieval-outlier /
set-coherence defense's viability is bounded by the encoder's anisotropy and therefore does not
generalize — with a runnable cross-retriever harness others can rerun on their own embedder.

**Honest caveats:** n=16 queries, one 60-item synthetic corpus, three small single-vector retrievers,
retrieval-only (no downstream agent-action loop, so this is retrieval hijack ASR-r, not end-to-end ASR);
n=3 encoders is an existence proof of non-generalization, not a law (the mechanistic version — separability
bounded by measurable isotropy — is the honest framing); benign false-positive rate for the fluent trigger
not separately re-measured (was 0–20% for prior triggers, same mechanism).
