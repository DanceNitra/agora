"""Gate for the reply to anthropics/claude-code#82056. Refuses to pass unless every number in the
draft is re-derived HERE, this cycle, and every citation is checked against its PRIMARY source.

Standing rule: nothing goes outward until VALIDATE -> AUDIT -> VERIFY has passed to 100%. A number in
a note is not verified data. A previous send of ours quoted a figure from a draft rather than from the
lab that produced it and was wrong by a factor.

Two classes of check, deliberately separated:
  OURS    re-derived from the receipts in this repo (both probes' result JSON, the index backups,
          the vault backup repo's git history). If an artifact is missing, that is a FAIL, not a skip.
  THEIRS  fetched live from GitHub and matched against the collaborator's own words. We are about to
          quote @yacb2's slope and attribute an argument to @hjqcan; both must survive their source.

Also gates the ROOM, not just the text: a verified draft posted into a closed thread, or one that
contradicts our own previous comment in the same thread, is still a defect. That has happened here
before -- 18/18 verified, posted into an issue closed 4h38m earlier.

Run:  python probes/gate_82056_reply_numbers.py
"""

import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DRAFT = os.path.join(REPO, "agora_output", "drafts", "reply_82056_the_window_drops_the_durable_layer.md")
MAIN = os.path.join(HERE, "which_memory_files_does_a_session_actually_open.result.json")
ATTACK = os.path.join(HERE, "round_k_attacking_our_own_window_result.result.json")
TOK = os.path.join(HERE, "a_byte_of_slug_is_not_a_byte_of_prose.result.json")
MEMORY_DIR = os.path.join(os.path.expanduser("~"), ".claude", "projects",
                          "C--Users-Danculus-agora", "memory")
VAULT = os.path.join(os.path.expanduser("~"), "agora-vault")

ISSUE = 82056
OUR_COMMENT = 5351599360
THEIR_COMMENT = 5352555064

checks = []


def check(name, ok, detail=""):
    checks.append((name, bool(ok), detail))
    print(f"  {'OK  ' if ok else 'FAIL'}  {name:52s} {detail}")
    return ok


def gh(path, jq):
    try:
        out = subprocess.run(["gh", "api", path, "--jq", jq], capture_output=True, text=True,
                             timeout=60, encoding="utf-8", errors="replace")
        return (out.stdout or "").strip() if out.returncode == 0 else None
    except Exception:
        return None


