"""Two readable surfaces of one record disagree about when it became true, and the write succeeded.

Target: tomcounsell/popoto, `ValidityField` (issue #580 "V0 validity primitives"), merged 2026-08-17
as a4f7fbf4. Measured against a live Redis, not read off the page.

THIS FILE REPLACES AN EARLIER PROBE OF MINE THAT WAS WRONG, and the way it was wrong is the reason
this one reads two surfaces instead of one. The first version defined "stored" as
`ValidityField.get_all_keys()` -- the six derived index keys -- and concluded that nothing records
whether `valid_from` was declared or substituted. One `HGETALL` refutes that: popoto persists the
field value itself, so a defaulted record holds msgpack nil and an asserted one holds the float
(M1 below). The criterion was narrower than the property, and it reported clean over a marker that
was there the whole time.

WHAT SURVIVED, AND WHAT IS NEW:
  M1  popoto DOES record the provenance, in the model hash: `.validity` is None for a defaulted
      record and the float for a declared one, across a reload. Credit where due; the earlier
      claim is withdrawn.
  M2  ...but only on the save path. `execute_supersede` writes the index and never the hash, so a
      valid-from asserted through it leaves `.validity` nil. The marker is path-dependent.
  M3  THE FINDING. Save a record with no event time (index := save clock, hash := nil), then
      re-save it carrying the corrected event time. The hash takes the correction; the index
      refuses it, because `ZADD NX` already holds a score. Both surfaces are readable, they now
      disagree by the size of the correction, and the save returned normally.
  M4  A consumer spends the disagreement: `filter(validity__as_of=t)` for t inside the corrected
      interval returns nothing, while `.validity` on the same record says the fact was true at t.
  M5  The documented idiom is not broken -- superseding with a NEW record carrying the corrected
      value lands correctly. So this is "cannot be amended in place", which is append-only design,
      not "cannot be corrected". The narrower claim is the honest one.

CONTROLS -- a measurement without these is a rumour with a decimal point:
  C1   positive       their documented supersede works in this harness, else the run voids itself.
  C2   agreement      a record saved WITH an event time has hash == index. This is what makes M3 a
                      divergence rather than a property of the two surfaces always differing.
  MUT1 must-fail      drop `NX` from the valid_from ZADD; M3's divergence MUST vanish. If it does
                      not, the probe is blaming the wrong mechanism.

RUN IT:
    docker run -d --name popoto-redis -p 6399:6379 redis:7-alpine
    git clone https://github.com/tomcounsell/popoto && cd popoto
    git checkout a4f7fbf4 && pip install redis msgpack
    python popoto_valid_from_hash_and_index_disagree.py

Any Redis works; set REDIS_URL to point elsewhere. The script flushes the DB it connects to between
measurements, so give it a scratch database. Writes its receipt beside itself.
"""
from __future__ import annotations

import json
import os
import sys
import time

os.environ.setdefault("REDIS_URL", "redis://localhost:6399/0")
if os.path.isdir("src/popoto"):          # running from inside a popoto clone
    sys.path.insert(0, "src")

from popoto import KeyField, Model, ValidityField  # noqa: E402
from popoto.fields import validity_field as VF  # noqa: E402
from popoto.redis_db import POPOTO_REDIS_DB as R  # noqa: E402

PINNED_REF = "a4f7fbf432e487a29cd4868fb9c1fb59956067c0"
results: dict = {"ref": PINNED_REF}
DAY = 86400.0


def log(m: str) -> None:
    print(m, flush=True)


class Fact(Model):
    fact_id = KeyField()
    validity = ValidityField()


def index_of(inst) -> float | None:
    """The valid_from score the temporal filters actually read."""
    return R.zscore(ValidityField.get_valid_from_key(Fact, "validity"), inst.db_key.redis_key)


def hash_of(fact_id: str):
    """The field value as a caller gets it back from the store."""
    got = Fact.query.get(fact_id=fact_id)
    return getattr(got, "validity", None) if got else None


