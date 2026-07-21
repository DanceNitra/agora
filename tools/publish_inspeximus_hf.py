"""publish_inspeximus_hf.py - push inspeximus to the Hugging Face Hub (discoverability) as a model-type repo.
Reads HF_TOKEN from server/.env (never printed); uses the huggingface_hub API (no token on any command
line). Publishes the HF card + the single-file core + MCP server + CITATION + LICENSE to <account>/inspeximus
(namespace = the token's authenticated account). Idempotent: re-run to update. ASCII prints."""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "agora_output", "inspeximus_dist")
REPO_NAME = "inspeximus"


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
    print("authenticated as:", who, "-> publishing model repo", repo_id)
    api.create_repo(repo_id, repo_type="model", exist_ok=True)
    uploads = [
        (os.path.join(SRC, "HF_CARD.md"), "README.md"),   # HF renders this as the card
        (os.path.join(SRC, "inspeximus.py"), "inspeximus.py"),
        (os.path.join(SRC, "mcp.py"), "mcp.py"),
        (os.path.join(SRC, "CITATION.cff"), "CITATION.cff"),
        (os.path.join(SRC, "LICENSE"), "LICENSE"),
    ]
    for local, remote in uploads:
        if not os.path.exists(local):
            sys.exit("missing upload file: " + local)
        api.upload_file(path_or_fileobj=local, path_in_repo=remote, repo_id=repo_id, repo_type="model")
        print("  uploaded:", remote)
    print("\nLIVE: https://huggingface.co/%s" % repo_id)


if __name__ == "__main__":
    main()
