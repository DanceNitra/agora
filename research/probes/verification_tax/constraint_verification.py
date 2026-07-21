"""Direction A firm-up — the decisive control: is the verification tax governed by task CHECKABILITY or by task
DIFFICULTY? Prior result: self-verify catches ~1/3 of errors on HARD reasoning (MMLU/multi-hop) but 100% on
arithmetic. Confound: arithmetic is also EASY. This test breaks the confound with a HARD-TO-SOLVE but
EASY-TO-CHECK task: constraint-satisfaction ('find a 3-digit number with digit-sum S, divisible by D, parity P').
An LLM must SEARCH to solve it (high first-pass error), but every constraint is MECHANICALLY checkable, so a
self-verifier that actually checks should catch nearly all errors. PREDICTION (checkability governs the tax):
catch on hard-but-checkable >> catch on hard-uncheckable (~0.33), residual -> ~0. FALSIFIER: if catch here is
no higher than ~0.33, the tax is about difficulty, not checkability, and the productivity claim is wrong.
Worker + self-verifier both qwen3-coder:30b (local, cloud-free). Reuses verification_tax.chat/SYS_W/SYS_V."""
import os, re, sys, json, random
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verification_tax as vt

rng = random.Random(13)
N_PROB = 40


def gen_problem():
    """Pick a target, derive constraints it satisfies; any number meeting ALL constraints is a valid answer."""
    while True:
        target = rng.randint(100, 999)
        s = sum(int(c) for c in str(target))
        divs = [d for d in [3, 7, 9, 11, 13] if target % d == 0]
        if not divs:
            continue
        d = rng.choice(divs)
        p = target % 2
        cons = {"digit_sum": s, "div": d, "parity": p}
        text = (f"Find a 3-digit integer N (100-999) such that: the sum of its digits is {s}; "
                f"N is divisible by {d}; and N is {'even' if p == 0 else 'odd'}. "
                f"There is at least one such number.")
        return text, cons


def check(n, cons):
    if not (100 <= n <= 999):
        return False
    if sum(int(c) for c in str(n)) != cons["digit_sum"]:
        return False
    if n % cons["div"] != 0:
        return False
    if n % 2 != cons["parity"]:
        return False
    return True


def extract_int(txt):
    up = (txt or "").upper()
    seg = up.split("ANSWER:")[-1] if "ANSWER:" in up else up
    m = re.findall(r"-?\d+", seg)
    return int(m[0]) if m else None


def verdict_no(txt):
    vu = (txt or "").upper(); idx = vu.rfind("VERDICT:")
    seg = vu[idx + 8:] if idx >= 0 else vu
    return ("NO" in seg) if idx >= 0 else ("NO" in vu and "YES" not in vu)


def do(item):
    text, cons = item
    ans = vt.chat([{"role": "system", "content": vt.SYS_W},
                   {"role": "user", "content": text + "\nReply 'ANSWER: <number>'."}]).strip()
    n = extract_int(ans)
    ok = (n is not None) and check(n, cons)
    vmsg = [{"role": "system", "content": vt.SYS_V},
            {"role": "user", "content": text + f"\n\nProposed answer: N={n}\nIs it correct? "
             "Check each constraint, then end with 'VERDICT: YES' or 'VERDICT: NO'."}]
    self_no = verdict_no(vt.chat(vmsg, cap=500))
    return ok, self_no


if __name__ == "__main__":
    print("compile OK - constraint-sat: HARD to solve, EASY to check (qwen3-coder:30b worker + self-verify)", flush=True)
    items = [gen_problem() for _ in range(N_PROB)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        res = list(pool.map(do, items))
    n = len(res)
    e = 1 - sum(1 for ok, _ in res if ok) / n
    wrong = [s for ok, s in res if not ok]
    right = [s for ok, s in res if ok]
    catch = (sum(1 for s in wrong if s) / len(wrong)) if wrong else float("nan")
    fa = (sum(1 for s in right if s) / len(right)) if right else 0.0
    residual = e * (1 - (catch if catch == catch else 0))
    print(f"\n  n={n}  first-pass error e={e:.2f}  (it IS hard to solve)", flush=True)
    print(f"  self-verify CATCH (NO on wrong) = {catch:.2f}   false-alarm = {fa:.2f}   residual = {residual:.3f}", flush=True)
    print("\n=== VERDICT (checkability vs difficulty) ===", flush=True)
    print(f"  hard-but-CHECKABLE catch = {catch:.2f}   vs   hard-UNCHECKABLE catch ~0.33 (MMLU/multi-hop, prior labs)", flush=True)
    if catch == catch and catch >= 0.6:
        print(f"  CONFIRMED: the verification tax is governed by CHECKABILITY, not difficulty. This task is HARD to solve "
              f"(first-pass error {e:.2f}) yet self-verification catches {catch:.0%} of errors (residual {residual:.2f}~0), "
              f"because the answer is MECHANICALLY checkable — vs only ~33% on equally/less-hard but UN-checkable reasoning. "
              f"So AI task-speedups convert to trustworthy output wherever the OUTPUT is cheaply checkable, regardless of how "
              f"hard it was to produce; the irreducible verification tax lives only on un-checkable open-ended work.", flush=True)
    elif catch == catch and catch >= 0.45:
        print(f"  PARTIAL: catch {catch:.2f} higher than the ~0.33 uncheckable baseline but not near 1.0 — checkability helps "
              f"but the model doesn't fully exploit it (it doesn't reliably re-check each constraint).", flush=True)
    else:
        print(f"  FALSIFIED-ish: catch {catch:.2f} not above the ~0.33 uncheckable baseline — the tax tracks DIFFICULTY, not "
              f"checkability; the productivity prediction (gains survive on checkable work) would not hold for this model.", flush=True)
    print("DONE", flush=True)
