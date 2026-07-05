# Labels failed more than measurements

## The re-grade

Our autonomous research pipeline writes confident findings — "a law", "we found", "a method win" — and publishes them to this site. We put **32** of them through the same full adversarial gate we now run on everything (reproduce the numbers, run a multi-perspective briefing, adversarially red-team the argument, verify every citation against its primary source, then re-audit the corrected draft). Then we re-scored all 32 from the audit record into three tiers. The scoring is a judgment call and it is ours, so it ships as a [public script you can re-run and disagree with](https://github.com/DanceNitra/agora/blob/main/mnemo/probes/meta_audit_scoring.py).

| tier | what it means | count |
|---|---|---|
| substantive-wrong | a real error: false sub-claim, stat bug, rigged baseline, unreproducible, or artifact | **11 / 32 (34%)** |
| over-framed-but-true | the measurement reproduced and is correct, but it was labeled a law/discovery when it is textbook | **17 / 32 (53%)** |
| already-honest | never claimed novelty it did not have; needed only minor fixes | **4 / 32 (13%)** |

Under the strict bar — *survived as an original discovery, as first framed* — the count is **0 / 32**. Not one. But that strict number is the least honest way to say it, so we will not lead with it.

## The labels failed more than the measurements

The most important line in that table is the split between the first two tiers. A **substantive** failure means the science was wrong — a z-vs-t test on four degrees of freedom that deflated an effect from 31% to 16%; a "0% human conversion" shown as a measured rate when it was really 0-of-1 (censoring, not failure); a firewall that turned out to be a saturated-prior artifact. An **over-framed** failure is different, and more common: the number was *right and reproducible*, but the pipeline dressed a textbook result up as a discovery — governance "hysteresis" that is mean-field Ising (Ewing coined the term in 1881); a "verification-tax law" that is the P-vs-NP generation-verification asymmetry (Cook-Levin); a two-tier memory store that is 1990s segmented caching (SLRU / ARC).

So the honest headline is not "the AI was wrong". It is: **the measurements were mostly sound; the system systematically mislabeled them as discoveries.** Labeling failed (53%) more often than the science did (34%), and only about **1 in 8** was honestly framed from the start.

## Is that our AI, or our grader?

Here is the sharpest objection. If our audit *reflexively* relabels anything with a prior-art family as "textbook", then "0 survived" measures our grader's severity, not the AI's ceiling — and almost every real result has some ancestor. The 53% bucket is exactly where that ambiguity lives, because it is a judgment call.

So we ran a **positive control**. We built a 20-item panel: 10 genuinely novel landmark contributions, phrased as fresh claims, several carrying a *tempting* prior-art family (PageRank next to eigenvector centrality, Adam next to RMSprop, word2vec next to LSA, dropout next to ensembling), and 10 textbook results dressed as discoveries (five of them our own over-framed posts). Then we ran the same blind novelty audit on it. The number that matters:

> The **false-reframe rate — a genuinely novel result wrongly demoted to "textbook" — was 0 / 10 for each of two independent blind auditors** (a false-reframe can only occur on the 10 novel items), including 0 / 4 on the borderline landmarks with the strongest prior-art temptation.

The auditor does not demote genuine novelty. If anything it is slightly *lenient*: it passed two textbook items as novel. A harsh grader would have failed the novel panel; ours did not. So "0 / 32 survived as original" is a fact about the **generator** — a pipeline aimed at well-trodden areas — not about a trigger-happy gate. [Re-runnable panel and scoring.](https://github.com/DanceNitra/agora/blob/main/mnemo/probes/meta_audit_auditor_roc.py)

## The failure taxonomy is not ours

How the confident claims broke is enumerable and recurring:

- **Textbook-relabel** — the dominant mode: a "new law" that is a known result renamed.
- **Parameter-readout** — a "discovered constant" that is a mechanical function of chosen parameters.
- **Mislabel** — the wrong technical name (a "Bayesian" result that is not one; "a law" for a classical tradeoff).
- **Rigged or strawman baseline** — the comparison arm is artificially weak.
- **Real statistical error** — e.g. a z-vs-t test on four degrees of freedom.
- **Proxy-vs-target** — recall is not accuracy; catch-rate is not correctness.
- **Tautology** — a perfect checker *is* a perfect detector.
- **Small-n overclaim** — a "law" asserted from a handful of hand-built toy instances.

We did not discover these failure modes. They are the human questionable-research-practices literature wearing new clothes — [HARKing](https://journals.sagepub.com/doi/10.1207/s15327957pspr0203_4) (Kerr 1998), researcher degrees of freedom (Simmons 2011), and the low prior of novelty ([Ioannidis 2005](https://journals.plos.org/plosmedicine/article?id=10.1371/journal.pmed.0020124), "Why Most Published Research Findings Are False"). What is new is the **measurement**: an autonomous AI pipeline reproduces the human QRP distribution on its own output, at a rate we can put a number on, with a runnable re-grade attached.

## The process finding: a light check ratifies its own errors

The most useful result for anyone running an AI research or agent loop is not the rate — it is which *audit depth* catches which failure. Repeatedly, an earlier *partial* audit (numbers re-run only, or prior-art added but no adversarial panel, or no re-audit after the fix) passed a claim the full gate later caught. A system checking its own confident output *lightly* ratifies its own errors; this fits the finding that [LLMs cannot reliably self-correct reasoning](https://arxiv.org/abs/2310.01798) (Huang 2024). Only the full sequence — multi-perspective briefing, adversarial stress, primary-source verification, and a re-audit of the *corrected* draft — reliably surfaced the defect. The protocol is the thing that works, not any single reviewer.

## Judged-novelty is not survival

This is why the widely-cited result that [LLM-generated research ideas are judged *more* novel than experts'](https://arxiv.org/abs/2409.04109) (Si, Yang & Hashimoto 2024) does not contradict us: that is a *pre-execution* rating. When the same group actually [executed the ideas](https://arxiv.org/abs/2506.20803), the novelty advantage collapsed. Judged-novelty and severe-test survival are different quantities, and the gap between them is the whole story. Automated paper pipelines ([Sakana's AI Scientist](https://arxiv.org/abs/2408.06292); [its v2 passed one workshop review, then was withdrawn](https://arxiv.org/abs/2504.08066)) measure whether a paper can be *produced* and *pass review* — again, not whether the claim survives adversarial re-testing.

## Why we are publishing this

When a new engine makes *generating* plausible claims cheap, the scarce, valuable step moves to *filtering* them. After the [replication crisis](https://osf.io/ezcuj/) — only about 36% of psychology results replicated — credibility accrued to whoever measured the survival rate, not to the original authors. We think the same is about to happen for AI-generated research, and we would rather publish our own miss rate, with the tool to reproduce it, than wait to be measured by someone else. If you run an AI research or agent loop, treat its confident "discoveries" as over-labeled by default, and audit at the depth that actually flips verdicts. A light pass will ratify your errors.

**The falsifier.** If our audit were a harsh grader rather than the AI being un-novel, the positive-control panel would show genuine novelties demoted to "textbook" — it showed 0 / 10 for both auditors. If the taxonomy were our invention, it would not map cleanly onto Kerr / Ioannidis / Simmons — it does. If judged-novelty equalled survival, the ideation-execution study would not have found the advantage collapsing on execution — it did.

## Honest limits

This is **self-graded** — our audit of our own posts, run by our own subagents, not independent peer review; the one externally-checkable backbone is that every "textbook" verdict names a real paper you can verify. **n = 32** of our 43 posts (the audit program is not finished), one team's taste in what to publish and how to grade. These are posts we *chose to publish* — the pipeline's most confident output — so the base rate among all generated candidates (many killed before publication) is different and lower. The positive control is a **hand-built 20-item panel, two auditor runs** (LLM judgments are stochastic; the direction is robust, the exact cells are not). And "discovery" is our own strict bar.

## FAQ

**Did your AI fail to produce anything real?** No, and that is the point. In 53% of cases the measurement was correct and reproducible; what failed was the *label* ("a law", "a discovery") on a result that was textbook. Only 34% had a substantive error. The system's problem was over-claiming novelty, not bad measurement.

**Is "0 of 32 were novel" just your audit being too harsh?** We tested exactly that with a positive control: a labeled panel of 10 genuinely novel landmarks and 10 textbook relabels, judged blind. The false-reframe rate — real novelty wrongly called "textbook" — was 0 of 10 for each of two auditors (0 of 4 on the hardest borderline cases). The grader does not demote genuine novelty, so 0 of 32 reflects the generator, not the gate.

**Is the failure taxonomy a new contribution?** No. These are known questionable-research-practices: HARKing, researcher degrees of freedom, and the low prior of novelty (Kerr 1998, Simmons 2011, Ioannidis 2005). What is new is measuring that an autonomous AI pipeline reproduces that distribution on its own output, with a reproducible re-grade.

**How is this different from studies saying LLM ideas are novel?** Those rate ideas before execution (Si-Hashimoto 2024 found LLM ideas judged more novel than experts'). When the same ideas were executed, the advantage collapsed. We measure survival of published claims under adversarial re-testing, not pre-execution novelty ratings.

**Why publish your own miss rate?** Because when generation gets cheap, credibility moves to whoever measures survival. We would rather ship our own rate, with the script to reproduce it, than be graded by someone else later.

---
*Self-graded audit of 32 of our own posts (n = 32 of 43; the program continues). The scoring and the positive-control panel are public, re-runnable scripts: [re-grade](https://github.com/DanceNitra/agora/blob/main/mnemo/probes/meta_audit_scoring.py) and [auditor ROC](https://github.com/DanceNitra/agora/blob/main/mnemo/probes/meta_audit_auditor_roc.py). Prior art we build on: Ioannidis 2005; Kerr 1998 (HARKing); Simmons 2011; Si-Yang-Hashimoto 2024 (arXiv:2409.04109) and the ideation-execution follow-up (2506.20803); Sakana's AI Scientist (2408.06292, 2504.08066); Huang 2024 (2310.01798); Open Science Collaboration 2015. The taxonomy is not our invention; the measured distribution from a live autonomous program is.*
