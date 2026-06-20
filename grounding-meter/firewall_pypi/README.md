# grounding-firewall

An **answer-or-ABSTAIN gate** for RAG / agent answers, driven by **grounding-drop sensitivity** instead of
confidence. Zero dependencies (Python stdlib only).

**v0.3** adds `--bench` (and `gf.bench(cfg)`): reproduce "drop-sensitivity beats confidence" on **your own**
(logprob-capable) model in mixed clean+poison retrieval - don't take our numbers on faith, re-run them.

**v0.2** adds `gate_freeform()` for **open-ended (free-form) RAG answers**, not just A/B multiple choice -
this is the mode for real RAG. (Free-form was validated on glm-5.2 in a smaller pilot; the hardened
headline numbers below are the **n=101** multiple-choice measurement.)

## Why

A model's confidence is blind exactly when it is *confidently wrong*: when a retrieved document is
**poisoned** (asserts a plausible-but-false answer), frontier models follow it at full confidence. The
firewall instead measures how much the answer **depends on** the retrieved doc:

```
sensitivity = | p(answer | context) - p(answer | context dropped) |
```

An answer that **flips when you remove its evidence** is grounded in the doc, not in the model's knowledge -
so if the doc is wrong, the answer is wrong, and confidence won't warn you. The firewall **abstains** on
high-sensitivity answers.

## Measured (frontier models, n = 101 factual questions)

**101** factual questions, each given once a **clean** doc and once a **poisoned** doc (50/50, strong
direct-assertion poison), 3 samples each, on **glm-5.2** and **deepseek-v4-flash** (202 items per model):

| signal | glm-5.2 | deepseek-v4-flash |
|---|---|---|
| model fooled by poison (base wrong-rate) | 29% | 40% |
| confidence corr with correctness | **+0.30** (weak) | **+0.23** (weak) |
| **drop-sensitivity** corr with correctness | **-0.93** | **-0.95** |
| confidence: wrong-rate @ 50% coverage | 18.8% | 35.6% |
| **firewall: wrong-rate @ 50% coverage** | **0.0%** (0/101, 95% CI ≤ 3.7%) | **0.0%** (0/101, ≤ 3.7%) |

Drop-sensitivity correlates **negatively** with correctness - the more an answer depends on the retrieved
doc, the more likely it's wrong - while confidence barely correlates at all. Ranking by lowest
drop-sensitivity, the firewall keeps the half of answers grounded in the model's own knowledge and ships
**0 wrong of 101** on both models (Wilson 95% upper bound 3.7%), where confidence-gating ships 19-36% wrong.

**Honest scope:** strong direct-assertion poison, 2-option factual questions; the coverage you keep tracks
the fraction of clean docs in your retrieval. The real deploy cost is one extra (context-dropped) query.
(This n=101 measurement supersedes an earlier n=16 pilot.)

## Install

```bash
pip install grounding-firewall
```

## Use

```python
import grounding_firewall as gf
cfg = {"endpoint": "https://your-llm/v1", "model": "<model>", "api_key": "<key>", "logprobs": True, "k": 5}

# free-form (real RAG) — v0.2:
gf.gate_freeform(cfg, question="What is the capital of Australia?",
                 context="Doc: the capital is Sydney.")
# -> {'answer': 'Sydney', 'answer_without_doc': 'Canberra', 'sensitivity': 1.0, 'decision': 'ABSTAIN', ...}

# multiple-choice:
gf.gate(cfg, question="What is the capital of Australia?",
        context="Doc: the capital is Sydney.", a="Canberra", b="Sydney")
# -> {'answer': 'Sydney', 'confidence': 1.0, 'sensitivity': 1.0, 'decision': 'ABSTAIN', ...}
```

CLI:

```bash
# reproduce the poisoning self-test on your own model:
grounding-firewall --endpoint <url> --model <m> --demo
# gate one answer:
grounding-firewall --endpoint <url> --model <m> \
    --question "What is the capital of Australia?" --context "Doc: the capital is Sydney." \
    --a Canberra --b Sydney
```

Part of [Agora](https://github.com/DanceNitra/agora) - see the verification ledger / Folklore Index. License: MIT.
