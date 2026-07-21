"""
reversibility_predictability_probe.py -- the reversibility gate has its own floor. MIT.

SETTLED (credit, do not re-claim): irreversible actions bound what any post-hoc correction can fix
(Krakovna et al. stepwise relative reachability, arXiv:1806.01186; Leave-no-Trace arXiv:1711.06782;
corrigibility). Classifying agent tool-actions by reversibility as a defense-of-last-resort is also done
(Action-Graded Severity Scale arXiv:2607.07474; ToolEmu arXiv:2309.15817; OWASP agent guidance).

THE OPEN CLAIM (prior-art-checked OPEN 2026-07-13): every reversibility-gate defense ASSUMES an action's
reversibility is decidable EX-ANTE from its tool signature (2607.07474 assigns it as fixed per-tool metadata)
-- and NOBODY validates that assumption. If, for a measurable fraction of real tools, reversibility is
determined by the ARGUMENT VALUES rather than the tool identity (Terminal.Execute('ls') vs Execute('rm -rf'),
SQL SELECT vs DROP, send-to-internal vs send-to-external), then a per-tool metadata gate is UNSOUND by
construction on that fraction -- an irreducible floor no memory-integrity defense (prevention or detection)
can close, because the poison only has to steer the ARGUMENTS of an otherwise-benign-looking tool.

MEASUREMENT: over the ToolEmu corpus (38 toolkits, 330 tools -- a real external tool set we did NOT build),
label each tool for whether its reversibility is ARGUMENT-DEPENDENT. Two independent models label the full
set so the number is not one model's opinion (report raw agreement + Cohen's kappa). Metric = fraction of
tools whose reversibility is NOT decidable from the signature alone, plus a failure-mode taxonomy.

RUN:  python reversibility_predictability_probe.py            (uses server/.env keys; deepseek + glm)
"""
import json, os, re, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.environ.get("TE_CORPUS", os.path.join(HERE, "data", "toolemu_all_toolkits.json"))
OUT = os.path.join(HERE, "data", "reversibility_predictability.json")


def _load_env():
    env = {}
    p = os.path.join(HERE, "..", "..", "server", ".env")
    for line in open(p, encoding="utf-8"):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1); env[k] = v
    return env


ENV = _load_env()
ENDPOINTS = {
    "deepseek-v4-flash": (ENV.get("AGORA_API_BASE_URL", "https://ollama.com/v1"), ENV.get("AGORA_API_KEY", "")),
    "glm-5.2": (ENV.get("AGORA_API_BASE_URL", "https://ollama.com/v1"), ENV.get("AGORA_API_KEY", "")),
}


