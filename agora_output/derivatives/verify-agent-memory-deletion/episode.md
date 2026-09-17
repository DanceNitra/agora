# Episode

## Title

Deleted, but still on disk: what five agent memory stores keep after delete()

## Description

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

## Chapters

1. Cold open: a delete call returns success in milliseconds; 1,020 writes later the text is still in the file
2. The scene: five stores, two markers, one grep
3. The suspects, in the vendors' own words: the write-ahead log, the history log, the index, the backups, the heap
4. The alibi and the false lead: the control marker, and the LanceDB row that was the instrument
5. What the law asks, and what nobody checks: Article 17, the EDPB report
6. The way out: key destruction, clear versus purge, a proof a stranger can check
7. Run it yourself, and the cliffhanger: hosted stores you cannot grep

## Focus

Tell this as a detective story in seven acts, in this order, using only the facts in the source titled FINAL ARTICLE 2026-09-17 and the cited sources. Do not invent numbers; every number you say must appear in that article. Keep every figure exact.

Act 1, cold open: a delete() call returns success in milliseconds. In Chroma, with the default hnsw:sync_threshold of 1000, the deleted document's text is still in chroma.sqlite3 until 1,020 more writes; with the threshold set to 50, until 59 more writes. Make the listener feel the gap between the return code and the disk.

Act 2, the scene: on 17 September 2026, one machine, five agent memory stores (chromadb 1.1.1, qdrant-client 1.18.0 in local mode, mem0ai 2.0.11, lancedb 0.30.0, inspeximus 2.24.0). Two markers stored in each, one deleted through the store's own API, the compaction the store exposes, then a search of the raw files for both. Two of five still held the deleted marker's bytes: mem0 and Chroma. All five delete calls returned success.

Act 3, the suspects, each in the vendor's own words: Chroma's write-ahead log keeps the ADD row with the text until the HNSW segment persists (issue #7659); mem0 keeps a history log by design, reset() purges it, and its graph store kept deleted nodes from 29 July 2025 until the fix on 23 March 2026 (issue #3245); Qdrant's server removes deleted vectors per segment only at deleted_threshold 0.2 and vacuum_min_vector_number 1000, and a maintainer said removing them immediately is more expensive than keeping them; pgvector overwrites the vector with zeros only when PostgreSQL vacuums, which by default is after more than 50 plus 20% of the table in dead tuples, over 200,050 on a million rows; Google Cloud says about two months from active systems, backups within six months, a 180-day commitment. Stress that none of these is a bug: each is documented, and Stahlberg, Miklau and Levine showed the same deferral in relational databases at SIGMOD 2007.

Act 4, the alibi and the false lead: the second marker, the one nobody deleted, survived in every store, so an "absent" is a real delete and not a wipe. Then the twist: an earlier version of the check reported LanceDB as PRESENT, but its compaction call had raised an ImportError that the script swallowed, so no compaction had run; with Table.optimize() the marker is gone. The verdict belonged to the instrument, not the store. And the qdrant row is local mode, a SQLite file with no optimizer, so it says nothing about the server.

Act 5, what the law asks: GDPR Article 17(1), erase without undue delay where a listed ground applies; Article 19, tell the recipients. The EDPB report adopted 18 February 2026, 32 authorities and 764 controllers, names procedural problems and says nothing about checking whether bytes went, nothing about vector stores. Strict text, no enforcement precedent on residue. Today it is a correctness and trust problem.

Act 6, the way out: the Ghost Vectors preprint (June 2026) inverted soft-deleted embeddings back to text in three HNSW implementations, 25.5% of exact person names and 46.4% of locations on Wikipedia biographies, 100% of age and gender markers on synthetic medical records, 99% top-1 identity on faces; their fix destroys the key on delete and took recovery to 0%. NIST SP 800-88 Rev. 2 (September 2025) calls a logical result "clear" and infeasible recovery "purge". The SaTML 2025 paper by Eisenhofer and colleagues gives a proof a third party can check without seeing the weights; a residue report or a signature from the deleting party is self-attestation.

Act 7, close: the check is one file, runs on what you have installed, names the file that still holds the bytes, and reports on your versions. End on the open question: hosted stores where you cannot read the disk, and compaction clocks shared across tenants. Credit the neighbouring tools vector-forget, forgetlayer, MemoryProof and Tombstone, and Sebastian Mondragon's post of 6 August 2026.

Tone: two hosts, one leads the investigation, the other keeps asking "but did it actually leave the disk?" Pace like a thriller, with the twist in act 4. No marketing language. Say the show name, Echoes of Tomorrow, once at the start and once at the end.

Hard rule on numbers: the only numbers you may say are these, exactly as written: five stores, two of five, two markers, 1,000 operations, 1,020 writes, 59 writes, threshold 50, 0.2, 1000 vectors, 20 percent, 50 tuples, 200,050 dead tuples, one million rows, two months, six months, 180 days, 17 September 2026, 29 July 2025, 23 March 2026, 18 February 2026, 32 authorities, 764 controllers, 25.5 percent, 46.4 percent, 100 percent, 99 percent, 0 percent, three HNSW implementations, June 2026, September 2025, 2007, 6 August 2026, the version numbers chromadb 1.1.1, qdrant-client 1.18.0, mem0ai 2.0.11, lancedb 0.30.0, inspeximus 2.24.0, issue 7659, issue 3245, Article 17, Article 19, SP 800-88 Rev. 2 (say it as "eight hundred dash eighty-eight"). Do not compute, round, estimate, or invent any other number, percentage, dimension, count or example figure. If you want to illustrate, use words, never a new number. Do not describe any vector's dimension. Do not mention a hex editor or forensic tools the article does not name.
