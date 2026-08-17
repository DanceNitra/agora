"""Is a DEFAULTED valid_from distinguishable from an ASSERTED one, and can it ever be repaired?

Target: tomcounsell/popoto, `ValidityField` (issue #580 "V0 validity primitives"), merged
2026-08-17 as a4f7fbf4. Measured against a live Redis, not read off the page.

WHY IT MATTERS NOW. popoto's build order (#456, 2026-08-16) says the valid-time axis is new to the
program, that M4 (#563) is its natural producer, and M1 (#560) its home. M4 is still open, and
M1's field list asks for a *nullable* bi-temporal interval. `ValidityField.__init__` does set
`null=True` -- and its docstring finishes the sentence: "a record may be saved without an explicit
valid-from, in which case save time is used." So the nullable state M1 wants is the one state
`on_save` cannot produce.

WHAT THIS SCRIPT FOUND, INCLUDING WHERE IT REFUTED ITS OWN AUTHOR:
  M1/M2/M2b  Nothing stored records whether valid_from was declared or defaulted. The one signal
             that separates them today is exact float equality between valid_from and ingested_at
             -- an artifact of on_save handing one `now` to both, not a declared contract. A batch
             caller using the supported `execute_supersede(valid_from=, ingested_at=)` form to
             assert "true as of ingest" reproduces the defaulted shape exactly. Measured, collides.
  M3         REFUTED THE HYPOTHESIS THIS SCRIPT WAS WRITTEN TO CONFIRM. `on_save` carries
             `except (TypeError, ValueError): valid_from = now`, which reads like a silent fallback
             to ingest time. It is unreachable through the ordinary save path: the model's type
             validation raises first. datetime, "2026-01-15T12:00:00" and "2026-01-15" all raise.
             popoto refuses to guess an event time, which is the correct call -- see MUT2.
  M4         A defaulted valid_from cannot be corrected through any ordinary write.
             `execute_supersede(mode="open", valid_from=<earlier>)` and a plain re-save both leave
             it unchanged and NEITHER RAISES -- the `ZADD NX` on the valid_from ZSET no-ops in
             silence. `import_state` (plain ZADD, admin path) is the only writer that can overwrite.

CONTROLS -- a measurement without these is a rumour with a decimal point:
  C0    build identity  sha256 of the file under test, so the numbers name their bytes.
  C1    positive        the documented supersede behaviour works in this harness. If it fails,
                        every finding below is void and the script says so and exits.
  MUT1  must-fail       drop `NX` from the valid_from ZADD; M4's "silently ignored" MUST flip.
                        If it does not, the probe cannot see a repairable valid_from and M4
                        measures nothing.
  MUT2  must-fail       make the swallowed TypeError strict; M3's "raises" MUST change shape.
                        This is the positive control for M3's ABSENCE claim: it proves the probe
                        would have detected a silent fallback had one been reachable.

RUN IT:
    docker run -d --name popoto-redis -p 6399:6379 redis:7-alpine
    git clone https://github.com/tomcounsell/popoto && cd popoto
    git checkout a4f7fbf4 && pip install redis msgpack
    python popoto_valid_from_is_a_default_nothing_records.py

Any Redis works; set REDIS_URL to point elsewhere. The script flushes the DB it connects to
between measurements, so give it a scratch database. Writes its receipt beside itself.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import sys
import time

os.environ.setdefault("REDIS_URL", "redis://localhost:6399/0")
if os.path.isdir("src/popoto"):          # running from inside a popoto clone
    sys.path.insert(0, "src")

import popoto  # noqa: E402,F401
from popoto import KeyField, Model, ValidityField  # noqa: E402
from popoto.fields import validity_field as VF  # noqa: E402
from popoto.redis_db import POPOTO_REDIS_DB  # noqa: E402

PINNED_REF = "a4f7fbf432e487a29cd4868fb9c1fb59956067c0"
SOURCE = "src/popoto/fields/validity_field.py"
results: dict[str, object] = {"ref": PINNED_REF}


def log(msg: str) -> None:
    print(msg, flush=True)


class Fact(Model):
    fact_id = KeyField()
    validity = ValidityField()


def state_of(inst) -> dict:
    """The record's stored interval, read back out of Redis."""
    keys = ValidityField.get_all_keys(Fact, "validity")
    m = inst.db_key.redis_key
    return {
        "valid_from": POPOTO_REDIS_DB.zscore(keys["valid_from"], m),
        "ingested_at": POPOTO_REDIS_DB.zscore(keys["ingested_at"], m),
        "invalid_at": POPOTO_REDIS_DB.zscore(keys["invalid_at"], m),
    }


