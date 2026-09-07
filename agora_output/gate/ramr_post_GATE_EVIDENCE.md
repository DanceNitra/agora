# GATE EVIDENCE — RAMR memaudit post (draft 20260907)

Draft: agora_output/drafts/20260907_ramr_memaudit_DRAFT.md

## 1. VALIDATE — every number vs its persisted source

| # | claim in post | source file | status |
|---|---|---|---|
| 1 | 97.2% floor / 96.0% coverage (v0.2) | ramr-repo README.md:60 | OK |
| 2 | 96.8% / 52.7% (v0.3 re-cut) | ramr-repo README.md:61 | OK |
| 3 | 40.0% / 1.7% (v0.5) | ramr-repo README.md:62 | OK |
| 4 | LoCoMo 36.3% / 44.3% "for our framing" | ramr-repo README.md:63 (+framing caveat :80-82) | OK |
| 5 | 73% → 83% cue inversion | ramr-repo README.md:87 | OK |
| 6 | id rule fires 136–148 of 300; right on 95.2–100.0% OF THE FIRES; null ≤1.0% | ERRATA.md §4 + ramr_id_cue_reconstruction_result.json (min 136 / max 148 / acc 0.952–1.0 / null ≤0.0096 / verdict 205_OF_300_DOES_NOT_REPRODUCE) | OK |
| 7 | envelope widens: 5 runs 138–143, 20 runs 139–146, 100 runs 136–148 | ERRATA.md §4 | OK |
| 8 | "205 of 300 does not reproduce" + "reconstruction, not the original run" | ERRATA.md §4 scope + result JSON .scope | OK |
| 9 | echo shortcut 98.6% (204/207); echo+case 98.9% at 87.7% coverage; recurrence 206/300 vs 5/300 | ERRATA.md §3 | OK |
| 10 | "205 had no receipt" — three files named | ERRATA.md §4 (memaudit.py, ramr_traces_v03_recut.py, README.md) | OK |
| 11 | CI: 0 of 8 fire on clean; planted cue 100.0% vs 0.0% null | ramr-repo README.md:74 | OK |
| 12 | Feng/Wallace/Boyd-Graber ACL 2019 quote + link | ramr-repo README.md:78 (P19-1554) | OK |
| 13 | closed-book ~0 by construction | ramr-repo README.md Design principles | OK |
| 14 | positional invariant was found by an EXTERNAL reviewer (audit reframe 1) | ramr-repo README.md:83-84 | OK |

Corrections the validate pass forced INTO the draft (before any gate step signed off):
- "before I used the benchmark for anything" → removed (v0.1 findings existed);
  replaced by "beside the results it could have inflated".
- Added the still-open ERRATA defect 1 (ids not content-addressed) to Honest limits.

## 2. STORM — four perspectives, pre-audit

File: agora_output/gate/ramr_post_STORM.md
Fixes forced into the draft: 1 (the alternative-to-publishing sentence — a stranger finds the
leak without the ERRATA trail).

## 3. AUDIT — stress-claim adversarial pass

File: agora_output/gate/ramr_post_AUDIT.md
Verdict: **REFRAME** (three reframes, all applied):
1. External reviewer credited for the positional invariant (300/300) — we did not find it first.
2. Floor/null rule: the post's own "report floor AND null or neither" now holds in-post
   (per-probe nulls: echo 1.7%, id ≤1.0%); the ramr-repo README TL;DR row got the same
   fix (pushed 5a2aadc).
3. Precision: "fires on 136–148 of 300 AND right on 95.2–100.0% of those fires" — the
   earlier phrasing conflated fires-of and right-of.

## 4. HUMANIZER — skill v2.8.2 applied

11-point scan; 4 fixes applied to the draft:
- cut signpost sentence ("This is the part I did not expect...")
- folded "Here is the actual lesson." opener into the paragraph
- varied "published" repetition (2 instances re-worded)
- em-dash density reviewed; kept where load-bearing

## 5. VERIFY — numbers vs artifacts

Same table as VALIDATE (each row re-checked at final text). All 14 rows OK.

## 6. RECEIPTS — deferred to the send flow, stated plainly

tools/humanizer_receipt.py requires --evidence under the session /tasks/ directory
(skill/subagent transcripts). This session runs in Codex, where that transcript
infrastructure does not exist; fabricating a path is exactly what the tool refuses and
what the owner prohibited ("zakazujem vytvarat si skripty na obchadzanie").
The three bindable receipts (humanizer / redteam / verify) are therefore to be
recorded in the Claude Code pipeline during send_approved.py flow, against this
draft's final bytes. Until then the draft is gate-REVIEWED, not send-approved.
