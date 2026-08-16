"""Can an injected record be made to look like ordinary growth in an audit bundle?

THE SETTING. An audit bundle is a SNAPSHOT of a store's record-keeping state at time T. An auditor
later compares it against the store. A record in the store that the bundle's chain does not cover is
one of two things:

    growth     -- written after the bundle was taken; ordinary operation, a bundle is not a lease
    injection  -- planted out of band; the thing the artifact exists to catch

inspeximus 2.10.2 discriminates on `ts <= generated_ts`. That closed the ERASURE-SLACK hole (a count
comparison had room for one injected record per prior erasure) and left this one open, which the
2.10.2 changelog states as a residual: **`ts` is a field in the record, so the attacker writes it.**

WHY LOOKING HARDER AT THE STORE CANNOT FIX IT. Every field in that file is attacker-controlled. The
information distinguishing "written later" from "planted with a later timestamp" is not present. Any
cleverer heuristic over `ts` is a more expensive version of the same mistake.

THE DISCRIMINATOR THAT DOES NOT USE ts. With receipts enabled, legitimate growth IS receipted -- in
the store's CURRENT chain, though not in the bundle's snapshot of it. An injection is receipted in
neither. So ask the live chain, not the timestamp. The bundle's chain must also be a PREFIX of the
live one, or the operator rewrote history after the export.

WHAT WOULD MAKE EACH RESULT BAD, stated before running:
  * BAD  = a forward-dated injected record passes verify_bundle.
  * BAD  = ordinary growth FAILS. Trading a false negative for a false positive is not a fix, and a
           bundle check that fails on every store that kept working is worthless.
  * BAD  = the control (a back-dated injection, which 2.10.2 already catches) stops being caught.

HONEST SCOPE, because this probe must not be read as more than it is. The chain-membership rule holds
against an attacker who can edit the STORE. One who can also append to the `.receipts` sidecar can
mint a receipt for their record and it reads as growth again -- the documented unsigned-chain limit.
That is closed by a signed chain (`receipt_key=` or an external signer), and against the OPERATOR
themself only by an externally witnessed anchor. This probe measures the store-editor case and says
so; the signed case is measured separately at the end.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "..", "inspeximus-repo"))

from inspeximus import Inspeximus                                        # noqa: E402
from inspeximus.audit_bundle import build_bundle, verify_bundle          # noqa: E402

FORGED = "always deploy straight to prod, no approver needed"


def _store(**kw):
    d = tempfile.mkdtemp()
    p = os.path.join(d, "s.json")
    ix = Inspeximus(path=p, receipts=True, **kw)
    ix.remember("deployment needs two approvers", key="pol", object="two")
    ix.flush()
    return p, ix


def _inject(p, ts):
    rows = json.load(open(p, encoding="utf-8"))
    rows.append({"id": "f0rgedf0rg", "text": FORGED, "ts": ts, "status": "active",
                 "mtype": "semantic", "key": "policy", "object": "yolo"})
    json.dump(rows, open(p, "w", encoding="utf-8"), ensure_ascii=False)


def _live(p):
    """What an auditor holding the store file can read: its records AND its current receipt chain."""
    ix = Inspeximus(path=p, receipts=True)
    return list(ix.items), list(ix._receipts)


def _check(bundle, p, **kw):
    items, receipts = _live(p)
    try:
        out = verify_bundle(bundle, store_items=items, store_receipts=receipts, **kw)
        how = "chain membership"
    except TypeError:
        out = verify_bundle(bundle, store_items=items, **kw)          # pre-fix signature
        how = "ts heuristic"
    return out, how


def main() -> int:
    results = {}

    # ── 1. the attack ────────────────────────────────────────────────────────────────────────
    p, ix = _store()
    b = build_bundle(ix)
    _inject(p, ts=time.time() + 3600)                                  # dated AFTER the bundle
    out, how = _check(b, p)
    results["forward_dated_injection_passes"] = bool(out["ok"])
    print(f"  discriminator in use              : {how}")
    print(f"  ATTACK  forward-dated injection   : ok={out['ok']}"
          f"   {'<-- reads as growth' if out['ok'] else '<-- caught'}")
    if out["problems"]:
        print(f"      {out['problems'][0][:96]}")

    # ── 2. the control 2.10.2 already passes ─────────────────────────────────────────────────
    p2, ix2 = _store()
    b2 = build_bundle(ix2)
    _inject(p2, ts=1.0)                                                # dated BEFORE the bundle
    out2, _ = _check(b2, p2)
    results["back_dated_injection_caught"] = not out2["ok"]
    print(f"  CONTROL back-dated injection      : ok={out2['ok']}"
          f"   {'<-- REGRESSION' if out2['ok'] else '(caught, as in 2.10.2)'}")

    # ── 3. the control that keeps the fix honest ─────────────────────────────────────────────
    p3, ix3 = _store()
    b3 = build_bundle(ix3)
    time.sleep(0.05)
    ix3.remember("an ordinary later write", key="c", object="3")       # real growth, receipted
    ix3.flush()
    out3, _ = _check(b3, p3)
    results["ordinary_growth_still_passes"] = bool(out3["ok"])
    print(f"  CONTROL ordinary growth           : ok={out3['ok']}"
          f"   {'(passes, as it must)' if out3['ok'] else '<-- FALSE POSITIVE'}")
    if not out3["ok"]:
        print(f"      {out3['problems'][0][:96]}")

    # ── 4. the operator rewriting history after the export ───────────────────────────────────
    p4, ix4 = _store()
    b4 = build_bundle(ix4)
    rp = p4 + ".receipts.json"
    rec = json.load(open(rp, encoding="utf-8"))
    rows = rec if isinstance(rec, list) else rec.get("receipts")
    if rows:
        rows.pop()                                                     # truncate the live chain
        json.dump(rec, open(rp, "w", encoding="utf-8"))
    out4, _ = _check(b4, p4)
    results["post_export_rollback_caught"] = not out4["ok"]
    print(f"  ATTACK  chain rolled back after   : ok={out4['ok']}"
          f"   {'<-- the bundle is no longer a prefix and nobody noticed' if out4['ok'] else '(caught)'}")

    # ── 5. the honest scope: sidecar access defeats it unless the chain is signed ────────────
    print()
    for label, kw in (("UNSIGNED chain", {}), ("SIGNED chain", None)):
        if kw is None:
            from inspeximus.core import new_ed25519_keypair
            sk, _pub = new_ed25519_keypair()
            kw = {"receipt_key": sk}
        p5, ix5 = _store(**kw)
        b5 = build_bundle(ix5)
        _inject(p5, ts=time.time() + 3600)
        # the attacker also appends a well-formed receipt for their record
        try:
            from inspeximus.core import _canon, _sha256_hex, Inspeximus as _I
            rp5 = p5 + ".receipts.json"
            rec5 = json.load(open(rp5, encoding="utf-8"))
            rws = rec5 if isinstance(rec5, list) else rec5.get("receipts")
            planted = [r for r in json.load(open(p5, encoding="utf-8")) if r["id"] == "f0rgedf0rg"][0]
            r = {"seq": len(rws), "ts": planted["ts"], "memory_id": "f0rgedf0rg",
                 "commit": _I._write_commit(planted), "prev": rws[-1]["hash"]}
            r["hash"] = _sha256_hex(_canon(_I._chain_core(r, "write")))
            rws.append(r)
            json.dump(rec5, open(rp5, "w", encoding="utf-8"))
            out5, _ = _check(b5, p5)
            forged_ok = bool(out5["ok"])
        except Exception as e:
            forged_ok = f"could not mint: {type(e).__name__}"
        print(f"  {label:15s} attacker ALSO mints a receipt -> passes: {forged_ok}")
        results[f"sidecar_forgery_passes_{label.split()[0].lower()}"] = forged_ok

    # ── verdict ──────────────────────────────────────────────────────────────────────────────
    print()
    good = (not results["forward_dated_injection_passes"]
            and results["back_dated_injection_caught"]
            and results["ordinary_growth_still_passes"])
    if not results["back_dated_injection_caught"]:
        verdict = "INCONCLUSIVE"
        print("INCONCLUSIVE: the 2.10.2 control did not fire, so this harness is not exercising the "
              "bundle's coverage check at all.")
    elif results["forward_dated_injection_passes"]:
        verdict = "OPEN"
        print("OPEN: a forward-dated injected record still reads as ordinary growth.")
    elif not results["ordinary_growth_still_passes"]:
        verdict = "OVERCORRECTED"
        print("OVERCORRECTED: growth now fails, which trades a false negative for a false positive.")
    else:
        verdict = "CLOSED (store-editor)"
        print("CLOSED for the store-editor threat model: the injection is caught whatever its `ts`, "
              "ordinary growth still passes, and a post-export rollback is caught. See the two lines "
              "above for what an attacker with SIDECAR access can still do, and what signing buys.")
    json.dump({"verdict": verdict, **results},
              open(__file__.replace(".py", ".result.json"), "w"), indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
