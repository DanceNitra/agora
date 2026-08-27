"""Per-forecaster calibration, measured against the only honest null: the forecaster's own marginals.

WHY THIS EXISTS. The swarm gate asks every agent for a decisive outcome inside 24 hours. That is the
right question for seven organs and the wrong one for King Aldric, whose unit of value is a Brier
score and whose verdicts mature on a horizon he chooses -- 21 to 120 days. Measured 2026-08-01 he
holds four records, all his own, none matured, so the gate reads him as producing nothing while he is
producing exactly what his organ is for. This tool measures him on his own terms, SEPARATELY from the
gate, so the question "should a long-maturation organ pass a daily bar" can be answered on numbers
rather than by moving the bar.

THE BASELINE IS THE LOAD-BEARING PART. Scoring a forecaster against 0.5, or against 1/3 for a
three-way call, flatters anyone whose calls are unbalanced: predict FLAT every time in a book that
resolves FLAT 70% of the time and you look skilled while carrying no information. The honest null is
SAME-MARGINALS INDEPENDENCE -- shuffle the forecaster's own calls against the same outcomes and ask
how often chance alone matches. This repo has already been burned the other way round: a prior
measurement of the ledger returned z = -4.79 against its own marginals, i.e. RELIABLY WORSE than
chance, which a 0.5 baseline had hidden.

Read-only. Prints a table and exits 0; it decides nothing and gates nothing.
"""
from __future__ import annotations

import json
import math
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

SERVER = Path(__file__).resolve().parents[1] / "server"
TRIALS = 20000
SEED = 20260801

#: A resolved forecast, per store: (file, id-field, author-field, call-field, outcome-field)
STORES = (
    (".predictions.json", "status", "by", "direction", "status"),
    (".oracle.json", "status", "by", "side", "outcome"),
)


def _load(name: str) -> list:
    p = SERVER / name
    if not p.exists():
        return []
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []
    return d if isinstance(d, list) else (d.get("items") or [])


def _resolved_pairs(name: str, author_f: str, call_f: str, outcome_f: str) -> dict:
    """{author: [(call, actual)]} over RESOLVED records only.

    BOTH SIDES ARE NEEDED, and the first version of this function kept only the hit boolean. That made
    the permutation below shuffle a list and sum all of it -- a control that could not move, so every
    z came out at exactly 0.00. Verified on the live book: `actual` holds the true direction (UP 81,
    FLAT 72, DOWN 59) and `direction == actual` reproduces the ledger's own `correct` count exactly
    (41 of 212), so the pairing is what skill is claimed over and the pairing is what gets destroyed.
    """
    out = defaultdict(list)
    for r in _load(name):
        if not isinstance(r, dict):
            continue
        who = str(r.get(author_f) or "unattributed").strip() or "unattributed"
        if name == ".predictions.json":
            if str(r.get("status") or "").lower() not in ("correct", "incorrect"):
                continue
            call, actual = str(r.get("direction") or "?").upper(), str(r.get("actual") or "?").upper()
            if "?" in (call, actual):
                continue
        else:
            if str(r.get("status") or "").lower() != "resolved" or r.get("outcome") is None:
                continue
            call = str(r.get("side") or "?").upper()
            actual = "YES" if float(r.get("outcome") or 0) > 0.5 else "NO"
            if call == "?":
                continue
        out[who].append((call, actual))
    return out


def _same_marginals(pairs: list, trials: int = TRIALS, seed: int = SEED) -> tuple:
    """(observed hit rate, chance hit rate, z) under SAME-MARGINALS independence.

    The forecaster's calls are permuted against the SAME multiset of outcomes. How often they said
    each thing and how often each thing happened are both preserved; only which call met which
    outcome is destroyed -- and that pairing is precisely the skill being claimed.
    """
    if len(pairs) < 5:
        return (None, None, None)
    calls = [c for c, _ in pairs]
    actuals = [a for _, a in pairs]
    obs = sum(1 for c, a in pairs if c == a) / len(pairs)
    rng = random.Random(seed)
    shuffled = list(actuals)
    tot = sq = 0.0
    for _ in range(trials):
        rng.shuffle(shuffled)
        r = sum(1 for c, a in zip(calls, shuffled) if c == a) / len(calls)
        tot += r
        sq += r * r
    mean = tot / trials
    var = max(1e-12, sq / trials - mean * mean)
    return (obs, mean, (obs - mean) / math.sqrt(var))


def _self_check() -> str:
    """THE CONTROL, run every time. A z that cannot go positive measures nothing.

    The first version of `_same_marginals` shuffled a list of hit booleans and summed all of it, so
    the permuted rate equalled the observed rate by construction and every z printed as exactly 0.00.
    It looked like a finding. It was an instrument that could not move. So this drives the statistic
    on two synthetic forecasters with the same call mix and asserts it separates them.
    """
    perfect = [("UP", "UP")] * 30 + [("FLAT", "FLAT")] * 30
    inverted = [("UP", "FLAT")] * 30 + [("FLAT", "UP")] * 30
    p_obs, p_chance, p_z = _same_marginals(perfect)
    i_obs, i_chance, i_z = _same_marginals(inverted)
    if not (p_z > 5 and i_z < -5):
        raise SystemExit("SELF-CHECK FAILED: perfect z=%.2f, inverted z=%.2f -- the statistic does "
                         "not separate a perfect forecaster from an inverted one, so every number "
                         "below is void" % (p_z, i_z))
    return ("self-check: perfect forecaster z=%+.1f, inverted z=%+.1f (both must be extreme, or the "
            "statistic is inert)" % (p_z, i_z))


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    print("FORECASTER CALIBRATION -- measured against same-marginals independence, %s"
          % time.strftime("%Y-%m-%d %H:%M"))
    print("data: %s" % SERVER)
    print("NOT a gate. Nothing here passes or fails anything; it reports what the book says.")
    print(_self_check())
    print()

    for name, _idf, author_f, call_f, outcome_f in STORES:
        recs = _load(name)
        pairs = _resolved_pairs(name, author_f, call_f, outcome_f)
        n_open = sum(1 for r in recs if isinstance(r, dict)
                     and str(r.get("status") or "").lower() in ("open", "pending"))
        print("%s -- %d records, %d unresolved" % (name, len(recs), n_open))
        if not pairs:
            print("    no resolved records with an author\n")
            continue
        print("    %-22s %6s %8s %10s %8s %s" % ("author", "n", "hit", "chance", "z", "calls"))
        for who, ps in sorted(pairs.items(), key=lambda kv: -len(kv[1])):
            obs, chance, z = _same_marginals(ps)
            mix = ", ".join("%s:%d" % (c, k) for c, k in Counter(c for c, _ in ps).most_common(3))
            if obs is None:
                print("    %-22s %6d %8s %10s %8s %s"
                      % (who[:22], len(ps), "-", "-", "too few", mix))
                continue
            print("    %-22s %6d %8.3f %10.3f %8.2f %s" % (who[:22], len(ps), obs, chance, z, mix))
        print()

    print("READING THE z COLUMN. It is the observed hit rate minus what the forecaster's OWN call mix")
    print("would score by chance, in standard deviations. Near 0 means the calls carry no information")
    print("beyond their frequencies. NEGATIVE means reliably worse than chance -- which this ledger has")
    print("measured before (z = -4.79), and which a 0.5 baseline hides completely.")
    print("\nUNRESOLVED IS NOT UNPRODUCTIVE. A forecast that has not reached its horizon is work done")
    print("and not yet scored; the count above is the honest way to see it, rather than a daily bar")
    print("that reads a months-long cycle as silence.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
