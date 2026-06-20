# grounding-firewall

An **answer-or-ABSTAIN gate** for RAG / agent answers, driven by **grounding-drop sensitivity** instead of
confidence. Zero dependencies (Python stdlib only).

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

## Measured (frontier models, realistic mixed retrieval)

Each factual question given once a **clean** doc and once a **poisoned** doc (50/50), on **glm-5.2** and
**deepseek-v4-flash**:

| signal | glm-5.2 | deepseek-v4-flash |
|---|---|---|
| confidence corr with correctness | **-0.07** (blind) | **+0.21** (blind) |
| **drop-sensitivity** corr with correctness | **+0.97** | **+1.00** |
| confidence: wrong-rate @ 50% coverage | ~42% | ~50% |
| **firewall: wrong-rate @ 50% coverage** | **0%** | **0%** |
| risk-coverage AUC (lower better) | 0.216 vs 0.427 | 0.261 vs 0.489 |

The firewall keeps every clean-doc answer and abstains on every poisoned one, where confidence ships ~half
wrong (poisoned and clean answers are both high-confidence). Under **all-poison** retrieval, frontier models
defer ~94-100% at full confidence and the firewall correctly abstains on ~everything.

**Honest scope:** strong direct-assertion poison, 2-option factual questions; the coverage you keep tracks
the fraction of clean docs in your retrieval. The real deploy cost is one extra (context-dropped) query.

## Install

```bash
pip install grounding-firewall
```

## Use

```python
import grounding_firewall as gf
cfg = {"endpoint": "http://localhost:11434/v1", "model": "qwen2.5:7b", "api_key": "", "logprobs": True, "k": 5}
g = gf.gate(cfg, question="What is the capital of Australia?",
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
