# 24 Brand-Guardian: voice card, red lines, series consistency, checklist

Episode: "Echoes of Tomorrow", outside outcomes, not ranking. Date: 2026-09-28.
Status: rules for the curator. Nothing posted, sent, committed, or pushed.

## Three lines before the rules

- Optimized for: rules the curator can check mechanically against the merged package, each with a
  do/don't written for this episode, not for podcasts in general.
- Rejected: taste verdicts dressed as vetoes, and a copy of episode 1's promo pattern where episode 1
  broke a rule set later (competitor names, model-rendered lettering, violet glow).
- Why: my veto covers measurable breaches only. Everything else in this file is labelled as a
  recommendation, and the owner decides taste.

## Sources read

- Role card, personality mirror, and Pamat mirror for 24.
- `crew/BRIEF.md` and the article `public/posts/src/decision-memory-needs-outside-outcomes.en.md`, in full.
- Storefront copy in `index.html`: "Your agent said it deleted that. We measured otherwise."
- `public/posts/src/memory-defense-veracity-gap.en.md`: an older voice (bold, em dashes), so the
  outside-outcomes article is the voice reference, not that post.
- Owner rules: our-posts-are-about-us-not-competitors, never-chase-a-leaderboard-number,
  design-restraint-not-ai-slop.
- Episode 1: `agora_output/episodes/verify-agent-memory-deletion/spotify.md`, `cover.png` and
  `cover_source.png` (both seen as images), and its `x.md` and `linkedin.md` promo.
- The three crew reports already in this folder (titles, cover, campaign), for early findings.

No audio, transcript, or `check.json` exists for this episode on disk (searched
`agora_output/` for the slug on 2026-09-28). Every rule that depends on the audio is marked.

## 1. Voice card

Eight rules. Each is testable on the text.

**V1. Lead with the measured number.**
- Do: "Lessons that carried a confirmed outcome lifted Claude Opus 5.5 from 0.594 to 0.750 on 160 engineering judgment forks."
- Don't: "What if your agent's memory is lying to you?"

**V2. Say what we set out to show, and that the result came out narrower.** This is the Agora signature: we publish what failed.
- Do: "We set out to show that better recall makes an agent choose better. The result is narrower."
- Don't: "Our research reveals what really makes agent memory work."

**V3. Every comparison carries its interval, or it is not said.**
- Do: "Ranking added 0.019. The 95% interval is -0.031 to +0.069, so this run cannot tell it from zero."
- Don't: "Ranking added almost nothing." (No interval, and "almost nothing" is a verdict the run cannot give.)

**V4. Noir is a frame of nouns, not a costume of voice.** Suspect, alibi, lead, forged evidence, witness: yes. Pastiche slang, puns, and closed-case language: no. The case is not closed, and the copy must not say it is.
- Do: "The prime suspect, similarity ranking, has an alibi: random lessons from the same repository got within 0.019 of it."
- Don't: "Case closed. The ranker's been framed, see." Also don't: "The ranker is innocent." The noir verdict that matches the data is "not proven".

**V5. The copy is about us. Name no competitor.**
- Do: "inspeximus can recall only the memories whose outcome was credited from outside the agent."
- Don't: "Unlike other memory layers, which rank by similarity..." (A comparison with no one named still reads as an attack, and this run tested no other store.)

**V6. Every product sentence names the switch and says it is opt-in.**
- Do: "In the Python API, `recall(influence_only=True)` returns only corroborated memories. `credit_requires_warrant` is off by default."
- Don't: "inspeximus keeps poisoned lessons out of your agent."

**V7. Google developer style, in full.** Short sentences, active voice, no "should", a colon between an item and its description, sentence case, no emoji, no exclamation marks, at most one hashtag, timeless (no "new", "now", "latest"), none of the brief's banned words.
- Do: "Qwen judging itself: 0.044 below no lessons, interval -0.087 to 0.000."
- Don't: "Game-changing new results - you should rethink your memory stack!"

**V8. Close on the receipt, not on a call to hype.**
- Do: "Every number is printed by one script: research/probes/taste_outcome_not_ranking.py"
- Don't: "Don't miss this one." or "Smash that follow."

