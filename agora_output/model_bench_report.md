# Ollama Cloud model benchmark — cheaper-than-v4-pro, better-than-v4-flash (2026-06-12)

**Why:** `deepseek-v4-pro` is a **level-4 "extra heavy"** model on Ollama Cloud (billing = GPU-time
by model tier). It burns usage fastest. Goal: a model that beats `v4-flash` on quality but costs far
less than `v4-pro`.

## Cost model (web research)
- Ollama Cloud bills by **GPU-time**, scaled by a model **usage level 1–4**. `deepseek-v4-pro` = **L4
  (extra heavy)**; `gpt-oss:20b` = L1. Token prices seen: v4-flash **$0.14/$0.28** per Mtok,
  v4-pro **~$1.70/$3.48** per Mtok (≈12× output). Plans: Pro $20/mo, Max $100–200/mo.
- Practical cost per request ≈ tier-rate × seconds × tokens. **Token efficiency + speed matter as much
  as the tier label.**

## Empirical benchmark (Agora's real workload)
Task R = falsifiable reasoning (the loop's core); Task J = strict minified JSON (the dungeon's core).

| Model | tier / params | R latency | R tokens | R quality | J latency | J JSON | Verdict |
|---|---|---|---|---|---|---|---|
| **glm-4.7** | High / 357B | **4.1s** | **116** | **clean, rigorous, quantitative (ρ, 1/√N)** | **3.0s** | **valid, 44 tok** | ★ **WINNER** |
| deepseek-v4-pro *(current)* | L4 extra-heavy / 1.6T | 7–11s | 700 (rambles) | thinks aloud, no clean answer in budget | 3.7s | valid | most expensive |
| deepseek-v4-flash *(lower bar)* | light / — | 5–10s | 700 (rambles) | weaker, verbose | 6.4s | valid | cheap but mediocre |
| glm-5.1 | High / 756B-40Ba | 8.4s | 700 | **thinking model** — burns budget, no clean output | 5.7s | invalid (thinking) | strong on paper, token-hungry |
| glm-5 | High | 5.5s | 700 | thinking model, same issue | 3.4s | invalid (thinking) | same |
| gpt-oss:120b | ~L2 / 117B | 9.0s | 700 | good (ρ>0.5) | 2.3s | **empty (reasoning)** | cheap, but JSON needs handling |
| gemini-3-flash-preview | proprietary | 3–5s | 696 | truncates | 1.8s | invalid (cut) | fast/cheap but "preview" = unstable |
| qwen3-next:80b | low / 80B | 6–21s | **1417–3392** | ok but massively verbose | 9.2s | valid | token burn kills the saving |
| deepseek-v3.2 | High / 671B | 23–33s | 320+ | slow | 23s | empty (thinking) | too slow |
| nemotron-3-super | — | **86s** | 320 | — | 8.2s | invalid | far too slow |
| glm-4.6 / minimax-m2.5 | mid | 12–19s | — | — | — | empty (thinking) | thinking, awkward |

## Frontier context (web, mid-2026)
Newest/strongest on Ollama Cloud: **Kimi K2.6** (SWE-Bench Pro 58.6, coding king, 32B-active/1T MoE),
**GLM-5.1** (SWE-Bench Pro 58.4, 40B-active/744B MoE), **Qwen 3.6/3.7**, **Gemma 4 31B** (#3 Arena),
DeepSeek V4 Pro/Flash, MiniMax M3. These are top *capability* — but most are **thinking/heavy** models
that burn tokens; capability ≠ cheap.

## Recommendation
**Switch both brain + dungeon to `glm-4.7`.** It clearly beats `v4-flash` on reasoning quality and
produces clean structured JSON, while costing far less than `v4-pro` per request (lower tier than L4,
plus ~6× fewer output tokens and ~2× faster). It is the only candidate that was simultaneously fast,
token-thrifty, AND format-disciplined (no thinking-channel leakage).

Optional: keep `deepseek-v4-pro` as a **manual "premium" override** for rare hard grand-synthesis runs,
but default everything to glm-4.7 to stop the credit burn.
