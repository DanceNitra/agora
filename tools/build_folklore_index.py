"""
build_folklore_index.py - assemble The Folklore Index: one normalized, citable, machine-readable
benchmark dataset that unifies Agora's two verification ledgers:
  - the replication Crucible  (public/crucible/crucible.json, curated)
  - the AI-Claim Crucible      (agora_output/aiclaims/aiclaims.json)

Each entry gets a STABLE citation key (FI-NNNN) that NEVER renumbers across rebuilds (persisted keymap
keyed by a content hash), so a published claim key stays valid forever - the whole point of a citable
benchmark. Emits the dataset JSON + a dataset card (README) + CITATION.cff. Re-run after any new verdict
(commit lab scripts first so code links resolve). Pure stdlib; ASCII output (cp1250 console).

Usage:  python tools/build_folklore_index.py
"""
import json, os, re, hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = "https://github.com/DanceNitra/agora"
OUT_DIR = os.path.join(ROOT, "agora_output", "folklore_index")
KEYMAP_PATH = os.path.join(OUT_DIR, "_keymap.json")
VERSION = "0.1.0"


def _load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _lab_path_from(field):
    """aiclaims 'lab' may be 'path/to.py (+ extra.json)' - take the first .py path."""
    if not field:
        return ""
    m = re.search(r"([\w./\\-]+\.py)", field)
    return m.group(1).replace("\\", "/") if m else ""


def _code_url(rel):
    rel = (rel or "").replace("\\", "/")
    if not rel:
        return "", False
    exists = os.path.exists(os.path.join(ROOT, rel))
    return (f"{REPO}/blob/main/{rel}" if exists else ""), exists


def _content_key(domain, claim):
    return hashlib.sha1((domain + "|" + claim.strip().lower()).encode("utf-8")).hexdigest()[:12]


def gather():
    entries = []

    # 1) replication Crucible (curated public version)
    crucible = _load(os.path.join(ROOT, "public", "crucible", "crucible.json"))
    crows = crucible if isinstance(crucible, list) else crucible.get("entries", crucible.get("replications", []))
    for r in crows:
        code = r.get("code") or ""
        rel = ""
        if code:
            mm = re.search(r"/blob/main/(.+)$", code)
            rel = mm.group(1) if mm else ""
        entries.append({
            "domain": "replication",
            "claim": (r.get("claim") or "").strip(),
            "source": (r.get("source") or "").strip(),
            "verdict": (r.get("verdict") or "").strip().upper(),
            "note": (r.get("note") or "").strip(),
            "lab_file": rel,
            "code_url": code,
            "code_resolves": bool(code),
            "date": (r.get("date") or "").strip(),
        })

    # 2) AI-Claim Crucible
    ai = _load(os.path.join(ROOT, "agora_output", "aiclaims", "aiclaims.json"))
    for e in ai.get("entries", []):
        rel = _lab_path_from(e.get("lab"))
        url, resolves = _code_url(rel)
        entries.append({
            "domain": "ai-claim",
            "claim": (e.get("claim") or "").strip(),
            "source": (e.get("source") or "").strip(),
            "verdict": (e.get("verdict") or "").strip().upper(),
            "note": (e.get("note") or "").strip(),
            "lab_file": rel,
            "code_url": url,
            "code_resolves": resolves,
            "date": (e.get("date") or "").strip(),
        })
    return entries


def assign_keys(entries):
    """Stable FI-NNNN keys via a persisted content-hash keymap (assign-once, never renumber)."""
    keymap = _load(KEYMAP_PATH) if os.path.exists(KEYMAP_PATH) else {}
    next_n = (max([int(v.split("-")[1]) for v in keymap.values()], default=0) + 1)
    for e in entries:
        h = _content_key(e["domain"], e["claim"])
        if h not in keymap:
            keymap[h] = "FI-%04d" % next_n
            next_n += 1
        e["key"] = keymap[h]
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(KEYMAP_PATH, "w", encoding="utf-8") as f:
        json.dump(keymap, f, indent=1, sort_keys=True)
    return entries


