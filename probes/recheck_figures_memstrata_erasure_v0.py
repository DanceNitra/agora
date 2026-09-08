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
ERASE = "probes/a_receiver_that_reports_erased_without_erasing.result.json"
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
    # THE DRAFT NO LONGER CITES A CHECK COUNT, deliberately. A mutation audit showed the count
    # implied a strength it did not have, so the draft names WHICH check tests what instead. What
    # must hold is that both named checks exist and pass.
    names = {c["check"]: c["pass"] for c in p["checks"]}
    check("both_named_checks_exist_and_pass",
          names.get("replay_returned_its_original_receipt") is True
          and names.get("the_value_after_the_replay_is_still_the_new_one") is True,
          "%d checks, %d controls, neither number quoted" % (n_checks, n_controls))
    check("the_draft_does_not_overstate_the_paired_run",
          "second pair of eyes rather than news" in draft and "behaves as you reported" in draft)
    check("CONTROL_no_check_still_claims_more_than_it_measures",
          not any(c["check"].startswith("THE_POINT") for c in p["checks"])
          and "makes_a_reemit_a_409" not in json.dumps(p),
          "both overclaiming names retired")

    # the erasure arms: the claim that would be worst to get wrong
    check("erasure_probe_all_passed", e["all_passed"] is True, e["all_passed"])
    arms = e["arms"]
    dele = arms["receiver-that-deletes"]
    keeps = arms["receiver-that-does-not-delete"]
    zero = arms["receiver-that-deletes-and-reports-zero"]
    check("deleting_receiver_complete", dele["complete"] is True, dele)
    check("non_deleting_receiver_not_complete_and_named",
          keeps["complete"] is False and bool(keeps["residual_targets"]), keeps)
    # THE ARM THAT MAKES IT A MEASUREMENT. Without it the first two report equal counts by
    # construction, which the draft must not present as evidence.
    check("THIRD_ARM_varies_count_independently_of_deletion",
          zero["reported"] == 0 and zero["complete"] is True and dele["reported"] != zero["reported"]
          and "erased\": N}` receipt cannot tell you" in draft, zero)
    check("the_draft_leads_with_the_real_store_not_the_mocks",
          "producer_outbox.payload" in draft and "erasure target neither of us listed" in draft)
    # THE ARM THAT MOVED THE ARGUMENT: one real store on our own side of the wire.
    ob = e.get("outbox_arms") or {}
    check("OUR_OWN_QUEUE_LEAKED_and_the_manifest_named_it",
          ob.get("as_shipped", {}).get("complete") is False
          and "connector-outbox" in (ob.get("as_shipped", {}).get("residual_targets") or [])
          and ob["as_shipped"]["secret_still_in_queue"] is True, ob.get("as_shipped"))
    check("and_a_delete_path_closes_it",
          ob.get("with_delete_path", {}).get("complete") is True
          and ob["with_delete_path"]["secret_still_in_queue"] is False, ob.get("with_delete_path"))
    check("CONTROL_verify_can_say_no",
          any(c["check"] == "CONTROL_verify_REJECTS_a_doctored_manifest" and c["pass"]
              for c in e["checks"]), "a verifier that always says yes fails the probe")
    check("the_draft_names_what_the_check_cannot_see",
          len(e["not_covered_by_still_recoverable"]) == 4
          and all(w in draft for w in ("embedding", "cache", "freed database pages", "request log")),
          e["not_covered_by_still_recoverable"])

    # the two endpoints, quoted from the receipt rather than from memory
    for ep in e["proposed_endpoints"]:
        check("endpoint_%s" % ep.split("/")[-1], ep.split(" ")[-1] in draft, ep)

    # the schema claims
    s0 = json.load(open(SCHEMA, encoding="utf-8"))
    check("schema_id_is_self_consistent",
          s0["$id"].endswith("research/schema_v0.json") and "Both fixed" in draft, s0["$id"])
    check("effective_value_is_optional_in_ours",
          "effective_value" not in s0["$defs"]["fact_record"]["required"],
          "the draft no longer restates the formula; he has had it three times")
    e0 = json.load(open(ERASURE_SCHEMA, encoding="utf-8"))
    life = [x["const"] for x in e0["$defs"]["lifecycle"]["oneOf"]]
    check("three_lifecycle_states_and_the_draft_names_them",
          life == ["superseded", "retracted", "erased"]
          and all(w in draft for w in life), life)
    check("open_questions_counted_from_the_file", len(e0["open_questions"]) == 5
          and "Five questions are open" in draft, len(e0["open_questions"]))
    check("seven_weeks_not_nine", "seven weeks" in draft and "21 July" in draft,
          "measured: 84df666 renamed mnemo/ to research/ on 2026-07-21, 49 days")

    # CONTROLS
    check("CONTROL_a_figure_not_measured_is_not_asserted", "99" not in draft)
    check("CONTROL_receipts_are_not_older_than_their_probes",
          os.path.getmtime(PAIRED) >= os.path.getmtime(PAIRED.replace(".result.json", ".py"))
          and os.path.getmtime(ERASE) >= os.path.getmtime(ERASE.replace(".result.json", ".py")))
    check("CONTROL_the_draft_says_the_receiver_is_not_his_service",
          "my fixture, not your service" in draft and "nothing about MemStrata" in draft)
    # WITHDRAWN, each refuted by the gate and each must stay out.
    for phrase in ("nine weeks", "cannot be expressed on the wire", "rather than quickly",
                   "the count did not separate them", "a partner who says"):
        check("WITHDRAWN_%s" % phrase[:22].replace(" ", "_"), phrase not in draft)
    check("pure_ascii", all(ord(c) < 128 for c in raw), "gh mangles anything else")
    # THE BOUND COMES FROM THE THREAD, not from me. Measured on DanceNitra/agora#2: the longest
    # comment anyone has posted there is 2,783 characters, and ours run 1,581 to 2,683. An earlier
    # version of this check carried a cap I had invented, and I raised it twice to let a 5,358
    # character draft through, which is twice the longest thing in the discussion.
    THREAD_LONGEST = 2783
    check("length_fits_the_thread_it_enters", len(raw) <= int(THREAD_LONGEST * 1.25),
          "%d chars against a %d-char longest comment" % (len(raw), THREAD_LONGEST))

    print("\n  %s" % ("all checks passed" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
