"""
publish_inspeximus_zenodo.py - archive inspeximus on Zenodo and mint a citable software DOI via the REST API.
Reads ZENODO_TOKEN from server/.env (never printed). If a prior inspeximus record exists it creates a NEW
VERSION (preserving the concept DOI); otherwise it creates a fresh deposition. Metadata from
agora_output/inspeximus_dist/.zenodo.json.

Needs a Zenodo token with scopes: deposit:write + deposit:actions.
Usage:  python tools/publish_inspeximus_zenodo.py            # production zenodo.org
        python tools/publish_inspeximus_zenodo.py --sandbox  # sandbox.zenodo.org (dry-run DOI)
"""
import os, re, sys, json, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "agora_output", "inspeximus_dist")
SANDBOX = "--sandbox" in sys.argv
BASE = "https://sandbox.zenodo.org" if SANDBOX else "https://zenodo.org"
# ARCHIVE THE CANONICAL REPO, not a staging folder. The old list named files in
# agora_output/inspeximus_dist, which held the library at version 1.1.0 while PyPI served 1.88.1 -- so a
# run would have minted a citable DOI for a two-month-old snapshot. Same defect the Hugging Face
# publisher had. `git archive HEAD` also guarantees only tracked, guard-cleared files ship.
CANON = os.environ.get("INSPEXIMUS_REPO", os.path.join(os.path.dirname(ROOT), "inspeximus-repo"))
ARCHIVE = "inspeximus-source.zip"
# The concept DOI this software versions under. Everything published here must land on ONE lineage.
CONCEPT_RECID = int(os.environ.get("ZENODO_CONCEPT_RECID", "21708778"))


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


def _existing_inspeximus(tok):
    """Return the most-recent published inspeximus deposition (so we VERSION it, never fork a new concept DOI)."""
    st, deps = _req("GET", BASE + "/api/deposit/depositions?size=100&sort=mostrecent", tok)
    if not isinstance(deps, list):
        return None
    # PIN THE CONCEPT DOI. This used to match the word "inspeximus" in the deposition title -- and the
    # prior record is titled "mnemo: ...", from before the rename. So it found nothing, minted a SECOND
    # concept DOI (10.5281/zenodo.21708778) beside the original (10.5281/zenodo.21128549), and split the
    # citation record for one piece of software. A title substring is not an identity; the concept
    # recid is.
    want = str(CONCEPT_RECID)
    hits = [d for d in deps if d.get("submitted") and (
        str(d.get("conceptrecid") or "") == want or str(d.get("id") or "") == want)]
    if not hits:
        sys.exit("no deposition under concept recid %s -- refusing to mint a THIRD concept DOI. "
                 "Set CONCEPT_RECID or pass --new deliberately." % want)
    return hits[0]


def main():
    tok = _token()
    print("target:", BASE, "(SANDBOX)" if SANDBOX else "(PRODUCTION)")
    existing = _existing_inspeximus(tok)
    if existing:
        print("existing inspeximus deposition:", existing["id"], "ver",
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

    import subprocess, tempfile
    zpath = os.path.join(tempfile.mkdtemp(), ARCHIVE)
    r = subprocess.run(["git", "-C", CANON, "archive", "--format=zip", "-o", zpath, "HEAD"],
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(zpath):
        sys.exit("git archive failed: " + (r.stderr or "")[:200])
    with open(zpath, 'rb') as f:
        _req("PUT", "%s/%s" % (bucket, ARCHIVE), tok, data=f.read(), ctype="application/octet-stream")
    print("  uploaded:", ARCHIVE, "(%.1f KB)" % (os.path.getsize(zpath) / 1024))
    for fn in ("README.md", "CITATION.cff", "LICENSE"):
        path = os.path.join(CANON, fn)
        if not os.path.exists(path):
            print("  SKIP (missing):", fn); continue
        with open(path, 'rb') as f:
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
