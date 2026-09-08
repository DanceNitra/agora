# Handoff, 2026-09-08

Written because the inspeximus write path is dead and this session's decisions could not reach the
store. Everything a restart needs is here, including the three decisions to re-write once the MCP
connection is back.

---

## 1. DO THIS FIRST: restart the MCP connection

**Our memory has not been written since 2026-09-07 20:22.** Four consecutive `remember_decision`
calls today were refused with `StoreChangedOnDisk`. Nothing was lost: the single-writer guard refuses
rather than clobbering, which is correct.

The cause is a stale build, not a design flaw. Three `inspeximus-mcp` processes run against
`~/.inspeximus/mcp_memory_chain.json` from two uv archives, **2.24.1** and **2.26.1**. The row-store
merge that avoids this landed in `b411754` on 2026-09-07 and ships in **2.27.0**. Neither running
build has `_merge_rows_from_disk`.

Restarting Claude Code makes uvx resolve 2.27.0. Verify afterwards with `where_am_i`: it must report
a version of 2.27.0 or later, and a `remember_decision` must return an id.

A narrower gap survives the upgrade and is fixed in `83c8e55` on inspeximus main: `reload` was never
an MCP tool and `StoreChangedOnDisk` appeared zero times in `mcp_server.py`, so on the JSON store
path a client still had no recovery. The write methods now reload once and retry.

---

## 2. Three decisions that must be written to inspeximus after the restart

These are already in the file store under `~/.claude/projects/C--Users-Danculus-agora/memory/` and
indexed in `MEMORY.md`. They are NOT in inspeximus, because of the above.

**topic: `outbound-gate-cost`**
The outbound gate now runs at a proportional tier, and a skill invoked in session counts as evidence.
`tools/gate_tier.py` decides whether red-team and verify need a subagent panel; `tools/skill_ran.py`
reads the harness's own `tool_use` record, which `humanizer_receipt.py` accepts via `--in-session`.
All three receipts stay required at every tier. Because: the receipt tool accepted only a subagent
transcript, so the gate cost an agent panel on a 35-word note and the owner stopped it. A `tool_use`
record cannot be written into this session's own transcript without calling the tool, so the cheap
path is stronger evidence than the expensive one. Commit `bfc8f05`.

**topic: `zero-results-need-a-positive-control`**
Before publishing any claim resting on a zero, inject a synthetic target into a copy and require the
instrument to find exactly it. If it cannot, the verdict is VOID rather than zero. Because: the count
of retired rows still referenced read 0 of 40, 0 of 18, 0 of 35 and 0 of 54, and across all 26
snapshots there are zero cross-line references at all, so the counter never had a target. The reading
before that was 37 of 54, an artifact of rows sharing one physical line.

**topic: `read-the-source-before-drafting`**
Read the source in full before writing the reply. Two drafts today were misdirected: the #91188 table
dated every event by its snapshot rather than by the archive, and the EDRN letter warned a co-author
against over-retracting when his own point 3 already said the rest of the paper was unaffected. Both
were caught by an adversarial pass, not by me.

---

## 3. What went out today, and what is waiting

**anthropics/claude-code#91188** — comment `5588661516` sent 16:44, transport verified. The
retirement cause class: our archive heading said "to fit the loader window" while the tool's own
commit message recorded a content criterion. @pm25coder replied at 17:01 in comment `5588867420` with
four points. **Unanswered.** He asks for a per-row manifest, separates layout adaptation from a
row-addressability bug, and proposed the re-creation metric.

**luoxuejian000/edrn-dmrg-verification#2** — comment `5589572006` sent, transport verified. Guanghao
withdrew his own involution section after exhaustively falsifying it; the letter agrees with his
scoping, supplies the mechanism, and catches that his own proposed restricted wording restricts on
non-degeneracy while 39 of his 84 counterexamples are non-degenerate. He owes us the paper version;
we owe him mark-up, not edits.

**punkpeye/awesome-mcp-servers#10649** — comment `5586172678` sent. Merge conflict resolved by
rebase, PR is MERGEABLE, check-submission passes. Waiting on the maintainer.

**DanceNitra/agora discussions/2** — the MemStrata letter went out as `18350141`. Waiting on Neeraj.

---

## 4. Measurements finished after the last comment, not yet published anywhere

Both on main, both with controls, both answering things pm25coder asked for.

`probes/packing_the_index_evicted_rows_nobody_judged.py` — the 15 rows that left by sharing a line
with a judged neighbour are cited by other notes at a median of 3.0, against 0.5 for the 32 the tool
judged and 3.0 for the rows still live. Permutation over 20,000 relabellings: judged against
adjacency p = 0.0068, adjacency against live p = 1.0000. The rows nobody evaluated look like the rows
that stayed.

`probes/a_retired_row_that_comes_back_is_the_cap_charging_twice.py` — re-creation rate 1 of 93 rows
where a window exists (1.1%). The cohort he asked about, the 15, has **zero** later snapshots, so for
them the metric is absent rather than low. It becomes answerable at the next trim.

Together these are the substance of a reply to `5588867420` when the owner wants one.

---

## 5. Repository state

- `agora` main is at `19848e7`; `integration/dungeon-alpha-omega` points at the same commit. They
  were merged and both pushed today, after main had diverged by 14 commits.
- `inspeximus` main is at `83c8e55`, CI green on the earlier `e7a0d19`.
- **38 uncommitted files** in agora, mostly receipts and work in progress. Deliberately not pushed.
- Today's memory index work: 505 files, 0 in neither index, 227 pointers delivered, both loader caps
  respected. Four rows were retired to the archive under a heading that states its cause class.

---

## 6. Open, in priority order

1. Restart the MCP connection, then write the three decisions in section 2.
2. Reply to pm25coder's `5588867420` using the two measurements in section 4. Gated.
3. The inspeximus silent-loss question is still open: CI reported 1 of 84 records lost with 8
   concurrent writers, 36 local trials reproduced nothing, and commit `9822f74` instruments the test
   so the next failure names which records vanished and in what shape.
4. Guanghao owes us his paper version; we owe him mark-up on the passages, never direct edits.
