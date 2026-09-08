"""Bind every number in the MemStrata reply to the receipt that produced it.

THIS IS ONE CHECK INSIDE VALIDATE. IT IS NOT THE GATE. The gate is validate, storm where the claim
rests on literature, redteam and verify. A script written beside the draft is not a substitute for
any of them; the last time one passed 28 of 28, an adversarial pass then took the draft apart.

What it can do here: refuse a figure the two probes did not produce, and refuse the two claims that
would be worst to get wrong in front of a collaborator, namely that both partner arms reported the
SAME erased count and that the schema now resolves from the URL it names.
"""
import io
import json
import os
import re
import sys

D = "drafts/memstrata_erasure_v0_reply.md"
PAIRED = "probes/the_old_retry_must_not_restore_the_old_value.result.json"
ERASE = "probes/a_partner_who_says_erased_and_still_answers.result.json"
SCHEMA = "research/schema_v0.json"
ERASURE_SCHEMA = "research/erasure_v0.json"


def main():
    raw = io.open(D, encoding="utf-8").read()
    draft = " ".join(raw.split())
    p = json.load(open(PAIRED, encoding="utf-8"))
    e = json.load(open(ERASE, encoding="utf-8"))
    ok = True

    def check(name, cond, got=""):
        nonlocal ok
        ok = ok and bool(cond)
        print("  %-4s %-50s %s" % ("YES" if cond else "NO", name, got))

    # the paired write
    n_checks = len(p["checks"])
    n_controls = sum(1 for c in p["checks"] if c["check"].startswith("CONTROL"))
    check("paired_probe_all_passed", p["all_passed"] is True, p["all_passed"])
    check("ten_checks", n_checks == 10 and "Ten checks" in draft, n_checks)
    # SIX, and the draft said five until this fired. The count comes from the receipt, not from
    # me: any check whose name starts with CONTROL_ is one, so adding a control updates the
    # number rather than silently making the sentence wrong.
    check("controls_counted_from_the_receipt",
          n_controls == 6 and "six of them controls" in draft, n_controls)
    check("the_point_check_passed",
          any(c["check"].startswith("THE_POINT") and c["pass"] for c in p["checks"]),
          [c["check"] for c in p["checks"] if c["check"].startswith("THE_POINT")])

    # the erasure arms: the claim that would be worst to get wrong
    check("erasure_probe_all_passed", e["all_passed"] is True, e["all_passed"])
    check("honest_arm_complete", e["honest_arm"]["complete"] is True, e["honest_arm"])
    check("lying_arm_not_complete", e["lying_arm"]["complete"] is False, e["lying_arm"])
    check("lying_arm_is_named", bool(e["lying_arm"]["residual_targets"]),
          e["lying_arm"]["residual_targets"])
    same_count = next((c for c in e["checks"]
                       if c["check"] == "CONTROL_both_arms_reported_the_same_erased_count"), None)
    check("BOTH_ARMS_REPORTED_THE_SAME_COUNT",
          same_count is not None and same_count["pass"] and "2 vs 2" in same_count["got"]
          and 'reported the same `{"erased": 2}`' in draft, same_count and same_count["got"])
    check("and_the_draft_says_the_count_did_not_separate_them",
          "the count did not separate them" in draft)

    # the two endpoints, quoted from the receipt rather than from memory
    for ep in e["proposed_endpoints"]:
        check("endpoint_%s" % ep.split("/")[-1], ep.split(" ")[-1] in draft, ep)

    # the schema claims
    s0 = json.load(open(SCHEMA, encoding="utf-8"))
    check("schema_id_is_self_consistent",
          s0["$id"].endswith("research/schema_v0.json") and "research/schema_v0.json" in draft,
          s0["$id"])
    check("effective_value_is_optional_in_ours",
          "effective_value" not in s0["$defs"]["fact_record"]["required"]
          and "my schema marks it optional" in draft,
          s0["$defs"]["fact_record"]["required"])
    e0 = json.load(open(ERASURE_SCHEMA, encoding="utf-8"))
    life = [x["const"] for x in e0["$defs"]["lifecycle"]["oneOf"]]
    check("three_lifecycle_states_and_the_draft_names_them",
          life == ["superseded", "retracted", "erased"]
          and all(w in draft for w in life), life)
    check("four_open_questions", len(e0["open_questions"]) == 4
          and "Four questions I left open" in draft, len(e0["open_questions"]))

    # CONTROLS
    check("CONTROL_a_figure_not_measured_is_not_asserted", "99" not in draft)
    check("CONTROL_receipts_are_not_older_than_their_probes",
          os.path.getmtime(PAIRED) >= os.path.getmtime(PAIRED.replace(".result.json", ".py"))
          and os.path.getmtime(ERASE) >= os.path.getmtime(ERASE.replace(".result.json", ".py")))
    check("CONTROL_the_draft_says_the_receiver_is_not_his_service",
          "not your service" in draft and "says nothing about MemStrata" in draft)
    check("pure_ascii", all(ord(c) < 128 for c in raw), "gh mangles anything else")
    check("length_reasonable", 2000 <= len(raw) <= 5000, "%d chars" % len(raw))

    print("\n  %s" % ("all checks passed" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
