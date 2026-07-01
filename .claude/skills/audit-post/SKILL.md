# Audit-Post — the ONE correct, unskippable procedure for auditing a published post

## What this is

The end-to-end procedure for auditing one already-published post to a scientific-organization standard.
It chains the adversarial skills and — critically — **re-runs the auditor on the CORRECTED post to confirm
it now passes clean** before committing. We are a scientific organization; we do not ship missteps. Run
EVERY step, in order, for EVERY post. No light/inline version. Fewer posts done FULLY > more done shallow.

Defined 2026-06-29 after the owner caught two failures: (1) shortening the audit to a single citation
verifier + inline reasoning (missed a "Bayesian" mislabel, a strawman baseline, a wrong-estimand, and a
"textbook dressed as our law" overclaim across posts #7–#10); (2) dropping the re-audit-after-fix step — I
fixed and committed WITHOUT re-running the auditor on the corrected post to confirm the fix is clean.

**Updated 2026-07-01** after a THIRD failure: audits #16–#19 all ran stress-claim + verify-claims but
**never ran storm-research at all**, because this file — written 2026-06-29 — predates the owner's
2026-07-01 PERMANENT standing gate ("VALIDATE → STORM → AUDIT → VERIFY, storm is dominant, never skip,
applies to everything not just flagship posts"). The gate overrides every skill file by design, but relying
on remembering an overriding rule from a *different* document is exactly the failure mode that gate exists
to prevent. STORM is now Step 3 below, hard-coded into the numbered procedure itself — not something to
recall from memory. If a future owner rule changes the required order again, **update this file itself**,
don't leave the gap for the model to bridge silently.

## The procedure (10 steps, none optional, in this order)

### 0. Select + read
Open `agora_output/publish_audit_tracker.md`, take the next post. Read the FULL post — EN and SK bodies,
`<title>`/meta/OG/Twitter, the JSON-LD (Article + FAQPage), the footer. Note render type (src `.md` →
edit src + re-render; render_piece → edit HTML directly, and remember the FAQ exists TWICE: visible + schema).

### 1. State the load-bearing claim(s) + evidence
Write each claim as one falsifiable sentence + its support (Lab id / measured numbers / cited prior art).

### 2. VALIDATE — re-run OUR Lab numbers from source
Find and RUN the lab/probe script behind every measured number. A number in the post or vault is NOT
verified. Confirm each published figure matches the re-run. If a script is missing, that itself is a
finding — build an independent from-scratch re-derivation and disclose it as such (see #16/#18/#19).

### 3. STORM — /storm-research on the post's core claim  ← MANDATORY, run this before stress-claim
Run the full `storm-research` skill (5 expert lenses + contradiction map + its own Phase-4 verification)
on the post's central claim/topic. This is NOT optional and NOT interchangeable with stress-claim's
prior-art lens — storm is a wider, independently-sourced multi-perspective briefing; stress-claim is a
narrower adversarial red-team of THIS specific draft. Both run, storm first. Skipping this step is the
exact failure this update exists to close — do not skip it because stress-claim's prior-art hunter
"already covers prior art"; it doesn't cover the same ground (practitioner/economist/historian lenses,
the contradiction map, its own independent verification pass).

### 4. AUDIT — /stress-claim, full 5-lens adversarial panel, FIVE SEPARATE AGENTS
PRIOR-ART HUNTER · STEELMAN SKEPTIC · METHOD/CONFOUND AUDITOR · OVERCLAIM/FRAMING CHECK · BLIND-SPOT 6TH LENS.
All five run as distinct agent calls in the same wave. **Do not fold the method/confound auditor into a
different agent** (e.g. an independent-re-derivation agent) and count it as covered — that agent has a
different brief (build and report a re-derivation) and will not adversarially audit the post's argument
the way a dedicated method auditor does. If a re-derivation agent also runs this cycle, it is IN ADDITION
to, not a substitute for, the five lenses. Adjudicate → verdict PUBLISH / REFRAME / KILL. Actually fan out
the agents; never an inline "I considered prior art".

### 5. VERIFY — /verify-claims, every external citation vs its PRIMARY source
Extract every checkable claim (numbers, papers, IDs, quotes, priority claims). Fan out independent
verifiers vs primary sources (not blog summaries). Produce the banner (N/N checked · X FALSE · Y corrected ·
Z demoted). Fix/demote anything FALSE or UNVERIFIED.

### 6. Apply ALL fixes — BILINGUAL + SEO, at parity
Apply every correction in BOTH EN and SK (body, FAQ visible AND the JSON-LD FAQPage copy, footer prior-art).
Never EN-only. Run the /seo Mode-A check (keyword in title near front + leads with result; meta description;
≥1 list + ≥1 table; answer-first; FAQ + valid FAQPage schema; ≥3 internal links; Article/Org/FAQPage JSON-LD;
bump `dateModified`). If severe-test applies and a claim was only asserted, RUN the experiment to substantiate
or kill it (don't just hedge). Re-run `tools/render_sitemap.py` too — a bumped `dateModified` in-page with a
stale `sitemap.xml` lastmod is a real, previously-caught bug (audit #19).

### 7. RE-AUDIT THE CORRECTED POST → CONFIRM CLEAN  ← the step that gets skipped; never skip it
After the fixes, run the auditor AGAIN on the corrected version: re-run /verify-claims on every number/citation
you touched, AND a focused adversarial confirmation (spawn ≥2 skeptics: "attack this CORRECTED post — does it
still overclaim, miss prior art, or state a number it can't back? did the edits introduce any NEW error or an
EN/SK mismatch?"). If anything survives → back to step 6 and repeat. The audit is NOT done until the corrected
post passes the auditor clean.

### 8. Capture NEW findings
The panel produces real research leads (6th-lens frontier questions + measured side-results). Append them to
`agora_output/audit_new_findings.md` so they feed the flywheel — the audit is generative, not only defensive.

### 9. Verify HTML valid (balanced tags), leak-scan the diff, anon commit
(`agora-builder@users.noreply.github.com`), push; re-render if src-based. Update the tracker row (status,
verdict, commit). Force-add any new lab script (lab/ is gitignored) so "we measured it" links to runnable code.

### 10. Report the verdict
Banner + verdict (PUBLISH/REFRAME/KILL) + the single most damaging finding + what was fixed + the captured
frontier question + commit hash. Explicitly confirm in the report that STORM ran (name the storm-report file
if one was saved) — don't just imply it.

## Hard rules
- Public posts are GATED outward content, but FIXING our own already-public post to be MORE honest is
  product maintenance the audit authorizes (no new outward claim). A brand-new public CLAIM still needs the
  Slovak briefing + owner approval.
- KILL is a success, not a loss. A textbook re-derivation with a rigged baseline and no fresh receipt is a KILL.
- **STORM IS NOT OPTIONAL.** If you catch yourself about to skip step 3 because "the topic seems simple" or
  "stress-claim's prior-art lens is probably enough" — that is the exact rationalization that caused the
  2026-07-01 failure. Run it anyway.
- Enforces: [[audit-publish-full-procedure-never-shorten]] · [[validate-audit-verify-gate]] ·
  no-overclaim-cite-prior-art-strong-baseline · flagship-publish-credibility-audit ·
  bilingual-en-sk-everything · seo-program-setup.
