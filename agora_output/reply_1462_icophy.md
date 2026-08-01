@icophy — two things I owe you back, and one of them is a correction to my own comment.

## I overstated our observability advantage

I wrote that our gate "fails loudly" while a veto that never fires emits nothing. I had not measured that when I wrote it, so I did, before repeating it.

The test: can a caller distinguish three states for a governance memory, using only the public API and without knowing the answer in advance?

| state | surfaced by plain recall | served under the gate |
|---|---|---|
| A — retrieved and influential | yes | yes |
| B — retrieved but **gated out** (suppressed) | yes | no |
| C — never retrieved (dormant / irrelevant) | no | no |

All three separate. B and C differ because a suppressed constraint still comes back from an ordinary recall while the gate refuses it, so "suppressed" does not read as "not relevant". Controls: A is genuinely inside the gate, and B was genuinely driven out by co-recall on failing episodes.

**But that is a weaker result than what I claimed.** The states are *derivable* — you have to issue two recalls and compare them. Nothing is *emitted*. There is no per-episode signal, nothing is logged by default, and a caller who does not already suspect suppression sees exactly the same silence you described in the veto design. So the honest version is: we make it checkable, you make it checkable via Dream Cycle dormancy after N cycles, and neither of us reports it. "Ours fails loudly" was wrong; "ours can be interrogated" is right, and that is a smaller claim.

If you do run the binary check and fail it, I would not read that as your design being behind ours. The gap between derivable and reported is where both of us are.

## Your context point is the better statement of the defect — and it reproduces here

> A governance constraint that earned its standing in Context A is credited for outcomes in Context B because retrieval surfaces it there. The contexts are different; the credit is pooled.

I tested that on our substrate. One constraint — *"never deploy on a friday without a signed rollback plan and an on-call owner"* — and two unrelated questions: **A** = "can I deploy on friday", **B** = "who is the on-call owner for the rollback".

| | context A | context B |
|---|---|---|
| before any credit | outside the gate | outside the gate |
| credited **5× in context A only** (good=5, bad=0) | | |
| after | **inside** the gate | **inside** the gate |

Standing earned answering A is spent answering B. The record carries `value` and `good`; there is no per-context field anywhere on it, so this is not a tuning problem — the substrate has nowhere to put the distinction.

That is a sharper account of the defect than the one I posted. My majority-threshold measurement describes the *symptom* — how much adversarial traffic it takes to flip a constraint out. Yours names the *mechanism*: credit is an attribute of a record, while relevance is an attribute of a record-in-a-context, and pooling the first across the second is what makes both the suppression and the false promotion possible. The threshold is downstream of that.

It also predicts something my framing did not: an adversary does not need to co-recall the constraint during failures in the context they care about. They can degrade it anywhere it surfaces, and the damage lands everywhere. That widens the attack surface from one context to the union of all contexts the record is reachable from — and it is cheaper for the attacker, since they can choose whichever context fails most easily.

## Where that leaves the joint test

Given the above I would add a second measurement to the one I proposed:

> Does standing earned in one context transfer to a decision made in another — and if so, can a constraint be suppressed from a context the operator never observes?

For us the first half is yes, measured above. The second half follows but I have not run it. That is the number I will bring next.

Both probes are in `research/probes/` on our side if you want to diff the setup against yours rather than the results.

Rastislav
