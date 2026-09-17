# Verified context for the re-issue of "Verify AI agent memory deletion"

Material from the NotebookLM deep research (notebook b1ad1d78-66e3-4794-836d-8a61b374f074, two runs on
2026-09-17, 58 sources) that survived a check against its primary source. Each item names the source it was
read from. Anything not listed here did not survive and must not enter the article or the episode.

## 1. NIST SP 800-88 Rev. 2, Guidelines for Media Sanitization (Chandramouli and Hibbard), final September 2025

Source: https://doi.org/10.6028/NIST.SP.800-88r2 (read from the PDF text, 112,506 chars; header carries
the DOI and "September 2025") and https://csrc.nist.gov/pubs/sp/800/88/r2/final (history: 07/21/25 Draft,
09/26/25 Final; supersedes Rev. 1 of 2014). Verified by an independent agent 2026-09-17: every quote verbatim.

- Clear (3.1.1): "applies logical techniques to sanitize data in all user-addressable storage locations of
  an ISM for protection against simple, non-invasive data recovery techniques using the same interface that
  is available to the user (e.g., host interface)."
- Purge (3.1.2): "apply physical or logical techniques that make the recovery of target data infeasible
  using state-of-the-art laboratory techniques but preserves the ISM in a potentially reusable state."
  "When possible, the purge sanitization method should be used instead of the clear sanitization method."
- Destroy (3.1.3): renders "target data recovery infeasible using state-of-the-art laboratory techniques
  and results in the subsequent inability to use the ISM for the storage of data."
- On validation (Appendix D, Change Log, p. 38): "Sanitization validation is described and focuses on checks
  (e.g., errors, anomalies, and other issues) to see whether the attempted sanitization was effective from a
  confidentiality and sensitivity perspective." The same Change Log says "Almost all 'verification' language
  has been removed." Rev. 2 uses the word validation (Sec. 4.5.2, p. 24). Write "validation" when
  attributing the idea to NIST; "verification" is our word, not theirs.
- The document is about media (ISM), not application-level delete calls. Use it for vocabulary only: our
  check is a validation of a clear-level outcome read through the store's own files.

## 2. Google Cloud, "Data deletion on Google Cloud"

Source: https://docs.cloud.google.com/docs/security/deletion ("This content was last updated in May 2024";
verified verbatim by an independent agent 2026-09-17).

- Stages: Stage 2 soft deletion ("a brief internal staging and recovery period"), Stage 3 "the data is
  deleted successively from Google's active and backup storage systems", Stage 4 "deleted data is
  eliminated from backup systems using both overwriting and cryptographic techniques." Marking for
  deletion happens "within a maximum period of 24 hours"; a recovery period "of up to 30 days might apply".
- "it generally takes about two months to delete data from active systems, which is typically enough time
  to complete two major garbage collection cycles."
- "The Google backup cycle is designed to expire deleted data within data center backups within six
  months of the deletion request."
- "Google Cloud commits to delete customer data within a maximum period of about six months (180 days)."
- "In Cloud Storage, customer data is also deleted through cryptographic erasure." Stated for Cloud
  Storage only; the preceding sentence says the other Compute, Storage and Database products are
  overwritten over time. Do not generalise cryptographic erasure to all of Google Cloud.

## 3. Eisenhofer, Riepel, Chandrasekaran, Ghosh, Ohrimenko, Papernot, "Verifiable and Provably Secure Machine Unlearning", IEEE SaTML 2025

Source: https://arxiv.org/abs/2210.09126 (v3, March 2025; venue stated on the abstract page)

- The abstract states, prefixed "recent work shows", that "a user is unable to verify whether their data
  was unlearnt from an inspection of the model parameter alone." The paper reports this as prior work,
  not as its own finding; cite it as the paper's premise. Accepted at IEEE SaTML 2025 (arXiv comment;
  satml.org/2025/program lists it; IEEE Xplore 10992417). Versions v1 2022-10-17, v2 2023-03-20, v3 2025-03-05.
- Proposes "the first cryptographic definition of verifiable unlearning" and a protocol "using SNARKs and
  hash chains"; the server proves "that d is not part of D'."
- Validated "for linear regression, logistic regression, and neural networks."

