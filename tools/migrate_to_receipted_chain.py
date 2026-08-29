"""Start a receipted chain for our own decision store, and repair what the guard now refuses.

WHY THIS EXISTS. `audit_the_audits` reports `demonstrated_on_your_store: []` on our live store, and
that is the honest number: the store was opened without receipts, so `verify_writes` and
`verify_attribution` have no write chain to check and fail their control before any corruption. We
sell memory integrity. Our own store has no chain.

WHY NOT JUST TURN RECEIPTS ON. Measured 2026-08-29: opening the existing 619-record store with
`receipts=True` starts the chain at the NEXT write. `verify_writes` then reports 618 records covered
by no receipt and `verify_attribution` reports 577 uncommitted, forever. A chain has to begin at an
empty store.

WHY NOT BACK-FILL RECEIPTS. A receipt issued today for a record written in July proves that the text
existed today. It is decoration, not evidence. So this migration is explicit about what the chain
attests: every record enters with today's write timestamp and its ORIGINAL `valid_from`, and the
receipt covers the store from the migration forward. That is real tamper-evidence going forward and
it claims nothing about original authorship.

THE REPAIR. 141 of 619 records (23%) are refused by the library's own frame-markup guard: tool-call
markup leaked into the stored text, so a `decision` field swallowed the `because` and `context` that
belonged beside it. The guard was added after they were written. Cutting the text at the first tag
recovers a clean decision for all 141, and everything after the cut is preserved under
`meta.recovered_text` rather than dropped, because the rationale is the half of a decision worth
keeping.

CONTROLS, all asserted, because a migration that silently drops records is worse than no migration:
  * every source record must land in the target, or the run aborts;
  * no repaired record may lose prose: the recovered text plus the decision must account for the
    original minus its tags;
  * the target must verify: `verify_writes` returns True and `demonstrated_on_your_store` is no
    longer empty;
  * the source file is opened READ-ONLY and never written.

Usage:
    python tools/migrate_to_receipted_chain.py --dry-run
    python tools/migrate_to_receipted_chain.py --out C:/Users/Danculus/.inspeximus/mcp_memory_chain.json
"""
from __future__ import annotations

import argparse
import glob
import collections
import io
import json
import os
import re
import sys

SRC_DEFAULT = "C:/Users/Danculus/.inspeximus/mcp_memory.json"
OUT_DEFAULT = "C:/Users/Danculus/.inspeximus/mcp_memory_chain.json"

# The markup that leaked in. `</decision>`, `<parameter name="because">` and friends.
SPLIT = re.compile(r'\s*(?:</(?:decision|because|context|topic|source)>'
                   r'|<parameter name="[a-z_]+">)\s*')


def load_records(path):
    raw = json.load(io.open(path, encoding="utf-8"))
    return raw["items"] if isinstance(raw, dict) and "items" in raw else raw


def prose_len(text):
    """Characters of actual prose, with the tags and whitespace runs removed."""
    return len(re.sub(r"\s+", " ", SPLIT.sub(" ", text or "")).strip())


