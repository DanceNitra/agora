# idcheck — is your causal/attribution number identified, or did the controls inject bias?

> Everyone "controls for everything to be safe." It's backwards. A control is a **claim about the
> causal graph**, and conditioning on the wrong variable doesn't just fail to help — it **injects
> bias** into an otherwise-correct estimate. `idcheck` makes you state the graph and tells you which
> controls to keep and which to drop. One file, zero dependencies.
> A sibling of [nullcheck](../nullcheck) (real-or-noise → identified-or-biased) / [inspeximus](../inspeximus) / [selfref](../selfref).

## The proof (`python idcheck.py`)
```
adjusting for a COLLIDER corrupts a correct estimate:
   true beta |  naive Y~X | + collider | bias injected
        0.00 |     -0.008 |     -0.924 |        -0.924
        0.50 |      0.492 |     -0.884 |        -1.384
        1.00 |      0.992 |     -0.844 |        -1.844
=> the naive model was right; 'more controls' flipped the sign.
```
The naive regression recovers the true effect almost exactly. The moment you add a collider as a
"control," the estimate's **sign flips**. Effect size and number-of-controls tell you nothing about
trust; *identification* does.

## Use it
```python
from idcheck import audit, collider_bias

# tag each variable you condition on by its causal role — that tag IS your identifying assumption
audit({"age": "confounder", "saw_competitor_ad": "collider", "clicked_email": "mediator"})
# -> verdict: BIASED — conditioning on 2 bad controls (saw_competitor_ad, clicked_email); drop them
#    keep: ['age']   identification_score: 0.167

collider_bias(0.5)   # the measured proof at your own beta
```
Roles: `confounder`, `proxy_confounder`, `outcome_predictor` (good — INCLUDE) · `collider`, `mediator`,
`descendant_outcome`, `instrument` (bad — DROP) · `unrelated` (optional). `good_and_bad_controls()`
prints the full table with the reason for each.

## Why a graph, not an autodetector
You cannot tell a confounder from a collider **from the data** — same correlations, opposite
adjustment rule. Identification is an *assumption*, and the honest move is to make it explicit: state
each control's role (the "claim about the graph"), and idcheck applies the back-door logic (Pearl's
good/bad controls). It turns "I controlled for a lot of stuff" into "here's exactly which controls are
admissible and which are injecting bias." It's the identification engine behind our claim-diligence
work, as a self-serve check. Open-core; the core stays free.

## What it is / isn't
`idcheck` audits *which variables to condition on* given your stated causal structure, and proves the
cost of getting it wrong. It does not discover the graph for you, and it assumes your role tags are
honest (garbage-in). Pair it with [nullcheck](../nullcheck): idcheck says whether the number is
*identified*, nullcheck says whether it's *real or noise*.
