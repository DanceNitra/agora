# A green test suite that never ran 156 of its tests

**The short answer.** Our suite reported **2813 passed**. In the CI base image, **156 test functions in it had never run** — not skipped-and-reported, but never collected at all. One module-level `pytest.importorskip` removes an entire file and reports that as a single skip line, so fifty hidden tests and one deliberate skip look identical in the summary. On a developer laptop the count is **0**, because the optional packages are installed there. That gap is why this survives for years.

**The claim under test.** That a green suite plus a visible skip count tells you what ran. It does not. The skip count is a count of *skip events*, not of tests that did not execute, and nothing in pytest's default or `-ra` output reconciles the two.

## The mechanism

Put a guard at module scope:

```python
import pytest
pytest.importorskip("some_optional_thing")   # module level

def test_one(): assert True
def test_two(): assert True
def test_three(): assert True
def test_four(): assert True
def test_five(): assert True
```

When that import fails, pytest does not skip five tests. The module raises `Skipped` during collection, so those five functions are never collected and never exist as test items. Put that file next to one with an ordinary in-test `pytest.skip()` and run with `-ra`:

```
SKIPPED [1] test_hidden.py:2: could not import 'some_optional_thing'
SKIPPED [1] test_visible.py:5: an ordinary in-test skip, for contrast
1 passed, 2 skipped
```

Both report `[1]`. Six test functions did not run, and the summary says "2 skipped". `-ra` cannot help, because there is nothing for it to count. (`--strict-markers` concerns unregistered markers and is a different problem.)

## Measuring it

The number depends entirely on **where** you measure, which is the reason nobody notices. Reading the AST tells you what sits behind a guard; checking `importlib.util.find_spec` tells you whether that guard actually fires in the environment you are in.

```python
import ast, importlib.util, pathlib, sys

SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)

def module_level_guards(tree):
    """Dependencies guarded at module scope. Never descends into a def or a class: a guard inside a
    function skips that one test and reports it honestly, which is not the failure mode here."""
    out = []
    for node in tree.body:
        if isinstance(node, SCOPES):
            continue
        for n in ast.walk(node):
            if (isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "importorskip"
                    and n.args and isinstance(n.args[0], ast.Constant)):
                out.append(n.args[0].value)
    return out

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "tests")
behind = hidden = 0
for path in sorted(root.rglob("test_*.py")):
    tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
    deps = module_level_guards(tree)
    if not deps:
        continue
    count = sum(isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef))
                and x.name.startswith("test_") for x in tree.body)
    behind += count
    absent = [d for d in deps if importlib.util.find_spec(d) is None]
    if absent:
        hidden += count
        print("%4d  %-44s missing: %s" % (count, path.name, ", ".join(absent)))
print("----")
print("%4d test functions sit behind a module-level importorskip" % behind)
print("%4d of them are INVISIBLE in this environment right now" % hidden)
```

On our repository:

```
255 test functions sit behind a module-level importorskip
  0 of them are invisible on this machine
```

Same repository, CI base image with pytest and cryptography only: **156**.

## Two ways we got the measurement wrong first

The first version counted every guard whether or not the package was missing. That turned 156 into **281** — a confident wrong answer that agreed with nothing, and it would have shipped if we had not cross-checked it against the repository's own census tool.

The second version switched to `ast.walk` and started descending into function bodies, so it counted a file whose `importorskip` sits inside a single test. That is the case that already behaves correctly and should never be counted. A three-line throwaway file with a nested guard caught it.

Both errors were found by a negative control rather than by reading the code, which is the recurring shape: an instrument that only ever sees the case it was built for cannot tell you it is wrong.

## What we do with the number

We pin it. The count of tests invisible in the base job lives in a constant, and it can only grow by editing that constant in a diff a human reads, with a note naming the module and the reason. A pin with slack absorbs exactly the growth it exists to surface, so it sits on the measured number with no headroom.

The first time the pin moved after that, the three newly hidden tests were ours — a guard we had added for a Python-version fallback. The honest fix was removing the optional dependency from that file, not raising the number. A guard against a release-blocking regression that only runs where the optional extras happen to be installed is a check that cannot fail where it matters.

## Why this is our problem specifically

We build [inspeximus](https://github.com/DanceNitra/inspeximus), a memory layer whose entire proposition is that a system should be able to say what it actually verified rather than what it hopes. The same defect keeps appearing one layer up and one layer down: an erasure audit that reports `verified` after enumerating nothing, an adapter that returns an empty list and is recorded identically to one that was walked, a coverage field that defaults silently and never says it defaulted.

A green suite hiding 156 tests is the same failure in the tooling we use to make those claims. It is not a separate lesson. **A check that cannot distinguish "I looked and found nothing" from "I never looked" is not a check, wherever it sits.**

**Falsifier.** If `-ra`, `--strict-markers`, or any default pytest output distinguishes a five-test module-level guard from a single in-test skip, the premise of this post is wrong. The reproduction is five lines above and takes under a minute.
