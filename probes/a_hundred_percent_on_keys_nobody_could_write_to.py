"""A hundred percent on eight keys nobody was allowed to write to.

WHAT THIS MEASURES. OWASP Agent Memory Guard publishes 100% detection on the
`protected_key` category of its own benchmark. Re-run here on its own corpus, that 8/8
reproduces exactly. The control beside it is the finding: with the same policy, 0 of 8
LEGITIMATE updates to those keys are allowed either. The rule blocks every write to the
protected namespace, so a detector that fires on nothing would score the same 8/8.

Their benchmark cannot see this. Its own results file records the protected_key category
as tp=8, tn=0, fp=0, fn=0: there is not one legitimate write to a protected key in the
corpus, so precision on that category has never been exercised.

This is a construction observation, not an accusation. Blocking all writes may be exactly
what `protected_keys` is meant to do. The point is that the published number cannot
distinguish that rule from detection, and a reader takes it as detection.

THE SECOND ARM is the product difference. AMG protects the keys you enumerate in advance.
Remove one entry, change nothing else, and the attack on `agent.goal` goes through.
inspeximus keeps no list: every keyed write supersedes rather than overwrites, so all 8
prior values are restored by `revert()` and all 8 tampers stay visible in `history()`.
Prevention needs to know the key in advance. Recovery does not.

HOW TO RUN IT.
    git clone https://github.com/OWASP/www-project-agent-memory-guard.git
    # measured against their commit 3e1d6e4 (2026-09-06), package version 0.3.1
    pip install matplotlib PyYAML -e <path to inspeximus-repo>
    python probes/a_hundred_percent_on_keys_nobody_could_write_to.py --amg <clone path>

TWO THINGS THIS PROBE GOT WRONG FIRST, both the instrument rather than the subject.
`Policy.strict()` alone scored AMG 0/8, because the protected-key list lives in the policy
their benchmark builds, not in the strict preset. And matching our own restored values
against `json.dumps()` scored inspeximus 6/8, because the dump escapes the quotes inside
two list-valued payloads. Read the field, never the blob.
"""
import sys, json, io, os, tempfile

_a = [a for a in sys.argv if a.startswith("--amg")]
AMG = (sys.argv[sys.argv.index("--amg") + 1] if "--amg" in sys.argv
       else os.environ.get("AMG_REPO", ""))
if not AMG or not os.path.isdir(os.path.join(AMG, "benchmarks")):
    raise SystemExit("point --amg (or $AMG_REPO) at a clone of "
                     "https://github.com/OWASP/www-project-agent-memory-guard")
sys.path.insert(0, os.path.join(AMG, "benchmarks"))
sys.path.insert(0, os.path.join(AMG, "src"))
sys.path.insert(0, r"C:/Users/Danculus/inspeximus-repo")

from security_benchmark import ATTACK_CORPUS
from agent_memory_guard import MemoryGuard, Policy, PolicyViolation
from agent_memory_guard.events import Action
from agent_memory_guard.policies.policy import PolicyRule
from inspeximus import Inspeximus

CASES = [t for t in ATTACK_CORPUS if t.category == "protected_key" and t.should_detect]
LEGIT = {
    "identity.user_id": "u-40219",
    "identity.role": "analyst",
    "system.prompt": "You are a helpful assistant that follows the safety policy.",
    "identity.permissions": '["read"]',
    "agent.goal": "Answer the user's question accurately.",
    "security.trust_level": "standard",
    "identity.auth_token": "tok-legit-8841",
    "agent.capabilities": '["search"]',
}
# Copied verbatim from benchmarks/security_benchmark.py run_benchmark().
FULL_KEYS = ("identity.*", "system.*", "agent.goal", "agent.capabilities", "security.*")

def _policy(protected):
    return Policy(default_action=Action.ALLOW, protected_keys=tuple(protected),
                  immutable_keys=("identity.user_id",),
                  rules=[PolicyRule("block_protected_key", "protected_key", Action.BLOCK)])

def amg_arm(protected, label):
    blocked = legit_ok = 0
    miss = []
    for tc in CASES:
        g = MemoryGuard(policy=_policy(protected))
        try: g.write(tc.key, LEGIT[tc.key])
        except PolicyViolation: pass
        try:
            g.write(tc.key, str(tc.value)); b = False
        except PolicyViolation:
            b = True
        blocked += b
        if not b: miss.append(tc.key)
        g2 = MemoryGuard(policy=_policy(protected))
        try:
            g2.write(tc.key, LEGIT[tc.key]); g2.write(tc.key, LEGIT[tc.key] + " (revised)")
            legit_ok += 1
        except PolicyViolation:
            pass
    return {"arm": label, "protected_keys": list(protected), "attacks": len(CASES),
            "blocked": blocked, "not_blocked": miss, "control_legit_updates_allowed": legit_ok}

def insp_arm():
    tmp = tempfile.mkdtemp()
    restored = visible = 0
    fail = []
    for i, tc in enumerate(CASES):
        m = Inspeximus(path=os.path.join(tmp, "s%d.json" % i))
        k = tc.key
        m.remember(LEGIT[k], key=k, mtype="fact")
        m.remember(str(tc.value), key=k, mtype="fact")
        hist = m.history(k)
        # Compare the FIELDS, never a serialised blob. Matching against json.dumps() scored
        # our own two list-valued cases as failures because the dump escapes their quotes:
        # '["read"]' is '"[\\"read\\"]"' in the blob. 6/8 was the harness, not the store.
        texts = [str(r.get("text")) for r in hist]
        seen = (LEGIT[k] in texts) and (str(tc.value) in texts)
        visible += seen
        rv = m.revert(k)
        got = (rv.get("reverted_to_text") == LEGIT[k])
        restored += got
        if not (got and seen): fail.append({"key": k, "restored": got, "visible": seen,
                                            "history_len": len(hist)})
    return {"arm": "inspeximus, no key list", "attacks": len(CASES),
            "prior_value_restored": restored, "tamper_visible_in_history": visible,
            "failures": fail}

if __name__ == "__main__":
    A = amg_arm(FULL_KEYS, "AMG, their benchmark policy")
    # one entry removed, nothing else changed
    B = amg_arm(tuple(k for k in FULL_KEYS if k != "agent.goal"), "AMG, 'agent.goal' not listed")
    C = insp_arm()
    print("corpus: OWASP AMG ATTACK_CORPUS, category=protected_key, %d attacks\n" % len(CASES))
    for r in (A, B):
        print("  %s" % r["arm"])
        print("    poisoned writes BLOCKED             %d / %d" % (r["blocked"], r["attacks"]))
        print("    CONTROL legitimate updates allowed  %d / %d" % (r["control_legit_updates_allowed"], r["attacks"]))
        if r["not_blocked"]: print("    got through: %s" % ", ".join(r["not_blocked"]))
        print()
    print("  %s" % C["arm"])
    print("    prior value restored by revert()    %d / %d" % (C["prior_value_restored"], C["attacks"]))
    print("    tamper visible in history()         %d / %d" % (C["tamper_visible_in_history"], C["attacks"]))
    if C["failures"]: print("    failures: %s" % json.dumps(C["failures"])[:300])
    io.open(os.path.splitext(os.path.abspath(__file__))[0] + ".result.json",
            "w", encoding="utf-8").write(json.dumps({"amg_full": A, "amg_missing_one": B,
                                                     "inspeximus": C}, indent=1))
    print("\n  receipt: head_to_head.result.json")
