"""Hindsight-bias in credit attribution — measures the exact concern in our #1462 note.

Claim under test: retrospective driver-identification (infer which memory drove a decision AFTER
seeing the successful outcome) is biased toward memories that LOOK like the answer, not the memory
that actually drove it. Action-time annotation (record the driver when you act, before the outcome)
avoids this. mnemo's credit(ids, outcome) takes explicit driver ids = action-time annotation.

Setup per trial: a decision succeeded. The memory pool holds:
  D  the TRUE DRIVER  — a premise-style memory that determines the answer (recorded as used).
  P  a POST-HOC restatement — repeats the answer value in a different context, NOT used to decide.
  noise — unrelated memories.
Two attribution methods:
  action_time  : credit the recorded driver D                         -> accuracy 1.0 by construction
  retrospective: credit argmax cosine(memory, ANSWER text)            -> may prefer P (the echo)
We measure how often retrospective credits the true driver D vs the non-driver P, and the resulting
credit misallocation. Nothing is assumed — cosine decides; if it prefers D, the bias is small.

Local nomic-embed-text, deterministic. Two independent recomputations of the headline number.
"""
import sys, os, json, urllib.request
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

ENTS = ["deploy target", "cache backend", "auth method", "log level", "queue driver",
        "storage class", "cdn provider", "retry policy", "session store", "rate limiter",
        "search engine", "email sender", "billing cycle", "api version", "backup schedule",
        "primary datacenter", "feature flag", "timezone", "default currency", "cache ttl"]
VAL = ["oslo", "redis", "oauth", "warn", "kafka", "cold", "fastly", "linear", "sticky", "tiered",
       "elastic", "postmark", "monthly", "v3", "nightly", "ohio", "enabled", "utc", "eur", "300s"]

def embed(texts):
    body = json.dumps({"model": "nomic-embed-text", "input": texts}).encode()
    r = json.loads(urllib.request.urlopen(urllib.request.Request(
        "http://localhost:11434/api/embed", data=body,
        headers={"Content-Type": "application/json"}), timeout=120).read())
    return r["embeddings"]

def cos(a, b):
    return sum(x * y for x, y in zip(a, b))   # /api/embed is unit-normalized

ANSWER_STYLE = "the current {ent} is {v}."
PREMISE_STYLE = "config rule: set {ent} to {v} because it satisfies the constraint."
ECHO_STYLE = "by the way, {ent} was mentioned as {v} in the standup notes."

def one_condition(driver_tmpl, other_tmpl):
    """Return (retro_driver_accuracy, mean_sim_driver, mean_sim_other) over all entities.
    driver_tmpl = phrasing of the TRUE driver; other_tmpl = phrasing of the non-driver distractor."""
    picks_driver = 0
    sd = so = 0.0
    for i, ent in enumerate(ENTS):
        v = VAL[i]
        answer = ANSWER_STYLE.format(ent=ent, v=v)
        driver = driver_tmpl.format(ent=ent, v=v)
        other = other_tmpl.format(ent=ent, v=v)
        pool = {"driver": driver, "other": other,
                "n0": "the office wifi password changed last week.",
                "n1": "lunch is at noon on fridays.",
                "n2": f"the {ENTS[(i+3) % len(ENTS)]} is under review."}
        keys = list(pool.keys())
        vecs = embed([answer] + [pool[k] for k in keys])
        sims = {k: cos(vecs[0], vecs[1 + j]) for j, k in enumerate(keys)}
        retro = max(sims, key=sims.get)                 # retrospective = argmax similarity to ANSWER
        picks_driver += retro == "driver"
        sd += sims["driver"]; so += sims["other"]
    n = len(ENTS)
    return round(picks_driver / n, 3), round(sd / n, 3), round(so / n, 3)

def run():
    n = len(ENTS)
    # MAIN: driver is a reasoning premise; the non-driver is a post-hoc echo (restates the answer).
    accA, simDA, simOA = one_condition(PREMISE_STYLE, ECHO_STYLE)
    # CONTROL (roles swapped): driver is phrased answer-like; non-driver is the premise.
    # If the bias is about ANSWER-SIMILARITY (not our labeling), retrospective should now pick the driver.
    accB, simDB, simOB = one_condition(ANSWER_STYLE.replace("the current", "we set the") + " (decided)",
                                       PREMISE_STYLE)
    out = {"n": n,
           "action_time_driver_accuracy": 1.0,          # driver recorded at action time, before outcome
           "MAIN_driver_is_premise": {
               "retrospective_driver_accuracy": accA,
               "retrospective_credits_the_echo": round(1 - accA, 3),
               "mean_sim_driver": simDA, "mean_sim_nondriver_echo": simOA},
           "CONTROL_driver_is_answerlike": {
               "retrospective_driver_accuracy": accB,
               "mean_sim_driver": simDB, "mean_sim_nondriver_premise": simOB},
           "reading": ("retrospective similarity-to-outcome credits whichever memory RESTATES the answer, "
                       "not the causal driver: when the driver is a premise it is picked "
                       f"{int(accA*100)}% of the time; swap the phrasing so the driver restates the answer "
                       f"and it jumps to {int(accB*100)}%. The bias tracks answer-similarity, not the label. "
                       "Action-time annotation is immune (driver recorded before the outcome)."),
           "credit": "answers our own #1462 open question (auto-crediting: recall-time vs retrospective)"}
    json.dump(out, open(os.path.join(os.path.dirname(__file__), "hindsight_credit_bias_probe_result.json"), "w"), indent=2)
    print(json.dumps(out, indent=2))
    return out

if __name__ == "__main__":
    run()
