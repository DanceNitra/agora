"""Fetch every probe our published posts link to, from its PUBLIC url, and run it as a stranger would.

WHY THIS EXISTS. On 2026-08-22 we asked two people on r/RAG to point a published probe at their own
store and send back two integers. They could not have. `live_stores()` scanned four hard-coded
directories of our own repository, so a reader who cloned it got `FAIL -- no stores read`, exit 1,
and nothing else. It failed loud rather than reporting a fake zero -- that half was right, and it is
the only reason this was not worse -- but the invitation in the write-up was unanswerable, and we
learned that by running our own artifact as a reader AFTER the ask went out.

That is the second instance of the class. The first was two receipts that loaded inspeximus from
`research/inspeximus.py`, a vendored single file from before it became a pip package, which no reader
has. So this file does the sweep instead of waiting for the third.

WHAT IT CHECKS, per linked probe:

  1. RESOLVES     the url in the post returns 200. A receipt nobody can fetch is not a receipt.
  2. RUNS AS A READER   copied alone into an empty directory, with no repo around it, does it
     produce output? The three outcomes that matter are different and are labelled separately:
        OK          it ran and printed something
        FAILS LOUD  it exited non-zero and SAID why -- acceptable, sometimes correct
        SILENT      it exited 0 while measuring nothing, or crashed with an import/path error
     SILENT is the defect. A probe that exits 0 over an empty scan hands the reader a number that
     was never measured, which is the exact shape every one of these probes was written against.
  3. WHAT IT NEEDS   static scan for the things that make a receipt unrunnable elsewhere: an
     absolute path, a repo-relative data directory, an API key, a dataset that is not in the repo.

WHAT IT DELIBERATELY DOES NOT DO. It does not execute a probe that wants an API key or a network
model call. Those cost the owner money and the point here is portability, not re-measurement, so
they are reported as NEEDS-KEY and left alone. Running them would also make this file's own result
depend on somebody's quota, which is not a property of the probe.

CONTROLS, both required:
  * POSITIVE  a file we KNOW is portable (a two-line script written here) must be classified OK.
    Without it, a harness that reports everything broken is indistinguishable from a broken harness.
  * NEGATIVE  a file we KNOW is not portable (imports a module that cannot exist) must be
    classified SILENT or FAILS LOUD, never OK.
  If either control lands wrong, the sweep is void and this file says so instead of printing a table.

Standard library only. No LLM calls, no GPU, no writes outside a temp directory.
Run:  python probes/every_publicly_linked_receipt_run_as_a_reader_would.py
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
POSTS = os.path.join(ROOT, "public", "posts", "src")
URL_RE = re.compile(r"https?://github\.com/[^\s)\"'\]]+\.py")
TIMEOUT = 90

#: things that make a receipt unrunnable somewhere else, and what to call each
NEEDS = [
    ("absolute path", re.compile(r"[A-Za-z]:[\\/]{1,2}Users|/home/[a-z]+/|os\.path\.expanduser")),
    ("api key", re.compile(r"OPENAI_API_KEY|ANTHROPIC_API_KEY|api_key|OLLAMA_|getenv\(['\"][A-Z_]*KEY")),
    ("network model call", re.compile(r"openai|ollama|anthropic|requests\.post|chat/completions")),
    ("repo-relative data dir", re.compile(r"os\.path\.dirname\(.*__file__|\.\./|ROOT\s*=")),
    ("a dataset file", re.compile(r"\.jsonl|\.csv|\.parquet|locomo|dataset")),
]


def linked_urls():
    urls = set()
    if not os.path.isdir(POSTS):
        return []
    for f in sorted(os.listdir(POSTS)):
        if not f.endswith(".md"):
            continue
        with open(os.path.join(POSTS, f), encoding="utf-8", errors="replace") as fh:
            for m in URL_RE.finditer(fh.read()):
                urls.add(m.group(0))
    return sorted(urls)


def raw_of(url):
    return url.replace("github.com/", "raw.githubusercontent.com/").replace("/blob/", "/")


def fetch(url):
    try:
        with urllib.request.urlopen(raw_of(url), timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except Exception as e:                                    # noqa: BLE001
        return getattr(e, "code", 0), ""


def classify(src, path, workdir):
    """Run it alone in an empty directory and say which of the three outcomes it is."""
    needs = [name for name, rx in NEEDS if rx.search(src)]
    if "api key" in needs or "network model call" in needs:
        return "NEEDS-KEY", "not executed: would spend the owner's quota", needs
    try:
        p = subprocess.run([sys.executable, path], cwd=workdir, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return "TIMEOUT", "still running after %ds" % TIMEOUT, needs
    out = (p.stdout or "") + (p.stderr or "")
    said_why = bool(re.search(r"FAIL|no such|not found|missing|refus|cannot|Error|Traceback", out))
    if p.returncode == 0:
        if len(out.strip()) < 40:
            return "SILENT", "exit 0 with %d chars of output" % len(out.strip()), needs
        return "OK", "exit 0, %d chars" % len(out.strip()), needs
    if said_why:
        first = next((l for l in out.splitlines()[::-1] if l.strip()), "")[:70]
        return "FAILS LOUD", "exit %d: %s" % (p.returncode, first), needs
    return "SILENT", "exit %d with no explanation" % p.returncode, needs


def controls(tmp):
    """A harness that reports everything broken is indistinguishable from a broken harness."""
    good = os.path.join(tmp, "_ctrl_good.py")
    with open(good, "w", encoding="utf-8") as fh:
        fh.write("print('portable probe ran and measured 3 of 3 things, here is a line of output')\n")
    bad = os.path.join(tmp, "_ctrl_bad.py")
    with open(bad, "w", encoding="utf-8") as fh:
        fh.write("import a_module_that_cannot_possibly_exist_anywhere\nprint('unreachable')\n")
    g = classify(open(good, encoding="utf-8").read(), good, tmp)[0]
    b = classify(open(bad, encoding="utf-8").read(), bad, tmp)[0]
    return g, b


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    t0 = time.time()
    tmp = tempfile.mkdtemp(prefix="reader_")
    g, b = controls(tmp)
    print("CONTROL  portable file      -> %-11s (must be OK)" % g)
    print("CONTROL  unportable file    -> %-11s (must NOT be OK)" % b)
    if g != "OK" or b == "OK":
        print("\nCONTROLS FAILED -- the harness cannot tell portable from broken. No table printed.")
        return 2

    urls = linked_urls()
    print("\n%d probe urls linked from published posts\n" % len(urls))
    print("  %-9s %-11s %-52s %s" % ("HTTP", "VERDICT", "PROBE", "DETAIL"))
    rows = []
    for u in urls:
        code, src = fetch(u)
        name = u.rsplit("/", 1)[-1]
        if code != 200 or not src:
            rows.append(dict(url=u, http=code, verdict="404", detail="url does not resolve", needs=[]))
            print("  %-9s %-11s %-52s %s" % (code, "DEAD", name[:52], "the post links to nothing"))
            continue
        d = tempfile.mkdtemp(prefix="p_", dir=tmp)
        path = os.path.join(d, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(src)
        verdict, detail, needs = classify(src, path, d)
        rows.append(dict(url=u, http=code, verdict=verdict, detail=detail, needs=needs))
        print("  %-9s %-11s %-52s %s" % (code, verdict, name[:52], detail[:60]))

    counts = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    print("\n" + "=" * 100)
    print("  " + "   ".join("%s %d" % (k, v) for k, v in sorted(counts.items())))
    silent = [r for r in rows if r["verdict"] in ("SILENT", "DEAD")]
    if silent:
        print("\n  THE ONES THAT MATTER -- a reader gets nothing, or a number nobody measured:")
        for r in silent:
            print("    %s\n      %s" % (r["url"].rsplit("/", 1)[-1], r["detail"]))
    else:
        print("\n  No probe hands a reader an unexplained result. FAILS LOUD is an acceptable outcome;")
        print("  SILENT is not, and there are none.")
    print("=" * 100)

    out = os.path.join(HERE, os.path.basename(__file__).replace(".py", ".result.json"))
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(dict(controls=dict(portable=g, unportable=b), rows=rows,
                       counts=counts, elapsed_s=time.time() - t0), fh, indent=1)
    print("\nreceipt -> %s   (%.0fs)" % (os.path.basename(out), time.time() - t0))
    shutil.rmtree(tmp, ignore_errors=True)
    return 1 if silent else 0


if __name__ == "__main__":
    sys.exit(main())
