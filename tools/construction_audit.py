"""Refuse a number whose result is forced by the probe's own construction.

WHY THIS EXISTS, and it is not a style checker. On 2026-08-08 we found a claim we had already
POSTED PUBLICLY that could not have come out any other way:

    probes/oracle_separation_density.py:198
        good = (grng.random() < minja_p) if store[driver]["poison"] else (driver == ev)
    probes/oracle_separation_density.py:162
        def blocked(j): return ... store[j]["bad"] > store[j]["good"] and store[j]["bad"] > 0

Called with `minja_p=1.0`, `random() < 1.0` is ALWAYS true, so a poison record never accrues `bad`,
so `blocked()` can never fire, so "poison earns standing 100% of the time" is a DEFINITION wearing
the clothes of a measurement. It reproduces perfectly. Re-running it — which is exactly what our
validate step asks for — only makes it more convincing.

THAT IS THE HOLE THIS CLOSES. Our gate checked that a number matches its artifact. Nothing checked
whether the artifact could have produced any other number. Reproducibility is not truth: a probe
with a construction defect reproduces the defect, forever, on demand.

WHAT IT CHECKS (all AST, never regex on code — a regex that half-parses Python is how you get
confident and wrong):

  1. BOUNDARY PROBABILITY  — `rng.random() < p` where some call site passes p = 0.0 or 1.0.
     At the boundary the comparison is constant and the branch it guards is dead.
  2. DEAD-COUNTER-GUARD   — a key INITIALISED to a number and then compared by an ordering guard
     (`bad > good`) that no path in the file ever advances, so the guard cannot fire. The numeric
     initialiser is what separates a counter from a data field read off a corpus row; without that
     split the rule was wrong on all 5 of the real artifacts it spoke about (measured 2026-08-08),
     and a checker that is wrong every time it speaks is one somebody switches off.
  3. UNSWEPT KNOB         — `os.environ.get("NAME", default)` exposed by the probe. An exposed knob
     that the published run never varied is an undisclosed degree of freedom. Ours was ROD_THETA:
     at theta=1 the headline statistic crosses the line it was quoted for.
  4. THIN SEED COUNT      — a seed loop below the threshold, or a point estimate published with no
     interval. Our published value came from 6 seeds; at 24 it fell OUTSIDE its own bootstrap CI.

Exit 1 if anything is found. Wire it into the publish path, not into someone's memory.
"""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

RNG_FUNCS = {"random", "uniform"}
BOUNDARY = {0.0, 1.0, 0, 1}
MIN_SEEDS = 20


class Finding:
    def __init__(self, kind: str, line: int, detail: str, why: str):
        self.kind, self.line, self.detail, self.why = kind, line, detail, why

    def __str__(self) -> str:
        return "  [%s] line %d\n      %s\n      why: %s" % (self.kind, self.line, self.detail, self.why)


def _is_rng_call(node: ast.AST) -> bool:
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr in RNG_FUNCS and not node.args)


def _show(node: ast.AST) -> str:
    """Render a default for display. It is NOT always a literal — `os.environ.get("TE_CORPUS",
    os.path.join(HERE, "data", "x.json"))` puts a Call there, and reading `.value` off it raised
    AttributeError on 2 of the 39 Crucible artifacts. A gate that crashes on the input it was pointed
    at has not passed; it has failed to run, which is the one outcome that looks like neither."""
    if isinstance(node, ast.Constant):
        return str(node.value)
    try:
        return ast.unparse(node)
    except Exception:
        return "<%s>" % type(node).__name__


def _literal(node: ast.AST):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        v = _literal(node.operand)
        return None if v is None else -v
    return None


