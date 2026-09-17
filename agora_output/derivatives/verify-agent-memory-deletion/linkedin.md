# LinkedIn

## Post

Two of five agent memory stores still held a deleted record on disk. All five delete calls had returned success.

On 17 September I stored two records in mem0, Chroma, Qdrant, LanceDB and inspeximus, deleted one through each store's own API, ran the compaction each one exposes, and searched the raw files for both.

mem0 and Chroma still had the deleted bytes. The record nobody deleted survived in all five, which is how I know an "absent" is a real delete and not a wiped store.

I thought I had found a bug. It is documented behaviour, in the vendors' own words:

→ Chroma keeps the document text in its write-ahead log until 1,020 more writes at the default threshold
→ mem0 keeps a history log on purpose
→ Google Cloud commits to 180 days before a deletion reaches its backups

An earlier version of my check reported LanceDB as holding the record too. Its compaction call had raised an error the script swallowed. The verdict belonged to the instrument, not the store. The check now carries a control marker and refuses to rule when compaction cannot run.

GDPR Article 17 says erase. Your code only says a function returned, and those are not the same observable.

The check is one file, runs offline on the backends you have installed, and names the file that still holds the bytes. Links in the first comment.

Which of your agent's memory stores have you grepped after a delete?

## First comment

The article, with every vendor's own statement, the GDPR and NIST references and the Ghost Vectors numbers: https://dancenitra.github.io/agora/public/posts/verify-agent-memory-deletion.html

The same investigation as a podcast episode, told as a detective story: https://open.spotify.com/episode/7khBL2ppx1uTfsY9UtuLMJ

The one-file self-check for Chroma, Qdrant, mem0, LanceDB and inspeximus: https://github.com/DanceNitra/ramr/blob/main/integrity/erasure_selfcheck.py
