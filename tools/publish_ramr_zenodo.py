"""publish_ramr_zenodo.py - archive the RAMR benchmark to Zenodo and mint a permanent DOI via the REST API.
Reads ZENODO_TOKEN from server/.env (never printed). Uploads a source snapshot (git-archive zip of the public
repo's HEAD -> only tracked, guard-cleared files) + README + CITATION.cff, sets metadata, and publishes -> a
permanent, citable DOI proving authorship + first-publication date.

Usage:  python tools/publish_ramr_zenodo.py            # production zenodo.org
        python tools/publish_ramr_zenodo.py --sandbox  # sandbox.zenodo.org (needs a sandbox token)
"""
import os, re, sys, json, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.environ.get("RAMR_REPO_DIR", "C:/Users/Danculus/ramr-pub")
ZIP = os.path.join(REPO, "ramr-v0.5.1.zip")
SANDBOX = "--sandbox" in sys.argv
BASE = "https://sandbox.zenodo.org" if SANDBOX else "https://zenodo.org"
FILES = [ZIP, os.path.join(REPO, "README.md"), os.path.join(REPO, "CITATION.cff")]

META = {"metadata": {
    "title": "RAMR — Retrieval-Augmented Memory Reliability",
    "upload_type": "software",
    "description": ("RAMR is a contamination-resistant synthetic benchmark for agentic-RAG / memory systems. "
                    "It isolates eleven failure modes with pre-registered falsifiers and bootstrap confidence "
                    "intervals: CONVERSION (does complete retrieval convert to a correct multi-hop answer), "
                    "CHAIN-FRAGILITY (cost of one missing hop), DISTRACTION (cost of irrelevant/look-alike facts), "
                    "FACT-RETENTION (does a compiled/summarized memory tier drop facts under a fixed budget), "
                    "OUTCOME-RANKED-RECALL (does ranking recall by was-it-right beat was-it-recalled), "
                    "FORGET-PRECISION (after a fact is updated, does recall return the current value or the stale "
                    "one), COMPRESSION-vs-RAW (does a compiled summary beat the raw noisy context, or only lose to "
                    "it), OPERATIONAL-CONTINUITY (on resume after compaction, is an already-completed action "
                    "re-executed), and TEMPORAL-AS-OF (out-of-order ingest: supersession resolves by validity-time, "
                    "not arrival order), ECHO-RESISTANCE (after a correction, does a restatement of the retired value resurrect it), and INTEGRITY-CONDITIONED RECALL (after a supersession / revert / poison, does recall return the correct current value). v0.5.0 adds a four-gate PREFLIGHT (budget parity, evidence-in-context, liveness, parameter efficacy) that refuses inadmissible comparisons and names the layer that failed - not a metric, but a check on whether a comparison was admissible at all. Also ships a reusable Folklore Meter probe (scores any AI-engineering "
                    "folklore claim against a runnable test) and a shared sha256-pinned RAMR-LS evidence-fixture "
                    "set. Includes a "
                    "frozen sha256-pinned dataset, a single runner, independent baselines (scikit-learn cosine; "
                    "SQLite FTS5/BM25 and dense-vector retrieval), and a number-verification ledger. A "
                    "findings+method release; numbers are synthetic and directional. Code: "
                    "https://github.com/DanceNitra/ramr"),
    "creators": [{"name": "Drahoš, Rastislav", "affiliation": "Agora"}],
    "keywords": ["benchmark", "agent-memory", "retrieval-augmented-generation", "evaluation", "llm",
                 "vector-search", "consolidation"],
    "license": "MIT",
    "access_right": "open",
    "version": "0.5.1",
    "related_identifiers": [
        {"relation": "isSupplementTo", "identifier": "https://github.com/DanceNitra/ramr", "scheme": "url"}],
}}


def _token():
    txt = open(os.path.join(ROOT, "server", ".env"), "rb").read().decode("utf-8", "replace")
    m = re.search(r'ZENODO_TOKEN\s*=\s*"?([^"\r\n]+)', txt)
    if not m:
        sys.exit("ZENODO_TOKEN not found in server/.env")
    return m.group(1).strip().strip('"')


def _req(method, url, tok, data=None, ctype="application/json"):
    headers = {"Authorization": "Bearer " + tok}
    if data is not None and ctype:
        headers["Content-Type"] = ctype
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(r, timeout=180)
        body = resp.read()
        return resp.status, (json.loads(body) if body else {})
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", "replace").replace(tok, "***")
        sys.exit("Zenodo %s %s -> HTTP %d: %s" % (method, url.split('?')[0], e.code, msg[:600]))


def _existing(tok):
    """Avoid minting a duplicate concept DOI: if a RAMR deposition already exists, version it instead."""
    st, deps = _req("GET", BASE + "/api/deposit/depositions?size=100&sort=mostrecent", tok)
    if not isinstance(deps, list):
        return None
    r = [d for d in deps if "ramr" in (((d.get("metadata") or {}).get("title") or "") + (d.get("title") or "")).lower()
         and d.get("submitted")]
    return r[0] if r else None


def main():
    tok = _token()
    print("target:", BASE, "(SANDBOX)" if SANDBOX else "(PRODUCTION)")
    for f in FILES:
        if not os.path.exists(f):
            sys.exit("missing upload file: " + f)
    existing = _existing(tok)
    if existing:
        print("existing RAMR deposition", existing["id"], "-> new version (concept DOI preserved)")
        st, nv = _req("POST", "%s/api/deposit/depositions/%d/actions/newversion" % (BASE, existing["id"]), tok)
        st, draft = _req("GET", (nv.get("links") or {}).get("latest_draft"), tok)
        dep_id = draft["id"]; bucket = draft["links"]["bucket"]
        for fobj in draft.get("files", []):
            if fobj.get("id"):
                _req("DELETE", "%s/api/deposit/depositions/%d/files/%s" % (BASE, dep_id, fobj["id"]), tok)
    else:
        st, dep = _req("POST", BASE + "/api/deposit/depositions", tok, data=b"{}")
        dep_id = dep["id"]; bucket = dep["links"]["bucket"]
        print("created NEW deposition:", dep_id)
    for path in FILES:
        with open(path, "rb") as fh:
            _req("PUT", "%s/%s" % (bucket, os.path.basename(path)), tok, data=fh.read(),
                 ctype="application/octet-stream")
        print("  uploaded:", os.path.basename(path))
    _req("PUT", "%s/api/deposit/depositions/%d" % (BASE, dep_id), tok, data=json.dumps(META).encode("utf-8"))
    print("metadata set")
    st, pub = _req("POST", "%s/api/deposit/depositions/%d/actions/publish" % (BASE, dep_id), tok)
    doi = pub.get("doi") or (pub.get("metadata") or {}).get("doi")
    print("\nPUBLISHED. DOI:", doi)
    print("record:", (pub.get("links") or {}).get("record_html") or (pub.get("links") or {}).get("html"))


if __name__ == "__main__":
    main()
