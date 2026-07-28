"""Pass 5 — the last verification-shaped surfaces: attest, symbol_status, anchor.

Same test: can it return a clean or reassuring verdict about something it never examined?
Contract printed before every probe.
"""
import inspect
import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\Danculus\inspeximus-repo")
from inspeximus import Inspeximus  # noqa: E402

OUT = []


def note(n, v, d=""):
    OUT.append((n, v))
    print(f"  >> {n}: {v}")
    if d:
        print(f"     {d}")


print("=== attest / attestation: is a BOGUS attestation caught, or carried? ===")
try:
    from inspeximus import attest, new_source_keypair
    sk, pk = new_source_keypair()
    st = Inspeximus(path=None)
    good_sig = attest("the payout wallet is 0xAAA", sk)
    mid_ok = st.remember("the payout wallet is 0xAAA", source={"doc": "treasury"},
                         attestation=(pk, good_sig))
    # a signature over DIFFERENT text, presented for this claim
    other_sig = attest("something else entirely", sk)
    mid_bad = st.remember("the payout wallet is 0xEVIL", source={"doc": "treasury"},
                          attestation=(pk, other_sig))
    g_ok = st.grade(mid_ok)
    g_bad = st.grade(mid_bad)
    print(f"  honest attestation -> grade {g_ok.get('grade')!r} attested={g_ok['evidence'].get('attested')}")
    print(f"  forged  attestation -> grade {g_bad.get('grade')!r} attested={g_bad['evidence'].get('attested')}")
    caught = not g_bad["evidence"].get("attested")
    note("attest", "OK" if caught else "DEFECT — a signature over other text counted as attestation",
         f"honest attested={g_ok['evidence'].get('attested')}, forged attested={g_bad['evidence'].get('attested')}")
except Exception as e:
    note("attest", "n/a", f"{type(e).__name__}: {str(e)[:130]}")

print("\n=== symbol_status: does 'not deprecated' differ from 'never heard of it'? ===")
try:
    from inspeximus.code_guard import deprecate_symbol, symbol_status
    print(f"  sig: {inspect.signature(symbol_status)}")
    st2 = Inspeximus(path=None)
    deprecate_symbol(st2, "old_api", "new_api", reason="renamed")
    dep = symbol_status(st2, "old_api")
    unknown = symbol_status(st2, "never_mentioned_api")
    print(f"  deprecated symbol -> {json.dumps(dep, default=str)[:150]}")
    print(f"  unknown symbol    -> {json.dumps(unknown, default=str)[:150]}")
    distinguishable = dep != unknown and (
        not isinstance(unknown, dict) or unknown.get("status") not in (None, "ok", "current"))
    note("symbol_status",
         "OK" if dep != unknown else "SUSPECT — same answer for deprecated and unknown",
         "an unknown symbol must not read as a cleared one")
except Exception as e:
    note("symbol_status", "n/a", f"{type(e).__name__}: {str(e)[:130]}")

print("\n=== anchor(): does it commit to what it claims to? ===")
try:
    st3 = Inspeximus(path=None, receipts=True)
    for i in range(4):
        st3.remember(f"fact {i}", key=f"k{i}", object=f"v{i}")
    a1 = st3.anchor()
    st3.remember("a fifth fact written after the anchor", key="k5", object="v5")
    a2 = st3.anchor()
    print(f"  anchor before: n_writes={a1.get('n_writes')} tip={str(a1.get('writes_tip'))[:16]}")
    print(f"  anchor after : n_writes={a2.get('n_writes')} tip={str(a2.get('writes_tip'))[:16]}")
    moved = a1.get("writes_tip") != a2.get("writes_tip") and a1.get("n_writes") != a2.get("n_writes")
    ok_c, _ = st3.verify_consistency(a1)
    note("anchor", "OK" if moved and ok_c else "SUSPECT",
         f"tip advances on a write={moved}; the older anchor still verifies as a prefix={ok_c}")
except Exception as e:
    note("anchor", "n/a", f"{type(e).__name__}: {str(e)[:130]}")

print("\n\n================ PASS 5 ================")
for n, v in OUT:
    print(f"  {n:16s} {v}")
