"""A per-record signature attests to the records that are PRESENT. Deletion is invisible to it.

WHY THIS EXISTS. inspeximus 2.4.0 binds the tenant into each record's Ed25519 attestation, so a row
MOVED between tenants stops verifying. That was built in answer to a reviewer's point on a public
thread about multi-tenant isolation -- and the incident that started that thread was tenant-scoped
data LOSS, not relocation. Those are different failures, and it is easy to hear the first as covering
the second. This measures the difference rather than arguing about it.

WHAT IT SHOWS
  1. delete every `acme` row from a signed store  -> verify_attestations says ok=True
  2. move ONE `acme` row into `beta`              -> ok=False            [CONTROL: the verifier is alive]
  3. place an UNBOUND-signed row into a tenant    -> ok=False            [the 2.4.0 downgrade fix]
  4. the receipt chain, on the same deletion      -> ok=False, and it NAMES the vanished ids

Read (1) with (2): a green line in (1) is not a dead instrument, because the same verifier fails in
(2) on the same data. Signature for PLACEMENT, receipt chain for CARDINALITY.

RUN IT
    pip install "inspeximus>=2.4.0" cryptography
    python attestation_binds_placement_not_cardinality.py

Exit 0 with the table. The assertions fail loudly if any conclusion inverts -- including the controls,
because a run whose control stopped failing has measured nothing.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

import inspeximus
from inspeximus import Inspeximus, new_source_keypair

SK, PK = new_source_keypair()


def _rows(p: Path):
    raw = json.loads(p.read_text(encoding="utf-8"))
    return (raw["items"] if isinstance(raw, dict) and "items" in raw else raw), raw


def _write(p: Path, rows, raw):
    if isinstance(raw, dict) and "items" in raw:
        raw["items"] = rows
        p.write_text(json.dumps(raw), encoding="utf-8")
    else:
        p.write_text(json.dumps(rows), encoding="utf-8")


def _build(d: Path, receipts: bool = False) -> Path:
    d.mkdir(parents=True, exist_ok=True)
    p = d / "m.json"
    s = Inspeximus(path=str(p), embed=None, writer_key=SK, receipts=receipts)
    a, b = s.for_tenant("acme"), s.for_tenant("beta")
    for i in range(3):
        a.remember(f"acme fact {i}")
    for i in range(2):
        b.remember(f"beta fact {i}")
    s.flush()
    return p


def _attest(p: Path, receipts: bool = False):
    res = Inspeximus(path=str(p), embed=None, writer_key=SK, receipts=receipts).verify_attestations()
    return res[0], list(res[1])


def main() -> int:
    print("inspeximus %s\n" % getattr(inspeximus, "__version__", "?"))
    root = Path(tempfile.mkdtemp())

    base = root / "base"
    p = _build(base)
    rows, raw = _rows(p)
    signed = sum(1 for r in rows if r.get("attested_sig"))
    print("store: %d records, %d signed" % (len(rows), signed))
    if not signed:
        print("REFUSED: nothing is signed, so this measures nothing (is `cryptography` installed?)")
        return 2
    ok0, _ = _attest(p)
    print("  0. untouched                              -> ok=%s   [CONTROL]" % ok0)

    d1 = root / "deleted"
    shutil.copytree(base, d1)
    r1, raw1 = _rows(d1 / "m.json")
    kept = [r for r in r1 if r.get("tenant") != "acme"]
    _write(d1 / "m.json", kept, raw1)
    ok1, pr1 = _attest(d1 / "m.json")
    print("  1. every acme row DELETED (%d -> %d)        -> ok=%s, %d problem(s)"
          % (len(r1), len(kept), ok1, len(pr1)))

    d2 = root / "moved"
    shutil.copytree(base, d2)
    r2, raw2 = _rows(d2 / "m.json")
    for r in r2:
        if r.get("tenant") == "acme":
            r["tenant"] = "beta"
            break
    _write(d2 / "m.json", r2, raw2)
    ok2, pr2 = _attest(d2 / "m.json")
    print("  2. ONE acme row MOVED to beta             -> ok=%s, %d problem(s)   [CONTROL]"
          % (ok2, len(pr2)))

    d3 = root / "unbound"
    d3.mkdir()
    p3 = d3 / "u.json"
    su = Inspeximus(path=str(p3), embed=None, writer_key=SK)
    su.remember("a fact signed while the store was unbound")
    su.flush()
    r3, raw3 = _rows(p3)
    for r in r3:
        r["tenant"] = "beta"
    _write(p3, r3, raw3)
    ok3, pr3 = _attest(p3)
    print("  3. UNBOUND-signed row placed into beta    -> ok=%s, %d problem(s)" % (ok3, len(pr3)))

    d4 = root / "receipts"
    p4 = _build(d4, receipts=True)
    d5 = root / "receipts_deleted"
    shutil.copytree(d4, d5)                       # the WHOLE dir: the chain lives beside the store
    r5, raw5 = _rows(d5 / "m.json")
    gone = [r.get("id") for r in r5 if r.get("tenant") == "acme"]
    _write(d5 / "m.json", [r for r in r5 if r.get("tenant") != "acme"], raw5)
    okw, prw = Inspeximus(path=str(d5 / "m.json"), embed=None, receipts=True).verify_writes()
    prw = list(prw)
    named = [g for g in gone if g and any(str(g) in str(x) for x in prw)]
    print("  4. same deletion, RECEIPT CHAIN           -> ok=%s, %d problem(s), %d/%d ids named"
          % (okw, len(prw), len(named), len(gone)))
    if prw:
        print("       e.g. %s" % str(prw[0])[:100])

    print("\nMEASURED: attestation is blind to deletion (ok=%s) while catching relocation (ok=%s)"
          % (ok1, ok2))
    print("MEASURED: the receipt chain sees the same deletion (ok=%s) and names %d of %d rows"
          % (okw, len(named), len(gone)))
    print("\nVERDICT: signature binds PLACEMENT, receipt chain binds CARDINALITY. Neither substitutes"
          "\n         for the other, and offering the first as protection against LOSS is a category"
          "\n         error -- the row that is gone carries no failing signature.")

    assert ok0 is True, "the untouched store already fails; the instrument is broken, not the claim"
    assert ok1 is True, "deletion is now DETECTED by attestation -- this conclusion has inverted"
    assert ok2 is False, "CONTROL FAILED: relocation is no longer caught, so line 1 proves nothing"
    assert ok3 is False, "the unbound-row downgrade is open again (fixed in 2.4.0)"
    assert okw is False and named, "the receipt chain did not name the deleted rows"
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
