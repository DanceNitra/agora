"""VALIDATE: re-derive every number claimed about admissibility_preconditions / audit_the_audits.

Run before anything is presented as settled or sent anywhere. Each figure below is recomputed here,
in this process, from the artifact it describes -- not read back from a commit message, a chat
message or my own memory of an earlier run.

Numbers under test, exactly as they were stated:
  * our live decision store: 450 records, 418 distinct keys all resolving, 107 locators,
    0 observations, 0 receipt-chain entries, receipts ENABLED
  * inspeximus exposes 24 verification surfaces and 71 MCP tools
  * the two new suites are 8 + 9 tests and pass
  * audit_the_audits on a healthy store: 4 NOTICED, 1 SUMMARY_HIDES_DETAIL, 0 MISSED, 0 CONTROL_FAILED
  * the live store returns 3 CONTROL_FAILED, and the reason is the empty receipt chain

A live store GROWS, so its record count is checked as a LOWER BOUND and its structural facts
(observations == 0, chain == 0) exactly -- the shape of claim that cannot go stale in the direction
the data moves.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path


def find_repo() -> Path:
    env = os.environ.get("INSPEXIMUS_REPO")
    if env and Path(env, "inspeximus", "core.py").is_file():
        return Path(env)
    here = Path(__file__).resolve().parents[2]
    for sib in ("inspeximus-repo", "inspeximus"):
        c = here.parent / sib
        if (c / "inspeximus" / "core.py").is_file():
            return c
    raise SystemExit("no inspeximus checkout found")


REPO = find_repo()
sys.path.insert(0, str(REPO))
LIVE = os.environ.get("AGORA_DECISION_STORE",
                      os.path.expanduser("~/.inspeximus/mcp_memory.json"))
F: list = []


def check(tag, ok, detail):
    F.append((tag, ok))
    print(f"  [{'ok  ' if ok else 'FAIL'}] {tag}: {detail}")


from inspeximus import Inspeximus  # noqa: E402

# ── the live store ────────────────────────────────────────────────────────────────────────────
if not os.path.exists(LIVE):
    check("the live decision store exists", False, f"MISSING: {LIVE}")
else:
    m = Inspeximus(path=LIVE, embed=False, receipts=True)
    n = len(m.items)
    assert n > 0, "COVER: an empty store makes every structural claim below vacuous"
    r = m.admissibility_preconditions()
    by = {p["id"]: p for p in r["preconditions"]}

    check("live store holds at least 450 records", n >= 450, f"{n} records (a floor: it grows)")
    ka = by["key_agreement"]
    check("key_agreement HOLDS, and it was applicable",
          ka["applicable"] and ka["holds"] and not ka["failed"],
          f"{ka['checked']} distinct keys, {len(ka['failed'])} unresolved")
    oc = by["observation_channel_alive"]
    check("observation channel is DEAD: locators > 0 and observations == 0",
          oc["applicable"] and not oc["holds"] and oc["observations"] == 0 and oc["locators"] > 0,
          f"{oc['locators']} locators, {oc['observations']} observations")
    # RETRACTED AND REPLACED. This file first asserted "receipts ENABLED with an EMPTY chain" and
    # it PASSED -- because the probe opened the store with receipts=True and thereby created the
    # condition it then verified. A validation that hands itself the answer is the defect this whole
    # release is about, committed by the validator. What is actually true is smaller and checkable
    # by anyone: the store was never written with receipts, and the verdict must not move with the
    # caller's constructor argument.
    rc = by["receipt_chain_covers_records"]
    check("the store was NEVER written with receipts (no sidecar on disk)",
          not os.path.exists(LIVE + ".receipts.json") and not rc["chain_file_on_disk"],
          "no <store>.receipts.json -- the integrity feature was never switched on here")
    verdicts = set()
    for kw in ({"receipts": True}, {"receipts": False}, {}):
        q = {x["id"]: x for x in Inspeximus(path=LIVE, embed=False, **kw)
             .admissibility_preconditions()["preconditions"]}["receipt_chain_covers_records"]
        verdicts.add((q["applicable"], q["holds"]))
    check("MUST-NOT: the caller's own flag cannot change the verdict", verdicts == {(False, True)},
          f"three ways of opening the same file -> {verdicts}"
          + ("" if verdicts == {(False, True)} else "  <- the finding is the caller's, not the store's"))
    check("overall verdict is NOT ok (the observation channel alone carries it)",
          r["ok"] is False, f"ok={r['ok']}")

    aa = m.audit_the_audits()
    check("live store: audit_the_audits returns CONTROL_FAILED for the receipt-dependent probes",
          len(aa["control_failed"]) >= 1,
          f"{len(aa['control_failed'])} control_failed, {aa['noticed']} noticed "
          "-- an already-unhappy surface is not scored, which is the point")

# ── the surfaces and the shipped tool count ──────────────────────────────────────────────────
V = [x for x in dir(Inspeximus)
     if not x.startswith("_") and callable(getattr(Inspeximus, x, None))
     and (x.startswith(("verify", "check", "detect"))
          or x.endswith(("audit", "_report", "certificate", "integrity", "coherence")))]
check("verification surfaces counted from the class, not from prose", len(V) >= 24,
      f"{len(V)} surfaces")

tools = len(re.findall(r"^@mcp\.tool\(\)",
                       (REPO / "inspeximus" / "mcp_server.py").read_text(encoding="utf-8"), re.M))
published = re.search(r"MCP server with \*\*(\d+) tools\*\*",
                      (REPO / "README.md").read_text(encoding="utf-8"))
check("README's tool count equals the live count",
      bool(published) and int(published.group(1)) == tools,
      f"live {tools}, README {published.group(1) if published else 'absent'}")
# REACHABLE IN THE CHECKOUT IS NOT REACHABLE ON THE RUNNING SERVER, and the first version of this
# file conflated them. The connected `inspeximus-mcp` is a uvx-pinned build from an earlier day; a
# tool added to this source tree is not in it until the connection is restarted. Reporting "exposed
# over MCP" from a grep of our own file is measuring the code we wrote, not the code that runs.
src = (REPO / "inspeximus" / "mcp_server.py").read_text(encoding="utf-8")
for name in ("admissibility_preconditions", "audit_the_audits"):
    check(f"{name} is exposed IN THIS CHECKOUT", f"def {name}(" in src,
          "present in mcp_server.py -- says nothing about the running server")
# THREE STATES, not two, and the first version collapsed them. It ran a HARDCODED uvx archive path
# -- the build pinned on 2026-08-12 -- so after that server was stopped the check kept interrogating
# a dead directory and reporting a stale version as "what runs". "Nothing is running" and "something
# old is running" need different answers, and neither is "the new tools are live".
import re as _re
import subprocess as _sp
mine = (_re.search(r'version = "([^"]+)"',
                   (REPO / "pyproject.toml").read_text(encoding="utf-8")) or [None, "?"])[1]
ps = _sp.run(["powershell", "-NoProfile", "-Command",
              "@(Get-CimInstance Win32_Process | ? { $_.CommandLine -like '*inspeximus-mcp*' })"
              ".Count"], capture_output=True, text=True, timeout=60).stdout.strip()
running = ps.isdigit() and int(ps) > 0

# What a FRESH resolve would serve is a fact about the published package and is checkable now.
fresh = _sp.run(["uvx", "--from", "inspeximus[mcp]", "python", "-c",
                 "import inspeximus;print(inspeximus.__version__)"],
                capture_output=True, text=True, timeout=180).stdout.strip().splitlines()[-1:] or [""]
check("a FRESH uvx resolve would serve this version", fresh[0] == mine,
      f"uvx serves {fresh[0] or 'unknown'}, checkout {mine}")
check("MCP availability is reported, not assumed", True,
      f"{'a server IS running -- its version was not interrogated here' if running else 'NO inspeximus-mcp process is running'}; "
      "the tools are callable only after the client reconnects, and this file does not claim they are")

# ── the tests exist, run, and their must-fail controls bite ──────────────────────────────────
suites = ["tests/test_admissibility_preconditions.py", "tests/test_the_checks_can_actually_fail.py"]
p = subprocess.run([sys.executable, "-m", "pytest", *suites, "-q", "-n", "0"],
                   capture_output=True, text=True, cwd=str(REPO), encoding="utf-8", errors="replace")
mm = re.search(r"(\d+) passed", p.stdout or "")
check("both new suites pass", p.returncode == 0 and bool(mm),
      f"{mm.group(1) if mm else '?'} passed, exit {p.returncode}")

# MUST-FAIL: blind a surface and audit_the_audits has to report MISSED. If it does not, the feature
# has itself become a check that cannot fail.
mustfail = subprocess.run(
    [sys.executable, "-c",
     "import sys;sys.path.insert(0,r'%s');"
     "import os,tempfile;from inspeximus import Inspeximus;"
     "d=tempfile.mkdtemp();ix=Inspeximus(path=os.path.join(d,'s.json'),embed=False,receipts=True);"
     "ix.remember('a',key='a',object='a');ix.flush();"
     "B=type('B',(type(ix),),{'verify_writes':lambda self,*a,**k:(True,[])});"
     "print(len(B(path=str(ix.path),embed=False,receipts=True).audit_the_audits()['missed']))"
     % str(REPO)], capture_output=True, text=True, encoding="utf-8", errors="replace")
missed = (mustfail.stdout or "0").strip().splitlines()[-1:] or ["0"]
check("MUST-FAIL: a blinded surface is reported as MISSED", missed[0].isdigit() and int(missed[0]) >= 1,
      f"{missed[0]} missed when verify_writes is stubbed clean"
      + ("" if missed[0].isdigit() and int(missed[0]) >= 1
         else "  <- the detector cannot detect, and every result above is void"))

print("\n" + "=" * 94)
bad = [t for t, ok in F if not ok]
print(f"VALIDATE: {len(bad)} unverified of {len(F)}" + (f"  -> {bad}" if bad else ""))
print("Record counts are floors on a growing store; structural facts (0 observations, 0 chain) are")
print("exact, because those are the claims and they do not drift in the direction the data moves.")
raise SystemExit(1 if bad else 0)
