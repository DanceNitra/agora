# Inbox plan — 2026-08-21

Owner: *"1 aj 2 aj 3 a postupne"* + *"zapis si vsetko do planu a prejdeme uplne vsetko postupne a dokladne"*.
One item at a time, measure each before moving on (change → observe → measure → next).

State of the queue when this was written: **39 pending**, oldest 2026-08-10, both servers healthy
(brain tick 564, dungeon 200). Scored against the board's own 24 `priority_terms`, not by eye.

| bucket | n | disposition |
|---|---|---|
| score 0 — off board | 6 | skip |
| score 1 on a single generic token (`agent`, `memory`) | 17 | stationery, not substance — skip unless it survives a read |
| saturated duplicates | 5 | keep newest, skip the rest |
| stubs with no content | 3 | skip |
| **real queue** | **~8** | below |

---

## TRACK 1 — the firewall pair (`ad2042` + `89f006`)

**Status: MEASURED. The belief the task asks me to model is refuted by our own later work.**

Two vault notes, both dated 2026-06-21, `theory_status: unmodelable`:

- `insight-grounding-firewall-is-adaptively-defeated-conditional-moat.md` (lab c0cf66) — the
  grounding-drop firewall loses its edge past ~32% adaptive poison and its defining signal flips sign
  (corr +0.52 → −0.36).
- `insight-firewall-defense-in-depth-decorrelation-restores-robustness.md` (lab 58454c) — the fix: a
  decorrelated second check "restores the firewall's edge across the entire adaptive range".

**The second note is wrong, and we already knew.** On 2026-07-06 a prior-art hunter killed the general
claim as textbook three times over (Krogh-Vedelsby 1995 ambiguity decomposition; Knight-Leveson 1986
common-mode failure; Carlini-Wagner 2017 / Tramèr 2020 — the adaptive adversary owns the attack
distribution). Then we measured it with **two real gates** instead of a knob.

Re-run today, `research/probes/gate_ensemble_coherence.py`, reproducing the July numbers exactly:

| forgery witness coherence | provenance false-allow | coherence catches | **AND-agreement false-allow** |
|---|---|---|---|
| 0.0 | 1.000 | 0.999 | **0.001** |
| 0.2 | 1.000 | 0.962 | 0.038 |
| 0.35 | 1.000 | 0.695 | 0.305 |
| 0.6 | 1.000 | 0.079 | **0.921** |

False-withhold cost on genuine recoveries: 0.075.

So the decorrelated pair does **not** hold at every level. It holds while the attacker is lazy. At
on-topic witnesses the two gates share the blind spot "plausible evidence" and 92% of forgeries get
through. The June note's own caveat said this would happen (*"if the second source is correlated …
ρ → 1 and the gain collapses"*) and then the summary claimed robustness anyway.

The difference between the two results is the difference between a **knob** and an **adversary**. The
June model set the adaptive fraction as a parameter; the July probe let the attacker choose it.

### TODO
- [x] read both notes in full
- [x] check prior art in our own memory before modelling
- [x] re-run the real two-gate probe this cycle
- [x] write the correction into the vault note 58454c — appended, not a rewrite; pushed via
      `safe_vault_push.py` (commit `fdd26205d9`, diff `1 A, 4 M, 0 D`, zero deletions)
- [x] mark `ad2042` and `89f006` done with the measurement as the result — queue 39 → **37**
- [ ] decide whether c0cf66's `adaptive-poison-firewall` belongs in the Methods Library (the note asks;
      it needs a brain restart to reach the agents, so batch it)

---

## TRACK 2 — the external map (`c822f7`, `5cee1a`) — **DONE**

- `c822f7` (08-10): *loudest need "provenance/trust" raised in 108 unrelated projects*
- `5cee1a` (08-18): same shape for *retrieval quality*, 35 projects

This is a market signal for inspeximus, not a note. Before treating it as one: **verify the 108 is a
count of real distinct projects and not a keyword hit**, the same way the source-coverage figure had to
be re-measured before it could be quoted. A number in a task description is not verified data.

