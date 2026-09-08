"""Bind every figure in the EDRN retraction reply to its source.

ONE CHECK INSIDE VALIDATE, NOT THE GATE. Three of the figures are HIS, three are OURS from an
earlier comment, two are the paper's, and four come from our own probe. Each is checked against the
thing it came from, because quoting a collaborator's number back to him wrongly is the worst failure
available in this thread.
"""
import io
import json
import os
import subprocess
import sys

D = "drafts/edrn_retraction_and_scope.md"
R = "probes/the_orbit_result_is_scoped_to_the_uniform_point.result.json"
PAPER = os.path.join(os.environ.get("TMPDIR", "/tmp"), "edrn", "paper_0908.md")


def gh(url):
    """His comments are in Chinese, so the encoding is not optional.

    Without an explicit encoding this decodes as the console codepage, cp1250 here, and raises
    UnicodeDecodeError; every check that quotes his numbers back to him then never runs. It passed
    under `python -X utf8` because that sets the subprocess default too, so the guard worked only for
    whoever happened to launch it with that switch. An empty read is now a refusal rather than a None
    flowing into the comparisons.
    """
    r = subprocess.run(["gh", "api", url, "--jq", ".body"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0 or not r.stdout:
        raise SystemExit(
            "REFUSED: could not read %s (rc=%s). The checks that quote his numbers cannot run, and "
            "passing without them is the failure this file exists to prevent. %s"
            % (url, r.returncode, (r.stderr or "")[:300]))
    return r.stdout


def main():
    raw = io.open(D, encoding="utf-8").read()
    draft = " ".join(raw.split())
    r = json.load(open(R, encoding="utf-8"))
    ok = True

    def check(name, cond, got=""):
        nonlocal ok
        ok = ok and bool(cond)
        print("  %-4s %-54s %s" % ("YES" if cond else "NO", name, got))

    # OURS, from the probe receipt.
    check("1106_pairs", r["pairs"] == 1106 and "1,106 pairs" in draft, r["pairs"])
    check("851_lose_symmetry", r["pairs_losing_symmetry"] == 851
          and "851 of 1,106 pairs lose automorphisms" in draft, r["pairs_losing_symmetry"])
    # I first wrote 348 here, which is the N=6 row of the printed table, not the total across
    # N=4,5,6. The receipt carries the total and the check now reads it rather than a line I copied.
    check("collapse_count_is_the_total_not_one_row",
          r["pairs_collapsing_to_identity"] == 398
          and "398 collapse to the trivial group" in draft
          and "348" not in draft, r["pairs_collapsing_to_identity"])
    check("255_keep", r["pairs_keeping_full_group"] == 255
          and "255 keep the full group" in draft, r["pairs_keeping_full_group"])
    check("the_probe_passed_its_controls", r["all_passed"] is True)

    # THE LETTER NO LONGER WARNS HIM AGAINST OVER-RETRACTING. His own comment scopes the retraction
    # correctly in its point 3, "the other parts of the paper are unaffected", so warning him was
    # telling him not to do what he had already said he was not doing.
    check("does_NOT_warn_him_against_over_retracting",
          "do not let it take" not in draft.lower()
          and "Your point 3, that the rest of the paper is unaffected, is right" in draft)
    # The humanizer removed an X-not-Y construction from this sentence. What the check is for is
    # unchanged: the 255 must be presented as unfinished work, including the admission that the
    # cross-check against his 84 pairs has not been done.
    check("the_255_are_an_open_question_not_a_reassurance",
          "The 255 need a look" in draft
          and "would extend past s=1 for those graphs" in draft
          and "I have not checked whether any of your 84" in draft)
    check("the_non_degeneracy_clause_catch_is_in",
          "non-degeneracy clause does no work" in draft
          and "39 of your own 84 counterexample pairs" in draft)
    check("asks_the_projector_question",
          "ground-manifold projector or a single eigenvector" in draft)
    # The three-quarters claim must follow from those numbers, not be asserted beside them.
    check("three_quarters_is_arithmetic_on_851_over_1106",
          abs(851 / 1106.0 - 0.75) < 0.03 and "three quarters of cases" in draft,
          "%.3f" % (851 / 1106.0))

    # HIS, quoted back to him. These come from his own comment, not from us.
    his = gh("repos/luoxuejian000/edrn-dmrg-verification/issues/comments/5581194066")
    check("his_84_counterexamples_are_his", "84" in his and "84 counterexample edge pairs" in draft)
    check("his_142_graphs_are_his", "142" in his and "across 142 graphs" in draft)
    check("his_45_and_39_split_is_his",
          "45" in his and "39" in his and "45 at a degenerate ground state and 39" in draft)
    # Matched on a line break before, which the rewrite moved. The sentence is what matters.
    check("his_figure_9_is_his", ("图9" in his or "图 9" in his)
          and "Your figure 9 makes it concrete" in draft)

    # THE PAPER'S.
    if os.path.isfile(PAPER):
        paper = io.open(PAPER, encoding="utf-8", errors="replace").read()
        check("the_seeds_42_44_45_and_43_are_the_paper's",
              "seeds 42, 44, and 45" in paper and "seeds 42, 44, 45" in draft
              and "(43)" in draft)
        # THE LETTER TELLS HIM THE s=1 RESULT SURVIVES. That is only true while the paper contains
        # it, so the claim is bound to the paper rather than to a phrase the letter happens to use.
        # The two checks this replaces guarded sentences the rewrite removed, which made them
        # vacuous; the assertion they were reaching for is checked here instead.
        check("the_s1_orbit_result_really_is_in_the_paper",
              "Orbit-resolved mechanism and symmetry constraint" in paper
              and "within-orbit variance vanishes" in paper)
        check("and_the_paper_really_scopes_it_to_the_uniform_point",
              "the Hamiltonian at $s=1$ is invariant under the full edge automorphism group" in paper
              and "The s=1 orbit result is a theorem with a premise" in draft)
    else:
        check("the_paper_was_downloaded_for_checking", False, PAPER)

    # OURS, from our own earlier comment. Getting our own prior number wrong is the same failure.
    prev = gh("repos/luoxuejian000/edrn-dmrg-verification/issues/comments/5572587393")
    check("the_energy_-28.8441898_is_from_our_own_earlier_comment",
          "-28.8441898" in prev and "-28.8441898" in draft)
    check("N_up_7_and_S_z_minus_one_half_are_from_it",
          "N_up = 7" in prev and "N_up=7" in draft and "S_z=-1/2" in draft)
    check("the_continuation_at_k_equals_1_is_from_it",
          "k=1" in prev and "Continuation at k=1" in draft)

    # THREAD CONVENTIONS, both owner-set and both easy to break.
    check("signed_as_agora_and_dancenitra",
          raw.rstrip().endswith("-- Agora, an autonomous research OS (DanceNitra)"))
    check("NO_ai_disclosure_in_this_thread",
          "AI assistance" not in draft and "AI-assisted" not in draft)
    # THE FINITE-SIZE FIGURES, which were in the letter before anything bound them. L2 comes from
    # the paper, the line itself from our own 7 September comment, and the three counts from the
    # gasket construction 3(3^n+1)/2, which is the check that would catch us repeating our own
    # earlier mistake rather than the paper's.
    gasket = tuple(3 * (3 ** n + 1) // 2 for n in (1, 2, 3))
    check("the_gasket_counts_are_6_15_42_by_construction", gasket == (6, 15, 42), gasket)
    check("the_6_15_42_line_is_in_the_draft_and_in_our_earlier_comment",
          "L1 has 6 sites, L2 has 15, L3 has 42" in draft
          and "L1 has 6 sites, L2 has 15, L3 has 42" in " ".join(prev.split()))
    if os.path.isfile(PAPER):
        pp = io.open(PAPER, encoding="utf-8", errors="replace").read()
        # THE FIGURES ARE OUT. The pregate found the spread already quoted four times in this
        # thread, once by Guanghao himself, so repeating it adds nothing. The inference stays and
        # the numbers must now be absent, which is the stricter requirement.
        check("the_depth_spread_figures_are_NOT_restated",
              "0.0874" in pp and "0.1045" in pp
              and "0.0874" not in draft and "0.1045" not in draft
              and "reads like a single" in draft)
        check("and_the_paper_calls_it_manifold_choice_not_statistics",
              "near-degenerate manifold rather than statistical uncertainty" in " ".join(pp.split()))

    check("pure_ascii", all(ord(c) < 128 for c in raw))
    check("no_em_or_en_dash", "—" not in raw and "–" not in raw)
    # He asked us to edit his paper. The rule is propose, never overwrite.
    check("offers_to_mark_up_rather_than_edit",
          "mark up the passages rather than edit them" in draft)

    print("\n  %s" % ("all checks passed" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
