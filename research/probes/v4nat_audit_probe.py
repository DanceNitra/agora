"""v4nat_audit_probe.py — the shortcut battery + baselines for the naturalized v4 fixture, before it goes to Marat.

Same discipline that caught the two shortcuts in templated v4: prove no cheap surface signal solves the set,
and that a chain-follower can. Reports, on the HELDOUT split (unseen style) unless noted:

  1. substring ANCHOR-NAME match  -> must be ~chance (names are filtered out of candidates)
  2. VALUE-token match            -> ~chance (values never in candidates)
  3. REVERT/KEEP keyword rule     -> ~chance (keywords filtered)
  4. TEMPLATE-signature majority  -> ~chance (naturalized phrasing has no fixed template; this is the artifact
                                     that beat templated v4 at F1 0.92, so it MUST collapse here)
  5. COSINE candidate->old vs new context line (local embedder) -> report AUROC (expected near chance)
  6. TRAIN->HELDOUT surface transfer: a majority-vote over candidate word-shape learned on TRAIN, scored on
     HELDOUT -> ~chance (proves the held-out-by-style split defeats surface memorization)
  7. LLM CHAIN-WALKER baseline (glm-5.2 / deepseek): read the natural context, resolve role->anchor->value,
     decide revert vs keep -> the "LLM baseline" Marat wants, and evidence the signal EXISTS in the text.

RUN: python research/probes/v4nat_audit_probe.py
"""
import os, sys, json, re, time, urllib.request
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

FX = "agora_output/public_fixtures/value_obscuring_reversion_heldout_v4nat.jsonl"
ROLES = ["security review", "the latency budget", "vendor contracts", "the data pipeline", "incident response",
         "the release train", "cost controls", "the schema registry", "access policy", "the mobile build",
         "capacity planning", "the search index"]
REVERT_KW = ["revert", "go back", "undo", "original", "before", "earlier", "previous", "prior", "first",
             "initial", "roll back", "restore", "used to", "back to", "older"]
KEEP_KW = ["keep", "stick with", "stay with", "leave it", "current", "latest", "newer", "updated"]

env = {}
for line in open("server/.env", encoding="utf-8", errors="replace"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); env[k.strip()] = v.strip().strip('"').strip("'")
KEY = env.get("AGORA_API_KEY") or env.get("OLLAMA_API_KEY")


def metrics(y, p):
    tp = sum(1 for a, b in zip(y, p) if a == 1 and b == 1); fp = sum(1 for a, b in zip(y, p) if a == 0 and b == 1)
    fn = sum(1 for a, b in zip(y, p) if a == 1 and b == 0); tn = sum(1 for a, b in zip(y, p) if a == 0 and b == 0)
    pr = tp / (tp + fp) if tp + fp else 0; rc = tp / (tp + fn) if tp + fn else 0
    f1 = 2 * pr * rc / (pr + rc) if pr + rc else 0
    return {"acc": round((tp + tn) / len(y), 3), "f1": round(f1, 3), "prec": round(pr, 3), "rec": round(rc, 3)}


def embed(texts):
    body = json.dumps({"model": "nomic-embed-text", "input": texts}).encode()
    r = json.loads(urllib.request.urlopen(urllib.request.Request(
        "http://localhost:11434/api/embed", data=body, headers={"Content-Type": "application/json"}),
        timeout=300).read())
    return r["embeddings"]


def cos(a, b): return sum(x * y for x, y in zip(a, b))


def auroc(y, s):
    pos = [si for si, yi in zip(s, y) if yi == 1]; neg = [si for si, yi in zip(s, y) if yi == 0]
    if not pos or not neg: return float("nan")
    return sum((a > b) + 0.5 * (a == b) for a in pos for b in neg) / (len(pos) * len(neg))


def chat(model, prompt):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": 16000, "temperature": 0.0}).encode()
    for a in range(3):
        try:
            r = urllib.request.urlopen(urllib.request.Request(
                "https://ollama.com/v1/chat/completions", data=body,
                headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}), timeout=180)
            return json.loads(r.read())["choices"][0]["message"]["content"].strip()
        except Exception:
            if a == 2: return None
            time.sleep(3)


def role_in(text):
    low = text.lower()
    hit = [r for r in ROLES if r.lower() in low]
    return max(hit, key=len) if hit else None