SCHEMA = {
    "key": "stable citation id (FI-NNNN), permanent per claim",
    "domain": "replication | ai-claim",
    "claim": "the widely-repeated claim, stated precisely",
    "source": "where the claim comes from / who repeats it",
    "verdict": "REPRODUCED | FAILED | NOT_COMPUTABLE",
    "note": "honest summary tying the measured result to the verdict, with scope/caveats",
    "lab_file": "repo-relative path to the runnable test (may be empty)",
    "code_url": "GitHub URL to the runnable test if it resolves",
    "code_resolves": "whether the runnable test file is present in the repo",
    "date": "YYYY-MM-DD",
}


def counts(entries):
    by_v, by_d = {}, {}
    for e in entries:
        by_v[e["verdict"]] = by_v.get(e["verdict"], 0) + 1
        by_d[e["domain"]] = by_d.get(e["domain"], 0) + 1
    return by_v, by_d


def write_dataset(entries):
    entries = sorted(entries, key=lambda e: e["key"])  # stable display order by permanent key
    by_v, by_d = counts(entries)
    resolves = sum(1 for e in entries if e["code_resolves"])
    dataset = {
        "name": "The Folklore Index",
        "version": VERSION,
        "description": ("A standing, machine-readable benchmark of widely-repeated AI / data-science "
                        "claims, each rebuilt as the smallest runnable test and ruled REPRODUCED / FAILED "
                        "/ NOT_COMPUTABLE. Honest, citable receipts for the field's folklore."),
        "homepage": "https://dancenitra.github.io/agora/public/crucible/",
        "repo": REPO,
        "license": "CC-BY-4.0 (data) / MIT (code)",
        "schema": SCHEMA,
        "counts": {"total": len(entries), "by_verdict": by_v, "by_domain": by_d,
                   "runnable_code_present": resolves},
        "entries": entries,
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "folklore_index.json"), "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=1, ensure_ascii=False)
    return dataset


def write_card(ds):
    by_v = ds["counts"]["by_verdict"]
    sample = next((e for e in ds["entries"] if e["verdict"] == "FAILED" and e["code_resolves"]), ds["entries"][0])
    card = f"""# The Folklore Index

{ds['description']}

**Version {ds['version']}** - {ds['counts']['total']} claims
({by_v.get('REPRODUCED',0)} REPRODUCED, {by_v.get('FAILED',0)} FAILED, {by_v.get('NOT_COMPUTABLE',0)} NOT_COMPUTABLE) -
{ds['counts']['runnable_code_present']} with a runnable test in the repo.

Every claim has a permanent citation key (`FI-NNNN`) that never renumbers, so a cited claim stays valid as
the index grows.

## Why it exists
The field repeats a lot of engineering folklore ("smaller chunks are better for RAG", "more context is
always better", "the leaderboard winner is the best model") with little runnable verification. The Folklore
Index rebuilds each claim as the smallest test that could settle it and records an honest verdict - including
NOT_COMPUTABLE when the claim cannot be cleanly settled. Every FAILED is a result you can re-run.

## Schema
Each entry in `folklore_index.json`:
{chr(10).join(f"- `{k}` - {v}" for k, v in ds['schema'].items())}

## How to cite one claim
> Agora Folklore Index, {sample['key']} ({sample['verdict']}): "{sample['claim'][:90]}..."
> {ds['homepage']} (v{ds['version']}).

## Verdict mix
- REPRODUCED: {by_v.get('REPRODUCED',0)}
- FAILED: {by_v.get('FAILED',0)}
- NOT_COMPUTABLE: {by_v.get('NOT_COMPUTABLE',0)}

## Provenance
Generated by `tools/build_folklore_index.py` from two source ledgers in this repo:
the replication Crucible (`public/crucible/crucible.json`) and the AI-Claim Crucible
(`agora_output/aiclaims/aiclaims.json`). Re-run after any new verdict. Data CC-BY-4.0, code MIT.
"""
    with open(os.path.join(OUT_DIR, "README.md"), "w", encoding="utf-8") as f:
        f.write(card)


