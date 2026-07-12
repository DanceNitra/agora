"""
publish_paper_zenodo.py - upload the value-obscuring-reversion joint paper (PDF) to Zenodo, mint a DOI.
Reads ZENODO_TOKEN from server/.env (never printed). Metadata from agora_output/collab/.zenodo.json.

Usage:  python tools/publish_paper_zenodo.py --sandbox   # sandbox.zenodo.org (dry-run, fake DOI) -- run FIRST
        python tools/publish_paper_zenodo.py             # production zenodo.org (permanent DOI)
"""
import os, re, sys, json, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COLLAB = os.path.join(ROOT, "agora_output", "collab")
PDF = os.path.join(COLLAB, "value_obscuring_reversion_MERGED_v1.pdf")
META = os.path.join(COLLAB, ".zenodo.json")
SANDBOX = "--sandbox" in sys.argv
BASE = "https://sandbox.zenodo.org" if SANDBOX else "https://zenodo.org"


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
        resp = urllib.request.urlopen(r, timeout=180)
        body = resp.read()
        return resp.status, (json.loads(body) if body else {})
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", "replace").replace(tok, "***")
        sys.exit("Zenodo %s %s -> HTTP %d: %s" % (method, url.split('?')[0], e.code, msg[:800]))


def main():
    if not os.path.exists(PDF):
        sys.exit("PDF not found: " + PDF)
    z = json.load(open(META, encoding="utf-8"))
    tok = _token()
    print("target:", BASE, "(SANDBOX)" if SANDBOX else "(PRODUCTION)")

    st, dep = _req("POST", BASE + "/api/deposit/depositions", tok, data=b"{}")
    dep_id = dep["id"]; bucket = dep["links"]["bucket"]
    print("created deposition:", dep_id)

    fname = "value_obscuring_reversion.pdf"
    with open(PDF, "rb") as f:
        _req("PUT", "%s/%s" % (bucket, fname), tok, data=f.read(), ctype="application/octet-stream")
    print("uploaded:", fname)

    metadata = {"metadata": {
        "title": z["title"], "upload_type": z["upload_type"],
        "publication_type": z.get("publication_type", "preprint"),
        "description": z["description"], "creators": z["creators"],
        "keywords": z.get("keywords", []), "license": z.get("license", "cc-by-4.0"),
        "access_right": z.get("access_right", "open"), "language": z.get("language", "eng"),
        "related_identifiers": z.get("related_identifiers", []),
        "notes": z.get("notes", ""),
    }}
    _req("PUT", "%s/api/deposit/depositions/%d" % (BASE, dep_id), tok,
         data=json.dumps(metadata).encode("utf-8"))
    print("metadata set")

    if "--publish" not in sys.argv:
        print("\nDRAFT ready (not published). Review at:",
              (dep.get("links") or {}).get("html", BASE + "/deposit/%d" % dep_id))
        print("Re-run with --publish to mint the DOI.")
        return

    st, pub = _req("POST", "%s/api/deposit/depositions/%d/actions/publish" % (BASE, dep_id), tok)
    doi = pub.get("doi") or (pub.get("metadata") or {}).get("doi")
    print("\nPUBLISHED. DOI:", doi)
    print("record:", (pub.get("links") or {}).get("record_html") or (pub.get("links") or {}).get("html"))


if __name__ == "__main__":
    main()
