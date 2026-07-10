"""Crucible Live — make the pre-registered forecast for one claim card.

Usage: python forecast_claim.py <claim_id>
Reads claim_cards/<id>.json (claim + source ONLY — run this BEFORE any harness exists),
queries the two pre-registered frozen forecasters, writes forecasts/<id>.json.
Append-only: refuses to overwrite an existing forecast.
"""
import json, os, re, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
env = {}
for line in open(os.path.join(ROOT, "server", ".env"), encoding="utf-8"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); env[k.strip()] = v.strip().strip('"').strip("'")
KEY = env.get("AGORA_API_KEY") or env.get("OLLAMA_API_KEY")
URL = "https://ollama.com/v1/chat/completions"
MODELS = ["glm-5.2", "deepseek-v4-flash"]          # pre-registered, epoch 1
PROMPT = open(os.path.join(HERE, "forecast_prompt_v1.txt"), encoding="utf-8").read()

def chat(model, prompt):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": 6000, "temperature": 0}).encode()
    for a in range(4):
        try:
            r = json.loads(urllib.request.urlopen(urllib.request.Request(
                URL, data=body, headers={"Authorization": f"Bearer {KEY}",
                                         "Content-Type": "application/json"}), timeout=180).read())
            return r["choices"][0]["message"]["content"]
        except Exception as e:
            if a == 3:
                print(f"[{model} FAIL: {e}]"); return None
            time.sleep(5 * (a + 1))

def parse(text):
    if not text:
        return None, None
    m = re.search(r'"p_reproduced"\s*:\s*([0-9.]+)', text)
    p = float(m.group(1)) if m else None
    r = re.search(r'"reason"\s*:\s*"([^"]{0,300})"', text)
    return (p if p is not None and 0 <= p <= 1 else None), (r.group(1) if r else None)

def trailing_base_rate():
    """Frozen comparator: trailing reproduce-rate over the last 20 computable ledger verdicts."""
    led = json.load(open(os.path.join(ROOT, "public", "crucible", "crucible.json"), encoding="utf-8"))
    items = led if isinstance(led, list) else led.get("entries") or led.get("items")
    comp = [i for i in items if i.get("verdict") in ("REPRODUCED", "FAILED")][-20:]
    return round(sum(1 for i in comp if i["verdict"] == "REPRODUCED") / len(comp), 3) if comp else None

def main():
    cid = sys.argv[1]
    card_p = os.path.join(HERE, "claim_cards", f"{cid}.json")
    out_p = os.path.join(HERE, "forecasts", f"{cid}.json")
    if os.path.exists(out_p):
        sys.exit(f"REFUSED: forecast for {cid} already exists (append-only protocol)")
    card = json.load(open(card_p, encoding="utf-8"))
    prompt = PROMPT.format(claim=card["claim"], source=card.get("source", "unknown"))
    out = {"claim_id": cid, "prompt_version": "v1", "epoch": 1,
           "forecast_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "base_rate_comparator_trailing20": trailing_base_rate(), "models": {}}
    ps = []
    for model in MODELS:
        p, reason = parse(chat(model, prompt))
        out["models"][model] = {"p_reproduced": p, "reason": reason}
        if p is not None:
            ps.append(p)
    out["ensemble_p_reproduced"] = round(sum(ps) / len(ps), 3) if ps else None
    json.dump(out, open(out_p, "w", encoding="utf-8"), indent=2)
    print(json.dumps(out, indent=2))
    print(f"\nNow COMMIT+PUSH claim_cards/{cid}.json + forecasts/{cid}.json BEFORE writing any harness code.")

if __name__ == "__main__":
    main()
