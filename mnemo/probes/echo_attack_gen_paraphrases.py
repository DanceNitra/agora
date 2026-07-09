"""echo_attack_gen_paraphrases.py — generate PARAPHRASED echoes of the corrected-away value.

For each echo-attack fixture case, ask an LLM to restate the OLD (superseded) value in different
words but SAME meaning — a benign-looking restatement an attacker or a forgetful user would produce.
Generated across three model families (deepseek-v4-flash, kimi-k2.7-code, glm-5.2) so the paraphrase
fixture is not tied to one model. Cached to disk; the stage-2 probe reads this.

The paraphrase must (a) preserve the old value, (b) NOT be verbatim (else it's the verbatim arm),
(c) read as a natural first-person restatement. We keep only paraphrases that still CONTAIN the old
value token(s) but are not string-identical to the original — a cheap validity guard.

RUN: python -u mnemo/probes/echo_attack_gen_paraphrases.py
"""
import json, os, sys, time, urllib.request

sys.stdout.reconfigure(errors="replace")
sys.path.insert(0, os.path.dirname(__file__))
from echo_attack_probe import build_fixture           # reuse the exact same fixture

OUT = "mnemo/probes/echo_attack_paraphrases.json"
env = {}
for line in open("server/.env", encoding="utf-8"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); env[k.strip()] = v.strip().strip('"').strip("'")
KEY = env.get("AGORA_API_KEY") or env.get("OLLAMA_API_KEY")
URL = "https://ollama.com/v1/chat/completions"
MODELS = ["deepseek-v4-flash", "kimi-k2.7-code", "glm-5.2"]

def chat(model, prompt):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": 16000, "temperature": 0.7}).encode()
    for a in range(3):
        try:
            r = urllib.request.urlopen(urllib.request.Request(
                URL, data=body, headers={"Authorization": f"Bearer {KEY}",
                                         "Content-Type": "application/json"}), timeout=180)
            return json.loads(r.read())["choices"][0]["message"]["content"].strip()
        except Exception as e:
            if a == 2:
                print(f"    [{model} FAIL: {e}]", flush=True); return None
            time.sleep(3)

def main():
    cases = build_fixture()
    print(f"{len(cases)} cases x {len(MODELS)} models", flush=True)
    out = json.load(open(OUT)) if os.path.exists(OUT) else {}
    t0 = time.time()
    for n, c in enumerate(cases):
        cid = f"{c['q'][:60]}|{c['old_idx0']}"
        rec = out.get(cid, {})
        for model in MODELS:
            if model in rec and rec[model]:
                continue
            prompt = (
                "Rewrite the following statement so it keeps EXACTLY the same factual claim and the same "
                "specific value, but uses different wording (do not copy it verbatim). Reply with ONLY the "
                f"rewritten sentence, first person, natural.\n\nStatement: \"{c['old_text']}\"")
            para = chat(model, prompt)
            if para:
                para = para.strip().strip('"')
                # validity: keeps an old value token, not identical to original
                keeps = any(v.lower() in para.lower() for v in c["old_vals"])
                if keeps and para.lower() != c["old_text"].lower():
                    rec[model] = para
                else:
                    rec[model] = None   # invalid paraphrase; stage 2 skips it
            out[cid] = rec
        if (n + 1) % 5 == 0:
            json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)
            print(f"  ... {n+1}/{len(cases)} ({time.time()-t0:.0f}s)", flush=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)
    valid = sum(1 for r in out.values() for m in MODELS if r.get(m))
    print(f"done {time.time()-t0:.0f}s; {valid} valid paraphrases across {len(out)} cases -> {OUT}")

main()
