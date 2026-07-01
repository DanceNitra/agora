# Gated reply drafts — 2026-06-28 (Reddit 1ui031b + GitHub #1121). Owner posts Reddit; I post GitHub on approval.

## REDDIT r/LLMDevs 1ui031b — 3 external comments

### -> u/Grue-Bleem  ("external validity is the weak point; agent workflows fail for many reasons")
Totally fair — external validity is the real limit, and it's the #1 caveat in the writeup: this is a mechanism-isolation probe (does confidence track correctness *at all*), not a predictor of real-task success, which fails for plenty of reasons beyond reasoning. The honest next step is a second task family (factual / multi-hop QA) to see if the gradient holds off arithmetic. Appreciate the push — thanks.

### -> u/EbbNorth7735  (wants it run on Qwen3.6-27B, 3.5-122B, DeepSeek V4 Flash, Gemma 4 31B, North Small)
The probe is a single file that reads any Ollama or API model, so those are all easy to add — and I'd genuinely like the data points. The result JSONs save raw per-item rows, so anything you run is directly comparable: https://github.com/DanceNitra/agora/tree/main/mnemo/probes/overconfidence_tax . I'll add a couple I can reach and post back; if you run any of those, drop the JSON and I'll fold it into the table.

### -> u/Combinatorilliance  (KEY: multi-sample / Monte Carlo temp sweep extracts predictive confidence even on small models; arXiv:2502.18389)
Great point, and thanks for the reference — I think it's complementary rather than contradictory. What I measured is specifically the model's *verbalized, single-shot* confidence (the cheap thing an agent gate usually reads), and that's the coin flip on small models. Multi-sample consistency confidence — your Monte Carlo temperature sweep — is a different, more expensive signal, and yes it's far more predictive, even on smaller models. So the practical takeaway actually sharpens: if you can't afford N samples, don't trust single-shot self-confidence below the frontier; if you can, sample-consistency is the way to recover it.

I'd like to run the multi-sample version on the same contamination-free task as a clean head-to-head — verbalized vs sampled confidence, per model. One tension I'd want to probe: a separate result of ours found self-consistency (majority vote over samples) *hurt* accuracy below a per-item accuracy crossover, so the sampling-budget vs base-accuracy tradeoff seems to matter for where sampled confidence pays off. Will dig into your link — appreciate it.

## GITHUB deepseek-ai/DeepSeek-V3 #1121 -> @qingkong66 (offered a shared test-fixture format)
@qingkong66 — appreciate that, and yes, let's make the formats line up. A session-facts + timestamps + valence JSON (the shape from your memory_loop.py) maps cleanly onto what the probes consume — the eviction / corroboration / supersession probes mostly need (item, timestamp, value-or-valence, source) per record, which your fixtures already carry. If you drop even a tiny sample of the Elina-Seed fixtures (10–20 records is plenty), I'll wire an adapter, run the probes on it, and post the numbers so they're comparable across both stacks. I'll open an Elina-Seed issue once I have the adapter + a first result, so there's something concrete to anchor it. Thanks for keeping the door open.
