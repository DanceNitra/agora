"""Does a vision LLM judge help pick the best makeup? Measured against the owner's own picks.

  python bench_judge.py sheet            -> writes judge_sheet.png (48 numbered looks) + judge_set.json
  python bench_judge.py judge --model typesafe/jev-router [--runs 3]
                                          -> asks the model for its top 5 of the sheet, logs latency and cost
  python bench_judge.py score            -> compares model and rule-score top 5 with owner_picks.json

owner_picks.json: {"top5": [tile numbers]} written from the owner's answer.
The API key is read from server/.env (OPENROUTER_API_KEY) and never printed.
"""
import base64
import json
import os
import sys
import time
import urllib.request

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
OUT = os.path.join(HERE, "..", "..", "agora_output", "reverse", "makeup_tool", "judge")
os.makedirs(OUT, exist_ok=True)


def sheet():
    import compare
    from agora_makeup import library, paint
    import itertools
    combos = list(itertools.product(library.base_looks(), library.INTENSITY, [None] + list(library.LIP), [None] + list(library.EYE)))
    rng = np.random.default_rng(11)
    looks = [library.variant(*combos[i]) for i in rng.choice(len(combos), 48, replace=False)]
    base = os.path.join(HERE, "agora_makeup", "data", "frontal_base.png")
    compare._init(base)
    tiles = []
    for i, l in enumerate(looks, 1):
        im = compare._paint(l).copy()
        cv2.rectangle(im, (0, 0), (44, 26), (0, 0, 0), -1)
        cv2.putText(im, str(i), (4, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        tiles.append(im)
    grid = np.vstack([np.hstack(tiles[r * 8:(r + 1) * 8]) for r in range(6)])
    cv2.imwrite(os.path.join(OUT, "judge_sheet.png"), grid)
    vm, face = paint.view_face()
    b = cv2.imread(base)
    skin = cv2.cvtColor(b, cv2.COLOR_BGR2LAB).astype(np.float32)
    from agora_makeup import zones
    cz = np.array([face.P(i) for i in zones.EYE["A"]["cheek"]]).mean(0).astype(int)
    skin_lab = skin[cz[1] - 8:cz[1] + 8, cz[0] - 8:cz[0] + 8].reshape(-1, 3).mean(0) * [100 / 255, 1, 1] - [0, 128, 128]
    rule = [compare.rule_score(l, skin_lab) for l in looks]
    json.dump({"ids": [l["id"] for l in looks], "rule_score": rule}, open(os.path.join(OUT, "judge_set.json"), "w"), indent=1)
    print("sheet", os.path.join(OUT, "judge_sheet.png"))


def _key():
    for line in open(os.path.join(HERE, "..", "..", "server", ".env"), encoding="utf-8"):
        if line.startswith("OPENROUTER_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"')
    raise SystemExit("OPENROUTER_API_KEY missing in server/.env")


PROMPT = ("You are a senior beauty editor choosing makeup for a fashion model. The image shows 48 makeup looks on "
          "the same face, numbered 1 to 48. Pick the 5 that make her look most like a top model: flattering, "
          "harmonious with her skin, polished, camera-ready. Reply with JSON only: {\"top5\": [n, n, n, n, n], "
          "\"why\": \"one short sentence\"}.")


def judge(model, runs):
    img = base64.b64encode(open(os.path.join(OUT, "judge_sheet.png"), "rb").read()).decode()
    log = []
    for r in range(runs):
        body = {"model": model, "messages": [{"role": "user", "content": [
            {"type": "text", "text": PROMPT}, {"type": "image_url", "image_url": {"url": "data:image/png;base64," + img}}]}],
            "usage": {"include": True}}
        req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", json.dumps(body).encode(),
                                     {"Authorization": "Bearer " + _key(), "Content-Type": "application/json"})
        t0 = time.time()
        d = json.loads(urllib.request.urlopen(req, timeout=300).read())
        dt = time.time() - t0
        txt = d["choices"][0]["message"]["content"]
        try:
            ans = json.loads(txt[txt.index("{"):txt.rindex("}") + 1])
        except Exception:
            ans = {"raw": txt[:300]}
        u = d.get("usage", {})
        log.append({"run": r + 1, "model_used": d.get("model"), "seconds": round(dt, 2), "cost_usd": u.get("cost"),
                    "tokens": u.get("total_tokens"), "answer": ans})
        print(json.dumps(log[-1]))
    json.dump(log, open(os.path.join(OUT, "judge_%s.json" % model.replace("/", "_")), "w"), indent=1)


def score():
    own = set(json.load(open(os.path.join(OUT, "owner_picks.json")))["top5"])
    st = json.load(open(os.path.join(OUT, "judge_set.json")))
    rule_top = [i + 1 for i in np.argsort(-np.array(st["rule_score"]), kind="stable")[:5]]
    print("owner", sorted(own), "| rule top5", rule_top, "hits", len(own & set(rule_top)), "of 5")
    rnd = np.random.default_rng(0)
    exp = np.mean([len(own & set(rnd.choice(48, 5, replace=False) + 1)) for _ in range(20000)])
    print("random baseline hits %.2f of 5" % exp)
    for f in os.listdir(OUT):
        if f.startswith("judge_") and f.endswith(".json") and f not in ("judge_set.json",):
            for run in json.load(open(os.path.join(OUT, f))):
                t = run["answer"].get("top5", [])
                print(f, "run", run["run"], t, "hits", len(own & set(t)), "of 5", run["seconds"], "s", run["cost_usd"], "USD")


if __name__ == "__main__":
    c = sys.argv[1]
    if c == "sheet":
        sheet()
    elif c == "judge":
        m = sys.argv[sys.argv.index("--model") + 1] if "--model" in sys.argv else "typesafe/jev-router"
        n = int(sys.argv[sys.argv.index("--runs") + 1]) if "--runs" in sys.argv else 3
        judge(m, n)
    elif c == "score":
        score()
