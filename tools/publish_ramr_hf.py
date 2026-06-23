"""publish_ramr_hf.py - push the RAMR benchmark dataset to the Hugging Face Hub (discoverability).
Reads HF_TOKEN from server/.env (never printed); uses the huggingface_hub API (no token on any command line).
Publishes the frozen fact-chain dataset + a dataset card + manifest + CITATION to <account>/ramr (the namespace is
the token's authenticated account). Idempotent: re-run to update. ASCII prints."""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_NAME = "ramr"
CARD = os.path.join(ROOT, "agora_output", "benchmark", "RAMR_HF_CARD.md")
PUB = os.environ.get("RAMR_REPO_DIR", "C:/Users/Danculus/ramr-pub")


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
    print("authenticated as:", who, "-> publishing dataset", repo_id)
    api.create_repo(repo_id, repo_type="dataset", exist_ok=True)
    uploads = [
        (CARD, "README.md"),                                                  # HF renders this as the card
        (os.path.join(PUB, "data", "ramr_chains_v0.1.0.jsonl"), "ramr_chains_v0.1.0.jsonl"),
        (os.path.join(PUB, "data", "manifest.json"), "manifest.json"),
        (os.path.join(PUB, "CITATION.cff"), "CITATION.cff"),
    ]
    for local, remote in uploads:
        if not os.path.exists(local):
            sys.exit("missing upload file: " + local)
        api.upload_file(path_or_fileobj=local, path_in_repo=remote, repo_id=repo_id, repo_type="dataset")
        print("  uploaded:", remote)
    print("\nLIVE: https://huggingface.co/datasets/%s" % repo_id)


if __name__ == "__main__":
    main()