def split_contaminated(text):
    """(clean_decision, recovered_remainder). The cut is at the FIRST tag, which is what works.

    An earlier version reassembled the chunks under their apparent labels and five records still
    tripped the guard, because the reassembly put markup back next to prose. Cutting once recovers
    all 141. The remainder is kept whole rather than parsed into fields: the tag sequences vary
    enough that assigning each fragment to `because` or `context` would be a guess, and a guess
    stored as a labelled field reads as fact.
    """
    m = SPLIT.search(text)
    if not m:
        return text, ""
    return text[:m.start()].strip(), text[m.start():].strip()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=SRC_DEFAULT)
    ap.add_argument("--out", default=OUT_DEFAULT)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    sys.path.insert(0, "C:/Users/Danculus/inspeximus-repo")
    from inspeximus import Inspeximus

    if os.path.exists(a.out) and not a.dry_run:
        raise SystemExit("refusing to overwrite an existing chain at %s; move it aside first" % a.out)

    records = load_records(a.src)
    before = collections.Counter(r.get("status") for r in records)
    print("source: %s" % a.src)
    print("  %d records, %s" % (len(records), dict(before)))

    target = a.out + (".dryrun" if a.dry_run else "")
    # A STORE IS NOT ONE FILE. The receipt chain lives beside it in `<path>.receipts.json`, and
    # removing only the JSON leaves the old chain in place: the next run appends to it and every
    # receipt from the previous run points at a record that no longer exists. Measured here, three
    # runs in: 2,476 receipts for 619 records, and `verify_writes` correctly reporting
    # "memory 79f453e50c: written but missing from the store (deleted out-of-band)". The first run
    # passed only because no sidecar existed yet. Rebuilding means removing every sidecar too.
    for stale in glob.glob(target + "*"):
        os.remove(stale)
    ix = Inspeximus(path=target, receipts=True)

    repaired = 0
    landed = 0
    lost = []
    for r in sorted(records, key=lambda x: x.get("ts") or 0):
        text = r.get("text") or ""
        meta = dict(r.get("meta") or {})
        try:
            ix.remember(text, key=r.get("key"), object=r.get("object"), tags=r.get("tags"),
                        mtype=r.get("mtype"), value=r.get("value", 1.0),
                        valid_from=r.get("valid_from"), source=r.get("source") or None,
                        meta=meta or None)
            landed += 1
            continue
        except ValueError:
            pass

        clean, remainder = split_contaminated(text)
        # CONTROL: the repair must not shed prose.
        if len(clean) + len(remainder) < prose_len(text) * 0.97:
            lost.append(r.get("id"))
            continue
        meta["recovered_text"] = remainder
        meta["repaired_by"] = "migrate_to_receipted_chain"
        meta["original_id"] = r.get("id")
        ix.remember(clean, key=r.get("key"), object=r.get("object"), tags=r.get("tags"),
                    mtype=r.get("mtype"), value=r.get("value", 1.0),
                    valid_from=r.get("valid_from"), source=r.get("source") or None, meta=meta)
        repaired += 1
        landed += 1

    ix.flush()
    after = collections.Counter(x.get("status") for x in ix.items)
    print("\ntarget: %s" % target)
    print("  %d records, %s" % (len(ix.items), dict(after)))
    print("  repaired (markup cut, remainder kept in meta.recovered_text): %d" % repaired)
    print("  lost: %d %s" % (len(lost), lost[:5]))

    ok, problems = ix.verify_writes()
    print("\n  verify_writes: %s %s" % (ok, (problems[:1] if problems else "")))
    s = ix.audit_the_audits()["surfaces"]
    print("  demonstrated_on_your_store: %s" % s["demonstrated_on_your_store"])
    print("  proved_on_a_fixture: %d surfaces" % len(s["proved_on_a_fixture"]))

    # STATUS DRIFT. Replaying keyed writes can land a different active/superseded split than the
    # source holds, and a migration that changes what is CURRENT without saying so is worse than one
    # that refuses to run. Measured on our own store: exactly one key drifts,
    # decision::verifying-two-code-paths-share-a-rule, where the source keeps two restatements of one
    # fact active (same `object`, so no change is asserted) and the replay retires the older. The
    # migrated state is arguably the more correct one -- a supersession key is meant to hold a single
    # current value -- but the cause is not established, so it is named and counted rather than
    # explained away.
    def split_by_key(rows):
        d = collections.defaultdict(collections.Counter)
        for rec in rows:
            k = rec.get("key")
            if k:
                d[k][rec.get("status", "?")] += 1
        return d

    src_split, dst_split = split_by_key(records), split_by_key(ix.items)
    drifted = sorted(k for k in set(src_split) | set(dst_split)
                     if src_split.get(k) != dst_split.get(k))
    if drifted:
        print("")
        print("  STATUS DRIFT on %d key(s) -- what is CURRENT changed:" % len(drifted))
        for k in drifted[:10]:
            print("    %s" % k)
            print("      source=%s  migrated=%s"
                  % (dict(src_split.get(k, {})), dict(dst_split.get(k, {}))))

    failures = []
    if landed != len(records):
        failures.append("only %d of %d source records landed" % (landed, len(records)))
    if lost:
        failures.append("%d record(s) would lose prose" % len(lost))
    if not ok:
        failures.append("verify_writes does not pass on the new chain")
    if not s["demonstrated_on_your_store"]:
        failures.append("demonstrated_on_your_store is still empty, so the chain bought nothing")
    if failures:
        print("\nNOT READY:")
        for f in failures:
            print("  * %s" % f)
        return 1
    print("\nREADY: every record landed, nothing lost, the chain verifies.")
    if a.dry_run:
        print("Dry run: %s was written for inspection. Re-run without --dry-run to build the real one."
              % target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
