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

**Updated again 2026-07-01, SAME DAY** after a FOURTH failure, caught within an hour of the third: the
"run the /seo Mode-A check" instruction was a clause buried inside a bigger step (old step 6, mixed in with
bilingual-fix instructions), and in practice it was never actually executed as a distinct checklist pass on
audit #19 — I made ad-hoc meta/JSON-LD/internal-link edits without running the LLM-summary self-test, without
checking the Three Kings against the char-length rules, and without requesting re-indexing. Writing a step
into a paragraph is not the same as writing it as a step. **SEO validation is now its own numbered step
(7), with the specific /seo Mode-A checklist items spelled out inline** so there's no clause to skim past.
Pattern to notice going forward: if a "run X" instruction is a sub-clause of a different step instead of its
own step, that's the shape of thing that gets silently skipped — split it out.

## The procedure (11 steps, none optional, in this order)

### 0. Select + read
Open `agora_output/publish_audit_tracker.md`, take the next post. Read the FULL post — EN and SK bodies,
`<title>`/meta/OG/Twitter, the JSON-LD (Article + FAQPage), the footer. Note render type (src `.md` →
edit src + re-render; render_piece → edit HTML directly, and remember the FAQ exists TWICE: visible + schema).

### 1. State the load-bearing claim(s) + evidence
Write each claim as one falsifiable sentence + its support (Lab id / measured numbers / cited prior art).

### 2. VALIDATE — re-run OUR Lab numbers from source, and make the artifact PUBLIC + LINKED
Find and RUN the lab/probe script behind every measured number. A number in the post or vault is NOT
verified. Confirm each published figure matches the re-run. If a script is missing, that itself is a
finding — build an independent from-scratch re-derivation and disclose it as such (see #16/#18/#19).
**A private re-derivation is NOT enough (standing-gate requirement, added audit #20):** every published
headline number must resolve to a runnable artifact a reader can OPEN. `agora_output/lab/` is gitignored,
so a script there cannot be linked — **promote the re-derivation to a PUBLIC tracked path (`research/probes/`),
make it self-contained (no local paths / secrets / PII), have it print every number the post cites, and add
an `<a href>` from the post body (EN + SK) to the file in the public repo** (`github.com/DanceNitra/agora/blob/main/research/probes/<name>.py`).
A post that carries a headline figure with no linked runnable probe is a NEEDS-FIX, not a PUBLISH — this
is exactly the gap the re-audit skeptic caught on #20. Consolidate one probe that reproduces the whole
number set (naive result + every correction + the sensitivity sweep), not a scatter of throwaway scripts.

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

### 6. Apply ALL fixes — BILINGUAL, at parity
Apply every correction in BOTH EN and SK (body, FAQ visible AND the JSON-LD FAQPage copy, footer prior-art).
Never EN-only. If severe-test applies and a claim was only asserted, RUN the experiment to substantiate or
kill it (don't just hedge).

### 7. SEO — run the actual /seo Mode-A checklist, as a checklist  ← its own step; do not fold into step 6
Go through `.claude/skills/seo/SKILL.md` Mode A item by item and CONFIRM each, don't just eyeball it:
- **Three Kings**: `<title>` has the keyword near the front, ≤~60 chars, leads with the measured result;
  H1 matches; first ~40 words state the direct answer.
- **Meta description**: 1–2 sentences, keyword present, states the result, not truncated (check char count,
  don't just read it).
- **≥1 list + ≥1 table**, answer-first structure, FAQ block present and its JSON-LD FAQPage matches the
  visible FAQ verbatim.
- **≥3 internal links** to related Agora posts; outbound links to the primary sources cited.
- **Schema**: Article/Organization/FAQPage JSON-LD all valid (`json.loads` it, don't assume); `dateModified`
  bumped to today.
- **LLM-summary self-test (a real GATE, run it)**: paste the finished post into the local strong model and
  ask it to summarize + list key claims with numbers. If the summary mangles or misses a key result, rewrite
  until it doesn't — "if our own strong model can't extract the finding cleanly, neither will ChatGPT."
- **`tools/render_sitemap.py`** re-run — a bumped `dateModified` in-page with a stale `sitemap.xml` lastmod
  is a real, previously-caught bug (audit #19). Request re-indexing in GSC if credentials are available.
Do not consider this step done because individual fixes were made in step 6 — actually run through this
list and check each item off; that's the difference between the instruction existing and it being executed
(audit #19 made the edits but skipped running this checklist, caught by the owner same-day).

### 8. RE-AUDIT THE CORRECTED POST → CONFIRM CLEAN  ← the step that gets skipped; never skip it
After the fixes, run the auditor AGAIN on the corrected version: re-run /verify-claims on every number/citation
you touched, AND a focused adversarial confirmation (spawn ≥2 skeptics: "attack this CORRECTED post — does it
still overclaim, miss prior art, or state a number it can't back? did the edits introduce any NEW error or an
EN/SK mismatch?"). If anything survives → back to step 6 and repeat. The audit is NOT done until the corrected
post passes the auditor clean.

### 9. Capture NEW findings
The panel produces real research leads (6th-lens frontier questions + measured side-results). Append them to
`agora_output/audit_new_findings.md` so they feed the flywheel — the audit is generative, not only defensive.

### 10. Verify HTML valid (balanced tags), leak-scan the diff, anon commit
(`agora-builder@users.noreply.github.com`), push; re-render if src-based. Update the tracker row (status,
verdict, commit). Force-add any new lab script (lab/ is gitignored) so "we measured it" links to runnable code.

### 11. Report the verdict
Banner + verdict (PUBLISH/REFRAME/KILL) + the single most damaging finding + what was fixed + the captured
frontier question + commit hash. Explicitly confirm in the report that STORM ran (name the storm-report file
if one was saved) AND that the SEO checklist (step 7) was run item-by-item — don't just imply either.

## Hard rules
- Public posts are GATED outward content, but FIXING our own already-public post to be MORE honest is
  product maintenance the audit authorizes (no new outward claim). A brand-new public CLAIM still needs the
  Slovak briefing + owner approval.
- KILL is a success, not a loss. A textbook re-derivation with a rigged baseline and no fresh receipt is a KILL.
- **STORM IS NOT OPTIONAL.** If you catch yourself about to skip step 3 because "the topic seems simple" or
  "stress-claim's prior-art lens is probably enough" — that is the exact rationalization that caused the
  2026-07-01 failure. Run it anyway.
- **SEO VALIDATION IS A CHECKLIST, NOT A VIBE.** Making meta/title/link edits during step 6 is not the same
  as running step 7's checklist. Go through the actual list and confirm each item; don't consider it done
  because individual fixes happened to touch the same fields.
- Enforces: [[audit-publish-full-procedure-never-shorten]] · [[validate-audit-verify-gate]] ·
  no-overclaim-cite-prior-art-strong-baseline · flagship-publish-credibility-audit ·
  bilingual-en-sk-everything · seo-program-setup.
