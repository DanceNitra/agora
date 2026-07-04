"""THE VERIFICATION TAX (cloud-free, direction A). When an AI does a task fast but its errors are systematic,
the output must be VERIFIED before it can be trusted. The real reliability of AI output is the residual error
AFTER verification: residual = e*(1-c), where e = first-pass error rate, c = fraction of errors verification
CATCHES. Thesis: c (catchability) is governed by TASK VERIFIABILITY — high on checkable tasks (recompute), low
on hard reasoning (systematic errors evade verification, our wall). So AI task-gains convert to trustworthy
output only where verification is reliable; on hard tasks the verification tax leaves high residual error.
Worker + self-verifier = qwen3-coder:30b across 4 task types spanning the verifiability spectrum."""
import os, re, json, time, random
from concurrent.futures import ThreadPoolExecutor
import urllib.request
import numpy as np

B = os.path.dirname(os.path.abspath(__file__))
URL = os.environ.get("VTAX_URL", "http://localhost:11434/v1/chat/completions")
MODEL = os.environ.get("VTAX_MODEL", "qwen3-coder:30b")
API_KEY = os.environ.get("VTAX_API_KEY", "")  # set for a hosted OpenAI-compatible endpoint
rng = random.Random(7)
LET = "ABCDEFGHIJ"


def chat(msgs, cap=700):
    body = {"model": MODEL, "temperature": 0.0, "max_tokens": cap, "messages": msgs}
    hdr = {"Content-Type": "application/json"}
    if API_KEY:
        hdr["Authorization"] = "Bearer " + API_KEY
    for _ in range(3):
        try:
            r = json.loads(urllib.request.urlopen(urllib.request.Request(URL, data=json.dumps(body).encode(), headers=hdr), timeout=180).read())
            return r["choices"][0]["message"].get("content") or ""
        except Exception:
            time.sleep(1.2)
    return ""


def _num(t):
    t = (t or "").upper(); i = t.rfind("ANSWER:"); seg = (t[i + 7:] if i >= 0 else t).replace(",", "")
    m = re.search(r"-?\d+\.?\d*", seg); return float(m.group(0)) if m else None


def _letter(t, n):
    t = (t or "").upper(); i = t.rfind("ANSWER:"); seg = t[i + 7:] if i >= 0 else t
    m = re.search(r"[A-J]", seg); return m.group(0) if (m and m.group(0) in LET[:n]) else None


def _norm(s):
    s = (s or "").lower(); s = re.sub(r"[^a-z0-9 ]", " ", s); return re.sub(r"\s+", " ", s).strip()


def arithmetic():
    out = []
    for _ in range(25):
        nums = [rng.randint(100, 999) for _ in range(15)]
        out.append(("Compute the exact sum of these numbers: " + ", ".join(map(str, nums)), sum(nums), "num"))
    return out


def musique():
    d = json.load(open(os.path.join(B, "data", "musique_grounding.json"), encoding="utf-8"))[:25]
    out = []
    for it in d:
        ctx = "Paragraphs:\n" + "\n".join(f"[{i+1}] {p}" for i, p in enumerate(it["full_paras"]))
        out.append((ctx + f"\n\nQuestion: {it['question']}", (it["answer"], it["aliases"]), "sub"))
    return out


def estimation():
    QA = [("the boiling point of water in Celsius", 100), ("the year the Berlin Wall fell", 1989), ("the speed of light in km/s", 299792),
          ("the number of bones in the adult human body", 206), ("the height of Mount Everest in meters", 8849), ("the population of Japan in millions", 125),
          ("the distance from Earth to the Moon in km", 384400), ("the year WWII ended", 1945), ("the number of UN member countries", 193),
          ("the diameter of the Earth in km", 12742), ("the length of the Amazon River in km", 6400), ("the speed of sound in air in m/s", 343),
          ("the atomic number of gold", 79), ("the number of elements in the periodic table", 118), ("the height of the Eiffel Tower in meters", 330),
          ("the year the French Revolution began", 1789), ("the population of the US in millions", 331), ("the year the Titanic sank", 1912),
          ("the number of chromosomes in a human cell", 46), ("the freezing point of water in Fahrenheit", 32), ("the number of keys on a piano", 88),
          ("gravity at Earth surface in m/s^2", 9.81), ("the boiling point of water in Fahrenheit", 212), ("the number of teeth in an adult human", 32),
          ("the year the telephone was patented", 1876)]
    return [(f"Estimate: what is {q}?", t, "est") for q, t in QA]


