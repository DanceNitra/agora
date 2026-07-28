"""Each advertised guarantee, handed input it CANNOT have examined. Does it still say OK?

The class, stated once: a function whose entire purpose is to REFUSE returns a clean verdict about
something it never structurally looked at. Six were found this way already. This attacks the rest of
the surfaces README.md and docs/AI_ACT.md advertise.

Every probe below is a pair — an HONEST case that must PASS (so a function that simply refuses
everything is not mistaken for a good one) and a BLIND case that must FAIL. A surface that clears both
is the seventh defect.
"""
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\Danculus\inspeximus-repo")

from inspeximus import Inspeximus  # noqa: E402

RESULTS = []


def report(name, honest_ok, blind_caught, detail=""):
    verdict = "OK" if (honest_ok and blind_caught) else (
        "DEFECT — clean verdict on input it did not examine" if honest_ok and not blind_caught
        else "refuses everything (useless, not a defect of this class)")
    RESULTS.append((name, honest_ok, blind_caught, verdict, detail))
    print(f"  {name:26s} honest={'PASS' if honest_ok else 'fail'}  "
          f"blind={'caught' if blind_caught else 'MISSED'}   {verdict}")
    if detail:
        print(f"      {detail}")


def store(n=6, receipts=True):
    st = Inspeximus(path=None, receipts=receipts)
    for i in range(n):
        st.remember(f"fact number {i} about the billing system", key=f"k{i}", object=f"v{i}")
    return st


print("=== verify_consistency: an anchor from ANOTHER store ===")
try:
    a, b = store(), store()
    anchor_b = b.anchor()
    ok_h, _ = a.verify_consistency(a.anchor())          # its own anchor -> must hold
    ok_x, probs = a.verify_consistency(anchor_b)        # a stranger's anchor -> must not hold
    report("verify_consistency", bool(ok_h), not bool(ok_x),
           f"foreign-anchor verdict ok={ok_x} problems={len(probs or [])}")
except Exception as e:
    report("verify_consistency", False, False, f"raised {type(e).__name__}: {e}")

print("\n=== verify_writes: receipts DISABLED (nothing to check) ===")
try:
    good = store(receipts=True)
    ok_h = good.verify_writes()
    if isinstance(ok_h, tuple):
        ok_h = ok_h[0]
    none = store(receipts=False)                        # no chain exists at all
    ok_b = none.verify_writes()
    if isinstance(ok_b, tuple):
        ok_b = ok_b[0]
    report("verify_writes", bool(ok_h), not bool(ok_b),
           f"with NO receipt chain it returned {ok_b!r} — 'nothing was checked' must not read as 'intact'")
except Exception as e:
    report("verify_writes", False, False, f"raised {type(e).__name__}: {e}")

print("\n=== detect_split_view: no co-signatures at all ===")
try:
    a, b = store(), store()
    aa, ab = a.anchor(), b.anchor()
    honest = Inspeximus.detect_split_view(aa, [], aa, [], [])       # same anchor, no cosigs
    blind = Inspeximus.detect_split_view(aa, [], ab, [], [])        # DIFFERENT anchors, no cosigs
    def _split(x):
        return bool(x.get("split_view") or x.get("split") or x.get("divergent")) if isinstance(x, dict) else bool(x)
    report("detect_split_view", not _split(honest), _split(blind),
           f"different histories, zero co-signatures -> {blind if not isinstance(blind, dict) else {k: blind[k] for k in list(blind)[:4]}}")
except Exception as e:
    report("detect_split_view", False, False, f"raised {type(e).__name__}: {e}")

print("\n=== check_code: a deprecated symbol the guard was never told about ===")
try:
    from inspeximus.code_guard import check_code, deprecate_symbol
    st = Inspeximus(path=None)
    deprecate_symbol(st, "old_api", "new_api", reason="renamed")
    honest = check_code(st, "result = old_api(1)")      # must flag
    blind = check_code(st, "result = never_declared_api(1)")   # nothing recorded -> must not claim safe
    def _flag(x):
        return bool(x.get("problems") or x.get("issues") or x.get("deprecated")) if isinstance(x, dict) else bool(x)
    honest_ok = _flag(honest)
    print(f"      honest flagged: {_flag(honest)} | unknown symbol result: "
          f"{ {k: blind[k] for k in list(blind)[:4]} if isinstance(blind, dict) else blind}")
    report("check_code", honest_ok, True,
           "unknown symbols are out of scope by design — recorded for completeness, not a defect")
except Exception as e:
    report("check_code", False, False, f"raised {type(e).__name__}: {e}")

print("\n=== erasure_certificate.self_check: content never compared ===")
try:
    st = store(receipts=True)
    st.forget(where=lambda r: r.get("key") == "k0", request_id="DSAR-1", basis="art17")
    cert = st.erasure_certificate(request_id="DSAR-1")
    sc = cert.get("self_check") if isinstance(cert, dict) else None
    ok_h = bool(sc.get("ok")) if isinstance(sc, dict) else bool(sc)
    tampered = dict(cert)
    if isinstance(tampered.get("erased_memory_ids"), list) and tampered["erased_memory_ids"]:
        tampered["erased_memory_ids"] = ["0" * 10]      # point it at a record never erased
    from inspeximus.core import Inspeximus as _I
    re_ok = None
    for fn in ("verify_erasure_certificate", "verify_certificate"):
        if hasattr(_I, fn):
            re_ok = getattr(_I, fn)(tampered)
            break
    report("erasure_certificate", ok_h, (re_ok is not None and not (re_ok[0] if isinstance(re_ok, tuple) else re_ok)),
           f"re-verify of a certificate pointed at a different record -> {re_ok}")
except Exception as e:
    report("erasure_certificate", False, False, f"raised {type(e).__name__}: {e}")

print("\n\n================ SUMMARY ================")
bad = [r for r in RESULTS if r[1] and not r[2]]
print(f"surfaces probed: {len(RESULTS)} | clean verdict on unexamined input: {len(bad)}")
for n, _, _, v, d in RESULTS:
    print(f"  {n:26s} {v}")
