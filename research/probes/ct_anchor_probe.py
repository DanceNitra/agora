"""Does an external, Certificate-Transparency-style anchor catch an operator who rewrites history?

`verify_writes` answers "is this log internally consistent". It cannot answer "is this the same log
you saw last time", because an operator who controls the store can rebuild a different history that
is *also* internally consistent. `anchor()` plus `verify_consistency()` is the RFC 6962 answer: an
untrusted log, an external witness holding a prior anchor, and a consistency check against it.

Three arms, each paired with a case that must NOT fire, so a green run cannot mean the check is
simply inert:

  1. append-only extension          -> verify_consistency PASSES   (a witnessed prefix still holds)
  2. a SUBSTITUTED history that is internally valid
                                    -> verify_writes still OK, verify_consistency FAILS (fork)
  3. rollback (fewer writes than the anchor saw)
                                    -> verify_consistency FAILS (the log shrank)

REWRITTEN 2026-08-23, and the reason is the point. The previous version imported `_sha256_hex`,
`_canon` and `_GENESIS` to forge a re-chained history by hand. All three are private, all three were
removed by inspeximus 2.20.0, and the probe had not been runnable since -- it died at import, so it
had been reporting nothing at all rather than reporting a failure. Arm 2 now performs the same
attack with the PUBLIC API only: the substituted history is built by the library itself, which is
both more honest (a real operator would do exactly that) and cannot rot when an internal helper is
renamed. Nothing here touches a private name.

Run: python research/probes/ct_anchor_probe.py    (deterministic, no LLM, no network)
Part of Agora / inspeximus (MIT).
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from inspeximus import Inspeximus  # noqa: E402

rows = []


def ck(ok, label, detail=""):
    rows.append((bool(ok), label, detail))
    return bool(ok)


def store(*texts):
    """A fresh receipts-enabled store holding `texts`, written entirely through the public API."""
    fd, path = tempfile.mkstemp(suffix=".json", prefix="cta_")
    os.close(fd)
    os.unlink(path)
    s = Inspeximus(path, receipts=True)
    for t in texts:
        s.remember(t)
    return s


TRUE = ("alpha is 1", "beta is 2", "gamma is 3")


def main():
    # --- arm 1: append-only extension keeps a witnessed prefix valid --------------------------
    a = store(*TRUE)
    witnessed = a.anchor()
    ok_writes, _ = a.verify_writes()
    ck(ok_writes, "the honest log verifies internally")
    a.remember("delta is 4")
    ok, why = a.verify_consistency(witnessed)
    ck(ok, "1. append-only extension still matches the witnessed anchor", "; ".join(why)[:80])

    # its paired non-firing case: the anchor must also hold against ITSELF, or the check is
    # rejecting everything and arm 2 proves nothing.
    ok, why = a.verify_consistency(a.anchor())
    ck(ok, "   control: a fresh anchor of the same log verifies against itself", "; ".join(why)[:80])

    # --- arm 2: a substituted history that is internally valid ---------------------------------
    # The operator does not forge anything. They rebuild the store with different content, through
    # the same library, so the internal chain is genuinely correct. This is the case verify_writes
    # cannot see, and the whole reason an EXTERNAL anchor exists.
    forged = store("alpha is 999", "beta is 2", "gamma is 3")
    ok_writes, _ = forged.verify_writes()
    ck(ok_writes, "2a. the substituted log verifies INTERNALLY (verify_writes cannot see the swap)")
    ok, why = forged.verify_consistency(witnessed)
    ck(not ok, "2b. but it FAILS against the externally witnessed anchor", "; ".join(why)[:80])

    # --- arm 3: rollback ------------------------------------------------------------------------
    rolled = store(*TRUE[:1])
    ok, why = rolled.verify_consistency(witnessed)
    ck(not ok, "3. a rolled-back log FAILS against the anchor", "; ".join(why)[:80])

    # --- the instrument must be able to fire AND to stay quiet -----------------------------------
    fired = [r for r in rows if r[1].startswith(("2b", "3"))]
    quiet = [r for r in rows if r[1].startswith(("1", "   control"))]
    ck(all(o for o, _, _ in fired) and all(o for o, _, _ in quiet),
       "the check both fires on a fork and stays quiet on an honest extension")

    print("== an external anchor catches what an internal chain cannot ==")
    for ok, label, detail in rows:
        print(f"  {'PASS' if ok else 'FAIL'}  {label}{('   [' + detail + ']') if detail else ''}")
    bad = sum(1 for o, _, _ in rows if not o)
    print(f"\n  {len(rows)} checks, {bad} failed")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
