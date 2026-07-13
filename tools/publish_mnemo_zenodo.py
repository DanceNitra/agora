"""
publish_mnemo_zenodo.py - archive mnemo on Zenodo and mint a citable software DOI via the REST API.
Reads ZENODO_TOKEN from server/.env (never printed). If a prior mnemo record exists it creates a NEW
VERSION (preserving the concept DOI); otherwise it creates a fresh deposition. Metadata from
agora_output/mnemo_dist/.zenodo.json.

Needs a Zenodo token with scopes: deposit:write + deposit:actions.
Usage:  python tools/publish_mnemo_zenodo.py            # production zenodo.org
        python tools/publish_mnemo_zenodo.py --sandbox  # sandbox.zenodo.org (dry-run DOI)
"""
import os, re, sys, json, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "agora_output", "mnemo_dist")
SANDBOX = "--sandbox" in sys.argv
BASE = "https://sandbox.zenodo.org" if SANDBOX else "https://zenodo.org"
FILES = ["mnemo.py", "mnemo_mcp.py", "deletion_manifest.py", "erasure_auditor.py", "README.md", "CITATION.cff", "LICENSE"]


def _token():
    txt = open(os.path.join(ROOT, "server", ".env"), "rb").read().decode("utf-8", "replace")
    m = re.search(r'ZENODO_TOKEN\s*=\s*"?([^"\r\n]+)', txt)
    if not m:
        sys.exit("ZENODO_TOKEN not found in server/.env (need scopes deposit:write + deposit:actions)")
    return m.group(1).strip().strip('"')


def _req(method, url, tok, data=None, ctype="application/json"):
    headers = {"Authorization": "Bearer " + tok}
    if data is not None and ctype:
        headers["Content-Type"] = ctype
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(r, timeout=120)
        body = resp.read()
        return resp.status, (json.loads(body) if body else {})
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", "replace").replace(tok, "***")
        sys.exit("Zenodo %s %s -> HTTP %d: %s" % (method, url.split('?')[0], e.code, msg[:600]))


def _zenodo_metadata():
    z = json.load(open(os.path.join(SRC, ".zenodo.json"), encoding="utf-8"))
    return {"metadata": {
        "title": z["title"], "upload_type": z.get("upload_type", "software"),
        "description": z["description"], "creators": z.get("creators", [{"name": "Agora"}]),
        "keywords": z.get("keywords", []), "license": z.get("license", "mit"),
        "access_right": z.get("access_right", "open"), "version": z.get("version", "0.4.0"),
        "related_identifiers": z.get("related_identifiers", []),
    }}


def _existing_mnemo(tok):
    """Return the most-recent published mnemo deposition (so we VERSION it, never fork a new concept DOI)."""
    st, deps = _req("GET", BASE + "/api/deposit/depositions?size=100&sort=mostrecent", tok)
    if not isinstance(deps, list):
        return None
    hits = [d for d in deps if "mnemo" in ((d.get("title") or "") +
            ((d.get("metadata") or {}).get("title") or "")).lower() and d.get("submitted")]
    return hits[0] if hits else None


def main():
    tok = _token()
    print("target:", BASE, "(SANDBOX)" if SANDBOX else "(PRODUCTION)")
    existing = _existing_mnemo(tok)
    if existing:
        print("existing mnemo deposition:", existing["id"], "ver",
              (existing.get("metadata") or {}).get("version"), "- creating a NEW VERSION (concept DOI preserved)")
        st, nv = _req("POST", "%s/api/deposit/depositions/%d/actions/newversion" % (BASE, existing["id"]), tok)
        draft_url = (nv.get("links") or {}).get("latest_draft")
        if not draft_url:
            sys.exit("no latest_draft returned; aborting (no duplicate created)")
        st, draft = _req("GET", draft_url, tok)
        dep_id = draft["id"]
        bucket = draft["links"]["bucket"]
        for f in draft.get("files", []):
            fid = f.get("id")
            if fid:
                _req("DELETE", "%s/api/deposit/depositions/%d/files/%s" % (BASE, dep_id, fid), tok)
        print("new-version draft:", dep_id)
    else:
        st, dep = _req("POST", BASE + "/api/deposit/depositions", tok, data=b"{}")
        dep_id = dep["id"]
        bucket = dep["links"]["bucket"]
        print("created NEW deposition (no prior record):", dep_id)

    for fn in FILES:
        path = os.path.join(SRC, fn)
        if not os.path.exists(path):
            print("  SKIP (missing):", fn); continue
        with open(path, "rb") as f:
            _req("PUT", "%s/%s" % (bucket, fn), tok, data=f.read(), ctype="application/octet-stream")
        print("  uploaded:", fn)

    _req("PUT", "%s/api/deposit/depositions/%d" % (BASE, dep_id), tok,
         data=json.dumps(_zenodo_metadata()).encode("utf-8"))
    print("metadata set")

    st, pub = _req("POST", "%s/api/deposit/depositions/%d/actions/publish" % (BASE, dep_id), tok)
    doi = pub.get("doi") or (pub.get("metadata") or {}).get("doi")
    print("\nPUBLISHED. DOI:", doi)
    print("record:", (pub.get("links") or {}).get("record_html") or (pub.get("links") or {}).get("html"))


if __name__ == "__main__":
    main()
