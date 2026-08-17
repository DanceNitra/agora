"""Run @safal207's own applicability evaluator, then ask what its 15 cases do not reach.

WHY THIS RUNS THEIR CODE INSTEAD OF DESCRIBING IT. @safal207 asked on anthropics/claude-code#34556 for
six temporal boundaries to be frozen as vendor-neutral fixtures, and separately reported already
having FRI-1/FRI-5 reference fixtures. Proposing a competing vocabulary to the person asking for a
shared one would be the wrong contribution, and asserting "your set does not cover X" from a partial
read of a repository is a negative existence claim -- the class that has bitten us before. So this
executes their evaluator at a pinned commit and reports what it does.

TARGET: safal207/Causal-Memory-Layer @ 18e3bee21cedd8249bd5634da37fb3a551d3b342
        cml/integrations/memory_applicability.py + tests/fixtures/memory_applicability_v0.1.json
        (fetched beside this file; re-fetch to re-verify)

SCOPE, stated because it bounds every claim below: this reads ONE fixture file at ONE commit. The
author reported newer FRI-1..FRI-5 fixtures that are not in this tree. Nothing here says those do not
cover these cases -- only that the 15 cases in THIS file do not, and the pinned sha makes that
checkable rather than asserted.

STRUCTURE:
  1. POSITIVE CONTROL -- replay all 15 of their cases through their evaluator. If these do not
     reproduce, the instrument is dead and every result below is void.
  2. Four boundaries from the thread, expressed in THEIR schema where it can hold them.
  3. The one that the schema structurally cannot express, and why that is the interesting one.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PIN = "18e3bee21cedd8249bd5634da37fb3a551d3b342"
RAW = "https://raw.githubusercontent.com/safal207/Causal-Memory-Layer/" + PIN + "/"

# Their code is FETCHED, not vendored. Two reasons, and the second is the one that matters:
#   1. Their repository is MIT, so copying would be permitted -- but a copy in our tree can drift
#      from theirs while still looking authoritative, and a reader checking our claim would then be
#      checking our copy of their code.
#   2. A commit ref pins a NAME. These digests pin the BYTES. If upstream ever force-pushes over the
#      sha, or a proxy serves something else, this fails loudly instead of measuring the wrong file.
WANT = {
    "cml/integrations/memory_applicability.py":
        "44af33be15cfe78d9b386fb0619ac5bc8d7d3d50587134386d80291b58bb27af",
    "tests/fixtures/memory_applicability_v0.1.json":
        "e6c4ac9b9a23d787c39223dad6ca6a75b64148fb3730972c51b99a5a3c0cfd7b",
}


def fetch_pinned(path: str) -> bytes:
    import hashlib
    import urllib.request
    local = HERE / Path(path).name
    body = local.read_bytes() if local.exists() else None
    if body is None or hashlib.sha256(body).hexdigest() != WANT[path]:
        with urllib.request.urlopen(RAW + path, timeout=30) as r:
            body = r.read()
        local.write_bytes(body)
    got = hashlib.sha256(body).hexdigest()
    if got != WANT[path]:
        raise SystemExit(
            f"REFUSED: {path} at {PIN[:12]} hashes {got[:16]}, expected {WANT[path][:16]}. "
            "The bytes are not the ones these results were measured against, so the run is void.")
    return body


for _p in WANT:
    fetch_pinned(_p)
sys.path.insert(0, str(HERE))
import memory_applicability as ma  # noqa: E402

F: list = []


def check(tag, ok, text):
    F.append((tag, ok))
    print(f"  [{'ok  ' if ok else 'FAIL'}] {tag}: {text}")


def run_case(c, now):
    src = ma.SourceObservation(**c["source"])
    return ma.evaluate_memory_applicability(
        source=src,
        stored_environment=ma.EnvironmentBinding(**c.get("stored_environment", {})),
        current_environment=ma.EnvironmentBinding(**c.get("current_environment", {})),
        now=now,
        caller_metadata=c.get("caller_metadata") or {},
    )


# ── 1. POSITIVE CONTROL ──────────────────────────────────────────────────────────────────────
fx = json.loads((HERE / "memory_applicability_v0.1.json").read_text(encoding="utf-8"))
now = datetime.fromisoformat(fx["now"].replace("Z", "+00:00")).astimezone(timezone.utc)
print(f"\nPOSITIVE CONTROL -- their {len(fx['cases'])} cases through their evaluator\n")

agree = 0
for c in fx["cases"]:
    r = run_case(c, now)
    got = r.status.value if hasattr(r.status, "value") else str(r.status)
    agree += got == c["expected_status"]
    if got != c["expected_status"]:
        print(f"    MISMATCH {c['id']}: got {got}, fixture says {c['expected_status']}")
check("their fixture reproduces against their evaluator", agree == len(fx["cases"]),
      f"{agree}/{len(fx['cases'])} statuses agree"
      + ("" if agree == len(fx["cases"]) else "  <- INSTRUMENT DEAD; nothing below is valid"))
if agree != len(fx["cases"]):
    raise SystemExit(1)

covered = {c["expected_status"] for c in fx["cases"]}
print(f"\n  statuses their 15 exercise: {', '.join(sorted(covered))}")
print(f"  environment fields bound  : {', '.join(ma.ENVIRONMENT_FIELDS)}")
print(f"  lineage states known      : {', '.join(sorted(ma.LINEAGE_STATES))}"
      if hasattr(ma, "LINEAGE_STATES") else "")

# ── 2. THE FOUR BOUNDARIES, in their schema where it holds them ──────────────────────────────
print("\nFOUR BOUNDARIES FROM THE THREAD, put through the SAME evaluator\n")

# (a) OBSERVATION FROM ANOTHER SESSION. @Stratogain measured OBSERVED_FRESH on a file the current
#     session had never read. Their schema has no session field, so the nearest expressible form
#     binds it as an environment field and asks what happens.
sess = {"source": {"locator": "file:policy.txt", "refetchable": True, "exists": True,
                   "expected_digest": "a" * 64, "observed_digest": "a" * 64},
        "stored_environment": {"repository": "org/repo", "commit_sha": "a" * 40, "actor": "session-1"},
        "current_environment": {"repository": "org/repo", "commit_sha": "a" * 40, "actor": "session-2"},
        "caller_metadata": {}}
r = run_case(sess, now)
got = r.status.value if hasattr(r.status, "value") else str(r.status)
check("(a) foreign-session observation is expressible via `actor`",
      got == "REVALIDATE",
      f"{got} {list(getattr(r, 'reasons', []) or [])} -- the digest MATCHES and it still revalidates, "
      "which is the right answer; the caveat is that `actor` means who is applying the memory, not "
      "who observed the source, so the two collapse onto one field")

# (b) DRIFT AFTER VERIFICATION vs drift generally. Their DRIFT compares expected vs observed digest
#     once. The VERIFY -> USE window is a SECOND comparison, after a verification that passed.
ver = {"source": {"locator": "file:policy.txt", "refetchable": True, "exists": True,
                  "expected_digest": "a" * 64, "observed_digest": "d" * 64},
       "stored_environment": {"repository": "org/repo", "commit_sha": "a" * 40},
       "current_environment": {"repository": "org/repo", "commit_sha": "a" * 40},
       "caller_metadata": {}}
r = run_case(ver, now)
got = r.status.value if hasattr(r.status, "value") else str(r.status)
check("(b) verify->use drift lands on the existing DRIFT status", got == "DRIFT",
      f"{got} -- correct, and it does NOT distinguish 'never verified' from 'verified, then moved'. "
      "Same status, different remedy: re-derive vs revalidate. A `verified_at`/`verified_digest` "
      "pair would separate them without a new status")

# (c) COLLECTOR LIVENESS. Not a property of one record, so a per-record evaluator cannot see it: the
#     honest test is whether a record written while the collector was dead is distinguishable from
#     one written while it was alive. Both arrive with no observation.
dead = {"source": {"locator": "file:b.txt", "refetchable": True, "exists": True,
                   "expected_digest": None, "observed_digest": None},
        "stored_environment": {"repository": "org/repo", "commit_sha": "a" * 40},
        "current_environment": {"repository": "org/repo", "commit_sha": "a" * 40},
        "caller_metadata": {}}
r = run_case(dead, now)
got = r.status.value if hasattr(r.status, "value") else str(r.status)

# PREDICTION WRONG, and the correction is the finding. I expected MATCH or REVALIDATE -- i.e. that a
# record with no observation would read as clean. It does not: it is UNRESOLVABLE, which is honest
# and better than we assumed. What UNRESOLVABLE does NOT do is separate two things with opposite
# remedies. Their own fixture has `writer-identity-is-not-refetchable-source` -> UNRESOLVABLE, a
# PERMANENT property of that anchor. A record written while the collector was dead is the same
# status and is an OUTAGE. One is nothing to fix; the other is an incident, and it ends the moment
# somebody restarts the collector. Their set already draws exactly this line between DRIFT and
# ORPHAN ("re-source, not revalidate"), so the distinction is theirs, applied one field over.
permanent = {"source": {"locator": "agent:scholar", "refetchable": False, "exists": None,
                        "expected_digest": None, "observed_digest": None},
             "stored_environment": {}, "current_environment": {}, "caller_metadata": {}}
rp = run_case(permanent, now)
gotp = rp.status.value if hasattr(rp.status, "value") else str(rp.status)
check("(c) a dead collector and a permanently unresolvable anchor share ONE status",
      got == gotp == "UNRESOLVABLE",
      f"collector-dead -> {got}; writer-identity -> {gotp}. Same verdict, opposite remedies: one is "
      "an outage that ends when somebody restarts a process, the other is a property of the anchor "
      "that never changes. This is the DRIFT/ORPHAN line they already draw, one field over -- and "
      "the liveness fact lives above the record, so it needs a store-level input "
      "(last_observation_at vs now) rather than a new status")

# (d) IDENTIFIER WRITE/QUERY EQUALITY -- the structural one.
sig = ma.evaluate_memory_applicability.__doc__ or ""
takes_a_record = "source" in str(
    __import__("inspect").signature(ma.evaluate_memory_applicability))
check("(d) the evaluator is handed an ALREADY-RESOLVED record", takes_a_record,
      "its inputs are (source, stored_environment, current_environment, now, caller_metadata) -- "
      "every one describes a record that was FOUND. A lookup that returned the wrong record, or "
      "nothing, because the identifier written was not the identifier queried cannot be posed to it "
      "at all. That is not a missing case; it is a case the shape cannot hold")

print("\n" + "=" * 96)
bad = [t for t, ok in F if not ok]
print(f"CML APPLICABILITY, PINNED 18e3bee: {len(bad)} failure(s) of {len(F)}"
      + (f"  -> {bad}" if bad else ""))
print("Their 15 reproduce exactly. Three of the four boundaries are expressible in their vocabulary")
print("and two of those three lose a distinction the remedy depends on. The fourth is not a gap in")
print("the case list -- it is upstream of the format, because every case begins after retrieval")
print("succeeded. SCOPE: one fixture file at one commit; the author reports newer FRI fixtures this")
print("does not see, and nothing here claims anything about those.")
raise SystemExit(1 if bad else 0)
