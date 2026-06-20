# Publishing the Folklore Index (GATED - owner's accounts)

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
