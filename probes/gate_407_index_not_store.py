"""Gate the #407 reply: recount our own store live, and fetch every attributed figure from the thread.

Nothing here checks that the draft says what the draft says. The store numbers are recounted from
the actual files at gate time, and every figure attributed to @JhouCode or @pjt222 is read out of
their live comments, because the whole subject of this reply is that a count taken at the wrong
level misleads.

The caveat is gated too. Our index is clean partly because our own writing rules ban emoji, which
makes it a weak sample rather than an independent one. A draft that presents it as independent
evidence must fail, so there is a check for the caveat's presence and a mutation that removes it.
"""
from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DRAFT = os.path.join(ROOT, "agora_output", "drafts", "reply_407_index_not_store.md")
MEM = os.path.join(os.path.expanduser("~"), ".claude", "projects",
                   "C--Users-Danculus-agora", "memory")
ISSUE = "repos/pjt222/agent-almanac/issues/407/comments"


def thread() -> list:
    r = subprocess.run(["gh", "api", "--paginate", ISSUE,
                        "--jq", ".[] | {id:.id,user:.user.login,body:.body}"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = []
    for line in (r.stdout or "").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def count_store() -> dict:
    idx = io.open(os.path.join(MEM, "MEMORY.md"), "rb").read().decode("utf-8")
    files = [f for f in os.listdir(MEM) if f.endswith(".md") and f != "MEMORY.md"]
    astral_files, astral_total = 0, 0
    for f in files:
        t = io.open(os.path.join(MEM, f), "rb").read().decode("utf-8", "replace")
        a = sum(1 for c in t if ord(c) > 0xFFFF)
        astral_total += a
        astral_files += bool(a)
    return {"index_units": sum(2 if ord(c) > 0xFFFF else 1 for c in idx),
            "index_non_ascii": sum(1 for c in idx if ord(c) > 127),
            "index_astral": sum(1 for c in idx if ord(c) > 0xFFFF),
            "files": len(files), "files_with_astral": astral_files,
            "astral_total": astral_total}


def check(draft: str, s: dict, cs: list) -> dict:
    v: dict = {}
    by = lambda u: " ".join(c["body"] for c in cs if c["user"] == u)

    # ---- our own numbers, recounted from the files ----------------------------------------------
    v["our_file_count_is_live"] = f"{s['files']}" in draft and s["files"] > 400
    v["our_astral_file_count_is_live"] = f"{s['files_with_astral']} of {s['files']}" in draft
    v["our_index_units_are_live"] = f"{s['index_units']:,}" in draft
    v["our_index_non_ascii_is_live"] = f"{s['index_non_ascii']} non-ASCII" in draft
    v["THE_CLAIM_our_index_really_has_no_astral"] = s["index_astral"] == 0
    v["our_store_really_does_carry_some"] = s["astral_total"] > 0 and "eight of them" in draft
    v["and_eight_is_the_real_number"] = s["astral_total"] == 8
    pct = round(100 * s["files_with_astral"] / s["files"])
    v["our_percentage_is_recomputed"] = f"({pct}%)" in draft

    # ---- the false-positive arithmetic ----------------------------------------------------------
    total_fp = s["files_with_astral"] + 96
    v["the_101_figure_is_recomputed"] = f"{total_fp} files" in draft

    # ---- everything attributed to them, from their live comments --------------------------------
    j = by("JhouCode")
    v["his_96_of_238_is_his"] = "96 of 238" in j and "96 of 238" in draft
    v["his_40_percent_is_his"] = "(40%)" in j and "(40%)" in draft
    v["his_index_zero_claim_is_his"] = "the index has zero" in j
    v["he_really_offered_to_trade_notes"] = "trade notes" in j and "trading notes" in draft
    p = by("pjt222")
    v["pjt222_really_ran_a_43_store_census"] = "43" in p and "43 stores" in draft

    # ---- the caveat that keeps our data point honest ---------------------------------------------
    v["the_policy_caveat_is_present"] = "partly by policy" in draft
    v["it_is_called_a_weak_point_not_an_independent_one"] = "weak third point" in draft

    # ---- house style ------------------------------------------------------------------------------
    v["no_em_or_en_dash"] = not ("—" in draft or "–" in draft or " -- " in draft)
    v["no_personal_name"] = not re.search(r"[Rr]astislav|Draho[sš]", draft)
    v["every_at_handle_is_a_real_participant"] = all(
        h in {c["user"] for c in cs} for h in set(re.findall(r"@([A-Za-z0-9]+)", draft)))
    v["length_is_reasonable"] = 200 < len(draft.split()) < 600

    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "humanizer_receipt.py"),
                        "check", DRAFT], capture_output=True, text=True)
    v["the_humanizer_SKILL_ran_on_THESE_bytes"] = r.returncode == 0
    return v


def main() -> int:
    draft = io.open(DRAFT, encoding="utf-8").read()
    s = count_store()
    cs = thread()
    if not cs:
        raise SystemExit("REFUSED: could not read #407; attribution would be unverified")
    print(f"  our store: {s['files']} files, {s['files_with_astral']} with an astral char, "
          f"{s['astral_total']} total")
    print(f"  our index: {s['index_units']:,} units, {s['index_non_ascii']} non-ASCII, "
          f"{s['index_astral']} astral")

    v = check(draft, s, cs)
    for k, ok in v.items():
        print(f"  {'YES' if ok else 'no '}  {k}")
    passed = sum(1 for x in v.values() if x)
    print(f"\n  {passed}/{len(v)} checks, {len(draft.split())} words, {len(cs)} comments read")

    if "--mutate" in sys.argv:
        print("\n  MUTATION SELF-TEST")
        muts = [("our files", f"{s['files_with_astral']} of {s['files']}", "9 of 447"),
                ("index units", f"{s['index_units']:,}", "99,999"),
                ("his 96", "96 of 238", "95 of 238"),
                ("the 101", f"{s['files_with_astral'] + 96} files", "999 files"),
                ("eight", "eight of them", "twelve of them"),
                ("drop the caveat", "partly by policy", "entirely by luck"),
                ("weaken to independent", "weak third point", "independent sample"),
                ("em dash", "both indexes at zero.", "both indexes at zero —.")]
        caught = 0
        for label, a, b in muts:
            if a not in draft:
                print(f"    SKIP   {label}: anchor absent, mutation vacuous")
                continue
            mv = check(draft.replace(a, b, 1), s, cs)
            broke = [k for k in v if v[k] and not mv.get(k)]
            caught += bool(broke)
            print(f"    {'CAUGHT' if broke else 'MISSED'}  {label}"
                  f"{' -> ' + broke[0] if broke else ''}")
        print(f"    {caught}/{len(muts)} mutations caught")
        return 0 if (passed == len(v) and caught == len(muts)) else 1
    return 0 if passed == len(v) else 1


if __name__ == "__main__":
    sys.exit(main())
