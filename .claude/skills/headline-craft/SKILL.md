---
name: headline-craft
description: How to write the title of an Agora article, its SEO title tag, its Reddit post title, its podcast episode title and its X hook, and how to test them before the owner sees them. Use whenever a headline, title, hook, subject line or episode name is needed, and whenever the owner asks "je to titulok?" Built 2026-09-17 from Harry Dry's 71-minute copywriting session read in full as a transcript, Ahrefs' title-tag guide, Hacker News' submission guidelines, and a measurement of the 150 top posts of the month in r/LocalLLaMA, r/MachineLearning, r/AI_Agents, r/LLMDevs, r/Rag and r/LangChain. Not recalled; measured.
argument-hint: "<slug or the article's one-line claim>"
---

# headline-craft: the one line that decides whether anyone reads the rest

A headline is a claim. It gets the same rigor as a number: a source for the craft, a test it must
pass, several versions, and the owner's choice. Never adopt a headline a red-team lens wrote; a
lens fixes overclaim, it does not write headlines.

## The three tests (Harry Dry, applied to every candidate)

1. **Can I visualize it?** Concrete beats abstract. "Charging pitbull" is remembered, "better way"
   is not. Zoom in until the sentence names an object: not "regain fitness" but "couch to 5K".
2. **Can I falsify it?** A sentence that is true or false makes the reader sit up. "He reads on the
   tube" beats "he is intelligent". Point at the fact; do not talk about it.
3. **Can nobody else say it?** "Never write an ad a competitor can sign." If any memory vendor or
   any other blog could put its name under the line, it is not ours yet.

Three no's means rubbish. Three yes's means a candidate. Then the two-second test: show it to
someone cold, count "one Mississippi, two Mississippi"; if they do not get it by two, rewrite.

## The method

- **Start from a fact**, ours, measured this cycle. The Rolls-Royce clock line was pulled from a
  motor magazine; Ogilvy's craft was choosing it. Our facts are the probe outputs.
- **Conflict.** Draw a line down the page and write the two sides: what the API said versus what
  the disk held; before versus after; the corporate way versus the copywriting way. The reader
  remembers relatively.
- **Write twenty versions.** The first dozen are the dirty water out of the tap. Keep going until
  a line you cannot add a word to or take a word from. Show three versions to a reader, never one;
  "I like it" is not feedback, "that sentence, in that one" is.
- **Parallelism and rhythm.** "22,000 hours writing, two learning how" was rewritten from 20,000
  for the parallel. Tougher than an F-150, faster than a 911.
- **Small claim, believable.** "Increase conversions from 1% to 2%" sells because it is sincere;
  "be a millionaire" does not. Our body says "evidence, not proof", so the headline may not say
  "prove".
- **Write it where the reader sees it**: the title in the search result mockup, the Reddit title in
  a list of other titles, the H1 on the rendered page. A line that spills to two lines is rewritten.

## The four surfaces are four different lines

| surface | constraint | source |
|---|---|---|
| SEO title tag | under 60 characters; the query the page targets near the front; matches intent; may differ from the H1 but on the same topic; no claim the page does not keep | Ahrefs title-tag guide: "anything under 60 characters is fine", 600 px; 68.54% of sites have titles Google rewrites |
| H1 on the page | the fact, concrete, falsifiable, ours; one sentence a stranger understands cold | Dry's three tests |
| Reddit title | median 12 words in the top 150 of our target subreddits this month; 39% carry a number; 22% are first person doing the thing; 25% are questions (r/AI_Agents mostly); tone is plain, a story or a contradiction, no marketing words; never the same title in two subreddits | measured 2026-09-17 with tools/distribution_radar.py, `top?t=month` |
| Hacker News | neutral and close to the original title; no uppercase, no exclamation, no praise, no gratuitous numbers, no editorializing | HN submission guidelines |
| Episode title | what the listener gets, in the order they hear it; a colon is allowed; the number stays | Dry: first line earns the second |
| X hook | one falsifiable fact, then the link in the last post | Dry: a fact guarantees you said something |

What won this month in our subreddits, as shape: "You can beat SOTA time series anomaly detection
with a 100 year old algorithm" (501 ups), "I trained a 44M parameter quantized LLM from scratch on
45B tokens. It ships in 19.8 MB" (229), "NeurIPS desk-rejected 178 papers for being AI-generated. The
detector flagged the track chairs' own papers" (248), "Our internal bot answered a question with the
unannounced reorg plan. It was only supposed to read the wiki" (137), "What the 100 biggest GitHub
repos put in their AGENTS.md files" (156). A number, a subject doing a thing, a contradiction.

## What a bad headline looks like, with the reason

- "Your delete() returned OK. Are the bytes still on disk?" (shipped 2026-09-17, rejected by the
  owner): a question instead of a fact; nothing to visualize; any vendor could sign it; "OK" and
  "bytes" ask the reader to translate. It fails tests 1 and 3.
- "Verify AI agent memory deletion: can you prove it is gone?": a keyword string with a question
  bolted on; fine as a title tag, not a headline; "prove" contradicts the body.

## Procedure

1. List the three strongest facts in the article, each with its number.
2. Write twenty lines. Do not judge until twenty exist.
3. Score each on the three tests (0 to 3) and the two-second test. Keep the top five.
4. Write the SEO title, the H1, the Reddit title, the episode title and the X hook from the
   survivors, each to its own constraint above.
5. Show the owner three per surface with their scores. He picks. Nothing renders before that.

## Cover art prompts for GPT Image (2 / 2.5), from OpenAI's own guide, read 2026-09-17

Sources: developers.openai.com/api/docs/guides/image-prompting and the cookbook
"GPT Image Generation Models Prompting Guide". Rules as stated there:
- Order: scene, subject, details, constraints, in labelled sections. Decide the result first.
- "Name materials, lighting, colors, and the visual medium." Say "photorealistic" when you want it.
  Specify scale, atmosphere and colour; a mood word alone does nothing.
- Text: put the exact words in quotation marks, say where they sit and in what typography, spell an
  unusual word letter by letter, then "ask for no extra text" and check the spelling in the output.
  Use `quality="high"` when the image carries text.
- Size is a parameter, never a sentence. gpt-image-2: both edges multiples of 16, at most
  8,294,400 pixels, so a square cover is 2880 x 2880 (Spotify accepts 1400 to 3000 square).
- Describe framing and texture with photography language (lens, light, surface), not "4K" or
  "masterpiece". For iteration: pass the previous output back and "change only X".
- The restrained typographic prompt of 2026-09-17 was rejected by the owner ("hovno"): for a
  podcast cover he wants a cinematic scene that tells the episode's story, with the title set
  inside it, not a product-page card. Restraint stays for the storefront pages, not for covers.