## 4. Chakraborttii, García Alvarado, Abdulofizova, Dwivedi, "Ghost Vectors: Soft-Deleted Embeddings Remain Reconstructible in HNSW Vector Databases", arXiv 2606.18497, submitted 16 June 2026 (v1)

Source: https://arxiv.org/abs/2606.18497

- "three HNSW implementations"
- Wikipedia biographies: "25.5% of exact person names and 46.4% of geographic locations"
- Medical (Synthea): "100% for both patient age and gender markers"
- Faces: "top-1 identity recovery reaches 99%"
- Fix: "Epoch Key Rotation, which encrypts vectors and discards the key upon deletion", "reduces observed
  PII recovery to 0%", "generates an ECDSA-signed cryptographic proof as an auditable record of the
  deletion event."
- Preprint, not peer reviewed at the time of writing: arXiv comment "Prepared for submission", single
  version v1, no journal reference as of 2026-09-17. Second author indexed by arXiv as "Alvarado".

## 5. Chroma: deleted rows stay in the write-ahead log until the HNSW segment persists

Sources: https://github.com/chroma-core/chroma/issues/7659 (open, filed 2026-08-29 by rutvikbuilds, 4
comments, all authors `NONE` association, no maintainer reply as of 2026-09-17, read in full) and our own
measurement of 2026-08-30 (memory `a-remedy-arm-that-could-not-fail-and-a-receipt-i-overwrote`).
Chroma `main` source: `sync_threshold` defaults to 1000 (collection_configuration.py:461,
configuration.py:336, hnsw_params.py:80); local_persistent_hnsw.py:296 persists at the threshold;
db/mixins/embeddings_queue.py:145 has `Coalesce(max_seq_id.seq_id, -1)`. Cite the reporter's CORRECTED
comment, not the issue title (which still says "reproduces closed #3793") and not the 4th comment of
2026-09-13, which repeats the uncorrected 150-write numbers.

- The WAL (`embeddings_queue` in `chroma.sqlite3`) is append-only; `delete()` appends a DELETE row and the
  earlier ADD row with the document text stays.
- Purge removes rows with `seq_id < min(segment max_seq_id)`; the HNSW segment writes `max_seq_id` when it
  persists, at `hnsw:sync_threshold` (default 1000). jstar0: "Until that persist, `purge_log` coalesces a
  missing vector-segment offset to -1 and deletes nothing."
- Reporter's corrected run (chromadb 1.5.9): queue collapses "from 752 to 1 at the threshold"; the subject
  text left the file between 1000 and 1250 further writes, which is SQLite page reuse, "VACUUM is the
  real answer there."
- Reporter: "A collection holding personal data that sees fewer than ~1000 operations retains the text of
  deleted records for as long as it stays quiet, and nothing in the public API forces the purge."
- Our own measurement, re-run 2026-09-17 with the public probe research/probes/chroma_wal_retention_threshold.py
  on chromadb 1.1.1, batch 1, deterministic: threshold 50 clears after 59 filler writes, the default after 1020,
  raw file and after VACUUM alike, control present. (The 2026-08-30 figures 60 and 1100 had no surviving
  receipt and are superseded.)
- jstar0 on `chroma vacuum`: a raw scan "can still see the bytes until VACUUM (or `chroma vacuum`)
  rewrites the file."

## 6. Qdrant: deleted vectors are removed per segment when two thresholds are met

Sources: https://raw.githubusercontent.com/qdrant/qdrant/master/config/config.yaml (lines 137-142) and
https://github.com/qdrant/qdrant/issues/4081 (closed, 2024-04-22, maintainers generall and timvisee).

