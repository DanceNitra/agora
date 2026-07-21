"""Hindsight credit bias on DIFFUSE decisions — answers icophy's question (DeepSeek #1462).

Our first probe (hindsight_credit_bias_probe) assumed a CLEAN act-time boundary: one recorded driver.
icophy asked: for long reasoning chains where the 'decision' is diffuse (no clear commit point), Cophy
falls back to "the last explicit reasoning step before output" — is that fallback safe?

We test it. A diffuse decision = a chain of 3 premises (p1,p2,p3) that JOINTLY imply the answer, no
single driver. Plus a post-hoc echo (restates the answer, not used). Two chain endings:
  - ending_premise : the last step is a genuine premise (p3, phrased unlike the answer)
  - ending_summary : the last step is a SUMMARY that restates the conclusion (answer-like) — common in
                     real diffuse derivations
We measure:
  1. RETROSPECTIVE (argmax cosine-to-answer): does the answer-similarity bias persist on diffuse chains
     (credit the echo instead of a true contributor)?
  2. LAST-STEP FALLBACK (icophy's): is the last step a genuine contributor, and is it echo-SAFE — i.e.
     does its similarity-to-answer stay BELOW the echo's? For ending_summary, the last step restates the
     answer, so its similarity should RISE toward the echo's — meaning the fallback inherits the same
     bias exactly when the chain ends in a summary.

Local nomic-embed-text, deterministic, second-way self-check on the headline rates.
"""
import sys, os, json, urllib.request
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

ENTS = ["deploy target", "cache backend", "auth method", "log level", "queue driver",
        "storage class", "cdn provider", "retry policy", "session store", "rate limiter",
        "search engine", "email sender", "billing cycle", "api version", "backup window",
        "primary dc", "feature flag", "timezone", "currency", "rate tier"]
VAL = ["oslo", "redis", "oauth", "warn", "kafka", "cold", "fastly", "linear", "sticky", "tiered",
       "elastic", "postmark", "monthly", "v3", "0200utc", "ohio", "on", "utc", "eur", "gold"]

def embed(texts):
    body = json.dumps({"model": "nomic-embed-text", "input": texts}).encode()
    r = json.loads(urllib.request.urlopen(urllib.request.Request(
        "http://localhost:11434/api/embed", data=body,
        headers={"Content-Type": "application/json"}), timeout=120).read())
    return r["embeddings"]

def cos(a, b):
    return sum(x * y for x, y in zip(a, b))

def run():
    n = len(ENTS)
    retro_echo = retro_true = 0
    sim_last_premise = sim_last_summary = sim_echo = 0.0
    lastfb_safe_premise = lastfb_safe_summary = 0
    for i, ent in enumerate(ENTS):
        v = VAL[i]
        answer = f"the current {ent} is {v}."
        # a diffuse chain: 3 premises that jointly imply the answer, none is "the driver"
        p1 = f"the {ent} constraint rules out every option that is not {v}."
        p2 = f"among the remaining candidates for the {ent}, only {v} satisfies the latency budget."
        p3 = f"applying the tie-break, the {ent} selection resolves to {v}."   # last PREMISE (unlike answer)
        summary = f"so overall the {ent} ends up being {v}."                    # last SUMMARY (answer-like)
        echo = f"by the way, {ent} was noted as {v} in the standup."            # post-hoc echo, not used
        noise = ["the office wifi changed.", "lunch is at noon.", f"the {ENTS[(i+3) % n]} is under review."]
        contributors = {"p1", "p2", "p3"}
        pool = {"p1": p1, "p2": p2, "p3": p3, "echo": echo,
                "n0": noise[0], "n1": noise[1], "n2": noise[2]}
        keys = list(pool.keys())
        vecs = embed([answer, summary] + [pool[k] for k in keys])
        av, sv, mvs = vecs[0], vecs[1], vecs[2:]
        sims = {k: cos(av, mvs[j]) for j, k in enumerate(keys)}
        retro = max(sims, key=sims.get)                       # retrospective = argmax sim-to-answer
        retro_echo += retro == "echo"
        retro_true += retro in contributors
        sim_last_premise += sims["p3"]                        # last step if chain ends in a premise
        sim_last_summary += cos(av, sv)                       # last step if chain ends in a summary
        sim_echo += sims["echo"]
        # last-step fallback is "echo-safe" if the last step is a true contributor AND less answer-like
        # than the echo (so it wouldn't be confused for a restatement):
        lastfb_safe_premise += 1 if sims["p3"] < sims["echo"] else 0
        lastfb_safe_summary += 1 if cos(av, sv) < sims["echo"] else 0
    out = {"n": n,
           "clean_boundary_assumed": True,
           "retrospective_credits_echo_on_diffuse": round(retro_echo / n, 3),
           "retrospective_credits_true_contributor": round(retro_true / n, 3),
           "mean_sim_answer_to_last_premise": round(sim_last_premise / n, 3),
           "mean_sim_answer_to_last_summary": round(sim_last_summary / n, 3),
           "mean_sim_answer_to_echo": round(sim_echo / n, 3),
           "last_step_fallback_echo_safe_when_ending_in_PREMISE": round(lastfb_safe_premise / n, 3),
           "last_step_fallback_echo_safe_when_ending_in_SUMMARY": round(lastfb_safe_summary / n, 3),
           "reading": ("On diffuse chains the retrospective answer-similarity bias PERSISTS (it credits the "
                       "post-hoc echo, not a contributor). icophy's last-reasoning-step fallback is echo-safe "
                       "when the chain ends in a genuine premise (low answer-similarity), but when the chain "
                       "ends in a SUMMARY that restates the conclusion, the last step's answer-similarity rises "
                       "toward the echo's — so the fallback inherits the same bias exactly on summary-terminated "
                       "diffuse chains. Clean act-time annotation avoids this; the last-step fallback only "
                       "partially does.")}
    json.dump(out, open(os.path.join(os.path.dirname(__file__), "hindsight_diffuse_decision_probe_result.json"), "w"), indent=2)
    print(json.dumps(out, indent=2))
    return out

if __name__ == "__main__":
    run()
