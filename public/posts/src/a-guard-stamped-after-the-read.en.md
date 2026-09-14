# Twelve concurrent writers, 9 records lost out of 2,880, every one of them reported as stored. Two causes we measured and refuted before the third one held, and a fourth I named wrongly after the fix shipped.

I ship an agent memory store whose pitch is that a write either lands or tells you it did not. Between
1 and 13 September its own CI said otherwise, and for most of those days nobody read it.

The rule that was broken is old. Emacs, CPython's `importlib` and git's index all take the file's
stat before they read it, cargo records the build's start time before rustc reads the sources, and
git documents why under [racy-git](https://git-scm.com/docs/racy-git). I knew the rule and had written the other order. The rule is old. The measurement is what this
piece adds: two causes that looked right and were refuted, the one that held, and a fourth I named
wrongly after the fix shipped.

The falsifier, up front: run `probes/does_a_wider_change_signature_stop_the_silent_loss.py` from the
inspeximus repository at commit `2e8483a`. It runs three arms, interleaved, thirty rounds of twelve
writers each. If the `old-order` arm loses nothing over thirty rounds, or the `fixed` arm loses
anything, the account below is wrong.

```
arm                               records claimed stored   records missing
old-order  (signature after read)              2,880                  9
fixed      (signature before read)             2,864                  0
widened    (before read, plus st_ino)          2,840                  0
```

## What the pipeline looked like from outside

On 8 September the `tests` workflow had failed on 13 runs in a row, passed once at `81b042f`, and
failed again. The dominant cause was embarrassing and unrelated: 8 of the last 11 red runs failed
on a probe about hook installation. Three more failed on a lock probe that compared its count of
clean trials against a constant while the code above it dropped void trials, so a worker that
failed to start on the runner read as a lost record, and in the last of them the message printed
the losses as `[0, 0, 0]` next to the failure it was reporting. That was fixed in `e7a0d19`. The
run on that commit went green on its second attempt. Its first attempt had lost 1 of 84 records to
the defect this piece is about, and the re-run erased that from the list view.

Inside that noise there was one real line: the concurrent-writer probe reporting a record that a
writer had been told was stored and that was not in the store. The committed receipt of that probe
carries the same shape from a local run, 448 records claimed and 1 missing. That is the property the
product sells, failing, in a run that nobody opened because the previous ten were red for a
different reason. After ten red runs in a row nobody opens the eleventh, so by then the pipeline carried no signal.

## The first cause, measured and wrong: the lock

The store takes a platform lock around every save. On a platform without `fcntl` or `msvcrt` it
writes anyway, unprotected, and until this month that branch left no trace. The obvious hypothesis
was that CI runners were taking that branch. The probe was changed to report the lock state per arm,
and the losses appeared with the lock held on every write. The unlocked branch now records itself and
prints its reason, so this hypothesis can be checked in one line next time instead of a day.

## The second cause, measured and wrong: the signature

Each handle keeps a signature of the file it last read, `(mtime_ns, size)`, and refuses to save over a
file whose signature has changed. Two same-length writes inside one mtime tick would collide on that
signature, and on this NTFS box mtime advanced in steps of 0.5 to 1.5 ms in the same receipt, so the
collision is real. Measured over
1,500 same-length writes in the receipt at `2e8483a`, `(mtime_ns, size)` collided 211 times; adding `st_ino` or a content hash
brought that to 0.

So the third arm widened the signature. It lost nothing, and neither did the arm that only fixed the
ordering. The collisions exist and did not cause this loss. The signature is unchanged in the release.

That sentence is narrower than it looks, and a hostile re-run of the probe found the edge. Every
writer in this workload appends, so every landed write is larger than the file it was checked
against, and two distinct states never share a size. In this workload `(mtime_ns, size)` cannot
collide except through the ordering defect itself, which is why a size-only signature also lost
0 of 1,432 and an mtime-only signature 0 of 1,416 in the re-run. Same-size rewrites inside one
mtime tick, 1 ms on this NTFS box and 4 ms on the ext4 one, are the regime where widening would
matter, and that regime is unmeasured here.

A note on that 211. The release notes for 2.27.1 said 119. The committed receipt says 211, and the
notes said 119 because a number was typed rather than read. The conclusion does not move, since the
collisions were refuted either way, but the figure in the notes was wrong for a day and is corrected
in 2.27.5.

## The cause that held: the guard described a file it never saw

`_load_from_disk` read the file, parsed it, and then stamped the signature. Nothing holds the lock
across those two steps; the lock covers the save. A writer that replaced the file between the read
and the stamp left the loading handle holding the old records under the new signature. The save
guard then compared signatures, saw no change, and rewrote the whole store from the stale view. A JSON
store cannot merge, so the other writer's record was gone, and that writer had already been told it
was stored.

The fix is the order: take the signature before the read. Then the only way a change can slip in is
during the read, which leaves the stored signature older than the file, and the guard reports a
difference that is not there. The caller gets a `StoreChangedOnDisk` it can retry. A false refusal costs one
retry. A silent overwrite costs a record nobody knows is gone.

## What the deterministic test looks like

A race that loses one record in 320 is not a test. The test that pins this monkeypatches the first
handle's read so a second, real handle writes inside it, then asserts that the record which landed inside the read is
still there after the first handle saves. Three cases: the write inside the read is not overwritten,
the late handle still persists its own record, and the control with no competing write keeps
everything. It fails on the old order every time and passes on the new order every time. The probe
stays beside it for the number.

## The fix shipped, CI lost another record, and I named the wrong cause for it

The ordering fix went out as 2.27.1, and its notes warned that a fix lands at the reported
instance while the class survives. Then CI on `ubuntu-latest`, which GitHub gives a public
repository as 4 vCPU, lost `w7:r0` at commit `0a26545`, with the lock held on every writer and the
ordering already fixed.

I found a real defect while chasing it. `reload()`, the retry path the `StoreChangedOnDisk`
message recommends, calls the fixed loader through `_merge_with_disk`, which then assigned a fresh
signature again: a stat after the read, outside the lock. Two arms were added to the probe that
retry through `reload()`, and on ext4 pinned to 2 CPUs, 80 rounds of 12 writers:

```
arm                                                    records claimed   missing
old-order     (signature after read, 2.27.0)                     7,680        50
fixed         (signature before read, 2.27.1)                    7,680         0
widened       (before read, plus st_ino)                         7,676         0
reload-old    (2.27.1, retry through reload(), re-stamp kept)    7,680        15
reload-fixed  (2.27.5, re-stamp removed)                         7,680         0
```

That shipped as 2.27.5, with a deterministic test, and the release notes said CI had caught it.
They were wrong, and a verify pass on this piece is what found it, by reading the CI harness
instead of my account of it. The harness never calls `reload()`. It reopens, like the probe. It
runs the default row store, whose save reaches the same re-stamp, but that store writes only the
ids it touched and derives deletions from a baseline read on the same open, so a stale signature
there cannot delete a peer's row. Measured on the CI path, row store and reopen on refusal, with
the re-stamp restored: 0 of 7,548 lost at 2 CPUs and 0 of 7,248 at 4, while the old-ordering
control lost 40 and 41. The `reload()` defect is real and fixed, and it is not what CI hit.

CI's two losses were `w7:r0` and `w1:r0`, a writer's first record both times, and that shape had
been in the logs since the first one. A probe with 8 writers each writing one record, in two conditions,
ext4 at 4 CPUs, 200 rounds each:

```
condition                                          first writes told stored   missing
the file did not exist when the writers started                       1,600         3
the file existed with one record                                      1,600         0
```

A creation race. `sqlite3.connect` creates the file before the first commit writes the SQLite
header. A second handle opening in that window sees a file that exists and does not look like a
row store, reads it as a JSON store holding nothing, converts that nothing to rows, and puts the
result over the path with `os.replace`, outside any lock. The first writer had already been told
its record was stored. 2.27.6 runs that conversion under the store lock and reads the header again
inside it, so a store a peer has created since is loaded, not replaced: 0 of 1,600 on the same
probe. The deterministic test reproduces the window without timing and fails 2 of 3 on 2.27.5.

The 2.27.5 notes now carry the correction beside the sentences that were wrong, the same way the
2.27.1 notes carry the 119. Two releases in a row each fixed something real and each described
its own evidence wrongly in one place, and both times the receipt that showed it was one I had
not read.

## What I would do differently

Read a red pipeline as its own defect, before it hides the next one. Make every guard say which
records it lost, not how many, because "1 missing" sent me to the lock and the signature, and the
names of the lost records would have pointed at the handle that held stale data. And when two
hypotheses die in a day, write down that they died, in the release notes, so the next person does not
spend the day again. The notes for 2.27.1 do that; this piece is the longer version.

The hostile re-run also left a bill. On Windows about one open in a hundred under this contention
raises `PermissionError`, because the loader reads the file while a peer is replacing it and does
not retry. That writer stores nothing and says so, which is the honest half of the pitch, and it is
still a defect. It is the next fix.

---

Receipts: `probes/does_a_wider_change_signature_stop_the_silent_loss.result.json` (three arms, 30
rounds), `probes/what_a_concurrent_writer_is_told_against_what_the_store_keeps.result.json` (lock
state per arm, and the control that removes the lock), and
`tests/test_a_write_between_the_read_and_the_signature_is_invisible.py`, all in DanceNitra/inspeximus
at `2e8483a` or later. The five-arm runs are
`probes/does_a_wider_change_signature_stop_the_silent_loss.linux-2cpu.result.json` (Linux, 80 rounds)
and the Windows `.result.json` at `30a734f` or later, with
`tests/test_a_reload_that_restamps_after_the_read_repeats_the_defect.py`. The CI-path arms are
`.rows-linux-2cpu.result.json` and `.rows-linux-4cpu.result.json`, and the creation race is
`probes/is_the_first_write_of_a_fresh_handle_the_one_that_goes_missing.py` with its `.linux-4cpu.result.json`
(2.27.5) and `.linux-4cpu.fixed.result.json` (2.27.6), plus
`tests/test_a_peer_creating_the_store_is_not_migrated_over.py`, all at the `v2.27.6` tag. The CI count is `gh run list --workflow tests` on that repository, the runs from 6 to 8
September ending at `6eee2de`.