def fresh(tag: str, **kw):
    """A record whose key is unique per run, so nothing collides across measurements."""
    inst = Fact(fact_id=f"{tag}-{time.time_ns()}", **kw)
    inst.save()          # returns a status, not the instance
    return inst


# ---------------------------------------------------------------- C0 build identity
if os.path.exists(SOURCE):
    with open(SOURCE, "rb") as fh:
        results["sha256"] = hashlib.sha256(fh.read()).hexdigest()
    log(f"C0  build identity   {SOURCE}")
    log(f"    sha256 {results['sha256']}")
else:
    results["sha256"] = None
    log(f"C0  build identity   {SOURCE} not on disk (installed popoto); ref only")
log(f"    ref    {PINNED_REF}")

# ---------------------------------------------------------------- C1 positive control
POPOTO_REDIS_DB.flushdb()
old, new = fresh("ctl-old"), fresh("ctl-new")
ValidityField.execute_supersede(
    Fact, "validity", new_member=new.db_key.redis_key,
    mode="supersede", old_member=old.db_key.redis_key,
)
current = {f.fact_id for f in Fact.query.filter(validity__current=True)}
c1_ok = (new.fact_id in current) and (old.fact_id not in current)
results["C1_positive_control"] = c1_ok
log(f"C1  positive control  supersede works: {c1_ok}")
if not c1_ok:
    log("    HARNESS BROKEN - every finding below is void. Stopping.")
    sys.exit(1)

# ---------------------------------------------------------------- M1/M2 is the default marked?
POPOTO_REDIS_DB.flushdb()
clock = time.time()
a = fresh("defaulted")                 # nothing asserted -> falls back to save time
b = fresh("asserted", validity=clock)  # a producer asserting "true as of now"
sa, sb = state_of(a), state_of(b)

results["M1_defaulted_state"], results["M2_asserted_state"] = sa, sb
results["M1_valid_from_equals_ingested_at"] = sa["valid_from"] == sa["ingested_at"]
log("")
log("M1  defaulted (no value passed)")
log(f"    valid_from={sa['valid_from']!r}  ingested_at={sa['ingested_at']!r}  "
    f"equal={sa['valid_from'] == sa['ingested_at']}")
log("M2  asserted valid_from == a clock the caller read just before saving")
log(f"    valid_from={sb['valid_from']!r}  ingested_at={sb['ingested_at']!r}  "
    f"equal={sb['valid_from'] == sb['ingested_at']}")
keys = ValidityField.get_all_keys(Fact, "validity")
results["stored_keys"] = sorted(keys)
log(f"    stored keys for this field: {sorted(keys)}  <- none carries the timestamp's provenance")

# M2b: the discriminator that DOES exist today is exact float equality between two
# independently-meaningful axes -- an artifact of on_save sharing one `now`, not a declared
# contract. execute_supersede takes valid_from and ingested_at as separate arguments and its own
# docstring endorses passing one clock for a batch. So a caller ASSERTING "true as of the instant
# we ingested it" reproduces the defaulted state exactly. Measure that; do not argue it.
POPOTO_REDIS_DB.flushdb()
d = fresh("m2b-defaulted")
batch_clock = time.time()
e = Fact(fact_id=f"m2b-asserted-{time.time_ns()}")
e.save()
ValidityField.execute_supersede(
    Fact, "validity", new_member=e.db_key.redis_key, mode="open",
    now=batch_clock, valid_from=batch_clock, ingested_at=batch_clock,
)
sd, se = state_of(d), state_of(e)
d_eq, e_eq = sd["valid_from"] == sd["ingested_at"], se["valid_from"] == se["ingested_at"]
results["M2b_asserted_batch_state"] = se
results["M2b_discriminator_defeated"] = d_eq and e_eq
log("")
log("M2b the coincidence discriminator, vs a batch caller asserting 'true as of ingest'")
log(f"    defaulted : valid_from==ingested_at -> {d_eq}")
log(f"    asserted  : valid_from==ingested_at -> {e_eq}")
log(f"    -> same shape: {d_eq and e_eq}. The only separator is float equality between two axes")
log("       that mean different things, and a supported call pattern reproduces it.")

