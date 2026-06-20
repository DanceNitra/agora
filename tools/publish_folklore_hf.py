"""
publish_folklore_hf.py - push the Folklore Index to the Hugging Face Hub as a dataset.
Reads HF_TOKEN from server/.env (never printed); uses the huggingface_hub API (no token on any
command line). Idempotent: re-run after `python tools/build_folklore_index.py` to update the dataset.

Usage:  python tools/publish_folklore_hf.py            # publishes to dancenitra/folklore-index
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_NAME = "folklore-index"          # namespace is derived from the token's authenticated account
SRC = os.path.join(ROOT, "agora_output", "folklore_index")


def _token():
    txt = open(os.path.join(ROOT, "server", ".env"), "rb").read().decode("utf-8", "replace")
    m = re.search(r'HF_TOKEN\s*=\s*"?(hf_\S+)', txt)
    if not m:
        sys.exit("HF_TOKEN not found in server/.env")
    return m.group(1).strip().strip('"')


def main():
    from huggingface_hub import HfApi
    api = HfApi(token=_token())
    who = api.whoami()["name"]
    repo_id = "%s/%s" % (who, REPO_NAME)
    print("authenticated as:", who, "-> publishing to", repo_id)

    api.create_repo(repo_id, repo_type="dataset", exist_ok=True)
    print("repo ready:", repo_id)
    REPO_ID = repo_id

    # (local file, path in the HF repo)
    uploads = [
        (os.path.join(SRC, "HF_DATASET_CARD.md"), "README.md"),       # HF renders this as the card
        (os.path.join(SRC, "folklore_index.jsonl"), "folklore_index.jsonl"),
        (os.path.join(SRC, "folklore_index.json"), "folklore_index.json"),
        (os.path.join(SRC, "CITATION.cff"), "CITATION.cff"),
    ]
    for local, remote in uploads:
        if not os.path.exists(local):
            print("  SKIP (missing):", local); continue
        api.upload_file(path_or_fileobj=local, path_in_repo=remote,
                        repo_id=REPO_ID, repo_type="dataset")
        print("  uploaded:", remote)

    print("\nLIVE: https://huggingface.co/datasets/%s" % repo_id)


if __name__ == "__main__":
    main()
