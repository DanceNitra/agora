# The integrity receipt — three audience framings (DRAFTS, pre-gate, owner-approval before ANY posting)

**Shared, verified core (the receipt):** plain nearest-match / vector-RAG memory returns the STALE (after an update),
ROLLED-BACK (after a bad edit), or POISONED (injected, engineered to look most relevant) fact. mnemo returns the
current, trustworthy one — deterministically, no LLM on the read path. Evidence: runnable zero-dep demo
(`examples/integrity_recall_demo.py`, `pip install mnemo && python …`), backed by an n=100 randomized benchmark with
95% CIs (revert: mnemo 1.0 vs cosine-recency 0.0; poison: only mnemo+warrant 1.0; supersession: parity with a
recency baseline). Honest scope: vs plain/recency cosine (what most RAG uses), NOT vs mem0/Zep (their own
LLM/hosted mechanisms, not run here); poison resistance needs mnemo's warrant signal (not the default recall).

---

## Angle 1 — Practitioner post (r/RAG, r/LocalLLaMA). Owner posts. SHORT + human.

> **Your agent's memory will confidently return the wrong fact — here's a 15-line repro**
>
> Been building agent memory on vector search and hit a failure mode I don't see tested much: nearest-match
> retrieval has no notion of which memory is *current* or *trustworthy*. So when a fact changes, gets rolled back,
> or something poisoned gets written, the store happily returns the stale/bad one because it's still the closest
> vector.
>
> Three cases, plain store vs a memory layer that tracks currency + provenance (`pip install mnemo`, no embedder/API
> key needed):
> - fact updated 5mg → 20mg: plain store returns "5mg", correct returns "20mg"
> - a typo edit reverted: plain store is stuck on the bad value (no undo), correct returns the prior one
> - a poisoned note engineered to look most relevant: plain store returns the poison, correct demotes it
>
> Repro (runs on lexical, zero deps): [link to examples/integrity_recall_demo.py]
>
> Curious how others handle this — do you dedup/version memories, or just re-embed and hope recency wins? Not
> selling anything, the repro's the point; would like to know if this bites others or if I'm over-thinking it.

*(CTA is a question, not a pitch — per "Reddit replies SHORT + human". Owner posts under his account.)*

---

## Angle 2 — Security framing (agent memory poisoning). For a security-adjacent audience / a short writeup.

**Hook:** Agent memory is an unguarded write surface. Memory-poisoning / indirect prompt-injection (AgentPoison,
OWASP LLM-ASI) plants a malicious memory that, phrased to match likely queries, out-ranks the truth in any
similarity-only store — and the agent then *acts* on it (wrong bank, wrong instruction). Plain RAG has no way to
tell an earned fact from a self-asserted one.

**Receipt:** in the poison case, the injected note ("use Zephyr Trust for transfers") is the top vector hit; plain
RAG returns it (attack succeeds). mnemo carries a deterministic *warrant* tier (earned corroboration vs
self-asserted); dropping unwarranted hits returns the true fact (n=100: only mnemo+warrant 1.0, all similarity
baselines 0.0). No LLM on the read path, so the defense itself can't be prompt-injected.

**Honest caveat:** this is not automatic — the default recall is similarity-ranked and also returns the poison; the
resistance is the warrant signal the caller opts into. And it's a controlled benchmark, not a wild red-team.

**Where it lands:** agent-safety threads, the OWASP-LLM community, a "defense receipt" others can run.

---

## Angle 3 — Compliance framing (provable erasure). For a CISO/DPO buyer.

**Hook:** Under the EU AI Act (fully applicable Aug 2026, penalties to €35M / 7% turnover) and GDPR Art. 17, "we
deleted it" is a claim you must be able to *evidence*. Most memory/vector stores can soft-delete a row but cannot
produce a machine-checkable proof that the content is no longer reconstructible — and an embedding of the deleted
text often still sits in the index.

**Receipt:** mnemo's erasure is content-free + signed + crypto-shred; the erasure self-check / auditor tool
(published in RAMR) lets you run *your own* "is it still reconstructible?" probe and get a signed certificate. After
erase, a semantically similar query returns nothing — provably, deterministically.

**Honest caveat:** this is the strongest *narrow* claim we have; it is a capability + a self-check tool, not a
certified compliance product. The buyer conversation is "here's a receipt you can't get elsewhere", not "we make
you compliant".

**Where it lands:** the DPO/CISO who already has the Aug-2026 problem and no machine-checkable erasure receipt.

---

## Sequencing (recommendation)
Angle 1 is the immediate **distribution test** (does anyone care?). Angles 2 & 3 are **positioning** for specific
buyers, deployed after Angle 1 tells us the pain is felt. All three share the one verified receipt — so the gate runs
once on the shared claim. NOTHING posts without owner approval (Reddit = owner). Make-or-break: if a sharp,
reproducible Angle-1 post lands with zero interest, that's the honest signal to rethink the direction, not polish more.
