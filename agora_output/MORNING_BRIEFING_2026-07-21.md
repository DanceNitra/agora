# Morning briefing — 21 July 2026

Everything below was produced overnight while you slept, in half-hour loop iterations. Where a number
appears, the file that produced it is named.

---

## 1. The dungeon stopped producing rubbish, and we know why it did

**Before:** 22 pending tasks, 17 of them off-mission — eight "Hypothesize from findings" on Landauer's
principle, orphan nodes and data ethics; a dialectic on ADHD fMRI meta-analyses; a replication of
reaction-diffusion phase transitions. All while the board had been locked to agent-memory integrity
for days.

**Now:** 3 pending, all defensible. 17 births blocked at the gate overnight, each logged.

**The cause was architectural, not a bug.** A code audit traced it to three things:

- Of **31 functions that queue tasks, only 5 called the board gate**. I had been patching them one at
  a time; the fix is a single choke point in `_brain_post_sync` that covers all of them, including
  ones added later.
- The gate itself fell **open** when nothing matched the board — precisely the case that needed
  gating. Its own comment said so: *"Soft by design — if nothing matches, the full pool passes, so the
  swarm never starves."* **The system ranked starvation as a worse failure than off-mission work.**
  For a locked frontier that is exactly backwards.
- Three selectors were **anti-correlated with the mission by construction**: belief-revision picked
  the *oldest* belief (ours are the newest), cartography picked the domain pair with the *fewest*
  bridges (in a vault of physics and category theory, guaranteed to be off-mission — and it was
  injected at the *front* of the hypothesis queue), and hypothesis induction sampled the whole 8k
  corpus at random with no pending cap.

Two further holes found by watching what was *born* rather than what was filtered: the board text
contains its own refusals ("Deprioritize … politics, cloud/trivia"), and reading it flat turned those
words into permissions; and matching any board token let "Specification curve **correction** tool"
through. A task must now name a subject that is actually ours.

**Nobody was fired.** Eight organs were briefly switched off and are back on, being repointed at the
outside world one at a time. Wren went first and is working: his task in the queue right now is
*"Chart the external map: loudest need 'provenance/trust' raised in 36 unrelated projects"*.

Vault output overnight: **9 notes in 8 hours**, on-mission.

---

## 2. We opened eyes outside our own pot

Every intake this system had was the vault (what we already thought) or arXiv (what academics
publish). Neither would have told us a competitor shipped a revert command last week.

- **External library** — 367 items harvested from GitHub issues, PRs and Reddit, deduplicated and
  searchable, stored in mnemo itself. Endpoints: `/brain/library/external/{harvest,search,map}`.
- **Competitor watch** — 10 rivals snapshotted (GitHub releases, PyPI versions, stars); reports only
  *deltas*, and flags loudly when a release touches our axis.
- **Contribution finder** — 125 threads where something we have shipped answers what is being asked.
  Saved at `agora_output/contribution_shortlist.json`.

---

## 3. The finding that should change what we say in public

Three independent instruments agreed, and they invert our pitch:

| need | distinct projects asking |
|---|---|
| provenance / trust | **84** |
| correction / update | **69** |
| retrieval quality | 28 |
| dedup / conflict | 22 |
| forget / erasure | 18 |
| determinism / cost | 17 |
| poisoning / safety | 15 |
| **revert / undo** | **10** |

`revert` — the feature we advertise as "nobody else has this" — is **last**. It is a proof, not a
pitch. Lead with correction and provenance; keep revert as the evidence underneath.

Full list of ten upgrades with the evidence per item: `agora_output/TOP10_UPGRADES.md`.

---

## 4. The number that says we have no users

`agora-mnemo` on PyPI, mirrors excluded, 29 days:

| | days | mean downloads/day |
|---|---|---|
| days we published a release | 20 | **555** |
| days we did not | 9 | **9** |

r = 0.977 across 97 releases. **Nine people install mnemo on a day we ship nothing.** Nothing public
cites the weekly figure — checked — and nothing should until that baseline moves.