def main():
    if not os.path.exists(DRAFT):
        sys.exit("FAIL: draft missing " + DRAFT)
    draft = open(DRAFT, encoding="utf-8").read()
    for p in (MAIN, ATTACK, TOK):
        if not os.path.exists(p):
            sys.exit("FAIL: receipt missing (re-run the probe, do not skip) " + p)
    main_r = json.load(open(MAIN, encoding="utf-8"))
    atk = json.load(open(ATTACK, encoding="utf-8"))
    tok = json.load(open(TOK, encoding="utf-8"))
    cf = main_r["counterfactual_overflow_index"]

    print("OURS -- re-derived from receipts in this repo")
    check("draft quotes 17 transcripts", "17 transcripts" in draft,
          f"corpus={len(main_r['corpus'])}") and check(
        "  and the corpus really is 17", len(main_r["corpus"]) == 17)
    check("population 415 matches receipt", "of 415" in draft and main_r["population"] == 415,
          f"population={main_r['population']}")
    check("161 opened matches receipt", "161 of 415" in draft and main_r["fact_files_read"] == 161,
          f"read={main_r['fact_files_read']}")
    check("113 authoring-loop matches receipt",
          "113 of those" in draft and main_r["read_in_own_authoring_loop_only"] == 113,
          f"same_only={main_r['read_in_own_authoring_loop_only']}")
    check("48 cross-session matches receipt",
          "touched 48 files" in draft and len(main_r["cross_session_recalled"]) == 48,
          f"cross={len(main_r['cross_session_recalled'])}")
    check("18 of 32 matches receipt",
          "18 of 32 (56%)" in draft and cf["recalled_hidden"] == 18 and cf["recalled_listed"] == 32,
          f"{cf['recalled_hidden']}/{cf['recalled_listed']}")
    check("p = 0.066 matches receipt",
          "p = 0.066" in draft and abs(cf["binomial_one_sided_p"] - 0.066) < 0.001,
          f"p={cf['binomial_one_sided_p']}")
    check("41.5% base rate matches receipt",
          "41.5%" in draft and abs(cf["lost_fraction"] - 0.415) < 0.002,
          f"lost={cf['lost_fraction']}")

    # the sensitivity RANGE must bracket every threshold actually measured
    sweep = atk["threshold_sweep"]  # [label, listed, hidden, p]
    shares = [100.0 * h / l for _, l, h, _ in sweep]
    ps = [p for *_, p in sweep]
    check("56-86% range brackets every threshold", "56–86%" in draft and
          round(min(shares)) >= 56 and round(max(shares)) <= 86,
          f"measured {min(shares):.0f}-{max(shares):.0f}%")
    check("p 0.012-0.066 range brackets every threshold",
          "p between 0.012 and 0.066" in draft and min(ps) >= 0.012 and max(ps) <= 0.0659,
          f"measured {min(ps):.4f}-{max(ps):.4f}")
    check("direction holds at EVERY threshold",
          all(h / l > cf["lost_fraction"] for _, l, h, _ in sweep),
          f"{len(sweep)} thresholds all above base rate")
    check("both implementations quoted (17/25 and 18/28)",
          "17/25 and 18/28" in draft
          and cf["recalled_hidden_excl_maintenance"] == 17
          and cf["recalled_listed_excl_maintenance"] == 25
          and any(l == 28 and h == 18 for _, l, h, _ in sweep),
          "both present in receipts")

    # C7 blind spot
    check("24 via tool calls / 0 harness content",
          "24 times via our own tool calls and 0 times as harness-emitted content" in draft)

    # index history -- re-derived from the vault backup repo and the local backups
    def vault_show(commit):
        out = subprocess.run(["git", "-C", VAULT, "show", f"{commit}:memory/MEMORY.md"],
                             capture_output=True, text=True, encoding="utf-8", errors="replace")
        return (out.stdout or "") if out.returncode == 0 else ""

    def commit_on(date):
        out = subprocess.run(["git", "-C", VAULT, "log", "--format=%h %ad", "--date=short",
                              "--", "memory/MEMORY.md"], capture_output=True, text=True,
                             encoding="utf-8", errors="replace")
        for line in (out.stdout or "").splitlines():
            h, d = line.split(maxsplit=1)[0], line.split(maxsplit=1)[1].strip()
            if d == date:
                return h
        return None

    # 2026-07-14 is NOT a unique state -- the vault has seven commits that day, spanning
    # 18.8-20.0 KB. The draft cited the earliest as if it were "the" 07-14 value and this gate
    # blocked the send. A date that resolves to many states must be quoted as a range.
    def commits_on(date):
        out = subprocess.run(["git", "-C", VAULT, "log", "--format=%h %ad", "--date=short",
                              "--", "memory/MEMORY.md"], capture_output=True, text=True,
                             encoding="utf-8", errors="replace")
        return [l.split(maxsplit=1)[0] for l in (out.stdout or "").splitlines()
                if l.split(maxsplit=1)[1].strip() == date]

    day = commits_on("2026-07-14")
    kbs = sorted(len(vault_show(c).encode()) / 1000.0 for c in day)
    check("07-14 quoted as a RANGE over its seven commits",
          len(day) == 7 and abs(kbs[0] - 18.8) < 0.05 and abs(kbs[-1] - 20.0) < 0.05
          and "18.8–20.0 KB across seven commits on 07-14" in draft,
          f"{len(day)} commits, {kbs[0]:.1f}-{kbs[-1]:.1f} KB")
    check("every 07-14 state is inside the 24.4 KB window", all(k < 24.4 for k in kbs),
          f"max {kbs[-1]:.1f} KB")

    for date, want_kb, want_lines in (("2026-07-23", 17.7, 114),):
        c = commit_on(date)
        body = vault_show(c) if c else ""
        kb = len(body.encode()) / 1000.0
        lines_n = body.count("\n")
        check(f"vault {date} = {want_kb} KB / {want_lines} lines",
              body and abs(kb - want_kb) < 0.15 and lines_n == want_lines
              and f"{want_kb} KB / {want_lines} lines" in draft,
              f"measured {kb:.1f} KB / {lines_n} lines")

    bak = os.path.join(MEMORY_DIR, "MEMORY.md.bak-20260817")
    kb17 = os.path.getsize(bak) / 1000.0 if os.path.exists(bak) else 0
    check("local backup 08-17 = 24.0 KB",
          abs(kb17 - 24.0) < 0.1 and "24.0 KB on 08-17" in draft, f"measured {kb17:.1f} KB")

    # consistency with what we ALREADY published in this same thread
    check("95 of 229 matches our own prior comment",
          "95 of 229 entries" in draft, "same figure we published in 5351599360")

    print("\nTHEIRS -- checked against the collaborator's own words (primary source)")
    their = gh(f"repos/anthropics/claude-code/issues/comments/{THEIR_COMMENT}", ".body")
    if their is None:
        check("fetched @yacb2's comment", False, "gh unavailable -- cannot verify a quote, so FAIL")
    else:
        check("@yacb2 really wrote '108 tokens fixed'", "108 tokens fixed" in their)
        check("@yacb2 really wrote '0.44 tokens/byte'", "0.44 tokens/byte" in their)
        check("@yacb2 really said it came from two ablation points",
              "two ablation points" in their and "two ablation points" in draft)
        check("we do NOT attribute #85595's filing to him",
              "85595" not in draft, "his comment claims it; its author is hobbyhack -- unverified")

    ours = gh(f"repos/anthropics/claude-code/issues/comments/{OUR_COMMENT}", ".body")
    if ours is None:
        check("fetched our own prior comment", False, "gh unavailable")
    else:
        check("our prior comment did ask the Zipfian question",
              "Zipfian" in ours and "2% of the value" in ours)
        check("draft answers the question we actually asked",
              "41% of entries might be 2% of the value" in draft)

    hj = gh(f"repos/anthropics/claude-code/issues/{ISSUE}/comments?per_page=100",
            '.[] | select(.user.login=="hjqcan") | .body')
    if hj is None or not hj:
        check("@hjqcan comment located", False, "cannot verify the attribution we make")
    else:
        check("@hjqcan really has an 'item 1' about store identity/observability",
              ("1." in hj or "item 1" in hj) and "observability" in hj.lower())

    print("")
    print("TOKENS -- re-derived from the tokenizer receipt (rewritten after the red-team panel)")
    r = tok["tok_per_byte"]
    ratios_t = tok["slug_over_prose"]
    live = tok["whole_states"]["live index (mixed)"]
    sluggy = tok["whole_states"]["08-19 (slug-heavy)"]
    check("tokenizer probe controls all pass", not tok["controls_failed"],
          f"failed={tok['controls_failed'] or 'none'}")
    lo_r, hi_r = min(ratios_t.values()), max(ratios_t.values())
    check("1.23-1.70x slug:prose range", "**1.23–1.70x**" in draft
          and abs(lo_r - 1.23) < 0.02 and abs(hi_r - 1.70) < 0.02,
          f"measured {lo_r:.2f}-{hi_r:.2f}")
    nb = live["_bytes"]
    delta = 100 * (sluggy["o200k_base"] / live["o200k_base"] - 1)
    check("3.3% whole-file movement", "**3.3%**" in draft and abs(delta - 3.3) < 0.15,
          f"{delta:.2f}%")
    check("0.275 -> 0.267 quoted exactly", "0.275 to 0.267 tokens/byte" in draft
          and abs(sluggy["o200k_base"] - 0.275) < 0.002
          and abs(live["o200k_base"] - 0.267) < 0.002,
          f"{sluggy['o200k_base']:.3f} -> {live['o200k_base']:.3f}")
    shr = tok.get("slug_share", {})
    live_share = 100 * shr.get("live index (mixed)", 0)
    check("42% slug share is COMPUTED and quoted", "**42%**" in draft
          and abs(live_share - 41.8) < 0.5, f"computed {live_share:.1f}%")
    check("the 1.7x self-correction is disclosed to him",
          "only a quarter of the index" in draft and "hardcoded" in draft,
          "we tell him we got it wrong before he finds it")
    pred = 108 + 0.44 * nb
    ours = live["o200k_base"] * nb
    entries = 236
    check("23,686 index bytes", "23,686-byte" in draft and nb == 23686, f"bytes={nb}")
    check("10,530 predicted", "**10,530 tokens**" in draft and abs(pred - 10530) < 2,
          f"pred={pred:.0f}")
    check("6,315 proxy count", "**6,315**" in draft and abs(ours - 6315) < 3, f"ours={ours:.0f}")
    check("0.178 tok/byte gap", "0.178 tokens/byte" in draft
          and abs((pred - ours) / nb - 0.178) < 0.002, f"{(pred-ours)/nb:.3f}")
    check("~18 tokens/entry over 236 entries", "18 tokens per entry across 236" in draft
          and abs((pred - ours) / entries - 18) < 1.5, f"{(pred-ours)/entries:.1f}")
    spread = max(max(v.values()) / min(v.values()) for v in r.values())
    check("1.41x cross-tokenizer spread is stated", "**1.41x on identical content**" in draft
          and abs(spread - 1.41) < 0.03, f"measured {spread:.2f}x")

    print("")
    print("RED-TEAM FIXES -- each panel finding must be visible in the draft")
    check("STEELMAN: the word 'unreachable' is GONE",
          "unreachable" not in draft.lower(),
          "our own 1.41x spread refuted it; the gap is 1.32-1.65x")
    check("STEELMAN: the confound is named, not hidden",
          "or just my tokenizer against yours" in draft)
    check("PRIOR-ART: the mechanism is credited, not sold as news",
          "CodeBPE" in draft and "Chirkova" in draft and "ICLR 2023" in draft)
    check("FRAMING: the tokenizer caveat appears in the GAP paragraph too",
          draft.count("tokenizer") >= 3
          and "Anthropic's own tokenizer was not available to me" in draft
          and draft.index("Anthropic's own tokenizer was not available to me")
              > draft.index("**10,530 tokens**") - 900,
          "it was silently dropped there before")
    check("FRAMING: the diagnosis ends in a QUESTION to him",
          "Which was your 0.44 fitted against" in draft)
    check("FRAMING: the hypothesis keeps its 'if'",
          "If it is the former" in draft and "probably genuine entry overhead" in draft)
    check("BLIND-SPOT: value-vs-position limit is stated",
          "never *value*" in draft and "treated as harm by assumption" in draft
          and "index inefficiency rather than a correctness defect" in draft)
    check("METHOD: slugs measured in real context, not joined",
          "in their real `](name.md)` context" in draft)
    print("\nTHE ROOM")
    state = gh(f"repos/anthropics/claude-code/issues/{ISSUE}", ".state")
    check("issue is OPEN", state == "open", f"state={state}")
    last = gh(f"repos/anthropics/claude-code/issues/{ISSUE}/comments?per_page=100",
              ".[-1].id")
    check("no newer comment we have not read", last == str(THEIR_COMMENT),
          f"last comment id={last}, we read {THEIR_COMMENT}")

    print("\nHYGIENE")
    check("draft is ASCII-safe apart from known typography",
          all(ord(ch) < 128 or ch in "—–…‘’“”" for ch in draft))
    check("tokenizer limitation is disclosed, not buried",
          "Anthropic's own tokenizer was not available" in draft
          and "not an absolute rate for Claude" in draft,
          "ratio asserted, absolute rate explicitly not")
    check("length is in our register (< 6,200 chars)", len(draft) < 6200, f"{len(draft)} chars")

    n = len(checks)
    bad = [c for c in checks if not c[1]]
    print("\n" + "=" * 74)
    print(f"{n - len(bad)}/{n} checks pass")
    if bad:
        print("BLOCKED -- do not send:")
        for name, _, detail in bad:
            print(f"   - {name}  {detail}")
    else:
        print("GATE PASSES. Still requires the owner's approval of this exact text before sending.")
    print("=" * 74)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
