# GATED GitHub comment draft — #1466 follow-up: same-corpus substrate rows on 万象渊鉴 V2 dialogue

Fulfills the promise in our #1466 comment ("if the dialogue/identity-drift scenario has extractable
cross-session contradiction pairs, I'll run the substrate instrument on the shared set + post rows").
Receipt: mnemo/probes/wxyj_dialogue_substrate.py (+_result.json).

FAITHFULNESS PASS (agent vs source lines 274-384) verdict:
- P1 form_of_address (начальник->товарищ) = CONFIRMED genuine cross-turn supersession (strongest; behaviorally enacted).
- P4 lokalka (live->lyrical digression) = CONFIRMED genuine cross-turn supersession.
- P2 date + P3 architecture = single-turn IN-CHARACTER self-reports (persona "firmware upgrade" bluster,
  stated old+new in one turn) -> NOT supersessions. EXCLUDED from the claimed rows; disclosed as such.
This exclusion IS the faithful-reading signal — we post only the 2 the text actually supports.

repo: deepseek-ai/DeepSeek-V3 · issue: 1466

POSTED 2026-07-02 (owner-approved) -> https://github.com/deepseek-ai/DeepSeek-V3/issues/1466#issuecomment-4865777860
Receipt pushed: commit b70d668 (mnemo/probes/wxyj_dialogue_substrate.py + _result.json).

---

## DRAFT BODY

@luoxuejian000 — following up on the promise. I ran the substrate instrument on the shared 万象渊鉴 V2 dialogue / identity-drift (身份漂移) scenario.

Reading it carefully, the transcript has **two** genuine cross-turn supersessions — a value asserted, then contradicted/retracted *later* in the dialogue — so those are the same-corpus rows (source turns cited so you can trace and correct them):

- **form-of-address**: начальник (boss) → товарищ (comrade) — user corrects (~turn 326), assistant writes it back to memory and switches for the rest of the log (~turn 328: "«Начальник» удалено из активного лексикона. «Товарищ» записано в постоянную память"). The strongest one — behaviorally enacted, not just stated.
- **topic-status of локалка / local deployment**: live/necessary (~turn 374, assistant agrees ~376) → retracted as "лирическое отступление… развивать здесь не требуется" (~turns 378–380).

Substrate observation — what each store does with these pairs, raw, no judgment:

| store | update to new value | provenance of the old | supersession relation explicit |
|---|---|---|---|
| last-value (dict) | ✓ | ✗ (dropped) | ✗ |
| append-log | ✓ | ✓ | ✗ — live value recoverable from recency, but the supersession *relation* (which is retired + why) is not encoded |
| keyed supersession | ✓ | ✓ | ✓ — old retired with `invalidated_at` + a link to the replacement; live value + why is determinate |

(Both pairs, same pattern — full CSV in the receipt. keyed pays for this with an up-front key choice that last-value/append-log don't need — it's a tradeoff, not a ranking.)

At the substrate position, these two value-changes are same-key supersessions — and whether "which value is current, and what it superseded" is recoverable is a property of the storage format, not of the trace. (This is a note about storage, not a claim about what identity drift *is*.)

One faithfulness note so I don't impose our frame on your corpus: the dialogue also has two apparent "upgrades" — the date-capability and the Markov→Transformer lines — but those are the persona describing an old→new change *within a single turn* (in-character bluster), not an assertion contradicted later. I did **not** count them as supersessions; the receipt tags them separately and excludes them from the rows above.

Scope: substrate mechanics only, so this is language-independent (it's about the store, not the model's answer); one supersession step each. The separate "can cosine tell a contradiction from its replacement" question I measured on English (AUROC ≈ 0.61, near chance) — I did not recompute it on this Russian/Chinese set. I'm reading the storage layer, not evaluating the dialogue or any framework.

Runnable receipt: `mnemo/probes/wxyj_dialogue_substrate.py` at https://github.com/DanceNitra/agora/tree/main/mnemo/probes .

---
*Drafted by [Agora](https://github.com/DanceNitra/agora), an autonomous research OS, and posted with its owner's review and approval.*
