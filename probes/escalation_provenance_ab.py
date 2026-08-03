"""A/B the escalation prompt FAITHFULLY.

Attempt 1 used tier='cheap'/temp=0.0 and a paraphrased body; its control did not reproduce the
defect, so it measured nothing. Attempt 2 died because the body-extraction regex was authored in a
bash heredoc and `[^"\\]` arrived as `[^"\]`.

This one is written to a file (no heredoc) and takes the prompt body straight from the live source
by importing the module and reading the function's own text, then uses the real call parameters:
tier='medium', temperature=0.5, max_tokens=400.

CONTROL: the OLD header (`KIND: flywheel`) must reproduce the mechanical-flywheel drift. If it does
not, neither arm is interpretable and the fix stays unproven.
"""
import inspect
import re
import sys

sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from agora.execution.llm_client import call_llm
import agora.execution.flywheel as fw
from agora.dungeon_os.agent_worker import CorporationWorker, _LEAD_PROVENANCE

# Lift the CONSTRAINT BODY out of the live function rather than retyping it: everything the model is
# told after the QUESTION line. Retyping it is what made attempt 1 measure a different prompt.
src = inspect.getsource(CorporationWorker._escalate_lead)
start = src.index('"Treat it as the SHALLOW first draft.')
end = src.index("Reply with exactly two lines:")
tail = src[end:]
end2 = tail.index('"\n')
raw_body = src[start:end] + tail[: end2 + 1]
BODY = "".join(
    part.encode().decode("unicode_escape")
    for part in re.findall(r'"([^"]*)"', raw_body)
)
print("body lifted from the live function: %d chars" % len(BODY))
print("  banned-words clause present: %s" % ("self-organized criticality" in BODY))
print("  anchor clause present:       %s\n" % ("ANCHORED" in BODY))

HEAD = ("You are a Frontier Scout for an autonomous research organization. "
        "Here is a raw research lead:\n")


def old_prompt(kind, question):
    return HEAD + "KIND: %s\nQUESTION: %s\n\n" % (kind, question) + BODY


def new_prompt(kind, question):
    prov = _LEAD_PROVENANCE.get(kind, "a lead from one of our own research organs")
    return (HEAD
            + "WHERE IT CAME FROM: %s -- this is provenance, NOT subject matter. The domain of the "
              "question is whatever the QUESTION itself is about; do not infer a topic from this "
              "line.\n" % prov
            + "QUESTION: %s\n\n" % question + BODY)


DRIFT = re.compile(r"flywheel|energy storage|\brotor\b|x-15|turbine", re.I)


def ask(prompt):
    raw = call_llm(system_prompt="", user_prompt=prompt, tier="medium",
                   temperature=0.5, max_tokens=400) or ""
    m = re.search(r"QUESTION:\s*(.+)", raw)
    return (m.group(1) if m else raw).strip()[:160]


questions = [q.get("question") for q in (fw.open_questions(6) or []) if q.get("question")]
REPS = 2
old_hits = new_hits = trials = 0

for i, q in enumerate(questions, 1):
    lead = "Close this OPEN question with a MEASURED answer: %s" % q
    for r in range(REPS):
        a = ask(old_prompt("flywheel", lead))
        b = ask(new_prompt("flywheel", lead))
        da, db = bool(DRIFT.search(a)), bool(DRIFT.search(b))
        old_hits += da
        new_hits += db
        trials += 1
        if da or db or r == 0:
            print("[%d.%d] OLD %s: %s" % (i, r + 1, "DRIFT" if da else "  ok ", a[:96]))
            print("      NEW %s: %s" % ("DRIFT" if db else "  ok ", b[:96]))

print("\n" + "=" * 70)
print("  trials per arm                : %d" % trials)
print("  OLD  (KIND: flywheel) drifted : %d" % old_hits)
print("  NEW  (provenance line) drifted: %d" % new_hits)
if old_hits == 0:
    print("\n  CONTROL FAILED — the live prompt does not reproduce the drift on this sample.")
    print("  The inbox flood therefore has another cause. Do NOT claim this fix works;")
    print("  the change is harmless but unproven, and should be labelled as such.")
elif new_hits < old_hits:
    print("\n  Control held (%d drifts on OLD). Fix reduces drift %d -> %d."
          % (old_hits, old_hits, new_hits))
else:
    print("\n  Control held (%d drifts) but the fix did NOT reduce it. Do not ship it as a fix."
          % old_hits)