## 2. Red lines

Any of these in the merged package is a veto. Each has the wording that replaces it.

| # | false or unestablished statement | why | correct wording |
|---|---|---|---|
| R1 | "Ranking is useless", "similarity search doesn't matter", "ranking failed" | Interval -0.031 to +0.069 includes gains up to about 0.07 | "Ranking added 0.019 (-0.031 to +0.069). This run cannot tell it from zero." |
| R2 | "This run cannot tell our ranker from zero" (campaign X post 1) | The ranker scored 0.769. Its gain is what cannot be told from zero | "cannot tell the ranker's gain from zero" |
| R3 | "The ranker is innocent / cleared / acquitted" | The run cannot exclude a gain below about 0.07 | "The ranker has an alibi", paired with 0.019 and the interval |
| R4 | "inspeximus prevents, detects, stops, or catches memory poisoning" | The outside credit was the dataset label | "Recalling only outside-credited lessons restored 0.825. The credit was the dataset's own label, so this shows what the gate does with the signal, not that it detects an attack." |
| R5 | "inspeximus does this by default / automatically / out of the box" | Opt-in; `influence_only` is Python API only; `credit_requires_warrant` is off by default | "opt-in: `recall(influence_only=True)` in the Python API; `credit_requires_warrant=True`, off by default" |
| R6 | "inspeximus made Claude better", "inspeximus lifted scores by 0.156" | Random same-repo lessons, with no inspeximus ranking, gave the 0.156 | "Lessons with confirmed outcomes lifted Opus from 0.594 to 0.750 at random, and to 0.769 by inspeximus recall" |
| R7 | "Project memory helps", "scope memory to the project", "repository context is the key" | Not established; the Opus run had no cross-project arm | Do not use. `remember(project=...)` may be named as a feature, never as a measured benefit |
| R8 | "Self-reflection hurts agents", "agents can't learn from themselves" | One model (Qwen), -0.044 with interval reaching 0.000 | "When Qwen judged its own choices, its lessons scored 0.044 below none (-0.087 to 0.000)" |
| R9 | "The outcome did the work" / "outside outcomes are the key to agent memory" as a general law | One benchmark, one domain, 160 forks, lessons carry the true outcome (a ceiling), 29% near-duplicate forks | Article wording: "The part of agent memory that carried the result is the outcome, and who confirmed it." Add "on these forks" when space allows |
| R10 | "Poisoning cut Opus from 0.750 to 0.637" or any mix of the two runs | The poisoning run is separate, default effort, clean 0.825 | "In a separate run, flipped twins cut 0.825 to 0.637" |
| R11 | "Half of real agent memory is poisoned" or flipped twins as a realistic attack rate | The store is deliberately extreme | "a deliberately extreme store where about half of every recalled set is wrong" |
| R12 | "26% better", "a 3% ranking boost", or any derived percentage | Not in FACTS; relative percentages inflate | Absolute scores and differences from FACTS only |
| R13 | Qwen 390-fork +0.115, Gemma +0.056, 86%, 29%, 0.669 used as a headline | 0.115, 0.056, 86% and 29% are in the article, not in FACTS | Promo uses FACTS numbers only. 0.669 is in FACTS, and it may appear only as "a two-line rule with no model scored 0.669" |
| R14 | "A two-line rule beats Claude" | 0.669 beats only the no-lesson arms, not the lesson arms | "A two-line rule with no model scored 0.669, above every no-lesson arm" |
| R15 | "Agents write better code with memory" | The task is judgment forks with both orders correct, not code generation | "engineering judgment forks", "chose the step whose branch had the better recorded outcome" |
| R16 | "Our benchmark" / "Agora's Taste-Bench" | Taste-Bench is Pan et al., arXiv 2609.25804 | "Taste-Bench (Pan et al.)" |
| R17 | "inspeximus scores 0.769" as a product score, or any leaderboard framing | 0.769 is one arm of our experiment; owner rule: never chase a leaderboard number | "the top 3 by embedding similarity (inspeximus recall): 0.769" |
| R18 | "We proved", "first", "breakthrough", "the future of agent memory" | Banned words; the claim is narrow | "We measured", "this run shows" |
| R19 | A host line quoted from the audio that carries a number or name not in FACTS | NotebookLM paraphrases; ep1's transcript produced "MemZero", "Qdrent" | Quote the host only after `check.json` is ok and the line matches FACTS word for word |
| R20 | Claude or Anthropic presented as partner, sponsor, or endorser | Opus 5.5 is the model under test, nothing more | "Decider: Claude Opus 5.5 at medium effort" |
| R21 | DANCHI brand, music, or art in the promo | Owner decision 2026-09-23: inspeximus and Agora are not DANCHI; P17: Danchi's own art is never redrawn. The show shares its name with a DANCHI track | Podcast promo carries Agora and inspeximus only. The cover never borrows DANCHI artwork |