- config.yaml: `deleted_threshold: 0.2` ("The minimal fraction of deleted vectors in a segment, required to
  perform segment optimization") and `vacuum_min_vector_number: 1000` ("The minimal number of vectors in a
  segment, required to perform segment optimization").
- generall (member): the parameters "define condition per segment when deleted vectors should trigger the
  optimizer. Please note, that once deleted, vectors are not affecting search results in any way."
- timvisee (member): "It is done this way because actually removing the vectors from disk immediately is
  more expensive than keeping them until enough have been deleted." (issuecomment-2068921872). The same
  comment notes that point and vector counts in Qdrant are approximate.

## 7. pgvector zeroes a deleted element at vacuum; PostgreSQL decides when vacuum runs

Sources: https://raw.githubusercontent.com/pgvector/pgvector/master/src/hnswvacuum.c (lines 685-692) and
https://www.postgresql.org/docs/current/runtime-config-autovacuum.html

- hnswvacuum.c, `MarkDeleted()` lines 687-692 in `hnswbulkdelete()`: `etup->deleted = 1;
  memset(&etup->data, 0, VARSIZE_ANY(&etup->data));` then `ItemPointerSetInvalid` on the neighbour tuple's
  indextids. The vector bytes are overwritten with zeros when the index is vacuumed. Caveat: VACUUM skips
  index cleanup "when there are very few dead tuples" (sql-vacuum.html, INDEX_CLEANUP), so a single VACUUM
  after one delete does not guarantee the memset ran. Particula's post of 2026-08-06 already quotes these
  two lines; the point is not novel, credit them.
- PostgreSQL: `autovacuum_vacuum_threshold` "The default is 50 tuples"; `autovacuum_vacuum_scale_factor`
  "The default is 0.2 (20% of table size)" (runtime-config-autovacuum.html). The combining rule is on
  routine-vacuuming.html (24.1.6): vacuum threshold = base + scale factor * reltuples, and autovacuum fires
  when obsoleted tuples EXCEED it, so a table of 1,000,000 rows autovacuums after more than 200,050 updated
  or deleted tuples. `autovacuum_vacuum_max_threshold` (default 100,000,000) exists in the PostgreSQL 18
  docs only; do not cite it for 17 and earlier.

## 8. Prior art on the same question

Source: https://particula.tech/blog/vector-database-gdpr-erasure-hnsw-soft-delete (Sebastian Mondragon,
2026-08-06).

- Names pgvector, Qdrant, Milvus, Weaviate, Chroma, FAISS, hnswlib; states "soft deletion is documented
  intended behaviour in every HNSW implementation"; gives reclamation scripts for three engines (pgvector
  SQL, Qdrant PATCH, Milvus pymilvus) and prose for the rest; the hnswlib block is a recovery demo. Names
  pgvector 0.8.6 (2026-07-29) and quotes the same two hnswvacuum.c lines.
- Same thesis as our post of 2026-08-01, five days later, independent. Credit it. Our differences: the
  self-check with a positive control, and the measured retention numbers above.

## 9. Our own self-check, run 2026-09-17 with the positive control

Source: https://github.com/DanceNitra/ramr/blob/main/integrity/erasure_selfcheck.py at commit 8e3e913
(authored 2026-09-17T12:49:48Z); run on this machine twice (once by me, once by an independent agent),
same six rows, exit 0, under one minute.

Versions: chromadb 1.1.1, qdrant-client 1.18.0 (local mode, `path=`), mem0ai 2.0.11, lancedb 0.30.0,
inspeximus 2.24.0.

| backend | result | file |
|---|---|---|
| instrument | ok | reader sees an undeleted marker |
| inspeximus | absent | |
| qdrant | absent | |
| mem0 | PRESENT | history.db (history log, by design; `reset()` purges) |
| chroma | PRESENT | chroma.sqlite3 |
| lancedb | PRESENT | a .lance fragment |

Every row's control marker survived, so every `absent` is a delete of exactly what was asked.
Mutation test of the probe: a store that wipes everything reads `control-failed`, one that deletes nothing
reads PRESENT, one that deletes exactly reads `absent`.

## 10. From the July 2026 storm on erasure completeness, re-verified 2026-09-17

Sources: storm-reports/correction-propagation-erasure-completeness-agent-memory-briefing.html
(2026-07-25, 17/17 citations checked), plus a fresh read of each primary source below.

- mem0ai/mem0 issue #3245 "Memory deletion does not clean up Neo4j graph data": opened 2025-07-29,
  closed 2026-03-23 by PR #4505 "fix: clean up graph store data on Memory.delete()" (merged
  2026-03-23). Reporter: `Memory.delete(memory_id)` "only removes data from the vector store (Qdrant)
  and adds a history record, but fails to remove corresponding nodes and relationships from the Neo4j
  graph store." (https://github.com/mem0ai/mem0/issues/3245)
