"""Run the Chroma residue probe against several chromadb releases, each in its own environment.

WHY A MATRIX. A single version answers nothing publishable. chroma-core/chroma#3793 was closed as fixed
by PR #4884 (June 2025); a user replied in July 2025 that it persisted on 1.0.15. The question a reader
actually has is whether it is true of the version they are running today, so the answer has to be a
trajectory across releases rather than one reading.

Each version gets a fresh virtual environment, because a package installed over another leaves the old
one's files behind and the version under test would not be the version that runs.

Run: python probes/chroma_residue_version_matrix.py [version ...]
Writes: chroma_residue_version_matrix.result.json beside this file.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROBE = os.path.join(HERE, os.environ.get(
    "MATRIX_PROBE", "does_a_deleted_document_survive_in_chromas_files.py"))
DEFAULT_VERSIONS = ["1.0.15", "1.1.1", "1.5.9"]

RUNNER = r'''
import json, sys
sys.path.insert(0, r"{here}")
import importlib.util
spec = importlib.util.spec_from_file_location("probe", r"{probe}")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
print("___RESULT___" + json.dumps(mod.run()))
'''


def run_one(version: str) -> dict:
    venv = tempfile.mkdtemp(prefix="chromaenv_")
    t0 = time.time()
    subprocess.run([sys.executable, "-m", "venv", venv], check=True, capture_output=True)
    # Resolve the interpreter AFTER the environment exists. Computing it first tested a directory that
    # had not been created yet, so the Windows branch always failed its own check and fell through to a
    # POSIX path that is not there: FileNotFoundError, from a probe that had installed nothing.
    py = os.path.join(venv, "Scripts", "python.exe")
    if not os.path.exists(py):
        py = os.path.join(venv, "bin", "python")
    if not os.path.exists(py):
        return {"version": version, "error": "no interpreter in the new environment at " + venv}
    inst = subprocess.run([py, "-m", "pip", "install", "--quiet", "chromadb==" + version],
                          capture_output=True, text=True)
    if inst.returncode != 0:
        return {"version": version, "error": "install failed",
                "detail": (inst.stderr or "")[-600:], "seconds": round(time.time() - t0, 1)}
    script = RUNNER.format(here=HERE.replace("\\", "/"), probe=PROBE.replace("\\", "/"))
    env = dict(os.environ)
    out = subprocess.run([py, "-c", script], capture_output=True, text=True, timeout=1800,
                         encoding="utf-8", errors="replace", env=env)
    for line in (out.stdout or "").splitlines():
        if line.startswith("___RESULT___"):
            res = json.loads(line[len("___RESULT___"):])
            res["install_seconds"] = round(time.time() - t0, 1)
            return res
    return {"version": version, "error": "probe produced no result",
            "stdout": (out.stdout or "")[-800:], "stderr": (out.stderr or "")[-800:]}


def main() -> int:
    versions = sys.argv[1:] or DEFAULT_VERSIONS
    rows = []
    for v in versions:
        print("=== chromadb %s ===" % v, flush=True)
        r = run_one(v)
        rows.append(r)
        print("   verdict: %s   problems: %s" % (r.get("verdict", r.get("error")), r.get("problems")),
              flush=True)
    out = os.path.join(HERE, os.environ.get("MATRIX_OUT",
                                            "chroma_residue_version_matrix.result.json"))
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"measured_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "rows": rows}, fh, indent=2, ensure_ascii=False)
    print("\nwrote", out)
    for r in rows:
        s = r.get("summary") or {}
        print("  %-8s %-24s live=%s vacuum_survives=%s"
              % (r.get("chromadb_version", r.get("version")), r.get("verdict", r.get("error")),
                 len(s.get("live_rows") or []), s.get("survives_vacuum")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
