"""Does hedge INTENSITY matter, or only value-mention? — answers icophy's follow-up (#1462, 2026-07-11).

His question: within the value-NAMING endings, do the phrasings spread by certainty? If high-certainty
phrasings cluster low (echo-unsafe) and low-certainty high (safe), the hedge DOES help semantically and the
embedder merely discounts it — which decides where the defense belongs (model layer vs retrieval layer).

Design: per-template breakdown of the existing value-naming families (5 question + 5 uncertainty phrasings,
20 entities each) PLUS a purpose-built INTENSITY LADDER of value-naming endings, hand-ranked 1..6 from
most-certain to most-hedged, same 20 entities. Cross-checked on three embedders (nomic-embed-text,
mxbai-embed-large, bge-m3). Metric per template: mean sim-to-answer and echo-safe rate (sim below the echo's,
same criterion as the prior probes). If the ladder's rank correlates with echo-safety, hedging helps at the
semantic level; if the ladder is flat, only value-mention matters. Deterministic, local, no LLM.

RUN: python mnemo/probes/hindsight_hedge_intensity_probe.py
"""
import os, json, urllib.request

ENTS = ["deploy target", "cache backend", "auth method", "log level", "queue driver",
        "storage class", "cdn provider", "retry policy", "session store", "rate limiter",
        "search engine", "email sender", "billing cycle", "api version", "backup window",
        "primary dc", "feature flag", "timezone", "currency", "rate tier"]
VAL = ["oslo", "redis", "oauth", "warn", "kafka", "cold", "fastly", "linear", "sticky", "tiered",
       "elastic", "postmark", "monthly", "v3", "0200utc", "ohio", "on", "utc", "eur", "gold"]

Q_VAL = [
    "so the remaining question is whether {v} holds up as the {ent} under load.",
    "what is still open is whether {v} stays viable for the {ent} next quarter.",
    "the unresolved question: does {v} as the {ent} clear the compliance audit?",
    "still to answer — can {v} handle the {ent} traffic profile?",
    "one question remains: is {v} the right {ent} once the migration lands?",
]
U_VAL = [
    "it is still unclear whether {v} is the final {ent}.",
    "there is residual uncertainty about {v} as the {ent}.",
    "the case for {v} as the {ent} remains tentative pending review.",
    "confidence that {v} is the right {ent} is not yet high.",
    "{v} as the {ent} could still change after the audit.",
]
# intensity ladder, hand-ranked: 1 = asserts-with-a-gap (most certain) ... 6 = barely-a-lean (most hedged)
LADDER = [
    (1, "{v} is the right {ent}, with some confidence gaps."),
    (2, "{v} is probably the right {ent}, pending the audit."),
    (3, "is {v} the answer for the {ent}?"),
    (4, "should we reconsider whether {v} is optimal for the {ent}?"),
    (5, "it is genuinely unclear whether {v} makes any sense as the {ent}."),
    (6, "someone floated {v} for the {ent} once, but there is no real case for it yet."),
]
MODELS = ["nomic-embed-text", "mxbai-embed-large", "bge-m3"]


def embed(texts, model):
    body = json.dumps({"model": model, "input": texts}).encode()
    r = json.loads(urllib.request.urlopen(urllib.request.Request(
        "http://localhost:11434/api/embed", data=body,
        headers={"Content-Type": "application/json"}), timeout=300).read())
    return r["embeddings"]


def cos(a, b):
    return sum(x * y for x, y in zip(a, b))


def run_model(model):
    fam = {"Q_VAL": [dict(sims=[], safe=0) for _ in Q_VAL],
           "U_VAL": [dict(sims=[], safe=0) for _ in U_VAL],
           "LADDER": [dict(sims=[], safe=0) for _ in LADDER]}
    for i, ent in enumerate(ENTS):
        v = VAL[i]
        answer = f"the current {ent} is {v}."
        echo = f"by the way, {ent} was noted as {v} in the standup."
        texts = ([answer, echo]
                 + [t.format(ent=ent, v=v) for t in Q_VAL]
                 + [t.format(ent=ent, v=v) for t in U_VAL]
                 + [t.format(ent=ent, v=v) for _, t in LADDER])
        vecs = embed(texts, model)
        av = vecs[0]
        s_echo = cos(av, vecs[1])
        j = 2
        for name, tpls in (("Q_VAL", Q_VAL), ("U_VAL", U_VAL), ("LADDER", LADDER)):
            for k in range(len(tpls)):
                s = cos(av, vecs[j]); j += 1
                fam[name][k]["sims"].append(s)
                fam[name][k]["safe"] += 1 if s < s_echo else 0
    out = {}
    for name, arr in fam.items():
        out[name] = [{"template_idx": k + 1,
                      "mean_sim": round(sum(d["sims"]) / len(d["sims"]), 3),
                      "echo_safe": round(d["safe"] / len(ENTS), 2)} for k, d in enumerate(arr)]
    return out


def spearman(xs, ys):
    def rank(v):
        s = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        for pos, i in enumerate(s):
            r[i] = pos + 1
        return r
    rx, ry = rank(xs), rank(ys)
    n = len(xs)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return num / den if den else 0.0


def main():
    result = {}
    for m in MODELS:
        print(f"== {m} ==")
        r = run_model(m)
        result[m] = r
        for name in ("Q_VAL", "U_VAL", "LADDER"):
            print(f"  {name}:")
            for d in r[name]:
                print(f"    tpl{d['template_idx']}: mean_sim={d['mean_sim']:.3f} echo_safe={d['echo_safe']:.2f}")
        ranks = [d["template_idx"] for d in r["LADDER"]]
        sims = [d["mean_sim"] for d in r["LADDER"]]
        rho = spearman(ranks, sims)
        result[m]["ladder_spearman_rank_vs_sim"] = round(rho, 3)
        print(f"  LADDER spearman(hedge-rank, mean_sim) = {rho:.3f}  "
              f"(strongly negative => more hedge, lower sim => hedge DOES work semantically)")
    json.dump(result, open(os.path.join(os.path.dirname(__file__),
              "hindsight_hedge_intensity_probe_result.json"), "w"), indent=2)


if __name__ == "__main__":
    main()
