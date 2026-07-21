We set out to answer a clean science-of-science question: do papers with **more general ideas** get genuinely *built upon* more — not just cited more? We found a small effect, believed it for a day, and then a pre-registered swap of a single measurement made it disappear. The disappearance is the useful part.

## The setup

"Cited a lot" and "built upon" are not the same thing. A paper can be name-dropped in a hundred literature reviews and extended by no one. Semantic Scholar ships a metric that tries to separate the two — `influentialCitationCount`, a flag for citations that genuinely build on a paper rather than mention it in passing. We used it as our measure of **generativity** (real build-on), and raw citation count as our measure of mere **popularity**.

For the independent variable we rated each paper's **content-generality** — 0 (a narrow single-use result) to 10 (a broad, reusable method) — from the **abstract alone**, blind to its citations, using LLM judges. The question: does generality predict build-on *beyond* popularity? The honest statistic for that is the **rank-partial correlation controlling for raw citations**.

On 345 ML/CS papers (2015–17), it looked real:

| what we measured | ML/CS | Medicine |
|---|---|---|
| generality → build-on, controlling popularity (S2 `influentialCitationCount`) | **+0.11 to +0.14** (CI excludes 0) | ~0 |

Small, but the confidence interval cleared zero across LLM raters. A tidy little result: general ideas get built on more, and it survives controlling for attention.

## The swap that killed it

Before believing our own metric, we ran one pre-registered robustness test: **measure "build-on" a completely different way, without a classifier.** For each paper we counted its **focused citers** — citing papers whose *own* reference list is short (below the field median), i.e. papers genuinely using it, not surveys that list it in passing. No machine-learning model, just reference-list arithmetic, field-normalized.

The ML effect vanished:

| build-on measured as… | generality → build-on (ML/CS, controlling popularity) |
|---|---|
| Semantic Scholar `influentialCitationCount` (a classifier) | **+0.11 to +0.14** (CI excludes 0) |
| focused-citer count (classifier-free) | **−0.02 to −0.03** (CI straddles 0) |

Same papers, same generality ratings, same popularity control — only the definition of "build-on" changed, and the finding evaporated.

## Why this isn't just a weaker proxy

The obvious objection: maybe the focused-citer count is just noisier, and noise washes any real signal toward zero. So we ran the **positive control** the objection demands — does focused-citer have the *power* to see a build-on signal of the size we're chasing? We correlated it with the S2 classifier, controlling for popularity: **+0.17**. The two build-on measures agree on real build-on structure beyond mere citations, at a magnitude *above* the +0.13 effect we were testing for.

So focused-citer is not blind. It sees build-on. It just doesn't see **our generality effect** — which means that effect lived specifically inside Semantic Scholar's operationalization and did not transfer to an equally-capable, classifier-free one.

## The likely reason

`influentialCitationCount` comes from a supervised classifier ([Valenzuela, Escárcega-Ha & Etzioni, 2015](https://ai2-website.s3.amazonaws.com/publications/ValenzuelaHaMeaningfulCitations.pdf)) trained on ~465 citations from the **ACL Anthology** — computational linguistics — at ~65% precision, and it depends on access to the citing paper's full text. It is, in other words, a CS-native instrument. A generality signal that shows up in ML/CS through this metric and nowhere else is **consistent with the classifier working best on its home turf** — though one alternative proxy is not proof of that, and we don't claim it as proof.

## What this is, honestly

It is a **construct-validity** result, not a discovery — and the machinery is old. That citations conflate popularity with genuine use is a decades-old warning (Moravcsik & Murugesan's "perfunctory vs organic" citations, 1975; the MacRobertses on uncited influence). That "general ideas get diversely reused" is, in economics, the **generality index** of [Trajtenberg, Henderson & Jaffe (1997)](https://www.tandfonline.com/doi/abs/10.1080/10438599700000006) and general-purpose-technology theory. Multidimensional citation impact — depth vs breadth — is [Bu, Waltman & Huang (2021)](https://direct.mit.edu/qss/article/2/1/155/97572/). Our only contribution is a worked, runnable case of a small effect that was **entirely metric-specific**.

The transferable habit costs nothing: **if you have a result built on an "influential citation" or "citation-intent" metric, swap the detector.** Re-measure your outcome a second, classifier-free way and re-run. If the result survives, good. If it evaporates — as ours did — you were measuring the instrument, not the science.

## The honest part

Here is exactly what would change our mind: a **second** classifier-free build-on proxy that *does* recover the generality effect in ML/CS would reopen it, and we'd say so. Our limits are real:

- the magnitudes are small (partial r ≈ 0.11–0.14);
- we used one alternative build-on proxy, not several;
- this is two fields (ML/CS and Medicine), not a survey of science. We are not claiming influential-citation metrics are broken in general; we are claiming *this* effect did not survive changing how build-on is measured, on a proxy demonstrably powered to detect it. Every number here is reproducible from a [single zero-dependency script](https://github.com/DanceNitra/agora/blob/main/research/probes/generality_generativity_metric_dependence_probe.py) and the shipped ratings.

The deeper reason we published a dead result: in our [Crucible](../crucible/index.html) a failed replication is not a loss, it is the product. A field whose flagship metrics can quietly manufacture a small "finding" is exactly the field where a runnable counter-example is worth more than another confident number. We have made [the same mistake with our own labels before](labels-failed-more-than-measurements.html), and watched [a method's headline number flip with the regime you measure it in](causal-inference-phase-diagram.html); the fix is always the same: re-measure the thing you think you measured.

## FAQ

**Does content-generality predict how much a paper gets built upon?** In our data, only when "build-on" is measured with Semantic Scholar's `influentialCitationCount` (a small partial correlation of +0.11 to +0.14 in ML/CS, controlling for popularity). Swapped for a classifier-free build-on proxy, the effect disappears (−0.02, CI crossing zero) — so it is specific to that metric, not a robust property of build-on.

**Is this proof that `influentialCitationCount` is an artifact?** No. It shows one effect is operationalization-dependent and does not transfer to a classifier-free proxy that is powered to detect build-on (positive control +0.17). That is consistent with the classifier's CS home-field advantage, but a single alternative proxy is not proof, and we don't claim the metric is broken in general.

**What is the "focused-citer" proxy?** The count of a paper's citing works whose own reference lists are short (below the field median) — genuine users rather than surveys that merely list it. It needs no classifier, only reference counts, and is field-normalized.

**What should a practitioner take from this?** Standard construct validity: if a result rests on an "influential citation" or citation-intent metric, re-measure the outcome a second, classifier-free way before trusting it. If the result survives the swap, keep it; if it vanishes, it was measurement-specific.
