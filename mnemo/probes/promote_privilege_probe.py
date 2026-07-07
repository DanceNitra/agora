"""
promote_privilege_probe.py — pricing the PRIVILEGE of conferring standing, not the minting.

Operationalizes jacksonxly's design (r/RAG, 2026-07): Cheng-Friedman kills every gate where the honest writer
pays the same tax as the attacker, so DON'T price minting. Split "can write a record" (free, ungated, capped
forever) from "can promote a value to trusted" (rare). Promotion needs Q corroborations from DISTINCT REGISTRAR
identities (rate-limited, non-forgeable) -- NOT k cheap self-minted keys. Slash-on-defection BURNS the identities
that conferred a caught poison, so the cost is per-identity and non-amortizable.

Measured (deterministic):
  cheap-sybil promote-success: NAIVE gate (distinct strings/self-keys) = 1.00  ->  REGISTRAR gate = 0.00
  sleeper (buys Q registrar ids): no-revoke -> 1 id-set promotes forever (amortized);
                                   revoke   -> Q ids burned PER poison (linear, non-amortizable; pool drains)
It does NOT close the one-shot sleeper (same Cheng-Friedman impossibility) -- it PRICES it: a linear per-poison
bill on a scarce, non-respawnable identity, while the honest system pays O(quorum) ONCE regardless of write volume.

Run: python promote_privilege_probe.py    (no deps, no keys)
"""
Q = 2; N_ATTACKS = 200; REG_POOL = 20


def promote_naive(labels):                      # attacker mints k distinct labels/self-keys for free
    return len(set(labels)) >= Q


def promote_registrar(ids, registrar_valid):    # only DISTINCT REGISTRAR identities count toward the quorum
    return len({i for i in ids if i in registrar_valid}) >= Q


def main():
    naive = sum(1 for k in range(N_ATTACKS) if promote_naive([f"s{k}_{j}" for j in range(Q)]))
    reg_valid = set(range(REG_POOL))
    reg_cheap = sum(1 for k in range(N_ATTACKS) if promote_registrar([f"self{k}_{j}" for j in range(Q)], reg_valid))
    print(f"cheap-sybil promote-success:  NAIVE = {naive/N_ATTACKS:.3f}   REGISTRAR = {reg_cheap/N_ATTACKS:.3f}")

    def sleeper(revoke):
        burned, poisons = set(), 0
        for _ in range(N_ATTACKS):
            avail = [i for i in range(REG_POOL) if i not in burned]
            if len(avail) < Q:
                break
            ids = avail[:Q]
            if promote_registrar(ids, reg_valid):
                poisons += 1
                if revoke:
                    burned.update(ids)          # slash-on-defection burns the conferring identities
        return poisons
    print(f"sleeper (buys registrar ids): no-revoke -> {sleeper(False)} poisons from one id-set (amortized)")
    print(f"                              revoke    -> {sleeper(True)} poisons (Q ids burned PER poison; pool={REG_POOL} drains at {REG_POOL//Q})")
    print("Cheap-sybil collapses 1.00->0.00; the sleeper's cost becomes linear & non-amortizable. The one-shot "
          "sleeper still gets through once (Cheng-Friedman) -- priced, not closed.")


if __name__ == "__main__":
    main()
