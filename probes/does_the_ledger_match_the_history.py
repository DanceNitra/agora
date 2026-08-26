"""C11: bind a revision ledger to the version-control history it claims to describe.

WHY. @qingkong66 named the gap on deepseek-ai/DeepSeek-V3#1591 and left it as an observation:

    "CI can pin the files, but it cannot catch whether the ledger description matches the actual
     revisions." / "CI 守门能锁住数据本身，但锁不住账本的描述与 git 历史是否一致"

He is right, and it is checkable. @UID9622's `integrity/calibration_dataset_check.py` runs C01-C10
-- manifest parse, files exist, record counts, JSON well-formed, request_id uniqueness, required
fields, per-file SHA-256, record_hash recompute, Merkle roots, secret scan -- and not one of them
opens `CHANGELOG.jsonl` or looks at git. A ledger entry can therefore name any version it likes for
any hash it likes and the suite stays green, which is exactly what happened.

WHAT THIS CHECKS, and the split matters because only the first half is mechanical:

  MECHANICAL, and it is the part that can fail loudly:
    L1  every `sha256_after` in the ledger is the hash of a blob that REALLY EXISTED at that path
        somewhere in git history. A hash of a state that never existed is a fabricated ledger.
    L2  the ledger's entry order agrees with the commit order of the states it names. An
        append-only ledger that runs backwards against history is describing a different sequence
        of events from the one that happened.
    L3  every commit that CHANGED the file is named by some ledger entry. A revision the ledger
        does not mention is an unlogged change, which is the failure a ledger exists to prevent.

  HEURISTIC, reported separately and never as a failure on its own:
    L4  the version label on an entry against the commit message of the state it points at. Commit
        messages are prose in whichever language the author writes, so this can only ever raise a
        question. It is what caught the live defect, but L1-L3 are what a CI gate should trust.

THE CONTROLS, because a checker over someone else's repository is exactly the kind that reports
SAFE when it is looking at nothing:
  * the ledger must parse and be non-empty, and at least one entry must carry a hash. A repository
    with no CHANGELOG passes L1-L3 vacuously, so that case REFUSES instead of passing.
  * every path named in `scope` must resolve to a real path with a real history, asserted.
  * a NEGATIVE CONTROL runs the same logic over a fabricated ledger entry whose hash is invented;
    L1 must fail on it. If it does not, the checker cannot see its own target.
  * a POSITIVE CONTROL: at least one real entry must PASS L1, or the harness is broken rather than
    the ledger.

This is not a novel idea -- it is the same shape as in-toto/SLSA provenance verification and a
transparency log, applied to a plain JSONL ledger with git as the log. What it is not is present in
this repository, and the gap it leaves is live right now.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = "data/shared-audit/CHANGELOG.jsonl"
# Every key a ledger entry uses to record a post-state hash, in this ledger's own vocabulary.
HASH_KEYS = ("sha256_after", "sha256_after_v10", "sha256_after_v11n")
# Which file each of the version-specific keys is about, when `scope` names more than one.
KEY_PATH = {
    "sha256_after_v10": "longhun-shared-audit-dataset-v1.0.jsonl",
    "sha256_after_v11n": "longhun-shared-audit-dataset-v1.1-negative.jsonl",
}


def git(repo: str, *args: str) -> str:
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise SystemExit("REFUSED: git %s failed: %s" % (" ".join(args), (r.stderr or "").strip()))
    return r.stdout


def blob_sha256(repo: str, commit: str, path: str) -> str | None:
    """sha256 of the file's BYTES as of `commit`, or None if it did not exist there."""
    r = subprocess.run(["git", "-C", repo, "show", "%s:%s" % (commit, path)],
                       capture_output=True)
    if r.returncode != 0:
        return None
    return hashlib.sha256(r.stdout).hexdigest()


def history(repo: str, path: str) -> list:
    """Every commit that changed `path`, oldest first, with the resulting file hash."""
    out = git(repo, "log", "--reverse", "--format=%H\t%cI\t%s", "--", path)
    rows = []
    for line in out.splitlines():
        if not line.strip():
            continue
        sha, when, subject = line.split("\t", 2)
        rows.append({"commit": sha, "short": sha[:8], "when": when, "subject": subject,
                     "sha256": blob_sha256(repo, sha, path)})
    return rows


def paths_in(scope: str, known: list) -> list:
    """The dataset paths an entry's free-text `scope` refers to."""
    if not scope:
        return []
    hit = [p for p in known if os.path.basename(p) in scope]
    return hit or (known if "both" in scope.lower() else [])


