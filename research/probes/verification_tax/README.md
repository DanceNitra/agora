# The verification tax — how much error survives self-verification

A runnable probe behind the post
[*The verification tax*](https://dancenitra.github.io/agora/public/posts/the-verification-tax.html).
It measures the **residual error after self-verification**: a model answers, then checks its own answer, and
we record `residual = e · (1 − c)` where `e` = first-pass error rate and `c` = fraction of errors the
self-check *catches* (flags as wrong). The question is whether `c` tracks **task difficulty** or **task
checkability** — i.e. whether a cheap ground-truth check exists.

**What this is an instance of (prior art — this is not a new law).** The generation–verification asymmetry is
the *definition* of NP: solutions can be cheap to verify yet hard to produce (Cook 1971; Levin 1973). That a
task with a **sound** checker leaves zero residual is therefore true **by construction** — the "keystone"
control below confirms the framing, it does not discover it. The empirical LLM half is also established:
intrinsic self-correction without external feedback does not improve (often degrades) reasoning
(**Huang et al., "LLMs Cannot Self-Correct Reasoning Yet," ICLR 2024**, arXiv:2310.01798); LLM errors are
**correlated across model families**, and *more accurate models have more correlated errors*
(**Kim, Garg, Peng & Garg, "Correlated Errors in Large Language Models," ICML 2025**, arXiv:2506.07962) — which
is why a second, independent model doesn't rescue the check. The economics is **costly state verification**
(**Townsend 1979**). What this probe adds is only the *measured LLM magnitudes* on a contamination-free set,
with honest CIs.

## Results (original run: worker + self-verifier = `qwen3-coder:30b` local; one frontier run = `glm-5.2`)

Raw per-task summaries are in `verification_tax_result.json` (local), `verification_tax_glm_result.json`
(frontier), `verification_tax_wide_result.json` (firmed n=60/cell), `verification_independent_result.json`
(independent checker). Wilson 95% CIs computed from the reported n:

| task | n | first-pass error | self-verify catch `c` | 95% CI on `c` | residual |
|---|---|---|---|---|---|
| arithmetic (cheaply checkable) | 25 | 0.08 | **1.00** | [0.87, 1.00] | **0.00** |
| MMLU-Pro (hard, not cheaply checkable) | 25 | 0.44 | 0.36 | [0.21, 0.56] | 0.28 |
| MMLU-Pro (firmed) | 60 | 0.30 | 0.17 | [0.09, 0.28] | 0.25 |
| multi-hop QA (hard, not cheaply checkable) | 60 | 0.42 | 0.36 | [0.25, 0.49] | 0.27 |
| **constraint search (hard to solve, cheaply checkable)** | 40 | 0.35 | **1.00** | — | **0.00** |

**Keystone (constraint search).** A "find a 3-digit N with digit-sum S, divisible by D, of parity P" task is
genuinely hard to *solve* (35% first-pass error) but every constraint is mechanically checkable, so the
self-check catches ~all errors and residual → 0. Read honestly: a mechanically-checkable task means the
verifier *is* a ground-truth oracle, so catch ≈ 100% is close to definitional — this **confirms** the NP
framing rather than discovering it.

### The cross-model comparison does NOT survive its own noise (why the post no longer headlines it)

At n≈25–60 per cell the catch-rate CIs overlap almost completely, so the "a stronger model self-checks worse"
story is **not** statistically supported and is additionally confounded by strict automated grading of a
frontier model's formatting:

| checker on hard reasoning | catch | 95% CI | note |
|---|---|---|---|
| `qwen3-coder:30b` checks itself | ~0.34 | wide, overlaps below | mean of MMLU-Pro + multi-hop |
| `glm-5.2` checks itself | ~0.19 | [~0.04, ~0.46] | false-alarm 0.00 **in-sample** (n=25; rule-of-three upper bound ≈0.12) |
| `glm-5.2` checks `qwen`'s answers (independent) | ~0.23 | [0.12, 0.44] | shared blind spots (Kim et al. 2025) |

The honest reading: **no** stack (self, stronger-self, independent-and-stronger) pushed hard-reasoning
error-catching clearly above ~1/3, consistent with Huang et al. — but the *ranking between models is within
noise*, so we do not claim "stronger is worse."

## The reframe the audit forced: the residual is a property of the verification CHANNEL, not the task

"Un-checkable" here means only "no cheap **ground-truth channel at inference time**" (the MMLU-Pro/multi-hop
items *do* have gold answers — that's how they were graded). This is a property of the verification protocol,
not a ceiling of hard reasoning. Because LLM errors are correlated across weights, a *second model* shares the
blind spot — but a channel that is **not drawn from the training distribution** (run the code, retrieve the
primary source, decompose into machine-checkable sub-claims; process supervision, **Lightman et al. 2024**,
arXiv:2305.20050) breaks the correlation by construction. So the open question is whether the residual is
governed by task difficulty at all, or by *how much of the reasoning the verifier can route through an
external ground-truth channel*.

## Run it

```bash
# default targets local Ollama (http://localhost:11434) with qwen3-coder:30b; override via env:
export VTAX_URL="https://your-openai-compatible-endpoint/v1/chat/completions"
export VTAX_MODEL="your-model"
export VTAX_API_KEY="sk-..."         # only if the endpoint needs auth
python verification_tax.py            # arithmetic + MMLU-Pro + numeric + multi-hop self-verify
python constraint_verification.py     # the hard-but-checkable keystone control (standalone: no dataset needed)
python verification_independent.py    # Part 3: an independent stronger model as the checker
```

`constraint_verification.py` and the arithmetic task are fully standalone. The MMLU-Pro / multi-hop (MuSiQue)
tasks read local dataset files (`data/…`) not bundled here — point them at your own copies, or just run the
constraint + arithmetic controls, which reproduce the checkable-vs-uncheckable contrast on their own.

## Honest limits

- Two models (one mid-local, one frontier), n = 25–60 per cell. The residual magnitudes are **directional, not
  a scaling law**; two points cannot establish invariance to model capability, so we make no "irreducible"
  claim.
- `residual = e·(1−c)` is an identity, not an independently-measured constant — change either input and it
  moves.
- The frontier (`glm-5.2`) run's higher error is partly strict-grading/format strictness (its own caveat),
  which is exactly why the cross-model ranking is not load-bearing.
- Self-verification is the **tool-free floor**; verifier-with-tools / process-supervision / best-of-N + a
  trained verifier are different (and likely lower-residual) regimes not tested here.

MIT-licensed. Part of Agora / inspeximus (https://github.com/DanceNitra/inspeximus).
