"""Intent tagger + version resolver in front of inspeximus — builds and measures the split jacksonxly proposed
(Reddit, 2026-07-11): tag each utterance assert / correct / revert, resolve "before" against the timeline,
and let cosine/value-matching never touch a revert (a revert is an instruction on the version graph).

WHAT WE ALREADY HAD: the plumbing — inspeximus.revert(key) restores the superseded predecessor from the ledger
(channel separation), as_of()/history() is the bitemporal part, echo_guard retires content restatements.
WHAT THIS PROBE BUILDS: the missing front — a deterministic, ledger-aware intent tagger + a fuzzy-temporal
resolver ("back/before" -> predecessor, "original/at first" -> first version) — wired end-to-end into real
inspeximus ops, and measured against the case that motivated it all.

THE HARD PAIR, measured, not hand-waved: an ECHO ("the cache region is osaka", stale value restated) and an
UNMARKED LEGITIMATE REAFFIRM (the same sentence, said by someone who KNOWS it changed and wants it back) can
be surface-IDENTICAL. The fixture contains byte-identical pairs differing only in ground-truth intent (and,
optionally, one preceding context turn showing change-awareness). No utterance-only tagger can get both
right; the probe measures what each POLICY costs on a mixed stream:
  - safe     : unmarked assertion of a superseded value is treated as an echo (never restores)
  - trusting : ... is treated as a reaffirm (restores)
  - context  : restores only when the preceding turn shows change-awareness
This yields the number the thread said nobody publishes: the legitimate-reaffirm false-positive /
stale-echo false-negative tradeoff per policy.

Fixture discipline (lessons from the v4 audits, same day): templates drawn RANDOMLY, independent of the
label, with a template-balance assert; no revert keyword leaks into non-revert classes; the echo/reaffirm
twins are byte-identical by construction. Deterministic (seed). End-to-end runs on the REAL Inspeximus class
(echo_guard on), not a policy abstraction.

Optional --llm: classify the same utterances with cloud LLMs (glm-5.2, deepseek-v4-flash) given the same
history+context, same metrics — deterministic rules vs LLM tagging, side by side.

RUN: python research/probes/intent_tagger_router_probe.py [--llm]
"""
import sys, os, json, random, re, time, urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from inspeximus import Inspeximus

random.seed(23)

ENTS = [("cache region", ["osaka", "malmo", "quito"]), ("primary shard", ["delta7", "sigma2", "rho4"]),
        ("build target", ["arm64", "riscv", "wasm"]), ("default currency", ["forint", "guarani", "krona"]),
        ("route profile", ["coastal", "inland", "alpine"]), ("api tier", ["bronze", "platinum", "silver"]),
        ("index locale", ["tallinn", "cusco", "hobart"]), ("worker pool", ["amber", "cobalt", "jade"]),
        ("log sink", ["vault3", "harbor8", "pier5"]), ("retry policy", ["linear", "jitter", "stepped"]),
        ("color theme", ["sepia", "slate", "ochre"]), ("scheduler", ["roundrobin", "weighted", "fair"]),
        ("session store", ["sticky", "pooled", "sharded"]), ("cdn provider", ["fastly", "bunny", "orbit"]),
        ("rate limiter", ["tiered", "flat", "burst"]), ("search engine", ["elastic", "sonic", "quick"]),
        ("email sender", ["postmark", "sendy", "relayx"]), ("backup window", ["0200utc", "0400utc", "0100utc"]),
        ("queue driver", ["kafka", "nats", "pulsar"]), ("feature flag", ["on", "off", "canary"])]
THREE_VERSION = {e for e, _ in ENTS[:8]}   # first 8 entities carry a v1->v2->v3 history

T_ASSERT = ["the {ent} is {v}.", "we set the {ent} to {v}.", "{ent}: {v}.",
            "for now the {ent} is {v}.", "the team picked {v} for the {ent}."]
T_CORRECT = ["correction: the {ent} is now {v}.", "actually the {ent} changed to {v}.",
             "update — the {ent} is now {v}.", "scratch that, the {ent} moved to {v}.",
             "the {ent} was switched to {v}."]
