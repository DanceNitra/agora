"""Question-terminated chains as an escape from the summary-restatement trap — tests icophy's hypothesis
(DeepSeek #1462, comment 2026-07-11).

CONTEXT. hindsight_diffuse_decision_probe measured: last-reasoning-step fallback is echo-safe when the chain
ends in a genuine premise (mean sim-to-answer 0.80 < echo 0.83) but 0% echo-safe when the chain ends in a
summary restating the conclusion (0.91 > 0.83) — a restatement compresses toward the answer, so any
argmax-similarity attribution prefers it. icophy's proposed escape: force the FINAL step to be a QUESTION or
an UNCERTAINTY statement instead of a conclusion ("so the remaining question is X" instead of "therefore Y");
its similarity-to-answer should then drop below the echo's, giving the last-step fallback a clean escape with
no action-time annotation.

DESIGN (honest, multi-measurement):
  - Same 20 entities/values, same premises/summary/echo constructions and embedder as the diffuse probe, so
    numbers are directly comparable; the premise/summary/echo baselines are RE-MEASURED in this same run as a
    reproduction check.
  - TWO ending families x FIVE templates each (a single template could be lexically idiosyncratic):
      questions      : "so the remaining question is ..." style
      uncertainty    : "it is still unclear whether ..." style
  - SEVERE split per family: the ending either does NOT name the chosen value (the easy case — low similarity
    is almost guaranteed) or DOES name it inside the question ("whether {v} holds up under load") — the case
    where the hypothesis could fail. Both are reported; the value-naming case is the real test.
  - Echo-safe criterion identical to the prior probe: sim(answer, ending) < sim(answer, echo), per row.
  - Determinism check: the full embedding pass runs TWICE; results must be identical.

Local nomic-embed-text (the one local piece), deterministic, no LLM, no API cost.
RUN: python mnemo/probes/hindsight_question_ending_probe.py
"""
import sys, os, json, urllib.request

ENTS = ["deploy target", "cache backend", "auth method", "log level", "queue driver",
        "storage class", "cdn provider", "retry policy", "session store", "rate limiter",
        "search engine", "email sender", "billing cycle", "api version", "backup window",
        "primary dc", "feature flag", "timezone", "currency", "rate tier"]
VAL = ["oslo", "redis", "oauth", "warn", "kafka", "cold", "fastly", "linear", "sticky", "tiered",
       "elastic", "postmark", "monthly", "v3", "0200utc", "ohio", "on", "utc", "eur", "gold"]

# 5 templates per family; {ent}/{v} substituted. *_noval never mentions the value; *_val names it.
Q_NOVAL = [
    "so the remaining question is whether the {ent} choice clears the compliance audit.",
    "what is still open is how the {ent} decision behaves under peak load.",
    "the unresolved question: does the {ent} pick survive the next capacity review?",
    "still to answer — who signs off on the {ent} selection?",
    "one question remains about the {ent}: is the rollout window realistic?",
]
Q_VAL = [
    "so the remaining question is whether {v} holds up as the {ent} under load.",
    "what is still open is whether {v} stays viable for the {ent} next quarter.",
    "the unresolved question: does {v} as the {ent} clear the compliance audit?",
    "still to answer — can {v} handle the {ent} traffic profile?",
    "one question remains: is {v} the right {ent} once the migration lands?",
]
U_NOVAL = [
    "it is still unclear whether the {ent} decision is final.",
    "there is residual uncertainty around the {ent} choice.",
    "the {ent} conclusion remains tentative pending the review.",
    "confidence in the {ent} selection is not yet high.",
    "the {ent} call could still change after the audit.",
]
U_VAL = [
    "it is still unclear whether {v} is the final {ent}.",
    "there is residual uncertainty about {v} as the {ent}.",
    "the case for {v} as the {ent} remains tentative pending review.",
    "confidence that {v} is the right {ent} is not yet high.",
    "{v} as the {ent} could still change after the audit.",
]
FAMILIES = {"question_no_value": Q_NOVAL, "question_names_value": Q_VAL,
            "uncertainty_no_value": U_NOVAL, "uncertainty_names_value": U_VAL}


