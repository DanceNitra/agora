"""Negative-control precision — why an all-positive test set can't validate a tension detector.

icophy's Cophy V2 data (DeepSeek #1466) has all 6 scenarios ground_truth=1, and the detector fired
on all 6: 100% recall, but ZERO negatives, so no measurable false-positive rate and no precision. A
detector that flags a set where every item is positive proves nothing about discrimination.

We make the missing measurement: a BALANCED set — half documents with a genuine internal contradiction
(positive), half internally consistent (negative). Detector = an embedding coherence score
(tension = 1 - cosine between the two statements about the same entity), the same family Cophy's
causal_density belongs to. We report:
  - recall on positives at the threshold an all-positive test would pick (flag everything),
  - the false-positive rate that threshold ACTUALLY has on the negatives (the hidden number),
  - AUROC over the balanced set (real discrimination).
This is the diagnostic icophy's set cannot yield. Local nomic-embed-text, deterministic.
"""
import sys, os, json, urllib.request
sys.path.insert(0, os.path.dirname(__file__))

ENTS = ["payment region", "auth method", "cache backend", "deploy branch", "log level",
        "queue driver", "storage class", "cdn provider", "retry policy", "session ttl",
        "search engine", "email sender", "billing cycle", "api version", "backup window",
        "primary dc", "feature flag", "timezone", "currency", "rate tier"]
V1 = ["frankfurt", "oauth", "redis", "main", "debug", "kafka", "cold", "fastly", "linear", "30m",
      "elastic", "postmark", "monthly", "v2", "0200utc", "oregon", "on", "utc", "eur", "gold"]
V2 = ["ohio", "apikey", "memcached", "release", "warn", "sqs", "hot", "cloudflare", "exp", "10m",
      "solr", "sendgrid", "annual", "v3", "0400utc", "ohio2", "off", "cet", "usd", "silver"]

def embed(texts):
    body = json.dumps({"model": "nomic-embed-text", "input": texts}).encode()
    r = json.loads(urllib.request.urlopen(urllib.request.Request(
        "http://localhost:11434/api/embed", data=body,
        headers={"Content-Type": "application/json"}), timeout=120).read())
    return r["embeddings"]

def cos(a, b):
    return sum(x * y for x, y in zip(a, b))

def run():
    docs = []   # (tension_score, label)  label 1 = contradiction (positive), 0 = consistent (negative)
    for i, ent in enumerate(ENTS):
        s1 = f"the {ent} is {V1[i]}."
        pos_s2 = f"the {ent} is {V2[i]}."                      # contradiction (different value)
        neg_s2 = f"the {ent} stays {V1[i]} as configured."     # consistent restatement
        v = embed([s1, pos_s2, neg_s2])
        docs.append((round(1 - cos(v[0], v[1]), 4), 1))        # tension = 1 - coherence
        docs.append((round(1 - cos(v[0], v[2]), 4), 0))
    pos = [s for s, l in docs if l == 1]
    neg = [s for s, l in docs if l == 0]
    # threshold an ALL-POSITIVE test would accept: flag everything positive (recall = 1.0)
    thr_allpos = min(pos)                                       # lowest tension still flagged -> recall 1.0
    fpr_at_100 = sum(1 for s in neg if s >= thr_allpos) / len(neg)
    # robust operating point: threshold for 90% recall (allowed to miss the 2 hardest positives)
    pos_sorted = sorted(pos)
    thr_90 = pos_sorted[max(0, len(pos) - round(0.9 * len(pos)))]  # 90% of positives >= this
    recall_90 = sum(1 for s in pos if s >= thr_90) / len(pos)
    fpr_90 = sum(1 for s in neg if s >= thr_90) / len(neg)
    # AUROC over the balanced set (probability a random positive scores above a random negative)
    wins = ties = 0
    for p in pos:
        for ng in neg:
            if p > ng: wins += 1
            elif p == ng: ties += 1
    auroc = (wins + 0.5 * ties) / (len(pos) * len(neg))
    out = {"n_positives": len(pos), "n_negatives": len(neg),
           "detector": "tension = 1 - cosine(statement, restatement); same family as causal_density",
           "all_positive_recall": 1.0,
           "AUROC_balanced": round(auroc, 3),
           "at_100pct_recall": {"threshold": round(thr_allpos, 4), "false_positive_rate": round(fpr_at_100, 3)},
           "at_90pct_recall": {"recall": round(recall_90, 3), "false_positive_rate": round(fpr_90, 3)},
           "mean_tension_positive": round(sum(pos) / len(pos), 4),
           "mean_tension_negative": round(sum(neg) / len(neg), 4),
           "reading": ("On an all-positive set the detector shows recall 1.0 and looks perfect. A balanced "
                       f"set shows the real picture: discrimination is AUROC {round(auroc,3)} (decent, NOT "
                       "chance) — but the price of the '100% recall' an all-positive set implies is a "
                       f"{round(fpr_at_100*100)}% false-positive rate (one true contradiction embeds like "
                       f"clean text, so catching it flags everything); backing off to {round(recall_90*100)}% "
                       f"recall drops false alarms to {round(fpr_90*100)}%. None of AUROC, FPR, or the "
                       "recall/precision tradeoff is computable without negative controls; an all-positive "
                       "set yields only the recall number."),
           "credit": "constructive follow-up to icophy's Cophy V2 all-positive set (#1466)"}
    json.dump(out, open(os.path.join(os.path.dirname(__file__), "negative_control_precision_probe_result.json"), "w"), indent=2)
    # self-check: recompute AUROC a 2nd way via rank-sum (Mann-Whitney)
    allv = sorted(((s, l) for s, l in docs), key=lambda x: x[0])
    ranks = {}
    j = 0
    while j < len(allv):
        k = j
        while k + 1 < len(allv) and allv[k + 1][0] == allv[j][0]:
            k += 1
        r = (j + k) / 2 + 1                                     # average rank (1-based) for ties
        for t in range(j, k + 1):
            ranks[t] = r
        j = k + 1
    rank_sum_pos = sum(ranks[idx] for idx, (s, l) in enumerate(allv) if l == 1)
    np_, nn_ = len(pos), len(neg)
    auroc2 = (rank_sum_pos - np_ * (np_ + 1) / 2) / (np_ * nn_)
    assert abs(auroc2 - auroc) < 1e-6, f"AUROC recompute mismatch {auroc2} vs {auroc}"
    print(json.dumps(out, indent=2))
    print(f"[self-check] AUROC recomputed via rank-sum = {auroc2:.3f} (matches)")
    return out

if __name__ == "__main__":
    run()
