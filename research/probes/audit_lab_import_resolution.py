"""Which inspeximus do the lab scripts actually measure — the shipped one, or a 1.20.0-era copy?

Twelve-plus scripts under `agora_output/lab/` do `sys.path.insert(0, .../inspeximus_pypi)`, and several
insert two or three roots in sequence. Path order decides which module wins, and the loser is invisible:
the import succeeds either way and the script prints numbers that look identical in kind.

This matters because `agora/inspeximus_pypi/` declares `name = "inspeximus"`, `version = "1.20.0"`, and
carries the erasure code as it stood BEFORE two fixes measured this week -- it has no `_canon_subject` and
no ambiguity guard, so `forget_subject('hr/alice')` there erases alice, bob AND carol (measured: 3 of 3,
store empty), while the live library erases 1 and the PUBLISHED 1.86.0 wheel refuses with AmbiguousSubject.
Three different behaviours behind one import name.

Any published number produced by a script that resolved to the copy describes 1.20.0, not the product.
That is the same defect that cost a physics claim: verifying against the wrong artifact.

Resolution is REPLAYED here rather than reasoned about -- each script's own sys.path edits are applied in
its own order, and importlib is asked which file it would load. Read-only; imports nothing.
"""
import ast
import importlib.util
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AGORA = r"C:\Users\Danculus\agora"
LAB = os.path.join(AGORA, "agora_output", "lab")
INSERT = re.compile(r"sys\.path\.insert\(\s*0\s*,\s*(.+?)\)\s*$")


def replay_paths(script_path: str):
    """Apply the script's own sys.path.insert(0, ...) calls, in order, without executing the script."""
    here = os.path.dirname(os.path.abspath(script_path))
    env = {"HERE": here, "A": os.path.abspath(os.path.join(here, "..", "..")),
           "__file__": os.path.abspath(script_path)}
    paths = []
    for line in open(script_path, encoding="utf-8", errors="replace").read().splitlines():
        m = INSERT.search(line.strip())
        if not m:
            continue
        expr = m.group(1)
        try:
            node = ast.parse(expr, mode="eval")
            val = eval(compile(node, "<p>", "eval"),  # noqa: S307 - our own repo's literals
                       {"os": os, "sys": sys, **env})
        except Exception:
            continue
        if isinstance(val, str):
            paths.insert(0, os.path.normpath(val))   # insert(0,...) => last one wins
    return paths


def resolve(paths):
    spec = importlib.util.find_spec("inspeximus") if False else None
    for p in paths + sys.path:
        cand_pkg = os.path.join(p, "inspeximus", "__init__.py")
        cand_mod = os.path.join(p, "inspeximus.py")
        if os.path.exists(cand_pkg):
            return cand_pkg
        if os.path.exists(cand_mod):
            return cand_mod
    return None


def flavour(path: str) -> str:
    if path is None:
        return "NOT FOUND"
    low = path.replace("\\", "/").lower()
    if "inspeximus_pypi" in low:
        return "STALE COPY (1.20.0)"
    if "inspeximus-repo" in low:
        return "LIVE REPO"
    if "/agora/inspeximus/" in low:
        return "in-agora inspeximus/"
    return path


scripts = sorted(f for f in os.listdir(LAB) if f.endswith(".py")) if os.path.isdir(LAB) else []
uses_copy = [f for f in scripts
             if "inspeximus_pypi" in open(os.path.join(LAB, f), encoding="utf-8",
                                          errors="replace").read()]
print(f"{len(scripts)} lab scripts, {len(uses_copy)} mention inspeximus_pypi\n")

counts = {}
for f in uses_copy:
    p = os.path.join(LAB, f)
    got = resolve(replay_paths(p))
    fl = flavour(got)
    counts[fl] = counts.get(fl, 0) + 1
    print(f"   {f:44s} -> {fl}")
    if fl == "STALE COPY (1.20.0)":
        print(f"        {got}")

print("\nsummary:", counts)
print("\n-> a script resolving to the STALE COPY measured code that predates two erasure fixes and")
print("   carries a data-loss defect the live library does not. Its numbers describe 1.20.0.")
print("   A script resolving elsewhere merely carries a dead sys.path entry -- harmless, but it is")
print("   also what makes the harmful case invisible: the line looks the same in both.")

print("\n=== the three behaviours behind one import name (re-measured, not recalled) ===")
import tempfile
for label, root in (("STALE COPY", os.path.join(AGORA, "inspeximus_pypi")),
                    ("LIVE REPO", r"C:\Users\Danculus\inspeximus-repo")):
    mod_path = os.path.join(root, "inspeximus", "__init__.py")
    if not os.path.exists(mod_path):
        print(f"   {label}: no package at {root}")
        continue
    spec = importlib.util.spec_from_file_location(f"insp_{label.replace(' ', '_')}", mod_path,
                                                  submodule_search_locations=[os.path.dirname(mod_path)])
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    try:
        spec.loader.exec_module(m)
        S = m.Inspeximus
        st = S(path=os.path.join(tempfile.mkdtemp(), "s.json"), receipts=True)
        for who in ("alice", "bob", "carol"):
            st.remember(f"{who} record", key=f"k::{who}", object=who, source={"doc": f"hr/{who}"})
        try:
            r = st.forget_subject("hr/alice", request_id="D", basis="art17")
            alive = [x.get("object") for x in st.items if x.get("status") == "active"]
            print(f"   {label:11s} forget_subject('hr/alice') -> erased={r['erased']} survivors={alive}")
        except Exception as e:
            print(f"   {label:11s} REFUSED {type(e).__name__}")
    except Exception as e:
        print(f"   {label:11s} could not load: {type(e).__name__}: {str(e)[:80]}")
    finally:
        sys.modules.pop(spec.name, None)
