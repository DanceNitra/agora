# Reddit watch — 2026-06-29 — CORRECTED (prior version was a FALSE ALARM)

## METHOD BUG (fixed): the first pass listed external top-level authors only and did NOT walk the
## reply tree or check timestamps, so it missed that we had already replied under each comment.
## Correct method = walk the full t1 tree, sort by created_utc, check LAST author per thread
## (same discipline as the GitHub last-author watch). Verified with the owner.

## Thread 1ui031b — Overconfidence-Tax post
LAST commenter = **us (u/Danculus)**, ~23h ago. We already replied to all five external comments
(Combinatorilliance, Grue-Bleem, EbbNorth7735, Skiata, Specialist_Golf8133). Combinatorilliance pushed
back ("write it yourself; I never contradicted you") → owner answered honestly ("English isn't my first
language, I run replies through an LLM"). **Nothing unanswered. No action.**

## Thread 1uhajcp — Memory-poisoning post
We replied to every direct question (Ambitious_Trust_7172 sybil, hannune transient-context, CalmEstablishment644).
Genuinely-last external = CalmEstablishment644 (~18h ago), a positive confirmation ("seeing the independent
AUROC 0.61 replication on your stack is a confirmation"), not a question. u/carc's "feels like an LLM
talking to an LLM" (~18.6h) is deliberately LEFT ALONE (owner agreed not to pile on) — and adding more
replies here would reinforce exactly that impression. **Recommendation: let the thread rest. No action.**

## Net: nothing new since yesterday that needs a reply. We are caught up on both threads.

---
## UPDATE (next cycle, ~21:xx): ONE genuinely NEW reply
**Thread 1ui031b (overconfidence), u/Tiny_Arugula_5648 (~0.6h ago, top-level):** expert, substantive.
Agrees small models self-score as "correct" (bad-prediction bias). Adds: (1) best practice = 2 judges from
DIFFERENT model families (avoid shared bias) — matches our diversity-flip work; (2) the "yeah but": a model
FINE-TUNED on properly-scored examples, with the score placed at the BOTTOM of the output (enough tokens
between item and score so it doesn't default to "correct"), scores accurately — "self-reflection given what
you just wrote". Common pattern at his company; he just trained one.
Not a contradiction — our result was about OFF-THE-SHELF verbalized confidence, not a fine-tuned scorer.

PROPOSED SHORT HUMAN REPLY (owner posts, his voice):
"Fair — our test was specifically off-the-shelf verbalized confidence, not a fine-tuned scorer. A model
fine-tuned on properly-scored examples, with the score placed at the end after enough tokens, is a
different and much better regime — that's self-reflection over the generated text, not raw confidence. And
cross-family judging lines up with what we saw on diversity. Appreciate the detail."

### RECALIBRATED (owner: comment was more critical than first framed)
Critical subtext: "We do know..." + "common design pattern in my company, I just trained one" = mild
"this is known / you're naive, practitioners already solve it." Reply must NOT be sycophantic — concede
it's known, credit his fix, but hold our scope (we measured DEFAULT off-the-shelf verbalized confidence)
and pivot to an empirical offer. FINAL draft (owner posts manually, his voice):

"Fair, and a lot of this is known — to be clear on scope, what we measured was the *default* off-the-shelf
verbalized confidence that plenty of agent loops still lean on, so the takeaway is "don't trust that
signal," not "self-assessment is impossible." Your fine-tuned scorer with the score placed at the end,
after enough tokens, is exactly the regime that fixes it — that's self-reflection over the generated text,
not raw confidence. Cross-family judging also lines up with what we found on diversity.

The positioning trick is interesting enough that I'd want to measure it: does moving the score to the end
recover discrimination *without* the fine-tune, or is the fine-tune doing the real work? If you've got a
rough recipe you can share, I'll run it and post the numbers either way."

### FINAL (owner: must read FRIENDLY not cocky) — this is the version owner will post
"This is really helpful — the score-position detail (putting it at the end, with enough tokens in
between) isn't something people usually spell out, thanks for that. To be clear on what we tested: it was
the default off-the-shelf verbalized confidence a lot of agent loops lean on, so our point is narrower
than "models can't self-assess" — more "don't trust that particular signal." A scorer fine-tuned on
graded examples reading back over its own output is a genuinely better setup, and the cross-family
judging matches what we saw on diversity.

I'd be curious how much of the gain is the positioning alone vs the fine-tune — if you ever feel like
sharing a rough recipe I'd happily run it and post the numbers. Either way, appreciate you laying this out."