## 3. Series consistency

Only one episode exists: "Deleted, but still on disk: what five agent memory stores keep after
delete()" (Spotify episode 7khBL2ppx1uTfsY9UtuLMJ, show 22RLIwyxmJW2mfGyMEHSmG). "Series" means one
precedent. Where that precedent breaks a later rule, the later rule wins, and the list says so.

### Must match

1. Title pattern: a short hook phrase, a colon, a plain explanatory clause, in sentence case.
   Episode 1: "Deleted, but still on disk: what five agent memory stores ..."
   Finding: the titles report proposes Title Case with an "AI Agent Memory:" prefix (for example
   "AI Agent Memory: The Ranker Had an Alibi Worth 0.019"). That breaks both sentence case and the
   hook-first pattern. A compliant shape: "The ranker had an alibi: what made an agent's past lessons
   useful". The curator can keep the search phrase in the explanatory clause.
2. Description structure, in this order:
   1. The question, then the answer in two or three sentences with the numbers.
   2. "This episode is the investigation, told as a detective story." Then the suspects, the alibi,
      and the twist.
   3. "Questions this episode answers:" as one paragraph of questions.
   4. "Chapters" with `(mm:ss)` timestamps taken from the real transcript.
   5. Links: "Read the article with every number, source and the probe:" then the article URL, then
      the probe URL.
   6. "Sources discussed:" for papers (Pan et al., Huang et al., ReasoningBank, Wang et al., Kim et
      al., Liu et al.).
   7. The sign-off.
   8. "Article:" and the article URL, repeated last.
   Finding: the campaign report's Spotify description is one 94-word block with two bare URLs. It has
   no detective-story line, no questions, no chapters, no sources, and no sign-off. It does not match.
3. Sign-off, verbatim except one spelling fix: "Echoes of Tomorrow is produced by Agora, an
   autonomous research organization. Every episode rests on a published article with a runnable
   probe. When a replication fails, we say so." Episode 1 spelled "organisation"; the storefront and
   Google style use "organization", so this episode uses "organization".
4. Spotify fields: season 1, episode type full, explicit no, episode number "next in the show", and
   the show field reads "Echoes of Tomorrow" before Publish.
5. Audio: mastered to -16 LUFS AAC 128k by `tools/podcast_episode.py`, with a `check.json` that
   reports `ok: true`.
6. Cover identity: the evidence table. Square 3000 x 3000 PNG, dark, one overhead lamp, scratched
   steel, brass markers, a black glove, a condensed uppercase title, and "ECHOES OF TOMORROW" tracked
   wide beneath it. The cover report's Concept A keeps this identity.
7. X thread shape: three to five posts. The first carries the number. The last carries the episode
   link and the article link.
8. LinkedIn shape: 120 to 200 words, with the episode link and the article link. Episode 1 put links
   in the first comment and ended on one question to the reader. Recommendation (taste, owner
   decides): keep the first-comment links, because the campaign report changed it without a reason
   from the owner.

### Must not be inherited from episode 1

1. Competitor names. Episode 1's description, X thread, and LinkedIn post named five stores. The
   owner rule of 2026-09-25 bans that on our own channels, and the brief bans it here.
2. Model-rendered lettering. `cover_source.png` shows the title baked into the image-model output.
   This episode sets its lettering as a deterministic overlay, in a condensed face with wide
   tracking, checked side by side against episode 1.
