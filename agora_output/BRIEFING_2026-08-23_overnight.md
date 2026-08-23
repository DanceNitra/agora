# Overnight, 22→23 August — probe audit

Two minutes. Everything below is local work; nothing went outward, no cloud calls, brain and dungeon
stayed off.

## Two decisions waiting for you

**1. `research/probes/echo_attack_probe_v1.py` has never parsed, in its entire history.** 1,664 bytes
ending mid-word at `best-ranked O`, one unterminated triple quote. It was committed as a fragment and
only ever touched since by a rename sweep. `echo_attack_probe.py` and `echo_attack_probe_v2.py` both
exist and both work. **Delete it, or do you want the v1 arm reconstructed?** I did not touch it.

**2. `research/probes/ct_anchor_probe.py` cannot run at all.** It imports `_sha256_hex`, `_canon` and
`_GENESIS` from inspeximus; all three are gone in 2.20.0 and there is no public replacement. It is
pinned to the private API of an older version. **Rewrite against the public API, or retire it?**

## What was fixed

**Three probes our posts link were unrunnable for a reader.** Two threw a bare `FileNotFoundError`
because they need a sibling file nobody was told about; two more in the inspeximus repo threw
`ModuleNotFoundError` *above* their own "set OPENAI_API_KEY" message, so the helpful line they carried
was unreachable by the only person who needed it. All now name the missing file and the command to
fetch it. Verified by actually following the printed instructions.

**Five real holes in the published probes, all closed.** The two worst are the same defect twice: a
hand-written sentence sitting next to a number computed at run time. Inverting one comparison takes
judge-vs-human agreement from 0.863 to 0.137 while the line still reads *"the celebrated ~80% human
parity"*. Doubling a constant updates one sentence to `d=0.4` and leaves the next one saying
`true 0.20`. The other three were missing input validation: survival could collapse to 0.00 and still
print a confident gap, an inclusion cutoff could select the bottom half while the header said "top
50%", and a probability parameter accepted 1.2.

**Three probes could not print their own results on this machine**, and two could not write their own
receipt file — `UnicodeEncodeError` on a cp1250 console. That is rule 11 in CLAUDE.md, applied in the
servers and never in the probes.

**Two probes were left behind when our own `source=` contract tightened.** I checked which side was
wrong before touching either: inspeximus 2.20.0 now rejects `{"channel","principal"}` and accepts only
a dict with a `doc` key. Our product changed under them; the fix keeps every original field.

## The uncomfortable half

**A large part of tonight was my own instruments being wrong — nine times, and every one surfaced by
running something rather than reading it.** Three are worth you knowing about:

- The mutation sweep first counted a **crash** as a control firing. Corrected, the result inverted:
  from "4 of 8 probes assert something" to **1 of 8**. Seven of our eight published probes compute
  numbers and exit 0 whatever they find. That is not a defect — our posts call them "runnable" and
  "re-run it or break it", never "test" — but a runnable receipt and a check that can fail are two
  different things, and only one of the eight is the second kind.
- A 289-file sweep reported one silent failure. **It was mine**: copying a repo-internal probe out to
  "run it as a reader" breaks its correct `__file__`-relative paths and manufactures exactly the
  defect I was hunting. Run in place, that probe reads 126,737 records and reports a real result.
- Three of seven guards I wrote failed their own both-directions test on the first attempt. One could
  not reach the hole it was written for; one failed on clean data because it compared against the
  wrong baseline; one was going to assert an invariant that does not exist.

I attacked my own four "not a hole" verdicts as well. All four survived — the closest call needed a
sweep over 24 operating points to settle, and it settled in their favour.

## State

Fourteen commits on agora main, one on inspeximus main with CI green 3/3. Three of the fourteen are corrections
to my own earlier work from the same night — including the count in this paragraph, which said ten
and then two until it was checked against the log. Nothing outward, nothing awaiting your approval
except the two decisions at the top.