**Marketing or capability? Neither. The capability is real and unfindable.** Three audit harnesses, a
parity-tested LangGraph store, a published null, signed provenance — and nine installs.

**How the leaders actually got their stars:** claude-mem's 88k came from four GitHub Trending
re-entries tied to major version bumps, plus annexing each new agent host as it launched. It has **2
Hacker News points, lifetime**, and sits in the *community* plugin directory, not the official one.
mem0's driver was the `embedchain` → `mem0` **rename-relaunch**, not the $24M. Papers buy roughly zero
stars — Graphiti's arXiv month was its worst.

---

## 5. Shipped overnight

- **mnemo 1.24.4** via GitHub Actions with **PyPI Trusted Publishing** — first release carrying a
  signed attestation binding the wheel to this repo, workflow and commit. Verified on the integrity
  endpoint.
- **The repo is now its own Claude Code plugin marketplace**: `/plugin marketplace add
  DanceNitra/mnemo` → `/plugin install mnemo@mnemo`. Both manifests verified as served by GitHub.
  The first manifest I wrote would have been **dead on arrival** — `uvx --from agora-mnemo mnemo-mcp`
  fails because the core is deliberately zero-dependency; caught by running the exact declared command
  from a clean environment.
- **README corrected**: it claimed "600–730 s of LLM extraction"; the real distribution across all 24
  scenarios is **519–917 s, median 606**. Version string was three releases stale.
- **MCP path-safety audit** — prompted by reading someone else's merged PR: **0 of our 30 MCP tools
  take a path, file, url or command argument**, so a model cannot point the server at arbitrary files.

---

## 6. What needs you

1. **The rename decision deserves re-deciding.** Standing call was "no rename". The single
   highest-leverage move in the entire star dataset was a rename-relaunch, and we carry an eight-way
   name collision. Not a recommendation — a decision that should be made again with this number on
   the table.
2. **Reddit r/RAG post** — you posted it; when replies come, three of the four questions can be
   answered with a link someone can run.
3. **EDRN** — still waiting on which definition of C they choose. Our sign-off is blocked on it.
4. **Marat** — the reply about his control being the wrong null is drafted; you send it.

---

## 7. What I would do first this morning

**Item 1 of the ten: make the drop-in story findable.** `MnemoStore` already passes an
operation-by-operation parity audit against LangGraph's own store — and it appears in no LangChain
integrations page, and `awesome-LangGraph#88` still sits unmerged. 39 threads are asking for exactly
this. It is a day of packaging, not a month of building, and it is the shortest path from "we have a
verified product" to "someone outside can find it".

---

## 8. Two things I could not verify from here, so they are yours

**Other MCP hosts.** The README documents the config generically and the snippet is correct
(`uvx --from "agora-mnemo[mcp]" mnemo-mcp`), but only Claude Code is installed on this machine, so
only that path is verified end to end. Cursor, Windsurf, Codex, Cline and Continue each keep their MCP
config in a different file, and Codex uses TOML rather than JSON — a user copying our JSON into Codex
would fail. Writing those paths without testing them is the same "fairly confident" that cost us three
corrections tonight, so they are not in the README. If you have Cursor open, confirming one path takes
a minute and then we can annex hosts properly, which is the mechanism behind claude-mem's 88k.

**The awesome-LangGraph listing.** Our PR #88 has been open since 17 July with no comment — but the
maintainer last merged anything on 10 July, in a single batch, and **eight PRs are queued behind that
date, ours among them**. Nothing is wrong with our submission; the channel is simply slow and outside
our control. Do not nudge with seven others waiting.

**Verified instead, on the exact artifact the new plugin installs** (`agora_mnemo-1.24.4`, sha256
`7b4bdd71e8a2…`): claims audit 13/13, governance audit CLAIM HOLDS. What we are telling people to
install is what we tested.

---

## 9. The pattern worth more than any single fix

One defect appeared in **three independent filters** written hours apart last night, each time looking
like a different bug: the task gate matched any board token, the contribution finder matched any offer
keyword, and the scout matched any theme. They admitted, respectively, "Specification curve correction
tool", an EU crypto wallet, and `[BOUNTY] Implement Device-Age Oracle Fields (fingerprint check)`.

