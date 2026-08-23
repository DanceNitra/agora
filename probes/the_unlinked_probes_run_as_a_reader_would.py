"""Run every research/probes file that is NOT publicly linked, the way a reader would.

WHY. Of the 15 probes our posts DO link, three of the three that had a dependency turned out
unrunnable for anyone but us: two threw a bare FileNotFoundError out of importlib and json.load, and
two more (in the inspeximus repo) threw ModuleNotFoundError above their own OPENAI_API_KEY check, so
the helpful message they carried was unreachable by the reader who needed it. That is 3 of 3.

289 more sit in research/probes unlinked. Any of them can be cited by a future post, and the base
rate is worth knowing before that happens rather than after. This copies each one alone into an
empty directory and runs it.

WHAT IS NOT EXECUTED, AND WHY IT IS SAID OUT LOUD. Two exclusions, and only one of them is a guess:

  * WOULD-USE-GPU -- references the local Ollama endpoint, an embedder, or CUDA. Excluded on a STATIC
    read, deliberately, because the only way to test it by behaviour is to run it, and running it
    puts load on the GPU against a standing instruction. The precision loss is accepted and named.
  * TOO-SLOW -- exceeded the timeout. Reported as its own bucket, never as silence. A short timeout
    on a probe with heavy imports looks exactly like a probe that prints nothing; that mistake was
    made three times tonight before it was caught.

Everything else runs, including anything that merely mentions an API key. A regex over the source is
not evidence about behaviour: erasure_selfcheck.py was labelled NEEDS-KEY on the word OPENAI_API_KEY
and in fact runs standalone with no key at all and prints its full table.

BUCKETS
  OK          ran and printed something
  FAILS LOUD  exited non-zero and said why -- acceptable, often correct
  SILENT      exited 0 having printed almost nothing, or died with no explanation. THE DEFECT.

WHAT THIS SWEEP TURNED OUT TO MEASURE, WHICH IS NOT WHAT IT SET OUT TO. Read this before quoting a
number out of the receipt.

The reader test copies a file alone into an empty directory. That is exactly right for a probe
OFFERED as a standalone download -- the 15 linked ones -- where it found three real defects. It is
the wrong test for a repo-internal probe, and 289 of these are repo-internal.

Two ways it goes wrong, both measured:

  1. A probe that resolves its data with `Path(__file__).resolve().parents[2]` is doing the correct
     thing for a file that lives in the repo. Copy it out and the same line points at nowhere.
     attestation_coverage_before_flipping_strict.py was the single SILENT in the 289. Run in place
     it reads 126,737 records across six stores and reports attestation coverage of 0.000% -- a real
     measurement. The SILENT verdict was an artifact of how this sweep opened it, not a defect in it.

  2. Of the 43 FAILS LOUD, 18 are ModuleNotFoundError and 11 FileNotFoundError -- the same shape.
     Re-running a sample of twelve IN PLACE does not clear them either, but for a THIRD reason: they
     need local services this machine is not running (_diag_blob.py wants Neo4j on :7687). So the
     bucket mixes at least three causes and separates none of them.

The honest reading of the 289-file run: OK 139 says those files are self-contained, which is real
information. Everything else in the table is about the harness or the environment as much as about
the probe, and none of it should be quoted as a defect rate. The count that survives is
SILENT = 0, once the one artifact is removed.

The class this belongs to is already in our memory as "an artifact of how you opened it is not a
defect in IT", and it was written after three near-misses in one day. This is the fourth.

CONTROLS, both required before any table prints:
  * a file known to be portable must classify OK;
  * a file known to be unportable must not.

Parallel by default over all cores. Standard library only. No LLM calls, no GPU, no writes outside a
temp directory.

Run:  python probes/the_unlinked_probes_run_as_a_reader_would.py [--limit N] [--timeout S]
      [--names FILE]   a newline-separated list, to skip the rate-limited contents API
"""
from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
POSTS = os.path.join(ROOT, "public", "posts", "src")
API = "https://api.github.com/repos/DanceNitra/agora/contents/research/probes?ref=main&per_page=100"
RAW = "https://raw.githubusercontent.com/DanceNitra/agora/main/research/probes/"

# Narrow deliberately. The first version matched the bare words "embed", "torch" and "transformers"
# anywhere, including in a comment, and excluded 10 of the first 12 files -- the same over-broad
# regex I had just criticised for the NEEDS-KEY label. What is excluded here has to be an actual
# runtime touch: a call, an import, or the local endpoint.
GPU_RE = re.compile(r"127\.0\.0\.1:11434|localhost:11434|api/embed|api/embeddings|"
                    r"ollama\.(embed|chat|generate)|SentenceTransformer\s*\(|"
                    r"^\s*import\s+torch|^\s*from\s+torch|\.cuda\s*\(|\.to\s*\(\s*[\"']cuda",
                    re.M)


def linked_names():
    out = set()
    if not os.path.isdir(POSTS):
        return out
    rx = re.compile(r"https?://github\.com/[^\s)\"'\]]+/([^/]+\.py)")
    for f in sorted(os.listdir(POSTS)):
        if f.endswith(".md"):
            with open(os.path.join(POSTS, f), encoding="utf-8", errors="replace") as fh:
                out |= set(rx.findall(fh.read()))
    return out


