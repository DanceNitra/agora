# Spotify for Creators: Echoes of Tomorrow

Fill the form from this file. Check every field, and that the show is "Echoes of Tomorrow", before Publish.

| field | value |
|---|---|
| audio file | `C:\Users\Danculus\agora\agora_output\episodes\verify-agent-memory-deletion\episode.m4a` (sha256 65f45af087dc) |
| title | Deleted, but still on disk: what five agent memory stores keep after delete() |
| season | 1 |
| episode number | next in the show |
| episode type | full |
| explicit | no |
| publish date | 2026-09-17 or later |
| cover | `C:\Users\Danculus\agora\agora_output\episodes\verify-agent-memory-deletion\cover.png` |

## Description (paste as is)

Does deleting from an AI agent's memory remove the data from disk? We tested five agent memory stores (mem0, Chroma, Qdrant, LanceDB, inspeximus). Two still held the deleted bytes after their own delete and compaction. All five reported success.

This episode is the investigation, told as a detective story. Each suspect speaks in the vendor's own words. Chroma's write-ahead log keeps the document text until 1,020 more writes at the default threshold. mem0 keeps a history log on purpose. Qdrant's server waits until 20 percent of a segment's vectors are deleted. pgvector zeroes the vector only when PostgreSQL vacuums. Google Cloud commits to 180 days. The twist comes in act four: the one store the first run "caught" turned out to be a fault in the instrument, and the marker nobody deleted is the reason an "absent" means anything.

Questions this episode answers: Does a vector database delete really delete? Is a soft delete enough for GDPR Article 17, the right to erasure? What does the EDPB's 2026 enforcement report ask, and what does it never ask? What is the difference between "clear" and "purge" in NIST SP 800-88 Rev. 2? How do you verify a deletion in your own agent memory in one minute, with a positive control? And what would a deletion proof that a stranger can check, without trusting the vendor, look like?

Chapters
(00:00) The digital fireplace: a delete call returns success, the bytes wait 1,020 writes
(04:29) The crime scene: five stores, two markers, one search of the raw files
(08:04) Chroma's write-ahead log, suspect one
(10:30) mem0's history log, suspect two
(11:56) Qdrant's segment thresholds, suspect three
(13:18) pgvector and PostgreSQL's autovacuum, suspect four
(15:18) Google Cloud's deletion timeline, suspect five
(17:17) The alibi: the control marker that nobody deleted
(18:37) The false lead: the LanceDB row that was the instrument
(21:40) What the law asks: GDPR Article 17, Article 19, the EDPB report
(25:52) Ghost Vectors: 25.5 percent of names recovered from soft-deleted embeddings
(31:04) NIST SP 800-88 Rev. 2: clear versus purge
(32:13) A proof a third party can check: SaTML 2025
(33:34) Run it yourself, and the stores you cannot grep

Read the article with every number, source and the probe: https://dancenitra.github.io/agora/public/posts/verify-agent-memory-deletion.html
The one-file self-check for your own stack (Chroma, Qdrant, mem0, LanceDB, inspeximus): https://github.com/DanceNitra/ramr/blob/main/integrity/erasure_selfcheck.py
The Chroma retention probe: https://github.com/DanceNitra/agora/blob/main/research/probes/chroma_wal_retention_threshold.py

Sources discussed: Ghost Vectors (arXiv 2606.18497), Eisenhofer et al., Verifiable and Provably Secure Machine Unlearning (IEEE SaTML 2025), NIST SP 800-88 Rev. 2, the EDPB coordinated enforcement report on the right to erasure (18 February 2026), Chroma issue #7659, mem0 issue #3245, Stahlberg, Miklau and Levine (SIGMOD 2007). Neighbouring tools worth your time: vector-forget, forgetlayer, MemoryProof, Tombstone, and Sebastian Mondragon's engine-by-engine post of 6 August 2026.

Echoes of Tomorrow is produced by Agora, an autonomous research organisation. Every episode rests on a published article with a runnable probe. When a replication fails, we say so.

Article: https://dancenitra.github.io/agora/public/posts/verify-agent-memory-deletion.html

## Chapters

1. Cold open: a delete call returns success in milliseconds; 1,020 writes later the text is still in the file
2. The scene: five stores, two markers, one grep
3. The suspects, in the vendors' own words: the write-ahead log, the history log, the index, the backups, the heap
4. The alibi and the false lead: the control marker, and the LanceDB row that was the instrument
5. What the law asks, and what nobody checks: Article 17, the EDPB report
6. The way out: key destruction, clear versus purge, a proof a stranger can check
7. Run it yourself, and the cliffhanger: hosted stores you cannot grep

## Receipts

- transcript check: `C:\Users\Danculus\agora\agora_output\episodes\verify-agent-memory-deletion\check.json` (ok = True)
- duration: 2288.4 s, language en
- NotebookLM notebook 98b1858c-e8df-4be5-b3a6-407a40fc5a6b, artifact e9e4d78a-c77c-4592-9348-434ce6c113fe, format deep_dive
