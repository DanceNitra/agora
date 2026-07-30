"""publish_inspeximus_hf.py - push inspeximus to the Hugging Face Hub as a model-type repo.

Reads HF_TOKEN from server/.env (never printed); uses the huggingface_hub API, so no token ever reaches a
command line. Publishes the HF card, CITATION, LICENSE and the WHOLE `inspeximus` package to
<account>/inspeximus. Idempotent: re-run to update. ASCII prints.

TWO THINGS THIS SCRIPT USED TO GET WRONG, both found on 2026-07-30:

1. IT PUBLISHED FROM A STAGING FOLDER. `agora_output/inspeximus_dist` held inspeximus.py at version
   1.1.0 while PyPI served 1.88.1, and this tool pushed that folder verbatim without rebuilding. One run
   would have shipped a two-month-old library as the public artifact. The canonical repo is the source
   of truth now; the staging folder supplies the card and nothing else.

2. IT SHIPPED A FLATTENED SINGLE FILE. Measured: copy core.py out on its own and it imports, remembers
   and recalls -- but forget_subject() raises, because erasure needs .erasure_residue and
   .deletion_manifest. The flat artifact could not do the one thing this project is known for. It now
   uploads the package directory.

It also sets the repo public explicitly. huggingface.co/Danchi17/inspeximus returned 401 to anonymous
visitors for weeks -- while the README and the storefront both linked to it -- because nobody ever
checked it from outside.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANON = os.environ.get("INSPEXIMUS_REPO", os.path.join(os.path.dirname(ROOT), "inspeximus-repo"))
SRC = os.path.join(ROOT, "agora_output", "inspeximus_dist")   # the HF card only
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
        (os.path.join(SRC, "HF_CARD.md"), "README.md"),        # HF renders this as the card
        (os.path.join(CANON, "CITATION.cff"), "CITATION.cff"),
        (os.path.join(CANON, "LICENSE"), "LICENSE"),
    ]
    for local, remote in uploads:
        if not os.path.exists(local):
            sys.exit("missing upload file: " + local)
        api.upload_file(path_or_fileobj=local, path_in_repo=remote, repo_id=repo_id, repo_type="model")
        print("  uploaded:", remote)

    pkg = os.path.join(CANON, REPO_NAME)
    if not os.path.isdir(pkg):
        sys.exit("canonical package not found: " + pkg)
    api.upload_folder(folder_path=pkg, path_in_repo=REPO_NAME, repo_id=repo_id, repo_type="model",
                      allow_patterns=["*.py", "py.typed"], ignore_patterns=["__pycache__/*"])
    print("  uploaded: %s/ (package)" % REPO_NAME)

    for fn in ("update_repo_settings", "update_repo_visibility"):
        if hasattr(api, fn):
            try:
                getattr(api, fn)(repo_id=repo_id, private=False, repo_type="model")
                print("  visibility: public")
                break
            except Exception as e:                              # pragma: no cover
                print("  visibility:", type(e).__name__, str(e)[:90])

    print("\nLIVE: https://huggingface.co/%s" % repo_id)


if __name__ == "__main__":
    main()
