"""Wire the flagship product into the Organization entity that answer engines read for disambiguation.

The homepage links inspeximus three ways -- PyPI, its GitHub repo, its own Pages site -- and the
Organization JSON-LD `sameAs` named none of them. `sameAs` is the property a search or answer engine
uses to decide that two mentions are the same entity, and "Agora" is an extremely generic name: a web
search for it returns Hungarian cultural centres, not this project. The distinctive, independently
citable identity here is inspeximus (a live PyPI package, its own repo, its own site) and it was absent
from the only machine-readable place that says "these are all us".

Idempotent: adds only what is missing, preserves order, touches every document that carries an
Organization node -- English and Slovak alike, since the Slovak pages carry the same entity.
"""
from __future__ import annotations

import json
import pathlib
import sys

from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = pathlib.Path(__file__).resolve().parent.parent

#: verified live this session: PyPI 200 (version 1.86.0), repo 200 (public), Pages site 200
ADD = [
    "https://github.com/DanceNitra/inspeximus",
    "https://pypi.org/project/inspeximus/",
    "https://dancenitra.github.io/inspeximus/",
    "https://dancenitra.github.io/",
]


def main() -> int:
    pages = [ROOT / "index.html"]
    pages += sorted((ROOT / "public").rglob("*.html"))
    if (ROOT / "sk").exists():
        pages += sorted((ROOT / "sk").rglob("*.html"))

    touched = 0
    for p in pages:
        html = p.read_text(encoding="utf-8", errors="replace")
        if '"Organization"' not in html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        changed = False
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
            except Exception:
                continue

            def walk(node):
                nonlocal changed
                if isinstance(node, list):
                    for x in node:
                        walk(x)
                elif isinstance(node, dict):
                    # only the Organization that already declares sameAs -- the per-post publisher stubs
                    # carry no sameAs and giving them one would duplicate the entity, not strengthen it
                    if node.get("@type") == "Organization" and isinstance(node.get("sameAs"), list):
                        for u in ADD:
                            if u not in node["sameAs"]:
                                node["sameAs"].append(u)
                                changed = True
                    for v in node.values():
                        walk(v)

            walk(data)
            if changed:
                script.string = json.dumps(data, ensure_ascii=False)
        if changed:
            p.write_text(str(soup), encoding="utf-8")
            touched += 1
            print(f"  {p.relative_to(ROOT).as_posix()}")
    print(f"\n{touched} document(s) updated" if touched else "\nnothing to add (already present)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
