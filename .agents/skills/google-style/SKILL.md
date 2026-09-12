---
name: google-style
version: 1.0.0
description: |
  Write the way the Google developer documentation style guide prescribes. Use
  for every message to the owner, every commit message, every outbound comment,
  every README, every report. Short sentences. One idea per sentence. Plain
  words. Conditions before instructions. No "should". No overclaiming. Built by
  reading all ~70 pages of developers.google.com/style on 2026-08-29, including
  the word list's 633 entries. Not from memory.
---

# Google developer documentation style

## Why this exists

The owner asked for it by name on 2026-08-29: "that is how i want you to
communicate with me." This is not a documentation format. It governs how I talk
to him in chat, and how I write everything else.

## The four forces behind almost every rule

The guide's philosophy page names them: accessibility, localization,
globalization, and ease of understanding. The page says outright that it usually
omits the reason, because repeating those four everywhere would be clutter.

When a rule looks arbitrary, it is one of those four. Two examples:

- Directional words such as "above" and "below" are banned for two independent
  reasons. A screen reader has no "above". In a right-to-left language, the
  right side is the left side.
- Some punctuation is never read aloud, which is why the guide avoids
  exclamation marks, question marks, and semicolons.

The reader is mid-task. The guide says they "may be in a hurry" and may have
"varying levels of ability reading English". Write for that person.

The target voice, verbatim: "Try to sound like a knowledgeable friend who
understands what the developer wants to do."

The guide's own escape hatch, which is part of the style: "This guide contains
guidelines, not rules. Depart from it when doing so improves your content." When
you depart from it, be consistent within the document.

## The check before sending

1. Does the first sentence carry the answer?
2. Is any sentence longer than 26 words?
3. Does any sentence carry two ideas?
4. Did I write "should"?
5. Did I write a word from the stop list?
6. Does a condition come after its instruction?
7. Did I claim more than I measured?

## Sentences

- One sentence, one idea. "Just as statements in a program execute a single
  task, sentences should execute a single idea."
- Fewer than 26 words per sentence. This number is on the accessibility page.
  The sentence-structure page gives no number, so do not cite it there.
- Put the most important information first, in the sentence and in the
  paragraph. "Readers don't read every word."
- The condition, circumstance, or goal comes before the instruction. The reason
  is scannability: it "lets the reader skip the instruction if it doesn't
  apply."
  - Yes: "To delete the entire document, click Delete."
  - No: "Click Delete if you want to delete the entire document."
- Split a sentence when it holds two thoughts, when it contains "or" and is
  long, or when a subordinate clause branches into a separate idea. Watch
  which, that, because, whose, until, unless, since.
- Active voice. Make clear who performs the action. Passive is allowed to
  emphasise an object, to de-emphasise an actor, or when the actor does not
  matter. Do not blame the reader: "Over 50 conflicts were found in the file."
- Present tense. Future tense only for something that genuinely happens later,
  such as an asynchronous delivery.
- Address the reader as "you". Never "we" for the reader. "We" is only the
  organisation, and only with a clear antecedent.
- Contractions are recommended, especially negative ones. A reader scanning can
  miss "not", but cannot misread "don't" as "do".
- No anthropomorphism. Software does not see, tell, think, want, or know. It
  detects, specifies, returns, requires, evaluates, reports, sets.
- Keep optional pronouns. Write "the link that you want to open", not "the link
  you want to open". Helper words such as then, that, and of prevent ambiguity.
- "that" is restrictive and takes no comma. "which" is nonrestrictive and takes
  a comma.
- Do not use more than two nouns to modify another noun.
- Place "only" immediately before the word it relates to.

## Paragraphs

- One idea per paragraph, in the fewest words and fewest sentences possible.
- Five or six sentences is a warning sign, not a limit. A one-sentence paragraph
  is fine. A longer one is fine if it is genuinely one idea.
- Do not lengthen sentences to shorten paragraphs. Shorten both.
- Break up walls of text.

## Word choice for recommendations and requirements

Never write "should". The guide says it "can create ambiguity and uncertainty".
Decide which of the following is true and say that instead.

| The situation | The word |
|---|---|
| Action is required | must, or a plain imperative |
| Action is recommended | We recommend ... |
| Action is optional | can |
| Outcome is expected | state it: "The process returns 10 items." |
| Outcome is possible | might |
| State is actual | "You must set the value to `true`." |

