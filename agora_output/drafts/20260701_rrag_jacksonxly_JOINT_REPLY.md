DRAFT — gated JOINT r/Rag reply to u/jacksonxly (folds: response to his time/entity/soft points +
our metadata result + the new soft-vs-hard measurement). Owner posts manually. NOT posted.
Frame: VALIDATE ✓ (probe reproduces, json=txt) · STORM ✓ (fresh storm on this exact topic) ·
AUDIT ✓ (soft keeps gain / halves-not-eliminates harm / n=74 / one impl) · VERIFY ✓ (numbers vs result json).

---

This is the sharpest version of the split — and you nudged me to actually measure the soft-vs-hard part, so here's what I got on LoCoMo.

Agreed on the extraction halves: time is a closed grammar (SUTime/duckling resolve "last month"/"Q3" offline, no LLM — hard-filter that half), and for personal/agent memory the entity vocab is closed too, so it's alias-linking against your own known set, not open NER — a small local model only as a schema-constrained slot filler. That matches how I'd build it.

On soft vs hard, your key point — measured (BM25+vector hybrid, recall@20, 10 conversations, conv-level bootstrap CI):
- **hard** speaker pre-filter: +0.146 overall — but on the ~5% of fired cases where the filter is wrong (gold is the other speaker) it craters recall from 0.56 (no filter) to 0.15. Exactly the "lossy extraction hard-deletes the answer" failure you flagged.
- **soft** (filter as a rerank boost, keep everything as fallback): +0.129 overall — keeps almost all the gain — and roughly halves the harm (0.15 → 0.27). Honest caveat: even soft is still below no-filter (0.56) on those wrong cases, so it *mitigates* the downside, doesn't erase it.

So you were right: soft is the safer default once extraction is lossy — you give up a sliver of the win for materially less downside. Two caveats on the whole thing so I don't oversell it: LoCoMo has 2 speakers, so this is near best-case for a speaker filter; and I ran brute-force retrieval — on an HNSW index a filter that correlates with embedding clusters can crater recall unless you do filtered-ANN.

Shipped the hard version as a `recall(where=)` metadata pre-filter in our little memory lib, but this measurement makes soft the better default. Script (now with the soft arm + the harm subset) if you want to break it: https://github.com/DanceNitra/agora/blob/main/mnemo/probes/locomo_metadata_prefilter.py

Still the open one, and where your production data beats a benchmark: does any of this survive at low selectivity (many entities) with predicted — not gold — filters?