def write_citation(ds):
    cff = f"""cff-version: 1.2.0
title: "The Folklore Index: a runnable benchmark of AI / data-science claims"
message: "If you use this dataset, please cite it and the specific claim key (FI-NNNN)."
type: dataset
version: "{ds['version']}"
license: CC-BY-4.0
repository-code: "{REPO}"
url: "{ds['homepage']}"
authors:
  - name: "Agora (autonomous research organization)"
"""
    with open(os.path.join(OUT_DIR, "CITATION.cff"), "w", encoding="utf-8") as f:
        f.write(cff)


KEYWORDS = ["ai", "llm", "evaluation", "replication", "reproducibility", "benchmark", "rag",
            "agents", "folklore", "verification"]


def write_publishing(ds):
    """Emit everything needed to publish externally (owner does the final account step, gated):
    a JSONL mirror, a Hugging Face dataset card, Zenodo DOI metadata, a pip-installable package, and
    a PUBLISHING.md with the exact commands."""
    entries = ds["entries"]

    # 1) JSONL mirror (Hugging Face datasets loads line-delimited JSON cleanly)
    with open(os.path.join(OUT_DIR, "folklore_index.jsonl"), "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    # 2) Hugging Face dataset card (YAML front-matter + body)
    by_v = ds["counts"]["by_verdict"]
    hf = f"""---
license: cc-by-4.0
language:
  - en
pretty_name: The Folklore Index
size_categories:
  - n<1K
tags:
{chr(10).join("  - " + k for k in KEYWORDS)}
configs:
  - config_name: default
    data_files: folklore_index.jsonl
---

# The Folklore Index

{ds['description']}

**v{ds['version']}** - {ds['counts']['total']} claims
({by_v.get('REPRODUCED',0)} REPRODUCED / {by_v.get('FAILED',0)} FAILED / {by_v.get('NOT_COMPUTABLE',0)} NOT_COMPUTABLE).
Each row has a permanent `key` (FI-NNNN) for stable citation. Load: `datasets.load_dataset("Danchi17/folklore-index")`.
Fields: {", ".join(ds['schema'].keys())}. Source repo: {REPO}. Data CC-BY-4.0, code MIT.
"""
    with open(os.path.join(OUT_DIR, "HF_DATASET_CARD.md"), "w", encoding="utf-8") as f:
        f.write(hf)

    # 3) Zenodo DOI metadata
    zenodo = {
        "title": "The Folklore Index: a runnable benchmark of AI / data-science claims",
        "description": ds["description"], "upload_type": "dataset", "access_right": "open",
        "license": "cc-by-4.0", "version": ds["version"], "keywords": KEYWORDS,
        "creators": [{"name": "Agora (autonomous research organization)"}],
        "related_identifiers": [{"identifier": REPO, "relation": "isSupplementTo", "scheme": "url"}],
    }
    with open(os.path.join(OUT_DIR, ".zenodo.json"), "w", encoding="utf-8") as f:
        json.dump(zenodo, f, indent=1)

    # 4) pip-installable package (flat layout): folklore_index with a tiny load() API + bundled data
    pkg = os.path.join(OUT_DIR, "pypi", "folklore_index")
    os.makedirs(pkg, exist_ok=True)
    with open(os.path.join(pkg, "folklore_index.json"), "w", encoding="utf-8") as f:
        json.dump(ds, f, indent=1, ensure_ascii=False)   # bundle the dataset inside the package
    init_py = '''"""The Folklore Index - a runnable benchmark of AI / data-science claims.

>>> import folklore_index as fi
>>> fi.verdicts()            # {'REPRODUCED': .., 'FAILED': .., 'NOT_COMPUTABLE': ..}
>>> fi.get("FI-0001")        # one claim by its permanent citation key
"""
import json, os

_DATA = os.path.join(os.path.dirname(__file__), "folklore_index.json")


def load():
    """Return the full dataset (metadata + entries)."""
    with open(_DATA, encoding="utf-8") as f:
        return json.load(f)


def claims():
    """Return the list of claim entries."""
    return load()["entries"]


def get(key):
    """Return one claim by its permanent FI-NNNN key, or None."""
    return next((e for e in claims() if e.get("key") == key), None)


def verdicts():
    """Return the verdict counts."""
    return load()["counts"]["by_verdict"]


__version__ = load().get("version", "0")
'''
    with open(os.path.join(pkg, "__init__.py"), "w", encoding="utf-8") as f:
        f.write(init_py)
    pyproject = f'''[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[project]
name = "folklore-index"
version = "{ds['version']}"
description = "A runnable benchmark of widely-repeated AI / data-science claims, each ruled REPRODUCED / FAILED / NOT_COMPUTABLE."
readme = "README.md"
requires-python = ">=3.8"
license = {{ text = "CC-BY-4.0" }}
keywords = {json.dumps(KEYWORDS)}
authors = [{{ name = "Agora (autonomous research organization)" }}]
classifiers = ["Programming Language :: Python :: 3", "Intended Audience :: Science/Research"]

[project.urls]
Homepage = "{ds['homepage']}"
Source = "{REPO}"

[tool.setuptools]
packages = ["folklore_index"]

[tool.setuptools.package-data]
folklore_index = ["*.json"]
'''
    with open(os.path.join(OUT_DIR, "pypi", "pyproject.toml"), "w", encoding="utf-8") as f:
        f.write(pyproject)
    with open(os.path.join(OUT_DIR, "pypi", "README.md"), "w", encoding="utf-8") as f:
        f.write("# folklore-index\n\n" + ds["description"] +
                "\n\n```python\nimport folklore_index as fi\nfi.verdicts()\nfi.get('FI-0001')\n```\n")

    # 5) PUBLISHING.md - the exact gated steps for the owner (his accounts/tokens)
    pub = f"""# Publishing the Folklore Index (GATED - owner's accounts)

Everything below is prepared by `tools/build_folklore_index.py`. Each publish step needs YOUR account/token;
nothing here runs automatically. Re-run the build first so all artifacts are current:

    python tools/build_folklore_index.py

## A. PyPI  (`pip install folklore-index`)
    cd agora_output/folklore_index/pypi
    python -m pip install --upgrade build twine
    python -m build                      # makes dist/*.whl + *.tar.gz
    python -m twine upload dist/*         # needs your PyPI API token

## B. Hugging Face dataset
    pip install -U huggingface_hub
    huggingface-cli login                 # your HF token
    # create a dataset repo named e.g. <you>/folklore-index, then:
    huggingface-cli upload <you>/folklore-index agora_output/folklore_index/folklore_index.jsonl folklore_index.jsonl --repo-type dataset
    huggingface-cli upload <you>/folklore-index agora_output/folklore_index/HF_DATASET_CARD.md README.md --repo-type dataset

## C. Zenodo DOI
    Easiest: enable the GitHub<->Zenodo integration for the agora repo, then cut a GitHub Release -
    Zenodo mints a DOI automatically using `.zenodo.json`. (Or upload the jsonl on zenodo.org and paste
    the .zenodo.json fields.)

After A/B/C: link the PyPI / HF / DOI from the Crucible page and from each post. The dataset then does the
distribution - researchers cite the DOI and pull the package; no manual social trawling required.
"""
    with open(os.path.join(OUT_DIR, "PUBLISHING.md"), "w", encoding="utf-8") as f:
        f.write(pub)


def main():
    entries = assign_keys(gather())
    ds = write_dataset(entries)
    write_card(ds)
    write_citation(ds)
    write_publishing(ds)
    by_v, by_d = ds["counts"]["by_verdict"], ds["counts"]["by_domain"]
    print("=" * 64)
    print("THE FOLKLORE INDEX v%s" % VERSION)
    print("=" * 64)
    print("total claims      : %d" % ds["counts"]["total"])
    print("by verdict        : %s" % by_v)
    print("by domain         : %s" % by_d)
    print("runnable code      : %d / %d resolve in the repo"
          % (ds["counts"]["runnable_code_present"], ds["counts"]["total"]))
    missing = [e["key"] for e in entries if e["lab_file"] and not e["code_resolves"]]
    if missing:
        print("WARNING: %d entries reference a lab file that is NOT in the repo (code link blank): %s"
              % (len(missing), ", ".join(missing[:8])))
    print("wrote: folklore_index.json, README.md, CITATION.cff, _keymap.json")
    print("publishing artifacts: folklore_index.jsonl, HF_DATASET_CARD.md, .zenodo.json, "
          "pypi/ (pip package), PUBLISHING.md")


if __name__ == "__main__":
    main()
