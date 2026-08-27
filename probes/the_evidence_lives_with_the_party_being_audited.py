"""A witness refused. Who can find that out, if the operator does not want them to?

WHAT 2.10.3 SHIPPED. `build_bundle(witnesses=[...])` asks each witness to co-sign the anchor, and a
witness that REFUSES has its reason recorded in the bundle as `witness_refusals`, which fails
verification. An honest witness refuses only a fork or a rollback, so that is the loudest signal in
the artifact -- it came from outside it.

THE STRUCTURAL PROBLEM, which no number of checks inside the artifact can fix: the artifact is built
by the party being audited. Measured below -- the operator deletes the refusals, reseals the
(advisory, self-computed) bundle hash, and an auditor who does not already hold the witness allowlist
sees an ordinary SELF-CERTIFIED bundle with no hint that three witnesses said no.

So the question is not "is the refusal recorded" but "can a third party ASK". Today they cannot: a
Witness has `last_head()`, an unsigned local dict read, and keeps no record of what it refused. Its
knowledge is real and unreachable.

WHAT IS MEASURED, and what would make each answer bad:
  1. The operator strips the refusals and reseals.
     BAD = an auditor without the allowlist gets a clean verdict.        (expected: it does)
  2. The auditor holds the allowlist and demands co-signatures.
     BAD = the strip works anyway.                                       (expected: caught)
  3. The witness is asked directly for a signed statement.
     BAD = there is no such surface, so "ask a third party" is advice with nothing behind it.
  4. SILENCE. The operator rewrites history and simply stops submitting heads.
     BAD = indistinguishable from an idle store, i.e. an attack whose cost is doing nothing.

CONTROL, so a green line means something: an honest export must remain co-signed and verifiable
throughout, or the harness is measuring a broken witness rather than a hidden refusal.
"""
from __future__ import annotations

import copy
import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "..", "inspeximus-repo"))

from inspeximus import Inspeximus                                            # noqa: E402
from inspeximus.audit_bundle import _bundle_hash, build_bundle, verify_bundle  # noqa: E402
from inspeximus.core import new_ed25519_keypair                             # noqa: E402
from inspeximus.witness_pool import Witness                                 # noqa: E402

SK, _PUB = new_ed25519_keypair()
STORE_ID = "prod"


def _scene():
    """An honest store witnessed at T, then rebuilt by an operator who holds the receipt key."""
    d = tempfile.mkdtemp()
    ws = [Witness(state_path=os.path.join(d, f"w{i}.json")) for i in range(3)]

    def store(sub, policy):
        os.makedirs(os.path.join(d, sub), exist_ok=True)
        ix = Inspeximus(path=os.path.join(d, sub, "s.json"), receipts=True, receipt_key=SK)
        ix.remember(f"deployment needs {policy}", key="pol", object=policy.split()[0])
        ix.remember("the deploy key rotates every 90 days", key="rot", object="90d")
        ix.flush()
        return ix

    honest = store("a", "two approvers")
    build_bundle(honest, witnesses=ws, store_id=STORE_ID)          # witnessed at T
    forged = store("b", "ONE approver")
    return d, ws, [w.public for w in ws], honest, forged


def _reseal(b):
    b.pop("bundle_hash", None)
    b["bundle_hash"] = _bundle_hash(b)
    return b


def main() -> int:
    out = {}
    d, ws, pks, honest, forged = _scene()

    b = build_bundle(forged, witnesses=ws, store_id=STORE_ID)
    out["refusals_recorded"] = len(b["anchor"].get("witness_refusals") or [])
    print(f"  the operator exports over the REWRITTEN store")
    print(f"    witnesses refused          : {out['refusals_recorded']}")
    print(f"    verify (allowlist held)    : {verify_bundle(b, witnesses=pks, threshold=2)['ok']}")

    stripped = copy.deepcopy(b)
    stripped["anchor"].pop("witness_refusals", None)
    _reseal(stripped)
    with_list = verify_bundle(stripped, witnesses=pks, threshold=2)
    without = verify_bundle(stripped)
    out["strip_caught_with_allowlist"] = not with_list["ok"]
    out["strip_passes_without_allowlist"] = bool(without["ok"])
    print(f"\n  ... refusals DELETED and the bundle resealed")
    print(f"    auditor WITH the allowlist : ok={with_list['ok']}"
          f"  {'(caught)' if not with_list['ok'] else '<-- hidden'}")
    print(f"    auditor WITHOUT it         : ok={without['ok']}"
          f"  {'<-- reads as an ordinary self-certified bundle' if without['ok'] else ''}")

    print(f"\n  can a third party ASK the witness?")
    w = ws[0]
    head = w.last_head(STORE_ID) or {}
    out["witness_has_signed_statement"] = hasattr(w, "attest")
    out["witness_has_refusal_log"] = hasattr(w, "refusals")
    print(f"    it knows the honest head   : {bool(head.get('writes_tip'))}")
    print(f"    signed statement surface   : {out['witness_has_signed_statement']}"
          f"{'  <-- nothing to ask' if not out['witness_has_signed_statement'] else ''}")
    print(f"    durable refusal record     : {out['witness_has_refusal_log']}"
          f"{'  <-- the refusal lives only in the operator-built artifact'
             if not out['witness_has_refusal_log'] else ''}")

    print(f"\n  SILENCE: the operator rewrites and simply stops submitting heads")
    since = time.time() - (w.last_head(STORE_ID) or {}).get("ts", time.time())
    out["staleness_visible"] = bool((w.last_head(STORE_ID) or {}).get("ts"))
    print(f"    witness records WHEN it last saw this store : {out['staleness_visible']}"
          f"{'  <-- an idle store and an abandoned one look alike' if not out['staleness_visible'] else ''}")

    print(f"\n  CONTROL: an honest export is still co-signed and verifiable")
    honest.remember("a third honest record", key="c", object="3")
    honest.flush()
    hb = build_bundle(honest, witnesses=ws, store_id=STORE_ID)
    ctl = verify_bundle(hb, witnesses=pks, threshold=2)
    out["honest_export_ok"] = bool(ctl["ok"]) and len(hb["anchor"].get("cosignatures") or []) == 3
    print(f"    cosignatures {len(hb['anchor'].get('cosignatures') or [])}/3, verify ok={ctl['ok']}"
          f"  {'' if out['honest_export_ok'] else '<-- the harness is measuring a broken witness'}")

    print()
    if not out["honest_export_ok"]:
        verdict = "INCONCLUSIVE"
        print("INCONCLUSIVE: the control failed, so nothing above is about hiding a refusal.")
    elif out["witness_has_signed_statement"] and out["witness_has_refusal_log"]:
        verdict = "ASKABLE"
        print("ASKABLE: a third party can get the witness's own signed account, so the evidence no")
        print("longer lives only with the party being audited.")
    else:
        verdict = "OPERATOR-HELD"
        print("OPERATOR-HELD: the refusal is real, the witness knows, and there is no way to ask it.")
        print("Every path to that knowledge runs through an artifact the audited party builds, and")
        print("stripping it costs one line. The fix is not another check inside the bundle.")
    json.dump({"verdict": verdict, **out},
              open(__file__.replace(".py", ".result.json"), "w"), indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
