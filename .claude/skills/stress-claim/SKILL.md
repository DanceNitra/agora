---
name: stress-claim
description: Adversarially red-team OUR OWN claim/finding/draft BEFORE we publish or build on it — not the citations (that's verify-claims), but the ARGUMENT and framing. Use before shipping any Crucible verdict, flagship claim, hypothesis, or post, and whenever the owner says "red-team this", "stress-test the claim", "is this groundbreaking or textbook?", "would this survive a sharp critic?", or "are we overclaiming?". Runs a skeptic-led multi-lens panel (prior-art, strongest counter, weakest link, the missing 6th lens, textbook/overclaim check) and returns a verdict (PUBLISH / REFRAME / KILL) with the specific fixes. This is the systematized version of the audit that killed 5 of 6 candidates in the breakthrough scan and caught the nudging confound — it is meant to find reasons we are WRONG, before someone else does.
argument-hint: "[the claim in one sentence, or a path to the draft]"
---

# Stress-Claim — adversarially red-team our own claim before we ship it

## What this does

Takes ONE of our claims (a Crucible verdict, a flagship thesis, a hypothesis, a post draft) and attacks it
the way a hostile expert would, *before* we publish or build on it. Where [`verify-claims`](../verify-claims/SKILL.md)
checks whether the cited **facts** are true, this checks whether the **argument** holds: is it actually
novel or a textbook re-derivation, does it overclaim past the evidence, what is the strongest counter, and
what is the blind spot no lens addressed. It returns a blunt verdict — **PUBLISH / REFRAME / KILL** — with
the exact fixes. The goal is to find why we're wrong before a sharp audience does (the breakthrough scan
killed 5/6 candidates this way; the nudging/G2G confounds were caught this way).

Self-contained: built-in `Agent` (general-purpose), `WebSearch`/`WebFetch`. No external services. ~5-7 agents.

## When to use (before, not after)

Run it BEFORE: recording a Crucible REPRODUCED/FAILED verdict, shipping a flagship/canon claim, opening a
gated outreach that asserts a finding, or committing to build on a result. Pairs with `verify-claims`
(facts) — run both before any flagship publish; this one is the argument/credibility half.

## Process

### 1. State the claim in one sentence + its evidence
Write the claim as a single falsifiable sentence, and list the evidence behind it (Lab id / measured
numbers / cited prior art). If given a draft, extract the load-bearing claim and its support.

### 2. Fan out the red-team panel (parallel, one message, ~5 agents)
Spawn `general-purpose` agents, each a distinct adversarial lens. Substitute `{CLAIM}` + `{EVIDENCE}`:

- **PRIOR-ART HUNTER** — `Find where {CLAIM} (evidence: {EVIDENCE}) has ALREADY been established. Web-search for the named result, the mechanism, and the closest published work (papers, textbooks, prior debunks). Is this a textbook re-derivation or genuinely new? Name the specific prior source(s) + URL that pre-empt it, or state "no close prior art found" with what you searched. Rule: if a known result already says this, it's textbook. Under 250 words.`
- **STEELMAN SKEPTIC** — `Build the STRONGEST case that {CLAIM} is WRONG or trivial (evidence: {EVIDENCE}). Attack the mechanism, the inference, the generalization. What would a hostile domain expert say first? What does the claim conveniently ignore? Give the single most likely way it falls apart + a concrete source/argument. Under 250 words.`
- **METHOD / CONFOUND AUDITOR** — `Audit the METHOD behind {CLAIM} (evidence: {EVIDENCE}). Is the metric measuring what it claims? Is the baseline strong or weak? Is there a confound, selection effect, overfit, or metric-mismatch that would reproduce the result without the claimed mechanism? Is the falsifier real (can it actually fail) or a demonstration? Name the sharpest methodological hole. Under 250 words.`
- **OVERCLAIM / FRAMING CHECK** — `Does {CLAIM} overclaim past its evidence ({EVIDENCE})? Flag: universal claims from one operating point, preprint magnitudes stated as fact, vendor/weak-baseline numbers, "first/nobody/proves" language, a model presented as a measurement. Rewrite the headline to the strongest version the evidence ACTUALLY supports. Under 250 words.`
- **BLIND-SPOT / 6TH LENS** — `What did the claim and its framing NOT consider about {CLAIM}? Name the perspective, regime, population, time-horizon, or failure mode that's missing and could flip the conclusion. This becomes the frontier question. Under 250 words.`

### 3. Adjudicate (inline)
- Did the prior-art hunter find a source that already establishes it? → likely textbook.
- Did the method auditor find a confound that reproduces it without the mechanism? → likely artifact / needs the confound ruled out.
- Did the overclaim check have to weaken the headline a lot? → reframe.
- Score each lens's hit 0-3 (how damaging). Sum + judge.

### 4. Verdict
- **PUBLISH** — survives all lenses; cite the prior art it builds on; ship the honestly-scoped headline.
- **REFRAME** — the core holds but the headline overclaims or a caveat is missing; ship the rewritten claim + the added scope/falsifier, not the original.
- **KILL** — textbook re-derivation with no fresh receipt, OR a confound reproduces it, OR the falsifier can't fail. Record it as an honest dead-end; do not publish.

Report: the verdict, the single most damaging finding, the rewritten claim (if REFRAME), the prior art to
credit, and the new frontier question (from the blind-spot lens).

## Guardrails
- **Default to skeptic.** The win is catching our own error, not defending the claim. A KILL caught here is a success, not a loss.
- **Textbook bar (Agora's RAISED BAR):** re-deriving a known result is a KILL unless we add a genuinely new runnable receipt; cite the prior art either way.
- **No-overclaim:** "the evidence can't separate X from the artifact" beats "X is false"; one operating point is never "the" effect; a model is not a measurement.
- **Severe-test rule:** if the falsifier can't actually fail, it's a demonstration, not a test → REFRAME or KILL.
- This finds reasons to NOT ship; `verify-claims` then checks the facts of what survives. Run both before a flagship.

## Related
verify-claims (facts half) · storm-research (external multi-lens briefing) · the breakthrough-scan +
artifact-debunk patterns. Enforces: no-overclaim-cite-prior-art-strong-baseline · capstone-prior-art-lesson
· flagship-publish-credibility-audit · build-until-groundbreaking (raised bar).
