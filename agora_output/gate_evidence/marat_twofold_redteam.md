# stress-claim on the Marat twofold-manifold reply

Skill invoked 2026-08-30. Five general-purpose lenses, one message, run BEFORE the claim was sent.
Surviving transcripts on disk: method/confound auditor and prior-art hunter (paths at the end).

VERDICT: the original headline was KILLED. Rewritten claim shipped instead.

## Original claim, as submitted to the panel
"Marat's twofold star ground manifold is the signature of a bipartition split 4-against-3, i.e. his
code is not building K_{1,6}."

## What each lens returned

PRIOR-ART HUNTER: TEXTBOOK-CITE-IT. Lieb and Mattis, J. Math. Phys. 3, 749-751 (1962),
doi:10.1063/1.1724276. The degeneracy |nA-nB|+1 is the trivial 2S+1 count, not a separate
Lieb-Mattis claim; what the theorem adds is uniqueness of the multiplet. Non-uniform positive
couplings ARE permitted (sign conditions per edge plus irreducibility), so the weighted edge does
not move it for s > 0. The theorem assumes isotropic Heisenberg exchange, a hypothesis the draft
had omitted. Do not confuse with Lieb-Schultz-Mattis (1961).

STEELMAN SKEPTIC: the diagnosis falls apart on one line. "Twofold at every s" is a signature of
broken SU(2), not of |nA-nB|=1. Measured three models on a GENUINE star that give 2: off-diagonal
written J not 2J (XXZ), Ising-only, and an isotropic run restricted to S_z = +/-1/2. A
Pauli-versus-spin factor of two in an ED build has a far higher base rate than a person writing
K_{1,6} and building a path. He runs DMRG, which conserves S_z and not S squared, so it cannot see
a sextet spread across six sectors at all.

METHOD / CONFOUND AUDITOR: the check carrying the claim could not fail. Seven spin-1/2 sites contain
six S=5/2 multiplets, so every graph on N=7 has sixfold levels; the star itself has one at 4 of 5 s.
Second hole: a triangle with pendants is non-bipartite and gives deg 2 at all five s, a second
counterexample to the "signature". Third: the mis-built-star control only caught DISCONNECTED
graphs, so a connected mis-build escaped it. What survived the attack: the Hamiltonian is isotropic
AFM Heisenberg, magnetisation-conserving, sign correct; the 1e-9 tolerance is safe from 1e-12 to
0.4; no sector is silently skipped; the s grid is not cherry-picked.

OVERCLAIM / FRAMING: the ring in our OWN result file is non-bipartite and twofold at 4 of 5 s, so
the headline contradicted its own receipt. Also: five s values are not "all s"; credit Lieb-Mattis
rather than framing a 1962 theorem as our finding; move his second question to the top, since he
asked whether to write it up or drop it.

BLIND SPOT: the two packages are one question. His theta1 = 0.819 is an angle between 2-dimensional
slices of what we measure as a 6-dimensional manifold, and a basis inside a degenerate manifold is
gauge-arbitrary. His unitary-invariance control rotates a subspace of FIXED dimension, so it is
invariant by construction and blind to the truncation. Better discriminator than |nA-nB|: his own
N=8 and N=9 controls, since an isotropic bipartite AFM star must give 7 and 8 there.

## What we did with it
Every finding above was re-measured independently before it was accepted. The ring, the anisotropy,
the N-scan and the s=0 rank change were all reproduced locally. The claim was rewritten from "his
graph is wrong" to "twofold is a statement about the operator, not the graph", the retraction was
written into the probe itself, and the mis-built-star control was replaced with a connected one.

Transcripts: tasks/a27f327cc144c0b21.output (method auditor), tasks/a004147b6a81cb546.output
(prior-art hunter). The other three lenses' transcript files were emptied by the harness; their
verbatim findings are recorded above.