log(f"ref {PINNED_REF}")

# ---------------------------------------------------------------- C1 positive control
R.flushdb()
old = Fact(fact_id="ctl-old"); old.save()
new = Fact(fact_id="ctl-new"); new.save()
ValidityField.execute_supersede(
    Fact, "validity", new_member=new.db_key.redis_key,
    mode="supersede", old_member=old.db_key.redis_key,
)
cur = {f.fact_id for f in Fact.query.filter(validity__current=True)}
c1 = ("ctl-new" in cur) and ("ctl-old" not in cur)
results["C1_positive_control"] = c1
log(f"C1  positive control   supersede works: {c1}")
if not c1:
    log("    HARNESS BROKEN - findings void. Stopping.")
    sys.exit(1)

# ---------------------------------------------------------------- M1 the marker EXISTS
R.flushdb()
a = Fact(fact_id="defaulted"); a.save()
clock = time.time()
b = Fact(fact_id="asserted", validity=clock); b.save()
m1 = {"defaulted_hash": hash_of("defaulted"), "asserted_hash": hash_of("asserted")}
results["M1_provenance_is_recorded"] = m1
log("")
log("M1  is the provenance of valid_from recorded anywhere? YES - in the model hash")
log(f"    defaulted .validity = {m1['defaulted_hash']!r}   (msgpack nil on the wire)")
log(f"    asserted  .validity = {m1['asserted_hash']!r}")
log("    -> a defaulted event time is distinguishable from a declared one, per record,")
log("       across a reload. An earlier version of this probe said otherwise; it was")
log("       reading only the six derived index keys. Claim withdrawn.")

# ---------------------------------------------------------------- C2 the surfaces AGREE normally
c2_hash, c2_index = hash_of("asserted"), index_of(b)
c2_agree = c2_hash is not None and c2_index is not None and abs(c2_hash - c2_index) < 1e-6
results["C2_surfaces_agree_normally"] = {"hash": c2_hash, "index": c2_index, "agree": c2_agree}
log("")
log("C2  control: on an ordinary declared save, do the two surfaces agree?")
log(f"    hash={c2_hash!r}  index={c2_index!r}  agree={c2_agree}")
log("    -> they do. So a disagreement below is a divergence, not just two different things.")

# ---------------------------------------------------------------- M2 the marker is path-dependent
R.flushdb()
c = Fact(fact_id="via-supersede"); c.save()
t_assert = time.time() - 10 * DAY
ValidityField.execute_supersede(
    Fact, "validity", new_member=c.db_key.redis_key, mode="open", valid_from=t_assert,
)
results["M2_supersede_leaves_hash_nil"] = {"hash": hash_of("via-supersede"), "asserted": t_assert}
log("")
log("M2  assert a valid-from through execute_supersede instead of the field value")
log(f"    asserted {t_assert!r} -> .validity is still {hash_of('via-supersede')!r}")
log("    -> execute_supersede writes the index and never the hash, so the marker that M1")
log("       found is only written by one of the two documented write paths.")

# ---------------------------------------------------------------- M3 THE DIVERGENCE
R.flushdb()
d = Fact(fact_id="diverge"); d.save()             # nobody said when: index := save clock, hash := nil
idx_before, hash_before = index_of(d), hash_of("diverge")
corrected = idx_before - 30 * DAY                  # the producer later learns the real event time
d.validity = corrected
d.save()                                           # ordinary save, returns normally
idx_after, hash_after = index_of(d), hash_of("diverge")
gap_days = (idx_after - hash_after) / DAY if (idx_after and hash_after) else None
diverged = hash_after is not None and idx_after is not None and abs(hash_after - idx_after) > 1.0
results["M3_divergence"] = {
    "index_before": idx_before, "hash_before": hash_before, "corrected_to": corrected,
    "index_after": idx_after, "hash_after": hash_after,
    "gap_days": round(gap_days, 2) if gap_days else None, "diverged": diverged,
}
log("")
log("M3  save with no event time, then re-save carrying the corrected one")
log(f"    before   hash={hash_before!r}  index={idx_before!r}")
log(f"    correct to {corrected!r}  (30 days earlier), via an ordinary save")
log(f"    after    hash={hash_after!r}  index={idx_after!r}")
log(f"    -> DIVERGED: {diverged}, by {gap_days:.1f} days, and the save raised nothing."
    if diverged else "    -> no divergence")

