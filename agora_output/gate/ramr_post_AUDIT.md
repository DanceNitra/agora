# AUDIT — stress-claim adversarial pass on the RAMR memaudit post

Verdict required: PUBLISH / REFRAME / KILL. The claim under stress:
"Surface rules solved 97.2% of my benchmark; I published that first; fixing planted two more;
memaudit (floor + permuted-null) is the instrument; run it on your data."

---

## Attack A — "The 97.2% is a manufactured villain. You built a strawman benchmark, 'found' its leak,
and monetized the confession."

Stress: Is the leak REAL and was it SHOCKING? v0.2 traces: positional invariant 300/300 (planted record
precedes replaced record — external reviewer found it, README line ~90: "reported by an external
reviewer"), kind label shipped per item, echo shortcut 98.9% at 87.7%. These are gross. The reviewer
found the positional one — WE did NOT find it first. The post's line "I published that number first"
must not imply we found everything first. The ERRATA/README say the positional invariant was "reported
by an external reviewer".
**Check draft:** the draft never claims we found all leaks ourselves. It says "I published that number
in the benchmark's README" (the number = 97.2% floor) — TRUE. The treadmill section: "the auditor caught
something new twice while we were using it" — true (inversion + id leak). BUT the draft omits the
external reviewer entirely. A hostile reader who checks ERRATA sees the positional invariant was
EXTERNAL. Omission makes the self-audit story look stronger than it is.
**Verdict: REFRAME required** — credit the external reviewer explicitly. This is exactly the
"reputation dies on a hidden fact" class. Add to the leak section: the positional invariant was
reported by an external reviewer (300/300), two more were ours (kind label, echo), and the auditor
generalized from there.

## Attack B — "97.2% at 96.0% coverage is a NUMBER WITHOUT A NULL in the TL;DR — you violated your own
rule (report floor AND null or neither)."

Stress: The TL;DR table row says "Surface-rule shortcuts solved 97.2% of our v0.2 traces" — no null
given for v0.2. The README table gives floor + coverage, not the v0.2 permuted-null. Does the source
give it? The README's battery section says the CI asserts 0/8 on clean and 100% vs 0% on planted — that
is the INSTRUMENT validation, not the v0.2 run's null. ERRATA section 3 gives echo-null 1.7%... for the
echo probe. The id-cue null ≤1.0%. What was the FLOOR-level null for v0.2's 97.2%? If unpublishable,
the post violates its own "report both or neither" rule by quoting 97.2% without its null.
**Check source:** README line 60 table (floor/coverage only). ERRATA gives per-probe nulls (echo 1.7%,
id ≤1.0%). The 97.2% floor is the MAX over probes — each probe's null is per-probe; the README table's
design reports floor+coverage. The post's "report both or neither" refers to floor AND null — the draft
TL;DR row cites the floor WITHOUT the null.
**Verdict: REFRAME required** — the TL;DR row (and body leak table) must state the null status: the
battery's chance control is the permuted-label null per probe; for the flagship v0.2 floor the honest
form is "97.2% at 96.0% coverage, against per-probe permuted-label nulls (e.g., echo 1.7%, id ≤1.0%)"
OR drop the standalone-null claim from the reader job (i.e., the reader reports floor+null for THEIR
data). Cleanest fix: in the leak table, add a null column with the known per-probe nulls (echo 1.7%,
id ≤1.0%) and for the battery-level floor state "per-probe nulls ≤ 1.7% on the leaks we traced". Must
not imply 97.2% had NO control — it did (permuted labels per probe).

## Attack C — "The instrument's CI claim (0/8 clean, 100% vs 0% planted) is a SELF-TEST on synthetic
data you built — circular."

Stress: The self-test proves the harness CAN fire, not that it's calibrated on real-world leaks.
**Check:** The post uses the CI numbers as instrument validation, not as evidence about any real
benchmark. That is the correct epistemic scope. The Feng quote bounds the claim.
**Verdict:** survives — no change.

## Attack D — "'Published the leak first' — first relative to WHOM? If the benchmark had zero users,
no one was about to expose it. The 'credibility asset' framing inflates the courage."

Stress: RAMR had ~0 external users; the leak endangered no one. The post implies a brave disclosure;
reality: low-stakes disclosure, high-strategy content.
**Check:** The draft does not claim bravery or stakes. "The alternative is someone else publishing it
about us" — with zero users, unlikely but not impossible (a reviewer DID find the positional invariant —
so external exposure was real). The distribution playbook says publish the loss; the post does not
pretend heroism.
**Verdict:** survives, but Attack A's fix (crediting the reviewer) also defuses this — the reviewer's
existence shows external eyes were on it.

## Attack E — Number-format stress: "136–148 of 300 = 95.2–100.0% right ON THE FIRES" — your post says
"an id-shape rule lands right on 95.2% to 100.0% of traces (136–148 of 300)". Precision: the rule FIRES
on 136–148 traces and is RIGHT on 95.2–100.0% OF THOSE FIRES. The draft's phrasing "lands right on
95.2% to 100.0% of traces (136–148 of 300)" conflates fires-of and right-of.
**Check source:** ERRATA: "an id-shape rule fires on 136 to 148 of them, right on 95.2% to 100.0%".
**Verdict: REFRAME required** — one-line wording fix: "fires on 136–148 of 300 traces and is right on
95.2–100.0% of those fires".

## Attacks considered and rejected (for the record)
- "LoCoMo comparison is unfair" — hedged three times, framing named; their cleanliness on our two leak
  axes is stated. Survives.
- "You should have just re-generated with content-addressed ids" — ERRATA says the real fix is not done;
  the post's Honest limits now name it. Survives.
- "All this to market memaudit" — memaudit is free, zero-dep, and the post's job-for-reader is running
  it on THEIR data, not installing ours. Survives (genre-level skepticism is Attack A/D territory).

---

# VERDICT: REFRAME (then PUBLISH)

Three reframes required before this draft is ready:
1. Credit the external reviewer for the positional invariant (300/300) — we did not find that one first.
2. Fix the floor/null presentation: TL;DR and leak table must carry the per-probe permuted-label nulls
   (echo 1.7%, id ≤1.0%) — the post's own rule is report floor AND null or neither.
3. Precision fix: the id rule "fires on 136–148 of 300 and is right on 95.2–100.0% of those fires" —
   not "lands right on ... of traces".