T_REVERT_OBSC = ["go back to what we had for the {ent}.", "put the {ent} back the way it was.",
                 "revert the {ent} change.", "undo that last {ent} change.",
                 "switch the {ent} back to the previous one."]
T_REVERT_ORIG = ["go back to the original {ent}.", "put the {ent} back to what we started with.",
                 "revert the {ent} to the very first choice.", "restore the original {ent} setting.",
                 "take the {ent} back to the initial pick."]
T_REVERT_NAMED = ["set the {ent} back to {v}.", "put the {ent} back to {v}.",
                  "go back to {v} for the {ent}.", "revert the {ent} to {v}.",
                  "switch the {ent} back to {v}."]
T_ECHO = ["the {ent} is {v}.", "reminder: the {ent} is {v}.", "as noted, the {ent} is {v}.",
          "fyi the {ent} is {v}.", "per the standup, the {ent} is {v}."]
T_INNOCENT = ["before the standup we reviewed the {ent} dashboard.",
              "earlier today someone asked about the {ent} runbook.",
              "the {ent} was discussed before lunch, no decision.",
              "previously the {ent} alerts were noisy, unrelated note.",
              "before rollout we should document the {ent} owners."]
T_CONTEXT_AWARE = ["i saw the {ent} got changed to {new}.", "so the {ent} was moved to {new}, right?",
                   "noticed the {ent} correction to {new} landed.", "the {ent} switch to {new} went through.",
                   "someone updated the {ent} to {new} yesterday."]

REVERT_VERBS = re.compile(r"\b(go back|put .{0,24}back|revert|undo|restore|switch .{0,24}back|set .{0,24}back"
                          r"|back to (what|the (original|previous|first|initial))|the way it was"
                          r"|what we (had|started with)|very first|initial pick)\b")
ORIGINAL_MARK = re.compile(r"\b(original|very first|started with|initial)\b")
CORRECT_MARK = re.compile(r"\b(correction|actually|update|scratch that|is now|moved to|was switched|changed to)\b")


def extract_value(text, ent, values):
    for v in values:
        if re.search(rf"\b{re.escape(v)}\b", text):
            return v
    return None


def build_fixture():
    rows = []
    for ent, vals in ENTS:
        three = ent in THREE_VERSION
        hist = vals[:3] if three else vals[:2]           # v1 -> v2 (-> v3)
        cur, prev, first = hist[-1], hist[-2], hist[0]
        base = {"entity": ent, "history": hist}
        rows.append({**base, "utterance": random.choice(T_CORRECT).format(ent=ent, v="zenith"),
                     "context": None, "cls": "correction", "true_intent": "correct",
                     "expect_current": "zenith"})
        rows.append({**base, "utterance": random.choice(T_REVERT_OBSC).format(ent=ent),
                     "context": None, "cls": "revert_obscuring", "true_intent": "revert",
                     "expect_current": prev})
        rows.append({**base, "utterance": random.choice(T_REVERT_NAMED).format(ent=ent, v=prev),
                     "context": None, "cls": "revert_named", "true_intent": "revert",
                     "expect_current": prev})
        if three:
            rows.append({**base, "utterance": random.choice(T_REVERT_ORIG).format(ent=ent),
                         "context": None, "cls": "revert_original", "true_intent": "revert",
                         "expect_current": first})
        echo_text = random.choice(T_ECHO).format(ent=ent, v=prev)
        rows.append({**base, "utterance": echo_text, "context": None, "cls": "echo",
                     "true_intent": "echo", "expect_current": cur})
        rows.append({**base, "utterance": echo_text,   # byte-identical twin, different ground truth
                     "context": random.choice(T_CONTEXT_AWARE).format(ent=ent, new=cur),
                     "cls": "reaffirm_unmarked", "true_intent": "revert", "expect_current": prev})
        rows.append({**base, "utterance": echo_text,   # ADVERSARIAL: echo with a FORGED change-aware
                     "context": random.choice(T_CONTEXT_AWARE).format(ent=ent, new=cur),  # context turn —
                     "cls": "adversarial_context_echo", "true_intent": "echo",  # byte-identical to the
                     "expect_current": cur})           # reaffirm twin INCLUDING context; only provenance differs
        rows.append({**base, "utterance": random.choice(T_INNOCENT).format(ent=ent),
                     "context": None, "cls": "innocent_temporal", "true_intent": "assert",
                     "expect_current": cur})
    # fairness: no revert verb leaks into non-revert classes; echo/reaffirm twins byte-identical
    for r in rows:
        if r["true_intent"] != "revert" or r["cls"] == "reaffirm_unmarked":
            assert not REVERT_VERBS.search(r["utterance"]), f"revert verb leaked: {r['utterance']!r}"
    return rows


