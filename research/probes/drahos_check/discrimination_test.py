"""Is 1/sqrt(1+D^2) actually DISTINGUISHED by the data, or does any smooth decreasing curve fit?

I claimed a specific analytic form on the strength of five points, and led with "six decimal places of
agreement at D=0.1". That is the weakest possible evidence dressed as the strongest: every candidate that
behaves like 1 - aD^2 at small D agrees to six decimals at D=0.1, because they all agree with EACH OTHER
there. The question is whether the LARGE-D points separate them.

Candidates, all with the same small-D behaviour to within the leading coefficient:
    1/sqrt(1+D^2)     the DM gauge factor I claimed
    1/(1+D^2)         a Lorentzian
    1 - D^2/2         the truncated expansion of the first
    exp(-D^2/2)       a Gaussian
    1/(1+D^2/2)       another rational with the same leading term
    cos(atan(D))      identical to 1/sqrt(1+D^2) -- included as a positive control on the fitter

Scored against arm A (their anisotropic model, the numbers I actually posted). If several candidates fit
within the deviation I called "a higher-order correction", the claim was pattern-matching.
"""
import sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# the numbers as POSTED, from their final_ed_scan.py at N=12
D = np.array([0.1, 0.2, 0.3, 0.5, 1.0])
measured = np.array([0.995035, 0.980711, 0.958572, 0.899303, 0.738942])

CANDIDATES = {
    "1/sqrt(1+D^2)   [claimed]": lambda d: 1 / np.sqrt(1 + d ** 2),
    "1/(1+D^2)": lambda d: 1 / (1 + d ** 2),
    "1 - D^2/2": lambda d: 1 - d ** 2 / 2,
    "exp(-D^2/2)": lambda d: np.exp(-d ** 2 / 2),
    "1/(1+D^2/2)": lambda d: 1 / (1 + d ** 2 / 2),
    "1/(1+D^2)^(1/3)": lambda d: (1 + d ** 2) ** (-1 / 3),
    "cos(atan(D))    [same fn, control]": lambda d: np.cos(np.arctan(d)),
}

print(f"{'candidate':>34} {'max |err|':>10} {'rms':>10} {'err@D=0.1':>11} {'err@D=1.0':>11}")
rows = []
for name, f in CANDIDATES.items():
    pred = f(D)
    err = measured - pred
    rows.append((float(np.max(np.abs(err))), name, float(np.sqrt(np.mean(err ** 2))),
                 float(err[0]), float(err[-1])))
for mx, name, rms, e0, e1 in sorted(rows):
    print(f"{name:>34} {mx:>10.6f} {rms:>10.6f} {e0:>11.6f} {e1:>11.6f}")

best = sorted(rows)[0]
claimed = [r for r in rows if "claimed" in r[1]][0]
print(f"\nbest fit          : {best[1].split('[')[0].strip()}  (max err {best[0]:.6f})")
print(f"the claimed form  : max err {claimed[0]:.6f}")
print(f"\nAt D=0.1 the spread ACROSS ALL candidates is "
      f"{max(f(np.array([0.1]))[0] for f in CANDIDATES.values()) - min(f(np.array([0.1]))[0] for f in CANDIDATES.values()):.6f}"
      f" -- so 'six decimals of agreement' there distinguishes nothing.")
print("The separation, if there is one, lives at D=1.0 where the candidates differ by "
      f"{max(f(np.array([1.0]))[0] for f in CANDIDATES.values()) - min(f(np.array([1.0]))[0] for f in CANDIDATES.values()):.3f}.")
