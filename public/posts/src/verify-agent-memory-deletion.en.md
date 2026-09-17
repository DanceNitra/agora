# Your delete() returned OK. Are the bytes still on disk?

We stored a record in five agent-memory stores, deleted it through each store's own API, ran the compaction each store exposes, and searched the raw files. On one machine on 17 September 2026, with chromadb 1.1.1, qdrant-client 1.18.0 in local mode, mem0ai 2.0.11, lancedb 0.30.0 and inspeximus 2.24.0, two of the five still held the record's bytes. All five delete calls returned success. Both cases are documented: mem0 keeps a history log by design, and Chroma keeps the text in its write-ahead log until 1,000 operations pass. A second record that nobody deleted stayed in every store, which is how we know an "absent" means the store deleted one record rather than everything. The check is [one file](https://github.com/DanceNitra/ramr/blob/main/integrity/erasure_selfcheck.py). It runs on the backends you have installed, names the file that still holds the bytes, and reports on your versions.

## The gap is between an obligation and an observable

GDPR Article 17(1) states the duty: the controller "shall have the obligation to erase personal data without undue delay" where one of its listed grounds applies. Article 19 adds that recipients of that data must be told, unless that proves impossible or involves disproportionate effort.

Both are stated as outcomes. Neither is something your code reports. What your code reports is that a function returned without raising.

The regulators' own survey shows where their attention is. The EDPB's coordinated enforcement report on the right to erasure, adopted 18 February 2026, drew on 32 data protection authorities and 764 controllers. The challenges it names are procedural: missing internal procedures, "reliance by some controllers on inefficient anonymisation techniques to handle erasure requests as an alternative to deletion", and difficulties with retention periods and "the deletion of personal data in the context of back-ups". It says nothing about checking whether the bytes went, and nothing about vector stores. So the legal text is strict and there is no enforcement precedent on residue. Today a leftover value is a correctness and trust problem, and it becomes a compliance problem when someone asks about it.

## Every engine defers physical deletion, and that is old news

Databases have marked rows deleted and reclaimed the space later for as long as they have existed. Stahlberg, Miklau and Levine showed at SIGMOD 2007 that tools which bypass the SQL interface and search the binary files recover deleted records from PostgreSQL, MySQL, DB2 and SQLite, with and without vacuum. Vector stores inherited the design. What is new is where agent memory puts personal data, and how rarely anyone checks the deferral.

| where the value survives | what the vendor says | the number |
|---|---|---|
| the vector index (server) | Qdrant removes deleted vectors per segment when two thresholds are met. A maintainer, on the tracker: removing them "immediately is more expensive than keeping them until enough have been deleted." | `deleted_threshold: 0.2` and `vacuum_min_vector_number: 1000` in Qdrant's config |
| the write-ahead log | Chroma appends a DELETE row; the earlier ADD row with the document text stays until the HNSW segment persists. A commenter on the open issue: until then the purge "coalesces a missing vector-segment offset to -1 and deletes nothing." | `hnsw:sync_threshold`, default 1000. Our measurement, [one probe](https://github.com/DanceNitra/agora/blob/main/research/probes/chroma_wal_retention_threshold.py): with the threshold set to 50 the text leaves the file after 59 filler writes, with the default after 1020 |
| the heap and the index, until vacuum | pgvector overwrites a deleted element with zeros when the index is vacuumed (`memset` in `hnswvacuum.c`). PostgreSQL decides when that happens. | autovacuum fires after more than 50 plus 20% of the table in dead tuples: over 200,050 on a million rows |
| a history log | mem0 keeps a history database by design; `reset()` purges it. Its graph store also kept deleted nodes: issue #3245 was open from 29 July 2025 until the fix landed on 23 March 2026. | `history.db` |
| backups | Google Cloud describes deletion as stages: soft delete, then "deleted successively from Google's active and backup storage systems". | "about two months" from active systems, backups "within six months", a 180-day commitment |

The index row matters because the residue is not only text. [Ghost Vectors](https://arxiv.org/abs/2606.18497) (Chakraborttii et al., preprint, June 2026) inverted soft-deleted embeddings back to text in three HNSW implementations. On Wikipedia biographies they report 25.5% of exact person names and 46.4% of geographic locations recovered. On synthetic medical records, 100% of patient age and gender markers. On facial embeddings, 99% top-1 identity recovery. Their fix encrypts each vector and destroys the key on delete, which took observed recovery to 0% and emits an ECDSA-signed proof of the deletion event. A preprint's numbers await review; the mechanism does not depend on them.

## What NIST calls this

NIST SP 800-88 Rev. 2, final in September 2025, is about storage media, and its words fit here with that caveat. Clear applies "logical techniques to sanitize data in all user-addressable storage locations", against "simple, non-invasive data recovery techniques using the same interface that is available to the user". Purge makes recovery "infeasible using state-of-the-art laboratory techniques", and the document prefers it "when possible".

A `delete()` that returned success tells you the call ran. A residue check that reads the store's own files afterwards validates a clear-level outcome. Key destruction, as in Ghost Vectors' scheme or Google's cryptographic erasure for Cloud Storage, is what purge looks like in software. Rev. 2 also renamed the activity to "validation" and dropped almost all "verification" language. Either word means the same thing here: look at the medium after the operation instead of at the operation's return code.

## Run it on your own store

The check is one file, standard library plus whichever backends you already have installed. It auto-detects them.

```bash
curl -O https://raw.githubusercontent.com/DanceNitra/ramr/main/integrity/erasure_selfcheck.py
python erasure_selfcheck.py
```

For each backend it stores two markers, deletes one through the backend's documented API, runs what the backend exposes as compaction (a SQLite VACUUM where the store is SQLite, LanceDB's `optimize()`, nothing where nothing is exposed), then searches the raw store files for both. The output looks like this:

```
==========================================================================
agent-memory erasure self-check - YOUR stack
==========================================================================
  instrument   ok             reader must see an undeleted marker
  inspeximus   absent
  your-store   PRESENT        somefile.sqlite3
--------------------------------------------------------------------------
'PRESENT' = the marker's bytes are still in the store's files after its own
delete + compaction (logical residue). 'absent' = gone, and the undeleted
control marker is still there. 'control-failed' and 'compaction-failed' =
no verdict.
```

`absent` means the bytes are gone from the store's own files after its own cleanup, and the second marker, the one nobody deleted, is still there. `PRESENT` means they are not gone, and the file that still holds them is named. `control-failed` means the second marker vanished too, so the store deleted more than it was asked to, or the probe never wrote, and there is no verdict. `compaction-failed` means the backend's compaction raised, and there is no verdict either. That last status exists because an earlier version of this check swallowed the exception and reported PRESENT for LanceDB after no compaction had run; the supported `Table.optimize()` clears the marker. A verdict after a step that never ran describes the instrument rather than the store.

Our run on 17 September 2026:

| backend | result | where |
|---|---|---|
| instrument | ok | |
| inspeximus | absent | |
| qdrant-local | absent | `qdrant_client` local mode: a SQLite table, no segments, no optimizer. Not the server in the table above |
| lancedb | absent | after `optimize()` |
| mem0 | PRESENT | `history.db`, the history log, by design |
| chroma | PRESENT | `chroma.sqlite3`, the write-ahead log, below `hnsw:sync_threshold` |

Every control marker survived, so each `absent` is a delete of exactly what was asked. Both `PRESENT` rows are documented behaviour and the table names the threshold or the design choice behind each. Two writes cannot cross a 1,000-operation threshold, so on a threshold-based store this check reports the state of a quiet collection, which is the state a low-traffic personal-data store is in most of the time. If a result on your stack surprises you, the right next step is the backend's issue tracker.

## Reading the result honestly

Two things decide whether a check like this is worth anything.

It has to be able to fail. A test that asserts `delete()` returned OK passes on an implementation that deletes nothing. This one asserts on the store's bytes afterwards, which is a claim about the world rather than about the call. The `instrument` row runs the same reader on a directory where nothing was deleted; if it does not report PRESENT, every other row is void.

It needs a positive control. Delete one record, confirm it is gone, then confirm a different record is still there. Without the second half, a store that silently wiped everything would score a perfect pass. Every backend check here carries that pair.

Counting rows through the API measures what the API shows you. After a deletion, query the store for the fact and read the raw files. Both are cheap.

## What this does not tell you

- It checks logical residue, not at-rest security. A plaintext store of any library leaves bytes in free space, on over-provisioned SSD blocks and in backups. The defence there is full-disk encryption and crypto-erasure, destroying the key. This check does not judge that layer.
- It matches literal bytes. A stored value is caught; a paraphrase of it is not, and neither is an embedding that no longer contains the text. Ghost Vectors recovers from the vector; this reader does not. A store that compresses or encodes its pages passes this reader without deleting anything, and a file the reader cannot open is reported as no verdict, never as absent.
- It runs where you can read the files. On a hosted store, Pinecone, Qdrant Cloud, mem0 Platform, Chroma Cloud, you cannot, and the only runnable half is asking the store the question again. Compaction thresholds there are per collection or per segment, never per subject, so one subject's erasure latency depends on every other tenant's write volume.
- A `PRESENT` from a threshold or an audit log is a design choice. Call the backend's documented purge and re-run.
- It is the operator checking the operator. A residue report from the deleting party, ours included, is self-attestation. A proof that a third party can check without reading the operator's disk is a different thing, covered in the next section.

## Verification one layer up

The same gap exists in model weights. Eisenhofer, Riepel, Chandrasekaran, Ghosh, Ohrimenko and Papernot ([IEEE SaTML 2025](https://arxiv.org/abs/2210.09126)) start from the premise, which they credit to earlier work, that a user "is unable to verify whether their data was unlearnt from an inspection of the model parameter alone". They propose a cryptographic definition of verifiable unlearning and a protocol built on SNARKs and hash chains in which the server proves a record is not in the training set, and the proof can be checked by someone who never sees the weights. Ghost Vectors' ECDSA signature and our own residue report are signed by the party that did the deleting, so they show that the act happened without letting a stranger confirm it. Nobody has closed that distance for a vector store yet.

## What we do about it

Verifiable deletion is the axis our own library is built on. `inspeximus` removes the content on `forget()`, writes a hash-chained, content-free tombstone for each deletion, and returns a residue report: how many records were scanned, what values were searched for, what was found, and the caveat above, that substring matching catches a stored value and misses a paraphrase. The tool prints its own limits in its own output.

Run the check on your own stack first. A clean result costs you a minute and tells you something you did not know.

## Neighbours and prior art

Other people have built tools for the same question, and they deserve credit. `vector-forget` (PyPI, July 2026) hard-deletes and verifies erasure in pgvector. `forgetlayer` (PyPI, July 2026) cascades a deletion across raw records, embeddings and summaries and, on mem0, reports that the memory text survives in the SQLite history table. MemoryProof (GitHub, August 2026) plants canaries with a target subject and a control subject and ships an over-delete adapter. Tombstone (GitHub, September 2026) tracks a subject across a RAG stack and reports a logical pass beside a physical fail. Sebastian Mondragon's [post of 6 August 2026](https://particula.tech/blog/vector-database-gdpr-erasure-hnsw-soft-delete) walked engine by engine through the same deferral with reclamation scripts. What this file adds is the instrument row, five stacks in one script, and the measured Chroma threshold series.

## FAQ

**Does deleting from a vector database actually delete the data?**
Not immediately, by design. Qdrant's server waits until a segment holds 20% deleted vectors and at least 1,000 vectors. Chroma's log keeps the text until the HNSW segment persists, by default after 1,000 operations; we measured 1,020 filler writes. pgvector zeroes the vector at vacuum, and PostgreSQL vacuums after more than 50 plus 20% of the table in dead tuples. The delete call returns success at the start of that delay.

**How do I verify a deletion in my agent's memory?**
Write two known markers, delete one through your backend's own API, run its own compaction, then read the raw store files and search for both. The deleted one must be absent and the other must still be there. If the deleted marker's bytes are still present, the delete has not removed them from disk yet.

**Are embeddings personal data under GDPR?**
That depends on whether the embedding can be linked back to a person, and Ghost Vectors reports that the link is practical on soft-deleted vectors. Your DPO decides the legal question. The check settles the prior one: whether the vector and its text are still on disk.

**Is a soft delete enough for the right to erasure?**
A soft delete hides a record from queries while leaving it in storage. Whether that satisfies Article 17 is a question for your DPO and your regulator; the EDPB's 2026 report does not address it. You cannot make that judgement until you know which of the two your stack is doing. This check tells you.

*Runnable receipt for everything above: [`integrity/erasure_selfcheck.py`](https://github.com/DanceNitra/ramr/blob/main/integrity/erasure_selfcheck.py). It is deterministic, runs offline, and tests only backends you already have installed.*

*Updated 17 September 2026: added the five-backend run, the vendors' thresholds with their sources, the NIST SP 800-88 Rev. 2 vocabulary, the EDPB report, Google's deletion timeline, the SaTML 2025 paper, and the neighbouring tools. The self-check gained a positive control, an instrument row and a refusal when compaction cannot run.*
