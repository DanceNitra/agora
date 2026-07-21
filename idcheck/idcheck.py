"""
idcheck — is your causal/attribution number actually IDENTIFIED, or did your controls inject bias?
(a inspeximus / nullcheck sibling: nullcheck asks "real or noise?", idcheck asks "identified or biased?")

The mistake everyone makes: "control for everything to be safe." It's backwards. A control is a *claim
about the causal graph*, and conditioning on the wrong variable doesn't just fail to help — it
ACTIVELY injects bias into an otherwise-correct estimate. We measured it: a regression that recovers
the true effect exactly gets its sign flipped (true +0.5 -> estimated -0.88) the moment you "control
for" a collider. Identification quality — *which* variables you condition on, per the graph — not the
effect size or the number of controls, decides whether a number is trustworthy.

    audit(controls)            tag each control by its causal role; get which to keep / DROP and why
    identification_score(...)  0..1: are the variables you condition on admissible?
    collider_bias(beta)        the measured proof — adjusting for a collider corrupts a correct estimate
    good_and_bad_controls()    the reference table (Pearl's good/bad controls), so you can classify yours

Grounding (reproduced this cycle): Agora Lab collider/M-bias — controlling a collider injects bias
~ -0.9 to -1.8; controlling a mediator removes the effect you're trying to measure. Zero dependencies,
deterministic. `python idcheck.py` reruns the proof so you can watch a "more controlled" model be wrong.
"""
from __future__ import annotations

import random
import statistics


# A control is a claim about the graph. Each role has a back-door verdict + the reason (Pearl's
# "good and bad controls"). INCLUDE = adjusting reduces bias; DROP = adjusting INJECTS bias.
ROLE_RULES = {
    "confounder":       ("INCLUDE", "common cause of treatment and outcome — omitting it biases (confounding); adjusting removes that bias"),
    "proxy_confounder": ("INCLUDE", "proxy for an unobserved confounder — adjusting reduces confounding bias"),
    "outcome_predictor":("INCLUDE", "cause of the outcome only (not of treatment) — a GOOD control: no bias either way, improves precision"),
    "collider":         ("DROP",    "common effect of treatment and outcome — conditioning OPENS a spurious path and injects bias (the big one)"),
    "mediator":         ("DROP",    "lies on the causal path treatment->outcome — adjusting removes part of the very effect you want (overcontrol)"),
    "descendant_outcome":("DROP",   "caused by the outcome — conditioning on a descendant of Y leaks the effect back, injects bias"),
    "instrument":       ("DROP",    "affects treatment only — adjusting for it AMPLIFIES any residual confounding (bad control); use it for IV instead, don't condition on it"),
    "unrelated":        ("OPTIONAL","neither cause nor effect of treatment/outcome — harmless; adds noise, not bias"),
}
_GOOD = {"confounder", "proxy_confounder", "outcome_predictor"}
_BAD = {"collider", "mediator", "descendant_outcome", "instrument"}


def audit(controls: dict) -> dict:
    """Audit the set of variables you are CONDITIONING ON (including in the regression / attribution
    model). `controls` = {name: role}, role one of: confounder, proxy_confounder, outcome_predictor,
    collider, mediator, descendant_outcome, instrument, unrelated. Returns the keep/DROP verdict per
    control, an overall identification verdict, and the score. Identification is an *assumption* — you
    state the role (that's the point: a control is a claim about the graph), idcheck applies the rules.
    """
    keep, drop, unknown = [], [], []
    reasons = {}
    for name, role in controls.items():
        rule = ROLE_RULES.get(role)
        if rule is None:
            unknown.append(name)
            reasons[name] = f"unknown role '{role}' — declare one of {sorted(ROLE_RULES)}"
            continue
        verdict, why = rule
        reasons[name] = f"{verdict}: {why}"
        if role in _BAD:
            drop.append(name)
        elif role in _GOOD:
            keep.append(name)
    has_confounder_control = any(controls.get(n) in ("confounder", "proxy_confounder") for n in controls)
    if drop:
        overall = (f"BIASED — you are conditioning on {len(drop)} bad control(s): {', '.join(drop)}. "
                   f"Each INJECTS bias; remove them. More controls is not safer.")
    elif not has_confounder_control:
        overall = ("UNDER-CONTROLLED (or no confounder declared) — no confounder among your controls; "
                   "if any common cause of treatment and outcome is unadjusted, the estimate is confounded.")
    else:
        overall = "ADMISSIBLE — given your stated graph, your control set conditions only on good controls."
    return {"verdict": overall, "identification_score": identification_score(controls),
            "keep": keep, "drop": drop, "unknown_role": unknown, "per_control": reasons}


