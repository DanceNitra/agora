#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create the Zenodo deposition for the second EDRN manuscript — as a DRAFT, never published here.

This is a NEW record, not a version of 10.5281/zenodo.21393316. That DOI belongs to a different paper
("Charge and Spin Response of One-Dimensional Electron Delocalization Relation Networks", 16 July 2026),
which reports Prediction 1 as negated in its initial test and explicitly leaves the correct test
"pending". The present manuscript is that test. Attaching it as a version of the earlier record would
put two different papers under one DOI, which Zenodo cannot cleanly undo.

The script uploads the files and writes the metadata, then stops. Publishing mints a permanent DOI
under three real people's names, so that action stays with the owner: run with --publish only on his
word, and only after he has seen the draft URL this prints.
"""
import argparse
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request

API = "https://zenodo.org/api"
REPO = pathlib.Path(r"C:/Users/Danculus/AppData/Local/Temp/claude/"
                    r"C--Users-Danculus-agora/c5317a10-d6e1-4480-8deb-effafb6407b2/scratchpad/edrn/repo")
ENV = pathlib.Path(r"C:/Users/Danculus/agora/server/.env")
PRIOR_DOI = "10.5281/zenodo.21393316"

TITLE = ("Systematic numerical study of the spin-gap prefactor in a one-dimensional Mott insulator: "
         "defect response, boundary effect, and cross-sector conservation")

DESCRIPTION = """<p>A systematic DMRG study of the spin-gap prefactor <em>A</em> = &Delta;<sub>s</sub>&thinsp;&times;&thinsp;<em>L</em>
in the one-dimensional Hubbard model at half filling, testing how it responds to a single-bond defect,
to the boundary condition, and across the charge and spin sectors.</p>

<p>This work carries out the test that the companion paper
(<a href="https://doi.org/10.5281/zenodo.21393316">10.5281/zenodo.21393316</a>) identified as necessary
and left pending: on a linear chain the connectivity index <em>C</em> is a deterministic function of
<em>L</em>, so a correlation between <em>A</em> and <em>C</em> across chain lengths is a mathematical
inevitability rather than physics. Varying the lattice topology at fixed <em>L</em> instead separates
the two, and the result is a decoupling: across the defect scan <em>A</em> moves by a factor of 5.66 at
<em>L</em>&thinsp;=&thinsp;40 and 6.86 at <em>L</em>&thinsp;=&thinsp;60, while <em>C</em> spreads by
1.02% and 0.69% respectively.</p>

<p><strong>Convergence.</strong> Every point of the defect scan carries a bond-dimension check: all ten
points were recomputed with independent code at &chi; = 100, 200, 300, 400 in both spin sectors (80 DMRG
runs), and the energies extrapolated linearly in the discarded weight. The control reproduces the
published &chi;&thinsp;=&thinsp;100 value of <em>A</em> to six significant figures (5.469865 against
5.469862). The open chain proves to be already converged at &chi;&thinsp;=&thinsp;100 &mdash; the largest
bias is 1.0% &mdash; in contrast to the periodic ring, where the same check moved <em>A</em> from 0.47 to
3.19&thinsp;&plusmn;&thinsp;0.03 because the wrap bond is long-range for a matrix-product state.</p>

<p><strong>Reproducibility.</strong> The scripts and all 80 raw DMRG cells are public at
<a href="https://github.com/DanceNitra/edrn-appendix-fix">github.com/DanceNitra/edrn-appendix-fix</a>,
so every table can be re-derived without running a single sweep. Every appendix table is generated from
the data file that produced it, and the file is named in the caption.</p>

<p>The three authors reached the same conclusions by independent methods on one open dataset: DMRG
(Li), independent DMRG plus Bethe-ansatz anchors and the convergence analysis (Drahos), and blind
cross-framework verification with TAT (Sultanov).</p>"""

CREATORS = [
    {"name": "Li, Guanghao", "affiliation": "Independent Researcher, Hefei, China",
     "orcid": "0009-0000-2047-7517"},
    {"name": "Drahos, Rastislav", "affiliation": "Agora Scientific"},
    {"name": "Sultanov, Marat", "affiliation": "TAT-Defense"},
]

KEYWORDS = [
    "Density Matrix Renormalization Group", "Hubbard model", "Mott Insulator", "Spin Gap",
    "Spin-Charge Separation", "Kane-Fisher", "Boundary conformal field theory",
    "Bond-dimension convergence", "Cross-Sector Conservation", "Cross-Framework Verification",
    "Electron Delocalization Relation Network",
]

FILES = ["paper_full.pdf", "paper_full.tex"]


def token() -> str:
    m = re.search(r"^ZENODO_TOKEN=(.+)$", ENV.read_text(encoding="utf-8", errors="replace"), re.M)
    if not m:
        sys.exit("ZENODO_TOKEN not found in server/.env")
    return m.group(1).strip().strip('"').strip("'")


def call(tok, method, path, data=None, raw=None, ctype="application/json"):
    url = path if path.startswith("http") else API + path
    body = raw if raw is not None else (json.dumps(data).encode() if data is not None else None)
    req = urllib.request.Request(url, data=body, method=method,
                                 headers={"Authorization": f"Bearer {tok}", "Content-Type": ctype})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            txt = r.read().decode()
            return json.loads(txt) if txt else {}
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {url} -> {e.code}\n{e.read().decode()[:900]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true",
                    help="mint the DOI. Permanent. Owner's word only.")
    ap.add_argument("--deposition", help="reuse an existing draft id instead of creating one")
    args = ap.parse_args()
    tok = token()

    if args.deposition:
        dep = call(tok, "GET", f"/deposit/depositions/{args.deposition}")
    else:
        dep = call(tok, "POST", "/deposit/depositions", data={})
        print(f"created draft {dep['id']}")

    bucket = dep["links"]["bucket"]
    for name in FILES:
        p = REPO / name
        if not p.exists():
            sys.exit(f"missing file: {p}")
        call(tok, "PUT", f"{bucket}/{name}", raw=p.read_bytes(),
             ctype="application/octet-stream")
        print(f"uploaded {name} ({p.stat().st_size:,} bytes)")

    meta = {"metadata": {
        "upload_type": "publication", "publication_type": "preprint",
        "title": TITLE, "description": DESCRIPTION, "creators": CREATORS,
        "keywords": KEYWORDS, "license": "cc-by-4.0",
        "access_right": "open",
        "related_identifiers": [
            {"identifier": PRIOR_DOI, "relation": "isContinuedBy", "scheme": "doi"},
            {"identifier": "https://github.com/DanceNitra/edrn-appendix-fix",
             "relation": "isSupplementTo", "scheme": "url"},
            {"identifier": "https://github.com/luoxuejian000/edrn-dmrg-verification",
             "relation": "isSupplementTo", "scheme": "url"},
        ],
    }}
    dep = call(tok, "PUT", f"/deposit/depositions/{dep['id']}", data=meta)
    print("metadata written")
    print(f"\nDRAFT (private, editable, deletable): {dep['links']['html']}")
    print(f"reserved DOI: {dep.get('metadata', {}).get('prereserve_doi', {}).get('doi', '?')}")

    if args.publish:
        dep = call(tok, "POST", f"/deposit/depositions/{dep['id']}/actions/publish")
        print(f"\nPUBLISHED: {dep['doi_url']}")
    else:
        print("\nNot published. Re-run with --deposition <id> --publish to mint the DOI.")


if __name__ == "__main__":
    main()
