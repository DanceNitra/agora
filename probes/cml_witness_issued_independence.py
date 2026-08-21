"""Is "independently authored" a checked property of CML #304, or an assumption the caller supplies?

CONTEXT. safal207/Causal-Memory-Layer#289. #304 strengthened the per-read witness from derived
correlation to witness-issued one-shot use-time binding, and the reference shape given in the thread
reads:

    ... -> successful sys_exit_read carries consumed read_id + kernel object
        -> independently authored CML Action.READ carries the same read_id + object_id

`evaluate_witness_issued_read_token_runtime_proof` receives `ledger_record` as a PARAMETER. This asks
whether the evaluator can tell an independently authored record from one copied out of the kernel
event -- which is what a single process doing both jobs produces.

WHY WE CARE RATHER THAN JUST ASKING: we adopted the earlier layer of this thread into inspeximus
2.14.0, so we are the third party who would reuse the evaluator away from the runtime wiring that
supplies the independence.

METHOD. Their own fixture, with exactly ONE thing changed: the ledger record is built by copying
`read_id` and `object_id` straight out of the bound kernel event.

CONTROLS, so a green result cannot be an artifact of this harness:
  C0  their own 8 tests must pass at the pinned commit   (else the environment is the finding)
  C1  their unmodified fixture must PASS
  C2  a wrong ledger read_id must FAIL                   (the check can fail at all)
  C3  token reuse on the followup must FAIL              (their negative control still bites)

RUN (unauthenticated, no credentials, ~20 s):
    git clone --depth 1 https://github.com/safal207/Causal-Memory-Layer.git cml304
    cd cml304 && git fetch --depth 1 origin PINNED_SHA && git checkout PINNED_SHA
    python -m pytest tests/test_witness_issued_read_token_runtime.py -q      # C0
    python independence_probe.py                                            # C1-C3 + the question
"""
PINNED_SHA = "db6ca00a53f9b04d7c84a5d072fcc16fa3cebf57"   # merge commit of #304, named in the thread

import sys

sys.path.insert(0, ".")
from cml.integrations.witness_issued_read_token_runtime import (  # noqa: E402
    FAIL, PASS, evaluate_witness_issued_read_token_runtime_proof, kernel_object_id,
)
from cml.record import Action, Actor, CausalRecord  # noqa: E402

SCOPE = "runtime-proof"
READ_ID = "witness-read:0123456789abcdef0123456789abcdef"
DEVICE = 8 << 20 | 1
INODE = 4242
OBJECT_ID = kernel_object_id(DEVICE, INODE)


def _bound(read_id=READ_ID, ret=1, resolved=1):
    return {"fd": 3, "device": DEVICE, "inode": INODE, "return_value": ret, "started_ns": 100,
            "object_resolved": resolved, "token_present": 1 if read_id is not None else 0,
            "read_id": read_id}


def _followup(read_id=None, ret=1):
    return {"fd": 3, "device": DEVICE, "inode": INODE, "return_value": ret, "started_ns": 200,
            "object_resolved": 1, "token_present": 1 if read_id is not None else 0,
            "read_id": read_id}


def _record(read_id=READ_ID, object_id=OBJECT_ID, action=Action.READ):
    return CausalRecord.new(
        actor=Actor(pid=123, uid=1000, ppid=1, comm="proof-child"),
        action=action, object_={"fd": 3, "object_id": object_id},
        permitted_by=f"witness_token:{read_id}", read_id=read_id)


def ev(**kw):
    args = {"scope_id": SCOPE, "issued_read_id": READ_ID, "bound_event": _bound(),
            "followup_event": _followup(), "ledger_record": _record(), "token_consumed": True}
    args.update(kw)
    return evaluate_witness_issued_read_token_runtime_proof(**args)


print("CONTROLS")
c1 = ev()
print("  C1 their unmodified fixture           -> %s  %s"
      % (c1["status"], "OK" if c1["status"] == PASS else "*** ENVIRONMENT IS THE FINDING ***"))
c2 = ev(ledger_record=_record(read_id="witness-read:" + "f" * 32))
print("  C2 wrong ledger read_id               -> %s  %s"
      % (c2["status"], "OK" if c2["status"] == FAIL else "*** CHECK CANNOT FAIL ***"))
c3 = ev(followup_event=_followup(read_id=READ_ID))
print("  C3 followup reuses the token          -> %s  %s"
      % (c3["status"], "OK" if c3["status"] == FAIL else "*** NEGATIVE CONTROL DEAD ***"))

print()
print("THE QUESTION: a ledger record COPIED from the kernel event (one process doing both jobs)")
bound = _bound()
copied = _record(read_id=bound["read_id"],
                 object_id=kernel_object_id(bound["device"], bound["inode"]))
r = ev(bound_event=bound, ledger_record=copied)
print("  ledger authored by copying the witness -> %s" % r["status"])
print("  every assertion true                   : %s" % all(r["assertions"].values()))
print("  identity coverage holds                : %s" % r["identity_coverage"]["holds"])
print("  object coverage holds                  : %s" % r["object_coverage"]["holds"])
print("  reasons                                : %s" % (r["reasons"] or "(none)"))

print()
ok = (c1["status"] == PASS and c2["status"] == FAIL and c3["status"] == FAIL)
print("VERDICT: %s" % (
    ("controls hold; a copied ledger record is CERTIFIED PASS -- independence is an assumption "
     "the caller supplies, not a property this function checks")
    if ok and r["status"] == PASS else
    ("controls hold and the copied record FAILS -- independence IS checked" if ok else
     "VOID -- a control did not behave")))
