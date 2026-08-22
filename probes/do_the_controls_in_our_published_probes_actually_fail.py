"""Mutate what each published probe measures, and check its own verdict notices.

WHY THIS EXISTS. On 2026-08-22 I found the same defect twice inside my own files, both times only
because an adversarial reader looked:

    w_neg = 0.0                       # printed as "manifold width = 0.0e+00", nothing computed
    width  = b - a                    # honest arithmetic, but at deg=1 it is zero by construction

Both printed a reassuring number that no input could have changed. That is the defect every probe in
this repo was written to catch, sitting in the probes. So this sweeps the class instead of waiting
for the third instance: for each published probe, MUTATE the code it measures with and check whether
its own verdict changes. A control that survives every mutation is not guarding anything.

WHAT A MUTANT IS. Source-level, one edit at a time, applied through `tokenize` so comments and string
literals are never touched: a comparison flipped (`>` to `<`, `==` to `!=`), a numeric literal
doubled, `True` to `False`, `and` to `or`. Mutants are taken in token order, not sampled, so the run
is reproducible.

WHAT COUNTS AS CAUGHT, AND THE FIRST ANSWER WAS WRONG. Each mutant lands in one of four buckets:

    GUARDED    an AssertionError fired, or the PASS/FAIL words the probe prints changed.
               This, and only this, is a control doing its job.
    CRASHED    the interpreter fell over -- TypeError, ValueError -- on mutated arithmetic.
               Nothing caught anything; the code simply broke.
    UNNOTICED  the probe printed different numbers and reported exactly the same thing.
    INERT      nothing moved at all: an equivalent mutant, or a line not on the executed path.

The first version of this file counted ANY change of exit status as caught and labelled four probes
GATE, "it asserts something, and the assertion is live". That sentence was false and it was published
before it was checked. Measured afterwards over 96 mutants on these 8 files: 28 of the 31 exit changes
were CRASHES, 6 were an AssertionError (all in one file) and 3 were a verdict flip. A crash is not a
gate. Correcting it moved the result from "GATE 4, REPORT-ONLY 1" to GATE 1, REPORT-ONLY 7.

A REPORT-ONLY VERDICT IS NOT AN ACCUSATION. Seven of our eight published probes compute numbers and
print them; they assert nothing and exit 0 whatever they find. That is what our posts actually claim
for them -- they are described as "runnable", "every number is re-runnable", "re-run it or break it",
never as tests that pass -- and those descriptions were checked against the published prose. The
finding is not that the prose overclaims. It is that a runnable receipt and a check that can fail are
two different things, and only one of the eight is the second kind.

CONTROLS, both required, because a harness that reports everything broken is indistinguishable from a
broken harness:
  * POSITIVE  a fixture with a REAL control -- it asserts a computed value against a threshold --
    must score high. If it does not, the mutation engine is not reaching live code.
  * NEGATIVE  a fixture carrying my exact bug -- a control assigned from a literal `0.0` and printed
    as a measurement -- must score LOW and its control line must show up as surviving. If that
    fixture scores high, this file cannot detect the thing it was built for.
If either control lands wrong the sweep refuses to print a table.

Parallel by default: mutants run in a process pool over all cores. Serial needs a reason.
Standard library only. No LLM calls, no GPU, no network except fetching the probes themselves.

Run:  python probes/do_the_controls_in_our_published_probes_actually_fail.py [--limit N] [FILE ...]
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import tokenize
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
TIMEOUT = 150
DEFAULT_LIMIT = 12
VERDICT_RE = re.compile(r"\b(PASS|FAIL|OK|GREEN|RED|REPRODUCED|NOT_COMPUTABLE|KILLED|SURVIVED|"
                        r"CONFIRMED|REFUTED|UNVERIFIABLE|VOID)\b")

EXC_RE = re.compile(r"^(\w*Error|\w*Exception|SystemExit)\b", re.M)

NUM_RE = re.compile(r"-?\d+\.?\d*(?:[eE][-+]?\d+)?")

FLIP = {">": "<", "<": ">", ">=": "<=", "<=": ">=", "==": "!=", "!=": "=="}


def mutants(src, limit):
    """One edit per mutant, via tokenize so comments and strings are never touched."""
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except Exception:                                              # noqa: BLE001
        return []
    sites = []
    for i, t in enumerate(toks):
        if t.type == tokenize.OP and t.string in FLIP:
            sites.append((i, t.string, FLIP[t.string]))
        elif t.type == tokenize.NUMBER:
            try:
                v = float(t.string)
            except ValueError:
                continue
            # 0.0 is NOT skipped. A control assigned a literal `0.0` and printed as a
            # measurement is the exact defect this file exists for, so it has to be mutable;
            # the first version skipped it and its own negative control went undetected.
            sites.append((i, t.string, repr(v * 2 if v else 1.0)))
        elif t.type == tokenize.NAME and t.string in ("True", "False"):
            sites.append((i, t.string, "False" if t.string == "True" else "True"))
        elif t.type == tokenize.NAME and t.string in ("and", "or"):
            sites.append((i, t.string, "or" if t.string == "and" else "and"))
    out = []
    step = max(1, len(sites) // limit) if len(sites) > limit else 1
    for idx, was, now in sites[::step][:limit]:
        new = list(toks)
        t = new[idx]
        new[idx] = tokenize.TokenInfo(t.type, now, t.start, t.end, t.line)
        try:
            code = tokenize.untokenize(new)
        except Exception:                                          # noqa: BLE001
            continue
        out.append((("line %d: %s -> %s" % (t.start[0], was, now)), code))
    return out


def signature(workdir, name):
    try:
        p = subprocess.run([sys.executable, name], cwd=workdir, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return dict(verdict=("timeout", ()), numeric=(0, 0), asserted=False, crashed=False)
    out = (p.stdout or "") + (p.stderr or "")
    # The signature must include what the probe actually reports. The first version used the exit
    # code plus verdict words only, and every published probe here returned base=(0, ()) -- they
    # print numbers, not the word PASS. A harness blind to the output cannot kill any mutant, and
    # would have reported a confident 0% for perfectly sound probes.
    nums = tuple(NUM_RE.findall(out))
    # TWO signatures, deliberately separate, and keeping them separate is the whole point.
    #   verdict  = exit code + PASS/FAIL words. This is what a GATE asserts.
    #   numeric  = what the probe printed. This only tells us the mutant CHANGED something, i.e.
    #              that it is not an equivalent mutant on dead code.
    # An earlier version folded the numbers into one signature and called any difference a KILL.
    # That is wrong: a mutant that shifts a printed number while the probe still exits 0 has not
    # been caught by anything -- it is precisely the uncaught case. Its own negative control
    # (a literal `0.0` printed as a measurement) scored 100% under that definition, which is how
    # the mistake surfaced.
    # hashlib, NOT the builtin hash(): hash() is salted per interpreter, and these signatures are
    # computed inside separate pool workers, so the same output would have compared UNEQUAL across
    # processes and every mutant would have looked killed. Caught by a shell error, not by a test.
    digest = hashlib.sha256("|".join(nums).encode()).hexdigest()[:16]
    exc = EXC_RE.findall(out)
    return dict(verdict=(p.returncode, tuple(sorted(VERDICT_RE.findall(out)))),
                numeric=(digest, len(nums)),
                asserted="AssertionError" in exc,
                crashed=bool(exc) and "AssertionError" not in exc)


def _run_one(args):
    name, code, label, deps = args
    d = tempfile.mkdtemp(prefix="m_")
    with open(os.path.join(d, name), "w", encoding="utf-8") as fh:
        fh.write(code)
    for dn, dsrc in deps:
        dp = os.path.join(d, dn)
        os.makedirs(os.path.dirname(dp), exist_ok=True)
        with open(dp, "w", encoding="utf-8") as fh:
            fh.write(dsrc)
    return label, signature(d, name)


def score_probe(name, src, deps, limit, pool):
    base = _run_one((name, src, "BASE", deps))[1]
    ms = mutants(src, limit)
    if not ms:
        return dict(name=name, base=list(base), n=0, killed=0, survived=[], note="no mutable sites")
    jobs = [(name, code, label, deps) for label, code in ms]
    # CORRECTED. The first version counted any change of exit status as "caught" and called the
    # probe a GATE. Measured afterwards: across 96 mutants on these 8 files, 28 of the 31 exit
    # changes were the INTERPRETER FALLING OVER on mutated arithmetic -- TypeError, ValueError --
    # which no control noticed and which says nothing about whether the probe asserts anything.
    # Only 6 were an AssertionError and 3 a change in the PASS/FAIL words. A crash is not a gate.
    guarded, crashed, unnoticed, inert = 0, 0, [], 0
    for label, sig in pool.map(_run_one, jobs):
        moved_verdict = sig["verdict"][1] != base["verdict"][1]
        if sig["asserted"] or moved_verdict:
            guarded += 1                     # an assertion fired, or the stated verdict changed
        elif sig["crashed"]:
            crashed += 1                     # the interpreter fell over; nothing caught anything
        elif sig["numeric"] != base["numeric"]:
            unnoticed.append(label)          # measured something different and said nothing
        else:
            inert += 1                       # equivalent mutant / dead code -- not evidence
    live = guarded + crashed + len(unnoticed)
    return dict(name=name, base=[list(base["verdict"][1]), base["verdict"][0]], n=len(ms),
                guarded=guarded, crashed=crashed, caught=guarded, unnoticed=unnoticed, inert=inert,
                # A RATIO, not "caught at least one". The negative fixture -- a control assigned a
                # literal 0.0 -- caught exactly one mutant (the one that flipped its exit) and let
                # five through including `0.0 -> 1.0`, and a boolean rule labelled it a GATE. What
                # separates a real gate from a decorative one is what FRACTION of live changes its
                # verdict notices: the positive fixture 6/6, the negative 1/6.
                kind=("INERT" if not live else
                      "GATE" if guarded / live >= 0.5 else
                      "WEAK-GATE" if guarded else "REPORT-ONLY"))


POS_FIXTURE = '''
import sys
vals = [1.0, 2.0, 3.0, 4.0]
mean = sum(vals) / len(vals)
spread = max(vals) - min(vals)
ok = spread > 1.0 and mean == 2.5
print("CONTROL spread %.3f mean %.3f -> %s" % (spread, mean, "PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
'''

NEG_FIXTURE = '''
import sys
vals = [1.0, 2.0, 3.0, 4.0]
mean = sum(vals) / len(vals)
w_neg = 0.0
print("CONTROL at a non-degenerate point: width = %.1e   PASS" % w_neg)
print("mean is %.3f" % mean)
sys.exit(0)
'''


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    argv = sys.argv[1:]
    limit = DEFAULT_LIMIT
    if "--limit" in argv:
        i = argv.index("--limit")
        limit = int(argv[i + 1]); del argv[i:i + 2]
    files = [a for a in argv if not a.startswith("-")]
    if not files:
        print("give one or more probe .py files to mutate", file=sys.stderr)
        return 2

    t0 = time.time()
    workers = min(12, (os.cpu_count() or 4))
    print("mutation sweep: %d files, up to %d mutants each, %d workers\n" % (len(files), limit, workers),
          flush=True)

    with ProcessPoolExecutor(max_workers=workers) as pool:
        pos = score_probe("_pos.py", POS_FIXTURE, [], limit, pool)
        neg = score_probe("_neg.py", NEG_FIXTURE, [], limit, pool)
        print("CONTROL  a real gate        kind=%-11s caught=%d unnoticed=%d  (must be GATE)"
              % (pos["kind"], pos["caught"], len(pos["unnoticed"])))
        print("CONTROL  literal-0.0 bug    kind=%-11s caught=%d unnoticed=%d  (must NOT be GATE,"
              " and the 0.0 line must be among the unnoticed)"
              % (neg["kind"], neg["caught"], len(neg["unnoticed"])))
        if pos["kind"] != "GATE" or neg["kind"] not in ("WEAK-GATE", "REPORT-ONLY")                 or not any("0.0 -> " in u for u in neg["unnoticed"]):
            print("\nCONTROLS FAILED -- cannot tell a gate from a report. No table printed.")
            print("  positive: %s\n  negative: %s" % (pos, neg))
            return 2
        print()

        rows = []
        for f in files:
            if not os.path.exists(f):
                print("  MISSING %s" % f)
                continue
            src = io.open(f, encoding="utf-8").read()
            name = os.path.basename(f)
            deps = []
            dpath = f + ".deps"
            if os.path.isdir(dpath):
                for root, _d, fs in os.walk(dpath):
                    for x in fs:
                        full = os.path.join(root, x)
                        deps.append((os.path.relpath(full, dpath).replace("\\", "/"),
                                     io.open(full, encoding="utf-8", errors="replace").read()))
            r = score_probe(name, src, deps, limit, pool)
            rows.append(r)
            print("  %-52s %-11s guarded %2d  crashed %2d  unnoticed %2d  inert %2d"
                  % (name[:52], r["kind"], r["guarded"], r["crashed"],
                     len(r["unnoticed"]), r["inert"]), flush=True)

    gates = [r for r in rows if r["kind"] == "GATE"]
    reports = [r for r in rows if r["kind"] == "REPORT-ONLY"]
    inert = [r for r in rows if r["kind"] == "INERT"]
    weak = [r for r in rows if r["kind"] == "WEAK-GATE"]

    print("\n" + "=" * 100)
    print("  GATE %d   WEAK-GATE %d   REPORT-ONLY %d   INERT %d   of %d published probes"
          % (len(gates), len(weak), len(reports), len(inert), len(rows)))
    print()
    print("  GATE         an ASSERTION fired or the stated verdict changed. A crash does not count:")
    print("               the interpreter falling over on mutated arithmetic caught nothing.")
    print("  REPORT-ONLY  every mutation changed the numbers it printed and NONE changed its")
    print("               verdict. Not a bug: it is a report, not a gate. But it cannot fail, so")
    print("               citing it as a check is a claim the artifact does not support.")
    print("  WEAK-GATE    it asserts something, but under half the changes it measured")
    print("               differently moved its verdict -- the literal-0.0 control's shape.")
    print("  INERT        nothing moved at all -- the mutated lines are not on the executed path.")

    if reports:
        print("\n  REPORT-ONLY, with an example of a change each one did not notice:")
        for r in reports:
            ex = r["unnoticed"][0] if r["unnoticed"] else "(none)"
            print("    %-52s %s" % (r["name"][:52], ex))
    if weak:
        print("\n  WEAK-GATE -- changes its own verdict did NOT notice:")
        for r in weak:
            print("    %-52s caught %d of %d live" % (r["name"][:52], r["caught"],
                                                      r["caught"] + len(r["unnoticed"])))
            for u in r["unnoticed"][:4]:
                print("        unnoticed: %s" % u)
    if gates:
        print("\n  GATE, and what still slipped past the verdict:")
        for r in gates:
            print("    %-52s caught %d, unnoticed %d" % (r["name"][:52], r["caught"], len(r["unnoticed"])))
            for u in r["unnoticed"][:3]:
                print("        unnoticed: %s" % u)
    print("=" * 100)

    out = os.path.join(HERE, os.path.basename(__file__).replace(".py", ".result.json"))
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(dict(controls=dict(positive=pos, negative=neg), rows=rows, limit=limit,
                       elapsed_s=time.time() - t0), fh, indent=1)
    print("\nreceipt -> %s   (%.0fs)" % (os.path.basename(out), time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
