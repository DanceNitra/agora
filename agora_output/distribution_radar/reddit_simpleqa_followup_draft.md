# Reddit follow-up draft — SimpleQA generalization (NOT posted; owner posts manually)

Target: r/LLMDevs thread 1ui031b (the original overconfidence/abstain post), as an update/comment.
Tone: short, human, owns the earlier overclaim, credits the multi-sample commenter. Owner can trim to his voice.

---

Quick follow-up — I re-ran this on SimpleQA (n=150) to check it wasn't an arithmetic artifact, and it changed two things for me:

- The verbalized-confidence gradient isn't as clean as I said. The 7B is still a coin flip (AUROC 0.47), but the 30B matches the frontier on raw discrimination (both 0.74). So "small models can't" was too strong — it's really the 7B-class that's at chance.

- What stays a clean gradient is operational: gating to the most-confident quarter gets you 6% → 21% → 62% accuracy across weak/mid/frontier, and only the frontier can answer any chunk at ≥90%. A model can rank its answers correctly and still not know enough to abstain usefully.

On multi-sample (someone raised this earlier): it recovers small models on arithmetic (~0.97) but not on SimpleQA recall (0.57–0.71). Re-sampling helps when the model can re-derive an answer, not when it just doesn't know the fact.

Probe + raw per-item data: https://github.com/DanceNitra/agora/tree/main/research/probes/overconfidence_tax