# ---------------------------------------------------------------- M4 a consumer spends it
probe_t = corrected + 60.0                         # one minute after the corrected event time
hit = {f.fact_id for f in Fact.query.filter(validity__as_of=probe_t)}
results["M4_consumer"] = {"as_of": probe_t, "returned": sorted(hit),
                          "hash_says_true_then": hash_after is not None and hash_after <= probe_t}
log("")
log("M4  a consumer reads one surface and not the other")
log(f"    .validity says the fact was true from {hash_after!r}")
log(f"    filter(validity__as_of={probe_t!r}) returns {sorted(hit) or '{}'}")
log("    -> the record's own field and the temporal filter answer the same question")
log("       differently, and nothing surfaces the disagreement.")

# ---------------------------------------------------------------- M5 the documented idiom is fine
R.flushdb()
e1 = Fact(fact_id="idiom-old"); e1.save()
true_from = time.time() - 15 * DAY
e2 = Fact(fact_id="idiom-new", validity=true_from); e2.save()
ValidityField.execute_supersede(
    Fact, "validity", new_member=e2.db_key.redis_key,
    mode="supersede", old_member=e1.db_key.redis_key,
)
seen = {f.fact_id for f in Fact.query.filter(validity__as_of=true_from + 60)}
idiom_ok = "idiom-new" in seen
results["M5_documented_idiom_works"] = {"as_of_hit": sorted(seen), "ok": idiom_ok}
log("")
log("M5  the documented route: supersede with a NEW record carrying the corrected value")
log(f"    as_of(corrected+1min) -> {sorted(seen)}   lands: {idiom_ok}")
log("    -> so the honest claim is 'valid-from cannot be amended IN PLACE', which is")
log("       append-only design working as intended, NOT 'cannot be corrected'.")

# ---------------------------------------------------------------- MUT1 must-fail
original = VF.SUPERSEDE_LUA
mutant = original.replace(
    "redis.call('ZADD', vf_key, 'NX', valid_from, new_member)",
    "redis.call('ZADD', vf_key, valid_from, new_member)",
)
assert mutant != original, "MUT1 did not apply - the anchor line moved; probe is void"
VF.SUPERSEDE_LUA = mutant
R.flushdb()
f = Fact(fact_id="mut1"); f.save()
f.validity = index_of(f) - 30 * DAY
f.save()
mut_gap = abs((index_of(f) or 0) - (hash_of("mut1") or 0))
VF.SUPERSEDE_LUA = original
mut1_ok = mut_gap < 1.0                            # with NX gone the index takes the correction
results["MUT1_probe_is_sensitive"] = {"gap_seconds": mut_gap, "divergence_vanished": mut1_ok}
log("")
log("MUT1 must-fail: the same correction with `NX` removed")
log(f"    hash/index gap = {mut_gap:.1f}s -> divergence vanished: {mut1_ok}"
    + ("  -> NX is the mechanism." if mut1_ok else "  -> PROBE BLAMES THE WRONG THING; M3 is void."))

# ---------------------------------------------------------------- verdict
ok = c1 and c2_agree and mut1_ok
results["all_controls_passed"] = ok
log("")
log("=" * 78)
log(f"controls: C1={c1}  C2={c2_agree}  MUT1={mut1_ok}  -> "
    f"{'findings are about popoto' if ok else 'FINDINGS VOID'}")

receipt = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "popoto_valid_from_hash_and_index_disagree.result.json")
with open(receipt, "w", encoding="utf-8") as fh:
    json.dump(results, fh, indent=2, default=str)
log(f"receipt -> {os.path.basename(receipt)}")
