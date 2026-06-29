"""
publish_agentreceipts_pypi.py - build + upload agora-agent-receipts to PyPI.
Reads PYPI_TOKEN from server/.env; passes it to twine via env vars only (never on a command line / in
printed output). Re-run after bumping the version (agent-receipts/pyproject.toml) for a new release.

Usage:  python tools/publish_agentreceipts_pypi.py
"""
import os, re, sys, glob, shutil, subprocess

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(ROOT, "agent-receipts")


def _token():
    txt = open(os.path.join(ROOT, "server", ".env"), "rb").read().decode("utf-8", "replace")
    m = re.search(r'PYPI_TOKEN\s*=\s*"?(pypi-\S+)', txt)
    if not m:
        sys.exit("PYPI_TOKEN not found in server/.env")
    return m.group(1).strip().strip('"')


def main():
    tok = _token()
    for d in ("dist", "build"):
        shutil.rmtree(os.path.join(PKG, d), ignore_errors=True)
    for egg in glob.glob(os.path.join(PKG, "*.egg-info")):
        shutil.rmtree(egg, ignore_errors=True)

    print("building wheel + sdist ...")
    b = subprocess.run([sys.executable, "-m", "build"], cwd=PKG,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if b.returncode != 0:
        print(b.stdout[-1500:]); print(b.stderr[-1500:]); sys.exit("build failed")
    dists = glob.glob(os.path.join(PKG, "dist", "*"))
    print("built:", [os.path.basename(d) for d in dists])

    print("uploading to PyPI ...")
    env = dict(os.environ, TWINE_USERNAME="__token__", TWINE_PASSWORD=tok)
    u = subprocess.run([sys.executable, "-m", "twine", "upload", "--non-interactive"] + dists,
                       cwd=PKG, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(((u.stdout + "\n" + u.stderr).replace(tok, "***"))[-2000:])
    if u.returncode != 0:
        sys.exit("upload failed (see output above)")
    print("\nLIVE: https://pypi.org/project/agora-agent-receipts/   ->   pip install agora-agent-receipts")


if __name__ == "__main__":
    main()
