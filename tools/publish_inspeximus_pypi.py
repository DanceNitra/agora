"""
publish_inspeximus_pypi.py - build + upload inspeximus to PyPI.
Reads PYPI_TOKEN from server/.env; passes it to twine via env vars only (never on a command line / in
printed output). Re-run after bumping the version for a new release.

BUILDS FROM THE CANONICAL REPO (../inspeximus-repo), not agora/inspeximus_pypi. Until 2026-07-19 this script pointed
at agora/inspeximus_pypi, a staging copy that stopped being the release source after 0.7.19 while every actual
release (1.9.x .. 1.17.0) came out of inspeximus-repo. Its pyproject was still pinned at 0.7.19, so this script
built a 0.7.19 artifact that PyPI then rejected as a duplicate - the release tool had quietly been dead for
months, and a release made "by hand" instead is how inspeximus_pypi and inspeximus-repo drifted apart in the first
place. Override the location with INSPEXIMUS_REPO=<path> if the checkout lives somewhere else.

Usage:  python tools/publish_inspeximus_pypi.py
"""
import os, re, sys, glob, json, shutil, subprocess, urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.environ.get("INSPEXIMUS_REPO") or os.path.join(os.path.dirname(ROOT), "inspeximus-repo")


def _token():
    txt = open(os.path.join(ROOT, "server", ".env"), "rb").read().decode("utf-8", "replace")
    m = re.search(r'PYPI_TOKEN\s*=\s*"?(pypi-\S+)', txt)
    if not m:
        sys.exit("PYPI_TOKEN not found in server/.env")
    return m.group(1).strip().strip('"')


def _version():
    """The version about to be published, cross-checked against the library's own __version__.

    These two have drifted before (the package said one thing, `inspeximus.__version__` another), which ships a
    wheel whose reported version is a lie. Refuse rather than publish a mismatch."""
    pyproject = open(os.path.join(PKG, "pyproject.toml"), encoding="utf-8").read()
    m = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.M)
    if not m:
        sys.exit(f"no version in {PKG}/pyproject.toml")
    v = m.group(1)
    src = open(os.path.join(PKG, "inspeximus", "inspeximus.py"), encoding="utf-8").read()
    m2 = re.search(r'^__version__\s*=\s*"([^"]+)"', src, re.M)
    if m2 and m2.group(1) != v:
        sys.exit(f"version mismatch: pyproject says {v}, inspeximus/inspeximus.py says {m2.group(1)} - bump both")
    return v


def _already_on_pypi(v):
    try:
        d = json.load(urllib.request.urlopen("https://pypi.org/pypi/inspeximus/json", timeout=20))
        return v in d.get("releases", {}), d["info"]["version"]
    except Exception:
        return False, "?"      # network trouble: don't block the release on it


def main():
    if not os.path.isdir(PKG):
        sys.exit(f"package dir not found: {PKG}  (set INSPEXIMUS_REPO=<path to the inspeximus checkout>)")
    v = _version()
    taken, live = _already_on_pypi(v)
    print(f"publishing inspeximus {v} from {PKG}   (PyPI currently: {live})")
    if taken:
        sys.exit(f"{v} is already on PyPI - PyPI never allows re-uploading a version. Bump first.")

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
    # A stale dist/ from an earlier release would otherwise be re-uploaded alongside the new one.
    stale = [d for d in dists if v not in os.path.basename(d)]
    if stale or not dists:
        sys.exit(f"refusing to upload: dist/ does not hold exactly {v} "
                 f"(unexpected: {[os.path.basename(d) for d in stale]})")

    print("uploading to PyPI ...")
    env = dict(os.environ, TWINE_USERNAME="__token__", TWINE_PASSWORD=tok)
    u = subprocess.run([sys.executable, "-m", "twine", "upload", "--non-interactive"] + dists,
                       cwd=PKG, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(((u.stdout + "\n" + u.stderr).replace(tok, "***"))[-2000:])
    if u.returncode != 0:
        sys.exit("upload failed (see output above)")
    print(f"\nLIVE: https://pypi.org/project/inspeximus/{v}/   ->   pip install inspeximus")


if __name__ == "__main__":
    main()
