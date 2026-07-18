"""spin_velocity_bethe.py — reproducible artifact for the weak-coupling anchor pi*v_s(U=0.5)=6.02776 used in the
EDRN Menu-2 paper (Li, Drahos, Sultanov). Backs the number with a runnable computation, not an assertion.

Exact Bethe-ansatz spin velocity of the 1D half-filled Hubbard model (t=1, lattice spacing=1):

    v_s(U) = 2t * I_1(2*pi*t/U) / I_0(2*pi*t/U)          (modified Bessel-function ratio)

Limits (sanity): U->0  => I1/I0 -> 1  => v_s -> v_F = 2t = 2  (pi*v_F = 2*pi = 6.2832);
                 U->inf => v_s -> 2*pi*t^2/U = pi*J/2 with J=4t^2/U (Heisenberg spin velocity).
Ref: Essler, Frahm, Goehmann, Kluemper, Korepin, "The One-Dimensional Hubbard Model" (CUP 2005);
Lieb-Wu (1968) dressed-energy equations.
"""
import math
try:
    from scipy.special import i0, i1            # numerically stable modified Bessel I_0, I_1
    def _ratio_I1_I0(x):
        return i1(x) / i0(x)
except Exception:
    def _ratio_I1_I0(x):
        # stable series for I1/I0 via ln-space terms: I_nu = sum (x/2)^(2m+nu)/(m!(m+nu)!)
        def lnI(nu):
            terms = []
            for m in range(400):
                lt = (2 * m + nu) * math.log(x / 2.0) - math.lgamma(m + 1) - math.lgamma(m + nu + 1)
                terms.append(lt)
            mx = max(terms)
            return mx + math.log(sum(math.exp(t - mx) for t in terms))
        return math.exp(lnI(1) - lnI(0))

def v_s(U, t=1.0):
    x = 2.0 * math.pi * t / U
    return 2.0 * t * _ratio_I1_I0(x)

if __name__ == "__main__":
    for U in [0.5, 1.0, 2.0, 4.0]:
        vs = v_s(U); print(f"U={U:<4}  v_s={vs:.6f}  pi*v_s={math.pi*vs:.6f}")
    vs05 = v_s(0.5)
    print("\nweak-coupling anchor:")
    print(f"  v_s(U=0.5)    = {vs05:.7f}")
    print(f"  pi*v_s(U=0.5) = {math.pi*vs05:.6f}   (paper: 6.02776)")
    # limit checks
    print(f"  limit U->0: v_s(U=0.01) = {v_s(0.01):.5f} -> v_F=2 ; pi*v_F={2*math.pi:.5f}")
    assert abs(math.pi * vs05 - 6.02776) < 1e-3, "pi*v_s(0.5) does not match 6.02776"
    print("\nOK: pi*v_s(U=0.5) matches the paper value to <1e-3.")
