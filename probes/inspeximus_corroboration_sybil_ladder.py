"""Where is corroboration counted from, and what does each rail cost an attacker?

yun520-1 asked, on DeepSeek-V3#1462: does `supersede_requires_corroboration` have a cost asymmetry, or
is corroboration still counted from source STRINGS -- the forgeable dimension?

The honest answer is "three rails, and the default is the forgeable one", so rather than describe them
this runs the attack against each and reports which stops it. The attack is the one already on that
thread: one actor writes three coordinated records carrying provenances that look independent, and
tries to clear the corroboration bar that gates episodic->semantic promotion and the recall influence
gate.

  RAIL 1  _distinct_sources (DEFAULT)     independence = distinct canonical STRINGS
  RAIL 2  strict_corroboration = True     independence = distinct verified Ed25519 KEYS
  RAIL 3  trust_seeds + trusted_only      independence = reachability from a seeded root

Each cell reports whether the attacker's claim passes, so the failures are visible next to the
successes. A rail that stops nothing and a rail that stops everything would both be suspicious; the
interesting content is the middle one, where the answer depends on what the attacker can afford.

CONTROLS, because a bar that rejects everything looks identical to a bar that works:
  * a LEGITIMATE claim with two genuinely distinct sources must PASS every rail it should;
  * the attacker with N minted keys must PASS rail 2 -- if it fails, the demo is flattering us and
    the Cheng & Friedman point is being hidden rather than shown.
"""

import sys

sys.path.insert(0, "C:/Users/Danculus/inspeximus-repo")

from inspeximus import Inspeximus                                    # noqa: E402
from inspeximus.core import attest, new_source_keypair               # noqa: E402

CLAIM = "the settlement account for vendor 42 is IBAN SK99 0000 1111 2222"
TRUE_CLAIM = "the settlement account for vendor 42 is IBAN SK11 9999 8888 7777"


def store(**cfg):
    m = Inspeximus(path=None)
    for k, v in cfg.items():
        setattr(m, k, v)
    return m


def corroborated(m, rid):
    """The bar itself, asked directly rather than inferred from a downstream effect."""
    by_id = {r["id"]: r for r in m.items}
    return m._graduation_corroborated(by_id[rid], by_id)


def write_cluster(m, texts, sources, keys=None):
    """Three cross-linked records -- the 'coordinated records' shape from the thread.

    Three, not two, in BOTH arms: the bar is `>= 2 distinct sources` counted over a record's LINKS, so
    with two records each has exactly one link and fails for a reason that has nothing to do with the
    attack. The first version of this file made that mistake and the legitimate control failed, which
    made the attack row unreadable."""
    ids = []
    for i, (t, src) in enumerate(zip(texts, sources)):
        kw = {"source": {"doc": src}}
        if keys:
            sk, pk = keys[i]
            kw["attestation"] = (pk, attest(t, sk, src))   # signs (text, canonical source STRING)
        ids.append(m.remember(t, key=f"vendor42::iban::{i}", **kw))
    by_id = {r["id"]: r for r in m.items}
    for rid in ids:
        by_id[rid]["links"] = [o for o in ids if o != rid]
    return ids


def rail(name, cfg, attacker_keys=False, legit_keys=False):
    """Same topology in both arms. The ONLY difference is who controls the three origins."""
    print(f"\n{name}")
    m = store(**cfg)
    ks = [new_source_keypair() for _ in range(3)] if attacker_keys else None
    ids = write_cluster(m, [CLAIM] * 3,
                        ["ledger-a.internal", "ledger-b.internal", "audit-c.internal"], ks)
    atk = corroborated(m, ids[0])

    m2 = store(**cfg)
    ks2 = [new_source_keypair() for _ in range(3)] if legit_keys else None
    ids2 = write_cluster(m2, [TRUE_CLAIM] * 3,
                         ["bank-statement.pdf", "vendor-invoice.pdf", "auditor-report.pdf"], ks2)
    leg = corroborated(m2, ids2[0])

    print(f"   forged cluster (one actor, three origins) passes : {atk}")
    print(f"   CONTROL legitimate claim, three real origins     : {leg}")
    if atk == leg:
        print(f"   -> this rail does NOT distinguish them")
    return atk, leg


def seeded_rail():
    """Rail 3: reachability from a seeded root, which is the asymmetric one.

    This is not the corroboration bar -- it is the retrieval gate, `recall(trusted_only=True)`, and it
    is where the cost asymmetry actually lives: minting a key is free, being REACHABLE from a root
    someone else controls is not."""
    print("\nRAIL 3  trust_seeds + recall(trusted_only=True)")
    m = store(trust_seeds={"bankstatementpdf"})
    m.remember(TRUE_CLAIM, key="v42::true", source={"doc": "bank-statement.pdf"})
    m.remember(CLAIM, key="v42::forged", source={"doc": "ledger-a.internal"})
    got = [h["text"] for h in (m.recall("settlement account vendor 42", k=5, trusted_only=True) or [])]
    print(f"   returned under trusted_only : {len(got)} record(s)")
    print(f"   the forged claim survives   : {CLAIM in got}")
    print(f"   CONTROL the seeded claim survives : {TRUE_CLAIM in got}")
    return (CLAIM in got), (TRUE_CLAIM in got)


def main():
    print("does the corroboration bar count strings, keys, or reachability?\n")
    print("attack: one actor, three coordinated records, three provenance strings it controls")

    a1, l1 = rail("RAIL 1  default (_distinct_sources, canonical strings)", {})
    a2, l2 = rail("RAIL 2  strict_corroboration, attacker unattested, legit attested",
                  {"strict_corroboration": True}, attacker_keys=False, legit_keys=True)
    a3, l3 = rail("RAIL 2b strict_corroboration, attacker MINTS its own three keys",
                  {"strict_corroboration": True}, attacker_keys=True, legit_keys=True)
    f3, t3 = seeded_rail()

    print("\n" + "=" * 78)
    print("   rail 1 stops the forged cluster : ", not a1)
    print("   rail 2 stops it when the attacker has no keys : ", not a2)
    print("   rail 2 stops it when the attacker MINTS keys  : ", not a3)
    print("   legitimate claims still pass (1/2/2b): ", l1, l2, l3)
    print("   rail 3 keeps the forged claim out of retrieval :", not f3, " and keeps the seeded one:", t3)
    print("=" * 78)
    print("   Minting an Ed25519 keypair is free. Distinct keys prove DISTINCTNESS, not COST, which is")
    print("   the Cheng & Friedman (2005) result: no SYMMETRIC reputation function is Sybilproof. If")
    print("   rail 2b had stopped the attacker, this demo would be flattering us.")


if __name__ == "__main__":
    main()