- EDPB, report on the Coordinated Enforcement Framework action on the right to erasure, adopted
  18 February 2026: 32 data protection authorities, 764 controllers. Challenges named include "lack of
  appropriate internal procedures to handle requests", "reliance by some controllers on inefficient
  anonymisation techniques to handle erasure requests as an alternative to deletion", and
  "difficulties faced by controllers regarding the determination of retention periods and the deletion
  of personal data in the context of back-ups". The report does not mention verifying that data is
  gone, nor vector or AI systems.
  (https://www.edpb.europa.eu/news/news/2026/edpb-identifies-challenges-hindering-full-implementation-right-erasure_en)
- The storm's reading of the law, verified there: Art. 17(1) carries no cost or technology qualifier;
  the "reasonable steps ... taking account of available technology and the cost of implementation"
  wording is Art. 17(2) and applies to data the controller made public. Strict text, no enforcement
  precedent on residue: a residue finding is a correctness and trust problem today and a compliance
  problem only prospectively. Do not write "residue is a GDPR violation".
- The storm's advice, adopted: test erasure by asking the question again, not by counting rows.

## Verification banner (verify-claims, 2026-09-17)

10 items checked by four independent verifiers plus two direct re-reads (mem0 #3245, EDPB) · 0 FALSE ·
3 corrected (PostgreSQL formula location and "more than"; PG18-only max threshold; Particula script count)
· 2 demoted (Ghost Vectors is a preprint; the SaTML premise sentence is prior work). Reports:
tasks/verify_A_nist_gcp.report.md, verify_B_papers.report.md, verify_C_chroma_qdrant.report.md,
verify_D_pgvector_priorart_selfcheck.report.md in the session tasks directory.

## 11. Prior art and neighbouring tools, found by the red-team and verified 2026-09-17

- Stahlberg, Miklau, Levine, "Threats to Privacy in the Forensic Analysis of Database Systems", SIGMOD 2007,
  https://people.cs.umass.edu/~miklau/assets/pubs/sigmod2007LMS/stahlberg07forensicDB.pdf (HTTP 200): tools
  that bypass the SQL interface and search binary files recover deleted records from PostgreSQL, MySQL,
  DB2 and SQLite, with a VACUUM column per system.
- `vector-forget`, PyPI, first release 2026-07-13, summary "Hard-delete AND verify erasure of a data
  subject from your vector store" (pgvector). https://pypi.org/project/vector-forget/
- `forgetlayer`, PyPI first release 2026-07-17, github.com/Ajay6601/forgetlayer (created 2026-07-17),
  summary "Provable deletion for AI agent memory: cascade-delete a memory across raw records, embeddings,
  summaries"; its README reports on mem0 that the memory text survives in the SQLite history table.
- MemoryProof, github.com/Hughhhhcoder/MemoryProof, created 2026-08-18, description "Test what your AI
  remembers. Prove what it forgot."; canaries, target plus control subject, a reference-overdelete adapter.
- Tombstone, github.com/Poojan6216/tombstone, created 2026-09-10, description "Track where a data subject's
  data actually went across a RAG/LLM stack, erase it everywhere, and get a receipt"; reports logical PASS
  beside physical FAIL for Chroma, FAISS, Qdrant, pgvector.
- Chroma issue #3793 (2025-02-13) is the original report that #7659 reproduces.

## 12. The self-check after the red-team, probe at commit 5a19373 (ramr main)

Run 2026-09-17 after the fix: instrument ok, inspeximus absent, mem0 PRESENT (history.db, by design),
chroma PRESENT (chroma.sqlite3, below hnsw:sync_threshold), qdrant-local absent, lancedb absent.
Two of five PRESENT. The earlier "lancedb PRESENT" in section 9 was a probe artifact: both compaction
methods raised ImportError (no pylance; deprecated in 0.30) and the probe swallowed it. `Table.optimize
(cleanup_older_than=timedelta(0))` clears the marker with the control intact. Mutation controls: a raising
compaction reads compaction-failed, wipe-all reads control-failed, delete-nothing reads PRESENT,
delete-exactly reads absent. inspeximus `forget()` docstring (core.py): "HARD-DELETE memories" and "EVERY
deletion emits a hash-chained, content-free tombstone".
- Hosted stores named as examples of "no filesystem access" (blind-spot lens): Pinecone, Qdrant Cloud,
  mem0 Platform, Chroma Cloud. No claim about any of them beyond that the customer cannot read raw files.

- Probe at commit 6753cf3: unreadable files are no verdict; docstring states the byte-reader limit.
