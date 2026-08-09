"""RUN the artifacts we publicly offered, and refuse when one stops reproducing its own result.

WHY. Our comment on openclaw#35203 ended "Happy to share the runnable replications for any of these".
On 2026-08-09 one of them, `research/probes/corroboration_poison.py`, was run for the first time in
months. It printed:

    RESULT: poison_blocked=True  legit_graduates=False  sybil_blocked=True  -> FAIL

Three silent causes, none of them a wrong claim: the library grew a guard that refuses to open an
empty store (the probe died at startup), `_GRADUATE_VALUE` moved 1.0 -> 5.0 while the fixture stayed
at 1.0, and graduation is applied by `consolidate()` rather than by the recall path the probe pumped.
The public claim held — poison and sybil were still blocked — but the receipt behind it did not run.
Had anyone taken us up on the offer, they would have run a FAILING probe of ours.

`publish_gate.py` audits these files as TEXT (AST). This RUNS them. A construction defect is visible
without execution; rot is not.

THE TRAP THIS IS BUILT AROUND. That probe **exited 0 while printing FAIL**. Every arm of this tool
therefore reads the VERDICT, and treats the exit code as one signal among several:

    crashed / traceback        -> REFUSE
    timed out                  -> REFUSE   (a receipt nobody can wait for is not a receipt)
    printed a FAIL-shaped line -> REFUSE
    printed NOTHING verdict-ish-> REFUSE as UNKNOWN. exit 0 with no verdict is not a pass.
    needs a resource we lack   -> reported explicitly and counted; never silently skipped

A skip is the whole disease. If a probe cannot run here, that is a fact about our receipts, not a
detail to swallow.

Run:  python -X utf8 tools/public_receipts.py [--timeout 120] [--only substring]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WAIVERS = ROOT / "tools" / "receipt_waivers.json"

# WHAT THIS TOOL ASKS, and the first version got it wrong: "does the receipt still RUN and report its
# own verdict" -- NOT "is the verdict positive". A replication ledger legitimately contains FAILED
# verdicts; `founder_survivorship_null.py` printing "VERDICT (mechanism): FAILED" is its PUBLISHED
# finding, not rot. Flagging those made the tool wrong on 2 of the 12 real artifacts on its first run.
# So a verdict line of ANY polarity means the receipt works. Failure is reserved for the probe's own
# SELF-CHECK reporting that its run did not reproduce.
VERDICT_RE = re.compile(r"\b(VERDICT|RESULT|MEASURED|REPRODUCED|CONCLUSION)\b", re.I)
SELFFAIL_RE = re.compile(r"(->\s*FAIL\b|RESULT:[^\n]*\bFAIL\b|\bREFUSED\b|NOT[ _]REPRODUCED|"
                         r"control (failed|did not)|does not reproduce)", re.I)
# 0xC0000142 STATUS_DLL_INIT_FAILED: Windows refusing to start the process at all. Measured on the
# first run -- a TimeoutExpired kill was followed by FOUR consecutive 0.0s "crashes" with this exact
# code, and every one of those probes ran fine on its own. That is the harness poisoning its own run,
# not four dead receipts, and reporting it as CRASHED would have been four false accusations.
INFRA_CODES = {3221225794, -1073741502}
RESOURCE_RE = re.compile(
    r"(ConnectionRefused|Max retries|Connection refused|URLError|No such file or directory|"
    r"FileNotFoundError|ModuleNotFoundError|CUDA|out of memory|ollama|11434)", re.I)


def _publish_gate():
    spec = importlib.util.spec_from_file_location("publish_gate", ROOT / "tools" / "publish_gate.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def discover() -> dict:
    """Every runnable artifact a PUBLIC post points a reader at, mapped to the posts citing it."""
    pg = _publish_gate()
    out: dict = {}
    src = ROOT / "public" / "posts" / "src"
    for md in sorted(src.glob("*.en.md")):
        local, _unres, _ext = pg.links_in_text(md.read_text(encoding="utf-8", errors="replace"))
        for p in local:
            out.setdefault(Path(p), []).append(md.stem)
    return out


def classify(rc: int, out: str, timed_out: bool) -> tuple[str, str]:
    if timed_out:
        return "TIMEOUT", "did not finish inside the budget"
    if "Traceback (most recent call last)" in out:
        why = RESOURCE_RE.search(out)
        if why:
            return "NEEDS-RESOURCE", "crashed on a missing resource: %s" % why.group(0)
        return "CRASHED", out.strip().splitlines()[-1][:160] if out.strip() else "no output"
    if rc in INFRA_CODES and not out.strip():
        return "INFRA", "the OS refused to start the process (0x%X) — harness problem, not the receipt" % (rc & 0xFFFFFFFF)
    if SELFFAIL_RE.search(out):
        line = next((l.strip() for l in out.splitlines() if SELFFAIL_RE.search(l)), "")
        return "FAIL", line[:160]
    if rc != 0:
        why = RESOURCE_RE.search(out)
        if why:
            return "NEEDS-RESOURCE", "exit %d on a missing resource: %s" % (rc, why.group(0))
        return "CRASHED", "exit %d" % rc
    if VERDICT_RE.search(out):
        line = next((l.strip() for l in out.splitlines() if VERDICT_RE.search(l)), "")
        return "PASS", line[:160]
    return "UNKNOWN", "exit 0 and no verdict line — that is not a pass"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--timeout", type=int, default=120, help="per-artifact seconds")
    ap.add_argument("--only", default="", help="run only artifacts whose path contains this")
    a = ap.parse_args()

    waivers = json.loads(WAIVERS.read_text(encoding="utf-8")) if WAIVERS.exists() else {}
    targets = discover()
    if a.only:
        targets = {k: v for k, v in targets.items() if a.only in str(k)}

    if not targets:
        print("REFUSED: no publicly-linked artifact was discovered. A receipt checker that finds\n"
              "         nothing to run has verified nothing — which is this tool's own disease.")
        return 1

    print("running %d publicly-linked artifact(s), %ds budget each\n" % (len(targets), a.timeout))
    problems = []
    for p in sorted(targets):
        rel = p.relative_to(ROOT).as_posix() if ROOT in p.parents else p.as_posix()
        t0 = time.time()
        timed_out = False
        try:
            r = subprocess.run([sys.executable, "-X", "utf8", str(p)], capture_output=True,
                               text=True, timeout=a.timeout, cwd=str(ROOT))
            rc, out = r.returncode, (r.stdout or "") + (r.stderr or "")
        except subprocess.TimeoutExpired:
            rc, out, timed_out = -1, "", True
        verdict, detail = classify(rc, out, timed_out)
        if verdict == "INFRA":                      # give the OS a moment and ask exactly once more
            time.sleep(2.0)
            try:
                r = subprocess.run([sys.executable, "-X", "utf8", str(p)], capture_output=True,
                                   text=True, timeout=a.timeout, cwd=str(ROOT))
                verdict, detail = classify(r.returncode, (r.stdout or "") + (r.stderr or ""), False)
            except subprocess.TimeoutExpired:
                verdict, detail = "TIMEOUT", "did not finish inside the budget (after an infra retry)"
        secs = time.time() - t0

        w = waivers.get(rel, {})
        waived = verdict in w.get("verdicts", [])
        tag = "waived" if waived else verdict
        print("%-9s %-58s %5.1fs  %s" % (tag, rel[-58:], secs, detail))
        print("           cited by: %s" % ", ".join(sorted(set(targets[p]))))
        if waived:
            print("           WAIVED %s — %s" % (w.get("dated", "?"), w.get("reason", "NO REASON")))
        elif verdict != "PASS":
            problems.append((rel, verdict, detail, sorted(set(targets[p]))))

    if problems:
        print("\nREFUSED — %d publicly-offered receipt(s) do not reproduce:" % len(problems))
        for rel, verdict, detail, posts in problems:
            print("  * [%s] %s\n      %s\n      cited by: %s" % (verdict, rel, detail, ", ".join(posts)))
        print("\nWe told readers these were runnable. Fix the artifact, or stop citing it.\n"
              "A NEEDS-RESOURCE result counts too: 'it needs our GPU' is a fact about the receipt.")
        return 1
    print("\nOK — every publicly-linked artifact still reproduces. Necessary, not sufficient: this says\n"
          "the receipt RUNS and reports its own verdict, not that the claim citing it is true.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