It is one bug class: **scoring relevance without first asking whether the item is about our subject at
all.** Widening the keyword list makes it worse, because the set of things that merely *contain* a word
dwarfs the set of things *about* it. All three now test aboutness as a hard precondition before any
score is computed — and the scout's test had to sit at the point of *collection*, because scout tasks
bypass the task gate by design.

Recorded as a permanent rule: `keyword-match-without-subject-check`.

---

## 10. Post-briefing (07:15–08:00): two of eight agents had been working for nothing

Checking the dungeon for churn, I found the opposite problem. No churn — but Elara and Voss logged the
same line every ten minutes, all night: *"curation held to pending (standing 0.47)"*. They were each
spending a 120-second vault-scanning subprocess and having **every** result thrown away.

The gate was an absolute constant, `0.55`, applied to a score that is relative. Standing starts from
mean pairwise trust and then blends in hit-rate, mastery and bounty — and every blend pulls the number
*down*. The whole roster had drifted underneath it: the highest standing of all eight agents that
morning was **0.476**. The organ had never applied, not once. And it feeds back: an agent that
completes nothing loses standing for producing nothing, sinking further below the gate that stopped it.

A gate that has never once passed looks exactly like a working gate in the logs. Both are calm.

**Fixed** (`tools/autolinker.py`, commit `291d3e3`): gate on rank within the live roster, with an
absolute value kept only as a real floor. Voss immediately produced his first result — **33
true-duplicate groups, 89 redundant copies** in the vault, now in
`04 Resources/Concepts/Agora Agents/quality_report_duplicates.md`.

**Then unlocking it revealed a second problem, which is why nothing was left in your vault.** Elara's
first unlocked run offered **2931 links across 763 notes at once**, and its most-linked targets were
all bookkeeping — `orphans_*`, `quest-request-to-king-aldric`, daily `Falsification_*`. I let it write,
saw what it wrote, and reverted it line by line: **0 added link lines remain in any real note.** Two
guards went in before it may write again — a 25-note budget per run so a backlog drips instead of
flooding, and machine output excluded as a link *target*.

Worth saying plainly: my first attempt at that exclusion was a keyword blocklist, and it merely moved
the hub from `orphans_*` to `Archival_Candidate_2026*` — the exact error I had recorded as a permanent
rule ninety minutes earlier. The working version is structural: a dated snapshot family (three or more
filenames identical once the date is removed) and anything under an agent-output folder. 3979 notes now
excluded as targets; the links that survive point at real concepts.

Recorded as a permanent rule: `absolute-threshold-on-a-relative-score` — **never gate a relative score
with an absolute constant**, and when unlocking any organ after a long lockout, assume a backlog and
cap the first run.

**Update at 08:00 — she is live and there is a sample in your vault to look at.** Two live runs went
through (07:18 and 07:45) and I watched what they wrote. Two residual noise sources showed up and are
fixed (`54e7605`): a dated snapshot family now counts at two members rather than three, and a note can
no longer gain a link to another *copy of itself* — the Breaktruth newsletters exist as a spaced
title, an underscored title and a `Bridge_` prefix of the same words, so each was collecting three
links back to itself.

What is in your vault right now: **92 links across 25 notes**, one budgeted run. The links read
sensibly — `Cognoscope` → its own validation note and the Debiased Prompt Builder; `Stigmergic
Self-Awareness` → Theory of Mind and Stigmy; each Breaktruth newsletter → its one article note.
Look at a few. From here she adds 25 notes per run until the backlog is gone.

To undo all of it at any point: every line lives under a `## Related (AutoLinker)` heading and nothing
else was touched, so it is a mechanical strip — tell me and it is gone in a minute.

---

**State at 06:15:** brain and dungeon up, inbox 3 (all machinery or on-mission), **31 off-mission
births blocked overnight**, external library 392 items, `mnemo-repo` clean and pushed. The `agora`
repo has 20 unpushed commits — left for you, since a push to a public repo deserves a secret scan in
daylight rather than at dawn.