# ── the deterministic, ledger-aware tagger + resolver ────────────────────────
def current_value(store, key):
    act = [r for r in store.items if r.get("key") == key and r.get("status") == "active"
           and r.get("object") is not None]
    return act[-1]["object"] if act else None


def value_chain(store, key):
    """the values that were actually CURRENT at some point, oldest->newest. Skips echo-retired arrivals
    (meta.echo_blocked — retired stale-on-arrival, never the current value); inspeximus's per-record
    superseded_by_policy judge-log is what makes this distinction readable."""
    chain = []
    for r in store.items:
        if r.get("key") != key or r.get("object") is None:
            continue
        if (r.get("meta") or {}).get("echo_blocked"):
            continue
        if not chain or chain[-1] != r["object"]:
            chain.append(r["object"])
    return chain


def tag(store, key, values, utterance, context, policy):
    """-> (intent, target_value|None): revert carries the version to restore (None = predecessor)."""
    u = utterance.lower()
    chain = value_chain(store, key)
    current = current_value(store, key)
    if REVERT_VERBS.search(u):
        named = extract_value(u, key, values)
        if named and named in chain and named != current:
            return "revert", named
        if ORIGINAL_MARK.search(u) and len(chain) > 1:
            return "revert", chain[0]
        return "revert", None                              # plain revert -> predecessor via revert()
    val = extract_value(u, key, values)
    if CORRECT_MARK.search(u) and val is None:
        val = extract_value(u, key, values + ["zenith"])
    if val is None:
        return "assert", None                              # no value, no revert verb -> plain note
    if val == current or val not in chain:
        return ("correct" if CORRECT_MARK.search(u) else "assert"), None
    # AMBIGUOUS: unmarked assertion of a superseded value — echo or reaffirm, policy decides
    if policy == "trusting":
        return "revert", val
    if policy == "context" and context and re.search(r"\b(changed|moved|switched|updated|correction|went through)\b",
                                                     context.lower()) and (current in context.lower() if current else False):
        return "revert", val
    return "echo", None


def route(store, key, intent, target, utterance, values):
    if intent == "revert":
        if target is None:
            store.revert(key)                              # ledger-resolved predecessor
        else:                                              # named/original -> sanctioned reaffirm write
            store.remember(f"restore {key} to {target}", key=key, object=target, reaffirm=True)
    else:                                                  # assert/correct/echo -> content write;
        val = extract_value(utterance, key, values + ["zenith"])   # echo_guard retires a stale echo
        store.remember(utterance, key=key if val else None, object=val)


def replay(row, policy):
    store = Inspeximus(path=None)
    store.echo_guard = True
    for i, v in enumerate(row["history"]):
        t = (T_ASSERT[0] if i == 0 else T_CORRECT[0]).format(ent=row["entity"], v=v)
        store.remember(t, key=row["entity"], object=v)
    values = row["history"] + ["zenith"]
    intent, target = tag(store, row["entity"], values, row["utterance"], row["context"], policy)
    route(store, row["entity"], intent, target, row["utterance"], row["history"])
    return intent, current_value(store, row["entity"])


