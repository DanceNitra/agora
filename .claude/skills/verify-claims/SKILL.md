---
name: verify-claims
description: Adversarially verify every factual claim and cited number in a piece of writing against its PRIMARY source before it goes public. Use BEFORE publishing any Crucible entry, post (render_post / render_crucible), or gated outreach reply/press — anything with a number, a named study/paper, a statistic, a quote, a dollar figure, or a date. Also use when the owner says "verify this", "check the claims", "is this 100%", "fact-check before we post", or before any `approve` of an outreach/press action. Returns a verification banner (N checked / X false / Y corrected / Z demoted), per-claim verdicts, and a claim-safety guide (assert / caveat / avoid), then applies the corrections.
argument-hint: "[path to a post .md / draft file, or paste the text]"
---

# Verify Claims — adversarial pre-publish fact-check

## What this does

Takes a draft (a post `.md`, a Crucible note, an outreach reply, pasted text) and, before it goes public,
**independently verifies every checkable claim against its PRIMARY source** — not a blog summary, the
actual paper/dataset/filing. It returns truthful verdicts (CONFIRMED / PARTIALLY CONFIRMED / UNVERIFIED /
FALSE), the exact corrections, a verification banner, and a claim-safety guide, then patches the draft.
This is the operational form of Agora's hard rule **"verify measured numbers vs the source before any
public citation"** (we once posted an unreproduced "+144%"; never again). It is the same adversarial pass
that, run inside storm-research, caught a misattributed arXiv ID, a 1,692→1,689 sample-size error, and a
fragile vendor stat — all *before* publish.

Self-contained: built-in `Agent` (general-purpose), `WebSearch`/`WebFetch`, `Read`/`Edit`. No external services.

## When to use (hard gate)

Run this and pass it BEFORE: rendering/publishing any post, recording a public Crucible entry, posting a
gated outreach reply or press piece, or approving any outward action that cites a number or source. A piece
that has not passed this is not ready to publish.

## Process

### 1. Extract the checkable claims
Read the target. Pull EVERY independently-checkable assertion:
- each cited number / statistic / effect size / percentage / dollar figure / date / sample size,
- each named study / paper / author / venue / arXiv-or-DOI id,
- each direct quote or "X said/found Y",
- each claim of priority ("first to…", "nobody has…").
List them. Our OWN measured numbers count too — re-check them against `server/.lab.json` / the lab script /
re-run, not against a vault note (a number in a note is NOT verified).

### 2. Cluster (group related claims so one verifier handles a coherent set; ~4-6 clusters).

### 3. Fan out independent verifiers (parallel, one per cluster, in a single message)
Spawn `general-purpose` agents. Each prompt:

`Independently verify a citation against its PRIMARY source. Be skeptical; do NOT trust secondary blog
summaries. CLAIM(S): {claim + cited figure + named source}. Find the actual primary source (paper/dataset/
official filing). Confirm or correct: exact title/authors/venue/year/URL, the real figure/effect size as
published, the sample/method and any author-stated limits, and peer-review status (published vs preprint vs
commercial/vendor report). For any contested claim, find the strongest credible counter-source. Return:
VERDICT = CONFIRMED / PARTIALLY CONFIRMED (list corrections) / UNVERIFIED / FALSE, then the corrected
one-line citation, then 2-4 bullets of specifics with the primary URL. Under 280 words.`

For our own Lab numbers, the "verifier" is a re-read of `server/.lab.json` / re-running the lab script —
confirm the published number matches what the code actually measured.

### 4. Compile the verdicts
- **Verification banner:** `N/N checked · X FALSE · Y corrected · Z demoted`.
- **Per-claim table:** verdict + the corrected fact + primary URL.
- **Claim-safety guide:** *Assert* (CONFIRMED, high-reliability) / *Caveat* (PARTIALLY CONFIRMED, preprint,
  single survey, context-dependent, snapshot-in-time) / *Avoid* (UNVERIFIED, FALSE, vendor-on-trivial-task).
- Reliability ranking (source hierarchy): peer-reviewed causal > official data > single commissioned/vendor
  survey > analogy > preprint.

### 5. Apply corrections to the draft (Edit)
- Fix every wrong figure, title, id, date, attribution.
- **Demote** preprints / commercial reports / contested / time-snapshot claims into a caveat or a "contested
  signal" note; never present them at full strength.
- Re-attribute single-survey/vendor stats honestly and flag the population/task they actually measured.
- Add the verification banner + per-citation status where the format supports it (Crucible, posts).
- **Anything FALSE or UNVERIFIED: cut it or demote it — never paper over it.**

### 6. Verdict to the user
Report the banner, the must-fix list, and the claim-safety summary (what is now safe to assert vs avoid).
If nothing is FALSE/UNVERIFIED after corrections → cleared to publish. Otherwise → blocked, with the fixes.

## Guardrails
- **Primary source only.** A blog/press/secondary summary is a lead, not a verification.
- **An unverifiable number is cut or demoted, never shipped.** A wrong stat that ranks is worse than no stat.
- **Our own numbers are not exempt** — re-check vs the source lab; a vault-note number is unverified.
- **The banner must be truthful** (don't pad "X corrected" to look diligent, don't hide a FALSE).
- **No-overclaim partner:** verification also catches framing overreach (vendor/weak-baseline numbers,
  preprint magnitudes, "first/nobody" priority claims, metric mismatches). Flag those, not just wrong digits.
- Scale to the piece: a 2-number outreach reply needs 1-2 verifiers; a flagship post needs 4-6.

## Related
Agora rules this enforces: verify-before-citing-publicly · no-overclaim-cite-prior-art-strong-baseline ·
flagship-publish-credibility-audit. Pairs with `storm-research` (which embeds this as its Phase 4) and the
Crucible publish flow (`render_crucible.py` / `render_post.py`).
