"""Run the local equivalent of the hermes-agent catalog gate `pinned-source-validate`.

The job clones a catalog entry's repo at the pinned sha and runs `hermes plugins validate`
on the entry's subdir. It fires only on upstream branches, so a fork head never gets it.
This probe runs the same command, prints its own progress, and carries a control: the same
plugin directory with the manifest's `name` line removed must be refused.

    python probes/hermes_catalog_pinned_source_gate.py

The Hermes that runs the command is the installed CLI, which is NOT the Hermes the job
builds from the pull request checkout. The receipt records the version, because the same
command on a different host is a different measurement.
"""
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time

REPO = "https://github.com/DanceNitra/inspeximus"
SHA = "2a4141cf89e0bbe5bcca9d2e167df41477ef5463"
SUBDIR = "integrations/hermes-plugin-inspeximus"
HERMES = os.environ.get(
    "HERMES_BIN",
    os.path.join(os.path.expanduser("~"), "AppData", "Local", "hermes", "bin", "hermes.exe"),
)
WORK = pathlib.Path(__file__).resolve().parent / "_hermes_gate2_work"
OUT = pathlib.Path(__file__).with_suffix(".result.json")

_T0 = time.time()


def say(msg):
    print("[%5.1fs] %s" % (time.time() - _T0, msg), flush=True)


def rmtree_force(path):
    """Git packs land read-only, and shutil.rmtree then raises WinError 5 on Windows."""
    def onerror(func, target, exc):
        try:
            os.chmod(target, 0o700)
            func(target)
        except OSError:
            pass

    try:
        shutil.rmtree(path, onexc=onerror)          # 3.12+
    except TypeError:
        shutil.rmtree(path, onerror=lambda f, t, e: onerror(f, t, e))


def run(args, timeout):
    # UTF-8 both ways. The console here is cp1250, and a check line reads `✓ name — detail`:
    # decoded with the console codec the tick and the dash arrive mangled, the counter below matches
    # nothing, and the receipt says 0 checks over a validation that printed 13. That happened once.
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    p = subprocess.run(args, capture_output=True, timeout=timeout, env=env)
    raw = (p.stdout or b"") + (p.stderr or b"")
    return p.returncode, raw.decode("utf-8", "replace")


def hermes_version():
    _, out = run([HERMES, "--version"], 120)
    m = re.search(r"v(\d+\.\d+\.\d+)", out)
    return m.group(1) if m else "unknown"


def validate(plugin_dir, install_deps):
    args = [HERMES, "plugins", "validate"]
    if install_deps:
        args.append("--install-deps")
    args.append(str(plugin_dir))
    _, out = run(args, 900)
    verdict = "none"
    for line in out.splitlines():
        s = line.strip()
        if s in ("Validation passed.", "Validation failed."):
            verdict = s.rstrip(".")
    return verdict, out


def main():
    if not os.path.exists(HERMES):
        say("no hermes CLI at %s" % HERMES)
        return 2
    if WORK.exists():
        rmtree_force(WORK)
    WORK.mkdir(parents=True)
    clone = WORK / "clone"

    ver = hermes_version()
    say("hermes CLI %s" % ver)

    say("cloning %s" % REPO)
    rc, out = run(["git", "clone", "--quiet", REPO, str(clone)], 1200)
    if rc != 0:
        say("clone failed: %s" % out.strip()[:200])
        return 1

    rc, out = run(["git", "-C", str(clone), "cat-file", "-t", SHA], 120)
    if out.strip() != "commit":
        say("pinned sha is not a commit in that repo")
        return 1
    run(["git", "-C", str(clone), "checkout", "--quiet", "--detach", SHA], 300)
    rc, head = run(["git", "-C", str(clone), "rev-parse", "HEAD"], 120)
    head = head.strip()
    if head != SHA:
        say("checkout landed on %s, not the pin" % head)
        return 1
    say("checked out the pin")

    plugin_dir = clone / SUBDIR
    say("validating the pinned plugin directory")
    verdict, out = validate(plugin_dir, install_deps=True)
    checks = len(re.findall(r"^\s*✓ ", out, re.M))
    deps = 0
    m = re.search(r"python dependencies — (\d+) installable", out)
    if m:
        deps = int(m.group(1))
    say("%s, %d checks" % (verdict, checks))
    if verdict == "Validation passed" and checks == 0:
        # A pass with no counted checks means the counter stopped matching, not that the gate ran
        # empty. Refuse rather than write a receipt whose figure a comment would quote.
        say("the check counter matched nothing; the instrument is the defect")
        return 1

    say("control: the same directory with the manifest name removed")
    ctl = WORK / "control"
    shutil.copytree(plugin_dir, ctl)
    manifest = ctl / "plugin.yaml"
    text = manifest.read_text(encoding="utf-8")
    manifest.write_text(re.sub(r"(?m)^name:.*$", "", text, count=1), encoding="utf-8")
    ctl_verdict, _ = validate(ctl, install_deps=False)
    say("control: %s" % ctl_verdict)

    receipt = {
        "probe": pathlib.Path(__file__).name,
        "repo": REPO,
        "pinned_sha": SHA,
        "subdir": SUBDIR,
        "hermes_version": ver,
        "hermes_built_from_pr_checkout": False,
        "attestation_verified": False,
        "verdict": verdict,
        "checks_passed": checks,
        "python_dependencies": deps,
        "control_verdict": ctl_verdict,
    }
    OUT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    say("receipt -> %s" % OUT)

    ok = verdict == "Validation passed" and ctl_verdict == "Validation failed"
    print("VERDICT: %s" % ("GATE2_PASSES_WITH_A_WORKING_CONTROL" if ok else "INCONCLUSIVE"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
