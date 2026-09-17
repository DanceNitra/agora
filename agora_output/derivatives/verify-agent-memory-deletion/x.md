# X thread

1.
Two of five agent memory stores still held a deleted record on disk after their own delete and compaction. All five delete calls returned success. The two were mem0 and Chroma, on one machine on 17 September 2026.

2.
None of it is a bug. Chroma's write-ahead log keeps the document text until 1,020 more writes at the default threshold. mem0 keeps a history log on purpose. Google Cloud commits to 180 days before a deletion reaches backups.

3.
The control: a second record that nobody deleted survived in all five stores. Without it, "absent" could mean the store wiped itself. With it, absent means the store deleted one record.

4.
The false lead: an earlier version of the check flagged LanceDB too. Its compaction call had raised an error the script swallowed, so nothing had compacted. The verdict belonged to the instrument, not the store.

5.
One-file check, runs offline on what you have installed: https://github.com/DanceNitra/ramr/blob/main/integrity/erasure_selfcheck.py

The article: https://dancenitra.github.io/agora/public/posts/verify-agent-memory-deletion.html

The same case as a podcast episode: https://open.spotify.com/episode/7khBL2ppx1uTfsY9UtuLMJ
