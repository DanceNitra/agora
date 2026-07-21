"""
POSITIVE CONTROL for the self-audit: is "0/32 of our AI's findings survived as an original discovery"
a property of a weak GENERATOR, or of a harsh AUDITOR that relabels anything with a prior-art family
as "textbook"? The 53% "over-framed-but-true" bucket is exactly the auditor's judgment call, so its
false-reframe rate must be measured before "0/32" can be attributed to the generator.

METHOD: a labeled 20-item panel, judged BLIND by the same prior-art/novelty pass used on our own posts.
  - 10 GENUINELY-NOVEL landmark contributions, phrased as fresh "we find" claims, several deliberately
    carrying a tempting prior-art family (PageRank vs eigenvector centrality; Adam vs RMSprop/AdaGrad;
    word2vec vs LSA/distributional semantics; dropout vs ensembling) -- the exact temptation to
    over-relabel that we are testing for.
  - 10 TEXTBOOK results dressed as discoveries (5 of them are OUR OWN over-framed posts: C6=#31 SLRU/ARC,
    C8=#26 ensemble decorrelation, C16=#30 stability-plasticity, C18=#18/#24 Ising tipping, C20=#17
    confidence-grounding), ground-truth TEXTBOOK.
Two independent auditors ran blind (no labels, no split disclosed). Their verdicts are recorded below
(LLM judgments are stochastic; these are our two runs -- re-run to reproduce the DIRECTION, not exact
cells). We report the confusion matrix, the false-reframe rate (novel wrongly demoted) and the miss
rate (textbook passed as novel).

FALSIFIER: if the auditor demoted genuine novelty to "textbook" at a high rate, then "0/32" would be
partly the grader's severity and the self-audit's causal claim ("the generator, not the gate, is why
nothing was novel") would collapse. It did not: false-reframe rate = 0/10 for BOTH auditors.

cloud-free, zero-dependency:  python meta_audit_auditor_roc.py
MIT. Part of Agora / inspeximus (https://github.com/DanceNitra/agora).
"""

NOVEL, TEXTBOOK = "NOVEL", "TEXTBOOK"

# (id, ground_truth, short_label, borderline_novel_with_strong_prior_art)
PANEL = [
    ("C1", NOVEL, "PageRank (vs eigenvector centrality)", True),
    ("C2", TEXTBOOK, "P vs NP / verify-vs-produce asymmetry", False),
    ("C3", NOVEL, "Transformer / attention-only", False),
    ("C4", TEXTBOOK, "pre-registration vs p-hacking (Simmons 2011)", False),
    ("C5", NOVEL, "Adam optimizer (vs RMSprop/AdaGrad)", True),
    ("C6", TEXTBOOK, "SLRU/ARC two-tier cache [our post #31]", False),
    ("C7", NOVEL, "GANs (adversarial generation)", False),
    ("C8", TEXTBOOK, "ensemble error-decorrelation, Krogh-Vedelsby [our #26]", False),
    ("C9", NOVEL, "denoising diffusion models", False),
    ("C10", TEXTBOOK, "correlated samples inflate precision (design effect)", False),
    ("C11", NOVEL, "word2vec analogy embeddings (vs LSA)", True),
    ("C12", TEXTBOOK, "no-optimal-online-cache, Sleator-Tarjan/Belady", False),
    ("C13", NOVEL, "CRISPR-Cas9 programmable editing", False),
    ("C14", TEXTBOOK, "diversity-generation-vs-convergence tradeoff [our #26 sibling]", False),
    ("C15", NOVEL, "Dropout regularization (vs ensembling)", True),
    ("C16", TEXTBOOK, "stability-plasticity dilemma, Grossberg [our #30]", False),
    ("C17", NOVEL, "AlphaFold2 end-to-end structure", False),
    ("C18", TEXTBOOK, "critical-coupling hysteresis = phase transition [our #18/#24]", False),
    ("C19", NOVEL, "nucleoside-modified mRNA-LNP vaccine", False),
    ("C20", TEXTBOOK, "confidence-vs-grounding decoupling = miscalibration [our #17]", False),
]

