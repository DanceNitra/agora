"""
publish_folklore_zenodo.py - upload the Folklore Index to Zenodo and mint a DOI via the REST API.
Reads ZENODO_TOKEN from server/.env (never printed). Creates a deposition, uploads the dataset files,
sets metadata from agora_output/folklore_index/.zenodo.json, and publishes -> permanent dataset DOI.

Needs a Zenodo personal access token with scopes: deposit:write + deposit:actions.
Put it in server/.env as:  ZENODO_TOKEN=...
Usage:  python tools/publish_folklore_zenodo.py            # production zenodo.org
        python tools/publish_folklore_zenodo.py --sandbox  # sandbox.zenodo.org (dry-run DOI)
"""
import os, re, sys, json, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "agora_output", "folklore_index")
SANDBOX = "--sandbox" in sys.argv
BASE = "https://sandbox.zenodo.org" if SANDBOX else "https://zenodo.org"
FILES = ["folklore_index.jsonl", "folklore_index.json", "README.md", "CITATION.cff"]


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
    # map our .zenodo.json into the API's metadata shape
    return {"metadata": {
        "title": z["title"], "upload_type": z.get("upload_type", "dataset"),
        "description": z["description"], "creators": z.get("creators", [{"name": "Agora"}]),
        "keywords": z.get("keywords", []), "license": z.get("license", "cc-by-4.0"),
        "access_right": z.get("access_right", "open"), "version": z.get("version", "0.1.0"),
        "related_identifiers": z.get("related_identifiers", []),
    }}


def main():
    tok = _token()
    print("target:", BASE, "(SANDBOX)" if SANDBOX else "(PRODUCTION)")

    # 1) create an empty deposition
    st, dep = _req("POST", BASE + "/api/deposit/depositions", tok, data=b"{}")
    dep_id = dep["id"]
    bucket = dep["links"]["bucket"]
    print("created deposition:", dep_id)

    # 2) upload files into the bucket
    for fn in FILES:
        path = os.path.join(SRC, fn)
        if not os.path.exists(path):
            print("  SKIP (missing):", fn); continue
        with open(path, "rb") as f:
            _req("PUT", "%s/%s" % (bucket, fn), tok, data=f.read(), ctype="application/octet-stream")
        print("  uploaded:", fn)

    # 3) attach metadata
    _req("PUT", "%s/api/deposit/depositions/%d" % (BASE, dep_id), tok,
         data=json.dumps(_zenodo_metadata()).encode("utf-8"))
    print("metadata set")

    # 4) publish -> DOI
    st, pub = _req("POST", "%s/api/deposit/depositions/%d/actions/publish" % (BASE, dep_id), tok)
    doi = pub.get("doi") or (pub.get("metadata") or {}).get("doi")
    print("\nPUBLISHED. DOI:", doi)
    print("record:", (pub.get("links") or {}).get("record_html") or (pub.get("links") or {}).get("html"))


if __name__ == "__main__":
    main()
