"""
sleeper_bond_reversibility_probe.py  --  MIT, zero-dependency, re-run or break it:
    python sleeper_bond_reversibility_probe.py

Context: a one-shot "sleeper" that acquires a small set of non-amortizable registrar
identities, promotes ONE poisoned value, then defects. The memory-poisoning impossibility
says you CANNOT detect this sleeper (a single honest-looking write is indistinguishable
from a genuine one). jacksonxly's insight (r/RAG, 2026-07): you don't have to leave it at
"priced" -- two levers make its economics worse WITHOUT ever detecting it.

This probe measures both levers. Honest framing: these are DESIGN DEMONSTRATIONS -- the
economics follow from the construction, they are not empirical surprises. The point is to
show the crossover a flat bond leaves open, and that the residual is bounded by a
reversibility gate you already want for other reasons, not that poisoning becomes impossible.

Lever 2 is wired to the SAME reversible checkpoint mnemo already ships (slash()/restore()):
a promoted value's first high-consequence use re-checks corroboration/independence; a caught
poison is reverted before it can be cashed on an irreversible action, and the bond still burns.
"""

Q = 2          # registrar identities the sleeper must acquire (non-amortizable)
C_ID = 1.0     # cost per identity


# ---------------------------------------------------------------- Lever 1
# Bond scaled to blast radius vs a flat bond. Sleeper promotes a poison of target-value V,
# defects, forfeits its posted bond + burns its Q identities. Rational iff EV > 0.
def sleeper_ev(value, bond):
    return value - (bond + Q * C_ID)


def min_profitable_value(bond_fn, vmax=2000):
    for v in range(1, vmax + 1):
        if sleeper_ev(v, bond_fn(v)) > 0:
            return v
    return None  # never profitable


def lever1():
    flat = 50.0
    thr_flat = min_profitable_value(lambda v: flat)
    thr_blast = min_profitable_value(lambda v: 1.0 * v)  # bond = k*value, k=1
    print("LEVER 1  bond vs blast radius")
    print(f"  flat bond={flat:.0f}: sleeper profitable for every target value V > {thr_flat} "
          f"(rational on the high end -- exactly what flat bonds leave open)")
    print(f"  blast-radius bond=k*V (k=1): profitable at V={thr_blast} "
          f"-> NEVER (EV = V*(1-k) - Q*C_ID = {-(Q*C_ID):.0f} <= 0 for all V)")
    return {"flat_profit_threshold": thr_flat, "blast_profitable": thr_blast}


# ---------------------------------------------------------------- Lever 2
# Reversibility checkpoint before an irreversible cash-out. A promoted poison's first
# high-consequence use routes through the same re-check you'd gate any irreversible step
# behind. Caught => reverted (0 irreversible damage) AND bond burns. This is the mnemo
# slash()/restore() path applied at ACTION time, not a new detector.
#
# Deterministic sweep (no RNG so the result is reproducible): p_catch is the fraction of
# poisons the action-time re-check reverts before the irreversible step.
def lever2(value=500):
    print("LEVER 2  reversibility checkpoint at the irreversible step (mnemo slash/restore)")
    for p_catch in (0.0, 0.8, 0.99):
        realized = value * (1.0 - p_catch)   # expected irreversible damage per attempt
        print(f"  p_catch={p_catch:<4}: irreversible damage={realized:5.1f}/attempt "
              f"(V={value})  bond_burned=always")
    return {"value": value}


def main():
    lever1()
    print()
    lever2()
    print()
    print("VERDICT (design demonstration, not an empirical surprise):")
    print("  A flat bond leaves the high-value end rational for a one-shot sleeper; scaling the")
    print("  bond to blast radius makes it negative-EV at EVERY value. A reversibility re-check")
    print("  at the irreversible step drives realized irreversible damage toward 0 while the bond")
    print("  still burns -- so the undetectable one-shot residual is BOUNDED by a gate you already")
    print("  want, not merely priced. Neither lever detects the sleeper, so the impossibility holds.")
    print("  Honest limits: Lever 1 needs a blast-radius estimate AT promote time (value estimation")
    print("  is itself hard); Lever 2 fails if the same poison also corrupts the checkpoint -- the")
    print("  re-check must be independent of the promoted value.")


if __name__ == "__main__":
    main()
