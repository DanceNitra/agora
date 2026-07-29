"""COMPLETION INTEGRITY — a task may not be closed until the artifact it owes has landed.

The root cause of the 42-day Bounty/Court and Graveyard outage was not scheduling and not the gate.
Three 'Challenge belief' tasks were queued on 2026-07-20/21, all three were marked done, and
.bounty.json's newest entry was 2026-06-17. The verdict was never posted. The work was recorded as
finished in the inbox and never arrived in the ledger, so the organ read dead while every process was
healthy and every check passed.

A warning was tried first and is not enough: `owed` shipped earlier the same day as advisory text in
the response, and the executor that ignores an advisory is the same one that closed those three tasks.
So this REFUSES the close.

The refusal has an explicit escape, because some closes legitimately produce no ledger entry -- an
editorial skip, a challenge that reached no verdict, a replication with nothing computable. The escape
is a named `skip_reason`, which turns a silent omission into a recorded decision. That is the whole
design: not "you must always produce an artifact", but "you may never omit one without saying so".

Deliberately keyed on the ledger's OWN freshness rather than on a caller-supplied artifact id. A
caller that must pass an id will pass one; a ledger that must have grown cannot be talked into it.
"""
from __future__ import annotations

import time

#: task-text prefix -> (human name of the ledger, loader, the endpoint that writes it)
_OWED = {
    "Challenge belief": (
        "the bounty ledger", "agora.execution.bounty",
        "POST /brain/belief-revise with verdict survived | revised | retired "
        "(record_challenge() silently ignores any other word)"),
    "Red-team belief": (
        "the bounty ledger", "agora.execution.bounty",
        "POST /brain/belief-revise with verdict survived | revised | retired"),
    "Judge debate": (
        "the bounty ledger", "agora.execution.bounty",
        "POST /brain/belief-revise with the judged verdict"),
    "Replicate claim": (
        "the replication ledger", "agora.execution.replication",
        "POST /brain/replication-record {claim,source,outcome,lab_id,note} with outcome "
        "REPRODUCED | FAILED | NOT_COMPUTABLE"),
    "Read paper": (
        "the library ledger", "agora.execution.library",
        "POST /brain/library-record with the arxiv_id and note path, so it is not re-read"),
}

#: How recently the ledger must have grown for the close to count as landed. Generous, because a long
#: task legitimately takes hours between its first tool call and its close.
_FRESH_S = 6 * 3600


def _newest_ts(module: str) -> float:
    try:
        mod = __import__(module, fromlist=["_load"])
        rows = mod._load()
        return max((float(r.get("ts", 0) or 0) for r in rows if isinstance(r, dict)), default=0.0)
    except Exception:
        return -1.0            # cannot read the ledger -> do not block on something we cannot see


def check_completion(task_text: str, skip_reason: str = "") -> dict:
    """Decide whether this task may be closed. Returns {ok, detail, note}.

    Fails OPEN when the ledger cannot be read: refusing a close because a store is missing would
    strand every task behind an unrelated defect, and the failure this guards against is silence,
    not a broken import.
    """
    kind = next((k for k in _OWED if task_text.startswith(k) or k in task_text[:80]), None)
    if not kind:
        return {"ok": True, "detail": "", "note": ""}
    ledger, module, how = _OWED[kind]
    if skip_reason:
        return {"ok": True, "detail": "",
                "note": f"closed WITHOUT writing {ledger} — recorded reason: {skip_reason[:200]}"}
    newest = _newest_ts(module)
    if newest < 0:
        return {"ok": True, "detail": "", "note": f"could not read {ledger}; close allowed"}
    age_h = (time.time() - newest) / 3600
    if age_h <= _FRESH_S / 3600:
        return {"ok": True, "detail": "", "note": ""}
    return {"ok": False, "note": "", "detail": (
        f"REFUSED: a '{kind}' task owes {ledger} an entry, and nothing has been written there for "
        f"{age_h:.1f}h. Either land the artifact ({how}) and close again, or close with "
        f"skip_reason='<why this produced no entry>'. Closing without either is what left "
        f"Bounty/Court and the Graveyard reading dead for 42 days while three challenge tasks sat "
        f"marked done.")}
