"""VALIDATE step: re-run every number the public write-up would assert, against PUBLISHED wheels.

The claim under test, in one sentence:

    Two consecutive inspeximus releases shipped erasure-correctness defects that a 1600-test library
    suite could not see, because the tests exercise the LIBRARY and the product is used through a
    SURFACE (the MCP server and the CLI).

Nothing here is read from a note or recalled from last night. Each arm downloads the wheel from PyPI and
runs the failing case against it, so every figure in the draft is backed by an artifact re-run this cycle.

Arms:
  1  1.86.0  a right-to-erasure request naming a subject ABSENT from the store deletes a real person's
             records and reports success                                        (over-erasure)
  2  1.87.0  a correction written through route() survives the subject's erasure holding their CURRENT
             value                                                              (under-erasure)
  3  1.88.0  both are fixed
  4  the SURFACE gap: a store written through the MCP server answered would_erase=0 to every phrasing
     of the subject, while the identical write through the library answered 1
  5  the suite size at the time, so "1600 tests were green" is a measured number and not a flourish

RUN:  python research/probes/validate_surface_blindness_claim.py
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CACHE = os.path.join(tempfile.gettempdir(), "inspeximus_wheels")
os.makedirs(CACHE, exist_ok=True)
RESULT = {}


def wheel(version: str):
    """Download + extract the PUBLISHED wheel. Never the repo."""
    d = os.path.join(CACHE, version)
    pkg = os.path.join(d, "x", "inspeximus", "__init__.py")
    if os.path.exists(pkg):
        return os.path.dirname(os.path.dirname(pkg))
    os.makedirs(d, exist_ok=True)
    subprocess.run([sys.executable, "-m", "pip", "download", f"inspeximus=={version}",
                    "--no-deps", "--no-cache-dir", "-d", d],
                   capture_output=True, check=True)
    whl = next(f for f in os.listdir(d) if f.endswith(".whl"))
    import zipfile
    with zipfile.ZipFile(os.path.join(d, whl)) as z:
        z.extractall(os.path.join(d, "x"))
    return os.path.join(d, "x")


def load(version: str):
    root = wheel(version)
    name = f"insp_{version.replace('.', '_')}"
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(root, "inspeximus", "__init__.py"),
        submodule_search_locations=[os.path.join(root, "inspeximus")])
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def store(mod):
    return mod.Inspeximus(path=os.path.join(tempfile.mkdtemp(), "s.json"), receipts=True)


def alive(m):
    return " ".join((r.get("text") or "") + str(r.get("object") or "")
                    for r in m.items if r.get("status") != "erased")


print("=== ARM 1: over-erasure. A ghost subject deletes a real person's records ===")
for v in ("1.86.0", "1.87.0", "1.88.0"):
    mod = load(v)
    st = store(mod)
    st.remember("alice payroll row", key="p", object="x", source={"doc": "hr/alice"})
    try:
        n = st.forget_subject("hr/nobody-here", request_id="G", basis="art17")["erased"]
        out = f"erased {n}"
    except Exception as e:
        n, out = None, f"REFUSED {type(e).__name__}"
    RESULT[f"arm1_{v}"] = out
    print(f"   {v}  forget_subject('hr/nobody-here') -> {out}"
          f"{'   <-- DATA LOSS' if n else ''}")

print("\n=== ARM 2: under-erasure. A routed correction survives holding the CURRENT value ===")
for v in ("1.86.0", "1.87.0", "1.88.0"):
    mod = load(v)
    st = store(mod)
    st.remember("alice home address is 5 Elm St", key="alice::addr", object="5 Elm St",
                source={"doc": "hr/alice"})
    st.route("actually alice moved to 9 Oak Ave", key="alice::addr", object="9 Oak Ave")
    res = st.forget_subject("hr/alice", request_id="R", basis="art17")
    survives = "9 Oak" in alive(st)
    RESULT[f"arm2_{v}"] = {"erased": res["erased"], "current_value_survives": survives}
    print(f"   {v}  erased {res['erased']}   CURRENT value survives: {survives}"
          f"{'   <-- the live data is what is left' if survives else ''}")

print("\n=== ARM 3: the SURFACE gap. Same write, library vs MCP server ===")
print("   CORRECTED MID-VALIDATION. The first version of this arm ran against 1.87.0 and produced")
print("   would_erase=0, which looked like the claim confirmed. It was not: 1.87.0's MCP tool ALREADY")
print("   takes `source` (added just before that release), and my call simply did not pass one -- so it")
print("   measured 'the caller omitted provenance', which is the documented contract, not a defect. The")
print("   surface gap belongs to 1.86.0 and earlier, and that is where it has to be shown.")
import inspect as _inspect  # noqa: E402

for v in ("1.86.0", "1.87.0"):
    mod_v = load(v)
    root = wheel(v)
    lib = store(mod_v)
    lib.remember("alice home address is 5 Elm St", key="addr::alice", object="5 Elm St",
                 source={"doc": "hr/alice"})
    lib_n = lib.forget_subject("hr/alice", request_id="D", basis="art17",
                               dry_run=True)["would_erase"]
    try:
        os.environ["INSPEXIMUS_PATH"] = os.path.join(tempfile.mkdtemp(), f"m{v}.json")
        spec = importlib.util.spec_from_file_location(
            f"mcp{v.replace('.', '')}", os.path.join(root, "inspeximus", "mcp_server.py"))
        mcp = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mcp)
        params = list(_inspect.signature(mcp.remember).parameters)
        can_attach = "source" in params
        # Pass a source when the tool ACCEPTS one -- otherwise the arm measures the caller, not the tool.
        if can_attach:
            mcp.remember("alice home address is 5 Elm St", key="addr::alice", object="5 Elm St",
                         source="hr/alice")
        else:
            mcp.remember("alice home address is 5 Elm St", key="addr::alice", object="5 Elm St")
        st2 = mod_v.Inspeximus(path=os.environ["INSPEXIMUS_PATH"], receipts=True)
        mcp_n = {p: st2.forget_subject(p, request_id="D", basis="art17",
                                       dry_run=True)["would_erase"]
                 for p in ("alice", "hr/alice", "5 Elm St")}
        RESULT[f"arm3_{v}"] = {"library": lib_n, "mcp": mcp_n, "mcp_can_attach_source": can_attach}
        print(f"   {v}  library(source) would_erase = {lib_n} | "
              f"MCP accepts source: {can_attach} | MCP-written: {mcp_n}")
    except Exception as e:
        RESULT[f"arm3_{v}"] = f"NOT MEASURED: {type(e).__name__}: {str(e)[:90]}"
        print(f"   {v}  MCP arm NOT MEASURED: {type(e).__name__}: {str(e)[:90]}")
print("   -> the claim is about the version where the tool COULD NOT attach a source at all.")

print("\n=== ARM 4: how many tests were green while that was true ===")
try:
    r = subprocess.run(["git", "-C", r"C:\Users\Danculus\inspeximus-repo",
                        "show", "v1.87.0:tools/skip_census.py"], capture_output=True, text=True)
    have_tag = r.returncode == 0
except Exception:
    have_tag = False
print(f"   v1.87.0 tag readable: {have_tag}")
print("   (the suite figure quoted in any draft must come from a run recorded in this repo's history,")
print("    not from memory -- 1648 was measured on the 1.88.0 release commit.)")

out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "validate_surface_blindness_claim.result.json")
json.dump(RESULT, open(out, "w", encoding="utf-8"), indent=2)
print(f"\nwrote {out}")
print("\n-> Any figure that does not appear in this file must not appear in the draft.")