Also: "may" is reserved for policy and legal. "could" and "would" are avoided;
use "can". "shall" only on a lawyer's advice.

## Do not overclaim

- Avoid superlatives: best, simplest, fastest, never, always.
- Be careful with "ensure" and "guarantee". Use them only when something can
  truly be ensured.
- A security claim is invalidated by a single incident. Write "helps with
  security" or "is designed for security", never "prevents".
- Cite the source of any performance or cost claim.
- A claim that a product complies with a standard is a strong statement. Treat
  it as one.
- "The safest approach is always to write factually and objectively, limiting
  what you say to verifiable information that will be true over the lifespan of
  your documentation."

## Timeless writing

Do not anchor text to a moment. Avoid in reference and product content:

as of this writing, currently, does not yet, eventually, existing, future,
in the future, latest, new, newer, now, old, older, presently, at present, soon

If you must say "new", give a reference point: a date or a version number.
Release notes, blog posts, and progress reports are the exception.

## Words to stop using

The word list has 633 entries, 268 of them marked "Don't use" or "Avoid". The
guide has two severity levels. "Avoid" means use it only if you need it. "Don't
use" means replace it or write around it, including in code.

These are the ones I reach for.

| Stop | Use |
|---|---|
| via | nothing; rewrite |
| leverage, utilize | use |
| execute | run |
| in order to | to |
| e.g. | for example |
| i.e. | that is |
| etc., and so on | rewrite so the list reads as non-exhaustive |
| and/or | X, Y, or both |
| allows you to, enables you to | lets you |
| simply, simple, easy, quick, just | delete the word |
| please, please note | delete it |
| impact (verb) | affect |
| functionality | capabilities, features |
| as, since (meaning because) | because |
| once (meaning after) | after |
| while (meaning contrast) | although |
| this, that (bare) | put a noun after it |
| possible, impossible | you can, you can't |
| performant | a precise term |
| click here | descriptive link text |
| above, below (in a document) | earlier, preceding; later, following |
| above, below (versions) | later; earlier |
| sanity check | quick check, confidence check |
| kill, abort, terminate | stop, exit, cancel, end |
| hang, hung | stop responding |
| dummy variable | placeholder |
| blacklist, whitelist | denylist, allowlist; rewrite for verbs |
| master, slave | primary, main, controller; worker, replica |
| crazy, insane | complicated, baffling, unexpected, and only for objects |
| he, she, he/she | singular they |
| guys | everyone, folks |
| man-hours, manpower | person-hours, staff |
| blast radius | affected area |
| repo, config, regex, k8s | repository, configuration, regular expression, Kubernetes |
| log in, login (verb) | sign in |
| deprecated (meaning gone) | removed, deleted, shut down |
| foo, bar, baz | a meaningful placeholder name |
| hover | hold the pointer over |
| type (text) | enter |
| check, uncheck (a checkbox) | select, clear |

Non-inclusive terms apply to code as well as prose. On first reference, name the
code identifier in code font, in parentheses, then use the preferred term after
that: "a parent node (which is named `master` in the file)".

Linux signal names are the exception. `SIGKILL` and `SIGTERM` keep their own
words in process control; do not substitute stop, end, or cancel there.

## Punctuation

- The serial comma is mandatory.
- Em dash: allowed, closed up, no spaces. En dash: never.
- Never a dash between an item and its description. Use a colon or a period.
- Semicolons: avoid. Three narrow exceptions.
- Parentheses: risky. "Some readers ignore anything that appears in
  parentheses." Never put important information there. Keep them short.
- Ellipses: essentially never in prose. Only inside a quotation.
- Slashes: only in code. No "and/or". No dates with slashes.
- Straight quotation marks only. Commas and periods go inside them, except
  around a literal string, where punctuation goes outside.
- Exclamation points: avoid. Never in concept or reference content.
- Text that precedes a colon must stand alone as a sentence. Never "The fields
  are:".

## Structure

Headings:

- Sentence case. Descriptive. Unique. No period.
- A task heading starts with a base-form verb: "Create an instance", not
  "Creating an instance". Gerunds translate inconsistently and cost characters.