# ---------------------------------------------------------------- M3 malformed assertion
POPOTO_REDIS_DB.flushdb()
cases = {
    "datetime": datetime.datetime(2026, 1, 15, 12, 0, 0),
    "iso_string": "2026-01-15T12:00:00",
    "date_string": "2026-01-15",
}
m3: dict[str, object] = {}
log("")
log("M3  a producer asserts an event time the field cannot parse")
for name, value in cases.items():
    t0 = time.time()
    try:
        st = state_of(fresh(f"malformed-{name}", validity=value))
        became_now = st["valid_from"] is not None and abs(st["valid_from"] - t0) < 5.0
        m3[name] = {"raised": None, "valid_from": st["valid_from"],
                    "silently_became_ingest_time": became_now}
        log(f"    {name:12s} NO ERROR; valid_from={st['valid_from']!r} is_ingest_time={became_now}")
    except Exception as exc:                                    # noqa: BLE001
        m3[name] = {"raised": type(exc).__name__}
        log(f"    {name:12s} raised {type(exc).__name__}  <- refuses to guess. Correct.")
results["M3_malformed"] = m3

# ---------------------------------------------------------------- M4 can it be repaired?
POPOTO_REDIS_DB.flushdb()
rec = fresh("repair")                       # opens with a defaulted valid_from
before = state_of(rec)["valid_from"]
true_from = before - 30 * 86400.0           # the producer later learns: true 30 days earlier

err = None
try:
    ValidityField.execute_supersede(
        Fact, "validity", new_member=rec.db_key.redis_key, mode="open", valid_from=true_from,
    )
except Exception as exc:                                        # noqa: BLE001
    err = f"{type(exc).__name__}: {exc}"
after = state_of(rec)["valid_from"]
rec.validity = true_from                    # and a plain re-save carrying the corrected value
rec.save()
after_save = state_of(rec)["valid_from"]

silently_ignored = (after == before) and (after_save == before) and err is None
results["M4_repair"] = {
    "before": before, "attempted": true_from, "after_supersede_open": after,
    "after_resave": after_save, "error_raised": err, "silently_ignored": silently_ignored,
}
log("")
log("M4  repair a defaulted valid_from through the ordinary write paths")
log(f"    stored before      {before!r}")
log(f"    producer asserts   {true_from!r}  (30 days earlier)")
log(f"    after mode='open'  {after!r}   error={err}")
log(f"    after plain save   {after_save!r}")
log(f"    -> silently ignored: {silently_ignored}")

# ---------------------------------------------------------------- M5 does a CONSUMER read it?
# The fair objection to everything above is "no bit was destroyed -- the caller supplied nothing,
# and ingest time is a sound upper bound, so this is an unstated bound, not fabricated data."
# That objection is answerable only by showing a consumer that reads the substituted value and
# gets an answer meaning two different things. popoto's own exclusion rule is the consumer, and
# the doc states it as a question about PROOF: "is this record provably closed or provably not
# yet started?" A defaulted valid_from answers that question with a proof nobody supplied.
POPOTO_REDIS_DB.flushdb()
t_query = time.time() - 3600.0                  # one hour ago
declared = fresh("m5-declared", validity=t_query - 60.0)   # asserted: true since 61 min ago
defaulted = fresh("m5-defaulted")                          # nobody said; gets ingest time
as_of_hit = {f.fact_id for f in Fact.query.filter(validity__as_of=t_query)}
declared_in = declared.fact_id in as_of_hit
defaulted_in = defaulted.fact_id in as_of_hit
results["M5_as_of"] = {
    "query_at": t_query, "declared_included": declared_in, "defaulted_included": defaulted_in,
}
log("")
log("M5  a consumer reads it: filter(validity__as_of=<1 hour ago>)")
log(f"    declared valid_from 61 min ago -> included: {declared_in}")
log(f"    defaulted (nobody asserted)    -> included: {defaulted_in}")
log("    -> the excluded record is excluded as 'provably not yet started'. Nothing was")
log("       proved: the exclusion rule asks for evidence and on_save manufactured it.")
log("       'we never knew when this became true' and 'this was demonstrably not true")
log("       yet' are returned as the same answer, and the caller cannot tell them apart.")

