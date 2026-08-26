"""Gate: the manuscript's data-availability line must be TRUE, and stay true.

A co-authored manuscript tells referees that all data, codes and scripts are at
github.com/DanceNitra/agora/tree/main/agora_output/hotrg_edrn. On 2026-08-20 that sentence was
false -- main was 317 commits behind the working branch and the public tree was missing
scan_guard.py entirely. It was fixed by publishing, and the fix was verified with ad-hoc shell
commands: a listing diff, a byte-size comparison, and 39 curl calls.

Ad-hoc verification is not a gate. The owner's standing rule (2026-07-26) is that the gate runs on
everything, as code rather than recall, and this file is the part of that rule I had skipped. It
exists so the property can be re-checked after any future commit, by anyone, in one command --
because the failure mode is not "we forgot to push once", it is "we push to the working branch for
weeks and the public tree silently ages while a manuscript points at it".

WHAT IT ASSERTS
  the public tree serving main is CONTENT-IDENTICAL to our working tree, for every path the
  manuscript's data-availability sentence covers.

Comparison is on LF-normalised content, not byte size: this repo is checked out with CRLF on
Windows, so a local `wc -c` is one byte per line larger than the blob GitHub serves. Comparing
sizes reports 5 false differences on an identical tree -- that is exactly the confusion this gate
removes.

CONTROLS
  C1 POSITIVE   a file known to be published must be found and must match. If the fetcher cannot
                confirm a file that is definitely there, it cannot be trusted to report absence.
  C2 NEGATIVE   a path that does not exist must 404. A checker that reports everything present
                is not checking.
  C3 THE FILE   scan_guard.py -- the one that was missing, and the guard that makes the
                manuscript's small-world section reproducible -- is asserted by name, so a
                regression on precisely this file cannot pass silently.
  C4 DENOM      the number of files compared is printed with the result.

Run:  python probes/gate_edrn_data_availability_is_live.py

THIS FILE IS NOT THE GATE. It recomputes figures against receipts, which is ONE check
inside VALIDATE. The gate is the SKILLS: verify-claims, stress-claim, humanizer, and
storm when the claim rests on literature. Owner, 2026-08-26, after I called a file like
this one "the gate" three times in a day: "ZAPIS SI TO NATVRDO A TEN TVOJ SKRIPT DAJ DO
HOVEN." tools/send_approved.py now refuses to publish without a receipt from each skill,
bound to the draft's bytes, so this file cannot stand in for them any more.
"""

import hashlib
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
RAW = "https://raw.githubusercontent.com/DanceNitra/agora/main/"
CITED_DIR = os.path.join("agora_output", "hotrg_edrn")
THE_FILE = "scan_guard.py"          # C3: the file that was absent

checks = []


def check(name, ok, detail=""):
    checks.append((name, bool(ok), detail))
    print(f"  {'OK  ' if ok else 'FAIL'}  {name:58s} {detail}")


def fetch(relpath):
    """-> (http_code, bytes or None)"""
    url = RAW + relpath.replace(os.sep, "/")
    r = subprocess.run(["curl", "-sL", "-w", "\n%{http_code}", url],
                       capture_output=True, timeout=90)
    out = r.stdout
    nl = out.rfind(b"\n")
    if nl < 0:
        return 0, None
    code = out[nl + 1:].decode(errors="replace").strip()
    return code, out[:nl]


def norm(b):
    """LF-normalised digest. CRLF in a Windows checkout is not a content difference."""
    return hashlib.sha256(b.replace(b"\r\n", b"\n")).hexdigest()


def local_set():
    """Every path the data-availability sentence covers."""
    paths = []
    d = os.path.join(REPO, CITED_DIR)
    for f in sorted(os.listdir(d)):
        p = os.path.join(d, f)
        if os.path.isfile(p) and not f.startswith("_") and f != ".gitignore":
            paths.append(os.path.join(CITED_DIR, f))
    for f in sorted(os.listdir(os.path.join(REPO, "probes"))):
        if f.startswith("edrn_") and (f.endswith(".py") or f.endswith(".result.json")):
            paths.append(os.path.join("probes", f))
    return paths


def main():
    paths = local_set()
    print(f"comparing {len(paths)} paths against the public tree serving main\n")

    print("CONTROLS")
    code, body = fetch(os.path.join(CITED_DIR, "hotrg.py"))
    c1 = code == "200" and body and norm(body) == norm(
        open(os.path.join(REPO, CITED_DIR, "hotrg.py"), "rb").read())
    check("C1 POSITIVE  a known-published file is found and matches", c1, f"HTTP {code}")
    code_n, _ = fetch(os.path.join(CITED_DIR, "this_file_does_not_exist_xyzzy.py"))
    check("C2 NEGATIVE  a nonexistent path 404s", code_n == "404", f"HTTP {code_n}")
    code_g, body_g = fetch(os.path.join(CITED_DIR, THE_FILE))
    c3 = code_g == "200" and body_g and norm(body_g) == norm(
        open(os.path.join(REPO, CITED_DIR, THE_FILE), "rb").read())
    check(f"C3 THE FILE  {THE_FILE} is live and matches", c3, f"HTTP {code_g}")

    print("\nTREE")
    missing, drifted, same = [], [], 0
    for rel in paths:
        code, body = fetch(rel)
        if code != "200" or body is None:
            missing.append((rel, code))
            continue
        local = open(os.path.join(REPO, rel), "rb").read()
        if norm(body) == norm(local):
            same += 1
        else:
            drifted.append(rel)
    check("every cited path is published", not missing,
          "all present" if not missing else f"{len(missing)} missing: "
          + ", ".join(f"{p} ({c})" for p, c in missing[:4]))
    check("every published path matches the working tree", not drifted,
          f"{same}/{len(paths)} identical" if not drifted
          else f"{len(drifted)} drifted: " + ", ".join(drifted[:4]))
    check(f"C4 DENOM     {len(paths)} paths compared, LF-normalised", True,
          "size comparison would report 5 false differences here (CRLF checkout)")

    n = len(checks)
    bad = [c for c in checks if not c[1]]
    print("\n" + "=" * 74)
    print(f"{n - len(bad)}/{n} checks pass")
    if bad:
        print("THE MANUSCRIPT'S DATA-AVAILABILITY SENTENCE IS NOT TRUE RIGHT NOW:")
        for name, _, detail in bad:
            print(f"   - {name}  {detail}")
        print("   Publish the missing paths to main before telling anyone to look there.")
    else:
        print("The data-availability sentence is true: the public tree is the working tree.")
    print("=" * 74)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