def mmlu():
    d = json.load(open(os.path.join(B, "data", "mmlupro_hard.json"), encoding="utf-8"))[:25]
    out = []
    for it in d:
        opts = "\n".join(f"{LET[i]}. {o}" for i, o in enumerate(it["options"]))
        out.append((f"{it['question']}\nOptions:\n{opts}", (it["gold_letter"], len(it["options"])), "mc"))
    return out


def grade(kind, ans, truth):
    if kind == "num":
        v = _num(ans); return v is not None and abs(v - truth) < 0.5
    if kind == "est":
        v = _num(ans); return v is not None and v > 0 and abs(np.log10(v / truth)) < np.log10(1.2)
    if kind == "sub":
        gold, al = truth; npd = _norm(ans); return bool(npd) and any(_norm(c) and _norm(c) in npd for c in [gold] + list(al or []))
    if kind == "mc":
        gold, n = truth; return _letter(ans, n) == gold
    return False


SYS_W = "Solve the task. Reason briefly, then end with exactly 'ANSWER: <answer>'."
SYS_V = "You are checking whether a proposed answer is correct. Reason briefly, then end with exactly 'VERDICT: YES' (correct) or 'VERDICT: NO' (incorrect)."


def run_task(name, items):
    def do(it):
        prompt, truth, kind = it
        ans = chat([{"role": "system", "content": SYS_W}, {"role": "user", "content": prompt + "\nReply 'ANSWER: <answer>'."}]).strip()
        ok = grade(kind, ans, truth)
        short = ans.split("ANSWER:")[-1].strip().splitlines()[0][:80] if "ANSWER:" in ans.upper() else ans[:80]
        v = chat([{"role": "system", "content": SYS_V}, {"role": "user", "content": prompt + f"\n\nProposed answer: {short}\nIs it correct?"}], cap=400)
        vu = v.upper(); idx = vu.rfind("VERDICT:"); seg = vu[idx + 8:] if idx >= 0 else vu
        says_no = ("NO" in seg) if idx >= 0 else ("NO" in vu and "YES" not in vu)
        return ok, says_no
    with ThreadPoolExecutor(max_workers=2) as pool:
        res = list(pool.map(do, items))
    e = 1 - sum(1 for ok, _ in res if ok) / len(res)
    wrong = [no for ok, no in res if not ok]
    right = [no for ok, no in res if ok]
    c = (sum(1 for no in wrong if no) / len(wrong)) if wrong else 0.0
    fa = (sum(1 for no in right if no) / len(right)) if right else 0.0
    return {"task": name, "n": len(items), "error_rate": round(e, 3), "verify_catch_rate": round(c, 3),
            "false_alarm": round(fa, 3), "residual_after_verify": round(e * (1 - c), 3)}


if __name__ == "__main__":
    print(f"compile OK - VERIFICATION TAX, worker+self-verify={MODEL}", flush=True)
    tasks = [("arithmetic (checkable)", arithmetic()), ("MMLU-Pro (knowledge)", mmlu()),
             ("numeric estimation", estimation()), ("multi-hop QA (hard reasoning)", musique())]
    rows = []
    for name, items in tasks:
        r = run_task(name, items); rows.append(r)
        print(f"  {name:32s}: e={r['error_rate']:.2f}  catch={r['verify_catch_rate']:.2f}  residual e(1-c)={r['residual_after_verify']:.3f}  (FA {r['false_alarm']:.2f})", flush=True)
    json.dump(rows, open(os.path.join(B, "verification_tax_result.json"), "w"), indent=1)
    print("\n=== VERDICT (the verification tax) ===", flush=True)
    rows.sort(key=lambda r: r["verify_catch_rate"], reverse=True)
    hi, lo = rows[0], rows[-1]
    if hi["verify_catch_rate"] - lo["verify_catch_rate"] >= 0.25:
        print(f"  VERIFICATION TAX CONFIRMED: catchability spans the verifiability spectrum ({lo['verify_catch_rate']:.2f} on '{lo['task']}' -> {hi['verify_catch_rate']:.2f} on '{hi['task']}'). On hard tasks self-verification catches few errors, so residual error AFTER verifying stays high ({lo['residual_after_verify']:.2f}) -> fast AI output can't be cheaply trusted, the task speedup does not convert to reliable output. On checkable tasks verification rescues it (residual {hi['residual_after_verify']:.2f}).", flush=True)
    else:
        print(f"  WEAK: catch gradient small ({lo['verify_catch_rate']:.2f}-{hi['verify_catch_rate']:.2f}).", flush=True)
    print("DONE", flush=True)
