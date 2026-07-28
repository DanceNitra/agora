"""The endpoint guard existed. Why did 20 rows walk past it?

`_REFUSAL_AT_SOURCE` covers "does not support" — singular. The production text says "do not support".
"""
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\Danculus\agora\server")
from agora.api.agent_os_api import _REFUSAL_AT_SOURCE as R  # noqa: E402
from agora.execution.non_finding import is_non_finding  # noqa: E402

TESTS = [
    "The provided sources do not support the claim about deltaG(q=0.6)-deltaG(0) = 0.077 N",
    "The provided sources does not support the claim about deltaG",
    "No source supports the claim about deltaG",
    "The joint finding is that the provided sources do not support the claim about deltaG",
    'Reality: {    "answer": "The provided sources do not support the claim about deltaG"',
]
print(f"{'old endpoint guard':>22} | {'new gate':>9} | text")
for t in TESTS:
    m = R.search(t)
    old = f"MATCH {m.group(0)[:16]!r}" if m else "MISS"
    new = "reject" if is_non_finding(t) else "accept"
    print(f"{old:>22} | {new:>9} | {t[:74]}")

print("\nthe difference is one letter: the pattern has `does not (support|fit|apply)`, the text says")
print("`do not support`. Singular verb form only. Everything else in that alternation is about")
print("`no paper/source/study ...`, which this sentence never says — it names the sources it WAS given.")