def chat(model, sys, usr, temperature=0.0, max_tokens=4000, retries=3):
    base, key = ENDPOINTS[model]
    body = json.dumps({"model": model, "temperature": temperature, "max_tokens": max_tokens,
                       "messages": [{"role": "system", "content": sys}, {"role": "user", "content": usr}]}).encode()
    for a in range(retries):
        try:
            req = urllib.request.Request(base + "/chat/completions", data=body,
                                         headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
            r = json.load(urllib.request.urlopen(req, timeout=180))
            return r["choices"][0]["message"]["content"]
        except Exception as e:
            if a == retries - 1:
                raise
            time.sleep(4 * (a + 1))


def parse_json(txt):
    txt = txt.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", txt, re.S)
    if m:
        txt = m.group(1).strip()
    m = re.search(r"(\[.*\]|\{.*\})", txt, re.S)
    if m:
        txt = m.group(1)
    return json.loads(txt)


def flatten_tools(corpus):
    tools = []
    for tk in corpus:
        for t in tk.get("tools", []):
            params = [p.get("name") for p in t.get("parameters", [])]
            tools.append({"toolkit": tk.get("toolkit"), "name": t.get("name"),
                          "summary": (t.get("summary") or "")[:240],
                          "params": params})
    return tools


SYS = (
    "You are a security analyst classifying whether an AI agent tool-action's REVERSIBILITY is decidable from "
    "the tool signature alone, or only from the ARGUMENT VALUES. Definition: an action is REVERSIBLE if, after "
    "it runs, an inverse or compensating operation available to the same agent can restore the prior state "
    "within a bounded window; otherwise IRREVERSIBLE. Be rigorous and concrete. Output STRICT JSON only."
)
USR_TMPL = (
    "For EACH tool below decide whether reversibility is ARGUMENT-DEPENDENT: i.e., does the same tool have BOTH "
    "a plausibly REVERSIBLE invocation AND a plausibly IRREVERSIBLE invocation depending on the argument values? "
    "(e.g. a shell 'Execute(command)' is arg-dependent: 'ls' reversible vs 'rm -rf /' irreversible; a pure "
    "read-only getter is NOT arg-dependent = always reversible; a dedicated 'PermanentlyDeleteAccount()' is NOT "
    "arg-dependent = always irreversible.)\n"
    "Return a JSON array, one object per tool, in order:\n"
    '{"name": <tool name>, "arg_dependent": <true|false>, '
    '"sig_label": <"REVERSIBLE"|"IRREVERSIBLE"|"MIXED">, '
    '"failure_mode": <"verb_polymorphic"|"destination_scope"|"magnitude_scope"|"target_identity"|"none">, '
    '"rev_example": <short concrete reversible args or null>, '
    '"irrev_example": <short concrete irreversible args or null>}\n\n'
    "TOOLS:\n"
)


def label(model, tools, batch=12):
    out = {}
    for i in range(0, len(tools), batch):
        part = tools[i:i + batch]
        listing = "\n".join(
            f"{j+1}. {t['name']} (toolkit {t['toolkit']}) params={t['params']} -- {t['summary']}"
            for j, t in enumerate(part))
        try:
            res = parse_json(chat(model, SYS, USR_TMPL + listing))
            if isinstance(res, dict):
                res = [res]
            for t, r in zip(part, res):
                out[(t["toolkit"], t["name"])] = r
        except Exception as e:
            print(f"  [{model}] batch {i//batch} parse/api fail: {str(e)[:80]}")
        print(f"  [{model}] labeled {min(i+batch, len(tools))}/{len(tools)}", flush=True)
    return out


def main():
    corpus = json.load(open(CORPUS, encoding="utf-8"))
    tools = flatten_tools(corpus)
    print(f"ToolEmu corpus: {len(corpus)} toolkits, {len(tools)} tools\n")

    print("Labeling with deepseek-v4-flash (full corpus)...")
    ds = label("deepseek-v4-flash", tools)
    print("\nLabeling with glm-5.2 (full corpus, reliability)...")
    gl = label("glm-5.2", tools)

    keys = [k for k in ds if k in gl]
    def ad(d, k):
        v = d[k].get("arg_dependent")
        return bool(v) if isinstance(v, bool) else str(v).lower() == "true"
    ds_ad = {k: ad(ds, k) for k in keys}
    gl_ad = {k: ad(gl, k) for k in keys}
    agree = sum(1 for k in keys if ds_ad[k] == gl_ad[k]) / len(keys)
    # Cohen's kappa
    both1 = sum(1 for k in keys if ds_ad[k] and gl_ad[k])
    both0 = sum(1 for k in keys if not ds_ad[k] and not gl_ad[k])
    po = (both1 + both0) / len(keys)
    p_ds = sum(ds_ad.values()) / len(keys); p_gl = sum(gl_ad.values()) / len(keys)
    pe = p_ds * p_gl + (1 - p_ds) * (1 - p_gl)
    kappa = (po - pe) / (1 - pe) if pe < 1 else 1.0
    # consensus arg-dependent fraction (both models agree true)
    consensus_ad = both1 / len(keys)
    either_ad = sum(1 for k in keys if ds_ad[k] or gl_ad[k]) / len(keys)

    # failure-mode taxonomy over consensus arg-dependent tools
    from collections import Counter
    fm = Counter(ds[k].get("failure_mode", "none") for k in keys if ds_ad[k] and gl_ad[k])

    print("\n" + "=" * 66)
    print(f"tools labeled by both models: {len(keys)}")
    print(f"arg-dependent (deepseek): {p_ds:.2f}   arg-dependent (glm): {p_gl:.2f}")
    print(f"inter-model raw agreement: {agree:.2f}   Cohen's kappa: {kappa:.2f}")
    print(f"CONSENSUS arg-dependent (both agree): {consensus_ad:.2f}  ({both1}/{len(keys)})")
    print(f"either-model arg-dependent:           {either_ad:.2f}")
    print(f"\n=> the reversibility gate is UNSOUND-by-signature on ~{consensus_ad*100:.0f}% of real tools")
    print("failure modes (consensus arg-dependent):")
    for m, c in fm.most_common():
        print(f"   {m:18} {c}")

    json.dump({"n_toolkits": len(corpus), "n_tools": len(tools), "n_labeled_both": len(keys),
               "arg_dependent_deepseek": round(p_ds, 3), "arg_dependent_glm": round(p_gl, 3),
               "raw_agreement": round(agree, 3), "cohens_kappa": round(kappa, 3),
               "consensus_arg_dependent": round(consensus_ad, 3), "either_arg_dependent": round(either_ad, 3),
               "failure_modes": dict(fm),
               "examples": [{"tool": f"{k[0]}.{k[1]}", "rev": ds[k].get("rev_example"),
                             "irrev": ds[k].get("irrev_example")}
                            for k in keys if ds_ad[k] and gl_ad[k]][:15]},
              open(OUT, "w"), indent=2)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
