"""Print a captured Bash output through the inspeximus context saver: saver_tail.py <output file> <intent>.

Under 5,000 bytes the saver returns the output unchanged. When the saver fails, the whole output is printed, so a
failure costs context and never hides output. Captures older than 2 days are removed.
"""
import os
import subprocess
import sys
import time

def main():
    path, intent = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "")
    raw = open(path, "rb").read()
    out = None
    if len(raw) >= 5000:
        # inspeximus 3.22.0 from PyPI. The embedder is the local bge-m3 by address, never by name.
        env = dict(os.environ, INSPEXIMUS_EMBED_URL="http://127.0.0.1:11434/v1/embeddings",
                   INSPEXIMUS_EMBED_MODEL="bge-m3", PYTHONIOENCODING="utf-8")
        args = [sys.executable, "-m", "inspeximus.context_saver", "--without-reranker", "hybrid", "--file", path]
        if intent:
            args += ["--intent", intent]
        try:
            r = subprocess.run(args, env=env, capture_output=True, timeout=90)
            if r.returncode == 0 and r.stdout.strip():
                out = r.stdout + ("\n[inspeximus-saver] %d bytes in, full output: %s\n" % (len(raw), path)).encode()
        except (OSError, subprocess.TimeoutExpired):
            pass
    sys.stdout.buffer.write(out if out is not None else raw)
    cutoff = time.time() - 2 * 86400
    d = os.path.dirname(path)
    for name in os.listdir(d):
        p = os.path.join(d, name)
        try:
            if os.path.getmtime(p) < cutoff:
                os.remove(p)
        except OSError:
            pass


if __name__ == "__main__":
    main()
