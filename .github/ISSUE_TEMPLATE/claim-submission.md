---
name: Submit a claim for replication
about: Propose an AI/ML claim for the Crucible — we'll forecast it publicly before we replicate it
title: "[claim] <one-sentence falsifiable claim>"
labels: claim-submission
---

**The claim (one falsifiable sentence, with the number if it has one):**
<!-- e.g. "Chaining LLM agents at 95% per-step reliability collapses to 77% end-to-end at 5 steps." -->

**Source (who says it, where):**
<!-- paper / blog / thread URL + date. Vendor claims and widely-repeated folklore are welcome. -->

**Why it's computable as a minimal model:**
<!-- can it be tested on a single machine with API-class LLMs or pure simulation? no giant training runs. -->

**Why FAILED is a live possibility:**
<!-- we deliberately hunt claims that could fail. If it's a proven theorem, it's probably not a fit. -->

---
What happens next (see [the protocol](https://dancenitra.github.io/agora/public/forecast.html)):
we write a claim card, a frozen forecaster publicly commits P(reproduced) BEFORE any harness exists,
we replicate it as the smallest faithful computational model, and the verdict + Brier score land in
[the Crucible](https://dancenitra.github.io/agora/public/crucible/) with a runnable receipt.
Third-party submissions like yours remove our claim-selection loop — thank you.
