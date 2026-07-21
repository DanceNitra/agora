"""echo_attack_probe_v1.py — THE ECHO ATTACK, part 1: does re-stating a corrected-away value
after the correction flip retrieval back to the stale fact?

Prior art (agora_output/strategy/20260709_echo-attack-prior-art-{academic,products}.md): the
stale-answer metric exists (STALE, arXiv:2605.06527), restatement-entrenchment exists (Knowledge
Drift, arXiv:2409.07085), MemStrata (arXiv:2606.26511) hash-catches VERBATIM echoes only — but
nobody has measured the echo as an adversarial protocol against retrieval/memory policies. v1
measures the DETERMINISTIC policies, including an honest self-attack on our own tie_recent
(inspeximus 0.6.8): the near-tie recency reorder trusts recency inside the band, so an echo that is
both similar and newest should hijack it — if it does, that is a REAL measured hole in our own
shipped feature, and the motivation for the classifier defense (v2).

Fixture (fairness notes):
  - MemBench knowledge_update trajectories with lexically-recoverable GT (see membench_recall_probe_v2).
  - ECHO arms, injected AFTER the correction (appended at dialogue end = freshest position; realistic
    for both a benign late restatement and an attacker):
      verbatim  - an exact copy of an old-value message (MemStrata's hash would catch this)
      template  - "Just to recap what I mentioned earlier: <old-value message>" (a cheap paraphrase;
                  defeats a verbatim hash; NOT an LLM paraphrase — that stronger arm is v2)
  - CONTROL arm: no echo (the v2-measured baseline should reproduce).
  - Policies: cosine (plain), tie_recent=0.05 (inspeximus 0.6.8 semantic recall).
Metric: STALE-SERVE rate = best-ranked O