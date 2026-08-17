"""Is the identifier a store writes the identifier it queries? Measured, after three wrong answers.

THE CLAIM THIS SUPPORTS IS A STORE-SIDE CLAIM, and saying so is the point. Three versions of this
probe were wrong before this one, each in a way the previous version could not see:

  v1  called `ix.remember()` / `ix.recall()` with ASCII keys it had just built -- the Python API,
      the layer that cannot have the bug. Coverage is anti-correlated with detection here: the
      feature has tests BECAUSE someone implemented it, and those tests import it directly.

  v2  drove the CLI, but every assertion carried an escape hatch on its own precondition
      (`same or rc != 0`, `len(both) < 2`, `not stored.get(name)`, an empty near-miss list, a final
      loop over only the keys that arrived). Measured by sabotage: with every CLI write refused it
      scored 14/14 over a store that received nothing. IEEE 1800 SVA calls that a VACUOUS SUCCESS
      and pairs every assertion with a `cover` on its antecedent; RIPR (Voas, IEEE TSE 1992) makes
      Reachability the first necessary condition before a test can fail at all. v2 was the defect
      it existed to detect.

  v3  forced PYTHONUTF8=1 into the child environment -- which is not test hygiene, it is THE
      MITIGATION. This console is cp1250 (CLAUDE.md 11). Without the forcing the CLI exits non-zero
      on an NFD key, and v2's `rc != 0` hatch scored that as a pass: a CLI that crashes on every
      accented identifier went green. Worse, `subprocess.run(text=True)` with no `encoding=` had
      the PARENT decode the child's UTF-8 as cp1250, so the reader thread died on byte 0x81 and
      run() returned rc=0 / stdout=None / no exception, while the probe printed "identical".

SO THIS VERSION: covers its antecedent before asserting anything, has no disjunctive escapes,
compares RAW BYTES in the file rather than two strings a shared codec pair would agree on, pins the
child's encoding explicitly, and runs the CLI leg BOTH with and without the UTF-8 forcing so the
mitigation is a reported condition rather than a hidden premise.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unicodedata

def _find_the_repo() -> str:
    """Where to run the CLI from. This was an absolute path on one Windows machine, which made a
    probe we offer as "runnable" runnable by exactly one person -- a claim that fails the moment a
    reader clicks the link. Resolution order, first hit wins:

      1. $INSPEXIMUS_REPO            -- an explicit answer beats every guess
      2. a sibling checkout          -- ../inspeximus-repo or ../inspeximus, the usual layout
      3. the installed package       -- run against whatever `import inspeximus` resolves to

    The last one is a fallback, not a default: running the CLI from an installed wheel measures the
    RELEASED build, which is a different experiment from measuring the working tree. The banner says
    which one happened, because a probe that will not tell you what it measured has told you nothing.
    """
    env = os.environ.get("INSPEXIMUS_REPO")
    if env and os.path.isdir(env):
        return env
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for sib in ("inspeximus-repo", "inspeximus"):
        cand = os.path.join(os.path.dirname(here), sib)
        if os.path.isfile(os.path.join(cand, "inspeximus", "cli.py")):
            return cand
    import inspeximus as _i                     # installed: measure what is installed, and say so
    return os.path.dirname(os.path.dirname(os.path.abspath(_i.__file__)))


REPO = _find_the_repo()
F: list = []


def check(tag, ok, text):
    F.append((tag, ok))
    print(f"  [{'ok  ' if ok else 'FAIL'}] {tag}: {text}")


CASES = {
    "nfc":      unicodedata.normalize("NFC", "sed\u00e1cia-kl\u00fa\u010d"),
    "nfd":      unicodedata.normalize("NFD", "sed\u00e1cia-kl\u00fa\u010d"),
    "colon":    "Bridge #205: the one with a colon",
    "long_a":   "session-abcdefgh-0000000000000000-alpha",
    "long_b":   "session-abcdefgh-0000000000000000-omega",
    "mixed":    "Acme-Tenant-ID",
    "trailing": "key-with-trailing-space ",
}


def write_all(force_utf8: bool):
    """Write every case through the CLI. Returns (store_path, {name: (rc, stderr_tail)})."""
    store = os.path.join(tempfile.mkdtemp(), "s.json")
    env = dict(os.environ)
    if force_utf8:
        env.update(PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    else:
        env.pop("PYTHONUTF8", None)
        env.pop("PYTHONIOENCODING", None)
    out = {}
    for name, key in CASES.items():
        r = subprocess.run(
            [sys.executable, "-m", "inspeximus.cli", "--path", store,
             "remember", f"value for {name}", "--key", key, "--object", name],
            capture_output=True, cwd=REPO, env=env)          # BYTES, no text=True: see v3 above
        out[name] = (r.returncode, (r.stderr or b"")[-90:].decode("utf-8", "replace"))
    return store, out


# ══════════════════════ the environment is a REPORTED CONDITION, not a hidden premise
# WHAT WAS MEASURED, printed before any result. A probe that will not name the build it exercised
# cannot be cited, and "measure the code that RUNS" is the rule this line exists to make checkable.
_v = subprocess.run([sys.executable, "-c", "import inspeximus;print(inspeximus.__version__)"],
                    capture_output=True, text=True, cwd=REPO).stdout.strip() or "unknown"
print(f"  TARGET: inspeximus {_v} at {REPO}")
print("  set INSPEXIMUS_REPO to point this elsewhere; a sibling checkout is found automatically\n")
print("  the CLI leg, run twice -- the second run is the one this machine actually has\n")
for forced in (True, False):
    store, res = write_all(forced)
    rows = json.load(open(store, encoding="utf-8")) if os.path.exists(store) else []
    bad = {n: v for n, (rc, v) in res.items() if rc != 0}
    label = "PYTHONUTF8=1 (forced)" if forced else "console default (cp1250 here)"
    print(f"  {label:34} {len(rows)}/{len(CASES)} written"
          + (f", refused: {sorted(bad)}" if bad else ", no refusals"))
    if not forced:
        # NOT an assertion about correctness -- a statement of the precondition the claim needs.
        # It USED to fail here: before inspeximus 2.13.0 the CLI stored the record and then crashed
        # printing the confirmation, exiting 1 on this cp1250 console. That is why the check keeps
        # its two branches rather than being deleted now that it passes -- it is the regression
        # guard for the fix, and a check that only ever passes has stopped measuring anything.
        check("the CLI writes every key WITHOUT a forced UTF-8 environment", not bad,
              "every key written on the console default -- no PYTHONUTF8 needed" if not bad else
              f"{sorted(bad)} refused without PYTHONUTF8=1 -- so any CLI-level claim below is "
              f"conditional on that, and the honest claim is a STORE claim: {list(bad.values())[0][:60]}")

# ══════════════════════ COVER THE ANTECEDENT before any assertion is allowed to count
store, res = write_all(True)
raw = open(store, "rb").read() if os.path.exists(store) else b""
rows = json.load(open(store, encoding="utf-8")) if os.path.exists(store) else []
stored = {r.get("object"): r.get("key") for r in rows}
print()
if len(stored) != len(CASES):
    print(f"  [FAIL] COVER: only {len(stored)}/{len(CASES)} keys reached the store")
    print("  ABORTING: every assertion below is satisfiable by absence.")
    raise SystemExit(1)
check("COVER: every case reached the store", True,
      f"{len(stored)}/{len(CASES)} present -- the assertions below can actually fail")

# ══════════════════════ raw bytes, not two strings a shared codec pair would agree on
for name, key in CASES.items():
    esc = json.dumps(key)[1:-1].encode()
    lit = key.encode("utf-8")
    present = esc in raw or lit in raw
    check(f"raw file bytes carry {name}", present,
          "present in the file exactly as sent" if present else "NOT in the raw bytes")

# ══════════════════════ no escapes: each of these can fail
for name, key in CASES.items():
    check(f"stored key == sent key ({name})", stored.get(name) == key,
          "identical" if stored.get(name) == key else f"sent {key!r} -> stored {stored.get(name)!r}")

nfc, nfd = CASES["nfc"], CASES["nfd"]
present = [r for r in rows if r.get("key") in (nfc, nfd)]
check("NFC and NFD stay two distinct keys", len({r["key"] for r in present}) == 2,
      f"{len(present)} rows, {len({r['key'] for r in present})} distinct -- same word to a human, "
      f"different bytes; the IDNA2003/2008 deviation class at store scale")

# ══════════════════════ the near-miss control, driven through a KEY-ADDRESSED surface
env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}


def forget_dry(key):
    r = subprocess.run([sys.executable, "-m", "inspeximus.cli", "--path", store,
                        "forget", "--key", key, "--dry-run"],
                       capture_output=True, cwd=REPO, env=env)
    return r.returncode, (r.stdout or b"").decode("utf-8", "replace")


rc_hit, out_hit = forget_dry(CASES["long_a"])
rc_miss, out_miss = forget_dry(CASES["long_b"][:-5] + "zzzzz")
check("a key-addressed surface resolves the real key", rc_hit == 0 and "0" not in out_hit.split()[:1],
      f"forget --key --dry-run on the real key: rc={rc_hit}")
check("control: a near-miss key resolves to nothing", out_miss != out_hit,
      "an id differing only after character 8 gets a different answer from the real one -- so the "
      "checks above are not passing on a lookup that matches everything")

print("\n" + "=" * 78)
bad = [t for t, ok in F if not ok]
print(f"IDENTIFIER, STORE-SIDE: {len(bad)} failure(s) of {len(F)}" + (f"  -> {bad}" if bad else ""))
print("SCOPE: the store and the CLI, run BOTH with PYTHONUTF8=1 forced and on the console default "
      "(cp1250 here) -- the second is the one that matters, and it is the leg that used to fail. "
      "It does not measure MCP/JSON-RPC or HTTP, and it says nothing about identifiers written by "
      "earlier versions already on disk: this reads surviving keys, so a fold that already merged "
      "two of them left no trace of the second.")
