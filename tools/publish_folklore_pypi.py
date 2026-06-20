"""
publish_folklore_pypi.py - build and upload the folklore-index package to PyPI.
Reads PYPI_TOKEN from server/.env and passes it to twine via env vars (TWINE_USERNAME=__token__,
TWINE_PASSWORD=<token>) - the token never appears on a command line or in printed output.
Re-run after `python tools/build_folklore_index.py` to ship a new version (bump the version first).

Usage:  python tools/publish_folklore_pypi.py
"""
import os, re, sys, glob, shutil, subprocess

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # twine output has unicode; console is cp1250
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(ROOT, "agora_output", "folklore_index", "pypi")


def _token():
    txt = open(os.path.join(ROOT, "server", ".env"), "rb").read().decode("utf-8", "replace")
    m = re.search(r'PYPI_TOKEN\s*=\s*"?(pypi-\S+)', txt)
    if not m:
        sys.exit("PYPI_TOKEN not found in server/.env")
    return m.group(1).strip().strip('"')


def main():
    tok = _token()
    # clean any prior build outputs
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
    # print output but scrub any accidental token echo
    out = (u.stdout + "\n" + u.stderr).replace(tok, "***")
    print(out[-2000:])
    if u.returncode != 0:
        sys.exit("upload failed (see output above)")
    print("\nLIVE: https://pypi.org/project/folklore-index/   ->   pip install folklore-index")


if __name__ == "__main__":
    main()