def audit(repo: str, ledger_lines: list, hist: dict, known: list) -> tuple[list, list]:
    """Returns (findings, checked) -- findings are L1/L2/L3/L4 hits, checked are the entries seen."""
    findings, checked = [], []
    by_hash = {}
    for path, rows in hist.items():
        for r in rows:
            if r["sha256"]:
                by_hash.setdefault(r["sha256"], []).append((path, r))

    order_seen = []
    for n, entry in enumerate(ledger_lines, 1):
        scope_paths = paths_in(entry.get("scope", ""), known)
        for key in HASH_KEYS:
            h = entry.get(key)
            if not h:
                continue
            want = [p for p in scope_paths
                    if key not in KEY_PATH or os.path.basename(p) == KEY_PATH[key]]
            checked.append({"line": n, "version": entry.get("version"), "key": key, "sha256": h})
            hits = by_hash.get(h, [])
            if not hits:
                findings.append({"rule": "L1", "line": n, "version": entry.get("version"),
                                 "detail": "sha256 %s... is not any historical state of %s"
                                           % (h[:12], ", ".join(os.path.basename(p)
                                                                for p in want or scope_paths))})
                continue
            path, row = hits[0]
            order_seen.append((n, row["when"], entry.get("version"), row["short"]))
            if want and path not in want:
                findings.append({"rule": "L1", "line": n, "version": entry.get("version"),
                                 "detail": "hash belongs to %s, entry is about %s"
                                           % (os.path.basename(path), KEY_PATH.get(key, "?"))})
            # L4, heuristic: does the commit that produced this state agree with the label?
            label = (entry.get("version") or "").lower()
            subj = row["subject"].lower()
            for tag in ("r1", "r2", "r3"):
                if tag in subj.split() or (" " + tag + " ") in (" " + subj + " "):
                    if label and not label.endswith(tag) and tag not in label:
                        findings.append(
                            {"rule": "L4", "line": n, "version": entry.get("version"),
                             "detail": "labelled %s, but the state it names was produced by %s "
                                       "whose own message reads: %s"
                                       % (entry.get("version"), row["short"], row["subject"])})
                    break

    # L2: the ledger's order against the commits' order.
    for (n1, t1, v1, c1), (n2, t2, v2, c2) in zip(order_seen, order_seen[1:]):
        if t2 < t1:
            findings.append({"rule": "L2", "line": n2, "version": v2,
                             "detail": "entry %s (%s, %s) predates entry %s (%s, %s) in git, but "
                                       "follows it in the ledger" % (v2, c2, t2, v1, c1, t1)})

    # L3: a commit that changed a file and is named by no entry.
    named = {c["sha256"] for c in checked}
    for path, rows in hist.items():
        for r in rows:
            if r["sha256"] and r["sha256"] not in named:
                findings.append({"rule": "L3", "line": None, "version": None,
                                 "detail": "%s changed %s to %s... and no ledger entry records "
                                           "that state (%s)"
                                           % (r["short"], os.path.basename(path), r["sha256"][:12],
                                              r["subject"][:60])})
    return findings, checked


def main() -> int:
    repo = None
    for a in sys.argv[1:]:
        if not a.startswith("--"):
            repo = a
    if not repo or not os.path.isdir(os.path.join(repo, ".git")):
        raise SystemExit("usage: does_the_ledger_match_the_history.py <path-to-git-clone>")

    lpath = os.path.join(repo, LEDGER)
    if not os.path.exists(lpath):
        raise SystemExit("REFUSED: %s is absent, so every rule below would pass over nothing"
                         % LEDGER)
    ledger = [json.loads(l) for l in io.open(lpath, encoding="utf-8") if l.strip()]
    if not ledger:
        raise SystemExit("REFUSED: the ledger is empty")
    if not any(any(e.get(k) for k in HASH_KEYS) for e in ledger):
        raise SystemExit("REFUSED: no ledger entry records a hash, so L1 could never fail")

    known = [l.strip() for l in git(repo, "ls-files", "data/shared-audit").splitlines()
             if l.strip().endswith(".jsonl") and "CHANGELOG" not in l]
    if not known:
        raise SystemExit("REFUSED: no dataset files found under data/shared-audit")
    hist = {p: history(repo, p) for p in known}
    for p, rows in hist.items():
        if not rows:
            raise SystemExit("REFUSED: %s has no history; the check would see nothing" % p)

    findings, checked = audit(repo, ledger, hist, known)

    print("  ledger entries      : %d   hashes recorded: %d" % (len(ledger), len(checked)))
    for p, rows in hist.items():
        print("  %-46s %d states in history" % (os.path.basename(p), len(rows)))
    print()
    for f in findings:
        where = ("ledger line %s" % f["line"]) if f["line"] else "history"
        print("  %s  %-16s %s" % (f["rule"], where, f["detail"]))
    if not findings:
        print("  no findings")

    # --- controls -----------------------------------------------------------------------------
    v = {}
    fake = ledger + [{"version": "v9.9-fabricated", "scope": os.path.basename(known[0]),
                      "sha256_after": "0" * 64}]
    neg, _ = audit(repo, fake, hist, known)
    v["NEGATIVE_CONTROL_an_invented_hash_fails_L1"] = any(
        f["rule"] == "L1" and f["version"] == "v9.9-fabricated" for f in neg)
    v["POSITIVE_CONTROL_some_real_entry_passes_L1"] = len(checked) > sum(
        1 for f in findings if f["rule"] == "L1")
    v["CONTROL_the_ledger_and_history_were_both_read"] = bool(ledger) and all(hist.values())
    v["CONTROL_the_checker_looked_at_more_than_one_file"] = len(known) >= 2
    print()
    for k, ok in v.items():
        print("  %s  %s" % ("YES" if ok else "no ", k))

    out = {"probe": os.path.basename(__file__), "repo": repo, "controls": v,
           "ledger_entries": len(ledger), "hashes_recorded": len(checked),
           "history": {os.path.basename(p): [{k: r[k] for k in ("short", "when", "subject",
                                                                "sha256")} for r in rows]
                       for p, rows in hist.items()},
           "findings": findings,
           "question_credit": "@qingkong66, deepseek-ai/DeepSeek-V3#1591 comment 5426973801: "
                              "'CI can pin the files, but it cannot catch whether the ledger "
                              "description matches the actual revisions.'",
           "gap": "integrity/calibration_dataset_check.py runs C01-C10 and none of them opens "
                  "CHANGELOG.jsonl or reads git history"}
    json.dump(out, io.open(os.path.join(HERE, "does_the_ledger_match_the_history.result.json"),
                           "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return 0 if all(v.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
