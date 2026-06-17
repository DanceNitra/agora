# SESSION HANDOFF — 2026-06-17 (restart to save credits)

We hit the Claude session limit (resets 12am Europe/Bratislava) during the verification phase of the
AI-productivity deep-research workflow. Restarting fresh. Nothing below is lost; this file + MEMORY.md
let the next session resume cheaply.

## HOW TO RESUME
1. Read this file + `MEMORY.md` first.
2. Re-enter the loop exactly as before: paste `/loop C:\Users\Danculus\agora\HANDOFF_LOOP_PROMPT.txt`.
3. The loop is now **DISCOVERY-FIRST** (empty inbox → ship one real thing from the backlog; the chatbot
   income lane is PARKED as commoditised). Reports go in the CHAT in Slovak, not Telegram (owner can't
   read truncated Telegram).

## CREDIT LESSON (important)
The deep-research **Workflow** is expensive: ~100 sub-agents, ~2-3.4M tokens, ~5-11 min, and it can hit
the session limit mid-run (the verification + synthesis of the AI-productivity run failed for this
reason). Use it **sparingly — at most one per session**, and capture its output to disk immediately
(the raw result lives only in a temp file that does NOT survive restart).

## TOP PRIORITY NEXT SESSION: write the AI-productivity article (do NOT re-run the workflow)
Owner asked for "nový výskum, ďalší článok." The research is DONE (workflow `wpkmut1ph`); only the
article remains. Write a gated press post in our house style ("felt vs measured", same brand as the
longevity pieces) from these **6 verified (3-0) findings**:

1. METR 2025 RCT: experienced open-source devs took **19% LONGER** to complete issues when allowed
   early-2025 AI tools — a measured, significant slowdown. (metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/)
2. **Perception-vs-measurement gap:** devs forecast a **24% speedup** beforehand and STILL believed AI
   sped them up **~20%** AFTER the measured slowdown. (same METR source)
3. Design: within-developer RCT, **16 experienced devs, 246 real issues** from mature repos (avg 22k+
   stars, 1M+ LOC) they'd worked on for years; each issue randomized AI-allowed/disallowed; ~2h/task. (METR)
4. arXiv 2507.09089 confirms: 16 devs (avg 5 yrs on the repos), 246 tasks, AI **+19% completion time**.
5. arXiv 2507.09089: self-estimated **-20%**, forecast **-24%** — opposite of the measured +19%.
6. METR 2026-02-24 update: **20% slowdown**, Feb-Jun 2025 data.

**Counter-evidence (FETCHED but NOT 3-vote-verified — the verification failed at the session limit, so
cite as claims, not verified fact):** GitHub Copilot study (n=95) showed 55% faster — BUT on a single
**greenfield synthetic task** (write an HTTP server in JS), auto-scored; the >90%-faster figures are
**self-report surveys**. Frame honestly: the big speedups are greenfield/junior/self-report; the measured
slowdown is experienced devs on their OWN mature codebases. That contrast IS the article.

Article angle: "AI makes experienced developers feel ~20% faster while measuring ~19% slower on their own
code — the felt-vs-measured gap, and why the 55%-faster headlines are greenfield/self-report." Honest
caveats: METR is experienced-dev/mature-repo-specific (doesn't generalise to all coding); METR itself is
redesigning over a recruitment-selection concern; this is early-2025 tooling.
Full raw workflow output was at: %TEMP%\claude\...\tasks\wpkmut1ph.output (ephemeral — findings above are the durable copy).

## WHAT SHIPPED THIS SESSION (already done — don't redo)
- **Build #2 — Finding Novelty & Significance Gate** at the discovery write path (server/agora/api/agent_os_api.py): rejects refusals + trivial bare-fact findings; counted in _PROMOTE_STATS. Committed + brain restarted, verified.
- **Income track (chatbot PARKED — commoditised, Chatbase ~$40/mo):** support_agent hardened against hallucination (defaults to `qwen3-coder:30b`; the 7B invented hours/phones/services); `reliability_receipt` built; real Smile Clinic demo + GATED outreach draft (`services/support_agent/outreach_smileclinic.md`); gig kit + `services/ACTION_PLAN.md`. Real model = done-for-you SERVICE on existing tools, NOT building software. Needs a market-check before any promise.
- **Longevity research line (the strong thread):** deep-research report → 3 vault notes (`deep-research-longevity-translation-gap`, `calibrated-prior-mouse-longevity-headlines`, `audited-longevity-translation-table`); survival-statistic Crucible replication REPRODUCED (`agora_output/lab/20260616-geroprotector-survival-statistic-artifact.py`); **2 PUBLISHED articles** (calibrated-prior + 16-scorecard, on dancenitra.github.io/agora); **living Longevity Ledger** (`tools/longevity_ledger.json` + `tools/render_longevity_ledger.py`, running number 0/16 proven, edit JSON + re-run as trials report).
- **Beliefs revised via Lab:** herding-cure (cheap if independents vote FIRST), self-refinement (plateaus at critic competence, doesn't reach excellence), detection-threshold (NOT a critical point — opposite precursors).
- **Outreach:** chroma#1330 BM25-hybrid comment PUBLISHED (gated, owner-approved). All 5 threads (hermes#10771, zeroclaw#5849, deer-flow#1898, mem0#5330, chroma#1330) caught up — us last author. Verify last-author per thread each cycle (Envoy can stall).
- **Loop file** `HANDOFF_LOOP_PROMPT.txt` updated: empty-inbox = discovery-first backlog, income parked.
- **3 lessons recorded** to the brain (built-a-core != product; verify-before-citing pays; surrogate/gauge-vs-outcome is our master-vein).

## PENDING INBOX (next session)
- `ab0223` Replicate: epidemic threshold vanishes on scale-free networks (clean computable Crucible candidate; lambda_c = <k>/<k^2> -> 0). Note: it's a TRUE textbook result, so it'll REPRODUCE — low Crucible novelty; do only if wanting a safe ledger entry.
- `3d366e` Exaptation scan (turn Agora outward — gated/parked-ish).
- `166e6d` Model belief: alt-data alpha = identification premium, not information premium (A20, finance — on-frontier, formal-model candidate).
- Forge gap `0f00aa` (survival-statistic Crucible) already DONE this session.

## OWNER PREFERENCES (hard rules learned this session)
- NO idle/"quiet" cycles — always ship from the backlog. NO Telegram reports (truncated) — report in CHAT, Slovak.
- Be rigorous + HONEST; no "we have a product" without a market-check. Don't claim shallow things are done.
- Gated outward: nothing publishes without owner `approve <id>`.