def main():
    rows = [json.loads(l) for l in open(FX, encoding="utf-8")]
    heldout = [r for r in rows if r["split"] == "heldout"]
    train = [r for r in rows if r["split"] == "train"]
    print(f"rows={len(rows)} train={len(train)} heldout={len(heldout)}")
    y = [r["reopens_stale"] for r in heldout]
    R = {}

    def norm(s): return s.lower().replace("the ", "").strip()

    # 1 anchor-name substring (strip the legitimately-named role first, so an anchor sharing a token with the
    # role — "the vendor" vs role "vendor contracts" — isn't a false hit)
    def anchor_sub(r):
        c = r["candidate"].lower().replace(r["role_target"].lower(), " ")
        o = norm(r["anchor_old"]) in c; cu = norm(r["anchor_current"]) in c
        return 1 if (o and not cu) else 0
    R["1_anchor_substring"] = metrics(y, [anchor_sub(r) for r in heldout])
    # 2 value token
    def val_match(r):
        c = r["candidate"].lower()
        return 1 if (r["old_value"] in c and r["current_value"] not in c) else 0
    R["2_value_match"] = metrics(y, [val_match(r) for r in heldout])
    # 3 revert/keep keyword
    def kw_rule(r):
        c = r["candidate"].lower()
        if any(k in c for k in REVERT_KW): return 1
        return 0
    R["3_keyword_rule"] = metrics(y, [kw_rule(r) for r in heldout])
    # 4 template signature: strip the role -> majority label per surface skeleton
    def sig(r):
        s = r["candidate"].lower()
        rt = role_in(s)
        if rt: s = s.replace(rt, "{r}")
        return re.sub(r"\d+", "#", s)
    by = {}
    for r in heldout: by.setdefault(sig(r), []).append(r["reopens_stale"])
    maj = {s: (1 if sum(v) / len(v) > 0.5 else 0) for s, v in by.items()}
    R["4_template_signature"] = metrics(y, [maj[sig(r)] for r in heldout])
    R["4_distinct_signatures"] = f"{len(by)}/{len(heldout)}"
    # 5 cosine candidate vs old/new context
    old_kw = ["was originally", "originally set", "first set", "set to"]
    feats = []
    for r in heldout:
        vecs = embed([r["candidate"]] + r["context"])
        cv = vecs[0]
        # identify old-value line vs current-value line by the value token present
        sims_old = max([cos(cv, v) for v, ln in zip(vecs[1:], r["context"]) if r["old_value"] in ln.lower()] or [0])
        sims_new = max([cos(cv, v) for v, ln in zip(vecs[1:], r["context"]) if r["current_value"] in ln.lower()] or [0])
        feats.append((sims_old, sims_new))
    R["5_cosine_sim_old>new"] = metrics(y, [1 if a > b else 0 for a, b in feats])
    R["5_cosine_AUROC"] = round(auroc(y, [a - b for a, b in feats]), 3)
    # 6 train->heldout surface transfer: candidate token-bag majority learned on TRAIN
    from collections import Counter
    tok = lambda s: set(re.findall(r"[a-z']+", s.lower()))
    pos_toks = Counter(); neg_toks = Counter()
    for r in train:
        (pos_toks if r["reopens_stale"] == 1 else neg_toks).update(tok(r["candidate"]))
    def surface_pred(r):
        sc = sum(pos_toks[t] - neg_toks[t] for t in tok(r["candidate"]))
        return 1 if sc > 0 else 0
    R["6_train_surface_transfer"] = metrics(y, [surface_pred(r) for r in heldout])

    # 7 LLM chain-walker baseline
    for model in ("glm-5.2", "deepseek-v4-flash"):
        preds = []
        for r in heldout:
            ctx = "\n".join(r["context"])
            prompt = (f"Context (a team's edit history):\n{ctx}\n\nNew utterance: \"{r['candidate']}\"\n\n"
                      f"The utterance refers to whoever is responsible for a certain area. Work out which "
                      f"value that person originally chose for the {r['entity']}, and whether following the "
                      f"utterance would REVERT to the old (superseded) value or KEEP the current one. "
                      f"Answer with exactly one word: revert or keep.")
            ans = chat(model, prompt)
            g = 1 if (ans and re.search(r"\brevert\b", ans.lower()) and not re.search(r"\bkeep\b", ans.lower().split("revert")[0])) else 0
            preds.append(g)
        R[f"7_LLM_{model}"] = metrics(y, preds)

    print(json.dumps(R, indent=2))
    lex = [R["1_anchor_substring"], R["2_value_match"], R["3_keyword_rule"], R["4_template_signature"],
           R["6_train_surface_transfer"]]
    all_lex_chance = all(m["f1"] <= 0.55 for m in lex)
    print("\nALL surface/lexical shortcuts at/below chance (f1<=0.55):", all_lex_chance)
    print("LLM chain-walker (signal exists if well above chance):",
          {k: v["f1"] for k, v in R.items() if k.startswith("7_")})
    json.dump(R, open(os.path.join(os.path.dirname(__file__), "v4nat_audit_probe_result.json"), "w"), indent=2)


if __name__ == "__main__":
    main()
