---
name: linkedin
description: Run Agora's LinkedIn as a marketing operation on top of sergebulaev/linkedin-skills (MIT, read in full 2026-09-17, kept at .agents/linkedin-skills-source/). Use for a LinkedIn post from a published Agora article or episode, a comment or reply on someone's post, a weekly plan, the profile rewrite, or the engager and thread reports. Every draft obeys Agora's rules first (numbers only from the gated article, humanizer last, owner pastes), then the bundle's 2026 craft (number-first hook, one contrast, one triple, link in the first comment).
argument-hint: "post <slug> | comment <url> | reply <url> | plan | profile | engagers <url> | threads"
---

# linkedin: the bundle's craft, Agora's rules

The bundle at `.agents/linkedin-skills-source/` is the reference. Read the file the task needs
from it before drafting; do not recall it. This skill says what Agora changes.

| task | read first in the bundle |
|---|---|
| post from an article or episode | `skills/linkedin-repurposer/SKILL.md`, `references/hook-formulas.md` (F7, F17, F19, F10, Density rule, Hook micro-rules) |
| post from scratch, founder voice | `skills/linkedin-post-writer/SKILL.md`, `references/founder-topics.md` |
| comment on someone's post | `skills/linkedin-comment-drafter/SKILL.md`, `references/voice-rules.md` |
| reply, thread sweep | `skills/linkedin-reply-handler/SKILL.md` |
| week plan | `skills/linkedin-content-planner/SKILL.md` |
| profile | `skills/linkedin-profile-optimizer/SKILL.md` |
| who engaged, which threads are warm | `skills/linkedin-engager-analytics/SKILL.md`, `skills/linkedin-thread-monitor/SKILL.md` |
| any of the above | `references/algorithm-heuristics.md` (timing, length, link placement, pod detection, edit window) |

## What Agora overrides

1. **Numbers come from the gated article, nowhere else.** A LinkedIn post is a derivative:
   `python tools/derive_post.py check <slug> agora_output/derivatives/<slug>/linkedin.md` must
   print `ok`. The bundle's "add an odd-precision number" rule is satisfied only with a number the
   article already carries. If the article has no number for the beat, the beat goes.
2. **Humanizer runs last, once**, the `humanizer` SKILL, then
   `tools/humanizer_receipt.py record ... --skill humanizer --in-session --wording-is-final`. The
   bundle's own `linkedin-humanizer` is a reference for the 2026 LinkedIn tells (reveal bridges,
   staccato stacks, "It's not X, it's Y"); it is not the pass. Agora's rule on em dashes stays:
   none, not "one per 100 words".
3. **Tier 0 only. The owner pastes.** No Publora key, no `LINKEDIN_SKILLS_CUSTOM_POSTER`, no
   auto-publish. Deliver the post body, the first comment (with the links), the posting window and
   the reply plan. The Apify read layer is a spend; it needs a `BUDGET:` line and the owner's words
   before the first token is set.
4. **Links in the first comment**, never in the body (0.4 to 0.6x reach in the bundle's data).
   The first comment carries the article, then the episode, then the probe. Zero hashtags.
5. **Google developer style still governs the sentence**: lead with the answer, one idea per
   sentence, no "should", no overclaim, no anthropomorphism. The bundle's lowercase sentence starts
   and `..` pauses are its author's voice, not ours.
6. **Never open with a question** (the bundle's -34% vendor figure); the question closes the post.
   Never "Here's what", "Stop X, start Y", "The result?", "Plot twist:". One contrast and one
   triple per post, and the triple is three sourced numbers or three named acts.
7. **The owner's name is on the profile.** LinkedIn is the one surface where the author is
   Rastislav Drahos, not the anonymous storefront identity. The post may say "we" for Agora and
   "I" for what he did. It never names a client, a collaborator, or a paper under review without
   his word; `references/story-bank.md` section 8 is the list.
8. **Voice profile and story bank live outside the repo.** Both files hold his career detail, and
   `github.com/DanceNitra/agora` is public. The filled copies live at
   `C:/Users/Danculus/.config/linkedin/voice-profile.md` and `.../story-bank.md`; the skill reads
   them from there and never writes them into the tree.
9. **Comments on other people's posts do not name inspeximus.** The bundle's rule and ours agree:
   describe what we measured, let the profile carry the product.
10. **Nothing goes outward before the owner taps approval**, and a comment on a maintainer's or
    a researcher's post is outreach, so it also gets the Slovak briefing (context, their point,
    our answer, how we use it).

## Post from an article, the procedure

1. Read the article source `public/posts/src/<slug>.en.md` and, if there is one,
   `agora_output/derivatives/<slug>/episode.md`. List the three strongest facts with their numbers.
2. Pick the formula by goal. Our articles are measurements, so the default is F19
   (a noticing, then an evidence stack of sourced numbers) or F17 (one variable changed, the
   outcome flipped). F7 when the article is a cost ledger. F10 when it is a sacred cow with dated
   receipts. Say which and why in one line.
3. Line 1 is the number. Hook inside 140 characters (mobile fold); 900 to 1,300 characters total;
   one to two sentences per paragraph with blank lines; one specific closing question; a one-line
   P.S. only when there is a real follow-up.
4. Write the first comment: the article URL, the episode URL, the probe URL, each with five words
   of what it is.
5. `derive_post.py check`, then the humanizer SKILL, then the receipt.
6. Show the owner: formula, the post, the first comment, the character count, the window
   (Tue, Wed, or Thu, 07:00 to 08:30 CET for EU decision makers), and the reply plan (answer
   every comment inside 90 minutes; the first hour decides most of the reach).

## What this skill does not do

It does not post, react, connect, or message. It does not scrape anyone's audience without the
owner's word. It does not let a post carry a number, a name, or a link the article does not.