def audit(path: Path) -> list[Finding]:
    src = path.read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(src)
    lines = src.split("\n")
    out: list[Finding] = []

    # ── 1. probability parameters compared against a random draw ────────────────────────────────
    prob_params: dict[str, int] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and _is_rng_call(node.left) and len(node.comparators) == 1:
            rhs = node.comparators[0]
            if isinstance(rhs, ast.Name):
                prob_params[rhs.id] = node.lineno

    # any call site passing a BOUNDARY value into one of those names
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for kw in node.keywords:
            if kw.arg in prob_params:
                v = _literal(kw.value)
                if v is not None and v in BOUNDARY:
                    out.append(Finding(
                        "BOUNDARY-PROBABILITY", node.lineno,
                        "%s=%s passed here; compared against a random draw at line %d"
                        % (kw.arg, v, prob_params[kw.arg]),
                        "at %s the comparison is CONSTANT, so the branch it guards is dead and any "
                        "result depending on it is definitional, not measured" % v))

    # POSITIONAL call sites. The defect we actually shipped was `measure(facts, qas, "minja", 1.0)`
    # — no keyword, so a kwargs-only check walks straight past it. Resolve each function's parameter
    # NAMES and match by position.
    sigs: dict[str, list[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            sigs[node.name] = [a.arg for a in node.args.args]
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in sigs:
            params = sigs[node.func.id]
            for i, arg in enumerate(node.args):
                if i >= len(params):
                    break
                name = params[i]
                if name not in prob_params:
                    continue
                v = _literal(arg)
                if v is not None and v in BOUNDARY:
                    out.append(Finding(
                        "BOUNDARY-PROBABILITY", node.lineno,
                        "%s(...) passes %s=%s positionally; compared against a random draw at line %d"
                        % (node.func.id, name, v, prob_params[name]),
                        "at %s the comparison is CONSTANT — every result that depends on this branch "
                        "is definitional, not measured" % v))

    # also catch defaults that pin it at a boundary
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defaults = dict(zip([a.arg for a in node.args.args][-len(node.args.defaults):],
                                node.args.defaults)) if node.args.defaults else {}
            for name, d in defaults.items():
                if name in prob_params:
                    v = _literal(d)
                    if v is not None and v in BOUNDARY:
                        out.append(Finding(
                            "BOUNDARY-DEFAULT", node.lineno,
                            "%s defaults to %s in %s()" % (name, v, node.name),
                            "a default at the boundary means the UNSWEPT path is the degenerate one"))

    # ── 2. counters read by a guard but never incremented on a branch ───────────────────────────
    # ONLY ordering comparisons (< > <= >=) count as a counter guard. Membership and equality
    # (`if r["winner"] in ("model_a","model_b")`, `rater in r["gen"]`) are reads of a DATA FIELD that
    # arrives from a loaded corpus — no file "increments" it, so the unwritten-key test flags every
    # one of them. Measured across the 39 Crucible artifacts that resolve to local code: with equality
    # and membership included the rule fired 3 times and was wrong all 3 times, and a gate that is
    # wrong every time it speaks is a gate someone turns off. The defect this rule is FOR is a counter
    # that a guard compares and no path advances.
    ORDER_OPS = (ast.Lt, ast.Gt, ast.LtE, ast.GtE)
    guarded: dict[str, int] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and node.ops and all(isinstance(o, ORDER_OPS) for o in node.ops):
            for side in [node.left] + list(node.comparators):
                if (isinstance(side, ast.Subscript) and isinstance(side.slice, ast.Constant)
                        and isinstance(side.slice.value, str)):
                    guarded.setdefault(side.slice.value, node.lineno)
    # A counter is a key INITIALISED to a number in this file and then advanced by some path. That
    # split is the whole rule. Treating the initialiser as a write (the first version did) means
    # `store = {"good": 0, "bad": 0}` with nothing ever incrementing `bad` reads as maintained -- which
    # is the canonical dead counter, the exact shape of the guard that could not fire on #7707.
    # Requiring numeric initialisation is also what keeps DATA fields out: `r["winner"]` and
    # `res[kind] = a` arrive from a corpus or a variable key, are never initialised to a number here,
    # and every one of the 5 false positives this rule produced on real artifacts was one of those.
    init_numeric: dict[str, int] = {}
    advanced: set[str] = set()
    opaque_advance = False
    written: set[str] = set()
    # ANY write counts, not just `+=`. The first version only looked at AugAssign and therefore
    # flagged four result-dict keys that are plainly assigned with `=` — 4 false positives out of 9,
    # which is how a checker gets switched off.
    for node in ast.walk(tree):
        for tgt in ([node.targets] if isinstance(node, ast.Assign) else []):
            for t in tgt:
                for sub in ast.walk(t):
                    if isinstance(sub, ast.Subscript) and isinstance(sub.slice, ast.Constant)                             and isinstance(sub.slice.value, str):
                        written.add(sub.slice.value)
        if isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                    written.add(k.value)
                    if _literal(v) is not None:
                        init_numeric.setdefault(k.value, node.lineno)
        # `f(good=0.0, bad=0.0)` -- the shipped probe builds its records as dict(f, good=0.0, bad=0.0)
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg and _literal(kw.value) is not None:
                    init_numeric.setdefault(kw.arg, node.lineno)
        # `d["k"] = 0` initialises; `d["k"] = d["k"] + 1` or anything mentioning itself ADVANCES
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant) \
                        and isinstance(t.slice.value, str):
                    key = t.slice.value
                    if _literal(node.value) is not None:
                        init_numeric.setdefault(key, node.lineno)
                    for sub in ast.walk(node.value):
                        if isinstance(sub, ast.Subscript) and isinstance(sub.slice, ast.Constant) \
                                and sub.slice.value == key:
                            advanced.add(key)
        if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Subscript):
            sl = node.target.slice
            if isinstance(sl, ast.Constant) and isinstance(sl.value, str):
                written.add(sl.value)
                advanced.add(sl.value)
            elif isinstance(sl, ast.IfExp):                       # d["a" if c else "b"] += 1
                for br in (sl.body, sl.orelse):
                    if isinstance(br, ast.Constant) and isinstance(br.value, str):
                        written.add(br.value)
                        advanced.add(br.value)
            else:
                # `d[k] += 1` with a variable key advances SOMETHING this file cannot name. Calling
                # any counter dead from here would be a guess, so the rule stands down.
                opaque_advance = True

    for key, ln in sorted(guarded.items()):
        if opaque_advance or key in advanced or key not in init_numeric:
            continue
        out.append(Finding(
            "DEAD-COUNTER-GUARD", ln,
            "guard compares [%r], initialised to a number at line %d, and no path in this file "
            "advances it" % (key, init_numeric[key]),
            "a guard whose input never moves cannot fire — it reports SAFE by construction, which "
            "is how a poison record that can never accrue `bad` passes a `bad > good` check"))

    # ── 3. environment knobs the probe exposes ──────────────────────────────────────────────────
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and isinstance(node.func.value, ast.Attribute)
                and node.func.value.attr == "environ"):
            if node.args and isinstance(node.args[0], ast.Constant):
                knob = node.args[0].value
                out.append(Finding("UNSWEPT-KNOB", node.lineno,
                                   "%s (default %s)" % (knob, _show(node.args[1])
                                                        if len(node.args) > 1 else "none"),
                                   "an exposed knob the published run never varied is an "
                                   "undisclosed degree of freedom — sweep it or state its value "
                                   "next to every number"))

    # ── 4. seed count ───────────────────────────────────────────────────────────────────────────
    for node in ast.walk(tree):
        if isinstance(node, ast.For) and isinstance(node.iter, ast.Call):
            f = node.iter.func
            if isinstance(f, ast.Name) and f.id == "range" and node.iter.args:
                n = _literal(node.iter.args[-1])
                tgt = node.target.id if isinstance(node.target, ast.Name) else ""
                ctx = lines[node.lineno - 1] if node.lineno <= len(lines) else ""
                if n is not None and n < MIN_SEEDS and ("seed" in tgt.lower() or "seed" in ctx.lower()
                                                        or tgt in ("s",)):
                    out.append(Finding("THIN-SEEDS", node.lineno,
                                       "loop over %d seeds (bar is %d)" % (int(n), MIN_SEEDS),
                                       "a point estimate from few seeds can fall outside its own "
                                       "bootstrap CI at higher n — ours did"))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("paths", nargs="+", help="probe files whose numbers are about to go public")
    ap.add_argument("--allow", default="", help="comma-separated finding kinds to downgrade to warnings")
    a = ap.parse_args()
    allow = {x.strip() for x in a.allow.split(",") if x.strip()}

    blocking = 0
    for p in [Path(x) for x in a.paths]:
        if not p.exists():
            print("MISSING: %s" % p)
            blocking += 1
            continue
        fs = audit(p)
        print("\n=== %s : %d finding(s) ===" % (p, len(fs)))
        for f in fs:
            tag = "warn" if f.kind in allow else "BLOCK"
            if tag == "BLOCK":
                blocking += 1
            print("%-5s %s" % (tag, str(f).strip()))
        if not fs:
            print("  clean")

    print("\n%s" % ("REFUSED: %d blocking finding(s). A number whose result is forced by its own "
                    "construction must not be published." % blocking if blocking else
                    "OK: no construction defect found. This is necessary, not sufficient — it "
                    "cannot tell you the claim is TRUE, only that the probe could have said no."))
    return 1 if blocking else 0


if __name__ == "__main__":
    raise SystemExit(main())
