# r/Rag (update to the July erasure thread; the owner pastes)

## Title

I deleted a record from 5 agent-memory stores and grepped the raw files. 2 still had it. All 5 returned success.

## Body

Follow-up to the erasure self-check I posted here in July. I reran it today with a positive control: two markers per store, delete one through the store's own API, run whatever compaction it exposes, then search the store's files for both.

Versions: chromadb 1.1.1, qdrant-client 1.18.0 (local mode), mem0ai 2.0.11, lancedb 0.30.0, inspeximus 2.24.0.

Result: mem0 and Chroma still held the deleted marker's bytes. inspeximus, qdrant-local and lancedb did not. The undeleted marker survived in all five, which is how I know an "absent" is a real delete and the store did not just wipe itself.

Both PRESENT rows are documented behaviour. mem0 keeps a history log on purpose (reset() purges it). Chroma keeps the document text in its write-ahead log until the HNSW segment persists at hnsw:sync_threshold, default 1000. I measured that directly: with the threshold set to 50 the text leaves chroma.sqlite3 after 59 more writes, with the default after 1020. There is an open Chroma issue (#7659) from someone else describing the same mechanism.

Two caveats if you run something similar. LanceDB reads absent only after Table.optimize(); its older cleanup calls raise without pylance, and a check that swallows that exception will report PRESENT after zero compaction. And qdrant in local mode is a SQLite file with no optimizer, so it says nothing about the server's deleted_threshold / vacuum_min_vector_number.

The check is one file and only tests the backends you have installed:
https://github.com/DanceNitra/ramr/blob/main/integrity/erasure_selfcheck.py

If you would rather listen than read, the same investigation is a podcast episode: https://open.spotify.com/episode/7khBL2ppx1uTfsY9UtuLMJ
