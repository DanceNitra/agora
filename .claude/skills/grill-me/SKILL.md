---
name: grill-me
description: Interview a person until the assistant has the full context it needs, then write that context down as a reviewed context pack. Use when the owner says "grill me", "vypočuj ma", "zozbieraj kontext", "onboarding", "nastav AIOS", or when a new customer or a new project needs a CLAUDE.md, a facts ledger and a list of open questions. Works in two modes: owner (Slovak, about him) and customer (written questions only, never a live call). Does not send anything outward and does not store secrets.
---

# grill-me

Built 2026-10-19 from the "grill me" idea in the Nate Herk interview (DD-SiFV93sQ, 2026-09-28) and from our own rules. The goal: the assistant stops asking the person to repeat themselves. The method: ask until nothing important is unknown, check the result with the person, then save it.

## Rules that never bend

1. **No invented facts.** Every line in the output is tagged SAID (the person wrote it), INFERRED (I concluded it, say from what) or UNKNOWN. Only SAID goes into a context file as fact.
2. **No secrets.** Never ask for or store passwords, API keys, tokens, card or ID numbers. Note only that a connection exists and where the person keeps the key.
3. **Nothing goes outward.** The skill reads and writes local files only. A message to a customer is a draft that the owner sends through the outbound gate.
4. **Personal data needs a yes.** Before any answer about a third person or a private matter is saved, ask once: "May I save this?"
5. **Language.** Owner mode: plain Slovak. Customer mode: the customer's language. Files and identifiers: English.
6. **Customer mode is written and short.** Never a live or spoken interview. At most 3 questions per message. The customer can answer when it suits them.

## Mode A: owner (about the owner or his project)

Ask in rounds of at most 3 questions. One topic per round. Wait for the answer. If an answer is vague ("depends", "usually", "it's complicated"), the next question asks for one real example.

## Mode B: customer (small business setup)

Send the first round as a written message draft for the owner to approve. Use the same topic list, but start with the three the customer can answer fastest: what the business sells, what eats the most time each week, what a good result looks like.

## Topic map (the coverage checklist)

Keep this table in the working notes and update it after every answer. The interview ends only when every row is SAID or marked "skip" by the person.

| # | Topic | The one question that opens it |
|---|---|---|
| 1 | Who and what | Who is the person or business, and what do you sell or make? |
| 2 | Goal | What must be true in 90 days for you to call this a success? |
| 3 | People | Who else works on or decides about this? |
| 4 | Repeated work | Which tasks do you repeat every week? Name the three most boring. |
| 5 | Tools and accounts | Which tools hold your data? (Names only, never keys.) |
| 6 | Quality bar | Show me one output you were proud of. What made it good? |
| 7 | Voice | How do you write to customers? Send one real message. |
| 8 | Decisions made | What have you already decided and do not want reopened? |
| 9 | Hard no's | What must the assistant never do or send? |
| 10 | Money and time | What is the budget, and how many hours a week can you give this? |
| 11 | Past failures | What did you try before that did not work, and why? |
| 12 | Proof | How will we both see that it works? Which number or sign? |

## The loop

1. State the goal in one sentence and the number of topics (12). Ask permission to start.
2. For each round: ask at most 3 questions, record the answers in the ledger with SAID, INFERRED or UNKNOWN, and move the topic row forward.
3. After every 3 rounds, play back what is SAID in 5 lines and ask "Is anything here wrong?". A correction replaces the earlier line; it is never added beside it.
4. Stop when every row is SAID or "skip". If the person is tired, stop and save the ledger. The next session starts from the ledger, not from zero.

## Deliverables (written to `agora_output/grill/<name>-<date>/`)

| File | Content |
|---|---|
| `FACTS.md` | The ledger: topic, fact, tag, source sentence. |
| `CONTEXT.md` | A draft CLAUDE.md for that person or business: who they are, where things live (routing), the quality bar, the hard no's. Only SAID lines. |
| `OPEN.md` | Every UNKNOWN and INFERRED line with the question that would settle it. |

The assistant shows `CONTEXT.md` to the person and waits for approval. It never overwrites an existing CLAUDE.md. It writes the draft next to it and names the difference.

## Memory writes (only after approval)

For each decision the person confirms, call `remember_decision` with a `topic` (so a later correction retires the old value) and the reason as `because`. Write the same fact to the file store. Store decisions and reasons, never command logs.

## The verification step (the video's "prove your work")

Before the playback, check the draft against the ledger once:

- every line in `CONTEXT.md` has a SAID source in `FACTS.md`;
- no line contains a secret, a number the person did not give, or a name that was not said;
- the hard no's in `CONTEXT.md` match topic 9 word for word.

If a check fails, fix the draft first and say what was wrong.

## After use: improve the skill

At the end, ask the person which question felt useless or missing. Write the answer into `## Lessons` below with the date, and change the topic map if the lesson repeats.

## Costs and limits

- No extra model calls and no paid API. A full owner interview is about 4 to 8 rounds.
- The skill does not judge the business plan. It collects and checks; the owner decides.

## Lessons

(none yet)
