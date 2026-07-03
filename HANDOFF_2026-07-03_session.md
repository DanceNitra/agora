# Session handoff — 2026-07-03

Continuity record for the next session. English + public-safe (this repo is public; no secrets/paths/keys).
Companion to `HANDOFF_CURRENT_STATE.md` and `HANDOFF_LOOP_PROMPT.txt`.

## TL;DR
A long build+audit session. Shipped real fixes and a cross-framework collaboration; ran 5 rigorous
severe-tests of "cognitive method" ideas and **honestly killed 4 of them as resource/known-result
confounds**. Net: strong credibility (we ship nothing unverified), one operational bug fixed, one live
collaboration deepened, and one genuine methodological through-line worth publishing. No breakthrough — and
that is stated plainly, not spun.

## Successes (shipped / proved)
- **Lab-ledger rotation fix (commit 0b6a34d)** — the 4th root cause of the recurring "0 notes/day": `.lab.json`
  cap was 100 (`.methods.json` 200), which at ~100 runs/day rotated a valid `lab_id` out within ~12h, so the
  LAB-FIRST gate falsely rejected discoveries citing a REAL-but-older experiment (`src_no_lab`) and audits
  couldn't find source scripts. Caps raised to 1000. Brain restarted, verified healthy (1 listener :8000,
  dungeon 200).
- **Cross-framework benchmark (DeepSeek-V3 #1462/#1466)** — delivered B-002 identity-override substrate trace;
  Marat's TAT-7 divergence confirmed our out→out prediction row-for-row (B-003 out→in vs B-002 out→out, same
  mechanism opposite verdict). We're the named "storage/substrate" layer; qingkong66 called our influence-gate
  "the cleanest substrate-level contribution so far." Joint report due **July 6**.
- **M2 forged-provenance attack CONFIRMED (commit e3389d2)** — measured that mnemo's `>=2 distinct-source`
  corroboration gate is Sybil-forgeable (two fresh domains pass). Answered the open #1462 obligation with a
  receipt. Posted (comment 4878412868).
- **B-001 recall + composed-soft-filter deployment numbers** published (commits c88f33b, fa25743) — jacksonxly
  r/Rag exchange; gave the honest full-composable-set deployment number (0.768 vs 0.585, +0.183).
- **Library drain (earlier)** — 200 papers triaged (27 A-grade), vault notes pushed, 3 Labs banked
  (e947cb calibration-not-closed-under-soft-mixing CONFIRMED; 65a02d/607862 grounding-fraction collapse
  refined). Product-upgrade roadmap created.
- **Fable-5 usage skill** built from a Storm run (early session), verified 16/16 citations.

## Honest kills / negatives (the severe-test working)
- **M1 embedding-norm re-ranker → REFRAME/dead (0718a40)** — the norm "advantage" is a LENGTH prior
  (corr(|d|,len) = -0.71); indistinguishable from a length re-rank. Not shipped.
- **M2 burst-monitor defense → NEGATIVE (e3389d2)** — the naive stateful fresh+burst monitor does NOT
  discriminate (TPR=FPR=1: withholds genuine simultaneous reporting identically to the attack) and 2/3 attack
  variants bypass it (pre-age / drip). Not a defense.
- **M2b blast-radius soft authority → KILLED by audit** — jacksonxly's idea, built + measured, but a 5-lens
  storm/audit showed it (a) restates Douceur-2002 Sybil impossibility, (b) gates a memory's AUTHORITY not its
  INFLUENCE (the low-blast read it "recovers" is the carrier that poisons a trusted memory's context), (c) its
  numbers are hand-constant artifacts. Prior art: NIST RAdAC, Biba integrity, CaMeL. Not shipped.
- **Atomic-decomposition calibration law → REFUTED (151c2e3, 0373a11, 84cffd7)** — Run 1 (holistic capped 250
  tok) looked like a dramatic CONFIRM (Δ→1.0 at K=8) but was a **token-budget confound**: decomposition makes
  K calls = K× tokens. With ample tokens, Δ=0 at every K across deepseek-v4-flash, deepseek-v4-pro, kimi-k2.6
  (2 families) + Claude inline. Also NO advantage on subtle chained affirming-the-consequent fallacies
  (hint-free + distractors): holistic ample-token judging catches every fallacy. Refuted on everything cleanly
  ground-truthable.

## The one genuine through-line (worth publishing, gated)
**In LLM cognition/memory, apparent "method wins" (decomposition, gating, ensembling, re-ranking) are
dominated by RESOURCE confounds (compute/tokens) or reduce to known impossibility results (Sybil). Control
for resources and cite prior art BEFORE crediting the method.** Five measured instances in one day (M1=length,
M2b=Douceur, decomposition=tokens ×2, burst-monitor=no-discrimination). Honest-negative, Crucible-style.
Draft: `agora_output/drafts/20260703_resource_confound_thesis_DRAFT.md`. NOT published — needs the full
validate→storm→audit→verify gate + owner approval.

## GitHub posts made this session (owner-approved, Claude posts on GitHub)
- #1466 comment 4877697246 — B-002 delivery
- #1466 comment 4878364214 — B-002 confirmation
- #1462 comment 4878412868 — forged-provenance / Sybil measurement

## Pending / owner-posts-manually (Reddit)
- **jacksonxly r/LangChain poison-RAG reply** (honest: Sybil measured, burst-fix fails, risk-scaling = Biba/
  RAdAC/Douceur, forward "cost-to-mint / attestable provenance" door). Drafted, ready, owner to post.
- (Older) hannune r/LangChain corroboration-fasttrack draft — still pending.

## Watch / open threads
- **July 6 joint report** (#1462/#1466): VERIFY our B-001/B-002/B-003 numbers vs probes; ensure Marat's report
  does NOT attribute his overclaimed Triumvirate −0.450 to us (we chose NOT to endorse it).
- Marat's TAT-T divergence rows; qingkong66 synthesis.
- **The one real open research question**: does decomposition help on genuinely-informal hidden-premise
  reasoning (Theoria 90.6 vs 62.5)? Untested here — needs a harder-to-ground informal-NL regime, a multi-day
  effort, not a quick probe.
- Forward door for the poison work: **mint-cost / attestable provenance** (signed/C2PA source credentials or
  earned-and-verified standing) — the only direction that isn't Douceur-blocked.

## Operational notes
- **ANTHROPIC_API_KEY is OUT OF CREDITS** (400 "credit balance too low") — our independent Claude anchor for
  flagship audits is dry; top up before relying on it.
- Ollama: `/api/embed` returns UNIT-normalized vectors, `/api/embeddings` returns RAW (norm ~20). Matters for
  any magnitude-based probe.
- kimi-k2.7 is not pulled; kimi-k2.6:cloud is available (different family, good cross-validation reasoner).
- Product roadmap (internal): `agora_output/strategy/20260703_library-drain-product-upgrade-roadmap.md`.

## Discipline learned this session (now standing)
- Before declaring a result KILLED/negative, re-test cross-family (add kimi) + Claude itself — a refutation
  deserves the same rigor as a confirmation.
- Control for the resource confound (compute/tokens/a simpler proxy) before crediting any cognitive method.
- On GitHub, Claude posts approved replies; on Reddit, the owner posts.

## Suggested next
1. Publish the resource-confound through-line (full gate) — best real artifact.
2. Prepare the July-6 joint-report verification pass.
3. Fresh breakthrough hunt in a NEW vein (the decomposition/poison veins are dry) — or the informal-hidden-
   premise regime if we want a multi-day serious attack.