### TODO
- [x] read both tasks in full
- [x] re-derive the count — the 108 is a PRE-REPAIR artifact. `external_library.AXIS` documents its
      own fix: the bucket was held up by bare `source`, 94 records alone ("fyxer or like api
      sourceforge?"); only 16 projects said provenance or attribution. Today: **19**, matching
      `5cee1a` exactly.
- [x] answered in a vault note (`safe_vault_push` `a03ed2b10d`, 1 A / 0 D) + cartography record
      `4002ea`. MEET: provenance/trust is the only axis whose whole top five is on topic (0% farm
      comment mass vs 79.7% for dedup/conflict); `microsoft/autogen` "Cryptographic action receipts
      for enterprise agents" (322 comments) is `witness()`/`verify_witness()` renamed. NOBODY ASKING:
      **revert/undo, 13 projects / 13 mentions / 1.00 per project** — last on both axes, the only
      need nobody raises twice, and it is our stated differentiator. Early, not imaginary, with a
      selling consequence and a stated falsifier.
- [x] instrument defect filed: `loudest` ranks by comment count, so a bounty farm
      (`Scottcjn/rustchain-bounties`, 1,432 comments) tops two axes. Ranking unaffected.
- [x] the completion gate REFUSED the close until the cartography ledger got an entry (474.6h empty).
      It was right. Landed the artifact, then closed.

---

## TRACK 3 — skip the dead tasks — **DONE, and reading them changed the list**

**13 skipped** via `gatekeeper/skip` + close. Queue **39 → 22**.

The plan said confirm each by reading it rather than by its score, and that condition earned its
keep: a blind bulk skip would have thrown away three live tasks that scored 1 —
`6ad22b` (a briefing on the OWNER'S OWN vault clusters), `a47fed` (a bridge to **MemOps**, our own
missing benchmark axis) and `e10a8d` (default-transparency attribution, squarely our axis) — plus
`c2431c`, which scores **0** and is about auditing **data leakage in benchmarks**, adjacent to RAMR.

Skipped, with the reason recorded on each:

| ids | why |
|---|---|
| `e21e6b` `6084cf` `48486b` `efd476` | `Forge analogy: Phase Transitions` fired **4×** onto arbitrary domains, three of them YouTube transcript ids |
| `68675d` `189be4` `883d4b` | Predict stubs — 23, 23 and 25 characters, a topic name and nothing else |
| `4d3e14` `a2d33d` | Dialectics off board (extension authoring, Qwen parity) |
| `122dd3` `b7c626` | Off frontier; each scored on the single word `agent` |
| `08ff92` | far-domain bridge — `external_library.py` documents this exact failure mode |
| `4624ec` | DeFi stability; finance is a TEST-BED, not the headline (CLAUDE.md §4) |

**A structural finding, not a historical one.** Six minutes after `5cee1a` was closed, the organ
queued `dcd381` with **byte-identical** headline figures. It was not a cadence bug — the generator
keys on the map's loudest need, the map is stable, so the same task regenerates every cycle whether
or not it was just answered. Closed as a duplicate with a note: it could key on whether the
cartography ledger has an entry for that need since the last map change, which is exactly the check
the completion gate already runs at close time.

Candidates, by reason:

**Off board (score 0) — 6:** `efd476`, `c2431c`, `a2d33d`, `6084cf`, `4d3e14`, `48486b`

**Saturated — same template repeated:** `Forge analogy: mechanism 'Phase Transitions' → …` fired
**4×** (`e21e6b` 08-14, `6084cf` 08-18, `48486b` 08-20, `efd476` 08-21). Keep at most the newest.
`Chart the external map` fired 2× (`c822f7`, `5cee1a`) — both kept, they are different subjects.

**Stubs — no content to work with:** `68675d` (*Predict: Product Design*, **23 chars**), `189be4`
(*Predict: Agent Identity*, 23), `883d4b` (*Predict: Emotional Memory*, 25).

**The instructive one:** `b7e0d2` scored **5 — the highest in the queue — and carries 0 leads to
answer.** Highest score, nothing to do. Another instance of the class we keep hitting: the score is
measuring the stationery, not the work.

### TODO
- [x] confirm each skip candidate by reading it, not by its score — it saved four
- [x] skip via the gatekeeper so the queue generators stop re-offering them (13/13 recorded)
- [x] re-count: **39 → 22**

### What remains (22), for the next pass
- **6 scout triages** (`b7e0d2` `1bcbf3` `5d2adb` `5ff405` `689453` `350918`) — outreach, gated. The
  older ones are probably dead: their issues have had 3–11 days to close. `b7e0d2` scores the
  **highest in the queue (5) and carries 0 leads to answer**.
- **on our axis:** `8e66b6` (memory-poisoning lead, Crucible candidate), `eb0599` (pipeline
  integrity), `c4fb68` (optimal forgetting read as miscalibration), `a47fed` (MemOps bridge),
  `e10a8d` (default-transparency attribution)
- **the owner's own material:** `6ad22b` — a briefing on real clusters in his vault, not the
  abstract frontier. Premium, and nothing else in the queue is like it.
- **gated drafts:** `18f093`, `77081f` — press pieces; both need the standing gate before anything.
- **needs a call:** `834831`, `a0719f` (replicating regret/PAC **proofs** — is a theory bound a
  computational replication?), `c2431c` (benchmark data leakage), `eb65c3`, `a66234`, `9bc1a0`,
  `ecd7e6`, `bd1903`

---

## Waiting on others (no action here)

- @Stratogain — the `witness_measuring` row on ramr#3, and whether the 2 h is a cap on the 3× rule
- @Guanghao Li — which observable/graph the EDRN control-edge subsection used
- anthropics/claude-code#82056, #81710 — replies

## Done today, for the record

- inspeximus **2.19.1** on PyPI, verified from a clean venv, PEP 740 attestation present
- `public/track-record.md` re-measured and live (234,557 records, 92.7%, re-checkable **zero**)
- replies sent: Causal-Memory-Layer#311, ramr#3
- `tools/humanizer_tells.py` — one tell list, constructions not words