# Recorded blind verdicts from two independent auditor agents (2026-07-05).
AUDITOR_A = {  # slightly lenient: passed 2 textbook items (C6, C14) as novel
    "C1": NOVEL, "C2": TEXTBOOK, "C3": NOVEL, "C4": TEXTBOOK, "C5": NOVEL, "C6": NOVEL,
    "C7": NOVEL, "C8": TEXTBOOK, "C9": NOVEL, "C10": TEXTBOOK, "C11": NOVEL, "C12": TEXTBOOK,
    "C13": NOVEL, "C14": NOVEL, "C15": NOVEL, "C16": TEXTBOOK, "C17": NOVEL, "C18": TEXTBOOK,
    "C19": NOVEL, "C20": TEXTBOOK,
}
AUDITOR_B = {  # perfect on this panel
    "C1": NOVEL, "C2": TEXTBOOK, "C3": NOVEL, "C4": TEXTBOOK, "C5": NOVEL, "C6": TEXTBOOK,
    "C7": NOVEL, "C8": TEXTBOOK, "C9": NOVEL, "C10": TEXTBOOK, "C11": NOVEL, "C12": TEXTBOOK,
    "C13": NOVEL, "C14": TEXTBOOK, "C15": NOVEL, "C16": TEXTBOOK, "C17": NOVEL, "C18": TEXTBOOK,
    "C19": NOVEL, "C20": TEXTBOOK,
}

GT = {pid: gt for pid, gt, _, _ in PANEL}


def score(name, verdicts):
    novels = [p for p in GT if GT[p] == NOVEL]
    texts = [p for p in GT if GT[p] == TEXTBOOK]
    # false-reframe: a genuinely NOVEL item the auditor called TEXTBOOK (the harsh-auditor failure)
    false_reframe = [p for p in novels if verdicts[p] == TEXTBOOK]
    # miss: a TEXTBOOK item the auditor passed as NOVEL (the lenient failure)
    miss = [p for p in texts if verdicts[p] == NOVEL]
    correct = sum(1 for p in GT if verdicts[p] == GT[p])
    # false-reframe on the BORDERLINE novels (strong prior-art family = the real temptation)
    bl = [p for p, gt, _, b in PANEL if b]
    bl_reframed = [p for p in bl if verdicts[p] == TEXTBOOK]
    print(f"--- {name} ---")
    print(f"  accuracy {correct}/{len(GT)}")
    print(f"  FALSE-REFRAME rate (genuine novel -> 'textbook'): {len(false_reframe)}/{len(novels)}"
          f"  {false_reframe if false_reframe else '(none)'}")
    print(f"  miss rate (textbook -> 'novel'): {len(miss)}/{len(texts)}  {miss if miss else '(none)'}")
    print(f"  false-reframe among borderline novels w/ strong prior art {bl}: "
          f"{len(bl_reframed)}/{len(bl)}  {bl_reframed if bl_reframed else '(none)'}")
    return len(false_reframe), len(novels)


def main():
    print("=== Auditor ROC positive control (n=20 labeled panel, 2 blind auditors) ===\n")
    fr = 0; tot = 0
    for name, v in [("Auditor A", AUDITOR_A), ("Auditor B", AUDITOR_B)]:
        a, b = score(name, v); fr += a; tot += b
    print(f"\nCOMBINED false-reframe rate across both auditors: {fr}/{tot} "
          f"({100*fr/tot:.0f}%) of genuine novelties demoted to 'textbook'.")
    print("\nREADING: the auditor does NOT demote genuine novelty (0% false-reframe, incl. the")
    print("borderline landmarks with tempting prior-art families). If anything it is slightly LENIENT")
    print("(passes some textbook as novel). So '0/32 of our posts survived as an original discovery'")
    print("reflects the GENERATOR (our pipeline, aimed at well-trodden areas), NOT a harsh grader.")
    print("\nLIMITS: n=20 hand-built panel, 2 auditor runs (LLM-stochastic), landmark items are famous")
    print("(recognizing genuine novelty is the correct behavior; the borderline items test the relabel")
    print("temptation directly and passed). Direction is robust; exact cells are not.")


if __name__ == "__main__":
    main()
