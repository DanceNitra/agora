# Launch plan — second_brain_mcp + mnemo (DRAFT, gated)

**Nothing here is published. This is the owner's "how to ship it" checklist. You press the button.**
Posts are in `LAUNCH_POSTS.md` (EN + SK). Passed an adversarial honesty review (wf_ec21e760); the two
blockers it found (broken run command, an unverified recall number) are fixed below.

## Verified-numbers reference card (do NOT drift from these in any comment)
| Claim | The number | Source |
|---|---|---|
| Run command (after flat download) | `NOTES_DIR=/path python second_brain_mcp.py` | tested working; `-m` package form fails after a flat curl |
| Lexical recall decays at scale | recall@5 0.94 (small) → **0.25** at ~6k notes | Lab `b4c260` |
| Semantic holds at scale | recall@5 **~0.65** at ~6k notes (≈2.6× lexical) | Lab `b4c260` |
| Paraphrase queries | semantic recall@5 **0.86** vs lexical **0.20** | Lab `3501f1` |
| Vault size | **~6,000 notes** (the corpus measured) | — |
| The 7× catch | own note "60-78%" vs real GJP **~6-11%** | second-brain briefing; still needs source re-check before any public claim |
| Severe-tested ideas | cue-validity crossover ~0.45; independence load-bearing | Lab `da40a0`, run in Agora's lab — **not** inside the MCP server |
| License | MIT, open core, free; hosted/pro = maybe later, not a promise | repo LICENSE |

## The pitch in one line
*A zero-config MCP server that turns your Markdown vault into a thinking partner — the retrieval and
structure live in the tool, the reasoning stays in your agent.*

## Channels & order (lowest-flame-risk first; ~10 days)
1. **Days 1-2 — quiet groundwork (no announcement).** Repo README leads with the honest architecture +
   the working run command; MIT LICENSE visible; a 30-60s asciinema/GIF of it running on a real vault;
   the `.mcp.json` snippet. Submit **MCP directory** listings (modelcontextprotocol/servers,
   awesome-mcp-servers, mcp.so / Glama / Smithery) — pure submissions, no flame risk, seed early stars.
2. **Day 3-4 — r/LocalLLaMA.** The most forgiving technical crowd; lead with single-file/zero-dep +
   the lexical→semantic scale curve. Tune the title to the sub.
3. **Day 5-6 — r/ObsidianMD, then r/PKM (+ r/Zettelkasten).** Lead with "find the gaps + silent
   contradictions in YOUR vault"; emphasize read-only, local, no telemetry (their #1 concern). One
   tailored post per sub — never cross-post the same body.
4. **Day 7 — Show HN.** Only once the repo has the demo, LICENSE, clean README, and a few
   directory-sourced stars. Weekday morning US time. Be in the comments the first few hours.
5. **Ongoing — X/Twitter thread.** Repo link in a reply, not the first tweet (link-first throttles).
   An SK standalone X post is fine for the founder's local audience; everything else defaults EN.

## How to handle the first comments (this is where it's won or lost)
- Be present the first 2-3 hours of each post. Fast, technical, non-defensive.
- Concede the true part first. If someone says "the LLM does the work, not your tool" — **agree**, that
  IS the design; the value is the substrate + the honesty.
- If asked for the number behind a claim, give the lab id from the card above. Never improvise a number.

## Dos & don'ts
- **DO** lead with the tool-vs-LLM split every time; it's the credible differentiator.
- **DO** use the one true story (the 7× catch) with its caveat (LLM did it; still needs source-check).
- **DO** say "runs today, zero config" (true via lexical fallback); call the embedder optional.
- **DO** state the license once, plainly: MIT, free core; no hard paywall tease.
- **DO** keep EN as default; SK only as a separate standalone post for the local audience.
- **DON'T** imply the tool "thinks"/"finds insights" on its own — the agent does.
- **DON'T** post any number not on the reference card; no "10×", "revolutionary", fake testimonials.
- **DON'T** add a waitlist / "DM me" / signup funnel in community posts — link only to the open repo.
- **DON'T** cross-post identical bodies; tailor per community.
- **DON'T** argue with downvoters or delete criticism; concede the true part.

## Pre-flight checklist (before ANY post)
- [ ] `curl` the two raw files into an empty dir and run the literal command — it must work in 60s.
- [ ] README run command, `.mcp.json`, and every post all show the **script form** (no `-m`).
- [ ] Every number traces to the reference card above.
- [ ] LICENSE present at repo root; README says MIT/open-core/free.
- [ ] Note count says ~6,000 everywhere (posts + README + this file).
- [ ] (Optional but strong) a demo GIF/asciinema in the README.