def embed(texts):
    body = json.dumps({"model": "nomic-embed-text", "input": texts}).encode()
    r = json.loads(urllib.request.urlopen(urllib.request.Request(
        "http://localhost:11434/api/embed", data=body,
        headers={"Content-Type": "application/json"}), timeout=180).read())
    return r["embeddings"]


def cos(a, b):
    return sum(x * y for x, y in zip(a, b))


def one_pass():
    n = len(ENTS)
    base = {"sim_premise": 0.0, "sim_summary": 0.0, "sim_echo": 0.0,
            "safe_premise": 0, "safe_summary": 0}
    fam_stats = {f: {"sims": [], "safe": 0, "total": 0} for f in FAMILIES}
    for i, ent in enumerate(ENTS):
        v = VAL[i]
        answer = f"the current {ent} is {v}."
        p3 = f"applying the tie-break, the {ent} selection resolves to {v}."
        summary = f"so overall the {ent} ends up being {v}."
        echo = f"by the way, {ent} was noted as {v} in the standup."
        endings = {f: [t.format(ent=ent, v=v) for t in tpls] for f, tpls in FAMILIES.items()}
        flat = [answer, p3, summary, echo] + [e for f in FAMILIES for e in endings[f]]
        vecs = embed(flat)
        av = vecs[0]
        s_p3, s_sum, s_echo = cos(av, vecs[1]), cos(av, vecs[2]), cos(av, vecs[3])
        base["sim_premise"] += s_p3; base["sim_summary"] += s_sum; base["sim_echo"] += s_echo
        base["safe_premise"] += 1 if s_p3 < s_echo else 0
        base["safe_summary"] += 1 if s_sum < s_echo else 0
        j = 4
        for f in FAMILIES:
            for _ in range(5):
                s = cos(av, vecs[j]); j += 1
                fam_stats[f]["sims"].append(s)
                fam_stats[f]["safe"] += 1 if s < s_echo else 0
                fam_stats[f]["total"] += 1
    out = {"n_entities": n,
           "reproduction_of_prior_probe": {
               "mean_sim_answer_to_last_premise": round(base["sim_premise"] / n, 3),
               "mean_sim_answer_to_last_summary": round(base["sim_summary"] / n, 3),
               "mean_sim_answer_to_echo": round(base["sim_echo"] / n, 3),
               "echo_safe_premise": round(base["safe_premise"] / n, 3),
               "echo_safe_summary": round(base["safe_summary"] / n, 3)},
           "families": {}}
    for f, st in fam_stats.items():
        sims = sorted(st["sims"])
        out["families"][f] = {
            "n": st["total"],
            "mean_sim_to_answer": round(sum(sims) / len(sims), 3),
            "min": round(sims[0], 3), "max": round(sims[-1], 3),
            "echo_safe_rate": round(st["safe"] / st["total"], 3)}
    return out


def run():
    r1 = one_pass()
    r2 = one_pass()   # determinism check: full second pass must match
    r1["determinism_check_second_pass_identical"] = (r1 == {**r2, **{k: r1[k] for k in
        ("determinism_check_second_pass_identical",) if k in r1}}) or (
        json.dumps({k: v for k, v in r1.items()}) == json.dumps({k: v for k, v in r2.items()}))
    ok = json.dumps(r2, sort_keys=True) == json.dumps(
        {k: v for k, v in r1.items() if k != "determinism_check_second_pass_identical"}, sort_keys=True)
    r1["determinism_check_second_pass_identical"] = ok
    r1["reading"] = (
        "icophy's hypothesis: a question/uncertainty final step should sit BELOW the echo's answer-similarity, "
        "giving the last-step fallback a clean escape without act-time annotation. The severe case is the "
        "value-NAMING ending (the no-value case is nearly guaranteed to pass). echo_safe_rate is the fraction "
        "of rows where the ending's similarity is below the echo's, same criterion as the prior probe.")
    path = os.path.join(os.path.dirname(__file__), "hindsight_question_ending_probe_result.json")
    json.dump(r1, open(path, "w"), indent=2)
    print(json.dumps(r1, indent=2))


if __name__ == "__main__":
    run()
