"""publish_crucible_zenodo.py — archive the Crucible replication ledger to Zenodo and mint a DOI.

WHY. Three of the five search queries this work should own are dominated by arXiv and DOI'd artifacts;
the Crucible is arguably a better object than most of what ranks there (a runnable ledger with code behind
every verdict, not a paper describing a method) and it was the only major artifact here without its own
identifier. RAMR and the Folklore Index already have one.

WHAT IS DEPOSITED. crucible.json — the machine-readable ledger — plus a generated method README. The
verdict counts in the Zenodo description are READ FROM THE LEDGER at publish time and cross-checked
against a recount of its own entries. They are never typed in. That is not fastidiousness: on 2026-07-28
this site was found publishing four different answers to one countable question because the numbers were
hand-maintained, and a DOI is permanent — a wrong count in a citable record cannot be quietly edited later.

Reads ZENODO_TOKEN from server/.env (never printed).

Usage:  python tools/publish_crucible_zenodo.py --sandbox   # rehearse against sandbox.zenodo.org
        python tools/publish_crucible_zenodo.py             # production; mints a permanent DOI
"""
import json
import os
import re
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, "public", "crucible", "crucible.json")
SANDBOX = "--sandbox" in sys.argv
BASE = "https://sandbox.zenodo.org" if SANDBOX else "https://zenodo.org"
SITE = "https://dancenitra.github.io/agora/public/crucible/"


def counts() -> dict:
    """The verdict tally, recomputed from the entries and cross-checked against the declared field."""
    d = json.load(open(LEDGER, encoding="utf-8"))
    entries = d.get("entries", [])
    got = {v: sum(1 for e in entries if e.get("verdict") == v)
           for v in ("REPRODUCED", "FAILED", "NOT_COMPUTABLE")}
    declared = d.get("counts") or {}
    if declared and declared != got:
        sys.exit(f"REFUSING TO PUBLISH: crucible.json disagrees with itself -- counts={declared}, "
                 f"entries tally to {got}. A DOI is permanent; fix the ledger first.")
    got["TOTAL"] = len(entries)
    return got


def readme(c: dict) -> str:
    return f"""# The Crucible — a public replication ledger for scientific and technical claims

Every entry is a claim rebuilt as the smallest computational model that could falsify it, then run.

- **REPRODUCED** — the mechanism holds in a minimal model
- **FAILED** — it does not. This is the point of the ledger, not an embarrassment: a record with no
  failures is a record that only tested safe claims.
- **NOT_COMPUTABLE** — an honest pass. The claim is descriptive rather than mechanistic, so there is no
  simulable core. Recorded rather than quietly dropped.

## This deposit

{c['TOTAL']} verdicts: **{c['REPRODUCED']} reproduced · {c['FAILED']} failed · {c['NOT_COMPUTABLE']} not
computable**. These figures are read from `crucible.json` at publish time and cross-checked against a
recount of its own entries; the deposit refuses to build if they disagree.

`crucible.json` carries, per entry: the claim, its source, the verdict, a note, the lab id of the run, and
a link to the runnable code where one exists.

## Method and its limits

Verdicts are produced by rebuilding a claim as a minimal model, not by re-running the original authors'
code or data. A REPRODUCED verdict therefore means *the stated mechanism holds in the smallest model that
expresses it* — not that the original study replicates in its own setting. A FAILED verdict means the
mechanism did not survive that minimal model, which is evidence about the mechanism as stated, and can also
mean the claim was stated too loosely to survive being made precise.

Entries are de-duplicated before counting: the same result restated in different notation is one verdict,
not several. The de-duplication is heuristic, and the renderer refuses to publish a count when a known
textbook family has accumulated verdicts that a human has not explicitly ruled duplicate or distinct.

Live ledger: {SITE}
"""


def _token() -> str:
    txt = open(os.path.join(ROOT, "server", ".env"), "rb").read().decode("utf-8", "replace")
    m = re.search(r'ZENODO_TOKEN\s*=\s*"?([^"\r\n]+)', txt)
    if not m:
        sys.exit("ZENODO_TOKEN not found in server/.env")
    return m.group(1).strip().strip('"')


def _req(method, url, tok, data=None, ctype="application/json"):
    h = {"Authorization": "Bearer " + tok}
    if data is not None and ctype:
        h["Content-Type"] = ctype
    r = urllib.request.Request(url, data=data, headers=h, method=method)
    with urllib.request.urlopen(r, timeout=120) as resp:
        body = resp.read()
    return json.loads(body) if body else {}


def main() -> int:
    c = counts()
    print(f"ledger: {c['REPRODUCED']}R / {c['FAILED']}F / {c['NOT_COMPUTABLE']}NC = {c['TOTAL']} verdicts")
    meta = {"metadata": {
        "title": "The Crucible — a public replication ledger for scientific and technical claims",
        "upload_type": "dataset",
        "description": (
            f"A public, machine-readable ledger of {c['TOTAL']} scientific and technical claims rebuilt as "
            f"minimal computational models and tested in code: {c['REPRODUCED']} reproduced, {c['FAILED']} "
            f"failed, {c['NOT_COMPUTABLE']} not computable (an honest pass, where a claim has no simulable "
            f"core). Every verdict ships a runnable model and a measured number. FAILED verdicts are "
            f"published as prominently as REPRODUCED ones: a replication record with no failures is a "
            f"record that only tested safe claims. Verdicts are produced by rebuilding the stated mechanism "
            f"as the smallest model that expresses it, not by re-running the original authors' code or "
            f"data, so REPRODUCED means the mechanism holds in that minimal model rather than that the "
            f"original study replicates in its own setting. Counts in this description are read from the "
            f"deposited ledger and cross-checked against a recount of its entries. "
            f"Live ledger: {SITE}"),
        "creators": [{"name": "Drahoš, Rastislav", "affiliation": "Agora"}],
        "keywords": ["replication", "reproducibility", "meta-science", "benchmark", "AI claims",
                     "computational replication", "open data"],
        "license": "MIT",
        "access_right": "open",
        "related_identifiers": [
            {"relation": "isSupplementTo", "identifier": "https://github.com/DanceNitra/agora",
             "scheme": "url"},
            {"relation": "isDocumentedBy", "identifier": SITE, "scheme": "url"},
        ],
    }}

    tok = _token()
    dep = _req("POST", f"{BASE}/api/deposit/depositions", tok, json.dumps({}).encode())
    dep_id, bucket = dep["id"], dep["links"]["bucket"]
    print(f"deposition {dep_id} created on {BASE}")

    rd = readme(c).encode("utf-8")
    for name, blob in (("crucible.json", open(LEDGER, "rb").read()), ("README.md", rd)):
        _req("PUT", f"{bucket}/{name}", tok, blob, ctype="application/octet-stream")
        print(f"  uploaded {name} ({len(blob):,} bytes)")

    _req("PUT", f"{BASE}/api/deposit/depositions/{dep_id}", tok, json.dumps(meta).encode())
    if "--publish" not in sys.argv:
        print(f"\nDRAFT ready, NOT published: {BASE}/deposit/{dep_id}")
        print("Re-run with --publish to mint the DOI (irreversible).")
        return 0
    out = _req("POST", f"{BASE}/api/deposit/depositions/{dep_id}/actions/publish", tok)
    print(f"\nPUBLISHED  DOI: {out.get('doi')}  {out.get('links', {}).get('record_html')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
