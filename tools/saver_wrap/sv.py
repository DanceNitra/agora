"""Run a command and print its output through the inspeximus context saver: sv.py [-i INTENT] -- <command>.

    python tools/saver_wrap/sv.py -i "which commit changed release.py" -- git log -n 300 --stat

The exit code is the command's own, so `&&` and `||` behave as usual. Output under 5,000 bytes is printed
unchanged. A larger one is printed as a digest, followed by the path of the full output for a follow-up read.
Captures live in ~/.claude/saver/out and are removed after 2 days.

Why a command and not a hook: a PreToolUse hook has to rewrite the command, and auto mode then reviews text that
differs from what runs, so the call is refused. A PostToolUse hook runs after the output is already in context,
so a digest added there costs context instead of saving it. Here the saver runs inside the command itself.
"""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(os.path.expanduser("~"), ".claude", "saver", "out")


def _sweep(cutoff):
    for name in os.listdir(OUT_DIR):
        p = os.path.join(OUT_DIR, name)
        try:
            if os.path.getmtime(p) < cutoff:
                os.remove(p)
        except OSError:
            pass


def main(argv):
    intent = ""
    if argv and argv[0] in ("-i", "--intent"):
        intent, argv = argv[1], argv[2:]
    if argv and argv[0] == "--":
        argv = argv[1:]
    if not argv:
        print(__doc__.strip().split("\n\n")[0], file=sys.stderr)
        return 2
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, "%s-%d.txt" % (time.strftime("%Y%m%d-%H%M%S"), os.getpid()))
    with open(path, "wb") as f:
        rc = subprocess.run(argv, stdout=f, stderr=subprocess.STDOUT).returncode
    tail = subprocess.run([sys.executable, os.path.join(HERE, "saver_tail.py"), path, intent],
                          capture_output=True)
    sys.stdout.buffer.write(tail.stdout)
    sys.stderr.buffer.write(tail.stderr)
    _sweep(time.time() - 2 * 86400)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
