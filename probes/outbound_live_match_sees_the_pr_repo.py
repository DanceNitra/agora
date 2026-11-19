"""Does live_match find a text that went out as a PR in another repository?

ONE check inside VALIDATE, not the gate. The gate is Validate, storm when the claim rests on
literature, stress-claim, and verify-claims.

THE DEFECT. `outbound.py status` reported "5 owner" for three texts that were already out, two of
them MERGED. live_match looked for our text in two places: comments on the meta thread, and issues
our account opened in the THREAD's repository. A `kind: pr` text names its destination in
meta.json under `creates.repo`, which for these three was a different repository, so the search
ran where the text was not. The owner approved one a second time on 2026-11-20 and the duplicate
gate was the only thing that stopped a second PR against a merged one.

THE CONTROLS. B withholds `creates.repo` and must still reproduce the defect, or this probe has
stopped measuring anything. C changes one byte and must not match, or the fix is a looser matcher
rather than a wider search.

Run: python probes/outbound_live_match_sees_the_pr_repo.py     (reads GitHub, writes nothing)
"""
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import outbound as ob                                                    # noqa: E402

SLUGS = ["fagi-udah-pr", "udah-poc-adapter-pr", "udah-poc-rerun-pr"]


def main():
    cache, bad = {}, 0
    for slug in SLUGS:
        d = os.path.join(ROOT, "agora_output", "outbound", slug)
        meta = json.load(io.open(os.path.join(d, "meta.json"), encoding="utf-8"))
        repo = (meta.get("creates") or {}).get("repo")
        payload = open(os.path.join(d, "draft.sealed.md"), "rb").read()

        a = ob.live_match(meta["thread"], payload, cache, also_repos=[repo])
        b = ob.live_match(meta["thread"], payload, cache, also_repos=[])
        c = ob.live_match(meta["thread"], payload + b"x", cache, also_repos=[repo])

        ok = bool(a) and b is None and c is None
        bad += not ok
        print("%-22s A=%-56s B=%s C=%s  %s"
              % (slug, (a[1] if a else None), bool(b), bool(c), "ok" if ok else "FAIL"))

    print("\n%d of %d slugs behave as intended." % (len(SLUGS) - bad, len(SLUGS)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