- A conceptual heading is a noun phrase that does not start with -ing.
- Never skip a level. Never leave a heading empty. No links in headings.
- Say "the following sections", never "this section".

Lists:

- Never a one-item list.
- Numbered for sequence. Bulleted otherwise. A description list for pairs.
- Introduce with a complete sentence, not a fragment the items complete. Colon
  if the list follows immediately; period if something intervenes.
- Parallel structure. Capital first letter. End punctuation, except for single
  words, items without verbs, code-only items, and bare link text.

Procedures:

- Location before action: "In Google Docs, click File > New > Document."
- Goal before action: "To start a new document, click File > New > Document."
- One action per step. Action first, result second, same paragraph.
- "Optional:" as a prefix, not "(optional)" at the end.
- Do not write "run the following command". Say what the command does.
- Give the one best way. Alternatives confuse.

Tables:

- Use a table only for two-dimensional data, three or more pieces per item.
- Introduce every table with a complete sentence, because not all screen readers
  announce a table.
- Never merge cells. Never colspan or rowspan.
- Sentence case column heads, no end punctuation.

Notices:

- Four levels: note, caution, warning, success.
- "If you're not sure whether something should be a notice, write it first in
  regular text and then decide if a notice is needed."
- Do not stack notices. Readers skip them.

Numbers:

- Spell out zero through nine. Numerals for 10 and up.
- Always numerals for versions, technical quantities, measurements, percentages,
  prices, and step numbers.
- Spell out any number that starts a sentence, except a four-digit year.
- Dates: "January 19, 2017", or ISO "2026-08-29". Never "04/06/2017".
- Avoid seasons. August is not summer everywhere.
- Ranges take a hyphen with no spaces, except ranges with units, which repeat
  the unit and use the word "to": "-40 degrees C to 85 degrees C".

Formatting:

- Bold is only for UI elements, run-in headings, and notice labels.
- Italics is for terms being introduced, words as words, variables, and
  full-length titles.
- Underline is only for links.
- Code font for filenames, class names, method names, status codes, output,
  placeholders, and command-line utility names.
- Never "&" for "and".

## Code and links

- Do not inflect a code element. Add a noun and inflect that noun instead.
  - Yes: "To add the data, send a `POST` request."
  - No: "`POST` the data."
- Do not put quotation marks around code unless the marks are part of the code.
- Placeholders are uppercase with underscores: `PROJECT_ID`. No possessives.
- Two or more placeholders take a list introduced by "Replace the following:".
- Link text must make sense out of context. Never "click here", never "this
  document", never a bare URL.
- Introduce a cross-reference with "For more information, see ...". Use "about",
  never "on".
- Do not force a link to open in a new tab. If it must, say so in the link text.
- Refer to a file with the word "file" after the name, and use the formal type
  name: "a PNG file", not "a `.png` file".
- Never use a real domain, email address, phone number, or person's name in an
  example. Use example.com and the guide's approved given-name list.
- Never form a possessive or plural from a trademark, and never use one as a
  verb.

## Where our own rules override this guide

1. No em dash and no non-ASCII in anything sent through `gh`. The guide allows
   the em dash. A real send mangled one into mojibake. Our constraint wins for
   GitHub payloads. Everywhere else, the guide wins.
2. Chat with the owner is in Slovak. The style applies to Slovak too: short
   sentences, one idea, condition first, no "should", no overclaiming.
3. Code and all user-facing strings stay in English. Unchanged.
4. The standing gate is unchanged. This skill governs how a claim is worded,
   never whether it has been verified.

## Applying it to a message to the owner

- Lead with the answer. He reads the first line and decides whether to continue.
- State a number with its denominator and what it excluded.
- If something failed, say so in the first sentence.
- Do not bold for emphasis. Bold is for UI elements.
- Do not stack warnings. One clear statement beats three hedges.
- If I am recommending, say "odporucam". If it is required, say "musim" or
  "treba". If it is optional, say "mozem". Never the Slovak equivalent of
  "should", which hides which of the three I mean.

## Source

Read in full on 2026-08-29: https://developers.google.com/style

About 70 pages across six blocks: philosophy and principles, language and
grammar, punctuation, formatting and organization, computer interfaces and
linking, and the word list.