# ---------------------------------------------------------------- MUT1 must-fail: drop NX
original_lua = VF.SUPERSEDE_LUA
mutant_lua = original_lua.replace(
    "redis.call('ZADD', vf_key, 'NX', valid_from, new_member)",
    "redis.call('ZADD', vf_key, valid_from, new_member)",
)
assert mutant_lua != original_lua, "MUT1 did not apply - the anchor line moved; probe is void"
VF.SUPERSEDE_LUA = mutant_lua
POPOTO_REDIS_DB.flushdb()
rec2 = fresh("mut1")
before2 = state_of(rec2)["valid_from"]
ValidityField.execute_supersede(
    Fact, "validity", new_member=rec2.db_key.redis_key, mode="open",
    valid_from=before2 - 30 * 86400.0,
)
after2 = state_of(rec2)["valid_from"]
mut1_sensitive = after2 != before2
VF.SUPERSEDE_LUA = original_lua
results["MUT1_probe_is_sensitive"] = mut1_sensitive
log("")
log("MUT1 must-fail: the same measurement with `NX` removed")
log(f"    before={before2!r} after={after2!r}  changed={mut1_sensitive}"
    + ("  -> the probe CAN see a repairable valid_from." if mut1_sensitive
       else "  -> PROBE IS BLIND; M4 measures nothing."))

# ---------------------------------------------------------------- MUT2 must-fail: raise instead
POPOTO_REDIS_DB.flushdb()
original_on_save = ValidityField.on_save


class StrictValidityField(ValidityField):
    @classmethod
    def on_save(cls, model_instance, field_name, field_value, pipeline=None, **kwargs):
        if field_value is not None:
            float(field_value)          # the fallback the shipped code swallows
        return original_on_save.__func__(
            cls, model_instance, field_name, field_value, pipeline=pipeline, **kwargs
        )


class StrictFact(Model):
    fact_id = KeyField()
    validity = StrictValidityField()


mut2_raised = None
try:
    StrictFact(fact_id=f"mut2-{time.time_ns()}", validity="2026-01-15").save()
except Exception as exc:                                        # noqa: BLE001
    mut2_raised = type(exc).__name__
results["MUT2_probe_is_sensitive"] = mut2_raised is not None
log("")
log("MUT2 must-fail: the same malformed input with the swallowed fallback made strict")
log(f"    raised={mut2_raised}  changed={mut2_raised is not None}"
    + ("  -> the probe CAN see a rejecting field, so M3's absence claim stands."
       if mut2_raised else "  -> PROBE IS BLIND; M3 measures nothing."))

# ---------------------------------------------------------------- verdict
all_controls = c1_ok and mut1_sensitive and (mut2_raised is not None)
results["all_controls_passed"] = all_controls
log("")
log("=" * 78)
log(f"controls: C1={c1_ok}  MUT1={mut1_sensitive}  MUT2={mut2_raised is not None}  -> "
    f"{'findings are about popoto' if all_controls else 'FINDINGS VOID'}")

receipt = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "popoto_valid_from_is_a_default_nothing_records.result.json")
with open(receipt, "w", encoding="utf-8") as fh:
    json.dump(results, fh, indent=2, default=str)
log(f"receipt -> {os.path.basename(receipt)}")
