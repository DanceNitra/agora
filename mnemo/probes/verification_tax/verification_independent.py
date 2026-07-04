"""Direction A completer: does an INDEPENDENT strong checker recover what self-verification cannot?
Self-verification fails on hard reasoning (catch ~0.19-0.36, glm-5.2 even worse, FA->0). The positive
complement: a worker (qwen3-coder:30b) answers hard tasks; we compare SELF-verification (qwen30 checks itself)
vs INDEPENDENT verification (glm-5.2, a stronger DIFFERENT-family model, checks qwen30's answers). If the
independent strong checker catches far more of the worker's errors, 'pay for an independent checker' is the
fix and we quantify it. If it ALSO catches few (because errors are shared across families, rho~0.7), even
external verification is limited -> the tax is deep. Hard tasks only (MMLU-Pro + multi-hop QA)."""
import os, re, sys, json, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verification_tax as vt   # task builders + grade + qwen30 chat (vt.chat)


def _cfg(path, key):
    txt = open(os.path.join(vt.B, "..", "..", path), "rb").read().decode("utf-8", "replace")
    m = re.search(key + r'\s*=\s*"?([^"\r\n]+)', txt)
    return m.group(1).strip() if m else None


_BASE = (_cfg("server/.env", "AGORA_REASONING_BASE_URL") or "").rstrip("/") + "/chat/completions"
_KEY = _cfg("server/.env", "AGORA_REASONING_KEY")


def glm_chat(msgs, cap=1400):
    body = {"model": "glm-5.2:cloud", "temperature": 0.0, "max_tokens": cap, "messages": msgs}
    hdr = {"Content-Type": "application/json", "Authorization": "Bearer " + (_KEY or "")}
    for _ in range(3):
        try:
            r = json.loads(urllib.request.urlopen(urllib.request.Request(_BASE, data=json.dumps(body).encode(), headers=hdr), timeout=240).read())
            return r["choices"][0]["message"].get("content") or ""
        except Exception:
            time.sleep(1.5)
    return ""


def verdict_no(txt, has_marker=True):
    vu = (txt or "").upper(); idx = vu.rfind("VERDICT:"); seg = vu[idx + 8:] if idx >= 0 else vu
    return ("NO" in seg) if idx >= 0 else ("NO" in vu and "YES" not in vu)


def run_task(name, items):
    def do(it):
        prompt, truth, kind = it
        ans = vt.chat([{"role": "system", "content": vt.SYS_W}, {"role": "user", "content": prompt + "\nReply 'ANSWER: <answer>'."}]).strip()
        ok = vt.grade(kind, ans, truth)
        short = ans.split("ANSWER:")[-1].strip().splitlines()[0][:80] if "ANSWER:" in ans.upper() else ans[:80]
        vmsg = [{"role": "system", "content": vt.SYS_V}, {"role": "user", "content": prompt + f"\n\nProposed answer: {short}\nIs it correct?"}]
        self_no = verdict_no(vt.chat(vmsg, cap=400))          # qwen30 self-verify
        indep_no = verdict_no(glm_chat(vmsg))                  # glm-5.2 independent verify
        return ok, self_no, indep_no
    with ThreadPoolExecutor(max_workers=2) as pool:
        res = list(pool.map(do, items))
    n = len(res); e = 1 - sum(1 for ok, _, _ in res if ok) / n
    wrong = [(s, i) for ok, s, i in res if not ok]
    right = [(s, i) for ok, s, i in res if ok]
    def rate(lst, idx, val):
        return (sum(1 for x in lst if x[idx] == val) / len(lst)) if lst else 0.0
    cs = rate(wrong, 0, True); ci = rate(wrong, 1, True)       # catch (NO on wrong)
    fas = rate(right, 0, True); fai = rate(right, 1, True)     # false alarm (NO on right)
    return {"task": name, "n": n, "error_rate": round(e, 3),
            "self_catch": round(cs, 3), "indep_catch": round(ci, 3),
            "self_FA": round(fas, 3), "indep_FA": round(fai, 3),
            "residual_self": round(e * (1 - cs), 3), "residual_indep": round(e * (1 - ci), 3)}


if __name__ == "__main__":
    print("compile OK - INDEPENDENT vs SELF verification, worker=qwen3-coder:30b, indep-checker=glm-5.2", flush=True)
    tasks = [("MMLU-Pro (hard)", vt.mmlu()), ("multi-hop QA (hard)", vt.musique())]
    rows = []
    for name, items in tasks:
        r = run_task(name, items); rows.append(r)
        print(f"  {name:22s}: e={r['error_rate']:.2f}  SELF catch={r['self_catch']:.2f} (FA {r['self_FA']:.2f}, resid {r['residual_self']:.2f})  |  INDEP catch={r['indep_catch']:.2f} (FA {r['indep_FA']:.2f}, resid {r['residual_indep']:.2f})", flush=True)
    json.dump(rows, open(os.path.join(vt.B, "verification_independent_result.json"), "w"), indent=1)
    ms = sum(r["self_catch"] for r in rows) / len(rows); mi = sum(r["indep_catch"] for r in rows) / len(rows)
    print("\n=== VERDICT ===", flush=True)
    print(f"  mean hard-task catch:  SELF={ms:.2f}  INDEPENDENT(glm-5.2)={mi:.2f}", flush=True)
    if mi - ms >= 0.20:
        print(f"  EXTERNAL VERIFICATION IS THE FIX: an independent strong checker catches far more of the worker's errors ({mi:.2f} vs self {ms:.2f}) -> the verification tax is payable, but ONLY by paying for an independent (different-family, comparably-capable) checker — exactly the bootstrap law (reliability comes from outside the model).", flush=True)
    elif mi - ms >= 0.08:
        print(f"  PARTIAL: independent checker helps ({mi:.2f} vs {ms:.2f}) but is itself limited (shared cross-family blind spots) — external verification recovers only part of the tax.", flush=True)
    else:
        print(f"  TAX IS DEEP: even an independent strong checker catches no more than self ({mi:.2f} vs {ms:.2f}) — errors are shared across families (rho~0.7), so external verification is also blind. Reliability needs ground truth / a checkable task, not just another model.", flush=True)
    print("DONE", flush=True)
