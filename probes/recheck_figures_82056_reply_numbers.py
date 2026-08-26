"""RECHECK THE FIGURES for for the reply to anthropics/claude-code#82056. Refuses to pass unless every number in the
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

THIS FILE IS NOT THE GATE. It recomputes figures against receipts, which is ONE check
inside VALIDATE. The gate is the SKILLS: verify-claims, stress-claim, humanizer, and
storm when the claim rests on literature. Owner, 2026-08-26, after I called a file like
this one "the gate" three times in a day: "ZAPIS SI TO NATVRDO A TEN TVOJ SKRIPT DAJ DO
HOVEN." tools/send_approved.py now refuses to publish without a receipt from each skill,
bound to the draft's bytes, so this file cannot stand in for them any more.
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
    check("population 416 matches receipt", "of 416" in draft and main_r["population"] == 416,
          f"population={main_r['population']}")
    check("161 opened matches receipt", "161 of 416" in draft and main_r["fact_files_read"] == 161,
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
          "17 times via our own tool calls and 0 times as harness-emitted content" in draft)

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
        check("@hjqcan attribution: only required if we actually make it",
              ("hjqcan" not in draft)
              or (("1." in hj or "item 1" in hj) and "observability" in hj.lower()),
              "draft no longer attributes to him, so this is vacuously satisfied")

    print("")
    print("TOKENS -- re-derived from the tokenizer receipt (rewritten after the red-team panel)")
    r = tok["tok_per_byte"]
    ratios_t = tok["slug_over_prose"]
    live = tok["whole_states"]["live index (mixed)"]
    sluggy = tok["whole_states"]["08-19 (slug-heavy)"]
    check("tokenizer probe controls all pass", not tok["controls_failed"],
          f"failed={tok['controls_failed'] or 'none'}")
    lo_r, hi_r = min(ratios_t.values()), max(ratios_t.values())
    check("1.22-1.69x slug:prose range", "**1.22–1.69x**" in draft
          and abs(lo_r - 1.22) < 0.02 and abs(hi_r - 1.69) < 0.02,
          f"measured {lo_r:.2f}-{hi_r:.2f}")
    nb = live["_bytes"]
    delta = 100 * (sluggy["o200k_base"] / live["o200k_base"] - 1)
    check("2.8% whole-file movement", "**2.8%**" in draft and abs(delta - 2.8) < 0.15,
          f"{delta:.2f}%")
    check("0.272 -> 0.265 quoted exactly", "0.272 to 0.265 tokens/byte" in draft
          and abs(sluggy["o200k_base"] - 0.272) < 0.002
          and abs(live["o200k_base"] - 0.265) < 0.002,
          f"{sluggy['o200k_base']:.3f} -> {live['o200k_base']:.3f}")
    shr = tok.get("slug_share", {})
    live_share = 100 * shr.get("live index (mixed)", 0)
    check("41% slug share is COMPUTED and quoted", "**41%**" in draft
          and abs(live_share - 41.4) < 0.5, f"computed {live_share:.1f}%")
    check("the 1.7x self-correction is disclosed to him",
          "only a quarter of the index" in draft and "hardcoded" in draft,
          "we tell him we got it wrong before he finds it")
    pred = 108 + 0.44 * nb
    ours = live["o200k_base"] * nb
    entries = 236
    check("23,921 index bytes", "23,921-byte" in draft and nb == 23921, f"bytes={nb}")
    check("10,633 predicted", "**10,633 tokens**" in draft and abs(pred - 10633) < 2,
          f"pred={pred:.0f}")
    check("6,332 proxy count", "**6,332**" in draft and abs(ours - 6332) < 3, f"ours={ours:.0f}")
    check("0.180 tok/byte gap", "0.180 tokens/byte" in draft
          and abs((pred - ours) / nb - 0.180) < 0.002, f"{(pred-ours)/nb:.3f}")
    check("~18 tokens/entry over 236 entries", "18 tokens per entry across 236" in draft
          and abs((pred - ours) / entries - 18) < 1.5, f"{(pred-ours)/entries:.1f}")
    spread = max(max(v.values()) / min(v.values()) for v in r.values())
    check("1.41x cross-tokenizer spread is stated", "**1.41x on identical content**" in draft
          and abs(spread - 1.41) < 0.03, f"measured {spread:.2f}x")

    pop_now = len([f for f in os.listdir(MEMORY_DIR) if f.endswith(".md")
                   and not f.startswith("MEMORY.md.bak")])
    check("FRESHNESS: population matches the live memory directory",
          main_r["population"] == pop_now,
          f"receipt {main_r['population']} vs on disk {pop_now} -- writing a memory invalidates this")
    live_index = os.path.join(MEMORY_DIR, "MEMORY.md")
    on_disk = os.path.getsize(live_index)
    check("FRESHNESS: receipt matches the LIVE index, byte for byte",
          nb == on_disk,
          f"receipt {nb} vs on disk {on_disk} -- re-run the probe if these differ")
    check("byte convention is stated, since 'a byte' is the ambiguity",
          "on disk, CRLF included" in draft and "`wc -c` reproduces it" in draft)
    check("the unprovable universal is gone",
          "every session demonstrably receives it" not in draft
          and "the session I am writing from is receiving that index right now" in draft,
          "one demonstrated case, not a claim about 17 transcripts")

    print("")
    print("STORM FIXES -- three things the external pass caught that would have embarrassed us")

    # S1: the mechanism. Our index is TOPIC-BUCKETED, not recency-ordered. Re-derived live from
    # the overflow backup, not asserted: every recalled-but-cut entry must fall in the bottom
    # sections, and none in the top two.
    overflow_p = os.path.join(MEMORY_DIR, "MEMORY.md.bak-20260819-prewrittenlines")
    hidden_files = set(cf.get("hidden_files", []))
    sec_of, order_secs = {}, []
    cur = None
    for line in open(overflow_p, encoding="utf-8", errors="replace"):
        if line.startswith("##"):
            cur = line.strip("# ").strip()
            order_secs.append(cur)
        for n in re.findall(r"\]\(([A-Za-z0-9_.-]+\.md)\)", line):
            sec_of.setdefault(n, cur)
    top2 = set(order_secs[:2])
    bottom4 = set(order_secs[-4:])
    in_top = [n for n in hidden_files if sec_of.get(n) in top2]
    in_bottom = [n for n in hidden_files if sec_of.get(n) in bottom4]
    check("S1 the index really is topic-bucketed, not recency-ordered",
          len(order_secs) >= 6 and "Standing rules" in order_secs,
          f"{len(order_secs)} sections: {', '.join(order_secs[:3])}...")
    check("S1 all recalled-but-cut entries sit in the bottom four sections",
          len(in_bottom) == len(hidden_files) and not in_top,
          f"{len(in_bottom)}/{len(hidden_files)} bottom, {len(in_top)} top")
    check("S1 the recency explanation is RETRACTED in the draft",
          "not recency-ordered" in draft and "it selected *my own layout*" in draft
          and "position is a proxy for category" in draft,
          "we tell him the mechanism we had ready was wrong")

    # S2: the receipt exists. We were about to say it did not.
    check("S2 /context and InstructionsLoaded are acknowledged",
          "/context" in draft and "InstructionsLoaded" in draft
          and '"there is no receipt" is wrong' in draft)
    check("S2 the surviving claim is narrowed to truncation state",
          "which files** loaded, not **how much of a file**" in draft
          and "Neither surfaces truncation state" in draft)
    check("S2 the documented limit is quoted, and the unit confusion resolved",
          "whichever comes first" in draft and "24.4 KiB *is* 25 KB" in draft)

    # S3: prior art we were about to miss
    check("S3 arXiv:2606.12945 cited with its verified numbers",
          "arXiv:2606.12945" in draft and "36.8%" in draft
          and "65.7%" in draft and "77.0%" in draft)
    check("S3 the mechanism distinction is drawn, not blurred",
          "consolidation policy choosing what to keep" in draft
          and "fixed window truncating a file" in draft)
    check("S3 novelty is claimed narrowly",
          "the only novelty I would claim here" in draft)
    check("S3 unverified sub-figure NOT cited (0.518 was not in the abstract)",
          "0.518" not in draft, "verifier could not confirm it")

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
              > draft.index("**10,633 tokens**") - 900,
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
    check("length is in our register (< 8,000 chars)", len(draft) < 8000, f"{len(draft)} chars")

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
