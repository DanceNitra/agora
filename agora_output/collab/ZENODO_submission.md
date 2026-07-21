# Zenodo submission package — value-obscuring reversion paper

Marat chose **Zenodo first** (no arXiv endorser yet in cs.CL/cs.AI; DOI now, arXiv later). This is everything
to fill into the Zenodo "New upload" web form. Owner (or Marat) uploads via the web account — I can't upload.

**File to upload:** `agora_output/collab/value_obscuring_reversion_MERGED_v1.pdf` (176 KB, camera-ready, has
Abstract + Related Work + References).

---

## Form fields (copy-paste)

- **Upload type:** Publication → *Preprint*
- **Title:**
  `When a Benchmark Shortcut Is the Answer: Decomposing Value-Obscuring Reversion Detection`
- **Authors** (order = as agreed; both real-name, owner approved public):
  1. `Sultanov, Marat` — affiliation: independent researcher (TAT / TreeAngleTap)
  2. `Drahoš, Rastislav` — affiliation: Agora (DanceNitra)
  *(ORCID: leave blank unless either of you has one — can be added after.)*
- **Description** (paste the abstract):

> Correcting a stored fact and reversing a memory to a prior value look similar but are different operations.
> We study *value-obscuring reversion*: an unmarked "go back / roll back" instruction that names no value, on a
> memory store that has already superseded an old value with a new one. A prior audit reported that plain
> cosine similarity (candidate utterance vs. the recent context lines) "fails" at this task (F1 0.481). An
> external red-team showed the opposite: the same cosine baseline solves the held-out set at F1 0.905–0.930.
> The audit had declared a *family* of shortcuts dead after testing a single member. Rather than escape into a
> harder fixture, we decompose the task: reference resolution is a text/similarity problem (the cosine baseline
> is right), while old-vs-new attribution is a *ledger/provenance* problem that no amount of text similarity can
> settle. A shuffle test confirms the split — positional similarity collapses to chance (0.930 → 0.500) once
> line order is destroyed, because the fixed order stood in for the provenance metadata every real store keeps.
> With explicit ledger metadata plus structure-match, F1 is 0.930 with order destroyed. Unresolvable references
> (target role in neither context line) are handled by abstention, not a guess. We ship the resolution as a
> store method, `classify_reversion`, that classifies (never restores) and defers the undecidable bare-"go
> back" twin to an authorized-revert channel. Lesson for practitioners: enumerate the shortcut family before
> declaring it dead, and separate the text channel from the ledger channel instead of building a bigger fixture.

- **Keywords:** `agent memory`, `memory integrity`, `belief revision`, `provenance`, `value-obscuring reversion`,
  `LLM`, `retrieval`, `benchmark shortcut`
- **License:** Creative Commons Attribution 4.0 International (CC BY 4.0)  *(standard open, lets people cite/reuse)*
- **Language:** English
- **Related/alternate identifiers** (add each as "is supplemented by this upload" / URL):
  - `https://github.com/DanceNitra/agent-memory-integrity` — the cross-system integrity benchmark
  - `https://github.com/DanceNitra/agora` — inspeximus (`classify_reversion` reference implementation)
- **Publication date:** the date you upload.
- **Notes (optional):** "Fixtures are author-built synthetic scenarios (disclosed in the paper); numbers are
  reproducible from the linked repositories."

---

## After it's live
- Zenodo mints a **DOI** immediately. Send Marat the DOI.
- He then drafts the short note on issue #1466 linking the paper and sends it to us for review before posting
  (his commitment). Owner reviews, then Marat posts (his account, his issue thread).
- Add the DOI to the paper's References/footer and to the integrity hub (`public/integrity/`) as a citable
  edition anchor if we want.