3. Violet light strips at both edges of episode 1's cover. The brief bans glow and neon.
4. Arrow bullets ("→") in the LinkedIn body. Use plain sentences or a hyphen list.

## 4. PASS/FAIL checklist for the merged package

Run each on the final text and image, not on the drafts. One FAIL blocks the package.

| # | check | how to test | PASS when |
|---|---|---|---|
| C1 | Every number is in FACTS | Extract every numeral with a regex; diff against the BRIEF FACTS table | 0 numbers outside FACTS (dates, URL digits, and "95%" excepted) |
| C2 | Every comparison has its interval | For 0.019, 0.156, 0.087, -0.044, 0.010: the interval sits in the same sentence or the next | All present, in every channel |
| C3 | No red line R1 to R21 | Regex for: useless, failed (about the ranker), innocent, prevents, detects, stops, protects, by default, automatically, project (as a benefit), proves, "%" after a derived figure | 0 hits, or each hit reviewed and matching the correct wording |
| C4 | The poisoning caveat travels with 0.825 | Every occurrence of "restored 0.825" | The dataset-label clause is in the same post, same paragraph |
| C5 | Opt-in stated at every product mention | Every sentence naming inspeximus plus a feature | "opt-in" or "off by default" present, and `influence_only` tied to the Python API |
| C6 | Bans and style | Search: banned words, emoji, "!", "should", more than one "#", em dash between item and description, "new", "now", "latest" | 0 hits |
| C7 | No competitor, no DANCHI | Search against the competitor list in `inspeximus` compare page and "DANCHI" | 0 hits |
| C8 | Series form | Title is hook, colon, clause, sentence case; description has all eight parts of section 3 in order; sign-off verbatim with "organization" | All true |
| C9 | Cover | Look at the rendered 3000 x 3000 PNG and at a 150 px thumbnail, dark render | No brain, robot, circuit, glow, neon, gradient blob, lens flare, face, model-rendered lettering, or clutter; the owner has seen the render |
| C10 | Audio-bound facts | `check.json` for this slug; chapters and any host quote against the transcript | `ok: true`, chapter timestamps from the transcript, no quote carrying a number outside FACTS. FAIL while no audio exists |

## 5. Findings on the drafts already in this folder

The curator asked for rules before the merge. These are early hits of those rules on the three
reports written before this one. They are findings for the curator, not edits.

| report | line | rule | fix |
|---|---|---|---|
| campaign, X post 1 | "This run cannot tell our ranker from zero" | R2 | "cannot tell the ranker's gain from zero" |
| campaign, X post 2 | "The outcome did the work." | R9 | "The outcome carried the result on these forks." |
| campaign, X post 2 and Spotify description | "scored 0.044 below no lessons" with no interval | C2, R8 | add "(-0.087 to 0.000)" |
| campaign, Spotify description | "Qwen lessons ... added 0.087" with no interval | C2 | add "(+0.036 to +0.138)" |
| campaign, Spotify description | one block, no series structure, no sign-off | C8 | rebuild on the eight-part structure in section 3 |
| campaign, Spotify description and LinkedIn | "Taste-Bench" with no attribution | R16 | "Taste-Bench (Pan et al.)" at first mention |
| campaign, LinkedIn | links moved from first comment to body | section 3, item 8 | taste; owner decides |
| titles, recommended #4 | "AI Agent Memory: The Ranker Had an Alibi Worth 0.019" | C8 | sentence case, hook first, for example "The ranker had an alibi: what made an agent's past lessons useful" |
| titles, Reddit 3 | "Accuracy fell from 0.825 to 0.637" | R10 | body must say "in a separate run" and carry the dataset-label clause |
| cover, Concept A | evidence-table identity, overlay lettering, no violet strips | section 3 | matches; confirm C9 on the render |

The campaign report also names r/Rag in the media plan while the titles report writes for
r/AI_Agents. That is a routing question, not a brand one, and the curator settles it.

## Veto versus taste

- Veto (measurable): R1 to R21, C1 to C7, C9, C10.
- Recommendation (taste, owner decides): the title wording within the pattern, first-comment links
  on LinkedIn, and the choice between cover concepts that all pass C9.