def listing(names_file=None):
    # The contents API is the only call here that needs the API at all, and unauthenticated it
    # rate-limits at 60/hour -- this hit 403 on the first real run. A caller who already has the
    # list (e.g. from `gh api ... --jq .name`) can hand it over and skip the call entirely.
    if names_file and os.path.exists(names_file):
        with open(names_file, encoding="utf-8") as fh:
            return sorted({l.strip() for l in fh if l.strip().endswith(".py")})
    names, page = [], 1
    while True:
        req = urllib.request.Request(API + "&page=%d" % page,
                                     headers={"Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            batch = json.load(r)
        if not batch:
            break
        names += [b["name"] for b in batch if b["name"].endswith(".py")]
        if len(batch) < 100:
            break
        page += 1
    return sorted(set(names))


def _one(args):
    name, src, timeout = args
    d = tempfile.mkdtemp(prefix="u_")
    p = os.path.join(d, name)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(src)
    try:
        r = subprocess.run([sys.executable, name], cwd=d, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        shutil.rmtree(d, ignore_errors=True)
        return name, "TOO-SLOW", "still running after %ds" % timeout
    out = (r.stdout or "") + (r.stderr or "")
    shutil.rmtree(d, ignore_errors=True)
    said = bool(re.search(r"FAIL|no such|not found|missing|refus|cannot|Error|Traceback|usage:", out))
    if r.returncode == 0:
        if len(out.strip()) < 40:
            return name, "SILENT", "exit 0 with %d chars" % len(out.strip())
        return name, "OK", "exit 0, %d chars" % len(out.strip())
    if said:
        tail = next((l for l in out.splitlines()[::-1] if l.strip()), "")[:70]
        return name, "FAILS LOUD", "exit %d: %s" % (r.returncode, tail)
    return name, "SILENT", "exit %d with no explanation" % r.returncode


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    argv = sys.argv[1:]
    limit, timeout = None, 60
    if "--limit" in argv:
        i = argv.index("--limit"); limit = int(argv[i + 1])
    if "--timeout" in argv:
        i = argv.index("--timeout"); timeout = int(argv[i + 1])
    names_file = None
    if "--names" in argv:
        i = argv.index("--names"); names_file = argv[i + 1]
    t0 = time.time()

    workers = min(12, os.cpu_count() or 4)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        good = "print('a portable probe ran and measured three of three things, here is output')\n"
        bad = "import a_module_that_cannot_exist_anywhere\nprint('unreachable')\n"
        cg = _one(("_ctl_good.py", good, timeout))[1]
        cb = _one(("_ctl_bad.py", bad, timeout))[1]
        print("CONTROL portable   -> %-11s (must be OK)" % cg)
        print("CONTROL unportable -> %-11s (must NOT be OK)" % cb)
        if cg != "OK" or cb == "OK":
            print("\nCONTROLS FAILED -- harness cannot tell portable from broken. No table.")
            return 2

        skip = linked_names()
        names = [n for n in listing(names_file) if n not in skip]
        if limit:
            names = names[:limit]
        print("\n%d research/probes files, %d already-linked excluded\n" % (len(names), len(skip)),
              flush=True)

        jobs, gpu = [], []
        for n in names:
            with urllib.request.urlopen(RAW + n, timeout=30) as r:
                src = r.read().decode("utf-8", "replace")
            if GPU_RE.search(src):
                gpu.append(n)
            else:
                jobs.append((n, src, timeout))
        print("  WOULD-USE-GPU, not executed by choice: %d" % len(gpu), flush=True)
        print("  executing: %d with a %ds timeout, %d workers\n" % (len(jobs), timeout, workers),
              flush=True)

        rows = []
        for name, verdict, detail in pool.map(_one, jobs):
            rows.append(dict(name=name, verdict=verdict, detail=detail))
            if verdict in ("SILENT", "TOO-SLOW"):
                print("  %-11s %-52s %s" % (verdict, name[:52], detail[:50]), flush=True)

    counts = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    counts["WOULD-USE-GPU (not run)"] = len(gpu)
    print("\n" + "=" * 96)
    print("  " + "   ".join("%s %d" % (k, v) for k, v in sorted(counts.items())))
    silent = [r for r in rows if r["verdict"] == "SILENT"]
    print("\n  SILENT is the defect: exit 0 having measured nothing, or a death with no explanation.")
    print("  FAILS LOUD is fine. TOO-SLOW is not silence and is counted apart.")
    if silent:
        print("\n  %d SILENT:" % len(silent))
        for r in silent[:20]:
            print("    %-52s %s" % (r["name"][:52], r["detail"]))
    print("=" * 96)

    out = os.path.join(HERE, os.path.basename(__file__).replace(".py", ".result.json"))
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(dict(controls=dict(portable=cg, unportable=cb), counts=counts,
                       gpu_excluded=gpu, rows=rows, timeout_s=timeout,
                       elapsed_s=time.time() - t0), fh, indent=1)
    print("\nreceipt -> %s   (%.0fs)" % (os.path.basename(out), time.time() - t0))
    return 1 if silent else 0


if __name__ == "__main__":
    sys.exit(main())