def main():
    rows = build_fixture()
    print(f"fixture: {len(rows)} rows | classes:",
          {c: sum(1 for r in rows if r['cls'] == c) for c in dict.fromkeys(r['cls'] for r in rows)})
    out = {"n": len(rows), "policies": {}}
    for policy in ("safe", "context", "trusting"):
        per = {}
        for r in rows:
            intent, cur = replay(r, policy)
            ok_intent = (intent == r["true_intent"]) or (r["true_intent"] == "echo" and intent == "echo")
            ok_state = (cur == r["expect_current"])
            d = per.setdefault(r["cls"], {"n": 0, "intent_ok": 0, "state_ok": 0})
            d["n"] += 1; d["intent_ok"] += ok_intent; d["state_ok"] += ok_state
        for c, d in per.items():
            d["intent_acc"] = round(d["intent_ok"] / d["n"], 3)
            d["state_acc"] = round(d["state_ok"] / d["n"], 3)
        out["policies"][policy] = per
        print(f"\n== policy: {policy} ==")
        for c, d in per.items():
            print(f"  {c:18s} n={d['n']:2d} intent_acc={d['intent_acc']:.2f} end2end_state_acc={d['state_acc']:.2f}")
    # the headline tradeoff: echo blocked vs legitimate unmarked reaffirm honored
    hl = {}
    for policy in ("safe", "context", "trusting"):
        p = out["policies"][policy]
        hl[policy] = {"stale_echo_blocked": p["echo"]["state_acc"],
                      "legit_reaffirm_honored": p["reaffirm_unmarked"]["state_acc"],
                      "forged_context_echo_blocked": p["adversarial_context_echo"]["state_acc"]}
    out["headline_tradeoff"] = hl
    print("\nHEADLINE (echo blocked / legitimate unmarked reaffirm honored / FORGED-context echo blocked):")
    for k, v in hl.items():
        print(f"  {k:9s} echo_blocked={v['stale_echo_blocked']:.2f}  reaffirm_honored={v['legit_reaffirm_honored']:.2f}"
              f"  forged_ctx_echo_blocked={v['forged_context_echo_blocked']:.2f}")
    json.dump(out, open(os.path.join(os.path.dirname(__file__), "intent_tagger_router_probe_result.json"), "w"),
              indent=2)

    if "--llm" in sys.argv:
        llm_pass(rows, out)


def llm_pass(rows, out):
    env = {}
    for line in open("server/.env", encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1); env[k.strip()] = v.strip().strip('"').strip("'")
    key = env.get("AGORA_API_KEY") or env.get("OLLAMA_API_KEY")
    url = "https://ollama.com/v1/chat/completions"

    def chat(model, prompt):
        body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}],
                           "max_tokens": 16000, "temperature": 0.0}).encode()
        for a in range(3):
            try:
                r = urllib.request.urlopen(urllib.request.Request(
                    url, data=body, headers={"Authorization": f"Bearer {key}",
                                             "Content-Type": "application/json"}), timeout=180)
                return json.loads(r.read())["choices"][0]["message"]["content"].strip()
            except Exception as e:
                if a == 2:
                    return None
                time.sleep(3)

    for model in ("glm-5.2", "deepseek-v4-flash"):
        per = {}
        for i, r in enumerate(rows):
            hist_lines = " -> ".join(r["history"])
            ctx = f'\nPrevious turn: "{r["context"]}"' if r["context"] else ""
            prompt = (f'A memory store tracks "{r["entity"]}". Version history (oldest to current): {hist_lines}.'
                      f'{ctx}\nNew utterance: "{r["utterance"]}"\n'
                      "Classify the utterance's intent toward the stored value. Answer with EXACTLY one word:\n"
                      "assert (new information or unrelated note), correct (deliberate update to a new value), "
                      "revert (wants a previous version restored), echo (restates an outdated value without "
                      "intending to change anything).")
            ans = chat(model, prompt)
            got = None
            if ans:
                m = re.search(r"\b(assert|correct|revert|echo)\b", ans.lower())
                got = m.group(1) if m else None
            d = per.setdefault(r["cls"], {"n": 0, "ok": 0, "none": 0})
            d["n"] += 1
            if got is None:
                d["none"] += 1
            elif got == r["true_intent"]:
                d["ok"] += 1
            if (i + 1) % 20 == 0:
                print(f"  [{model}] {i+1}/{len(rows)}", flush=True)
        print(f"\n== LLM tagger: {model} ==")
        for c, d in per.items():
            print(f"  {c:18s} n={d['n']:2d} intent_acc={d['ok']/d['n']:.2f}" +
                  (f" (unparsed {d['none']})" if d["none"] else ""))
        out.setdefault("llm", {})[model] = per
    json.dump(out, open(os.path.join(os.path.dirname(__file__), "intent_tagger_router_probe_result.json"), "w"),
              indent=2)


if __name__ == "__main__":
    main()
