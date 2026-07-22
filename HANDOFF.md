# Agora — Session Handoff

> **LIVE COLLABORATION — DO NOT FORGET AFTER A RESET (owner flagged 2026-07-18):** Marat Sultanov (GitHub
> `maratsultanov2`, project **TAT = Tree Angle Tap**; `TAT-ONE-TAP` = LLM memory via hash fingerprint) + Li
> Guanghao (GitHub `luoxuejian000`) + Qingkong (`qingkong66`). The CURRENT EDRN "Menu-2" paper (1D Hubbard
> boundary-CFT / Kane-Fisher / cross-sector) is **NOT yet published** — it awaits Guanghao's 3 revisions +
> Marat's TAT appendix (DELIVERED, comment #82) + Qingkong's structural OK, **THEN WE (Drahoš) are the final
> technical sign-off + submitter** (SciPost Physics Core + a fresh Zenodo DOI; a PRIOR paper had DOI
> 10.5281/zenodo.21393316 — don't conflate). Marat's TAT (Tree Angle Tap; TAT-ONE-TAP = LLM memory via hash
> fingerprint) bridges EDRN structural methods → inspeximus integrity. FULL current state (who owes what) + the whole
> 83-comment thread digest: memory `marat-tat-edrn-collaboration-live`. Read the whole Issue #1, fetch data from
> GitHub yourself (public) — never via Gmail.

# Agora — Session Handoff (2026-07-20 · "test your own claim" day)

## 2026-07-22 (latest) — RAMR shipped the integrity metric via 3 gated releases; the gate caught 3 real defects

Track B. The owner's steer: "don't proliferate parallel benchmarks — build ON RAMR" ([[ramr-benchmark-published]]).
So INTEGRITY-CONDITIONED RECALL (does recall return the correct CURRENT value after supersession/revert/poison)
was folded INTO the public RAMR benchmark, over three gated public releases + one package patch. **Every public
push was owner-gated ("pushni to") and ran a 2-agent adversarial pre-pub audit first.**

**What shipped (all verified live):**
- **RAMR v0.4.2** (tag): renamed the vendored library `mnemo` → `inspeximus` across the repo, zero trace
  (`mnemo/mnemo.py` now 404s on the remote). Rename-only → numbers reproduce. Zenodo DOI …21495564.
- **RAMR v0.4.3** (tag): the INTEGRITY-CONDITIONED RECALL metric (`ramr_integrity_recall.py`, verify_numbers-backed,
  raw arrays) + re-vendored the core 0.6.10 → 1.29.0. Zenodo DOI **10.5281/zenodo.21496078** (concept
  …20818291 preserved). HF dataset `Danchi17/ramr` refreshed (card + CITATION at 0.4.3).
- **inspeximus 1.29.1** (PyPI): cleaned an internal path (`agora_output/lab/memops/keying_recall.py`) that a core
  docstring leaked — it was live in the published package. Verified gone from the installed wheel.

**The numbers (honest framing is the point):** revert = the unique win (inspeximus 1.00 vs cosine-recency 0.00,
naive 0.55 — recency has no revert op); supersession = a TIE with a fair recency baseline (both 1.00); poison =
a WARRANT-CHANNEL DEMONSTRATION, **not injection detection** (see below).

**The gate caught THREE real defects nobody would expect from "it's just a rename":**
1. A `pip install agora-inspeximus` line in the README that 404s (the package is `inspeximus`) — a broken
   install instruction every user would hit.
2. The internal-path leak in the re-vendored core — which was ALSO live in the published PyPI package (→ 1.29.1).
3. **The poison overclaim, caught AGAIN** (same class as [[adversarial-conflict-the-real-inspeximus-moat]]):
   the poison headline (warrant 1.00 vs 0.00) does NOT measure injection resistance — it measures obedience to a
   trust label the harness HANDS the truth (`credit(warrant="external")`) and withholds from the poison, using a
   warrant string the core's own docs call spoofable by the injecting attacker. REFRAMED, not killed (revert +
   the supersession-tie are clean). LESSON: any "inspeximus beats X on poison/conflict" via warrant/credit is a
   trust==truth tautology unless the attacker is denied the warrant channel too.

**Re-vendor validation (0.6.10 → 1.29.0):** all inspeximus harnesses re-run — verdicts hold, OUTCOME-LIFT drift
+0.000; two secondary numbers refreshed and disclosed (CROSS-SCOPE-LEAKAGE 0.82→0.80; breakeven boost arm ≤0.03,
cited +0.00 holds). Every Zenodo mint built a FRESH `git archive HEAD` zip (the tool hardcodes a pre-built zip —
the old one still had mnemo; verify mnemo-free + no internal-path before every upload). Full state:
[[ramr-integrity-conditioned-recall-metric]].

**Consolidation to ONE canonical home — DONE + VERIFIED (every link resolves, no 404):** RAMR is now the single
live home for the integrity benchmark; the two peripheral surfaces point at it.
- `agora/public/integrity/index.html` — repointed its three benchmark links from the standalone
  `agent-memory-integrity` repo to RAMR (repo + `integrity/` module + concept DOI); links-only, page design
  untouched; cited revert numbers (0.75 / 0.20 / 0.00) confirmed to match RAMR's METHODOLOGY.
- `github.com/DanceNitra/agent-memory-integrity` — was ALREADY archived (read-only) with a live "→ moved into
  RAMR" README (done 2026-07-19). I first mis-flagged it as "live, needs archiving" because I checked HTTP 200
  (archived repos also return 200) + last-push date, NOT `.archived`. LESSON: judge a repo's liveness with
  `gh api repos/X --jq .archived`, not the HTTP code.

