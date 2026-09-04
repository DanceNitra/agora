# EPJ B submission package

Built 2026-09-01 from Li Guanghao's 29 August manuscript, which he confirmed as final. **Nothing has
been sent and nothing is approved by the co-authors.** This file is regenerated from the build
receipts, so it cannot drift from the package the way the first version did.

## 1. Files

| file | what it is |
|---|---|
| `manuscript.tex` | the submission source, `sn-jnl` with the `iicol` option |
| `manuscript.pdf` | 10 pages, zero undefined references after three passes |
| `abstract.tex` | the abstract on its own, so it can be diffed |
| `Fig1.pdf` to `Fig4.pdf` | extracted from the inline TikZ and compiled separately |
| `sn-jnl.cls`, `bst/` | the class and bibliography styles the journal asks for |
| `graphical_abstract.png` | 480 x 262 px, ratio 1.832, drawn from the focused audit of Fig. 2 |
| `cover_letter.md` | the two points the journal requires |
| `manuscript_2026-08-29_asreceived.tex` | his file, untouched, so every change is diffable |
| `build_manuscript.py`, `extract_figures.py`, `make_graphical_abstract.py` | the build, re-runnable on a revision |

## 2. Owner fields

| field | value |
|---|---|
| corresponding author e-mail | `rastislav.drahos@gmail.com` |
| ORCID | `0009-0009-4792-1433`, carried as text because the class's `\orcid` macro needs a logo file the package does not ship |
| co-author e-mail addresses | not held; requested in the thread. The journal requires one only for the corresponding author |

## 3. Every change to his file

Required by the journal:

| change | the rule |
|---|---|
| `revtex4-2 [aps,prb]` to `sn-jnl [iicol]` | his file was formatted for Physical Review B |
| abstract 334 to 248 words | the stated limit is 150 to 250 |
| four inline TikZ pictures became `Fig1`-`Fig4` | the template: figures are attached, not embedded |
| an artificial-intelligence subsection in Method | Springer requires it there; COPE requires it to name the tool and the use |
| a Declarations section | eight statements; submissions without them are returned as incomplete |
| DOIs on ten references, an access date on the eleventh | "if available, please always include DOIs" |
| keywords added | the template asks for them |
| a short running-head title | `sn-jnl` takes one |

Our decisions, not the journal's:

| change | why |
|---|---|
| four prior studies added and cited | they were never in the bibliography, though he had been thanked for them; one is EPJ B's own 2004 paper on this lattice |
| Sec. 6.1: the two random graphs named and excluded | the text said thirty, then listed twelve and sixteen |
| his data availability subsection removed | the Declarations statement says the same thing |
| a hardcoded `Table~I` became a reference | revtex numbers tables in Roman, `sn-jnl` in arabic, so it pointed at nothing |
| two contribution sentences removed from the acknowledgements | the Declarations statement covers them, in the journal's form |
| author contributions narrowed | the gasket controls in Sec. 6.1 are his; ours is the thirty-graph replication |
| the AI disclosure rewritten | it had understated our role and claimed a page-number correction that was ours to make |

## 4. Open, and not ours to close

- **The corresponding-author role.** Accepted in the owner's name on 2026-09-01 at 07:18 UTC in a
  comment he had not seen, confirmed publicly by Guanghao at 08:04. It cannot change after
  acceptance, so submitting is the act that settles it.
- **Co-author approval.** Neither Guanghao nor Marat has seen this package. Nothing in the
  manuscript or the cover letter asserts that they have.
- **Two co-author e-mail addresses**, optional but worth deciding deliberately.

## 5. How it was checked

`probes/what_the_epjb_submission_still_needs.py` measures the manuscript against sixteen rules from
the journal's instructions: **16 of 16 pass**. Each rule is exercised against a case that satisfies
it and one that breaks it, and a rule whose two fixtures agree is reported as broken rather than as
a pass.

Two adversarial passes ran over the package. The first returned STOP and found seven defects,
including four references the author believed were in the paper and an abstract that had silently
lost seven of his results. The second, on the corrected package, found three more: a missing
backslash that rendered the lattice name with an apostrophe on page 1, a caption pointing at a table
that no longer existed, and a graphical abstract that showed a monotone descent for a paper about
non-monotonicity. All ten are fixed and each fix is verified in the built file.

The build's own controls refuse rather than warn: a lost numeric token from his body, an abstract
outside 150 to 250 words or missing any result it is required to carry, a lattice name without its
accent, and a graphical abstract whose minimum is not interior. Each was proved able to fire by
mutation.
