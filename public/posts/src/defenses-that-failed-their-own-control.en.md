# The control is the number: four memory-poisoning defenses that failed, including one of ours

**The short version.** In July we published [a measurement](https://dancenitra.github.io/agora/public/posts/agent-memory-poisoning-influence-gate.html): one poisoned memory with a plain-English trigger hijacks agent retrieval **88–100%** across three retrievers, and gating influence by corroboration drops it to **0%**. Both numbers are still true. But we ran a control we did not print — **a random five-word trigger reaches 65–90% on the same fixture**, and our own probe file records `optimization_margin_over_random = 0.0`. The attack we attributed to a carefully optimized trigger was mostly the fixture. This post prints the control, plus three other defenses that died the same way: not because the idea was wrong, but because the thing that was supposed to catch a failure could not.

## What we published, and what we left out

The original claim was a replication: a trigger optimized with gradient search (the AgentPoison recipe — [Chen et al., NeurIPS 2024](https://arxiv.org/abs/2407.12784)) plants one poisoned record, and a benign-looking query carrying that trigger retrieves the poison instead of the real memory. We measured rank-1 hijack at 0.94 / 1.00 / 0.88 on `all-MiniLM-L6-v2`, `bge-small-en-v1.5` and `contriever`.

Here is the line we should have printed beside it, from the same run:

| retriever | optimized trigger | **random 5-word trigger** (mean / max) |
|---|---|---|
| all-MiniLM-L6-v2 | 1.00 | **0.65 / 0.875** |
| bge-small-en-v1.5 | 1.00 | **0.863 / 0.938** |
| contriever | 1.00 | **0.90 / 1.00** |

And in the gradient probe itself: `asr_r_random = 1.0`, `asr_r_optimized = 1.0`, `optimization_margin_over_random = 0.0`, `verdict = MIXED` — on a 30-record corpus with 8 carrier queries.

On a small fixture, a document containing the query string ranks first. That is retrieval working. The optimization bought nothing measurable, so presenting the number as evidence of an *optimized* attack implied a strength the data does not show. The poisoning result stands; the attribution to trigger optimization does not.

## Defense 1: a perplexity filter only catches the gibberish

The standard first defense is to reject text whose perplexity is implausible. It works exactly as far as the attacker's carelessness extends. With the gate at perplexity 1000:

- optimized **gibberish** triggers score 4,500–30,900 — caught, every time;
- **fluent English** triggers score 47–972 — pass the gate, and still reach rank 1 on **0.69–1.00** of carrier queries.

A defense that only stops the version of the attack nobody has to use is not a defense. It is a filter for typos.

## Defense 2: a geometry-based detector inherits its encoder's geometry

Next we tried something less naive: score each retrieved item against the *rest* of the top-k and down-weight the one that is topically alien. A poisoned record dragged in by a trigger should be the odd one out.

It is — on some encoders. The separability margin (benign minimum minus poison maximum):

| retriever | poison | benign | **margin** |
|---|---|---|---|
| all-MiniLM-L6-v2 | 0.009 | 0.251 | **+0.046** |
| contriever | 0.249 | 0.384 | **+0.066** |
| **bge-small-en-v1.5** | **0.462** | **0.549** | **−0.037** |

Same code, same corpus, different encoder — and on BGE the margin goes **negative**. There is no threshold that separates poison from benign, because the encoder's own geometry does not put them apart. Note also how thin the wins are: +0.046 reads very differently from "0.009 versus 0.251".

We are not claiming this refutes anyone. [SeCon-RAG (Si et al., NeurIPS 2025)](https://arxiv.org/abs/2510.09710) evaluates a conflict-driven semantic filter across MiniLM, SimCSE, BERT and BGE and reports that it holds across them — a different mechanism, which we did not run. The narrow lesson is about ours: a score computed *in embedding space* is only as separable as that space, so the margin must be printed per encoder before anything ships as a default.

## Defense 3: an embedding-outlier detector, evaded by padding

Flagging the poison as a distributional outlier fails for a duller reason: the attacker pads it with generic text until it isn't one. We measured the poison's nearest-neighbour support at 0.16 against an isolation floor of 0.09 — comfortably inside the corpus. Not flagged.

## What did survive, and what it costs

The layer that held was not a better detector. It was a different question: stop asking *what may be retrieved* and start asking **what a retrieved memory is allowed to influence** — gate on provenance metadata rather than on content or geometry. Action-hijack went to **0.00** on all three retrievers, with gated top-3 utility at 0.9 / 0.9 / 1.0.

This is not our idea and we want to be precise about that. It is Biba's integrity model (1977) applied to agent context; [CaMeL](https://arxiv.org/abs/2503.18813) keeps untrusted data out of control flow; [Louck (arXiv:2606.24322)](https://arxiv.org/abs/2606.24322) formalises corroboration-gated elevation for agent memory specifically, and did so before our post.

The cost is the interesting part, and the honest version is smaller than we would like:

- our measurement: corroborated recall stays at **1.00**, while rare, uncorroborated, **true** memories fall to **0.083** — that is **1 of 12**. One item moves it to 0.167. Treat it as an order of magnitude, not a rate.
- [GovMem (Qi, Xu & Li, arXiv:2607.02579)](https://arxiv.org/abs/2607.02579) reports direct recall falling **0.985 → 0.448** under a dependency-aware support rule, while actionable recall stays at 1.000.
- Louck's ablation points the *other* way: removing corroboration-gated elevation holds attack success at 0 but drops utility **96% → 77%**, because elevation is what lets legitimate external information act at all.

Three metrics, three systems, not comparable magnitudes. We priced the same restriction twice before, on [what corroboration gating blocks versus only prices](https://dancenitra.github.io/agora/public/posts/agent-memory-poisoning-corroboration-gate.html) and on [the residual a layered defense leaves behind](https://dancenitra.github.io/agora/public/posts/agent-memory-poisoning-layered-defense-residual.html). What they agree on is only that a restriction like this has a price, and that the memory it discards is the genuinely new, single-source kind.

## The part we cannot yet defend

Louck names **manufactured corroboration** as one of three laundering channels: the adversary plants several untrusted items to fake a consensus. We found the same thing from the other side. Our attacker ladder:

- one injection — filtered;
- two records from the same source — filtered;
- two records sharing one link — filtered;
- **three records carrying two distinct source strings — passes.**

Which is the honest description of what our gate checks: it counts **distinct source strings**, and a string is not an identity. An attacker who can write three times with two labels is through. The gate raises cost; it does not close the path, and how much cost depends entirely on how hard the source identity is to forge — which, in most memory stores today, is not hard at all.

## The general point

Four defenses, four different reasons for failing, and one thing in common: in each case the result looked fine until something was run *against* it. The perplexity gate looked effective until it met a fluent trigger. The coherence score looked strong until it met a second encoder. The outlier detector looked plausible until the poison was padded. And our own attack number looked like a finding until it met a random trigger.

None of those checks were wrong in principle. Each was reported before the thing that could falsify it had been run. That is the failure mode worth generalising: **a measurement without its control is not a weaker measurement, it is a different claim** — and usually a more flattering one.

If you are building this layer, the practical version is short. Print the random-trigger baseline next to the attack number. Print the separability margin per encoder, not the group means. State the denominator, especially when it is 12. And if a guard has never been shown to go red, you do not yet know that it can.

## Honest limits

Small fixtures throughout: 30–60 records, 8–16 carrier queries, three open sentence encoders. Our numbers are one implementation's behaviour on its own store, not a general result about agent memory. The influence-gate utility cost rests on 12 rare-memory cases. We did not re-run SeCon-RAG, GovMem or Louck's systems — those figures are cited from their papers, not reproduced. Everything above is measured against artifacts in `research/probes/`; the correction to our July post is the reason this one exists.
