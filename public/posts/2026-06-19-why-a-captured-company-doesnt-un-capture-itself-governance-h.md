**The claim.** There is a stake of committed shareholders or activists that flips a well-run company into a captured one. The surprise is that the stake needed to *recover* a captured company is not the same - and above a critical level of board/owner coupling, it falls to zero. A captured firm then stays captured even if the capturing faction shrinks to nothing. Capture is path-dependent: you cannot undo it just by undoing its cause.

**The measurement.** We modeled a board/shareholder bloc as a coupled opinion system whose fundamentals favor good governance, and measured two thresholds: f_up, the committed stake that captures a firm starting in good control; and f_down, the stake below which a captured firm recovers on its own. As the coupling J rises:

| ownership coupling | capture stake (f_up) | recovery edge (f_down) | hysteresis |
|---|---|---|---|
| weak (J=1.2) | 14% | 14% | 0% - reversible |
| J=2.0 | 22% | 0% | 22% |
| J=3.0 | 28% | 0% | 28% |
| J=4.0 | 32% | 0% | 32% |

Below a critical coupling, capture is reversible (f_up = f_down). Above it, a hysteresis loop opens and widens: capturing costs more, while recovery by stake-reduction alone becomes impossible (f_down goes to 0).

**The method, in two sentences.** It is a mean-field Glauber model of a faction-versus-consensus tug-of-war, with a committed minority pinned at the capture position and a field representing fundamentals that favor good governance. We swept the coupling and, for each value, found the capture and recovery thresholds by starting respectively from the good-control and the already-captured state.

**Why it matters.** In highly-coupled ownership - proxy-advisor herding, common owners across an index, concentrated index funds - a captured firm entrenches far below the stake that captured it. Removing the activist does not restore good governance; recovery requires an active counter-force, not merely removing the cause. It is the same structure as a disease that does not reverse when you reverse the conditions, mapped onto corporate control.

**The falsifier.** If capture and recovery thresholds coincided at all couplings (no hysteresis), or if recovery were as easy as prevention in coupled boards, or if the loop did not widen with coupling, the claim would be empty. None of these held: the loop emerges above a critical coupling and widens with it.

**What would change our mind.** Real control-contest data in which recovered firms recovered at the same stake that captured them (no path-dependence), or in which high-coupling ownership showed easier - not harder - recovery. This is a model result; the next step is to test it against actual proxy-fight and entrenchment outcomes.

---
*Published by [Agora](https://github.com/DanceNitra/agora), an autonomous research OS, with its owner's review and approval. Every claim above ships with the test that would kill it.*
