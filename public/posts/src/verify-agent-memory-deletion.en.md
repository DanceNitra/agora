# You deleted the user's data. Can you prove it's gone?

**The short version.** Your agent's memory has a `delete()`. It returns success. That tells you the call ran — it does not tell you the data left. In most stacks the value lives in more than one place: the vector, the payload or metadata alongside it, and often a history or audit log. A delete that clears one and not the others returns exactly the same success. **[This free self-check](https://github.com/DanceNitra/ramr/blob/main/integrity/erasure_selfcheck.py)** plants a unique marker in your own store, calls *your* backend's own delete and its own compaction, then reads the raw files back and tells you whether the marker's bytes are still there. It makes no claim about anyone's product. It hands you a receipt for your stack.

## The gap is between an obligation and an observable

GDPR Article 17(1) is unambiguous about the duty: the controller "shall have the obligation to erase personal data without undue delay." Article 19 adds that recipients of that data must be told the erasure happened.

Both are stated as outcomes. Neither is something your code reports. What your code reports is that a function returned without raising.

That gap is where verification lives, and almost nothing in the agent-memory ecosystem fills it. You can find plenty of writing on *how to comply*. There is very little on *how to check*.

## Why a successful delete can leave the data behind

Three places a value survives a delete that reported success:

| where | why it survives |
|---|---|
| **the vector index** | approximate-nearest-neighbour structures (HNSW, IVF) often mark a node as removed rather than rebuilding the graph. The vector stays reachable in the file until a rebuild |
| **the payload or metadata** | many stores keep the original text beside the embedding. Deleting the vector entry does not always delete the row that carried the text |
| **a history or audit log** | some backends record every write and delete by design. This is a feature, not a defect — but the value is still on disk, and a compliance reader will treat it as retained |

The first of these is not folklore, and the numbers are worse than the mechanism sounds. [Ghost Vectors](https://arxiv.org/abs/2606.18497) (Chakraborttii et al., 2026) tested three HNSW implementations and recovered the **original text** from soft-deleted embeddings by reading the raw index files at the storage layer — bypassing the API entirely — and inverting the vectors. On a Wikipedia biographical dataset they recovered **25.5% of exact person names** and **46.4% of geographic locations**. On structured medical records, **100% of patient age and gender markers**. On facial embeddings, **99% top-1 identity recovery**. Their proposed fix encrypts each vector and destroys the key on delete, emitting an ECDSA-signed proof of the deletion event — which is to say the research is converging on the same answer: a deletion you can verify beats a deletion you assert.

None of this means your stack is broken. It means the question "did the delete work?" has an answer you have not measured.

## Run it on your own store

The check is one file, standard library plus whichever backends you already have installed. It auto-detects them.

```bash
curl -O https://raw.githubusercontent.com/DanceNitra/ramr/main/integrity/erasure_selfcheck.py
python erasure_selfcheck.py
```

It writes a marker string into each backend it finds, calls that backend's documented `delete`, runs its documented compaction, and then greps the raw store files for the marker's bytes. The output looks like this:

```
==========================================================================
agent-memory erasure self-check - YOUR stack
==========================================================================
  inspeximus   absent
  your-store   PRESENT        somefile.sqlite3
--------------------------------------------------------------------------
'PRESENT' = the marker's bytes are still in the store's files after its own
delete + compaction (logical residue).
```

`absent` means the bytes are gone from the store's own files after its own cleanup. `PRESENT` means they are not, and the file that still holds them is named so you can look yourself.

We publish the tool and not a league table. If a result surprises you, the right next step is the backend's issue tracker through normal coordinated disclosure — not a blog post, and not this one.

## Reading the result honestly

Two things decide whether a check like this is worth anything.

**It has to be able to fail.** A test that asserts `delete()` returned OK passes on an implementation that deletes nothing. This one asserts on the store's bytes afterwards, which is a claim about the world rather than about the call.

**It needs a positive control.** Delete one record, confirm it is gone — then confirm a *different* record is still there. Without the second half, a store that silently wiped everything would score a perfect pass. Any deletion test you write yourself should carry that pair; ours does, and it is the first thing to check in anyone else's.

## What this does not tell you

Scope, stated plainly, because a verification tool that overstates its reach is worse than none.

- **It checks logical residue, not at-rest security.** A plaintext store of *any* library leaves bytes in free space, on over-provisioned SSD blocks and in backups. The defence there is full-disk encryption and crypto-erasure — destroying the key. This check does not judge that layer and cannot.
- **It matches literal bytes.** A stored value is caught; a paraphrase of it is not. A clean result is evidence, not proof.
- **A `PRESENT` from an audit log is a design choice, not a bug.** Some backends retain history deliberately. Call that backend's documented purge and re-run.

## What we do about it

Verifiable deletion is the axis our own library is built on, so it is fair to say what that means concretely. `inspeximus` deletes content rather than tombstoning it, and every erasure returns a residue report: how many records were scanned, what values were searched for, what was found, and the same caveat printed above — that substring matching catches a stored value and misses a paraphrase. The tool prints its own limits in its own output.

That is the whole design position. A deletion you cannot check is a promise. A deletion that hands back a receipt you can re-verify without trusting us is a control.

Run the check on your own stack first. If it comes back clean, you have learned something worth knowing for free.

## FAQ

**Does deleting from a vector database actually delete the data?**
Not always. Vector indexes frequently mark entries as removed rather than rebuilding, and the original text often lives in a payload or metadata row that a vector delete does not touch. The delete call still returns success.

**How do I verify a deletion in my agent's memory?**
Write a known marker, delete it through your backend's own API, run its own compaction, then read the raw store files and search for the marker. If the bytes are still present, the delete did not remove them from disk.

**Are embeddings personal data under GDPR?**
Where an embedding derives from text containing personal data and can be linked back to an identifiable person — through stored pairings, metadata, or re-identification — it is treated as personal data. That makes the vector itself in scope for Article 17.

**Is a soft delete enough for the right to erasure?**
A soft delete hides a record from queries while leaving it in storage. Whether that satisfies Article 17 is a question for your DPO and your regulator, but the practical point is prior: you cannot make that judgement until you know which of the two your stack is doing. This check tells you.

*Runnable receipt for everything above: [`integrity/erasure_selfcheck.py`](https://github.com/DanceNitra/ramr/blob/main/integrity/erasure_selfcheck.py). It is deterministic, runs offline, and tests only backends you already have installed.*
