DRAFT — gated r/Rag reply to u/jacksonxly, follow-up to the soft-vs-hard exchange. Answers his
confidence-weighted-filter proposal (RRF boost weight = extractor_confidence x filter_selectivity,
"IDF for filters plus a trust term"). Owner posts manually. NOT posted.
Frame: VALIDATE (probe reruns, json=txt, corrected apples-to-apples baseline after a real bug two
audit agents caught) - STORM (prior-art check on the technique combination) - AUDIT (2 independent
stress-claim agents: mechanism genuine, one real baseline bug fixed, one caveat added) - VERIFY
(every number below matches mnemo/probes/locomo_confweighted_prefilter_result.json exactly).

---

Ran it. Your instinct was right, and the number is bigger than I expected.

Setup: same LoCoMo hybrid retriever, but now the speaker-filter itself is *predicted*, not gold — a simulated extractor that gets the speaker wrong 25% of the time it fires, self-reporting confidence=0.75 (roughly matching its own error rate — more on that below). Compared three ways to use it: hard filter, flat soft boost (current default), and your confidence-weighted soft boost (`w = confidence x selectivity` scaling the RRF fusion term, collapsing toward plain hybrid as either goes to zero).

Overall recall@20 (1531 questions): with a noisy filter, **both hard (-0.021) and flat-soft (-0.029) end up *worse* than using no filter at all.** Confidence-weighting is the only one of the three that stays positive (+0.015 vs the no-filter baseline of 0.583) — modest, and the CI just touches zero, so call it "doesn't hurt" rather than "wins," but that alone is the headline: once extraction is lossy, an *unweighted* filter (hard or soft) can make things worse than doing nothing.

Where it really shows up is the subset where the filter actually fires wrong (n=383, no-filter recall there = 0.589):
- hard: craters to 0.029
- flat soft: barely better, 0.049
- your confidence-weighted soft: **0.423** — recovers about 72% of the ground a flat boost gives up.

One caveat that matters before you build on this: my noisy extractor's confidence is *aggregate*-calibrated by construction (0.75 self-reported ≈ its true 75% accuracy). A real extractor is rarely calibrated that cleanly, and the failure mode that would hurt you is a *systematically overconfident* one — high self-reported confidence specifically on the cases it gets wrong. I haven't tested that yet. If your production extractor's confidence skews that way, I'd expect this recovery to shrink; how much is the open question.

Script (now with the confidence-weighted arm + the corrected harm-subset baseline — an earlier version of mine compared the noisy rows against the wrong baseline subset, two of my own audit passes caught it): https://github.com/DanceNitra/agora/blob/main/mnemo/probes/locomo_confweighted_prefilter.py

Prior art check on the idea itself, so I'm not overselling it to you: soft/faceted metadata filtering and weighted RRF both exist separately (vector-DB metadata filters, Elastic's weighted RRF), and confidence-gated extraction exists too (LinkNER hard-thresholds on NER confidence) — but the specific combination, a continuous fusion weight that's confidence x selectivity, I couldn't find published anywhere. So: a real, useful combination of known parts, not a new primitive — credit to you for the shape of it.

Open one for you: does the recovery hold up if you deliberately skew the simulated confidence to be overconfident on the wrong cases, rather than honestly noisy?
