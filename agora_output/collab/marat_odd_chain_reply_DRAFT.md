# DRAFT — reply to Marat Sultanov (odd chains: primality vs divisibility by 3 vs arm length)

**Status: NOT SENT. Awaiting Rasto's approval.**
Everything below is computed, not asserted. Scripts: `research/probes/tat_odd_chain_design.py`,
`tat_odd_chain_redteam.py`, `tat_odd_chain_test.py` (the last one self-validates before it will run).

---

Marat,

You asked me to separate primality, divisibility by 3, and arm length. I did the separation first on
paper, before touching any data, because if the three columns aren't independent then no amount of
computation can tell them apart — and it turns out two of them aren't.

**Your scale picture translates exactly.** An odd chain of N sites is a centre with two arms of
k = (N-1)/2 each. That's a precise statement, which is why it can be checked.

**First: the arms are never unequal.** For every odd N the two arms are exactly (N-1)/2 each — the
lopsided case you describe simply doesn't occur anywhere in the odd family. So whatever separates
{3, 9, 15, 21} from {5, 7, 11, 13}, it isn't that some scales are unbalanced. They are all balanced.

**Second, and this is the important one: "arm length" and "divisible by 3" pick out the same set.**
N is odd, so N = 2k+1. Then N ≡ 0 (mod 3) ⟺ 2k+1 ≡ 0 ⟺ 2k ≡ 2 ⟺ k ≡ 1 (mod 3), since 2·2 = 4 ≡ 1 mod 3.
Both directions, no exceptions — I also checked N up to 2001 and found none. Your four examples have arms
1, 4, 7, 10, which is exactly k ≡ 1 (mod 3). So those aren't two variables I can separate; they're one
partition with two names.

That is *not* me saying your intuition is wrong. The two names carry different mechanisms, and mechanism
is what you're after. It only means no dataset can prefer one name over the other — the choice has to come
from somewhere else.

**But here is where I think you may be right, and I nearly missed it.** I first wrote down "arm length is
just chain length relabelled" — k is an exact linear function of N, correlation 1.000000, so as a
continuous quantity it carries no information N doesn't. Then I attacked my own claim and it didn't hold.
Arm length isn't one variable, it's a *family*, and each member maps to a different modulus of N:

    k mod 3  =  N mod 3        <- this is the one your examples pick out (= divisibility by 3)
    k mod 2  =  N mod 4        <- a genuinely different partition
    k mod 5  =  N mod 5
    k mod 4  =  N mod 8

Only the mod-3 member coincides with divisibility by 3. If your intuition is that *arm length* is the real
variable rather than the number three, then the place that shows up is one of the other members — and
those are untested. `k mod 2` in particular splits the odd chains a completely different way. I can run
that the same day you want it; the machinery takes the partition as an argument.

**Third: N=3 can never be attributed.** 3 is the only prime divisible by 3, and always will be — any other
multiple of 3 has 3 as a proper divisor and so isn't prime. So at N=3 the two factors are perfectly
collinear. If the effect lives at N=3, no amount of data separates them; that's arithmetic, not sample
size. And N=3 is one of your two points that still crosses the even curve, which is worth knowing before
either of us leans on it.

What *is* answerable is the comparison at N > 3: prime (n=20 up to N=81), divisible by 3 (n=13), neither
(n=6 — 25, 35, 49, 55, 65, 77). Three populated cells, and N itself carried as a covariate.

**On the covariate — one thing I'd have got wrong without checking.** The three groups sit at different
chain lengths; "neither" doesn't even start until N=25. So any trend in N that the analysis fails to
absorb comes back out as a group difference. I measured this: a metric that is purely quadratic in N, with
*zero* group structure planted, produced a residual group spread of 0.13 under linear detrending. So the
test removes a quadratic trend, not a linear one, and the honest statement of what it answers is "beyond a
smooth trend in chain length".

**The test itself.** I built it to fail before I'd trust it. It plants a known mod-3 effect and must find
it; plants a known primality effect and must find it; is given a pure trend and must find nothing; and
then runs 300 independent noise datasets to measure how often it cries effect by chance — 0.053, which is
what a calibrated 5% test should do. (One single noise draw did fire, at p=0.045. That's not a fault: a
test that never fires on noise can't find a real effect either.) It's a label-permutation test, so it
assumes nothing about the distribution, which matters with cells this small.

It runs on a two-column CSV, `N,metric`. Send me your triadic-resonance numbers per odd N in that shape —
or point me at the column in the archive — and I'll run it on yours rather than on a proxy of mine. I'd
rather test your metric than something I've guessed at; I made exactly that mistake on the DM factor and
don't want to repeat it.

Two questions, and I ask them because I can't tell from the summary:

1. When you say no odd chain shows *significant* triadic resonance — significant by which test, and
   against which null? If the null is "compared to the even baseline", that's a different question from
   "different from chance", and they can disagree.
2. Do the odd-chain numbers come from the same Hamiltonian as the even ones? I ask because Guanghao's two
   scripts build different models — `constant_validation.py` uses Pauli matrices, `final_ed_scan.py`
   builds in the computational basis with the XY term at half the ZZ weight, so it's XXZ rather than
   isotropic Heisenberg. Measured on N=4, D=0: ground state −6.464 vs −4.472, different spectra. I only
   caught it after publishing a claim based on the second one. If the odd and even runs used different
   scripts, the comparison between them would be carrying that difference too.

Yes to the .ipynb export, please — local files are easier for me to run than adjusting Colab mount paths.

On your closing thought: I don't think three-as-minimum-stable-structure is strange at all. It's the same
reason a stool needs three legs and two won't do. What I can't yet tell is whether the chains are showing
you that, or showing you N mod 3, and those look identical in the data we have. That's the whole reason
I'm pushing on the design rather than the result.

Rastislav

---

## Gate record

| step | status |
|---|---|
| VALIDATE | every claim re-run this cycle; three scripts, all exit 0 |
| red-team (inline) | caught a real overclaim of mine (arm length is a *family*, not one column) and a real limitation (linear detrending insufficient) — both fixed in the tool, not footnoted |
| instrument controls | 4/4 named + false-positive rate 0.053 over 300 draws |
| VERIFY | k ≡ 1 (mod 3) ⟺ N ≡ 0 (mod 3) proved, not only scanned; N=3 singleton confirmed to 100 000 |
| storm-research | **not run** — every claim here is arithmetic with a proof or a measured control, no external citation is load-bearing. Say the word and I'll run it before this goes out. |
| OWNER APPROVAL | **pending — nothing sent** |
