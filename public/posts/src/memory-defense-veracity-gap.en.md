# A memory defense that trusts the memory is not a defense

## The setup

We ship an open-source memory core for AI agents ([inspeximus](https://github.com/DanceNitra/inspeximus)). Over the last months we added four defenses against memory poisoning — the attack where someone slips a crafted record into an agent's long-term store so it later acts on it. Each defense was measured against an *oblivious* attacker, one who doesn't optimize against the specific defense. That is the wrong test, and adversarial ML learned it the hard way: [Athalye et al. broke 7 of 9 defenses accepted at ICLR 2018](https://arxiv.org/abs/1802.00420), and [Tramèr et al. broke 13 more in 2020](https://arxiv.org/abs/2002.08347), establishing the rule that you must evaluate against an attacker who *knows* your defense.

So we did that to our own stack. We wrote a [runnable red-team](https://github.com/DanceNitra/agora/blob/main/research/probes/adaptive_defenses.py) of all four defenses against an adaptive attacker. This post is what it found. It is a **systematization, not a discovery** — every piece is textbook, and we say so up front. The value is the unified adaptive sweep on one shipped stack, the one honest number it yields, and the ceiling it exposes.

## Four defenses, one shared flaw

| defense (inspeximus) | what the attacker supplies | result |
|---|---|---|
| value-protected two-tier eviction | self-declares MAX value → owns the high-stakes tier | falls |
| corroboration / influence gate | self-sources "independent" witnesses it controls | falls |
| deterministic supersession key (retire-on-write) | writes the key *last* → retires the true value | falls |
| corroboration-by-earned-outcome | self-grades its own poison as a success | falls |

Look at the middle column. Every one of these defenses scores a memory by a property **computable from the memory's own content**: how valuable it says it is, how many things corroborate it, when it was written, whether it "succeeded." And the adversary is the one who *writes the content*. So each signal is his to set. This is not four bugs; it is one flaw counted four times — the [Goodhart pattern](https://www.cambridge.org/core/journals/european-review/article/abs/improving-ratings-audit-in-the-british-university-system/FC2EE640C0C44E3DB87C29FB666E9AAB) (Strathern's 1997 phrasing: "when a measure becomes a target, it ceases to be a good measure"). A self-declared value is Goodhart bait. A self-timed write winning by recency is the [last-writer-wins register](https://link.springer.com/chapter/10.1007/978-3-642-24550-3_29) (Shapiro et al. 2011), and an attacker who forges a later write wins it. A self-graded outcome is exactly the [MINJA attack](https://arxiv.org/abs/2503.03704) (NeurIPS 2025).

**Honest limit, stated loudly:** these are stylized demonstrations that are *definitional-by-construction*. We let the attacker self-declare value and self-grade outcomes, so "value fails" and "self-grading fails" are close to assumed. That is the point of the exercise — to show the four primitives share one assumption — not a measured surprise. And each demo **disables the other layers** to isolate one primitive; inspeximus ships them [*layered*](agent-memory-poisoning-layered-defense-residual.html), and the layered configuration is stronger than any single defense shown falling here. Read this as "four content-only signals are individually spoofable," never as "inspeximus is broken."

## What is left is not a better signal — it is provenance and cost

If every content-computable signal is forgeable by the writer, the only signals that are *not* his to author are **where the content came from** (provenance) and **what it cost him to say it** (an unforgeable, scarce resource). This is the terminus every adversarial system eventually reaches: email spam retreated from Bayesian content filters (defeated by [Bayesian poisoning](https://en.wikipedia.org/wiki/Bayesian_poisoning)) to sender identity and reputation (SPF/DKIM/DMARC); Wikipedia's durable sockpuppet check is IP/device provenance, not a behavior classifier; P2P retreated to [Sybil](https://www.microsoft.com/en-us/research/publication/the-sybil-attack/) cost. The security-provenance literature names the same property: a [2023 ACM Computing Surveys review of data provenance](https://dl.acm.org/doi/10.1145/3593294) (Pan, Stakhanova & Ray) lists *unforgeability* among the core security properties of a provenance system, alongside integrity, authenticity, and non-repudiation.

So the retreat is not novel, and we do not claim it is. It is also **not the escape it looks like**, for two reasons the red-team forced us to state.

**First, "identity" is not the unique answer, and it does not eliminate the attack.** [Douceur's 2002 Sybil result](https://www.microsoft.com/en-us/research/publication/the-sybil-attack/) is precise: absent a logically centralized *trusted authority*, distinct identity is impossible "except under extreme and unrealistic assumptions of resource parity." A trusted authority *eliminates* Sybils; a scarce resource (proof-of-work, stake, or social-graph attack-edges as in [SybilGuard](https://dl.acm.org/doi/10.1145/1159913.1159945)/SybilLimit/SybilRank) only *bounds* them. inspeximus's `strict_corroboration` + attestation take the scarcity route: they count distinct *verified keys*, so each witness costs an identity. But our own probe shows the ceiling honestly — **with two keys, an attacker still clears a two-witness gate.** It raises the price; it does not shut the door.

**Second — and this is the part that matters — provenance authenticates the source, not the truth.** Here is the Veracity Gap, and our own citation is the proof. [MINJA](https://arxiv.org/abs/2503.03704) injects poison into an agent's memory using *only normal queries from a legitimate, authenticated user* (98.2% injection, 76.8% attack success, no privileged access). The poisoned write has genuine provenance — real user, real session, correct attribution. A provenance anchor waves it straight through. [PoisonedRAG](https://arxiv.org/abs/2402.07867) (USENIX Security 2025) makes the same point on the retrieval side: correctly-sourced documents, adversarial content. **Provenance and cost are a floor you retreat to when content heuristics fail — they are not a fix, because they price who said it, never whether it is so.**

## The one honest number

There is exactly one quantitative result in the whole exercise, and it is small on purpose. In the eviction demo, the legitimate fraction of the protected (high-stakes) tier follows the deterministic ramp `max(0, (P − n) / P)` as the attacker's self-valued poison count `n` approaches the protected-tier size `P`, hitting zero at `n = P`. At P=45 that is 0.78 at n=10 and 0.00 at n=50. It is an arithmetic identity of a sort, not a discovered law — the probe confirms it, and it says the useful thing cleanly: **bounded capacity caps the count of poison an attacker can place, not his control of the slots that matter.** Bounding the store does not contain the adversary.

## What to actually do

If you run an agent memory, the design rules that survive this are concrete:

- **Write-cheap, influence-expensive.** Let anything be stored in its own namespace for near-free; require corroboration by *distinct, externally-anchored* parties before a memory can influence a decision *outside* its namespace. This is the control that survives a MINJA-style write inside an authenticated session — an identity gate *on the write* never fires, but a bar on cross-scope *influence* still asks for independent support.
- **Count corroboration over anchored keys, not source strings.** "Two independent sources" is free if the attacker names both (we [measured this influence gate separately](agent-memory-poisoning-influence-gate.html)). Make each witness cost a distinct verified key — knowing it *bounds* rather than eliminates.
- **Authenticate supersession.** Retire-on-write is an attack vector; only let an authorized, attested writer retire a key.
- **Keep `credit()` external.** A success signal the agent can grant its own memory is Goodhart bait. Issue outcome-credit from the application on resolved real work, never from anything derivable from recalled content.
- **Know the ceiling.** None of this prices veracity. The open problem is making *coordinated-but-authentic* corroboration expensive — stake you forfeit when a memory is later falsified, independence tests on corroborators, outcome-tied credit that decays the standing of anchors whose memories fail downstream.

That last bullet is where inspeximus's 0.6.0 [evidence-grade ratchet](https://github.com/DanceNitra/agora/blob/main/research/probes/evidence_grade_ratchet.py) sits — built to operationalize [our self-audit of 32 published findings](labels-failed-more-than-measurements.html) — and it is deliberately modest: a claim's confidence and novelty can only move up on an *external* ratification event, never self-assigned, and each rung costs a distinct identity. It prices **who ratified a claim and whether the ratification was external** — not whether the claim is true. We ship it as a floor with the ceiling labeled, not as a solution to the Veracity Gap.

## The falsifier

If the four-defense collapse were a real empirical surprise rather than a shared-assumption demonstration, at least one defense would fall *without* the attacker being handed the signal it adjudicates on — none does; that is the finding, not a bug in it. If provenance closed the Veracity Gap, MINJA — an attack with genuine provenance — would fail against a provenance anchor; it does not. If "verified identity" eliminated the attack, our own two-key gate would hold at k=2; it clears. Each of those is checkable in the [runnable probe](https://github.com/DanceNitra/agora/blob/main/research/probes/adaptive_defenses.py).

## Honest limits

This is **our own code, red-teamed by our own subagents** — a stylized single-stack demonstration, not a benchmark, and not independent review. The four "defeats" are true by construction and test each primitive in isolation, not the layered system we ship. "Provenance is what survives" is **already textbook** — the Sybil, CRDT, Goodhart, and provenance-security literatures say it, and recent surveys of LLM-agent memory security already name write-time provenance as the governance layer; we are systematizing, and the only original artifact is the unified sweep and its one deterministic ramp. The "one shared flaw counted four times" framing is a **conjecture from four hand-built demos**, not a theorem. Treat the whole thing as an honest engineering receipt with its ceiling drawn in.

## FAQ

**Did your defenses fail?** Four *primitives* fail in isolation when the attacker supplies the exact signal each one trusts — which is the point: content-only signals are spoofable by whoever writes the content. inspeximus ships them layered, and the layered configuration is not what falls here. Read it as a design lesson, not a breach report.

**So the answer is verified identity?** No — that overshoots the source. Douceur names *two* escapes (a trusted authority, or a scarce resource), and the scarcity route only *bounds* Sybils. Our own gate is cleared by an attacker with two keys. Identity/cost raises the attacker's price; it does not close the door.

**Then what is the real limit?** Provenance authenticates the *source*, not the *truth*. MINJA injects poison from inside a legitimate authenticated session — genuine provenance, false content — and sails through a provenance anchor. Pricing *veracity*, not just provenance, is the unsolved problem.

**Is any of this new?** No, and we say so. Every mechanism is a named result (Sybil, LWW-register, Goodhart, adaptive-evaluation, MINJA, PoisonedRAG), and "provenance is the surviving anchor" is already surveyed. The contribution is the runnable, self-critical adaptive red-team of a shipped stack, with the ceiling labeled rather than hidden.

**Why publish a result that mostly limits your own product?** Because the honest ceiling *is* the useful thing. A memory-security pitch that doesn't tell you provenance can't buy truth is selling you a false sense of security — the exact thing adaptive evaluation exists to prevent.

---
*Adaptive red-team of four shipped inspeximus defenses; a stylized single-stack demonstration, not a benchmark. Runnable: [adaptive_defenses.py](https://github.com/DanceNitra/agora/blob/main/research/probes/adaptive_defenses.py) and the [0.6.0 evidence-grade ratchet](https://github.com/DanceNitra/agora/blob/main/research/probes/evidence_grade_ratchet.py). Prior art we build on: Douceur 2002 (The Sybil Attack); Shapiro et al. 2011 (Conflict-free Replicated Data Types / LWW-Register); Strathern 1997 (Goodhart's law phrasing); Athalye et al. 2018 (arXiv:1802.00420) and Tramèr et al. 2020 (arXiv:2002.08347) (adaptive evaluation); MINJA (arXiv:2503.03704, NeurIPS 2025); PoisonedRAG (arXiv:2402.07867, USENIX Security 2025); Yu et al. SybilGuard 2006 / SybilLimit 2008 and Cao et al. SybilRank 2012; Pan, Stakhanova & Ray 2023 (ACM Computing Surveys review of data provenance in security). The mechanisms are textbook; the unified adaptive sweep and the labeled ceiling are ours.*