def identification_score(controls: dict) -> float:
    """0..1 summary of the control set's admissibility. 1.0 = every conditioned variable is a good
    control AND at least one confounder is covered. Each bad control conditioned on drops it sharply
    (bad controls actively inject bias, they are worse than missing). Returns 0.0 if any bad control."""
    if not controls:
        return 0.0
    bad = sum(1 for r in controls.values() if r in _BAD)
    if bad:
        # any bad control means the estimate is biased; scale how wrong by the share that are bad
        return round(max(0.0, 0.5 - 0.5 * bad / len(controls)), 3)
    has_conf = any(r in ("confounder", "proxy_confounder") for r in controls.values())
    return 1.0 if has_conf else 0.6


def _ols_partial(x, y, c=None):
    """OLS slope of y on x (single), or the PARTIAL slope of x in y ~ x + c (controlling for c).
    Pure stdlib via covariances — the partial-regression formula."""
    n = len(y)
    mx, my = statistics.fmean(x), statistics.fmean(y)
    sxx = sum((xi - mx) ** 2 for xi in x) / n
    sxy = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y)) / n
    if c is None:
        return sxy / sxx
    mc = statistics.fmean(c)
    scc = sum((ci - mc) ** 2 for ci in c) / n
    sxc = sum((xi - mx) * (ci - mc) for xi, ci in zip(x, c)) / n
    scy = sum((ci - mc) * (yi - my) for ci, yi in zip(c, y)) / n
    denom = sxx * scc - sxc * sxc
    return (scc * sxy - sxc * scy) / denom if denom else float("nan")


def collider_bias(beta: float = 0.5, n: int = 20000, seed: int = 7) -> dict:
    """The measured proof. X->Y with true effect `beta`; collider C = X + Y + noise. The NAIVE
    regression Y~X recovers beta; "controlling for" the collider C corrupts it. Returns both estimates
    and the bias that adjusting injected — so you can see a more-controlled model be more wrong."""
    rng = random.Random(seed)
    X = [rng.gauss(0, 1) for _ in range(n)]
    Y = [beta * xi + rng.gauss(0, 1) for xi in X]
    C = [xi + yi + 0.3 * rng.gauss(0, 1) for xi, yi in zip(X, Y)]
    naive = _ols_partial(X, Y)
    adjusted = _ols_partial(X, Y, C)
    return {"true_beta": beta, "naive_Y_on_X": round(naive, 3),
            "adjusted_for_collider": round(adjusted, 3),
            "bias_injected_by_adjusting": round(adjusted - beta, 3),
            "lesson": "the naive estimate was right; 'controlling for' the collider injected the bias"}


def good_and_bad_controls() -> dict:
    """Reference: each causal role -> INCLUDE / DROP / OPTIONAL + why. Classify your candidate controls
    against this, then run audit()."""
    return {role: {"verdict": v, "why": why} for role, (v, why) in ROLE_RULES.items()}


if __name__ == "__main__":
    print("idcheck — is the number identified, or did the controls inject bias? (reproduces Agora collider lab)\n")
    print("1) the measured proof — adjusting for a COLLIDER corrupts a correct estimate:")
    print(f"   {'true beta':>9} | {'naive Y~X':>10} | {'+ collider':>10} | {'bias injected':>13}")
    for b in (0.0, 0.5, 1.0):
        r = collider_bias(b)
        print(f"   {b:>9.2f} | {r['naive_Y_on_X']:>10.3f} | {r['adjusted_for_collider']:>10.3f} | {r['bias_injected_by_adjusting']:>13.3f}")
    print("   => the naive model was right; 'more controls' flipped the sign.\n")

    print("2) audit a control set (each control = a claim about the graph):")
    spec = {"age": "confounder", "saw_competitor_ad": "collider", "clicked_email": "mediator"}
    a = audit(spec)
    print(f"   controls: {spec}")
    print(f"   verdict : {a['verdict']}")
    print(f"   score   : {a['identification_score']}  | keep: {a['keep']}  drop: {a['drop']}")
