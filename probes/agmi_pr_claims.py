"""Every figure and named fact in the 2026-09-24 PR description for tech4biz-yasha/agmi, recomputed.

Each claim reads its value from a source file AND checks that the PR body states it, so a figure that
drifts in either place fails. Sources: session V's measurement outputs (default row on his main and on
our branch, the label row, the key row), the CI logs of the fork run and main's run, the branch commit,
and the adapter and test files at 3887e39. tools/recompute_receipt.py runs this and mutates the inputs;
inputs come only from AGORA_INPUT_DIR.
"""
import io
import json
import os
import re

D = os.environ["AGORA_INPUT_DIR"]


def text(name):
    try:
        return io.open(os.path.join(D, name), encoding="utf-8", errors="replace").read()
    except Exception:
        return ""


body = text("pr_body.md")
main_default, ours_default = text("main_default.txt"), text("ours_default.txt")
label, key = text("inspeximus-defended.txt"), text("inspeximus-defended-key.txt")
ci_fork, ci_main = text("ci_fork_36051660064.txt"), text("ci_main_36046813204.txt")
adapter, tests = text("inspeximus_recall.py"), text("test_inspeximus_recall.py")
try:
    commit = json.loads(text("branch_commit.json"))
except Exception:
    commit = {}

WRITE_CELLS = ["memory_injection", "retrieval_hijack", "indirect_prompt_injection",
               "update_poisoning", "metadata_poisoning"]


def claim(cid, ok, desc, stated):
    ok = bool(ok) and all(s in body for s in stated)
    print("CLAIM %s %s %s" % (cid, "PASS" if ok else "FAIL", desc))


def row(txt, cell):
    m = re.search(r"^\s*%s\s+@v\d+\s+(\S+)\s+.*$" % cell, txt, re.M)
    return m.group(0) if m else ""


def channel(line, name):
    m = re.search(r"%s: ([^;)]*)" % name, line)
    return m.group(1).strip() if m else None


def default_like(line, ref, name):
    return channel(line, name) is not None and channel(line, name) == channel(ref, name)


claim("base", commit.get("parents") == ["d5e0c56c7d8ebfa54890cf243e956b4b81a842c3"]
      and commit.get("sha", "").startswith("3887e39") and len(commit.get("files", [])) == 3,
      "one commit 3887e39 on top of main d5e0c56", ["One commit on top of main (d5e0c56)"])
claim("default_identical", main_default and main_default.split("\n", 1)[1] == ours_default.split("\n", 1)[1],
      "the default row on our branch matches main's byte for byte", ["prints the same bytes as main"])
lab_ext = all(channel(row(label, c), "external") == "kept out 5 of 5" for c in WRITE_CELLS)
lab_rest = all(default_like(row(label, c), row(main_default, c), n)
               for c in WRITE_CELLS for n in ("laundered", "agent-laundered"))
claim("label_row", lab_ext and lab_rest,
      "label row: external kept out 5/5 on every write cell, the other channels equal the default row",
      ["label row, 5 write cells    kept out   = default   = default"])
key_two = all(channel(row(key, c), n) == "kept out 5 of 5" for c in WRITE_CELLS for n in ("external", "laundered"))
key_third = all(default_like(row(key, c), row(main_default, c), "agent-laundered") for c in WRITE_CELLS)
claim("key_row", key_two and key_third,
      "key row: external and laundered kept out 5/5, agent-laundered equals the default row",
      ["key row, 5 write cells      kept out   kept out    = default"])
claim("bleed_safe", "safe" in row(label, "cross_session_bleed") and "safe" in row(key, "cross_session_bleed"),
      "cross_session_bleed is safe in both rows", ["cross_session_bleed is safe in both rows"])
claim("all_vulnerable", all("VULNERABLE" in row(t, c) for t in (label, key) for c in WRITE_CELLS),
      "every write cell is VULNERABLE in both rows", ["Every write cell is VULNERABLE in both rows"])
claim("ci_fork", ci_fork.count("108 passed, 2 skipped") == 2 and "11.71s" in ci_fork and "11.87s" in ci_fork,
      "fork run: 108 passed, 2 skipped, test step 11.71 s and 11.87 s",
      ["108 passed, 2 skipped", "11.7 s and", "11.9 s on the fork run"])
claim("ci_main", ci_main.count("103 passed, 2 skipped") == 2 and "9.91s" in ci_main and "36.61s" in ci_main,
      "main run: 103 passed, 2 skipped, test step 9.91 s and 36.61 s",
      ["main: 103 and the same 2", "9.9 s and 36.6 s"])
claim("args_default_off", all(re.search(p, adapter) for p in (r"provenance: bool = False",
                                                              r"trust_seeds: set \| None = None",
                                                              r"attest: bool = False")),
      "the three adapter arguments default off", ["three optional arguments, all off by default"])
claim("keyring_before_sign", re.search(r"if self\.attest and KEYRING\.verify\(", adapter) is not None,
      "the adapter signs only what KEYRING verifies", ["only what agmi.signing.KEYRING verifies"])
names = ["test_the_new_arguments_default_off", "test_label_row_holds_on_the_external_channel_only",
         "test_key_row_also_holds_on_the_laundered_channel", "test_key_row_trusts_the_seeded_key_not_any_key",
         "test_a_trust_root_no_genuine_write_reaches_earns_no_cell"]
claim("five_tests", all(("def %s(" % n) in tests for n in names), "five new tests at 3887e39",
      ["Cost: five more tests"])
