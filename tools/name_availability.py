#!/usr/bin/env python3
"""Check a candidate product name against the registries that can actually block us.

A web search tells you whether a name is FAMOUS. It does not tell you whether it is FREE. These are
different questions and only the second one blocks a release, so every candidate a human or an agent
proposes has to come through here before it is taken seriously.

Checked, in order of how badly each one can hurt:
  PyPI    — a taken name is fatal; PyPI does not rename or transfer on request.
  npm     — needed later for any JS client; a taken name forces a scope.
  GitHub  — the repo name AND the org/user name (an org squatted by someone else costs us the URL).
  crates  — cheap to check, and a Rust crate with our name muddies search results.
  DNS     — .com/.dev/.io resolving at all is treated as taken; NXDOMAIN is the only clean signal.

Usage:  python tools/name_availability.py aster ratchet keelson ...
Exit code is 0 always — this reports, it does not gate.
"""
from __future__ import annotations

import json
import socket
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

UA = {"User-Agent": "name-availability-check/1.0"}
TIMEOUT = 10


def _head_ok(url: str) -> bool | None:
    """True = exists, False = free, None = could not tell (never guess on a None)."""
    req = urllib.request.Request(url, headers=UA, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status == 200
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        return None
    except Exception:
        return None


def pypi(name: str) -> bool | None:
    return _head_ok(f"https://pypi.org/pypi/{name}/json")


def npm(name: str) -> bool | None:
    return _head_ok(f"https://registry.npmjs.org/{name}")


def crates(name: str) -> bool | None:
    return _head_ok(f"https://crates.io/api/v1/crates/{name}")


def github_owner(name: str) -> bool | None:
    return _head_ok(f"https://api.github.com/users/{name}")


def github_repos(name: str) -> tuple[int | None, str]:
    """How many repos are literally named this, and the most-starred one — the collision we care
    about is not 'does the name exist' but 'would we be the obvious result for it'."""
    url = (f"https://api.github.com/search/repositories?q={name}+in:name&sort=stars&per_page=1")
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            d = json.loads(r.read().decode())
        n = d.get("total_count")
        items = d.get("items") or []
        top = ""
        if items:
            it = items[0]
            top = f"{it['full_name']} ({it['stargazers_count']}*)"
        return n, top
    except Exception:
        return None, "?"


def dns(name: str, tld: str) -> bool | None:
    try:
        socket.getaddrinfo(f"{name}.{tld}", None)
        return True
    except socket.gaierror:
        return False
    except Exception:
        return None


def mark(v: bool | None) -> str:
    return "TAKEN" if v is True else ("free" if v is False else "?")


def check(name: str) -> dict:
    n = name.lower()
    with ThreadPoolExecutor(max_workers=8) as ex:
        f = {
            "pypi": ex.submit(pypi, n),
            "npm": ex.submit(npm, n),
            "crates": ex.submit(crates, n),
            "gh_owner": ex.submit(github_owner, n),
            "com": ex.submit(dns, n, "com"),
            "dev": ex.submit(dns, n, "dev"),
            "io": ex.submit(dns, n, "io"),
            "repos": ex.submit(github_repos, n),
        }
        out = {k: v.result() for k, v in f.items()}
    out["name"] = n
    return out


def main() -> None:
    names = sys.argv[1:]
    if not names:
        print(__doc__)
        return
    rows = [check(n) for n in names]
    hdr = f"{'name':<12} {'pypi':<6} {'npm':<6} {'crates':<7} {'gh-user':<8} " \
          f"{'.com':<6} {'.dev':<6} {'.io':<6} gh-repos-named-this"
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        n_repos, top = r["repos"]
        print(f"{r['name']:<12} {mark(r['pypi']):<6} {mark(r['npm']):<6} {mark(r['crates']):<7} "
              f"{mark(r['gh_owner']):<8} {mark(r['com']):<6} {mark(r['dev']):<6} "
              f"{mark(r['io']):<6} {n_repos if n_repos is not None else '?'}"
              + (f"  top: {top}" if top else ""))
    print("\n'?' means the check could not complete — treat it as unknown, never as free.")
    print("A domain that resolves is treated as taken; only NXDOMAIN is a clean signal.")


if __name__ == "__main__":
    main()
