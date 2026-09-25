---
name: outbound
description: The ONLY way any text leaves Agora (GitHub comment, PR, reply, post). One text, under 100k tokens, gate and seal included. Use for every outbound draft, every "posli", every seal. Mechanics are tools/outbound.py (0 tokens); the model writes the draft and runs ONE gate subagent.
---

# Outbound: one text, under 100k tokens

Owner rule, 2026-09-25: one outbound page costs under 100k tokens, gate included. On 2026-09-24 one
page cost millions because every step ran by hand in a session with a 94%-full context. Every step
that needs no judgment is a script. Do not rebuild any of it by hand, and do not re-derive this
procedure: follow it.

## The six steps

| step | command | model tokens |
|---|---|---|
| 1. start | `python tools/outbound.py new SLUG --thread owner/repo#N --sign github\|edrn [--kind pr]` | 0 |
| 2. write | write `agora_output/outbound/SLUG/draft.md` and `claims.py` (one claim per figure) | the draft |
| 3. lint | `python tools/outbound.py check SLUG` until it prints `all N checks pass` | 0 |
| 4. gate | `python tools/outbound.py gate SLUG` prints ONE subagent prompt; run it once, model `sonnet`; record the three receipts it prints | 40-60k |
| 5. seal | `python tools/outbound.py seal SLUG --inputs <source files>` (render, receipt, log, stamp, SVG pair, footer) | 0 |
| 6. owner | `python tools/outbound.py show SLUG`, send him the two render PNGs with SendUserFile, then wait for `posli <6 hex>`; then `python tools/outbound.py post SLUG --sha <full hash>` | small |

`python tools/outbound.py status` shows every text in flight and its next command. Run it first after
a restart or a compaction instead of reconstructing state from memory.

## Rules that save the tokens

- **Run the whole text in a SHORT session.** The main session only commissions it. A long context
  multiplies every turn. Compact any session at about 40%, not 94%.
- **Freeze the text before step 4.** An edit after the gate invalidates the receipts by design and
  costs a new gate run. Fix everything `check` reports first.
- **Never paste the draft into chat.** The owner reads the render and answers `posli <first 6 hex of
  the sha>`. `tools/owner_spoke.py` accepts that reply (owner decision 2026-09-25, commit e415da30).
- **One gate subagent, not a panel.** Humanizer, verify-claims and stress-claim run inline inside it,
  each once. No storm unless the claim rests on literature rather than a re-runnable artifact.
- **Not other people's work.** If their question needs a computation they can run, send the script,
  not our result. Before any run over 100k tokens, tell the owner the cost and wait.
- **Over budget: stop and say so.** Never finish a text silently at 300k.

## Where each piece goes

| piece | place | never |
|---|---|---|
| draft, claims.py, receipts, renders | `agora_output/outbound/SLUG/` (local, private) | any repo push |
| seal SVG pair | `DanceNitra/inspeximus` `docs/seal/` (seal_draft.py does it) | anything else into inspeximus |
| a probe the text links to | public `DanceNitra/agora` `probes/`, via the `C:/Users/Danculus/_pubmain` worktree, only that probe and its result, owner sees the file list first | pushing our working branch |
| physics scripts for EDRN | the `DanceNitra/edrn-dmrg-verification` fork branch | agora or inspeximus |
| session reports, strategy, plans | `agora_output/strategy/` (private) | any public place, any link in a comment |

inspeximus holds only the product and its seals. It is not a storage place for our outreach.

## What stays exactly as before

The gate is still the three SKILLS with receipts (`tools/humanizer_receipt.py`), the seal is still on
every text (`send_approved.py` refuses without it), the owner still approves every send, EDRN is
signed "Rastislav Drahoš, Agora Research OS" with no AI disclosure, and gh payloads stay pure ASCII.
`outbound.py check` enforces the last two.