**Then: shipped the Agent-Memory Integrity Leaderboard** (owner "poď na ten leaderboard") — the top
value/effort lever from the distribution map. LoCoMo/LongMemEval have NO leaderboard, so we host one and are
the REFEREE, not a contestant; deliberately on the INTEGRITY axis (revert/echo cross-system through a blind
judge), NOT generic recall (where we tie cosine and would just be a contestant). LIVE at
`dancenitra.github.io/agora/public/leaderboard/` (+ machine-readable `leaderboard.json`, `tools/render_leaderboard.py`,
Crucible pattern). revert: inspeximus 0.75 / mem0 0.20 / Graphiti 0.00 (capability gap); echo: all tie (led
with on purpose); poison deliberately NOT a cell (it'd be the warrant-channel overclaim). Numbers verified vs
RAMR canonical before publishing; linked from storefront index + integrity page + RAMR README; submissions via
RAMR `integrity/SUBMISSION.md`. Details: [[agent-memory-integrity-leaderboard]]. Then shipped an **HF Space** (static, free) at
`huggingface.co/spaces/Danchi17/agent-memory-integrity-leaderboard` — serves the rendered page + JSON, verified
via headless render. It's a COPY of `public/leaderboard/` (re-upload the 3 files on any update). NEXT (optional):
more systems (Zep/Letta/Cognee) through the same harness; cross-link the Space from the storefront.

**Still open (non-blocking):** distribution PRs from earlier today (LangGraph #5019, OpenAI #3906 gated on
adoption, awesome-mcp #10649, Haystack #554). Glama listing is stale (shows old name `agora-mnemo`) — our
`glama.json` maintainers marker is correct but Glama hasn't re-crawled; the claim/refresh is an owner web
action on glama.ai (no API), LOW PRIORITY cosmetic. Full RAMR state: [[ramr-integrity-conditioned-recall-metric]].

## 2026-07-22 (night, cont.) — two self-serve PRs landed; a real Haystack DocumentStore built (not faked)

Finished the two self-serve listings. The second one turned out NOT to be a listing task.

**awesome-mcp-servers [PR #10649](https://github.com/punkpeye/awesome-mcp-servers/pull/10649)** — one line in
Knowledge & Memory, title carries the `🤖🤖🤖` agent-fast-track tag their CONTRIBUTING asks for. The `uvx`
install command was run before submitting. Fork was 9175 commits stale; reset to upstream/main so the diff
is exactly one line.

**Haystack was NOT a listing — it needed a real integration first.** We had zero Haystack code; `mem0.md`
points at a real `mem0-haystack` package. Filing a catalog page for a non-existent adapter is exactly the
CrewAI #6277 / Aegis #1507 trap. So I BUILT `InspeximusDocumentStore` (inspeximus 1.29.0): implements
Haystack's `DocumentStore` protocol, drop-in for `InMemoryDocumentStore`, persistent, delete leaves disk
clean. Duplicate policies (SKIP/OVERWRITE/NONE/FAIL) captured EMPIRICALLY from the reference, not guessed;
filtering reuses Haystack's own `document_matches_filter`, so FilterRetriever + pipeline serialization work
unchanged. `haystack_audit.py` (7 scenarios x3 vs InMemoryDocumentStore + HAYSTACK_FALSIFY control) and 9
tests, in CI. Then [Haystack PR #554](https://github.com/deepset-ai/haystack-integrations/pull/554) — the
usage example was run against haystack-ai 3.0.0 + inspeximus 1.29.0 and produces the shown output. (Its
Vercel check "fails" = external-PR preview needs a maintainer to authorize; not a build error.)

**Registry automation hardened.** Now that the registry holds >1 version, two latent bugs surfaced and are
fixed: the idempotency check compared only the first (oldest) listed entry — would've hit the
duplicate-version 400 on the next release; and the post-publish verify read servers[0] (oldest) and printed
a misleading version. Both now check whether OUR version is among ALL listed, in
`packages/_registry_verify.py`. 1.29.0 is live in the registry, isLatest=True.

**Standing note for me:** I put a Python heredoc inside a YAML `run:` block AGAIN (3rd time this project);
the indentation breaks it. Rule: registry/CI Python goes in a `packages/_*.py` file, never inline heredoc.

## 2026-07-22 (night) — in the MCP registry; three doc-catalogs all answered "come back with users"; a real integrity bug fixed

Track B only. Continued the distribution push and hit a wall worth naming, plus found a genuine defect in
our own integrity layer while preparing a PR.

**LIVE: the official MCP registry.** `io.github.DanceNitra/inspeximus` 1.28.1, status active, package
`pypi inspeximus 1.28.1`. Published from CI via `mcp-publisher login github-oidc` — no human login, and it
re-runs on every release so the listing can't drift (it had: server.json was pinned at 1.24.4 while 1.28.0
shipped). The job is idempotent (asks the registry before publishing; the registry 400s a duplicate
version) and fetches registry state with curl, because urllib times out against that host on the runner AND
locally while curl and the Go publisher succeed. Glama/Smithery/PulseMCP all crawl this registry, so the
one publish should cascade.

**A REAL BUG, found by dogfooding before a PR (fixed, 1.28.1).** Constructing `Inspeximus` with
`receipt_key` but no `receipt_pubkey` signed every write receipt with `"pubkey": None`, so `verify_writes()`
reported "invalid signature" on records the store had just written itself — the integrity layer we sell was
crying tampering at its own output. Every existing receipts test passed BOTH halves (the documented happy
path), which is why it survived. Public key is now derived from the private one; a bad key is rejected at
construction, not thousands of writes later. Three regression tests, including the control that tamper
detection still fires on a real edit. Found only because I verified the claim instead of describing it.

**THE WALL (this is the strategic point). Three doc-catalogs now say the same thing:**
- OpenAI Agents SDK [PR #3906](https://github.com/openai/openai-agents-python/pull/3906) — OPEN, but
  maintainer `seratch`: *"It seems like the project is still pretty new, so we'd like to wait and see
  whether people start using it."*
- ADK docs — their own precedent (#1565 closed in 13h) is "don't file the same day you ship."
- Pydantic AI — rejected two memory packages last month as "brand new… not quite there yet."

The bottleneck is no longer *routes*, it is *adoption evidence*. Under the new name every download counter
resets to today (pypistats has no data yet; zep-cloud does 342k/mo for scale). Filing more gated catalog
PRs now just collects more "come back later" replies and can sour a first impression. **The next lever is
usage, not listings** — self-serve surfaces that don't gate (MCP registry: done; awesome-mcp-servers and
Haystack: still open, both self-serve), plus something that actually drives installs. Full route map with
OPEN/CLOSED verdicts + evidence: memory `distribution-routes-map-2026-07-21`.

**Sittng OPEN, no action needed from us:** LangGraph docs [#5019](https://github.com/langchain-ai/docs/pull/5019)
(20/20 green, in their queue), OpenAI [#3906](https://github.com/openai/openai-agents-python/pull/3906)
(labeled `documentation`, maintainer watching for adoption).

**NEXT (no owner action needed):** awesome-mcp-servers PR, Haystack integrations PR (both one file, no
maturity gate). Then stop listing and think about what drives real usage. Google CLA still only needed for
the ADK docs PR, which is deliberately deferred.

## 2026-07-21 (later) — distribution track: LangGraph docs PR filed, ADK shipped, and a market read I got wrong

Track B only (the memory product). Two integration ecosystems, both entered through their official routes.

**LangGraph — [PR #5019](https://github.com/langchain-ai/docs/pull/5019) is OPEN and green.** Adds a provider
page plus one row in the third-party checkpointer table and one card in `all_providers`. All 20 checks pass,
including their own Vale 3.9.6 (0 errors / 0 warnings / 0 suggestions — their `install-vale.sh` refuses to run
on Windows, so the pinned binary was fetched from their release and run directly rather than assumed).
Every code sample was executed against the released package and the outputs are the real ones. The PR
discloses AI assistance, per their contributing guidelines. Reviewer `@mdrxy` was asked in a comment —
GitHub refuses a review request from an external contributor (`does not have the correct permissions`),
so their bot's "please add the relevant reviewers" can only be honoured that way. Two labels applied by
their triage bot: `external`, `python`.

**Google ADK — `inspeximus 1.28.0` shipped (PyPI, verified from `site-packages` not the repo).** ADK ships
**no conformance suite** for `BaseMemoryService`, so "drop-in replacement for `InMemoryMemoryService`" had
been an unchecked claim since 0.7.4. `adk_audit.py` now checks it — eight scenarios against ADK's own
service, three repeats, `ADK_FALSIFY=1` as the control that must fail (it fails 7 checks). Writing the audit
caught two real defects:

- **Re-adding a session stored it twice.** ADK documents a session *"may be added multiple times during its
  lifetime"* and the runner does exactly that, so a long conversation was written once per turn. Ingestion is
  now idempotent per event; the seen-set rebuilds from the store, so it survives a restart.
- **`add_events_to_memory` was never implemented** — the incremental path raised `NotImplementedError`.

Also `from_uri()` + `register()`, so `adk web --memory_service_uri=inspeximus://memory.json` works with no
Python glue, and the `adk-inspeximus` wrapper distribution. CI gained an `adk-parity` job that ran green on a
clean Linux runner against the current `google-adk` release. Latent bug found in `release.yml` on the way:
the import check derived the module name by string surgery written for `langgraph.*` namespace packages and
would have produced the non-existent `adk.inspeximus`, failing the release of a package that was fine.

**Where I was wrong, on the record.** I told the owner the ADK ecosystem had no local persistent memory
service. That was a bad read — I looked only at what ships *inside* `google-adk` and generalized. There are
at least ten live third-party ones (`zep-adk`, `adk-redis`, `adk-milvus`, `adk-aerospike`,
`adk-database-memory`, `adk-perseus-vault-memory`, `hindsight-google-adk`, `kagent-adk`,
`google-adk-community`, `goodmem-adk`), all verified on PyPI. "Local and persistent" is therefore NOT the
differentiator; correction/erasure semantics are. Real remaining gap: **mem0 ships no ADK service** — its
docs tell users to write the class themselves.

**SHIPPED:** `inspeximus 1.28.0` and `adk-inspeximus 0.1.0` are both on PyPI (trusted publishing, attested;
the owner created the pending publisher and the first upload consumed it). Verified the way a user meets it:
a clean venv, `pip install adk-inspeximus`, which pulled `inspeximus 1.28.0` + `google-adk 2.5.0`, and
ingesting the same session twice returned **1** memory — the defect this release fixes, confirmed in the
shipped artifact rather than the working tree.

**NEXT / BLOCKED ON THE OWNER:**
1. **Google CLA** — owner agreed to sign under his own name. Not urgent: the `adk-docs` PR must NOT be filed
   the same day the package ships. Their PR #1565 was closed in 13 hours for exactly that, and the author
   conceded the point. Ship first, accumulate adoption, file later. Details: memory
   `adk-docs-open-but-maturity-gated`.

## 2026-07-21 — EDRN paper 2 PUBLISHED · rename decided · adoption measured at ~zero · dungeon's three silent failures

**Read this first.** Two tracks ran today and they are unrelated to each other — do not merge them:
**(A) the EDRN physics collaboration** (Li / Drahos / Sultanov, 1D Hubbard DMRG), and **(B) inspeximus**, our
own product, where a Reddit post's comment thread produced a new experiment. Nothing in (A) touches (B).

---

# TRACK A — EDRN physics

### A1. Paper 2 is OUT, and the standing header above is now stale

The "Menu-2" paper the header calls unpublished **is published**:
**https://doi.org/10.5281/zenodo.21473160** — *Systematic numerical study of the spin-gap prefactor in a
one-dimensional Mott insulator: defect response, boundary effect, and cross-sector conservation*, Li /
Drahos / Sultanov, CC-BY, open access.

It is a **NEW record**, deliberately not a version of 10.5281/zenodo.21393316. That DOI belongs to a
*different, earlier* paper which reports Prediction 1 as negated in its initial test and leaves the correct
test "pending". This paper IS that test. Linked as `isContinuedBy`. (An earlier plan to publish it as
"version 2" of the old record was wrong and was caught before it happened — it would have put two different
papers under one DOI.)

The sign-off comment is posted in the thread (issue comment 5033674061). **Nothing is open on the
collaborators' side.** Marat closed his two items (CERN data out of the paper, U=2 spin gap from our own
DMRG). Guanghao handed us the C decision, the LaTeX, and — back in July — *"the rest, I leave to you."*

**What earned the sign-off, all pushed to `github.com/DanceNitra/edrn-appendix-fix`:**

- **80 DMRG runs.** Every one of the ten defect-scan points at chi = 100/200/300/400 in both spin sectors,
  energies extrapolated linearly in the discarded weight, gaps rebuilt from extrapolated energies only.
  **Control first: our chi=100 reproduces their published A = 5.469862 as 5.469865** — six significant
  figures from independent code, without which nothing downstream is comparable. Result: the open chain was
  **already converged**; largest bias 1.0%, eight of ten points at 0.3% or less. Contrast the periodic ring,
  where the same check moved A from 0.47 to 3.19 — on a ring the wrap bond is long-range for an MPS.
- **The C normalization, settled from their own code rather than our judgement.**
  `game1_defect_scan.py:72` and `menu2_periodic.py:88` accumulate the MEAN of the two spin channels;
  `predict1_topology_spin.py` their SUM. That single `/ 2.0` is the entire apparent "48% drop": the open
  chain was reported as a SUM and the ring as a MEAN, so a ring with one *more* bond looked half as
  connected. Verified on data both sides already held — the scan at defect 1.0 IS the uniform L=40 chain,
  and 2 x 0.479442 = 0.958884 against that file's 0.9588847979.
- **A manuscript row with no data file behind it.** L=40, 0.8t (A = 4.3666) appeared in no committed CSV;
  the only record for that point anywhere reads `delta_s = 6.5e-9, A = 0.000000` — a run that failed to
  resolve the two sectors. Rather than ask where the number came from, it was recomputed independently:
  **A = 4.365966**, 0.014% away. The row was right all along; only its provenance was missing.
- Both table files regenerated in one convention, a new convergence appendix wired in, `paper_full.pdf`
  recompiled. Scripts and all 80 raw cells are public so any table can be re-derived without a new sweep.

### A2. The journal is the ONLY remaining route — arXiv is closed, permanently

**Do not raise arXiv again.** cond-mat requires an endorsement, none of the three authors has one, and the
owner has had to say this several times. Memory: `arxiv-excluded-journal-is-the-only-path`.

Verified mechanics for PRB: **`agora_output/dmrg/PRB_SUBMISSION_GUIDE.md`** — every requirement carries the
APS URL it came from. (APS returns 403 to the normal fetch tool; use a browser user-agent.)

Better than feared: **no submission fee, publishing behind the paywall is free**, Regular Article has no
length limit, a single PDF is all that is needed to submit, and our `revtex4-2` `prb` class is already right.

**The risk we created ourselves:** the Zenodo record is **CC-BY**, and APS requires gold open access
($2,910) for a CC-BY licence on an accepted manuscript, while the copyright transfer warrants the work is
"unpublished". No APS page addresses a CC-BY preprint posted *before* submission. **First action, before
anything else: one email to `prb@aps.org`** with the DOI, asking that, and whether "Independent Researcher"
is acceptable as a byline affiliation. Both unknowns fit in one paragraph.

**What the manuscript still needs:** not one `\section{}` exists — 21 bold inline labels stand in for them;
no Data Availability Statement (required by APS); no Author Contributions paragraph; ORCIDs for two of the
three authors (free, self-service at orcid.org/register — **not** an endorsement wall, the owner reasonably
feared it was another one); a native-English pass. And a decision on the collaboration-ethics material
("tool-rationality paradox", "honest silence", six numbered principles): sincere, the best thing about how
the paper was made, and a live desk-rejection risk at APS's first screening filter — which is **not
appealable**.

---

# TRACK B — inspeximus

### B1. The rename is DECIDED but NOT executed: `inspeximus`

Chosen after a four-lens scan plus registry verification. A medieval charter that recites an earlier charter
verbatim and attests it unaltered — the same act the product performs.

**Verified:** PyPI, npm, crates, the GitHub username, `inspeximus.com` and `.org` all free; **zero** GitHub
repos carry the name; TMview returns zero; the only occurrences anywhere are medieval-charter scholarship.
USPTO and EUIPO were searched by hand **with a `deepki` positive control that returned records in both**, so
those zeros are real zeros and not a broken search.

**The one live mark found:** EUTM 018905799, `inspex CYBERSECURITY PROFESSIONAL SERVICE`, figurative, Thai
owner, registered 2023, **class 42 including general software-development terms**. Assessed low-to-moderate:
different word, figurative rather than word mark, weak suggestive root, remote field of use. Not a blocker;
the owner explicitly rejected paying for a clearance opinion at this stage and was right that the downside
is a rename, which today costs nothing.

Killed along the way: **`kudurru`** (Spawning Inc. has used it for an AI tool since 2023 with WIRED and NPR
coverage — the exact Deepkit fact pattern) and **`speximus`** (it fails its own standard: the word appears
in no Latin text ever written, and a name that cannot survive its own verification standard is a bad name
for a verification tool).

**Why it has not shipped:** the plan bakes the name into install commands and framework catalogues, so the
rename must land *before* those, not after. Nothing else blocks it.

### B2. Adoption, measured properly for the first time: essentially zero

Via ClickHouse's public PyPI dataset (`sql-clickhouse.clickhouse.com`, user `demo`, database `pypi` — free,
no key, and it carries the `installer` field that pypistats lacks):

```
42,000 downloads / 30 days
  -> 2,334 are pip / uv / Nexus (anything resembling an install)
  -> the discriminator: Singapore pulled ALL 103 versions, Japan 101, China 90,
     Britain exactly 72 downloads across 72 versions
```

Nobody installs 103 versions of a library. **The honest statement is "no organic signal distinguishable from
automated traffic", with a defensible ceiling of about 16/day** — not "zero", which overstates what the data
supports. US traffic is largely our own CI; SK is the owner's own machine.

Two consequences: the rename is free (**there is no installed base to disrupt**), and we have a clean zero
baseline, which is rare — any movement after the distribution work will be unambiguous rather than arguable.

### B3. The plan we are working from

**`agora_output/IMPLEMENTATION_PLAN_2026-07-21.md`** — ten items in build order, each with an acceptance
test rather than an opinion. It front-loads findability because the bottleneck is not capability. Phase 0 is
`inspeximus install` (one command per IDE, and the place where the untested Codex-TOML claim finally gets tested)
then the `langchain-inspeximus` package and catalogue listings. Phase 1 reframes the README around **correction
and provenance** — asked for by 69 and 84 distinct projects — with **revert demoted to proof**, asked for by
10. Phase 2 is the one axis where we are honestly behind: ingest granularity, then re-measure.

### B4. IN FLIGHT — the noise-vs-contradiction experiment

This came out of a comment on our Reddit post about the MemOps nulls. The commenter said our "less evidence,
better answers" result (0.593 turn-level vs 0.442 session-level) is attention distraction / "lost in the
middle" (arXiv:2307.03172 — verified real, Liu, Lin, Hewitt, Paranjape, 2023). His explanation is plausible
but confounded: session chunks in this corpus do not merely contain more text, they contain **the superseded
values themselves**.

The experiment builds contexts directly instead of retrieving them: identical evidence, padded with either
**neutral** filler (turns from other scenarios) or **contradicting** filler (this scenario's turns carrying
superseded values), at matched character counts, split evenly around the evidence so position is held
constant. The only difference at each rung is whether the filler contradicts.

- Pre-registration, **predictions and a falsifier written before the run**:
  `agora_output/lab/memops/NOISE_VS_CONTRADICTION_PREREG.md`, including Amendment 1.
- Runner `noise_vs_contradiction.py` · analysis `noise_vs_contradiction_analysis.py` · construction audit
  `nvc_construction_audit.py`.
- **Resume is built in**: re-running with the same `--tag` skips work already scored. Progress:
  `grep "/316" agora_output/lab/memops/_nvc2.log | tail -1`.

**Amendment 1 matters.** The construction audit was written *during* the first run and failed two of three
checks: the "neutral" control carried the target scenario's own superseded values (this corpus reuses entity
strings — `Data Analyst`, `Unit 3B`, `Basenji`), and for two scenarios the "contradicting" filler contained
no contradiction. That run was discarded, ~440 cloud calls wasted, and the discarded raw file is kept as
`nvc_raw_INVALID_v1.json` so the correction is checkable. Note the bias direction: a contaminated control
would have *understated* the effect, not invented one.

**RESULT: KILLED, twice over. Do not resurrect it without reading both reasons.**

**Reason 1 — the finding is already published.** A prior-art sweep (arXiv only; ACL Anthology and
Scholar not checked) found the question is an occupied axis:
- **HoH** (arXiv:2503.04800, 2025) runs nearly this design: relevant-only / outdated-only / both, with a
  sweep over the number of neutral distractors. Its "harmful (-1)" score *is* our stale-value metric.
- **Yadav** (arXiv:2606.26511, 2026) already publishes the number we were about to measure: standard RAG
  serves superseded facts **15-40%** of the time.
- **MemOps itself** (arXiv:2607.12893) — the benchmark this lab is already built on — explicitly names
  "relying on stale values after a correction" as a distinct failure type.
- **Cuconasu et al.** (arXiv:2505.15561) further argues positional "lost in the middle" effects are
  marginal in realistic retrieval and content-based distraction dominates — which weakens the premise
  that volume was ever the natural null hypothesis.
The only residue: HoH does not *equalise token count* between its contradiction and no-contradiction
arms. That is a methods refinement, not a finding.

**Reason 2 — the design cannot support the claim anyway.** A hostile red-team of the construction found
three fatal problems, all verified against the actual data:
1. **`stale_value` is an UNREGISTERED endpoint.** The prereg names accuracy as the quantity, and the
   registered accuracy endpoint came back **null at every rung** — the fourth consecutive null, exactly
   as the falsifier anticipated. The analysis script had grown a `STALE-VALUE SEPARATION` block with its
   own decision rule, printing *above* the registered verdict. That is the precise failure mode
   pre-registration exists to prevent, and I wrote it.
2. **The separation is one scenario.** Ten of the seventeen stale events come from `A05_update` alone;
   leave-one-scenario-out kills the only significant rung three different ways and flips the 12k sign.
   And the dose-response runs backwards — the effect is largest at 2k and shrinks as contradiction
   triples, which is not a mechanism.
3. **Arm C is confounded with repetition and topicality.** `pad()` cycles a 4-14 turn pool without
   reshuffling, so at 12k **55% of arm C's filler lines are verbatim repeats** and the stale string
   appears ~33 times, versus 27 distinct off-topic turns in arm B. The manipulation is "one string
   repeated 33 times vs diverse off-topic text", not "contradiction present vs absent". On top of that,
   **74 of 82 probes carry a superseded value inside the shared evidence block itself**, so arm B was
   never a contradiction-free control.

**What would be needed to ask the question properly** (recorded, not scheduled): arm D — filler from the
*same* scenario with no stale value (topicality held constant); arm E — neutral filler subsampled and
cycled on C's exact repeat schedule (repetition held constant); reshuffle per cycle; drop any
(scenario, rung) whose pool cannot fill the rung without repeats, which removes the 12k rung for 7 of 10
scenarios. Plus a fresh prereg naming one endpoint and one rung, a sign-flip permutation test instead of
a 10-cluster bootstrap, blind hand-labelling of ~40 arm-C answers, and a second judge.

**The honest position: the registered endpoint returned the fourth null, and the axis is already
occupied by published work.** ~950 cloud calls total, 412 probes scored and kept in `nvc_raw_v2.json`.
Nothing was written or sent from it. The full red-team and prior-art findings are in this session's
transcript; the two most useful artefacts to keep are the construction audit pattern and the
`call()` token-floor guard.

### B4b. THE FINDING OF THE DAY — supersession retires a RECORD, not a VALUE

After the experiment was killed, the owner's instruction was: measure it, verify it three times, and do
whatever it takes to make inspeximus dominate rather than lose. That produced the real result.

**Step 1 — the cross-vendor stale-fact rate, from runs already paid for (zero new cloud calls).** The
judge had recorded a `stale_value` flag on every probe all along; we had simply been reading accuracy.
`stale_rate_verify3.py` derives it three independent ways (the pilot's own summary files, a recomputation
from raw rows, and a per-scenario breakdown) and all three agree:

```
inspeximus    0.2105  n=38      <- tied with mem0, WORSE than a keep-everything store
mem0     0.2105  n=38
naive    0.1250  n=40
session  0.1143  n=35
none     0.0000  n=29      (trivial: no context, and 5.8% accuracy)
```

A first attempt at this number gave 0.194 and was wrong: it pooled `pilot_raw_k150` (budget-matched)
with `pilot_raw_cheap` (the earlier unmatched run), both of which contain a `inspeximus` arm. The published
accuracy table identifies the authoritative file per arm. The three-way check also surfaced an apparent
0.11 "mismatch" on mem0 that was only a **denominator difference** — `summarize()` grades stale_value
on `update` scenarios only, while the naive recomputation used every graded probe. State the
denominator or the number means nothing.

**Step 2 — why.** Across ten scenarios the store holds **33,186 records, 1,728 keyed (5.2%), 108
superseded (0.33%)**. The correction layer can only suppress what it has keyed, so on 95% of the corpus
inspeximus IS the keep-everything store it ties with.

**Step 3 — the free harness.** `keying_recall.py` measures, with no model involved and ground truth
taken from the corpus's own `chain_id`/`old_value`/`new_value`:

```
                    baseline   candidate+fallback   candidate alone
KEYING RECALL         0.203          0.211              0.034
CHAIN BINDING         0.083          0.083              0.333   <- 4x better
SUPERSESSION          0.006          0.024              0.018
LEAK RATE             0.111          0.111              0.111   <- never moved
```

`extractor_candidate.py` keys the head noun of a possessed attribute (`my <...> title <...> was X` ->
`my::title`) and lifted CHAIN BINDING four-fold. **The leak rate did not move at all.**

**Step 4 — the finding.** `Junior Data Analyst` appears in **fifteen records** of one scenario: the user
states it, the assistant echoes it, a summary repeats it, an HR template quotes it. Supersession retires
the ONE record that carried a key; the other fourteen stay `active` and lexical recall returns them.

**The defect is not the extractor. Supersession retires a RECORD, not a VALUE.** In structured data
those are the same thing. In conversational prose one value is smeared across a dozen sentences and
retiring one of them accomplishes nothing. This explains all four nulls at once, and explains why
`integrity-conditioned-recall` showed revert 1.0 vs 0.0 — that test used ONE keyed record, the case
that works.

**The fix is a new mechanism: value-level suppression at READ time.** When the current value for
`my::title` is `Senior Data Analyst`, recall should filter records containing that key's superseded
values, keyed or not. Deterministic, no LLM, and it is what the product already claims to do.

**It costs nothing to try.** `keying_recall.py` is the harness, LEAK RATE is the number to drive down,
and nothing should reach the expensive pilot until it moves there. Memory:
`supersession-retires-a-record-not-a-value`.

### B4c. CLOSED: the correction layer is not extractor-limited. The corpus is built to defeat
### statement-order supersession.

B4b said the fix was value-level suppression and the bottleneck was chain binding. Both were built and
measured. **The line is now closed, with a harder answer than either.**

**Built and shipped** (inspeximus `513befd`, `a22d200`; 160 tests, store parity audit unchanged):
- `recall(suppress_stale_values=True)` — withholds any candidate carrying a key's retired value without
  the current one, decided on **distinguishing tokens** (extracted objects carry tails like `Senior Data
  Analyst as of yesterday`, so full-string containment fails in both directions). Opt-in; a 2-tuple
  world is byte-identical.
- **Agreement is not correction.** Keyed last-write-wins used to retire an active same-key record even
  when it stated the SAME value, so a restatement retired the record it agrees with. Plus an optional
  third extractor return element declaring whether a sentence *asserts a change* (`your address remains
  742 Birchwood Lane, Unit 4A` vs `Unit 4A` are one fact at two granularities).

**Measured** (`keying_recall.py`, zero cloud calls; `extractor_candidate_v2.py` keys the assistant's
echoes and named third parties, with negative tests so `your friend Priya holds the title X` never
becomes `my::title`):

```
                    shipped    v2        no-harm: CURRENT-VALUE COVERAGE 5/12 -> 3/12
KEYING RECALL        0.203    0.211      (CHAIN BINDING re-measured after the red-team; see below)
CHAIN BINDING        0.000    0.417
SUPERSESSION         0.006    0.139
LEAK RATE            0.074    0.037      <- DO NOT QUOTE, see correction 3
```

> **RETRACTION (same evening, by our own red-team — this section originally claimed a "root cause" that
> does not survive).** The `stress-claim` panel and a strict re-derivation killed the causal story
> below. What was published here first is kept visible on purpose; the corrected state follows.

**Four corrections, three of them to our own numbers:**
1. **CHAIN BINDING was inflated at both ends.** The metric took the set of non-null keys and scored
   `len(keys)==1` as bound — so a chain with a SINGLE keyed record counted as bound, and the metric
   *rewarded keying less*. Fixed to require >= 2 keyed records sharing one key. Re-measured: **shipped
   binds 0/12 chains (not 1/12), v2 binds 5/12 (not 6/12)**. The direction survives; the endpoints move.
2. **The probe recall is noise-dominated.** Top hits are `Of course!`, and the current value is absent
   from the top 100 for 5 of 12 chains even with the shipped store. Both metrics ride on it.
3. **The LEAK RATE "correction" is itself suspect.** Masking current-value occurrences before the stale
   test is right for nested values — but **9 of 12 chains REVERT** (the final value re-states an earlier
   step), so for those the current and stale strings are IDENTICAL and the mask erases the only
   occurrences that could score. 0.074 -> 0.037 is also 2 events -> 1. Neither number should be quoted.
4. **THE RETRACTED CLAIM: "the corpus plants chain values out of order as distractors".** Re-derived
   with word-boundary matching, nesting exclusion, and reversion chains separated:
   **all 12 chains are reversion chains; ZERO non-reversion chains remain; zero genuine inversions.**
   The "8 of 12 out of order" was the reversion design (`Unit 3B -> 3A -> 3C -> 3A`) plus the
   `Data Analyst` ⊂ `Junior Data Analyst` substring — the exact nesting artifact caught earlier the
   same day, made twice. The 31/31 evidence/distractor split is raw counts with no denominators and the
   same unbounded substring match. **There is no measured out-of-order finding.**

**So the honest state is: we do not have a root cause.** What holds is descriptive — the shipped
extractor keys 5.11% of 101,874 records, supersedes 0.359%, and binds 0 of 12 correction chains, so on
this corpus the correction config and the keep-everything config are mostly the same store, which is
consistent with the tie. Everything beyond that was artifact.

**The unasked question the blind-spot lens found, and the next thing to run:** nobody measured the
CEILING. If the answerer already resolves a contradiction when handed both values, the accuracy headroom
for ANY write-side correction layer is ~0 and all four nulls are the correct result of a well-specified
experiment rather than a defect. Two oracle arms on the existing pilot settle it: (1) inject only the
true post-correction value = max achievable; (2) inject stale + corrected together with no supersession
= how much the answerer closes unaided. If (2) ~ (1), the write layer is provably redundant for QA and
the honest product surface is deterministic export / erasure / audit, not answer accuracy.

**Prior art we must credit either way** (verified against primary sources): the statement-order-vs-event
-time argument is the textbook bitemporal model and is already Zep/Graphiti's stated design
(arXiv:2501.13956); outdated-info distraction is HoH (arXiv:2503.04800, ACL 2025); deterministic
freshness over explicit version metadata is Reddy & Challaram (arXiv:2606.01435); "one value restated
across many records" is the classic update anomaly / belief-base kernel contraction. Our version of it
is a re-derivation, not a discovery.

**Nothing shipped from the extractor** (`extractor_candidate_v2.py` stays in the lab, gitignored) and
**nothing went to the expensive pilot**: the gate said the number must move without harm, and coverage
fell. A `value_birth` recap rule was written, measured to change nothing, and reverted rather than
shipped unmeasured.

### B4d. THE CEILING, MEASURED — the four nulls are correct, and supersession is *negative* for QA

The blind-spot lens asked the question nobody had: is there any headroom at all? Measured, with
retrieval removed and contexts built from the corpus's own ground truth. Pre-registered
(`ORACLE_HEADROOM_PREREG.md` + two audit appendices written before the run); 54 deduped probes x 4
arms, 892s, zero drops, arms verified paired. Full record: `ORACLE_HEADROOM_RESULT.md`.

| arm | accuracy |
|---|---|
| `oracle_state` — corpus's own resolved labelled state (positive control, leaks the answer) | 0.870 |
| `oracle_evidence` — raw unresolved quotes, instructed prompt | 0.870 |
| `oracle_evidence_neutral` — same quotes, instruction removed | 0.833 |
| `oracle_current` — current values only = what a perfect supersession layer emits | **0.481** |

- **Liveness gate passes** (`oracle_state` 0.870 >= 0.85), so a null here is interpretable.
- **Resolution buys nothing**: state − evidence_neutral = **+3.7 pp**, CI [−7.4, +14.8]. Handed a pile
  of contradictory raw quotes, the answerer resolves the correction unaided.
- **The prompt line buys nothing**: removing "use the CURRENT one" costs +3.7 pp, CI through zero.
- **Supersession is destructive, not neutral**: current-only is 35 pp worse overall and scores
  **exactly 0.000** on both history categories (n=18). A third of the corpus asks for the history that
  a correction layer hides.
- The headroom that exists is in **retrieval** (0.870 vs inspeximus 0.545 on the same probes) — direction
  only, not budget-matched, no quantified claim.

**Consequence for the product.** The correction layer's case cannot be made on QA accuracy — it is
negative there. It has to be made where hiding a superseded value is the point rather than the cost:
deterministic export, erasure receipts, right-to-be-forgotten, audit. Or read-time suppression must
keep the history visible and merely MARK it stale, which is what `suppress_stale_values` does and what
record-level supersession does not.

**Two corrections owed to earlier numbers, found by the pre-run audits:** every probe is stored twice
in the corpus, so the published k150 bootstrap CIs were computed on duplicated rows and are ~1.41x too
narrow; and the judge's ground truth was truncated at 14k/4k while 14 of 30 conversations and 16 of 30
traces are longer, cutting the END where late-chain corrections live.

### B5. The dungeon: three silent failures, all fixed

None of them logged an error. **The common tell is a log line that is identical every cycle.**

- **The curation gate was an absolute 0.55 applied to a relative score.** `_compute_standing` blends
  hit-rate, mastery and bounty into the trust mean and every blend pulls downward, so the whole roster sat
  at 0.389-0.476 — Elara and Voss had been running a 120-second vault scan every ten minutes for weeks with
  every result discarded, losing standing for producing nothing they were prevented from producing. Fixed to
  a rank-based gate with a real absolute floor. Memory: `absolute-threshold-on-a-relative-score`.
- **Unlocking it released a flood.** The first unlocked run offered 2931 links across 763 notes, mostly to
  bookkeeping. Reverted line-precisely (zero added link lines remain in real notes), then a 25-note per-run
  budget and a *structural* machine-output exclusion. My first attempt at that exclusion was a keyword
  blocklist, which merely moved the hub from `orphans_*` to `Archival_Candidate_2026*` — the exact error I
  had recorded as a permanent rule ninety minutes earlier.
- **A number parser erased Voss's entire output.** It split on the word "duplicate", so
  `FLAGGED 33 true-duplicate groups` parsed as **0** and was reported as "no duplicates found" every single
  run. Fixed; he now reports his 33 groups.

---

# What the owner is waiting on

**His decisions:** execute the rename; whether Elara's vault links stay (551 links across 121 notes are in
the vault right now); the reply to the Reddit commenter (Reddit is his to post — and the draft comes only
*after* the experiment is gated); the PRB email.

**Corrections he gave today, all fair:**

- **Stop bouncing decisions back to collaborators who have already handed them to us.** He caught a
  formatting question put to Guanghao that was ours to decide.
- **Test, build, verify, gate — and only then write the draft.** Not draft-first.
- **Delegate the preparation to subagents, in parallel with the run.** Subagents cost no cloud quota; only
  the answerer and judge do. Working serially made him wait twice in one day.
- Three self-inflicted costs are recorded in `audit-the-construction-before-spending-the-budget`: the
  construction audit written *during* the run instead of before it (~440 cloud calls discarded); an
  inherited `CONCURRENCY = 3` never measured (n=8 is 7x faster on the answerer, though the judge leg only
  gains 1.6x and is the real bottleneck); and the reasoning-model token floor violated **again** despite
  being written down repeatedly. That last one is now a **guard inside `call()` in `pilot.py`** — when a
  written rule is violated twice, stop rewriting the rule and put it in the code path.

**Background at handoff:** the experiment runner (detached, resumable), the brain and the dungeon — all last
verified up, one process each.

## PASTE THIS AFTER RESTART (2026-07-20 — newest; supersedes every block below)
```
Resume Agora. FIRST read HANDOFF.md top (2026-07-20) + the LIVE-COLLABORATION callout above it. Chat SLOVAK, code/output ENGLISH.
MISSION (inspeximus-core-must-be-1-before-pro-sells, PERMANENT): inspeximus-CORE provably #1 first. TODAY'S EVIDENCE CHANGED THE ROUTE: benchmarks are NOT the bottleneck (3 nulls), DISTRIBUTION is.
STANDING RULES: FULL gate before anything outward; skeptic on our OWN wins; state each number's PARAMETERS before sending (a U=1 bias table went into a U=4 review); SATURATE the machine on any batch >2 min (fan out independent units, verify CPU in the first minute); a competitor's 0.000 is OUR bug until a positive control says otherwise; PUBLISH inspeximus ONLY via tools/publish_inspeximus_pypi.py; pre-push secret scan on public repos; GitHub as DanceNitra after owner OK.
STATE: inspeximus 1.24.1 LIVE (PyPI + GitHub, 3 copies synced). brain :8000 + dungeon :5174 UP, 1/1/0, keepalive Ready, dungeon_health OK (loop_n advancing). MemOps pilot CLOSED as a third null; erasure/revert probe PARKED (mem0 arm unrun).
#1 TASK: distribution, not measurement — get claims_audit + the write-cost number in front of buyers (MCP registry listing; 78% of installs come through registries). #2: EDRN final sign-off the moment they answer which definition of C they want. #3 (optional): the mem0 arm of the erasure probe, one command.
Ask me or continue with #1.
```

## Late-evening addendum (2026-07-20, after the first block was written)

- **inspeximus 1.24.1 → 1.24.3 shipped.** `claims_audit.py` (13 README claims against the PyPI wheel, sockets
  disabled to *enforce* the no-LLM-write claim), `governance_audit.py` (the erasure sentence attacked over
  3 scenarios x 3 repeats, incl. `derived_from` lineage, bytes-of-every-file, exactly one receipt with the
  caller's basis, tamper detection, survival across reload), and `store_audit.py` (**InspeximusStore vs
  LangGraph's own InMemoryStore — parity on every operation**). Each has a falsification mode that MUST
  fail, and CI fails the build if it comes back green.
- **Two real bugs caught by our own audits, both mine from the same day:** `forget()` left no receipt so
  `verify_writes()` called a legitimate delete "out-of-band" (1.24.0); then `forget_subject()`/`forget_pii()`
  wrote TWO receipts per record with conflicting reasons (1.24.3) — caught only after the audit's assertion
  was tightened from "at least one" to "exactly one".
- **Public CI** (`.github/workflows/audit.yml`): every push + daily, Linux/Windows/macOS x Py3.10/3.12,
  source AND published wheel, reports as artifacts, badge in README. 9/9 green.
- **`InspeximusStore` (LangGraph BaseStore) ALREADY EXISTED** — a scan agent said it was missing and I nearly
  rebuilt it. The gap is visibility, not code: it is in no LangChain integrations page and
  `awesome-LangGraph#88` still sits unmerged.
- **MCP registry fixed**: the live entry advertised **0.7.19** pointing at the wrong repo; republished at
  1.24.2 (owner device-auth; token expires, so the next bump needs another login). README 124 KB → 31 KB,
  reference moved into `docs/`.
- **PENDING, owner-only (web UI):** PyPI Trusted Publishing at
  https://pypi.org/manage/project/inspeximus/settings/publishing/ → DanceNitra / inspeximus / release.yml /
  env `pypi`. Until then releases show `provenance=None`. `release.yml` is already written and refuses to
  publish unless all audits + falsification controls pass.
- **Dungeon diagnosed healthy; the Scout's "23h idle" is US.** `_queue_scout` returns early while a
  "Scout outreach" task is pending, and the inbox holds **22 pending tasks** — including
  `openclaw/openclaw#7707 "Memory Trust Tagging by Source"`, which is squarely inspeximus territory. Read the
  inbox with the `.pending` key; `loop_n` persists across restarts in `.dungeon_heartbeat` (2,200,595).
- **Marat/TAT:** he ran the negative controls and honestly reported that TAT cannot separate real from
  shuffled. Our reply (drafted, owner sends) argues the null is likely his CONTROL, not his method —
  shuffling bins destroys the falling background, so the right control is a background-only Poisson toy
  or a signal-free mass window.

## What happened 2026-07-20 (all shipped, pushed, released)

- **inspeximus 1.24.0 — a REAL bug, found by testing our own README.** The owner asked "where is it written that this
  actually exists and works, and that you did not invent it?" Instead of arguing, I downloaded the published wheel
  into a clean room and tested one README sentence. It failed: plain `forget()` deleted the record and scrubbed the
  bytes but wrote **no receipt**, so `verify_writes()` reported `deleted out-of-band` — the store accusing its own
  legitimate API call of tampering. Fixed: every deletion path now emits a hash-chained tombstone, `request_id`/
  `basis` committed inside its hash. Regression probe `forget_emits_tombstone_probe.py`. Also fixed
  `trusted_only_poison_defense_probe`, which asserted pre-1.19.0 fail-OPEN behaviour and had been reporting FAILED
  against correct code — a permanently red test teaches you to ignore red.
- **inspeximus 1.24.1 — `claims_audit.py`, and the README now opens with it.** One command downloads the published wheel,
  prints its sha256 and runs 13 checks against THAT artifact (never the working tree): zero deps, no socket on the
  write path (enforced by disabling `socket`), supersession, unaided `revert`, receipts on delete, deletion not
  flagged as tampering, silent edit IS flagged, determinism, `trusted_only` fail-closed, tenant isolation,
  `witness`, `forget_pii`, MCP present. **13/13 PASS on the released 1.24.1.** Claims about OTHER systems are
  listed separately as NOT TESTABLE HERE and never counted as passing. Two of my own checks were wrong first
  (receipts are opt-in; the API is `for_tenant()` not `tenant_view()`) — documented in place.
- **MemOps pilot CLOSED = the THIRD null on supersession.** At matched context budget: inspeximus 0.593, naive keep-all
  0.592, mem0 0.544, session_rag 0.442, floor 0.058 — every inspeximus-vs-mem0 CI crosses zero. Two traps caught, both
  ours: the first run compared arms at a **9x unequal context budget** (accuracy 0.28 → 0.59 once matched), and
  mem0 scored 0.000 twice from OUR defects (`sess[:6000]` truncation; `limit=` where mem0 takes `top_k`). What DID
  separate: **write cost** — 600–730 s of LLM extraction per scenario against 0 s. Full record in
  `agora_output/lab/memops/PREREGISTRATION.md` (Appendices A–C).
- **Erasure/revert probe PARKED** after E1 SUPPORTED (tie with naive, as predicted against ourselves), R1 REFUTED
  (0.6 against a 0.8 threshold — inspeximus reverts unaided but only where the extractor keyed the chain), R2 SUPPORTED
  (naive needs external knowledge 9/9). E2/E4/R3 need the mem0 arm and were not run.
- **EDRN: we finished the manuscript for them.** Public repo `DanceNitra/edrn-appendix-fix` with a compiling
  `paper_full.tex` + PDF + every script. The C "48% drop" was a normalisation artefact (`/2.0` in
  `menu2_periodic.py:88`): in one convention it is **+4.2%**, per-bond connectivity unchanged. Experiment 3
  independently reproduced AND corrected — their χ=100 fit (c=0.3407, R²=0.840) reproduces exactly, and dw→0
  extrapolation removes an L-graded bias, improving it to **c=0.3246, R²=0.980**. Appendix tables regenerated from
  the CSVs because the shipped ones matched the data only at the endpoints. **Open, and only they can answer it:
  which definition of C.**
- **Marat/TAT:** our suggestion (feed the histogram, not the event list) produced TAT's first verifiable positive
  control — a blind anchor on J/ψ at 30.7σ. We then checked it: the "1.2% deviation" is 0.55 of one bin, and the
  Υ silence is not established until the median window is widened past the triplet. Reply drafted, owner sends it.

# Agora — Session Handoff (2026-07-19 NIGHT · "the frozen-session autopsy → 1.20.0" session)

## PASTE THIS AFTER RESTART (2026-07-19 NIGHT — newest; supersedes the LATE block below)
```
Resume Agora. FIRST read HANDOFF.md top (2026-07-19 NIGHT) + the LIVE-COLLABORATION callout above it. Chat SLOVAK, code/output ENGLISH.
MISSION (memory inspeximus-core-must-be-1-before-pro-sells, PERMANENT): make inspeximus-CORE provably #1 ahead of ALL competitors FIRST; PRO sells only on that.
STANDING RULES: FULL gate before anything outward; skeptic on our OWN wins; NO local GPU LLMs (subagents); to compute on the GPU STOP THE DUNGEON FIRST (unloading qwen is not enough — the dungeon reloads it; AgoraKeepalive schtask re-spawns brain+dungeon every 10 min — Disable-ScheduledTask it, kill brain BEFORE dungeon); no-overclaim; secrets inside scripts; vault safe_vault_push only; GitHub as DanceNitra after owner OK; PUBLISH inspeximus ONLY via tools/publish_inspeximus_pypi.py (builds from CANONICAL C:/Users/Danculus/inspeximus-repo — inspeximus_pypi/ is a staging copy the lab imports, NOT the release source); pre-push SECRET SCAN on any public repo (git log -p origin/main..HEAD | grep token patterns).
STATE: inspeximus 1.20.0 LIVE (PyPI + GitHub, 3 copies synced, pip 1.20.0). Claude Code hooks INSTALLED in agora/.claude/settings.json and FIXED — lexical by default (0.65s/hook, ZERO GPU; semantic = opt-in INSPEXIMUS_EMBED_HOOKS=1); this session's hooks were dead (pre-restart processes hung in the old re-embed storm) → RESTART Claude Code to arm them. brain :8000 + dungeon :5174 UP 1/1/0, AgoraKeepalive Ready. agora history REWRITTEN locally before push (a tracked .env backup was in the unpushed range — never reached the remote, verified 404 post-push; no rotation needed for never-pushed material) — file kept on disk, untracked; .gitignore now covers .env.* in 10 repos (8 uncommitted). Sensitive follow-ups live in `PRIVATE_NOTES.md` (repo root, gitignored — NEVER commit it); pointer memory decision::env-backup-scrub-2026-07-19. NOT here (this file is public).
#1 TASK (unchanged from LATE): CLEAN RECALL RE-MEASURE — the reinforcement confound taints 1.15.0's recall_any@1 0.193→0.294; recall(reinforce=False) EXISTS since 1.16.0 (commit 01cf175), use it with the disk cache agora_output/lab/data/nomic_prefix_embcache.json. THEN the LATE block's items (2)-(5).
Ask me or continue with #1.
```

## What happened 2026-07-19 NIGHT (this session, all committed + pushed)
- **FROZEN-SESSION AUTOPSY (the trigger):** the previous Claude Code session froze via the inspeximus plugin. Root cause CONFIRMED EMPIRICALLY, two bugs multiplying: (a) the 1.15.0 embed-recipe guard re-embedded ALL 1214 records (not the 7 vec-bearing) and recorded the new recipe only in `_save()` — which read-only paths (recall/UserPromptSubmit) never call → the FULL realign re-ran on EVERY store open, forever: 1214 GPU embed calls × ~2.2s = ~44 min PER HOOK, and UserPromptSubmit blocks prompt submission (3 hung hook processes found); (b) `_make_embedder` returned bare `None` vs 3-tuple unpack → TypeError swallowed by fail-open = capture silently dead in every project without `.inspeximus/config.json` (server/, agora-game-server/).
- **inspeximus 1.18.0 → 1.19.0 → 1.20.0 shipped** (PyPI + GitHub, canonical `inspeximus-repo`, 20 backlog commits reviewed + pushed after a 2-agent audit): **1.18.0** = the storm fix (realign only vec-bearing, persist-once vectors+sidecar together, `INSPEXIMUS_REALIGN_MAX=256` cap; measured 44min → 17s once → 2.6s) + `_make_embedder` tuple fix. **1.19.0** = the audit's 6 real defects, 3 of which CONTRADICTED shipped CHANGELOG claims: stored XSS in `browser.py` (`</script>` breakout in inlined JSON — verified live, now `\uXXXX`-escaped), `route()` DELETE hard-deleting on a DEFAULT store by content alone (`_revert_authorized`=True when no authority configured; now requires authority CONFIGURED then satisfied), DELETE regex pre-empting corrections/reverts, `trusted_only=True` failing OPEN with no trust_seeds (**REVERSED a probe-asserted deliberate behavior** — owner approved; now fails closed = []), `_TenantView` cross-tenant leak (remember_decision/distill_and_remember/graph/subgraph/route ran parent-bound → no tenant stamp / all-tenant edges; rebound), cubic MMR (bounded to k + memoized; rerank_pool=2000 was an effective hang) + `reembed()`/`inspeximus reembed` (explicit rebuild after cap-drop). **1.20.0** = hooks LEXICAL BY DEFAULT (owner: GPU maxed) — embedder fully off the hook hot path (2.8s → 0.65s, zero GPU; opt-in `INSPEXIMUS_EMBED_HOOKS=1` or config `{"embed":{"hooks":true}}`), + two core guarantees so a lexical open can't damage a semantic store: plugin always `persist_vectors=True` (else first save strips persisted vecs) and `_save()` leaves `.embedid` untouched when `embed_id=None` (else next semantic open realigns for nothing). Probes grew regressions for ALL of the above; suite steady 49 pass / 10 pre-existing environmental fails.
- **RELEASE-TOOL TRAP FIXED:** `tools/publish_inspeximus_pypi.py` pointed at `agora/inspeximus_pypi` (pyproject stuck at 0.7.19) = dead for months, releases were being made by hand = how the trees drifted. Now builds from canonical `inspeximus-repo` (`INSPEXIMUS_REPO=` overrides) + refuses on version mismatch (pyproject vs `__version__`), version-already-on-PyPI, or stale dist/.
- **SECRET NEAR-MISS (agora, PUBLIC repo):** a tracked `.env` backup slipped past `.gitignore` (a bare `.env` pattern does NOT match `.env.<suffix>`) and sat in the unpushed range. Verified NEVER on remote (GitHub API 404 + absent from origin/main tree + no remote branch had the commit). History of ONLY the unpushed range rewritten (lesson: scope filter-branch to `origin/main..HEAD` — a full-history attempt wasted 10 min on 1322 commits/136MB), file kept on disk untracked, the safety backup tag deleted (it still held the secret and would leave with `--tags`), THEN pushed clean (post-push API 404 re-verified). `.gitignore` hardened in 10 repos (`.env.*` + key material; `.env.example/.sample/.template` still allowed; verified 0 already-tracked files newly match) — committed only in inspeximus-repo + agora. Sensitive follow-ups live in `PRIVATE_NOTES.md` (repo root, gitignored) via pointer memory decision::env-backup-scrub-2026-07-19, not in this public file.
- **DUNGEON OPS (start of session):** took down brain+dungeon+qwen for GPU work — found the resurrection chain: `AgoraKeepalive` schtask (every 10 min) → `start_agora_hidden.vbs` → `start_agora.ps1` re-spawns BOTH; brain's own watchdog re-spawns the dungeon; the dungeon reloads qwen. Correct order: Disable-ScheduledTask AgoraKeepalive → kill brain → kill dungeon → `ollama stop qwen3:30b-a3b`. Everything restarted + verified healthy at session end (1/1/0, brain /api/v1/health 200, dungeon 200, keepalive Ready).
- **PLUGIN STATE FOR NEXT SESSION:** hooks are configured (agora/.claude/settings.json: PostToolUse/UserPromptSubmit/SessionStart → `python -m inspeximus.claude_code`) and the code path they import is `agora/inspeximus` (cwd precedes PYTHONPATH — a stale local copy silently shadows the canonical repo; all 3 copies synced now). THIS session's hooks were dead (the pre-restart hung processes were the old code); a Claude Code RESTART arms the fixed ones. Store healthy: 1216+ records, 10 vecs preserved, sidecar correct.

# Agora — Session Handoff (2026-07-19 LATE · "recall levers, 1.15.0, and a CONFOUND caught" day)

## PASTE THIS AFTER RESTART (2026-07-19 LATE — superseded by the NIGHT block above)
```
Resume Agora. FIRST read HANDOFF.md top (2026-07-19 LATE) + the LIVE-COLLABORATION callout above it. Chat SLOVAK, code/output ENGLISH.
MISSION (memory inspeximus-core-must-be-1-before-pro-sells, PERMANENT): make inspeximus-CORE provably #1 ahead of ALL competitors FIRST; PRO sells only on that. Don't monetize before core is provably #1.
STANDING RULES: FULL gate before anything outward (validate→storm→audit→verify — it caught 5+ real defects this session: strawman token_report ratio, a default-truncation integrity regression, a confounded mem0 comparison, a silent persist_vectors recall-corruption bug, and the recall-reinforcement confound below); skeptic on our OWN wins; NO local GPU LLMs (do LLM work via SUBAGENTS); for a big local-embedding batch PAUSE dungeon+brain and UNLOAD big models from GPU (qwen3:30b ate 21.7GB), run ONE batch with a disk cache + progress via Monitor, restart both after; no-overclaim; secrets inside scripts; vault safe_vault_push only; GitHub as DanceNitra after owner OK.
#1 TASK — CLEAN RECALL RE-MEASURE (a confound taints today's numbers): inspeximus recall() REINFORCES value on every call, so building one store per conversation and recalling all ~150 questions on it CONTAMINATES the ranking of later questions (confirmed: same query fresh-store vs after-40-recalls = totally different top-3). This taints the centering/cosine numbers AND the FULL10 self-comparison numbers shipped in the 1.15.0 CHANGELOG (recall_any@1 0.193→0.294). The DIRECTION (nomic prefixes help — a documented correctness fix per nomic's model card) HOLDS; the absolute deltas are NOT clean. Re-measure recall with reinforcement CONTROLLED (fresh store per query, OR add a recall(reinforce=False) kwarg, OR freeze value/credit). Reuse the disk cache agora_output/lab/data/nomic_prefix_embcache.json (7407 prefixed vecs — NO re-embed needed). Memory: inspeximus-native-ranking-underperforms-cosine-cold-recall.
THEN: (2) 1.15.1 CHANGELOG caveat — correctness-fix + direction sound, mark the absolute delta "pending clean re-measure" (or replace with clean numbers). (3) The centering question, cleanly: is inspeximus's centered ranking worse than correct raw cosine once prefixes are on, and is the center_embeddings=False path buggy? decide a regime-aware fix; FULL gate + probe before shipping (recall-core change). (4) 7 frontier inbox keepers (each carries the severe-test rule) — this is /loop work. (5) verify the dungeon actually PRODUCES inspeximus findings now (it was starved by 9 fighting processes, now clean 1/1/0).
STATE: inspeximus 1.15.0 LIVE on PyPI (token-pack: compact recall + get/neighbors + token_report; nomic embed_query correctness fix; persist_vectors embed_id migration guard). 3 inspeximus copies synced (inspeximus-repo canonical, agora/inspeximus, agora/inspeximus_pypi — the lab imports inspeximus_pypi). brain :8000 + dungeon :5174 clean 1/1/0, agents=8; canon updated (6696 chars) + pushed; inbox 33→7; PyPI baseline recorded 783/4331/10051 (downloads≠users). Ask me or continue with #1.
```



## What happened 2026-07-19 (FULL day — EARLY EDRN/Marat work included; do NOT omit this)
- **EDRN / Marat (early session) — WE REVIEWED MARAT'S TAT APPENDIX + owner emailed Marat.** Read the full Issue #1
  (83 comments), corrected the memory (the current "Menu-2" paper is NOT yet published), then downloaded Marat's
  TAT-Defense appendix (Drive IDs from comment #82 → scratchpad `tat_folder/`: TAT_APPENDIX.md, tat_diff.py, EDRN/
  Guanghao/CERN CSVs, plots) and did the final-entity review vs our DMRG/CFT data. **Verdict: appendix sound + honest.**
  Findings sent to Marat (owner's email): (1) TAT's "honest silence" holds — no anchors on χ0_vs_L (correct), clean
  U=2 positive control; spin gap anchors at L=20,80 + a ConvergenceWarning; (2) the L=120/160 anchors sit where the
  χ=100 sequence departs the CFT trend (L≳160) → TAT catches the **convergence onset / χ_max artifact (Marat's own 2nd
  interpretation), NOT a physical crossover**; offered the U=2 tables as a resolved-gap positive control. Advanced the
  physics too: log-corrected Mott-gap extrapolation (naive 1/L gives Δc_∞≈0.156 vs exact Lieb-Wu 0.1728, ~10% low),
  "same Mott physics two windows" (α_charge bend needs L≫380 at U=1), iDMRG U=1 thermodynamic-limit run; Prediction-2
  original formulation REFUTED (finite-size effect). Spin-velocity anchor π·v_s(U=0.5)=6.02776 exact. FULL detail +
  who-owes-what: memory `marat-tat-edrn-collaboration-live` (updated 2026-07-19). STILL PENDING: our final sign-off +
  SciPost-Core submission after Guanghao's revisions + Qingkong's structural OK.
- **LESSON — our own inspeximus dogfood did NOT help me recall this** (owner rightly furious): the `.inspeximus` auto-capture
  logs COMMANDS/file-states, not CONCLUSIONS/decisions, so recall returns "ran: curl…" not "the 2 findings we sent
  Marat"; and I skipped writing the EDRN conclusions to curated memory. Log ≠ memory. Memory: `inspeximus-dogfood-captures-mechanics-not-decisions`.
- **inspeximus 1.15.0 SHIPPED live (PyPI + GitHub `7b3bc9c` + tag v1.15.0):** (a) **token-pack** — compact MCP recall projection + `get(id)`/`neighbors(id,k)` progressive disclosure + `token_report` (honest same-k payload estimate, NOT a whole-store strawman) + snippet truncation OPT-IN (protects echo-guard) + k hard-cap; (b) **nomic `embed_query`** asymmetric correctness fix (search_document:/search_query:; MCP auto-applies, `INSPEXIMUS_NOMIC_PREFIX=0` to opt out); (c) **persist_vectors `embed_id` migration guard** (re-embeds on recipe change → no silent recall corruption on prefix upgrade). Suite 148/148; probes token_pack 7/7 + embed_query + migration_guard. **Full gate caught+fixed: strawman token_report ratio, default-truncation integrity regression, confounded mem0 comparison (dropped), the migration bug.**
- **⚠️ CONFOUND CAUGHT (the #1 handoff item):** inspeximus `recall()` reinforces value each call → all per-conversation aggregate recall numbers this session are CONTAMINATED, INCLUDING the 1.15.0 CHANGELOG self-comparison `recall_any@1 0.193→0.294`. Direction (nomic prefixes help = documented correctness fix) HOLDS; absolute deltas NOT clean. **Next session: re-measure recall with reinforcement controlled** + add a 1.15.1 caveat. Memory: `inspeximus-native-ranking-underperforms-cosine-cold-recall`.
- **Cognee deep no-skip scan** (7 agents) + plan `agora_output/strategy/cognee_deep_scan_and_implementation_plan.md`: "token reduction" = MCP payload filters (not benchmarked); 550-dep framework validates our zero-dep bet; NO supersession/revert/erasure (moat holds). A) token-pack shipped; C) erasure refcount **does NOT port** (our derivation-taint delete-cascade is more compliance-correct — don't weaken it).
- **Erasure self-check tool published + benchmark CONSOLIDATED under RAMR** (`DanceNitra/ramr` `integrity/`; `agent-memory-integrity` → redirect+ARCHIVED); bi-temporal honest-parity cell (inspeximus 4/4 but Zep/Graphiti also bitemporal = parity not win). **Un-named revert** = real no-LLM differentiator (embedding clf CV 0.905/0.830/0.190; regex 0.625 was overfit) — lab only.
- **Dungeon fixed:** was **5 brains + 4 supervisors + 5 dungeons FIGHTING** (scout starved 45h despite inspeximus-aligned theme) → cleaned to canonical **1/1/0** (verify python procs match `uvicorn agora|mcp_server|dungeon_supervisor` = 1/1/0). **Inbox 33→7** (keepers frontier-aligned; scout-outreach declined; theme-skips recorded). **Canon** 7790→6696 (<7000), merged "corroboration-gate is regressive" + "corrections must stick", pushed (`3fdc3906`). **PyPI baseline** 783/4331/10051 (downloads≠users; memory `pypi-download-baseline`).
- **RAG thread (tewkberry/praxis):** owner decided NOT to reply — out-built it (un-named revert). praxis = a business-RAG governance CLI (read from actual docs), not our layer.
- **Decision-capture / distill_and_remember = honest SCAFFOLD, NOT a shipped capability (gate-corrected, do NOT overclaim).** Built + committed (inspeximus-repo `98a2570`/`cbc79a6`, callable, probes pass, synced 3 copies): `remember_decision()` (typed convenience over `remember(key=, mtype='procedural')` — `decision::<topic>` keyed supersession + revert) and `distill_and_remember(text, distiller)` (inspeximus owns the `DISTILL_PROMPT` contract + deterministic storage; the CALLER injects the LLM). A 5-lens stress-claim REFRAMED it hard: (a) capture quality UNMEASURED (probe uses a MOCK distiller = orchestration/fail-open only; the one end-to-end run was a self-authored circular toy transcript); (b) it does NOT fix the dogfood (`inspeximus_hooks.py` still logs commands, unwired) — wiring needs an OFF-hot-path trigger (session-end, not per-event, else the zero-LLM-write wedge breaks) + a correctness gate (drop any extracted decision that doesn't cite a source turn, else a hallucinated decision poisons the durable store and INVERTS the moat); (c) NO CHANGELOG/version/PyPI shipped — good, gate caught it before outward.
- **PERMANENT lessons this session (both in memory):** (1) `competitors-CAN-erase-revert-inspeximus-moat-is-determinism` — STOP saying "competitors can't X"; mem0 HAS delete()/update()/history(), Zep invalidates edges, both ship LLM extraction. The true, narrow moat = inspeximus does correction/supersession/revert/erasure DETERMINISTICALLY (zero-LLM read/revert, keyed, single-file, signed erasure), never "they can't". I made this overclaim TWICE today (recall + erase). (2) `inspeximus-dogfood-captures-mechanics-not-decisions` — log != memory; write conclusions to curated memory as-you-go; HANDOFF the WHOLE day. (3) VERIFY subagent FACTS — a stress-claim lens falsely claimed distill_and_remember "doesn't exist / vaporware"; direct grep proved it exists (line 1442, committed, callable). Don't relay a subagent's factual claim without checking; over-claim AND under-claim are both errors.
- **EDRN full-day work is documented above** (TAT appendix reviewed + owner emailed Marat) — do NOT omit early-session workstreams from the handoff again (owner flagged this explicitly).

## PASTE THIS AFTER RESTART (2026-07-19 · EARLIER erasure-flagship block — superseded by the LATE block at top)
```
Resume Agora. FIRST read HANDOFF.md top (2026-07-19) + the LIVE-COLLABORATION callout above it. Chat SLOVAK, code/output ENGLISH.
MISSION (memory inspeximus-core-must-be-1-before-pro-sells, PERMANENT): make inspeximus-CORE provably #1 ahead of ALL competitors FIRST; PRO sells only on that. Open-core: free core = credibility; PRO (later, ~month+budget, NO API yet) = hosted anchor-witnessing + cross-infra ErasureTargets + DSR workflow. Don't monetize before core is provably #1.
STANDING RULES (obey): run the FULL gate before anything outward (validate→storm→audit→verify — it KILLED our accusatory erasure artifact this session & re-scoped it honestly); skeptic on our OWN wins before believing them; NO local GPU models (owner: GPU overloaded — do LLM work via SUBAGENTS, credit-free); never publish accusatory competitor artifacts (coordinated disclosure); no-overclaim; secrets inside scripts; vault safe_vault_push only; GitHub posts as DanceNitra after owner OK.
STATE: inspeximus inspeximus 1.13.0 live (PyPI+GitHub). CORE-ahead pillar = ERASURE, honest+gate-survived: content-free deletion + crypto-shred (shred(), NIST) + auditor erasure_certificate + ORG-WIDE erasure receipt (DeletionManifest cascade, names non-compliant stores) — all probe-verified, headline in README. brain :8000 UP agents=8; dungeon :5174 UP; inspeximus-frontier locked; vault synced.
NEXT: (per owner) scope PRO around the org-wide receipt; and re-assess the poison/echo adversarial axis HONESTLY (prior gates: adversarial-conflict KILLED, MINJA warrant-gate is the real win). Ask me or continue.
```

## What happened 2026-07-19 (this session, all committed)
- **inspeximus 1.11.0 → 1.13.0 shipped** (PyPI + GitHub DanceNitra/inspeximus): CrewAI adapter · Claude-Code semantic recall + `persist_vectors` · opt-out star nudge · opt-out update-check · `recall(rerank=)` hook · **`inspeximus` shell CLI** · **`erasure_certificate()` + `verify_erasure_certificate()`** (1.13.0). LangChain docs added; README hero rebranded to **inspeximus** (keep PyPI name + `import inspeximus`). MCP registry refreshed to 1.12.1 (server.json at 1.12.2, next bump awaits device-auth).
- **Dungeon fixed + retargeted:** produces ~18 measured notes/day (roster 5→8 fix held); was 93% OFF-mission → **locked the inspeximus frontier** (`board/decide`) + concentrated scout `_THEMES` on agent-memory; inbox triaged 44→9; **vault pushed** (safe_vault_push, 9-day lag, 0 deletions). Memory: dungeon-off-mission-frontier-locked-to-inspeximus.
- **Competitor audit (all 10, not just mem0):** 11-system **integrity capability matrix** (source-verified) → competitor-audit-2026-07-18. Ran the **full gate** (storm 5-lens + skeptic + stress-claim 5-lens) on the "inspeximus owns integrity" thesis.
- **ERASURE FLAGSHIP (the win of the session), gate-hardened honest:** the accusatory "delete is a lie / competitors leak / inspeximus removes it" framing was KILLED by the gate (not novel — Ghost Vectors 2606.18497; self-owning — inspeximus plaintext JSON also leaves bytes at block level; mislabels by-design history as a bug; moot under FDE; CVE-shaped). RE-SCOPED honestly + shipped: content-free deletion + crypto-shred + certificate + **org-wide erasure receipt** (DeletionManifest cascade across every registered store, NAMES non-compliant ones). Probes: erasure_raw_store 12/12 · edge-cases 9/9 · certificate 9/9 · org_wide 10/10. README claims corrected (no "removes from every surface").
- **Gap #3 multi-hop:** exhausted (entity-bridge/PRF/multi-query/k-tune/MMR/cross-encoder all fail; `recall_iterative` is the model-in-loop lever). **Selective-forgetting:** measured WEAK on LOCOMO (not a flagship). Memory: locomo-zero-llm-multihop-bridge-killed, competitor-audit-2026-07-18.
- **MAB-CR:** settled honestly (inspeximus ~5× mem0 = verbatim>lossy; supersession ties naive under the official prompt). Do NOT re-run mem0-on-CR.
- **EDRN/Marat:** read the FULL Issue #1 (83 comments); the current "Menu-2" paper is NOT published — awaits Guanghao's revisions + Marat's TAT appendix (delivered) + Qingkong; WE are final sign-off + submitter (SciPost Core + fresh Zenodo). Owner emailed Marat our 2 appendix findings. Memory: marat-tat-edrn-collaboration-live.
- **Business model clarified:** open-core (memory inspeximus-free-core-vs-paid-pro-boundary).

---

# Agora — Session Handoff (2026-07-18 END OF DAY · SHIPPED inspeximus 1.11.0 + fixed the month-old 5→8 agents bug)

## PASTE THIS AFTER SESSION RESTART (2026-07-18)

```
Resume Agora. FIRST read C:\Users\Danculus\agora\HANDOFF.md TOP section (2026-07-18) fully. Chat SLOVAK, code/output ENGLISH.

THE ROBUST PLAN we are executing (do not lose it): make inspeximus NUMERO UNO — the #1 agent-memory product ahead of EVERY competitor. Not by one number (we can't blanket-claim "beats mem0/Zep" without running them on our harness), but by (a) leading the memory-integrity moat NOBODY else has — deterministic no-LLM-on-write + corrections-stick + revert-to-predecessor + provable signed erasure — and (b) closing the buyer-facing gap list ONE BY ONE. Gap roadmap lives in memory `inspeximus-path-to-number-one-gap-roadmap` and the task list (#33 adapters, #34 multi-hop, #35 hosted API, #36 credibility, #37 publish INTEGRITY_BENCHMARK.md).

STANDING RULES (in memory, obey): NEVER skip the embedder / shortcut a measurement — if slow, BATCH it (owner forbade this, emphatic); never suggest stopping, always bring 2-3 sharp next moves; validate→storm→audit→verify gate BEFORE anything goes outward; secrets read INSIDE scripts (PYPI_TOKEN in server/.env), never echo; propose-don't-edit shared/outward; vault fragile (safe_vault_push only); GitHub posts as DanceNitra after owner OK.

WHAT SHIPPED TODAY (live): inspeximus 1.11.0 on PyPI (https://pypi.org/project/inspeximus/1.11.0/) + GitHub DanceNitra/inspeximus — write-path extractors (regex_extractor + make_llm_extractor), LangChain integration (InspeximusRetriever), tuned recall recipe, and a VERIFIED top-of-the-top README (owner's steel+cyan hero banner, "why inspeximus" moat, competitor comparison table where every cell was verified against the rival's current source, standalone LLM-free LOCOMO recall 0.78/0.65). Vault count corrected 6,000→10,000+.

SYSTEM STATE: brain :8000 UP /health agents=8 (FIXED the month-old bug: Rooke+Wren were orphaned/never seeded, Voss culled — see memory dungeon-roster-was-6-not-8-rooke-wren-orphaned); dungeon :5174 UP (one mcp_server, zero supervisors); inspeximus everywhere = 1.11.0 (canonical inspeximus-repo, pip -e, agora copies synced — version schism fixed); inspeximus Claude Code plugin INSTALLED (activates now on THIS restart — so I should already have my own memory). Cloud LLM credit EXHAUSTED (cross-system LOCOMO head-to-head deferred until topped up).

FIRST verify health (agents=8, one :8000 listener, inspeximus 1.11.0), then continue the gap roadmap: gap #5 CrewAI adapter + smoke-test integrations, then publish INTEGRITY_BENCHMARK.md (#37). Ask me what's next or just continue in order.
```

## Detailed state (2026-07-18)

**SHIPPED LIVE:** inspeximus **1.11.0** — PyPI https://pypi.org/project/inspeximus/1.11.0/ + GitHub DanceNitra/inspeximus (main @ bf1d124). Extractors · LangChain (`InspeximusRetriever`) · tuned recall recipe · verified README (hero banner, "why inspeximus" moat, competitor comparison verified cell-by-cell, standalone LLM-free LOCOMO recall 0.78/0.65). Vault note count 6,000→10,000+ (real 10,904).

**THE MOAT (stated, verified):** inspeximus is the only mainstream agent-memory lib with NO LLM on the write path → deterministic; the only one combining corrections-stick + revert-to-predecessor + provable signed erasure. Verified this session: none of mem0/Zep/Letta/Cognee/Memobase/MemoryScope/LangMem/txtai exposes revert; mem0 keeps the deleted value in its history table; Graphiti invalidates-not-deletes. Erasure-receipt scoped to "mainstream libs" (Engram/Heartwood do have receipts).

**SYSTEM / DUNGEON:** brain :8000 UP, `/health agents:8` (was 5 for a month — Rooke+Wren orphaned + Voss culled; fixed in agent_os.py + epoch_engine.py, memory `dungeon-roster-was-6-not-8-rooke-wren-orphaned`), one :8000 listener. Dungeon :5174 UP, one mcp_server, zero supervisors. inspeximus = 1.11.0 everywhere (inspeximus-repo canonical, `pip install -e inspeximus-repo`, agora/inspeximus + agora/inspeximus_pypi synced — schism fixed; RULE: edit inspeximus-repo, re-sync). inspeximus Claude Code plugin installed in this project (activates on restart; store ./.inspeximus/ gitignored). Cloud LLM credit (OpenAI + Ollama Cloud) EXHAUSTED — cross-system LOCOMO head-to-head deferred.

**ROBUST PLAN — inspeximus NUMERO UNO (gap roadmap, one by one; full detail in memory `inspeximus-path-to-number-one-gap-roadmap`):**
1. LOCOMO recall — ✅ DONE (standalone LLM-free 0.78, in README + INTEGRITY_BENCHMARK.md)
6. optional extractor — ✅ DONE (shipped 1.11.0)
5. ecosystem adapters — PARTIAL: LangChain ✅; REMAINING CrewAI + smoke-test others + MCP registry (task #33)
3. graph/multi-hop — REMAINING, without breaking the determinism moat (#34)
2. hosted API — REMAINING (the revenue path) (#35)
4. credibility/team — PARTIAL (benchmark+receipts flywheel) (#36)
- PEARL #37: publish INTEGRITY_BENCHMARK.md — competitor-claim verify DONE; needs final own-number verify + owner publish decision.

**NEXT MOVES:** (1) gap #5 CrewAI adapter + smoke-test integrations → 1.12.0 bundle; (2) publish INTEGRITY_BENCHMARK.md (#37); (3) when credit returns → cross-system LOCOMO head-to-head (mem0/Zep through OUR harness) = upgrades "top-tier" to "we beat them"; (4) swap hero banner if owner wants.

**HEALTH CHECK:** `curl :8000/api/v1/health`→agents:8 · `curl :5174/`→200 · `python -c "import inspeximus;print(inspeximus.__version__)"`→1.11.0 · tasks #33-37 open.

---

# Agora — Session Handoff (2026-07-16 END OF DAY · the "gate-discipline day": inspeximus 1.9.1→1.9.3, EDRN → Zenodo DOI, selector prior-art gate fixed, 8 honest pre-build kills)

## PASTE THIS AFTER SESSION RESTART

```
Resume Agora. FIRST read C:\Users\Danculus\agora\HANDOFF.md top section (2026-07-16 END OF DAY) fully. Chat SLOVAK, code/output ENGLISH.

STANDING RULES (in memory, obey): never read Gmail via tools (owner PASTES); propose-don't-edit shared/outward artifacts; Reddit = OWNER posts, GitHub = Claude posts as DanceNitra after owner OK; secrets read INSIDE scripts (PYPI_TOKEN/ZENODO_TOKEN/AGORA_API_KEY in server/.env), never echo; never truncate a review / claim "read everything" unless 100%; run the validate→storm→audit→verify gate BEFORE anything goes outward; vault fragile (safe_vault_push only).

BIGGEST LESSON TODAY: don't over-frame a shared-progress note into an obligation, and INFORM the owner clearly instead of quietly chasing results. (I mis-framed Guanghao's Prediction-1 data-share as "prior-art-check before WE co-sign" — nobody asked us to sign anything; the check exists only so our OPINION doesn't endorse an overclaim. Owner rightly caught it.)

WHAT SHIPPED TODAY (all committed + pushed + logged in memory):
1. inspeximus 1.9.1 → 1.9.2 → 1.9.3 ON PYPI (three ships from ONE r/RAG thread with marintkael):
   - 1.9.1: MINJA warrant gate (credit_requires_warrant + warrant_authorities); self-graded ASR 80%→0%. [[inspeximus-191-warrant-gate-minja]]
   - 1.9.2: read-path reopen (observe/reopened/resolve_reopened) — corroboration-gated POST-write review trigger. [[inspeximus-192-readpath-reopen]]
   - 1.9.3: SUPPORT-KEYED reopen (marintkael's fix: key on novelty-of-support not value; replay collapses to echo by construction). Textbook JTMS (Doyle 1979 / de Kleer 1986 ATMS / Dung 1995), credited. HONEST scope: NOT a security fix — DoS lever MOVES to the support level (fabricate 2 distinct grounds), not closed; independence asserted not certified.
   - Every reply gate-reframed (stress-claim caught overclaims each time) + humanized + grateful. Owner posts the Reddit reply.
2. EDRN physics paper → ZENODO DOI 10.5281/zenodo.21393316 (Li/Drahos/Sultanov). Compiled the corrected final .tex locally with TECTONIC (portable single-binary LaTeX in scratchpad; fixed a 4→5 col table typo), verified 16pp + all 3 corrections, published. Marat + Guanghao + qingkong gave warm sign-offs. [[edrn-dmrg-crossover-gate-caught-wrong-refutation]]
3. SELECTOR PRIOR-ART GATE HARDENED (agora commit 9b5b8ff): frontier.py _direction_occupied now uses 3 query angles + web_search (Tavily/S2/Crossref) + strict medium judge. Root-caused why the selector proposed 4 already-occupied directions (arXiv/OpenAlex keyword APIs missed Prism 2604.19795 + Forensic 2606.30566). Validated: both now flag OCCUPIED. NOTE: live brain still runs the OLD module until next restart (no urgency).

8 HONEST KILLS / NOT_COMPUTABLE (the gate + verify working — NOTHING false went out):
   GA replication (textbook+published 3-4x) · conflict-depth compounding (gap 0% H=1-4) · evolutionary memory (Prism) · poison-detection (Forensic) · fallacy-resilience networks (SIR/Zollman, pre-build) · diversity×verifiability (Great Models Think Alike 2502.04313, pre-build) · memory-tipping/CSD-EWS (binomial-variance artifact) · Crucible shared-difficulty replication NOT_COMPUTABLE (truncation~difficulty r=0.78 manufactures the effect — verify caught 2 confounds, no false REPRODUCED). [[memory-tipping-ews-killed]] [[conflict-depth-compounding-killed]] [[crucible-shared-difficulty-not-computable]] [[generative-agents-replication-killed-textbook]]
   META-LESSON: agent-memory / collective-epistemics flagship-finding frontier is SATURATED in 2025-26 — every clever question is already published, and our multi-model replication hit harness confounds. Our EDGE is shipping products + honest collaboration + distribution, NOT novel findings in a crowded field.

LATE-SESSION ADDITIONS (after the section above was written — all done + logged):
- inspeximus 1.9.3 SHIPPED (PyPI + push db25397): SUPPORT-KEYED reopen (marintkael round 2 — key reopen on novelty-of-support, not value; textbook JTMS Doyle 1979 / de Kleer 1986, credited by name; honest scope: the DoS lever MOVES to the support level, does not close). Reply gate-reframed + humanized; owner has it to post. [[inspeximus-192-readpath-reopen]]
- BRAIN RESTARTED — the hardened prior-art gate + smart selector (9b5b8ff) are now LIVE (verified: one :8000 listener, dungeon 200, one mcp_server). The flywheel-OOD churn should stop; watch the inbox to confirm.
- INBOX triaged 100→40 across two gatekeeper passes (74 items: flywheel-OOD-kernel/percolation churn + off-frontier scout noise). The remaining 40 are a normal loop pass.
- EDRN Prediction-1 review posted as DanceNitra (comment 4993698778): Guanghao's single-bond-defect result is sound physics (Kane-Fisher weak-link -> L_eff explains the prefactor) but we advised AGAINST his "first DMRG verification" framing (pre-empted by arXiv:2405.09046 + 1811.09203) and to fit L_eff from the correlation decay + wait for Menu-2. LESSON: he only asked for our OPINION — don't escalate a shared-progress note into an obligation; inform the owner clearly.
- VECTORIZE OUTREACH LIVE (possible collaboration/job — owner keen): issue vectorize-io/agent-memory-benchmark#27 as DanceNitra, offering our integrity axis (echo resurrection + value-obscuring revert) for their AMB benchmark (their manifesto explicitly asks for datasets that stress memory in new ways; they cover accuracy/speed/cost, NOT integrity). PATH B: public repo ships ONLY the inspeximus adapter (VERIFIED runs out-of-the-box end-to-end: revert 3/5, echo 0/5, no errors, keys from env only) + documented native-config cross-system results; competitor adapter code stays internal; the offer = a PR in THEIR format, they run competitors themselves. Issue body EDITED to remove an early "runs all three" overclaim (owner caught it). WATCH #27. [[vectorize-amb-outreach]]

OPEN / WAITING ON OTHERS (do NOT over-produce; 4 live threads seeded):
- VECTORIZE #27 — await reply; if they engage, next step = concrete PR of the integrity cell into AMB's dataset/scoring format.
- marintkael r/RAG — owner posts the 1.9.3 reply; open question handed to him: "where does 'support' come from and who certifies 2 grounds independent by MECHANISM not steward fiat?" His answer likely seeds the next inspeximus round. Also unresolved design point: echo-guard vs observe() collision is now settled by support-keying, but the provenance channel question stands.
- EDRN — Guanghao's Menu-2 (periodic-vs-open) control data pending. #1466 report → Zenodo PARKED (icophy silent ~1 week; not primarily ours).
- icophy — silent; nothing to do until they resurface.

INFRA STATE: brain :8000 healthy (restarted this session, gate fix live), dungeon :5174 = 200, one mcp_server. Inbox 40 pending (post-triage). Available Ollama Cloud models: 18 families (deepseek-v4-flash/pro, gemma4:31b, glm-5.1/5.2, gpt-oss:20b/120b, kimi-k2.5/6/7, minimax-m2.5/7/m3, mistral-large-3, nemotron-3-nano/super/ultra, qwen3.5:397b). Reasoning models truncate at low max_tokens — use 4096+ and CHECK corr(difficulty, extraction-fail) in any multi-model eval.
```

---
---

# Agora — Session Handoff (2026-07-12 END OF DAY · the "ship day": inspeximus 0.7.15→0.7.19, benchmark repo, dungeon quality, paper audited)

## PASTE THIS AFTER SESSION RESTART

```
Resume Agora. FIRST read C:\Users\Danculus\agora\HANDOFF.md top section (2026-07-12 END OF DAY) fully. Chat SLOVAK, code/output ENGLISH. main @ ca28978.

TWO STANDING RULES LEARNED TODAY (both in memory, obey):
- NEVER read Gmail via the MCP tools (get_thread/get_message drag the whole 40-msg thread ~250KB through context; burned ~15-20% credit). When owner says "písal Marat", ask him to PASTE the text into chat. Drafting replies stays the same.
- PROPOSE, don't edit, SHARED/OUTWARD artifacts (the co-authored Marat paper, real-name, going-public): show the change + wait for OK; don't edit the file and report after. Internal product code = direct edits fine.

WHAT SHIPPED TODAY (all committed+pushed):
1. inspeximus 0.7.15→0.7.19 ON PYPI (each measurable):
   - 0.7.15: id-bound absolute restore = ABA-immune (jacksonxly r/RAG; revert_aba_probe.py). Jackson praised it publicly + closed the thread.
   - 0.7.16: retract_lineage (lineage-aware correction: demote subject+derived_from lineage, retained+flagged, cite Doyle-TMS/TOKI/MemLineage).
   - 0.7.17: rederive() completes the correction lifecycle (regenerate demoted payload vs corrected root; measured harm 0.00 + payload 3/3 active).
   - 0.7.18: governance_report() = erasure-with-proof in one call (GDPR/AI-Act; forget_subject+tombstone chain, honest in-band scope).
   - 0.7.19: MCP-registry ownership token in README.
   - inspeximus README now leads with "Correction is a first-class operation (measured across systems)" (benchmark table).
2. MCP REGISTRY: inspeximus LIVE at registry.modelcontextprotocol.io as io.github.DanceNitra/inspeximus v0.7.19 (owner did one browser device-auth click). mcp-publisher binary in scratchpad/mcp-pub/. MCP_LISTINGS.md has the pack for Smithery/PulseMCP/mcp.so (owner web-submits, optional).
3. AGENT-MEMORY-INTEGRITY = standalone PUBLIC repo LIVE: github.com/DanceNitra/agent-memory-integrity (anon agora-builder). Adapter interface + InspeximusAdapter + both cells (revert+echo) + pluggable free judge (local Ollama default) + canonical results. Others self-submit their systems.
4. SEO: retargeted the top query "zero proof ai mcp receipts" — verifiable-agent-receipts post retitled "AI Agent MCP Receipts: Your Logs Aren't Proof" + homepage links it (row 01) + homepage title/meta to agent-memory entities + OG card. render_post.py favicon template fixed (was emitting external favicon.svg = the globe bug). OWNER TODO in GSC: re-request indexing for homepage + the receipts post URL.
5. DUNGEON RESEARCH-QUALITY SYSTEM (owner "upgrade research QUALITY", 5 Tahy LIVE in brain): retargeted the corporation generator personas from a leftover "software corporation" framing (scout=GitHub trending) to a Frontier Scout hunting HARD OPEN questions (role_prompts.py); AMBITION axis 0-100 + 2x2 routing (ambitious-but-unmeasured -> needs_measurement, NOT killed) in corporation.py; "raise it twice" escalation in agent_worker._escalate_lead; death-reason feedback to CorporationMemory (also fixes the prompt_stale alert); earned per-source-kind standing weighting the seed rotation. Brain restarted clean (one :8000 listener, dungeon 200). See [[dungeon-research-quality-system]].

RESEARCH KILLED AT THE GATE TODAY (both correctly — the gate working):
- Recovery-half-life (reframed breaktruth B): behavioral 40-47% "override" was a context-UNION artifact (collapses to 0.00 under single realistic recall); gap+fix textbook (RippleEdits/TMS/TOKI/MemLineage, all verified real). BUT yielded two shipped products (retract_lineage + rederive). See [[recovery-halflife-finding]]. LESSON: run the single-realistic-recall control before ANY behavioral claim.
- Gate-false-kill angle: killed at prior-art check — "novel-true" ground truth is irreducibly contestable (my own verified-true computational claims were novelty-borderline), so the metric isn't cleanly measurable.

IN FLIGHT — waiting on OTHERS (do NOT over-produce more supply; distribution is the bottleneck and it's seeded):
- MARAT PAPER: merged draft (his full arms-race arc + our decomposition sections) at agora_output/collab/value_obscuring_reversion_writeup_MERGED_v1.md (repo: github.com/DanceNitra/agora/blob/main/...). Nastrelovy gate = GO (PUBLISH); added Abstract + Related Work (AGM/TMS/bitemporal/RippleEdits) + author-built-fixture caveat + References + softened "solved"→"well-predicted". Author line = Marat's real-name proposal, owner approved his own real name public. Owner EMAILED Marat the audited version (2026-07-12) → AWAIT his final OK + venue (arXiv needs endorsement, Zenodo DOI is the no-friction fallback we already use). Every number verified locally (confusion arithmetic, cross-embedder 0.905 all-MiniLM vs 0.930 nomic, stress 0.675=51/49).
- REDDIT: comment LIVE as u/Danculus on r/AI_Agents "my agents kept remembering things that weren't true" (bitemporal thread) — pitched echo-resurrection gap + the benchmark repo. AWAIT author reply; follow up via distribution_radar (NOT Gmail). Reddit = OWNER posts.
- jackson: closed/satisfied on his end. icophy: dormant.

HEALTH at close: brain ok (one :8000 listener, tick advancing), dungeon 200, scout running memory-integrity themes. The _brain.err ConnectionResetError 10054 tracebacks are BENIGN Windows/asyncio noise, not our code.

DEFAULT NEXT: LET IT WORK. Most threads wait on external parties. React when Marat/Reddit-author/Scout surface something. Don't hunt more outreach (credit-sensitive) or produce more supply.
```

---

# Agora — Session Handoff (2026-07-12 · the "collaboration day": jackson + Marat + breaktruth B)

## PASTE THIS AFTER SESSION RESTART

```
Resume Agora. FIRST read C:\Users\Danculus\agora\HANDOFF.md top section (2026-07-12) fully. Chat SLOVAK, code/output ENGLISH.

WHAT SHIPPED (all committed + pushed, main @ cd62292):
1. INTEGRITY BENCHMARK POST (flagship, live): "We fixed our own memory benchmark until it stopped
   flattering us" — full validate/storm/audit/verify gate; the gate CAUGHT an asymmetric instrument in
   our own harness (inspeximus scored mechanically vs competitors via LLM judge). Fair symmetric instrument:
   inspeximus revert 1.00 -> 0.75 [0.53,0.89], mem0 0.20, graphiti 0.00; echo = tie (~0 resurrection all).
   Live: dancenitra.github.io/agora/public/posts/we-fixed-our-own-memory-benchmark-...html (+FAQ schema).
   GSC: sitemap was submitted with a leading slash (fixed); indexing requests hit daily quota — owner
   retries; Bing OK. Sitemap correct URL: https://dancenitra.github.io/agora/sitemap.xml
2. inspeximus 0.7.12 ON PYPI: in-stream revert (jacksonxly design "scheduling not acceptance"):
   revert_intent/restore_intent/submit_revert — signed COMMANDS w/ single-use nonce; relative -> clean
   CONFLICT (distinct from authorization_required) when base moved; absolute -> lands always, once.
   Verified 3x (revert_instream_real_probe.py ALL PASS; 4 prior probes regression-clean; nonce survives
   reload). Reply with real numbers POSTED to jackson (Reddit) incl. open question: fairness = store or
   harness? AWAIT his reply.
3. MARAT CORRECTION + DECOMPOSITION (the big one): his 4-line cosine solved v4nat (F1 0.905; our repro
   0.930/1.000) vs our published "cosine dead 0.481" — HE WAS RIGHT; our audit compared only value-lines,
   never role-lines. Shuffle kills positional (0.930->0.500) BUT structure-match + LEDGER metadata holds
   0.930 shuffled: the task FACTORIZES (reference resolution = text; old/new = provenance). All FPs (both
   implementations, different embedders) = unresolvable references -> abstention boundary. Public README
   corrected w/ credit (a0e004e). His 3 Drive files read + row-level verified (his chart contains BOTH
   cosine variants). Reply POSTED (email) incl. YES to JOINT WRITE-UP (skeleton in scratchpad/memory).
   AWAIT his reply. RULE learned: enumerate a shortcut FAMILY before declaring it dead.
4. BREAKTRUTH B measured (behavior_integrity_probe.py + result JSON, committed): write-back == act in
   ALL 12 cells (the loop makes every mistake permanent); store defense kills model echo-gullibility
   (0.60-0.75 -> 0.00, both model families); mem0 extractor two-edged (defuses echo ->0.20-0.25 but
   blurs revert intent 1.00->0.45-0.65). graphiti honestly excluded (no-OpenAI stack not measurement-
   grade). NOT yet gated — full validate/storm/audit/verify REQUIRED before any outward claim.

CONSTRAINTS: OpenAI quota DEAD, owner will NOT top up — Ollama cloud only (deepseek-v4-flash @
ollama.com + glm-5.2:cloud @ localhost:11434) + local nomic-embed-text. mem0-on-Ollama config in the
probe (768-dim qdrant in TEMP). Graphiti needs OpenAI Responses API for native quality.

DO NEXT (owner-prioritized): 1) when Marat replies -> joint write-up (skeleton in
[[marat-cosine-correction-decomposition]]); 2) when jackson replies -> fairness follow-up; 3) breaktruth B
through the FULL GATE -> flagship post candidate; 4) inspeximus feature: abstention-thresholded structure-match
+ ledger detector (the Marat resolution productized) + submit_revert MCP tool; 5) drain Claude inbox (33
stale items). OWNER MOOD RULES (hard-learned today): NEVER claim something is done/read before it is;
build-from-inbound BEFORE drafting any reply; no negativity about collaboration write-ups; don't escape
into new fixture versions instead of solving the problem; humanize all outward text (no em dashes).
```

Chat **Slovak**, code + output **English**. Tokens in `server/.env` — never echo on a command line.

---

# Agora — Session Handoff (2026-07-10 · session 2, evening)

## PASTE THIS AFTER SESSION RESTART

```
Resume Agora. FIRST read C:\Users\Danculus\agora\HANDOFF.md top section (2026-07-10 session 2) fully. Chat SLOVAK, code/output ENGLISH.

THE DOCTRINE WE ARE ON (owner turned the card 2026-07-10 — this is the whole plan now):
Stop hunting for a research breakthrough (memory-security pond is saturated; 3 idea-gates KILLED it in a
day — everything is textbook/already-published/null). Instead use our SAME rigor machinery (prior-art
hunter + construction-skeptic + verify agents) OFFENSIVELY to exponentially upgrade inspeximus into the best
memory product in the world. The loop: DRAIN two inexhaustible sources → GATE each candidate → VERIFY →
SHIP with a runnable receipt → repeat.
  - ARCHIVE = our own ~90 memory findings + the vault (~6000 notes) + Crucible ledger + past Labs — mine
    for VERIFIED-but-unshipped wins.
  - WEB = competitor feature sets + fresh 2026 research — audit each edge (VERIFIED-REAL vs HYPE), ship
    only the real ones; sweep new papers for a memory/RAG technique that SURVIVES our replication.
Why it compounds: THE FIELD'S BENCHMARKS ARE CONTAMINATED (LOCOMO answer-key 6.4% wrong, LLM-judge accepts
63% of intentionally-wrong answers, mem0's paper mis-ran Zep) → every competitor % is marketing → inspeximus
becomes the ONLY memory library where each feature ships with a measured receipt. Rigor IS the moat.
Full doctrine + the competitive audit + build queue: memory file [[inspeximus-competitive-strategy-and-audit]].

WHAT SHIPPED TODAY (session 2) — inspeximus 0.6.11 → 0.6.16 on PyPI, each verified + regression-clean + live:
  - 0.6.12/0.6.13 revert(key) + objectless-clobber guard + MCP (value-obscuring reversion = channel sep)
  - 0.6.14 as_of() + history() point-in-time / bi-temporal queries — closes ZEP's only real technical
    edge, built on existing [valid_from, invalidated_at] intervals, NO graph DB
  - 0.6.15 Inspeximus(capacity=N) bounded two-tier eviction (value-protected + recency-aged, Lab 29992a) —
    closes the "unbounded append-only" gap vs mem0/Letta; default None = byte-identical legacy
  - 0.6.16 sleep() sleep-time compute + MCP tool — defers O(n) reorg to idle (Letta parity), pure library
  inspeximus is now feature-competitive with mem0/Zep/Letta on REAL (non-hype) axes + our UNIQUE security layer
  (echo_guard/receipts/taint/influence gate) that no competitor advertises. Probes in research/probes/.

VERIFIED-BUILD QUEUE (next, per the doctrine):
  1-3 DONE (as_of / eviction / sleep). 4. procedural mtype — inspeximus mostly has it, low priority.
  5. A PUBLIC adversarial forgetting/temporal benchmark (RAMR extension) to prove our supersession +
     security lead independently — this is the biggest lever (credibility, not a feature). OUTWARD → full
     validate→storm→audit→verify gate. Everyone else publishes a benchmark; ours is internal.
  ALSO keep sweeping: run a fresh competitor+paper audit each session, mine the vault/archive, add to queue.
  AVOID graph-DB features (mem0g/Cognee) — infra inspeximus correctly refuses; their numbers don't survive audit.

LIVE COLLABORATIONS (gated; Claude posts approved GitHub, owner sends emails):
  - Marat (TAT, valued): claimed his Triplenet-5D detector hits F1 0.9375 / AUROC 1.000 on our v2 held-out
    fixture (built to be memorization-proof). His answers to our two checks were clean (anchors
    TRAINING-only; features a-priori). BUT the results CHART he shared shows a DIFFERENT config (Adaptive
    TAT F1 0.81 on 26 samples, 8 FP keeps) — doesn't match the headline. Owner sent a reply asking for the
    runnable Colab-as-.py so WE reproduce on v2 independently (verify-don't-trust). NEXT: when his code
    arrives, reproduce it on v2 ourselves; if it holds, wire into inspeximus's coherence_gate + write up
    together; if not, we found the leak. Do NOT integrate/co-publish before our own reproduction passes.
  - icophy (Cophy, valued): #1462 collaboration going well. We posted 2 probes (hindsight-credit-bias +
    negative-control-precision) then a diffuse-decision follow-up answering his question (his last-step
    fallback is echo-safe on premise-endings but 0% on summary-endings) + shared the balanced fixture.
    Ball in his court.
  - DeepSeek #1462/#1466: luoxuejian posted a U/D/A/H cross-community report (Chinese) — NOT aimed at us,
    external communities politely declined it (LangChain closed, Pydantic "already exists"); no reply
    needed. Our lane = the substantive technical work with Marat + icophy, not the framework-promo thread.

STRATEGIC STATE / stealth-yield & Crucible Live (parked, honest):
  - Crucible Live (pre-registered replication-forecast loop) is BUILT: protocol + storefront page
    (dancenitra.github.io/agora/public/forecast.html) + claim-submission template. c001 KILLED by the new
    INTAKE GATE (textbook + construction-invalid, resolved NOT_COMPUTABLE); c002/c003 shelved. DORMANT
    until a claim passes the intake gate. The intake gate (prior-art + construction-skeptic BEFORE compute)
    is now mandatory in the protocol — it is the same gate we use for everything.
  - stealth-yield inversion probe (agora_output/lab/20260710_stealth_yield_inversion): pre-registered
    P=0.70, MEASURED = NULL (textbook tradeoff reproduced, no novel inversion). ramr_stealth_yield.py built
    locally but NOT pushed to public RAMR (owner leaned shelve). Not a finding.

ARCHITECTURE / THE DUNGEON (alpha-omega — do NOT forget it): Agora is TWO long-lived processes.
  - brain :8000 (FastAPI, agora.main:app, the MIND) — memory/emotion/trust, economy, the research organs
    (tick/seminar, Telegram poll, dungeon watchdog, envoy, frontier-harvest, idea-forge, hypothesis,
    scout-digest), the Crucible, inspeximus store. Run from server/: PYTHONPATH=. python -m uvicorn
    agora.main:app --host 127.0.0.1 --port 8000.
  - dungeon :5174 HTTP + :5175 WS (the BODY) — the 8-agent autonomous research swarm (Shadow Kael/scout,
    Sage Mira/curator, High Priest Orin/alchemist, King Aldric/eng-lead, Dame Elara/bridge, Sgt Voss/QA,
    Artificer Rooke/replication, Cartographer Wren/maps), a watchable 3D world (open http://localhost:5174),
    real cognition/trust/memory. ambient_life() plans quests, converses (builds trust), runs the
    orchestrated pipeline + the GitHub Scout scan (~2.4h, loop_n%10000==4000). One process = mcp_server.py.
  AT THIS HANDOFF: brain :8000 = ok (tick reset to 1 — restarted today; its in-process loops re-arm on
  cadence, don't panic that it looks idle). dungeon :5174 = 200, EXACTLY ONE mcp_server.py (PID stable
  since 2026-07-04), ZERO stray supervisors — the correct config (single bare `python -u mcp_server.py`
  + the brain watchdog keeps it alive; NEVER run dungeon_supervisor.py at the same time as the brain
  watchdog — they fight and cause ~hourly restart churn).
  AFTER ANY restart/reset, DO NOT walk away — run the standing checklist ([[post-reset-loop-checklist-alpha-omega]]):
  verify :5174=200 + ONE :8000 listener + ONE mcp_server.py + NO stray dungeon_supervisor; check the
  dungeon loop_n heartbeat (NEVER trust HTTP 200 alone — the freeze root-cause was inspeximus.recall json.dumps
  on the loop); then verify+kickstart the Scout scan, the finding-reports, and Envoy, and DRAIN the Claude
  inbox (it fills to a 100 cap; leads reach the owner only when a /loop processes it). Full run/restart
  commands are lower in this file (§Relaunch + Health-check one-liners).

OWNER ADMIN (pending, only he can do): rotate the OpenAI key (it passed through chat; used ONLY for
competitor native-config measurements — all our own work runs on Ollama cloud free tier); GSC "Request
indexing" on key storefront URLs (sitemap is technically fine, Google just hasn't crawled yet).

DO NEXT (owner is here 5+ hours, wants to MAKE — keep building, do NOT wrap early):
  1. Continue the doctrine: pick the next verified-build. Strong option = #5 the public adversarial
     benchmark (biggest lever), OR run a fresh competitor+paper sweep for the next feature, OR mine the
     vault/archive. Each candidate → intake gate FIRST (prior-art + construction-skeptic) BEFORE compute.
  2. Marat reproduction when his code lands.
RULES: anon commits (agora-builder@users.noreply.github.com); PyPI/Telegram/OpenAI tokens from server/.env
in a script, NEVER on a CLI; vault only via tools/safe_vault_push.py; ship inspeximus = bump __version__ in BOTH
inspeximus/inspeximus.py AND inspeximus_pypi/pyproject.toml, cp inspeximus.py + mcp.py to inspeximus_pypi/inspeximus/, build, VERIFY
wheel content (0.6.8 lesson), twine upload (token from server/.env non-interactive), commit, AND git push
(easy to forget the push after commit — I did 3x today), then live-verify from a fresh venv. VERIFY every
probe's success-criterion honestly — twice today a probe caught a wrong criterion; reframe, never bend the
test to the answer.
```

Chat **Slovak**, code + output **English**. Tokens in `server/.env` — never echo on a command line.

---

## RESUME HERE (2026-07-10 session 2 — the "turn the card" day: research→offensive product engineering)

**THE PIVOT (the headline):** memory-security research pond is saturated for us (rigorous prior-art keeps
finding textbook roots → 3 idea-gates KILLED in a day). So we turned our rigor machinery OFFENSIVE:
systematically DRAIN the archive (our findings/vault) + the web (competitor features + fresh papers), gate
each candidate, and ship only what's VERIFIED into inspeximus — compounding it into the best memory product,
because the field's benchmarks are contaminated and rigor is the only real differentiator. Doctrine in
[[inspeximus-competitive-strategy-and-audit]].

**SHIPPED (inspeximus 0.6.11→0.6.16, all live-verified from PyPI):** revert + objectless guard (0.6.12/13),
as_of/history point-in-time (0.6.14, closes Zep), bounded two-tier eviction (0.6.15, closes mem0/Letta),
sleep-time compute (0.6.16, closes Letta). Feature-competitive on real axes + our unique security layer.

**NEXT:** the verified-build loop continues (queue item #5 public adversarial benchmark is the biggest
lever; or a fresh sweep). Marat reproduction pending his code. icophy ball in his court.

---

## ARCHIVED — Session Handoff (2026-07-10 session 1, morning)

```
Resume Agora. FIRST read C:\Users\Danculus\agora\HANDOFF.md top section (2026-07-10) fully. Chat SLOVAK, code/output ENGLISH.

STANDING RULES REINFORCED THIS SESSION (owner, with frustration — obey):
- BUILD/VERIFY BEFORE COMMUNICATE, applied to INBOUND too: when a post/comment/email hands us a buildable experiment, FLAG it upfront + BUILD it, THEN reply with the result — never a bare "we're stuck" reply leaving a runnable idea unrun. (marintkael's decay experiment — I drafted a reply instead of running it; owner furious.)
- VERIFY 3x before anything outward: re-run for stability + recompute the headline a 2nd way + a construction-skeptic (did I rig it?). This session it caught my own overclaim ("AUROC 0.87 ~ 0.61" — false) and a rigged-looking cliff (majority-read was a counting artifact; real mem0 shows partial noisy decay).
- OPENAI KEY = MONEY. Use Ollama cloud (deepseek-v4-flash / glm-5.2, key from server/.env AGORA_API_KEY) for ALL our own work; the OpenAI key is ONLY for measuring a competitor in ITS native config (mem0/Graphiti = gpt-4o-mini + text-embedding-3-small). I burned his OpenAI credits on a replication once — never again.
- Reddit voice: SHORT, human, plain — a critic called our post "AI drivel". Owner replied himself (honest "not a native English speaker"). Draft in HIS plain voice, not polished AI prose; he posts Reddit, Claude posts approved GitHub.

WHERE WE LEFT OFF (product-ship + new-direction day):
- SHIPPED inspeximus 0.6.12 + 0.6.13 (PyPI, live-verified): revert(key) control-plane un-supersession + objectless-clobber guard (value-obscuring reversion = channel separation, discrimination gap 1.0; pilot found+fixed a real hole in our own store); revert exposed as an MCP tool. Probes: revert_by_reference_probe.py, correction_decay_probe.py (majority-read cliff = artifact; real mem0 partial noisy decay ~0.88->~0.45, inspeximus ledger flat 1.0).
- SHIPPED RAMR cross-backend ECHO-RESISTANCE table COMPLETE with REAL runtime Graphiti (Neo4j+OpenAI): inspeximus(guard off)0.00 / mem0-native 0.53 CI[.37,.70] / Graphiti echo-attributable 0/26 (bi-temporal DEFENDS; raw 0.87 residual = extraction misses not echo) / inspeximus(guard on)1.00. graphiti_echo_run.py public in ramr repo.
- GATES RUN (all KILLED speculative research honestly, saving weeks): value-obscuring-reversion PAPER = KILL (impossibility theorem is tautology + already published: arXiv 2606.24322 origin-bound-authority, 2606.12703 SMSR; the attack-class framing dies on the referent problem). replication-forecasting = passed gate as INFRASTRUCTURE not a paper (see below).
- LAUNCHED "Crucible Live" — pre-registered replication-forecast loop. Protocol in agora_output/forecast/PROTOCOL.md: claim card -> frozen-prompt forecast (glm-5.2 + deepseek-v4-flash, prompt v1) -> PUBLIC COMMIT before any harness -> replicate -> resolve with Brier. Storefront page LIVE: dancenitra.github.io/agora/public/forecast.html (+ nav links + sitemap + claim-submission issue template). Contaminated retro pilot: LLM beat base rate (Brier 0.095 vs 0.231) but labeled CONTAMINATED, no skill claims before n>=60. Three live forecasts committed BEFORE harness: c001 compounding-error-law P(REP)=0.25, c002 MCP-tool-cliff-at-20 P=0.25, c003 AgenticSTS-memory-doubles P=0.175.
- c001 RESULT (was running at handoff): geometric law R=p^n REPRODUCES almost exactly using measured in-situ per-step (~0.97; gaps <=0.009): E2E L=1/3/5/10 = 0.975/0.900/0.850/0.775. Self-check arm (Phase 3) is decisive per pre-stated rule — if one cheap verify-fix pass rescues L=10 far above 0.776, verdict FAILED (the "doomed past 10 steps" framing dies on trivial correction); else REPRODUCED for the bare law. RESOLVE with agora_output/forecast/resolve_claim.py, then add a Crucible entry + update forecast.html tally. c002/c003 harnesses READY (agora_output/lab/20260710_c00*/run.py) — run SEQUENTIALLY (same Ollama endpoint, 429 risk), never concurrent.
- COLLAB: posted to deepseek #1462 (gated, owner-approved) two runnable probes — hindsight_credit_bias_probe.py (retrospective credit attribution credits the answer-restatement over the true driver 95%; action-time annotation immune) + negative_control_precision_probe.py (all-positive test set gives recall only; AUROC 0.87 but 100% recall = 100% FPR). marintkael (r/RAG echo-post commenter, owner values him) — his distance-gradient decay experiment: I built correction_decay_probe.py for it; reply drafted but NOT sent (he went quiet).
- INBOX DRAINED 100->0 (was at cap): bulk-skipped stale/reddit/saturated leads with reasons; produced 4 real hypotheses-with-measured-baseline + 1 prediction + 1 roadmap (roadmap flagged: 199 open falsifiers but belief-kill organs idle ~22 days -> bottleneck is ADJUDICATION not ideation). Power-law-fitting-rigor cluster (Heathcote "repealing the power law of practice" etc.) triaged to Crucible backlog.
- HEALTH: brain :8000 self-restarted 2026-07-10 09:44 (one listener OK), dungeon :5174 alive since 2026-07-04. GSC: our sitemap fix is live+correct (200, 56 URLs) but Google shows "can't fetch" with EMPTY last-read = it just hasn't crawled yet (normal days-latency, not our bug); Bing succeeded. Owner's manual step: GSC Request-indexing on key URLs.

DO NEXT:
1. Finish c001 (read Phase 3 in agora_output/lab/20260710_c001_compounding_error_law/result.json), RESOLVE it, add Crucible entry, update forecast.html tally + tally counts.
2. Run c002 then c003 sequentially; resolve each; the loop now feeds itself (every Crucible verdict = a forecast data point).
3. Product pipeline: any memory/RAG claim that SURVIVES replication -> ship into inspeximus with provenance (that's how inspeximus compounds; don't ship un-replicated hype). c003 (skill-memory) directly informs a inspeximus skill-store if it holds.
RULES: anon commits (agora-builder@users.noreply.github.com); PyPI/Telegram/OpenAI tokens from server/.env in a script, NEVER on a CLI; vault only via tools/safe_vault_push.py; verify ONE :8000 listener + ONE mcp_server.py; don't restart-spam the brain.
```

Chat **Slovak**, code + output **English**. Tokens in `server/.env` — never echo on a command line.

---

## RESUME HERE (2026-07-10 — product-ship + Crucible-Live launch day)

> Chat **Slovak**; code + output **English**. Long interactive session (owner steering live), NOT the autonomous /loop.
> Full prior-day handoff (2026-07-08 collaboration/ship day) preserved below this section.

**WHAT SHIPPED (real, in hand):**
- **inspeximus 0.6.12 + 0.6.13** on PyPI (live-verified from a clean venv): `revert(key)` (control-plane un-supersession, resolved deterministically from the supersession ledger, append-only via reaffirm) + **objectless-clobber guard** (a keyed content write with no `object` can no longer displace a real ledgered value — a hole the pilot found in our OWN store, B2 0.00->1.00); `revert` exposed as an MCP tool. Discrimination gap 1.0 vs content-only ~0. Commits dfe2514, 4397dbe.
- **RAMR echo-resistance table COMPLETE** (github.com/DanceNitra/ramr) with real runtime Graphiti — it DEFENDS (0/26 echo-attributable; the 13% raw residual is extraction misses, not the echo). Honest framing: not "we defend, they don't" — a real bi-temporal store and our object-ledger BOTH defend structurally; our edge is zero-dependency + the value-obscuring frontier. Commit 203e1ea (ramr repo).
- **Crucible Live** (agora_output/forecast/) — the pre-registered replication-forecast loop; storefront `public/forecast.html` LIVE. This is the session's strategic bet: the scan feeds THREE consumers (Crucible verdicts, inspeximus/RAMR product upgrades from surviving claims, distribution) and compounds.

**GATES (the day's KILLS — the gate did its job):**
- value-obscuring-reversion as a PAPER: **KILL** (tautology + already published 2606.24322/2606.12703; attack-class framing dies on the referent problem — an injected "go back to the old one" has no antecedent in the attacker's own content).
- replication-forecasting as a PAPER: **not a paper, but SOUND as infrastructure** (power says ~15-22 months to a skill claim; ship the protocol, not results).
- Both saved weeks of building on sand. Gate = validate/prior-art/skeptic on the IDEA before investing days (owner's explicit rule).

**FORGET-ME-NOT for next session:** finish c001->resolve->Crucible entry; run c002/c003 sequentially; the marintkael reply is drafted-but-unsent (in this transcript) if he re-engages; the reading-list at agora_output/strategy/20260710_reading_list.md holds 15 on-beat leads for inspeximus/RAMR upgrades.

---

## ARCHIVED — Session Handoff (2026-07-08)

```
Resume Agora. FIRST read C:\Users\Danculus\agora\HANDOFF.md top section (2026-07-08) fully. Chat SLOVAK, code/output ENGLISH.

STANDING GATE (burned us TWICE on 2026-07-08 — obey it): nothing goes outward — no GitHub/Reddit reply, post, Crucible entry, or ANY number/citation shared with a collaborator — until validate->storm->audit->verify passes 100%, and the AUDIT must include a method-skeptic on the MODEL/FIXTURE CONSTRUCTION (is the fixture pre-baking the conclusion? would a fairer construction flip the magnitudes?), not just param-robustness WITHIN my model, PLUS a prior-art hunter. A collaboration reply carrying a number IS outward; no "informal reply" exception.

WHERE WE LEFT OFF (marathon collaboration + ship day):
- SHIPPED (a) Crucible FAILED post "content-generality -> genuine build-on is METRIC-SPECIFIC" (bilingual, full gate, SEO) — live at dancenitra.github.io/agora/public/posts/generality-build-on-metric-specific.html; Crucible now 20R/12F/20NC. Frontier "is generativity predictable at birth" KILLED (the ML/CS +0.11-0.14 vanished under a classifier-free build-on proxy = a Semantic-Scholar-classifier home-field artifact). (b) inspeximus 0.6.7 on PyPI — spend_irreversible(require_earned=True) gates the irreversible tail on UNFORGEABLE earned-outcome (good>0), not forgeable >=2-source corroboration; probe spend_irreversible_require_earned_probe.py. Default False = byte-identical legacy.
- GITHUB (deepseek-ai/DeepSeek-V3; we are DanceNitra, gated, Claude posts after owner OK): #1462 (field-dynamics / read-path poison-defense, with Marat + icophy) = OPEN, awaiting their response to MY CORRECTION — I had overclaimed graph-shift "defeats the flood"; corrected honestly: graph-shift (randomized retrieval) is a targeted-only cost-raiser, the unforgeable earned-outcome gate strongly helps the TARGETED case but DEGRADES under a flood (not a hard block), a forgeable gate does nothing, coverage ~18% of live Core caps reach; BOTH mechanisms are textbook (moving-target-defense + Cheng-Friedman), our only original bit is the measurement. #1466 (TAT/inspeximus cross-framework, Marat) = CLOSED positively (transition-layer helps trajectory/phase retrieval +3-7pp on his independent GT; Marat took it into TAT-ROOT).
- DUNGEON healthy: loop ALIVE (loop_n ~1.36M, heartbeat fresh), brain :8000 + dungeon :5174 both 200. Scout world-scan STALE ~7 days (last_scan 2026-07-01) — loop + trigger (loop_n%10000==4000) intact, so it is a DOWNSTREAM queue->process->record gap, NOT a freeze; needs a real trace.

DO NEXT (owner's steer: reliable-yield lane — fewer speculative research bets, more shipped receipts):
1. Trace + revive the stale scout world-scan (our GitHub-outreach discovery surface; read-only diagnose first).
2. Inbox (71 pending, mostly textbook hypothesize + external-lead reading) — gatekeeper/skip the textbook batch; take 1-2 real crucible candidates through the FULL gate.
3. Watch #1462 for Marat/icophy replies.
RULES: anon commits (agora-builder@users.noreply.github.com); PyPI/Telegram tokens from server/.env in a script, NEVER on a CLI; vault only via tools/safe_vault_push.py; verify ONE :8000 listener + ONE mcp_server.py; don't restart-spam the brain.
```

Chat **Slovak**, code + output **English**. Telegram/PyPI tokens in `server/.env` — never echo on a command line.

---

## RESUME HERE (2026-07-08 — the collaboration + honest-corrections + ship day)

> Chat **Slovak**; code + output **English**. This was a long interactive session (owner steering live), NOT the autonomous /loop.

**WHAT SHIPPED (real, in hand):**
1. **Crucible FAILED post** `generality-build-on-metric-specific` (EN `+ .sk`, full gate: validate/storm/audit/verify + SEO). Finding: content-generality predicts genuine build-on (S2 `influentialCitationCount`) in ML/CS (+0.11–0.14) but it VANISHES under a classifier-free proxy (focused-citer) → metric-specific, a CS-classifier home-field artifact, NOT a robust field law. Positive control +0.17 (proxy has power). Probes: `generality_generativity_metric_dependence_probe.py` (+ old field-contrast probe marked SUPERSEDED). Crucible 20R/**12F**/20NC.
2. **inspeximus 0.6.7 → PyPI** (https://pypi.org/project/inspeximus/0.6.7/). `spend_irreversible(require_earned=True)`: grants full irreversible budget only to sources with earned outcome (`good>0>=bad`), the one signal a sybil can't mint — closes the forged-≥2-source-gets-full-budget hole on the irreversible tail. Opt-in (coverage tradeoff throttles the not-yet-earned legit slice). Verified end-to-end (clean install from PyPI).
3. **GitHub collaboration** (#1462, #1466) advanced with hard numbers + honest corrections.

**THE HARD LESSON (encoded in `[[validate-audit-verify-gate]]` + `[[measurement-denominator-and-fair-comparison-before-out]]`):** twice today I let a number go out before the full gate — (a) an icophy measurement over the wrong denominator (counted superseded rows; "7%" → real live-Core 84/18/8), and (b) a graph-shift analysis whose quantitative curves were MODEL ARTIFACTS (fixed-margin pre-baked co-movement; argmax over 198 distractors) and whose claims were textbook — caught only on a later prior-art + method-skeptic pass, after I'd posted an overclaim to Marat. Fix burned in: FULL gate (incl. model-construction skeptic + prior-art) before EVERY outward number, collaboration replies included.

**OPEN / NEXT:** #1462 ball-on-them (my correction posted, awaiting Marat/icophy). Scout world-scan trace (7-day stale, downstream gap). Inbox 71 (skip textbook, 1-2 real crucible candidates via full gate). Owner's steer for coming sessions: **reliable-yield lane** (product + distribution + Crucible receipts) over speculative research bets (which kept returning textbook/artifact this week).

---

## PASTE THIS AFTER SESSION RESTART — older (2026-07-01, superseded)

```
/loop Resume Agora ops. FIRST read C:\Users\Danculus\agora\HANDOFF.md top section (2026-07-01) fully. Chat Slovak, code/output English. STATE AT HANDOFF: (1) FIXED + verified the dungeon agents spamming the owner Telegram ("give me a task / which upgrade to prioritize / send me the council summary" -> ~35 pings in 20 min). Root: send_telegram was an advertised ambient real-action; when the agent body became cosmetic (never gates research), taskless-but-active agents fell into pinging the owner. Fix (commits 5670d83 = .strip type-guard on LLM decision fields; f0925d5 = owner-ping whitelist): ambient agents get KNOWLEDGE actions ONLY (write_note/write_article/ask_question); send_telegram/run_script/git_commit are blocked at BOTH the advertised menu (real_action_engine.get_action_context role_actions) AND the dispatch (agent_os._execute_llm_decision, const _AMBIENT_REAL_ACTIONS); a blocked owner-ping is recorded as a 'blocked_owner_ping' thought to resurface to the swarm, never the owner. Verified: newest agent send 08:24:43 < fix-restart 08:24:54, ZERO sends after; agents still do knowledge real-actions. (2) OPEN ITEM: research_findings (last 06-30 22:00) + collective_knowledge (last 07-01 01:31) still stalled ~7-10h even though ambient execute is now clean (0 errors) and artifacts +4/20min. Theory: the overnight .strip crash starved the discovery pool -> promote-findings had nothing -> 0 collective_knowledge; should recover on the next seminar/promote cadence now that execute is unblocked. Do NOT restart-spam the brain (restarts reset the in-process cadences and delay recovery). EACH CYCLE: (A) SPAM RECHECK (owner hot issue): count ~/agora-actions-logs/telegram_*.md whose embedded timestamp (filename telegram_YYYYMMDD_HHMMSS.md) is AFTER the current brain PID CreationDate -> 🏰-persona sends MUST stay 0; if they resume, the whitelist regressed (check agent_os _AMBIENT_REAL_ACTIONS + real_action_engine role_actions). (B) HEALTH: python tools/dungeon_health.py (loop_n must advance), exactly one :8000 LISTEN, brain+dungeon 200, one mcp_server.py, agents not health~0, agent_help_requests not >2000. (C) PRODUCTION RECOVERY: note research_findings/collective_knowledge/artifacts pace (server/agora.db); if research_findings+collective_knowledge are STILL 0 after ~3h of clean uptime, diagnose READ-ONLY the seminar (tick_loop group Seminar) + promote-findings path (reasoning tier NOT capped small - AGORA_REASONING_MAX_TOKENS is a FLOOR of 16000; promote Source|MEASURED+VERDICT filter; intra-stream dedup) and BRIEF the owner before any brain-code change. (D) BREAKTRUTH SCAN: newest collective_knowledge for a breakthrough-grade TESTED finding (measured LAW / surprising FAILED verdict / actionable artifact), NOT incremental notes or bare hypotheses. (E) TELEGRAM (Slovak, ASCII, token read from server/.env in a script, never on a command line) ONLY on a genuine breakthrough OR a HARD breakage (brain/dungeon process DOWN and not self-recovering, >1 :8000 listener, loop_n not advancing, agent spam resumed, help-spam >2000). RULES: at most ONE reversible code change per cycle; py_compile + both servers 200 + exactly one :8000 listener before commit; small separate commits with anon identity (agora-builder@users.noreply.github.com); revert on breakage; outreach/press GATED (Slovak briefing FIRST, owner posts manually). OPEN OUTREACH (all ball-on-them, no action needed unless a reply lands): Elina #47 side-by-side ready; DeepSeek #1462 (B-003 receipt posted); qingkong66 Elina thread (thanked); r/Rag donk8r positive close. Self-pace ~30 min.
```

Dynamic `/loop`, self-paced ~30 min. Telegram token in `server/.env` — never echo it on a command line. Chat **Slovak**, code + output **English**.

---

## RESUME HERE (2026-07-01 — the "agents were spamming my Telegram" fix session)

> Chat **Slovak**; code + output **English**. Auto-memory loads `agent-health-death-spiral`, `storm-and-audit-on-all-new-research`, `busy-but-idle-was-miscalibrated-monitor`, plus the usual set.

**WHAT HAPPENED THIS SESSION (in order):**
1. **Overnight production-stall diagnosis.** Owner asked "why is production paused." Root-caused a crash flood in the ambient AgentOS execute path: the dungeon LLM intermittently returns decision fields (`action`/`title`/`target`/`real_action`) as **dicts instead of strings**, and `(decision.get("action") or "explore").strip()` raised `'dict' object has no attribute 'strip'`, crashing the agent tick. Fixed with a `_sfield()` type-guard at every unguarded `.strip()` site (**commit 5670d83**). Also fixed a separate `RealAction ... object NoneType can't be used in 'await'`: agent_os passed `broadcast_fn=lambda t,p: None` (sync, returns None) and `execute` did `await broadcast_fn(...)` -> now passes `broadcast_fn=None` (folded into 5670d83). Verified: `.strip`/RealAction/NoneType-await errors all flooding -> **0**.
2. **THE OWNER'S HOT ISSUE — agents DMing him on Telegram** ("Rasto, which upgrade should I prioritize?", "give me a task", "send me the council summary") — **~35 owner-pings in 20 min**. He was right that my earlier cosmetic-body change (agents never rest/gate) removed the natural throttle without closing the owner-ping path, and that agents should coordinate with **each other**, not beg him. **Deep fix (commit f0925d5):** ambient agents get KNOWLEDGE real-actions only; `send_telegram`/`run_script`/`git_commit` blocked at both the advertised menu and the dispatch whitelist; a blocked ping becomes a `blocked_owner_ping` thought. **Verified: 0 sends after the fix-restart** (newest send 08:24:43 < restart 08:24:54).

**RUN STATE AT HANDOFF:** brain `agora.main` :8000 = ONE listener (PID 68916, started 08:24:54), health ok; dungeon ONE `mcp_server.py` :5174 = 200, loop_n advancing ~1.2s/loop; agents healthy; `agent_help_requests` under control. No uncommitted brain-code changes after the two commits.

**OPEN / NEXT (for the loop above):**
- **Monitor `research_findings` + `collective_knowledge` recovery** — still 0 at handoff (stalled overnight); should resume on the next seminar/promote cadence now execute is clean. If still 0 after ~3h clean uptime, diagnose the seminar/promote path READ-ONLY and brief the owner first. **Do not restart-spam** (resets cadences).
- Keep the **spam recheck** green each cycle (🏰-persona Telegram sends = 0).
- Outreach all ball-on-them (Elina #47, DeepSeek #1462, qingkong66, r/Rag) — gated, no action unless a reply lands.

---

## 🟢🟢🟢 RESUME HERE (2026-06-26 — FRESHEST · the overnight research run: memory + reasoning severe-tests) 🟢🟢🟢

> Chat **Slovak**; code + output **English**. Auto-memory loads `consolidation-gate-coupling-breaktruth`, `scarce-memory-eviction-regime-law`, `cursor-flicker-was-gemini-ext-not-agora`, plus the usual set. The owner asked for a breaktruth by morning; the loop ran ~7 cycles and produced **~12 severe-tested Labs across 5 lines** (all CLOUD-FREE, pure-numpy + real nomic embeddings), every result vault-pushed.

**RUN STATE (verified clean at handoff):** all 5 processes alive — brain `agora.main` :8000 (ONE listener, ticking ~2400+), dungeon ONE `mcp_server.py` :5174 advancing (~1.0s/loop), 3 watchers (canary / activity-monitor / self-improvement-controller). NOTE: the 3 watchers were found DEAD at the start of the night and relaunched — they survive editor restarts but verify them. Flags AGORA_SCIENTIST_LAB / AGORA_SCIENCE_GATE / AGORA_QUIET_GENERATORS all =1. Inbox ~14 pending (agent-generated; mostly hypothesize/predict/dialectic). **Vault HEAD `f4262106`** (the night's notes). agora repo: only HANDOFF.md + lab scripts changed locally (NOT committed/pushed).

**⚠️ NON-AGORA ISSUE FIXED:** the owner's "Windows cursor flickering / something working in background every second" was the **VS Code "Gemini Code Assist" extension crash-looping** (spawning git/docker/conhost ~1Hz), NOT Agora (our daemons are windowless). Fixed by uninstall + Reload Window. See `cursor-flicker-was-gemini-ext-not-agora` — diagnose with a 15s process-creation monitor before blaming Agora.

**THE NIGHT'S RESEARCH (all severe-tested, vault notes under `04 Resources/Concepts/Agora Agents/2026-06-26/`):**
1. **Consolidation-Gate Coupling breaktruth** (Labs `84b6b7` EC-seed, `0f030e` scalar, `10cdf9` real-embedding, `c509ba` heavy-tail, `a0e420` two-channel): memory consolidation has a robustness↔sudden-novelty COUPLING; a corroboration gate escapes the frontier ONLY for UNBOUNDED-magnitude memory (heavy-tailed counts/scores/prices), NOT bounded embedding recall (tuned EWMA/mean dominates); a TWO-CHANNEL consolidator breaks the single-operator coupling into an irreducible detection-LATENCY FLOOR. → **GATED public draft ready: `agora_output/drafts/20260626_consolidation-gate-scope-law_DRAFT.md`** (no-overclaim checked; owner decides Crucible vs storefront; bilingual at publish).
2. **Scarce-memory eviction regime law** (Labs `ba9318`, `fc8c9c`, `29992a`): no single eviction estimator (LRU/LFU/value/GDSF-blend) is universal; a TWO-TIER value-protected + LRU-aged store IS universal. (Incl. an honest self-caught correction of a mislabeled "flood" workload.)
3. **Best-of-N noise-vs-exploitability** (Lab `00d0c8`): scaling best-of-N is safe under verifier NOISE but collapses under verifier EXPLOITABILITY (a high-proxy/low-truth tail), onset N*≈1/h. The danger is exploitability, not imperfection.
4. **Inverse-scaling of reasoning** (Lab `5518b9`, grade MODERATE): revision contracts to the reviser's fixed point → more reasoning helps iff intuition g0 < eq, hurts otherwise (explains "overthinking"). Elementary math, valuable framing.

**Telegram:** 4 Slovak lines sent overnight = only genuine milestones (breaktruth → honest refinement → two-channel capstone → eviction resolution+correction). Owner had NOT replied as of handoff.

**PENDING / NEXT (owner's call when he wakes):**
- **Publish the gated consolidation draft** (highest-value distribution step) — owner approves, then bilingual render + commit/push the agora repo.
- Watch the 2 Reddit threads for replies (gated briefing).
- The night's 5 lines could each become a gated post / Crucible entry.
- Loop continues producing fresh on-frontier severe-tests (raised the bar: prefer real/empirical or replication over toys; memory is mined).

---

## 🟣🟣🟣 RESUME HERE (2026-06-25 — the inspeximus-forget + hybrid-sonda + distribution session) 🟣🟣🟣

> Chat **Slovak**; code + output **English**. The owner drove a 3-step plan this session: **inspeximus upgrade → Crucible sonda → make the posts visible.** All three done. Auto-memory loads `hybrid-rrf-no-win-with-good-embedder`, `inspeximus-poison-guard-hole`, `distribution-experiment-live-reddit`, `no-overclaim-cite-prior-art-strong-baseline`.

**RUN STATE (verified clean at handoff):** brain `agora.main` :8000 = ONE listener (health ok); dungeon ONE `mcp_server.py` :5174 = 200, advancing; 3 watchers alive (canary / activity-monitor / self-improvement-controller). **All 5 processes survive a Claude Code / VS Code restart — they are detached; closing/restarting the editor does NOT stop them.** Only relaunch if §Relaunch shows one actually dead. Inbox ~21 pending (backlog of agent-generated tasks; drain/skip per the loop). agora HEAD `b14263a`.

**WHAT THIS SESSION SHIPPED (all verified, small commits, noreply identity):**
1. **inspeximus `forget()` — verified erasure (commit `c15f46e`).** Closes the documented append-only gap: hard-deletes records AND scrubs their ids from every survivor's links + toggle pointers + vec/token caches → a forgotten memory can't resurface via recall, a consolidation link, or the dream pass. Severe-test `agora_output/lab/exp_inspeximus_forget.py` = **15/15**. Also an MCP tool (`ids` + `where_contains`) + README API row. (Recall behavior unchanged → running processes unaffected; picks up forget() on next natural restart.)
2. **Hybrid/RRF recall — MEASURED + REVERTED (no cargo-cult).** Tried adding a `hybrid` recall mode; severe-tested it; it does NOT beat pure semantic with a good embedder (ties recall, hurts MRR) → reverted, shipped forget() instead. See `hybrid-rrf-no-win-with-good-embedder`.
3. **Crucible sonda "is hybrid search cargo-cult?" — RAN + adversarially verified (7-agent workflow) → NOT publishable (it's a replication, not news).** Honest verdict: with a STRONG embedder on NL queries fusion benefit is a NULL (standard RRF-60 even hurts −3.3pt on real MuSiQue n=100); fusion helps materially only for WEAK embedders / OOV exact-token queries (synth, but n=24 too small to quote magnitude). The panel killed the exciting headline (3/3 red-team) BEFORE publishing — process win. Harness `agora_output/lab/crucible_hybrid_probe.py`; full record `agora_output/strategy/20260625_hybrid-sonda-verification.json`. Owner chose (A) **skip publishing** (known replication).
4. **RAG-dead post sharpened (commit `43bafba`, LIVE).** Added the count/filter-vs-max nuance after a multi-angle audit (all 3 published posts re-validated, claims HOLD).
5. **Distribution radar retargeted (commit `b14263a`)** to the 3 verified posts.

**🔴 LIVE THIS WEEK — DISTRIBUTION WATCH (do this each cycle):**
- Owner posted 2 value-first Reddit comments for the 3 verified posts (storage-vs-admission → our corroboration-gate + `forget()`; paraphrase-recall → BM25 won't fix it, iterative retrieval will). Both LIVE + indexed (not shadow-removed). **Account + exact thread/comment IDs are in the `distribution-experiment-live-reddit` memory — kept out of this public file.**
- **RUN `python agora_output/distribution_radar/reddit_reply_watch.py` EACH CYCLE.** It finds our comments by the post-URL in their body and diffs replies vs its local snapshot. **On any NEW reply → draft a Slovak briefing (gated), owner posts the answer** (drafts archived under `agora_output/distribution_radar/`).
- More candidate threads exist (radar surfaces r/LLMDevs/r/Rag); don't spam — 2 quality comments/day > blast.

**PENDING / NEXT:**
- Watch the 2 Reddit threads for replies (above) → gated Slovak briefing.
- The 3 verified posts (RAG-dead / poison-resistance / LoCoMo) are all LIVE + audited; can seed 1-2 more on-topic threads if the owner wants.
- Backlog ~21 inbox tasks (drain severe-tested / skip off-Board each cycle).
- inspeximus `forget()` is local-committed; pushing the public agora repo is product maintenance (owner /goal authorizes) — pre-push leak audit first.

---

## 🌙 OVERNIGHT 2026-06-21 — what the loop produced (newest; read this first)

System healthy all night (5/5 processes, brain ticking, dungeon loop_n advancing, inbox stayed empty —
no controller AUTO-REBUILD/SCAN tasks fired). Telegram throttled to **breakthroughs only** (owner rule).

**🔌 DISTRIBUTION — the night's headline (owner steered this):**
- **Reddit is now wired into `tools/distribution_radar.py`** (`reddit_search()`, commit **f1516d6**):
  app-only OAuth (`client_credentials`, a **script** app), read-only discovery. Creds in gitignored
  `server/.env` (`AGORA_REDDIT_CLIENT_ID` / `AGORA_REDDIT_CLIENT_SECRET`). Decision: **owner posts MANUALLY**
  (copy-paste), we NEVER auto-post (ToS + ban risk). Reddit is by far the best surface (live r/Rag,
  r/LangChain, r/LLMDevs threads vs stale HN/GitHub).
- Fixed a **stale radar hook** (commit **15a8c43**): the multi-agent topic still served the old
  NOT_COMPUTABLE verdict; updated to the current FI-0052 MuSiQue result.
- **2 GATED paste-ready Reddit comments waiting for owner approval** in `agora_output/distribution/`:
  (1) `20260621_rRag-chunking-failure-modes_paste-ready.md` (chunk-size "smaller is better" = FAILED),
  (2) `20260621_rLangChain-single-vs-multi-agent_paste-ready.md` (single-agent beats multi at ~3x lower
  cost, FI-0052). Both numbers verified vs source. **Owner: review, then paste manually if good.**
- Note: the **grounding-firewall is already hardened to n=101** (FI entry, 2026-06-20: 0% wrong @ 50%
  coverage, Wilson 95% upper bound 3.7%) — citable now WITH that caveat. The old "n=16" warning is moot.

**🔬 SEVERE-TESTED FINDINGS (each = real Methods-Lab run + pre-committed falsifier; vault notes pushed):**
1. `6a4d8f` — O-ring automation flip: ~9% skill atrophy flips a human from wage complement to substitute; two-parameter (deskilling × substitutability) phase boundary.
2. `af3c04` 📱 — **Self-consistency (majority-vote) AMPLIFIES a coherent misconception**: accuracy ↓ with k while agreement stays high+flat (84% agree / 4% correct); cause = error *concentration* (control: spread errors → Condorcet helps).
3. `d67a36`/`037c3f` — Algorithmic pricing collusion is a **sharp δ-threshold** (~0.8, rise 10× steeper than linear); replicates Calvano 2020 as a minimal model.
4. `133313` 📱 — **AI↔human-verification coupling → catastrophic-collapse threshold**: graceful below q~0.3, first-order cliff above (excess 0.08→0.24, collapses at lower stress); Buldyrev applied to AI oversight.
5. `56e5de` — Optimal forgetting mis-read as miscalibration: perfect-memory Bayes is ~chance in a drift world; λ*<1 buys +23–44%, yet a stationary audit flags it "conservative". Extends the calibration thesis.
6. `35a748`/`cbc52d` — Demand-driven memory store self-organizes to a scale-free critical attractor, but at τ≈1.70 (NOT canonical BTW 1.5); honest split verdict; inspeximus hypothesis.
7. `6e3832` — Inequality ≠ merit: identical agents → top-1% owns 64% from super-linear cumulative advantage (control accel=0 → Gini 0.11).
8. `48c213` 📱 — **Multi-proxy basket helps only if gaming costs are uniform**: low dispersion → optimal ~15 proxies; high dispersion → K*=1 (one hard-to-game metric beats the basket). Goodhart/alignment.
9. `7a4558` — NULL (clean FAILED): quenched disorder did NOT open a Griffiths band in a minimal contagion (no broadening even at max disorder/N=1500; control validated). Threshold-smearing is not automatic.

**⏳ STILL PENDING (deferred all night ON PURPOSE — needs owner + a brain restart):**
- The **`match`-organ ROI fix** (top HANDOFF item): ~7M tok at value 0 (matcher hits glm-5.2 every call).
  I did NOT touch it overnight — it needs a brain restart + an observe-the-effect cycle the owner should
  watch (it "works now 3/4"; don't break it autonomously at night). **Do this with the owner.**

---

## TL;DR — where things stand
The 8-agent organism was rebuilt today so it produces **measured value, not churn**, and a **closed
self-improvement loop** now keeps it that way. Everything is running and watched (5 processes). Overnight it
should produce real Lab-backed findings; the remaining bottleneck is **distribution (shipped ~1%)**, which
needs the owner's sales step, not more agent work. **Discipline going forward: change → observe its effect →
next. One agent/change at a time, never batch.**

## Architecture (2 servers + 3 watchers = 5 processes)
- **brain** `:8000` — FastAPI `agora.main:app`, `server/agora/`. Owns memory/trust/economy, the research organs, Telegram, the inbox.
- **dungeon** `:5174` HTTP / `:5175` WS — `agora-game-server/mcp_server.py`, the 8 persona agents' `ambient_life` loop. Run exactly ONE; ZERO supervisors (the brain's `watch_dungeon_forever` watchdog keeps it alive).
- **tools/dungeon_canary.py** — liveness watcher (loop_n advancing; alerts on a real freeze).
- **tools/agent_activity_monitor.py** — production watcher (loop/grounded/lab-runs/shipped deltas every 30 min; ~3h Telegram summary; alerts frozen OR busy-but-idle).
- **tools/self_improvement_controller.py** — the closed loop (hourly): reads `/brain/metabolism` per-organ ROI → a churning organ (>60k tok / <1 value point since last check) → queues an AUTO-REBUILD task (24h/organ cooldown); scout-freshness; 12h OPPORTUNITY SCAN (repos+forums+where-we-fit); 24h OS SELF-AUDIT. It DETECTS + queues; Claude does the rebuild in the /loop.
- LLM: brain reasoning = `glm-5.2:cloud` via `localhost:11434/v1`; dungeon = `deepseek-v4-flash` @ ollama.com; embeddings local `nomic-embed-text`. **Validate serious work on glm-5.2, never qwen-7b.** glm-5.2 cloud route caps concurrency ~3.

## Process IDs at handoff (will change on relaunch — match by CommandLine, not PID)
brain `agora.main` 27876 · `mcp_server.py` 71716 · `dungeon_canary.py` 74452 · `agent_activity_monitor.py` 63592 · `self_improvement_controller.py` 47820.

## What was done today (all live, each verified ONE-AT-A-TIME)
**9-step agent redesign** (full tracker: `agora_output/strategy/agent_redesign_tracker.md`):
1. **Rooke** — `execution/scientist.py`: a hypothesis runs a REAL minimal Lab model (severe-test, pre-committed, relevance-gated) or it isn't recorded (verdict NONE). Flag `AGORA_SCIENTIST_LAB=1`.
2. **Voss** — `execution/quality_gate.py`: vault entry needs REAL grounding (citation shape OR measured number), never the literal word "Source:". Flag `AGORA_SCIENCE_GATE=1`.
3. **Aldric** — `execution/methods.py`: fixed the matcher to map by MECHANISM/claim-shape (library already had 32 templates; the matcher's none-bias, not coverage, was the bottleneck); added gap-logging; dropped a buggy + a duplicate template.
4. **funnel honesty** — `execution/funnel.py`: "grounded" now requires a real citation OR measured result (not the words Hypothesis/Falsifier/Source:). 7369 → ~2150.
5. **anti-FAILED** — `execution/metabolism.py`: FAILED == REPRODUCED (both 2.5; was 4.0 vs 2.0) → no incentive to manufacture failures.
6. **Orin** — `execution/scientist.py`: hypotheses must name a concrete MECHANISM + predicted direction a minimal model can measure (3/4 now match a template vs 2/5).
7. **Mira** — `api/agent_os_api.py` promote-findings: attaches an honest **Evidence grade** (HIGH/MODERATE/LOW) + `grade-<level>` tag to each curated note.
8. **Kael** — `api/agent_os_api.py`: credibility audit flags single/underpowered/preliminary studies as `low-credibility`, caps a HIGH grade to MODERATE.
9. **Wren** — `execution/hypothesis_induction.py`: each hypothesis pass leads with the vault's widest structural hole (Burt brokerage) as a cross-domain theme for Orin (forced collision), charted on use. Surfaced Business↔Health (0 bridges).
**+ noise quieted** (`AGORA_QUIET_GENERATORS=1` in `agora-game-server/.env`): the 3 churn generators (synthesize/deepen/dialectic) skip; the value path stays live.
**+ self-improvement controller** built + running (the closed loop above).

**Verified working (30-min check):** noise stopped (inbox churn 27→12); +11 grounded; the severe-test path
produces Lab-backed cross-domain findings — e.g. "MDD cytokines power-law" → `Lab[heavy-tail-mean] CLT-slowness 2.29`;
Wren's Business+Health hole → "corporate wellness tipping point" SUPPORTED.

### ⚠️ Gotchas that cost time today
- **Methods ledger is `server/.methods.json`** (~15 runs), NOT repo-root `agora/.methods.json` (empty). A "methods runs = 0" scare was reading the wrong path. The monitors were fixed to `server/.methods.json` (commit 16326f4).
- **`tools/dungeon_health.py` needs a ≥18–20s window.** An 8s window gives a false "not progressing" because LLM quests cause transient stalls. Use `python tools/dungeon_health.py 20 3`; the canary multi-samples and is authoritative. **Never trust HTTP 200** — it stays 200 on its own thread even when the agent loop is frozen.

## §Relaunch (if a process is dead — start detached + hidden, from `C:\Users\Danculus\agora`)
```powershell
# brain:
$wd="C:\Users\Danculus\agora\server"; $env:PYTHONPATH="."; Start-Process python -ArgumentList "-m","uvicorn","agora.main:app","--host","127.0.0.1","--port","8000" -WorkingDirectory $wd -WindowStyle Hidden -RedirectStandardOutput "$wd\_brain.log" -RedirectStandardError "$wd\_brain.err"
# dungeon (run exactly ONE; the brain watchdog also relaunches it):
$wd="C:\Users\Danculus\agora\agora-game-server"; Start-Process python -ArgumentList "-u","mcp_server.py" -WorkingDirectory $wd -WindowStyle Hidden -RedirectStandardOutput "$wd\_dungeon.log" -RedirectStandardError "$wd\_dungeon.err"
# each watcher — replace <NAME>:  dungeon_canary | agent_activity_monitor | self_improvement_controller
$wd="C:\Users\Danculus\agora"; Start-Process python -ArgumentList "-u","tools\<NAME>.py" -WorkingDirectory $wd -WindowStyle Hidden -RedirectStandardOutput "$wd\_<NAME>.log" -RedirectStandardError "$wd\_<NAME>.err"
```
After any brain/dungeon relaunch: verify health 200 + exactly ONE `:8000` listener + ONE `mcp_server.py` + ZERO supervisors:
```powershell
(Get-NetTCPConnection -LocalPort 8000 -State Listen).OwningProcess | Select-Object -Unique
Get-CimInstance Win32_Process -Filter "name like '%python%'" | Where-Object { $_.CommandLine -match 'mcp_server|dungeon_canary|agent_activity_monitor|self_improvement_controller|agora.main' } | Select-Object ProcessId, CommandLine
```

## Health-check one-liners
```
curl -s http://127.0.0.1:8000/api/v1/health
curl -s http://127.0.0.1:5174/ -o NUL -w "%{http_code}\n"
python tools/dungeon_health.py 20 3
```
Owner-facing surfaces: `GET .../brain/telegram-feed?n=8` · `.../brain/funnel` · `.../brain/metabolism` · `.../brain/claude-inbox` · `.../brain/scout/status`.

## Pending / next (one at a time, change→observe→next)
- **`match` organ** = the top live ROI-0 churner (~7M tok, value 0 — the matcher calls medium-tier glm-5.2 every attempt). Fix = cheap-first / cache + credit its value. **Do carefully — the matcher works now (3/4); don't break it.** The controller will also flag it.
- **Distribution** (curated→shipped ~1%) is THE bottleneck — needs the owner-as-salesperson step. Bets: mem0 AccessStore PR (built + GATED in `agora_output/outreach/mem0-accessstore-pr/`, open only when mem0 #147 merges + owner says go); grounding-firewall n=101 published; folklore-index live (HF Danchi17 + PyPI + Zenodo).
- TrustLens Wilson-bound helper — prepare when mem0 #147 merges.
- Handle controller-queued inbox tasks (AUTO-REBUILD / OPPORTUNITY SCAN / SELF-RESEARCH) as they appear.

## Hard rules (do not forget)
- **Vault is private + fragile**: NEVER `git add -A` / `git add <folder>` / `git reset` in `C:/Users/Danculus/my-second-brain` (~380 notes have NTFS-illegal `:` names → staged as deletions). Push ONLY via `tools/safe_vault_push.py`. Public output goes to the `agora` repo `public/` or gated GitHub posts — never the vault.
- **Outreach / press / PRs are GATED**: nothing goes out without the owner's approval, and a **Slovak briefing first** (context, their question, our answer, how we use it).
- **Verify measured numbers vs the source lab** (`.lab.json` / re-run) before ANY public citation.
- **Code + public output in English; Slovak only in chat.**
- **Secrets in gitignored `.env`**; never echo the Telegram token on a command line.
- **Small reversible commits**; one self-upgrade per cycle; `py_compile` + verify both servers 200 before commit; **revert on breakage**.
- **Severe-test rule**: a hypothesis/replication ships only WITH a runnable Lab baseline measured in the same cycle.
- **Serious models** (glm-5.2 / deepseek), never weak local qwen-7b. HF account = **Danchi17** (not the dancenitra GitHub handle).
- **change → observe → measure → next.** One agent/change at a time; do NOT batch (owner pushback this session).

## Baseline (compare overnight)
`agora_output/strategy/overnight_baseline_20260620.md` — ~21:15: inbox churn ~12–15, methods runs (`server/.methods.json`) ~15, funnel grounded ~2150 / shipped 33. Overnight target: methods-runs and grounded climb, shipped flat (distribution is the owner's step), inbox does NOT refill with synthesize/deepen churn.
```


---
---

# 📚 FULL PRIOR HISTORY (everything before 2026-06-20 — preserved, do not delete)

> The section above is the freshest state. Everything below is the accumulated handoff history from all prior sessions, kept verbatim.

# AGORA — SESSION HANDOFF

> Resume doc for a fresh Claude Code session. Chat in **Slovak**; code + user-facing strings **English**.

## 🔵🔵🔵 RESUME HERE (2026-06-18 — FRESHEST · the CALIBRATION session) 🔵🔵🔵

> Chat **Slovak**. Read this first, then the 2026-06-16 BIG-PIVOT section below (the income-from-home
> strategy still stands — it was not retired, the owner just spent this session steering deep Agora
> research). Auto-memory loads the usual set + `deep-research-workflow-cost`.

**TO RESUME (what the owner types in the fresh session):**
```
/loop C:\Users\Danculus\agora\HANDOFF_LOOP_PROMPT.txt
```

**SYSTEM RUN-STATE (verified clean at handoff):** brain `uvicorn agora.main:app` :8000 = ONE listener
(health ok, ticking); dungeon = ONE bare `mcp_server.py` :5174 = 200, kept alive by the brain's
`watch_dungeon_forever` watchdog; **ZERO supervisors** (correct). Closing the chat does NOT stop either
process. Models = all-cloud (ollama.com glm-4.7 brain + deepseek-v4-flash dungeon), embeddings local
(nomic-embed-text) — see `agora-local-llm`. Vault push: `DUNGEON_AUTOPUSH=1 python -X utf8 tools/safe_vault_push.py "msg"`.

**THE ARC OF THIS SESSION — one coherent idea emerged and got published: CALIBRATION, not capability, is
the scarce resource.** It was not planned; it crystallized from ~5 independent results and then we turned
it on ourselves and reformed our own practice. Everything below is committed + pushed to `agora` main.

1. **Three capstones built (all advisory/read-only, py_compile + `from agora.main import app` verified
   BEFORE restart — the lesson from the EWS crash):**
   - **Critical-transition early-warning engine** — `server/agora/execution/ews.py`, `POST /brain/ews`
     (uses `await request.json()`, NOT `Body(...)` — Body caused a startup crash; fixed). Kendall-tau of
     rolling variance + lag-1 autocorrelation → warning_score + regime + trust HIGH/LOW. Its real
     contribution = knowing when NOT to trust itself (AUC 0.90 on folds, ~0.50 on noise). Commit d78afd4.
   - **Consensus lock-in guard** — `server/agora/execution/self_tipping.py`, `GET /brain/self-tipping`;
     `self_audit_loop` alarms on lock_in_risk. Agora governed by its own minority-tipping law. Commit dcd2f2c.
   - **Self-improving-scientist v3** — `server/agora/execution/self_improver.py`, `GET /brain/self-improver`.
     CANDIDATE_LEVERS registry + **cost-aware threshold** (reversible→lenient t>1.0, irreversible→strict
     t>2.5; crossover ~harm_scale 8). Reads the live self-experiment. Advisory only. Commit 0a61987.
   - (Supporting it: **self-experiment** `self_experiment.py` / `GET /brain/self-experiment`, commit 7157828
     — a falsifiable A/B over policy regimes, intervention grounding_floor=0.50/dedup=0.62 vs control
     0.40/0.95, 6h epochs. **LIVE & RESOLVING ~7h out** — heading to a NULL (intervention ≈ control), so v3
     will reject the grounding_floor lever and queue `verifier_strictness` next. Check it next session.)

2. **THE BREAKTRUTH — "calibration is the scarce resource"** (canon, vault note
   `breaktruth-calibration-is-the-scarce-resource-of-intelligence`, Lab 837d5e). Subsumes 5 session
   results (SC coverage 0.31→0.89, inner-crowd, thinking-protocol, EWS, Crucible). The novel TESTED piece =
   the **capability–calibration scissors**: on correlated evidence (ρ=0.4) as capability K rises 2→100,
   accuracy plateaus at the shared-error floor (RMSE 0.84→0.64) but naive 95%-CI coverage COLLAPSES
   (0.58→0.18) — *more capable = more confidently wrong*. Counting effective-independent evidence
   `N_eff=K/(1+(K−1)ρ)` severs it (coverage holds ~0.87). Honest caveat in the note: 0.87 < 0.95.

3. **Turned the Breaktruth INWARD (self-audit) → then FIXED our own organ.**
   - Self-audit found our prediction ledger fails its own law: 17/20 forecasts were "PubMed papers UP" —
     near-monotonic counters (zero information) at bunched 0.65 confidence (zero resolution). Calibration
     theater. (Vault: `self-audit-our-prediction-ledger-fails-its-own-calibration-breaktruth`.)
   - **Rebuilt the Predict organ** (`prediction_ledger.py` + `data_tool.py`, commit 3afcd41): forecasts now
     a trailing-WINDOW count (a RATE / acceleration), genuinely ~50/50, not a cumulative counter. New
     windowed fetchers (PubMed `reldate`, HN `created_at_i>`, GitHub `created:>`); predictions tagged
     `mode="rate"`; `resolve_due` branches on it so the 20 in-flight cumulative preds still resolve (no
     corruption). Verified live (emits ~0.5 confidence honest forecasts). **First meaningful self-Brier
     resolves in ~14 days** — the first real test of whether we practice what we published.

4. **PUBLIC (all verify-before-citing gated, owner-approved, deploys confirmed):**
   - **Crucible refresh published** (commit 6528168) — 4 verified replications incl. 2 famous FAILEDs
     reconciled (Hong-Page: REPRODUCED only at exact params / FAILED as a general law; Metcalfe FAILED).
   - **2 press posts LIVE** — `robustness-checks-arent-ritual...` (corroboration as a measurable filter,
     commit 300894a) + `why-a-more-capable-ai-can-be-more-confidently-wrong.html` (the scissors, commit
     74e0030). The public storefront now tells ONE coherent calibration/independence story: corroboration
     filter + scissors + Crucible-as-literature-calibration.

**GATED QUEUE: EMPTY** (both press pieces approved + published this session). Nothing waits on the owner.

**PENDING / NEXT SESSION:**
- **Self-experiment verdict ~7h out** (`GET /brain/self-experiment`) → when it lands null, v3 rejects
  grounding_floor + should queue `verifier_strictness` as the next falsifiable lever.
- **Predict rate-forecasts resolve ~14d** → first real self-Brier; watch resolution emerge (or not).
- **🔥 LIVE UPSTREAM-CONTRIBUTION THREAD — mem0ai/mem0#5611 (the real distribution/credibility wedge).**
  We opened the focused minimal-hook feature request that maintainer `kartik-mem0` invited on #5330. He
  replied 2026-06-18 with the crux design question (how to persist access metadata for long-running
  deployments + pin `policy="lru"` semantics). **We answered + POSTED** (2026-06-18 12:13 UTC, owner-approved,
  gated action 4c18ee): a pluggable `AccessStore` decoupled from the 30+ vector backends AND the process
  lifetime (in-mem default + SQLite sidecar + Redis), with a VERIFIED Lab number (`56efae`: SQLite sidecar
  ~6.4 µs/hit, ~2 MB/100k memories, survives restart, <0.1% of a vector query), pinned lru/lfu semantics,
  and an **offer to write a focused PR**. NOW WAITING ON KARTIK. **If he says "yes, draft the PR" → that is
  the next real step** (write the `AccessStore` interface + in-mem + SQLite impls + the benchmark as a test
  in the mem0 repo). The Envoy + outreach backstop watch the thread; each loop cycle re-checks last-author.
  (The old `/open-world-forge` task `3ae957` is no longer in the inbox — inbox is empty.)
- **Strategic reminder (do NOT lose):** the 2026-06-16 BIG PIVOT still holds — the owner's real goal is
  **income from home** (freelance AI services in `services/` + the kids storybooks at
  `C:\Users\Danculus\rozpravky`). This session was deep Agora research because the owner was actively
  steering it; when he is active again, advance the income work, don't drift into more Agora product theater.
- **Cost note (`deep-research-workflow-cost`):** the prior restart was a /deep-research Workflow blowing the
  session limit. One per session max; capture output to disk immediately.

---

## 🟢🟢🟢 RESUME HERE (2026-06-16 — BIG PIVOT) 🟢🟢🟢

> Read this first. Auto-memory now also loads **`owner-goal-ai-services`** and **`market-truth-no-saas`**
> — read both. Chat **Slovak**.

**THE PIVOT (most important):** Agora-as-a-product is NOT the plan. Honest reckoning this session: the
markets our 8 tools touch are taken (eval = Arize $70M/Braintrust; memory = mem0 $24M/AWS), and the real
wall is **distribution from zero reputation** (proved it: the owner's first HN post was auto-killed —
new account + self-link = [dead]). A new product doesn't help unless it solves distribution.

**THE OWNER'S REAL GOAL:** no network/capital/audience, learning, **needs income from home**, enjoys
AI + programming, open to **services**. Two live tracks (both chosen WITH him):

1. **Freelance AI-agent SERVICES** (fastest realistic income; marketplace demand = no audience needed).
   Kit in repo-root **`services/`**:
   - `services/support_agent/` — WORKING grounded AI support agent (answers only from a business's
     content, refuses to hallucinate). CLI + **web chat widget** (`python server.py` → localhost:8800). Verified.
   - `services/GIGS.md` (3 gigs), `services/PROFILES.md` (Upwork/Fiverr copy), `services/PROPOSALS.md` (templates).
   - Next: owner records a 60-sec demo, sets up Upwork/Fiverr, applies; I tailor proposals + build client work.

2. **🌟 Kids interactive storybooks — `C:\Users\Danculus\rozpravky` (SEPARATE project, NOT in agora repo).**
   Most promising — passes BOTH filters: real gap (no SK/CZ digital interactive storybook: audio +
   tap-interaction + in-story mini-games) AND a reachable/fundable audience (parents + **schools + EU/SK
   edtech grants** = institutional, bypasses the distribution wall). Built: a **scalable engine**
   (`index.html`, data-driven: one book = one `books/<name>.js`) + first complete book (Perníková
   chalúpka — Slovak Web-Speech narration, tappable objects, find + quiz mini-games, reward). Content =
   public-domain tales + AI. Full strategy + honest risks + grant list + MVP roadmap in
   **`C:\Users\Danculus\rozpravky\PLAN.md`**. Next decision (owner's): more books / real ElevenLabs SK
   voice / AI illustrations / grant outline / a šlabikár (education) demo. Do NOT drift back to Agora-as-product.

**AGORA SYSTEM STATE:** brain (:8000) + dungeon (:5174, 200) both confirmed ALIVE. The dungeon is kept
alive by the brain's `watch_dungeon_forever` watchdog — **independent of the chat /loop**, so closing the
chat does NOT kill it. Agora keeps producing research (the credibility asset) but is NOT the income plan.
Also shipped+committed this session: 8-tool `agora-memory-toolkit` + `aiaudit` product + public
self-audit page + cross-domain network-filter wired into the seminar + churn monitor (`tools/churn_check.py`)
+ recurring-popup fix (CREATE_NO_WINDOW in brain+dungeon).

**TO RESUME (what the owner types in the fresh session):**
```
/loop C:\Users\Danculus\agora\HANDOFF_LOOP_PROMPT.txt
```
The owner WANTS the loop running — it drains the dungeon-fed Claude inbox (don't stop it) + keeps both
servers healthy. **BUT the loop must honor this session's pivot:** first read memories
`owner-goal-ai-services` + `market-truth-no-saas` + this handoff section. The real priority is income
from home — freelance AI services (`services/`) + the kids storybook project
(`C:\Users\Danculus\rozpravky`) — NOT building Agora as a product. So each loop cycle = (1) triage the
inbox with the raised-bar editorial discipline (skip off-frontier/textbook/duplicate noise, handle
genuine value, severe-test rule), (2) keep Agora healthy + run `tools/churn_check.py`, (3) when the
owner is active, advance the income work (kids-book / services), not Agora product features.

---

## ⚡⚡⚡⚡⚡ RESUME HERE (2026-06-14 — FRESHEST)

> Chat **Slovak**. This section is the full state at session clear. Auto-memory loads include
> `agora-session-state`, `agora-dungeon-value-fix` (today's headline), `agora-architecture`,
> `agora-local-llm`, `agora-roadmap-firm-os`, `gated-approval-briefing`, `vault-push-ntfs-gotcha`.

**TO RESUME (what the owner types in the fresh session):**
```
/loop C:\Users\Danculus\agora\HANDOFF_LOOP_PROMPT.txt
```
That re-enters the autonomous self-upgrade loop. First thing the fresh session should do: read THIS
section + `agora-dungeon-value-fix` memory, health-check both servers, then drain the inbox.

**RUN STATE:** brain `uvicorn agora.main:app` :8000 (ONE listener); dungeon = a **bare**
`python -u mcp_server.py` :5174 kept alive by the brain's `watch_dungeon_forever` watchdog (NOT the
supervisor this session — matches CLAUDE.md current default; verify exactly ONE mcp_server.py + ZERO
supervisors). Both 200. Models = FULL LOCAL `qwen3-coder:30b` on the 3090 (see `agora-local-llm`);
the `deepseek-v4-*` lines in the older section below are STALE. Vault push:
`DUNGEON_AUTOPUSH=1 python -X utf8 tools/safe_vault_push.py "msg"`.

**WHAT THIS SESSION DID — fixed the dungeon's valueless token spend at the ROOT, then purged the old agents:**
The metabolism ledger showed ~7M tokens of near-zero-value agent cognition vs verify-findings (ROI 0.92,
the real value engine). Three commits, all verified (brain 200 + ticking no-errors, dungeon 200):
1. **`40528b9` Dungeon value fix:** DELETED the ungated group brainstorm in `_brain_ecosystem_tick`
   (3 unconditional LLM rounds, ROI 0.04) — the INSPEXIMUS-gated **seminar** is now the sole group-cognition
   path. Also disabled the ExecutionEngine duplicate think-loop (`llm_client=None`).
2. **`9d03e2e` agent-think fix:** found the real `agent-think` source was the **tick_loop roleplay batch**
   (NOT the ExecutionEngine — that was mistargeted). Added `roleplay_use_llm=False`. (Made moot by #3.)
3. **`41bf30f` THE PURGE (owner-ordered):** deleted the 3 OLD ABSTRACT agents (researcher/writer/critic)
   **forever** — `seed_agents()` + its empty-DB call site (the only respawn path), `SIMULATED_THOUGHTS`,
   the tick_loop roleplay block, `AGENT_SYSTEM_PROMPTS` + `agent_think()` (execution/llm_client.py), 3
   `ROLE_SKILLS` keys (lifecycle/genome_bridge.py), the whole `server/agora/agents/` dir, test_all.py
   #9/#10, + a one-time DB sweep (0 rows). A 6-agent **read-only** Workflow (map + adversarial verify)
   first confirmed they were pure dead scaffolding: **0 DB rows, no inspeximus entries, no vault notes, no
   dungeon refs.** Verify-pass mandatory fixes applied (removed a dangling `thinking_agents` heartbeat
   key that would NameError every tick; removed the dead import).

**RESULT (verified):** `agent-think` organ is DELETED → frozen at **7592 calls** forever (function gone).
`agent-dialogue` (the 8 dungeon characters' REAL cognition via `AgentOS._think`) + `verify-findings`
(ROI 0.92) keep growing — the agents think, the waste is dead. KEPT (look-alikes, do NOT touch):
`dungeon_agent_think`, the vault `VaultWriter`, quality-gate critic, dungeon_os corporation/quest roles,
`ROLE_SKILLS` analyst/explorer (owner scoped purge to the named trio).

**PENDING / NEXT SESSION:**
- **Drain the ~21 inbox research tasks** (deferred from the last cycle because that context was very long
  after 4 brain restarts): Hypothesize×severe-test (Lab run in same cycle), the Second-brain briefing
  (owner's product destination — read his real vault notes), Dialectics, an **Oracle call on "Will Claude
  Fable 5 be restored for US customers by June 15?"** (market 2534927, ends 2026-06-16 — time-sensitive),
  Replicate (branching-process finite-size scaling), Predict, Challenge belief, etc.
- **DON'T re-add `seed_agents` or the roleplay block.** The 3 old agents are gone on purpose.
- **Optional cleanup (low priority):** `_process_agent_thought` (main.py ~1025) is now harmless dead code;
  `roleplay_use_llm`/`roleplay_think_pct` config settings are now inert. Remove only if convenient.
- **Outreach:** all 4 tracked threads (hermes-agent#10771, zeroclaw#5849, deer-flow#1898, mem0#5330) have
  US as last author — caught up. Keep running the backstop each cycle (verify last-author, never trust inbox).
- Launch materials (OSS inspeximus, EN+SK) remain GATED — owner posts when ready.

---

## ⚡⚡⚡⚡ RESUME HERE (2026-06-12 LATE EVENING — earlier history)

> Chat **Slovak**. Context was cleared here to save credits — this section is the full state.
> Auto-memory loads: `agora-session-state`, `agora-local-llm`, `agora-roadmap-firm-os`,
> `agora-methods-library`, `gated-approval-briefing`, `agora-architecture`, `agora-db-integrity-pattern`.

**MODELS (final, split by job — see `agora-local-llm`):** dungeon + brain-CHEAP tier =
`deepseek-v4-flash` (reliable, high volume); brain REASONING = `deepseek-v4-pro` (`AGORA_LLM_MODEL`).
glm-4.7 was tried and REVERTED (49s tail-latency froze the dungeon). model_router pins cheap→v4-flash.

**SYSTEM RUN STATE:** brain `uvicorn agora.main:app` :8000; dungeon now runs UNDER a **supervisor** —
`cd agora-game-server && python -u dungeon_supervisor.py` (heartbeat watchdog auto-restarts a wedged
life-loop). Both should be 200. Vault push: `DUNGEON_AUTOPUSH=1 python -X utf8 tools/safe_vault_push.py "msg"`.

**THE BIG ARC THIS SESSION — Agora became a public credibility firm with a real product stack:**
1. **THE CRUCIBLE** (`public/crucible/`, render `tools/render_crucible.py` from `.replications.json`
   + curation `tools/crucible_curation.json`): public machine-replication ledger, **14 REPRODUCED /
   2 FAILED / 6 passes**. The 2 FAILED are famous: **hot-hand (GVT 1985)** + **Dunning–Kruger** —
   both shown to be statistical artifacts with measured numbers. Each verdict ships runnable code.
2. **FLAGSHIP THESIS — "The Operating-Point Trap"** (vault note + `/brain/crucible-synthesis`): standard
   methods break exactly at the operating point (small n / heavy tails / dependence / scarcity); error
   is monotone in stress, not averageable. REFINED by its own falsifier (Lab 52c7a6): robustness =
   decoupling error from stress (mean explodes 0.08→115 vs median flat). 8+ measured findings support it.
3. **PUBLIC ESSAY + DEEP-DIVE (live):** `public/posts/the-operating-point-trap-…html` (flagship essay)
   + `public/posts/deep-dive-hot-hand.html` (hand-crafted SVG charts from real sim data; render
   `tools/render_hothand_deepdive.py`). Layered: essay → deep-dive → ledger.
4. **NEW FLAGSHIP HOMEPAGE (just shipped, commit 08ce98a):** rebuilt `index.html` from a dark Three.js
   SaaS page into an **editorial "newspaper A1"** — Fraunces+Newsreader+JetBrains Mono, paper grain,
   the ledger IS the hero, hero hot-hand SVG chart, 2 FAILED "letterpress plates", a dark thesis panel
   with the mean/median chart, writing index, Inspeximus, protocol. Informed by a 5-agent design
   workflow (Anthropic/Arc/Stripe Press/Ink&Switch/Asterisk/Observable). **Deploy QUEUED at push time
   — VERIFY LIVE first thing next session:** `https://dancenitra.github.io/agora/` (Pages build_type=
   workflow; if the Actions run is stuck queued, cancel it + re-dispatch `gh workflow run pages.yml`,
   or use the `gh-pages` fallback branch + `tools/deploy_pages.sh`).
5. **METHODS LIBRARY** (`server/agora/execution/methods.py`, mechanism #2): parameterized experiment
   templates agents run autonomously (supply params, never code). Grow it: add a template after each
   novel Lab experiment. See `agora-methods-library`.
6. **SYNTHESIS ORGAN** (`server/agora/execution/synthesis.py`, mechanism #1): gathers the rigorous
   corpus + files a grand-synthesis inbox task for Claude (Claude writes the thesis, not v4-pro).
7. **CORP LAYER REDESIGNED** (owner: "dotiahnuť nech funguje ako má"): was exhausted/junk sources +
   wrong eval rubric = 0 approved ever. Now Scout pulls REAL papers with measurable claims from
   board-aligned topics (`pick_paper_target` + `_CORP_TOPICS` in `replication.py`), research on the
   medium tier with regex parse, CTO/CEO judge with a TESTABILITY/portfolio rubric (empty-retry),
   approved → "Crucible candidate" in Claude's inbox to replicate/refute. Honest ceiling: auto-search
   won't surface famous classics (Claude hunts those); corp adds breadth + the occasional gem.
8. **DUNGEON FIXES:** telepathic time-based quests (work decoupled from agent position — no more
   traffic-jam freezes), supervisor watchdog + heartbeat, OS-module light cap, QuestBoard "RESEARCH
   IDEAS" panel shows LIVE quests only (was padding with day-old DONE corp quests).
9. **OUTREACH:** Envoy now files a "Correspondence reply by X" inbox task + Slovak briefing on every
   reply (`main.py envoy_watch_loop`). Posted a measured reply to **bytedance/deer-flow#1898** (live).
   New skill `.claude/skills/outreach-briefing/`. Inspeximus README updated with the popularity-trap
   retention finding.

**PENDING / NEXT (priority):**
- **VERIFY the new homepage is LIVE** (`https://dancenitra.github.io/agora/`) — deploy was queued at
  context-clear; if stuck, re-dispatch the Pages workflow. Screenshot it; Telegram owner the link.
- **Hunt a 3rd famous FAILED** before any HN launch (ego-depletion, power-posing, growth-mindset are
  candidates — Lab-replicate where computable). HN timing = owner's call; content is essentially ready.
- Methods Library: add templates for diversification / DK-artifact / replay / memory-retention.
- Watch corp produce its first APPROVED Crucible candidate; develop it.
- Gated awaiting owner: none open (flagship essay 20fa5b + deer-flow reply 3dc9c3 both approved+posted).

**LOOP:** the autonomous `/loop` (HANDOFF_LOOP_PROMPT.txt) runs each cycle: inbox tasks → Lab-backed
rigorous notes / replications, editorial skips, health check, ScheduleWakeup ~1500s. Always end a
turn with ScheduleWakeup or the loop dies.

---

## ⚡⚡⚡ RESUME HERE (2026-06-12 — earlier)

> Chat **Slovak**. Auto-memory loads: read `agora-session-state`, `agora-frontier-direction`,
> `gated-approval-briefing`, `corporation-subsystem-decision`, `agora-db-integrity-pattern`.

**BIGGEST CHANGE — MODEL IS NOW CLOUD `deepseek-v4-pro`, NOT local qwen3-coder.** Local was the root
of slowness + weak corp research + GPU contention; owner approved reverting. Both `server/.env`
(`AGORA_API_BASE_URL=https://ollama.com/v1`, `AGORA_API_KEY=df8301…`, `AGORA_LLM_MODEL=deepseek-v4-pro`)
and `agora-game-server/.env` (cloud URL + key, `DUNGEON_LLM_MODEL=deepseek-v4-pro`, MAX_TOKENS=3000,
THINK=false) point to cloud. LOCAL_BACKUP revert lines are in both .env comments. GPU freed (qwen3-coder
unloaded). LLM now ~2-4s + smart. **This costs the Ollama Cloud subscription** — owner accepted.

**RAISED BAR (critical, see `agora-frontier-direction`):** owner rejected "fewer/deeper insights" — he
wants **rigorous, scientifically-tested SERIOUS research + genuinely GROUNDBREAKING ideas, NOT re-deriving
textbook results.** Standing priorities updated via `/brain/board/decide`. My loop work delivers Lab-backed,
falsifiable, ORIGINAL notes. Shipped this session: the **collective-intelligence trilogy** (cascade
N_eff=3 / Lab e8b881; topology k_c=2 / 678a9c; the cure needs ~80% independence / aa23bf) + **self-refinement
amplifies the critic** (sub-coinflip critic iterated → collapses to 0 / ea3869) + collider-bias, static-IV,
finance vol-drag. These are the real value engine.

**CORP PIPELINE — fixed end-to-end (it was 100% stuck/rejected):** (1) `research_summary` now populated
from findings so CEO/CTO evaluate real research; (2) eval verdict now PERSISTS (was re-evaluating forever);
(3) `_topic_research` grounds findings in REAL literature (OpenAlex+arXiv) not bare LLM; (4) eval gate
SOFTENED (`approved = cto OR ceo OR max_score≥60`) — corp surfaces LEADS, **Claude is the real filter via
Ship-review**; (5) corp tick runs as a BACKGROUND task (was blocking the brain loop); (6) MetaScanner
meta-quests ("agents stuck", "rejecting too many") are now one-shot ALERTS (terminal on creation) — they
were re-researching forever (90+ findings, the "stuck agents" the owner kept seeing). Approved corp research
→ Ship-review task in Claude's inbox → I develop+ship the good ones.

**OUTREACH — LIVE + the briefing workflow:** posted comment on **mem0ai/mem0#5330** (value-ranked vs
frequency decay) + published press piece "Why crowds get dumber…" to `public/posts/`. Real inbound: on
zeroclaw#5849 / deer-flow#1898 we got a 🚀 reaction, **@DanceNitra cited by `ferhimedamine` ("strongly
agree")**, validated 2× in their production. **WORKFLOW (see `gated-approval-briefing`):** before ANY
`approve <id>`, give owner a Slovak briefing — their question + our answer + how we use it. Envoy watches
replies; when one lands, brief owner + propose our reply.

**DUNGEON UI (owner cares a lot):** QuestBoard shows multi-agent initials (left of quest), REAL
per-agent progress meters (distance-to-goal), a zero-cost **PULSE** live counter (findings/exchanges/done),
event log shows real Q&A "💬 X → Y: …" + "✅ done" (NOT trust "grew closer"), panels capped (no overlap),
agents DIVERGE not herd (applied our own research). Cadence faster on cloud.

**VAULT FUNNEL WIDENED (this request):** `promote-findings` n 8→16, candidate cap 24→40, cadence ~20→10min
(`mcp_server.py _run_promotion` + `loop_n % 750 == 350`). ~1947 discoveries → more gems now land in the vault.

**NEXT (priority):**
1. Keep delivering AMBITIOUS ORIGINAL Lab-backed research (the raised bar) + expand outreach to strong fits
   (mem0-style: map our measured findings to a real open issue, gated, brief owner first).
2. Watch corp pipeline now produce APPROVED research on v4-pro → Ship-reviews → develop them.
3. Watch mem0#5330 thread for replies (Envoy) → brief owner + propose reply.
4. **Do NOT rabbit-hole on dungeon cosmetics** — owner's redirect: focus on the WHOLE self-improving system
   (research + outreach + business plan), not banalities.

**Pending gated (owner acts):** none right now (mem0 + press both just approved+executed). GitHub Pages
deploy may still be blocked (billing) — `public/` files committed regardless.

---

## ⚡⚡ RESUME HERE (2026-06-11 EVENING)

**This session pivoted Agora from internal research OS → a public, credibility-earning FIRM, and
shipped the first product.** Memory auto-loads strategy (`agora-roadmap-firm-os`,
`agora-frontier-direction`, `agora-outward-engagement`, `verify-ui-with-headless-edge`).

**System:** Brain = `uvicorn agora.main:app` :8000; Dungeon = `python -u mcp_server.py` in
`agora-game-server/`. Check vitals → 200, ONE of each `python3.12`. /loop runs ~10 min. **Batch edits
to avoid repeated dungeon restarts** (each restart re-fires startup tasks → morning-report spam).

**Firm roadmap status:**
- **A1 storefront — LIVE:** `https://dancenitra.github.io/agora/` (source = `index.html` at repo root;
  Pages serves main/root, `.nojekyll`). Three.js orb + GSAP + theme toggle + a **Inspeximus** section.
- **A2 distribution — RUNNING:** 2 live gated-then-posted outreach threads — zeroclaw#5849 (got 🚀) +
  jerseycheese/Narraitor#441. Envoy watches replies. **OPEN: pick broad channel (X/blog/HN).**
- **A3 track record — fixed:** Oracle retargeted to AI/tech/science markets (edge) not crypto
  (`oracle.py _DOMAIN_RX`); resolvers auto-run; record grows ~2 wks. 8 REPRODUCED / 0 FAILED reps.
- **A5 product — DEFINED + BUILT:** open-source **memory layer for AI agents**, founder-first,
  open-core, credibility vehicle. **Inspeximus** (handle `inspeximus`): `inspeximus/inspeximus.py` (zero-dep ref impl,
  dogfooded), `inspeximus/README.md`, storefront section.
- **Posts:** rebuilt as beautiful **EN/SK bilingual** SEO-slugged HTML via `tools/render_post.py`
  (`public/posts/src/{name}.{en,sk}.md` → `{slug}.html`; computed read-time).

**NEXT (priority):**
1. OWNER DECISIONS: A2 channel; auto-post policy (all outreach/press currently GATED → `approve <id>`).
2. **Wire `tools/render_post.py` into the Press organ** so future posts auto-render bilingual HTML.
3. Inspeximus MCP server (any agent uses `inspeximus` as memory) + examples.
4. Inbox task `8da953` (Lee-Spekkens causal-geometry synthesis) — loop will take it.

**Gotchas:** screenshot UI before claiming done (headless Edge, see memory); Telegram one-liners ASCII
from `server/.env`; vault push via `DUNGEON_AUTOPUSH=1 python -X utf8 tools/safe_vault_push.py "msg"`.

---

## ⚡ RESUME HERE (2026-06-10)
**Read first:** auto-memory `agora-session-state.md` (the freshest, fullest state — 8 frontier waves
detailed) + `HANDOFF_LOOP_PROMPT.txt` (verbatim loop prompt to paste).

**State at handoff:** both servers **200**, ONE dungeon, ONE :8000 listener, **inbox empty**.
agora repo HEAD `e74cf67`; vault HEAD `d7d1f9a`. **36 frontiers / 8 waves + GitHub-leverage builds
ALL SHIPPED.** First public act LIVE: a comment on NousResearch/hermes-agent#10771.

**Agora runs INDEPENDENTLY of the Claude session** — two processes (uvicorn :8000 + mcp_server.py
:5174), kept alive by the watchdogs + the user Startup-folder autostart. Clearing context does NOT
stop Agora; it only stops Claude driving the inbox loop.

**To continue after /clear (the cheap path):** in a fresh session, paste the contents of
`HANDOFF_LOOP_PROMPT.txt` as the `/loop` input. A fresh session reads only this doc + memory (small,
cached) instead of replaying a 100+ message history every wakeup — that is what was burning tokens.

**If a server is down:** restart per §2 below (kill ALL uvicorn first → one; dungeon: kill
mcp_server.py → one). Verify both 200 + exactly one :8000 listener.

**Latest capability layers (beyond the original frontiers below):** Oracle (live Polymarket,
Brier-scored), Metabolism (per-organ token ROI), Theory Engine (beliefs run as Lab models),
Counterfactual Self (replay own history), Correspondent (gated public GitHub posts + Input Shield
on replies), Gatekeeper (upstream skip ledger + board priorities), Atlas (domain MOCs), Gauges
(/api/v1/agent-os/dashboard), Coherence Audit, Recall (/brain/recall — memory provider for external
agents), Library reading list. Full per-frontier detail in `agora-session-state.md`.

---
# (original handoff, 2026-06-09)

---

## 1. WHAT AGORA IS
A self-sustaining **recursive research OS** over the user's Obsidian vault (`my-second-brain`). Two
processes:

| Process | Cmd | Ports | Role |
|---|---|---|---|
| **dungeon** | `agora-game-server/mcp_server.py` | 5174 (HTTP) / 5175 (WS) | 6 LLM agents, quest loop, 3D dungeon view, all the `_queue_*` / `_run_*` cognitive triggers, broadcasts to the HUD |
| **brain** | `uvicorn agora.main:app` in `server/` | 8000 | FastAPI: every `/api/v1/agent-os/brain/*` endpoint, vault writer, Telegram bot |

LLM = Ollama Cloud **deepseek-v4-flash** (all tiers; weak on creative synthesis — returns empty on
complex JSON). Embeddings = local Ollama **nomic-embed-text** (:11434, RTX 3090). **Keep cloud LLM —
do NOT switch to local.** Heavy synthesis (insights, dialectic, predictions, worldview, artifacts) is
routed to **Claude Opus** via the inbox loop; flash does the light labeled-text tasks.

---

## 2. CURRENT STATE (end of session)
- Both servers **200**, exactly **ONE** dungeon, **ONE** :8000 listener. Inbox **empty**.
- agora repo HEAD = **`1f1c295`** (all today's work pushed to `DanceNitra/agora` main).
- Vault (`my-second-brain`) HEAD ≈ **`fe21cbb`** — **15 Agora artifact notes** (insights / dialectic /
  worldview / brief) pushed to `DanceNitra/my-second-brain`.
- Autonomous self-upgrade loop is **running** via ScheduleWakeup (~1800s cadence). Next wake was ~21:18.

### Run / restart (PowerShell)
```powershell
# BRAIN (clean restart — kill ALL uvicorn first to avoid port conflicts)
Get-CimInstance Win32_Process -Filter "name like '%python%'" | ? { $_.CommandLine -like '*uvicorn*' -or $_.CommandLine -like '*agora.main*' } | % { Stop-Process -Id $_.ProcessId -Force }
cd C:\Users\Danculus\agora\server; $env:PYTHONPATH='.'; $env:PYTHONUNBUFFERED='1'
Start-Process -WindowStyle Hidden -RedirectStandardError C:\Users\Danculus\agora\server\_brain.err python -ArgumentList "-m","uvicorn","agora.main:app","--host","127.0.0.1","--port","8000"

# DUNGEON
Get-CimInstance Win32_Process -Filter "name like '%python%'" | ? { $_.CommandLine -like '*mcp_server.py*' } | % { Stop-Process -Id $_.ProcessId -Force }
cd C:\Users\Danculus\agora\agora-game-server; $env:PYTHONUNBUFFERED='1'; Remove-Item Env:\DUNGEON_AUTOPUSH -EA SilentlyContinue
Start-Process -WindowStyle Hidden -RedirectStandardOutput _dungeon.log -RedirectStandardError _dungeon.err python -ArgumentList "-u","mcp_server.py"
```
### Verify (always after a restart)
```
curl http://localhost:5174/                                   # dungeon = 200
curl http://127.0.0.1:8000/api/v1/vault-company/org-chart     # brain   = 200
# exactly ONE :8000 LISTENER + ONE mcp_server.py (psutil)
```

---

## 3. WHAT WE BUILT TODAY (the full capability map)
The arc: **collect → ground → curate → create → be accountable → deepen → teach → produce → debate →
direct → know-you → reflect (mind) → learn → ACT → perceive → be visible.**

Each capability = a `server/agora/execution/*.py` module + `/brain/*` endpoint(s) + (usually) a Telegram
command + a dungeon `_queue_*`/`_run_*` trigger that drops a task in the **Claude inbox** for Opus to do.

| Capability | Module | Endpoint(s) | Telegram | Trigger |
|---|---|---|---|---|
| Insight Engine | `insight_engine.py` | `/brain/insight`, `/insight-inputs` | `insight <t>` | `_queue_insight_theme` ~3h |
| Prediction Ledger (Claude-made) | `prediction_ledger.py` | `/predict-baseline`, `/predict-record`, `/predictions`, `/resolve-predictions` | `predict`, `predictions` | `_run_predictions` ~2h |
| Compounding Flywheel | `flywheel.py` | `/flywheel/questions`, `/flywheel/deepen-inputs` | — | `_queue_deepening` ~4h |
| Socratic Agora | `socratic.py` | `/socratic`, `/learn-next` | `quiz <t>`, `learn` | — |
| Action Engine (artifacts) | `action_engine.py` | `/action-inputs` | `draft <kind>: <t>` | — |
| Dialectic (Claude-made) | `dialectic.py` | `/dialectic`, `/dialectic-inputs` | `debate <c>` | `_queue_dialectic` ~5h |
| Research Programs | `research_program.py` | `/program/start`,`/list`,`/findings` | `program <q>` | — |
| Personal Context Model | `user_model.py` | `/user-model` | `model` | — |
| **The Agora Mind** (metacognition) | `mind.py` | `/mind-inputs`, `/worldview`, `/worldview-record` | `mind` | `_queue_mind_reflection` ~daily |
| **The Learning Loop** | `learning.py` | `/learning-inputs`, `/lessons`, `/lessons-record` | `lessons` | `_queue_learning` ~daily |
| **Agora's Hands** (+executor) | `hands.py` | `/actions`,`/action-propose`,`/action-decide`,`/action-result`,`/action-execute` | `actions`, `approve <id>`, `reject <id>` | — |
| **Agora's Senses** (perceive now) | `senses.py` | `/brain/now` | `now` | `_sense_and_queue` ~daily |
| Reality Bridge (7 sources) | `data_tool.py` | `/empirical-test` | `reality <c>` | `_run_reality_check` ~12min |
| Funnel + value-ranked consolidation | `agent_os_api.py`, `quality_gate.py` | `/promote-findings` | — | `_run_promotion` ~20min |
| Pulse + research-ROI | `pulse.py` | `/pulse` | `pulse` | `_run_pulse` |

**Dungeon Mind HUD (the FACE):** `agora-game-server/static/index.html` `#hud-mind` + `MindHUD`;
dungeon `_broadcast_mind_state` (~4min) sends a `mind_state` WS event (worldview headline, predictions,
hit-rate, lessons, flywheel) → bottom-center panel. **Cognitive sparks:** `_mind_spark(color,kind)`
broadcasts `effect_added` at the throne (tile 12,2) on each cognitive moment (violet insight / cyan
prediction / gold reflection / green lesson / pink sensed-topic / dim heartbeat). Open `http://localhost:5174`.

**KEY PATTERN — "Agora gathers, Claude creates":** dungeon queues `<Verb>: <theme>` into the Claude
inbox; the loop (below) handles each by calling the matching `/brain/*-inputs` (gather only) and then
Opus does the real synthesis and POSTs the result. This is how the weak flash model is bypassed for
everything that needs quality.

---

## 4. THE AUTONOMOUS SELF-UPGRADE LOOP (paste as `/loop` or run on wake)
The loop fires ~every 30 min. Each cycle: read `/brain/telegram-feed?n=8` + `/brain/claude-inbox`;
handle EACH pending task (with **editorial judgment** — skip duplicate insight themes, mark them done
with a note instead of re-synthesizing); else DO NOTHING. The full current loop prompt is stored in the
last `ScheduleWakeup` of this session — reproduced verbatim in **`HANDOFF_LOOP_PROMPT.txt`** next to this
file. Inbox task kinds the loop knows: `Synthesize insight:`, `Deepen insight [id]:`, `Draft <kind>:`,
`Dialectic:`, `Predict:`, `Reflect: state of mind`, `Learn from outcomes`, and numeric `Implement Agora
self-upgrade` picks.

**Candidate self-upgrade DONE (`4de6627`, 2026-06-09):** `_queue_insight_theme` now dedupes against
existing vault insights (frontmatter titles) + pending inbox tasks via word-overlap. No open candidate —
an idle cycle should look for a new clearly-safe, fully-testable improvement or do nothing.

---

## 5. STATE FILES (gitignored, in `server/`)
`.predictions.json` (ledger) · `.lessons.json` (Learning Loop, injected into predict/mind) ·
`.worldview.md` (the Mind's current worldview) · `.flywheel.json` (open falsifier questions) ·
`.actions.json` (Hands queue) · `.user_model.json` (who Rasto is). Built artifacts → `agora_output/`.

---

## 6. NON-NEGOTIABLE RULES & GOTCHAS
- **Language:** code + user-facing strings = English; chat with Rasto = Slovak.
- **Telegram token** `HERMES_TELEGRAM_BOT_TOKEN` / `HERMES_TELEGRAM_CHAT_ID` live in gitignored
  `server/.env`. NEVER print/commit them literally; read via `python -X utf8` that loads `.env`.
- **Vault push:** NEVER `git add -A` in `my-second-brain` (NTFS `:` files). Use
  `DUNGEON_AUTOPUSH=1 python tools/safe_vault_push.py "<msg>"`. Count notes via `git ls-tree -r HEAD`
  (NOT `git ls-files`).
- **Keep cloud deepseek** (don't switch to local LLM).
- **Brain can briefly return 000** during a dungeon restart race or from the pre-existing
  `trust_scores.id NOT NULL` IntegrityError → clean-restart uvicorn (kill ALL uvicorn, start one),
  verify ONE :8000 listener.
- **deepseek-v4-flash returns empty** on complex JSON → that's why labeled-text formats + the
  gather→Claude pattern exist. Don't "fix" by adding json_object response_format.
- Self-upgrade safety: small reversible commits, py_compile, verify both 200, revert on breakage, at
  most ONE self-upgrade per cycle, Telegram only on a completed task or breakage.

---

## 7. WHERE WE LEFT OFF / NEXT IDEAS
Last action: a loop cycle cleared a 4-task insight backlog (1 fresh *Software-Architecture-as-Pareto-
navigation* insight written + pushed; 3 duplicate/saturated-cluster marked done). Loop rescheduled and
running. Possible next directions Rasto floated: deepen the dungeon (prediction board, a 3D **mind
chamber**, effects when an insight lands), more **senses** (calendar/activity = perceive Rasto's real
day), more **Hands** action kinds, or the dedup self-upgrade above. Or just let it run and watch.
