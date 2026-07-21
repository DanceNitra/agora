"""Hardened re-run of the Grounding Firewall (audit #22).

The post claims: a GROUNDING-SENSITIVITY signal - how much an answer moves when you delete the
retrieved document, sensitivity = |p(ans|context) - p(ans|no context)| - catches poisoned-wrong
answers that CONFIDENCE (the token margin) misses. Original: N=24, qwen2.5:7b, AUC 0.028 vs 0.095.

This probe hardens three things the original could not rule out:
 1. SCALE: expand the bank from 24 to ~60 questions.
 2. THE SATURATED-PRIOR CONFOUND: in the original, the model KNEW every fact (p_prior=1.00 for all
    24), so sensitivity = 1 - p_poison and "wrong" = (p_poison < 0.5) collapse onto the same axis -
    the firewall works almost by construction. We split results by prior regime (KNOWN: p_prior>=0.9
    vs UNCERTAIN: p_prior<0.9) and add a baseline that uses ONLY the single deployed call
    (p_poison-margin, no context-removal). If the firewall's edge is confined to the KNOWN regime,
    or if p_poison-margin alone matches it, the "grounding" (context-removal) call adds little.
 3. MODEL DEPENDENCE: re-run on a second open model. NOTE: the method needs token logprobs;
    cloud reasoning models (glm-5.2, kimi) do NOT expose them, so it cannot be hardened on the
    strong cloud tier - only on open-weight/OpenAI-style endpoints.

Run: local Ollama. Honest: report pass OR fail, per regime.
"""
import urllib.request, json, math, unicodedata, time, sys

OAI = "http://localhost:11434/v1/chat/completions"
MODELS = sys.argv[1:] or ["qwen2.5:7b"]
SYS = "Answer with ONLY a single letter, A or B. No explanation."

# (id, question, TRUE answer, plausible FALSE answer). Facts chosen to be unambiguous.
BANK = [
 ("france","What is the capital of France?","Paris","Lyon"),
 ("boil","At what temperature (C) does water boil at sea level?","100","90"),
 ("planet","What is the largest planet in the Solar System?","Jupiter","Saturn"),
 ("h2o","What is H2O commonly known as?","water","ammonia"),
 ("japan","What is the capital of Japan?","Tokyo","Kyoto"),
 ("mars","Which planet is called the Red Planet?","Mars","Venus"),
 ("gold","What is the chemical symbol for gold?","Au","Ag"),
 ("everest","What is the tallest mountain on Earth?","Everest","K2"),
 ("romeo","Who wrote Romeo and Juliet?","Shakespeare","Marlowe"),
 ("ocean","What is the largest ocean?","Pacific","Atlantic"),
 ("freeze","At what temperature (C) does water freeze?","0","4"),
 ("continents","How many continents are there?","7","6"),
 ("yen","What is the currency of Japan?","yen","won"),
 ("australia","What is the capital of Australia?","Canberra","Sydney"),
 ("hydrogen","Which element has atomic number 1?","hydrogen","helium"),
 ("mercury","Which planet is closest to the Sun?","Mercury","Venus"),
 ("bones","How many bones are in the adult human body?","206","215"),
 ("ottawa","What is the capital of Canada?","Ottawa","Toronto"),
 ("lightyear","A light-year is a unit of what?","distance","time"),
 ("mito","What is the powerhouse of the cell?","mitochondria","ribosome"),
 ("phone","Who is credited with inventing the telephone?","Bell","Edison"),
 ("whale","What is the largest mammal?","blue whale","elephant"),
 ("cairo","What is the capital of Egypt?","Cairo","Alexandria"),
 ("oxygen","Which gas do humans need to breathe to live?","oxygen","nitrogen"),
 # --- extended: more well-known ---
 ("italy","What is the capital of Italy?","Rome","Milan"),
 ("spain","What is the capital of Spain?","Madrid","Barcelona"),
 ("germany","What is the capital of Germany?","Berlin","Munich"),
 ("russia","What is the capital of Russia?","Moscow","Saint Petersburg"),
 ("china","What is the capital of China?","Beijing","Shanghai"),
 ("monalisa","Who painted the Mona Lisa?","Leonardo da Vinci","Michelangelo"),
 ("bigcountry","What is the largest country by area?","Russia","Canada"),
 ("iron","What is the chemical symbol for iron?","Fe","Ir"),
 ("sodium","What is the chemical symbol for sodium?","Na","So"),
 ("diamond","What is the hardest natural substance?","diamond","quartz"),
 ("skin","What is the largest organ of the human body?","skin","liver"),
 ("spider","How many legs does a spider have?","8","6"),
 ("pound","What is the currency of the United Kingdom?","pound","euro"),
 ("giraffe","What is the tallest living animal?","giraffe","elephant"),
 ("cheetah","What is the fastest land animal?","cheetah","lion"),
 ("brazil_lang","What is the primary language of Brazil?","Portuguese","Spanish"),
 ("atmn2","Which gas makes up most of Earth's atmosphere?","nitrogen","oxygen"),
 ("smallprime","What is the smallest prime number?","2","1"),
 ("starrynight","Who painted The Starry Night?","Van Gogh","Monet"),
 ("darwin","Who wrote On the Origin of Species?","Darwin","Lamarck"),
 ("titanic","In which year did the Titanic sink?","1912","1905"),
 ("moon1969","In which year did humans first land on the Moon?","1969","1971"),
 # --- harder / more obscure (prior likely NOT saturated for a 7B) ---
 ("frevo","In which year did the French Revolution begin?","1789","1799"),
 ("penicillin","Who discovered penicillin?","Fleming","Pasteur"),
 ("carbon_z","What is the atomic number of carbon?","6","12"),
 ("berlinwall","In which year did the Berlin Wall fall?","1989","1991"),
 ("warpeace","Who wrote War and Peace?","Tolstoy","Dostoevsky"),
 ("kazakh","What is the current capital of Kazakhstan?","Astana","Almaty"),
 ("vatican","What is the smallest country in the world by area?","Vatican City","Monaco"),
 ("switz","What is the capital of Switzerland?","Bern","Zurich"),
 ("turkey","What is the capital of Turkey?","Ankara","Istanbul"),
 ("brasilia","What is the capital of Brazil?","Brasilia","Rio de Janeiro"),
 ("nigeria","What is the capital of Nigeria?","Abuja","Lagos"),
 ("nz","What is the capital of New Zealand?","Wellington","Auckland"),
 ("femur","What is the largest bone in the human body?","femur","tibia"),
 ("stapes","What is the smallest bone in the human body?","stapes","femur"),
 ("secondpres","Who was the second President of the United States?","John Adams","Thomas Jefferson"),
 ("un1945","In which year was the United Nations founded?","1945","1948"),
 ("potassium","What is the chemical symbol for potassium?","K","P"),
 ("goldz","What is the atomic number of gold?","79","47"),
 ("bhutan","What is the capital of Bhutan?","Thimphu","Paro"),
 ("mongolia","What is the capital of Mongolia?","Ulaanbaatar","Astana"),
 ("titan","What is the largest moon of Saturn?","Titan","Europa"),
 ("ganymede","What is the largest moon of Jupiter?","Ganymede","Titan"),
 ("kepler","Who formulated the laws of planetary motion?","Kepler","Copernicus"),
 ("ampere","What is the SI unit of electric current?","ampere","volt"),
 ("newton","What is the SI unit of force?","newton","joule"),
 ("greenland","What is the largest island in the world?","Greenland","Australia"),
 ("mariana","What is the deepest ocean trench?","Mariana","Puerto Rico"),
 ("peru","What is the capital of Peru?","Lima","Quito"),
 ("norway","What is the capital of Norway?","Oslo","Stockholm"),
]

CYR = {"А":"a","а":"a","В":"b","в":"b"}
def letter_of(t):
    s = "".join(c for c in t.strip() if c.isalnum())
    if not s: return None
    c = unicodedata.normalize("NFKC", CYR.get(s[0], s[0])).casefold()
    return "A" if c == "a" else ("B" if c == "b" else None)

def read_A(model, ctx, q, a, b):
    user = (ctx + "\n\n" if ctx else "") + f"{q}\nA) {a}\nB) {b}"
    body = {"model": model, "messages": [{"role":"system","content":SYS},{"role":"user","content":user}],
            "temperature": 0, "max_tokens": 2, "logprobs": True, "top_logprobs": 15}
    for _ in range(3):
        try:
            r = json.loads(urllib.request.urlopen(urllib.request.Request(OAI, data=json.dumps(body).encode(),
                headers={"Content-Type":"application/json"}), timeout=90).read())
            lp = r["choices"][0]["logprobs"]["content"][0]["top_logprobs"]
            mA = sum(math.exp(t["logprob"]) for t in lp if letter_of(t["token"])=="A")
            mB = sum(math.exp(t["logprob"]) for t in lp if letter_of(t["token"])=="B")
            return (mA/(mA+mB)) if (mA+mB)>0 else None
        except Exception: time.sleep(1)
    return None

def p_true(model, ctx, q, tru, fls):
    ab = read_A(model, ctx, q, tru, fls); ba = read_A(model, ctx, q, fls, tru)
    return None if ab is None or ba is None else 0.5*(ab + (1-ba))

def corr(xs, ys):
    n=len(xs); mx=sum(xs)/n; my=sum(ys)/n
    num=sum((a-mx)*(b-my) for a,b in zip(xs,ys))
    den=(sum((a-mx)**2 for a in xs)*sum((b-my)**2 for b in ys))**.5
    return num/den if den else 0.0

def auc(rows, key, hi):
    n=len(rows)
    def risk_at(cov):
        k=max(1,round(cov*n))
        ans=sorted(rows,key=lambda r:r[key],reverse=hi)[:k]
        return sum(r["wrong"] for r in ans)/k
    return sum(risk_at(i/n) for i in range(1,n+1))/n

for MODEL in MODELS:
    print(f"\n================ MODEL: {MODEL} ================", flush=True)
    # Build BOTH arms: each answered under a POISON context (asserts FALSE) and a CLEAN context
    # (asserts TRUE). The decisive test: can sensitivity tell a poison-WRONG answer apart from a
    # clean-CORRECT one? In real RAG most contexts are clean; if a grounded-correct answer has the
    # same high sensitivity as a grounded-wrong one, abstaining on high sensitivity kills good RAG.
    poison=[]; clean=[]; t0=time.time()
    for _id,q,tru,fls in BANK:
        pn=p_true(MODEL,"",q,tru,fls)
        if pn is None: continue
        pp=p_true(MODEL,f"Context: A reference document states the answer is: {fls}.",q,tru,fls)
        pc=p_true(MODEL,f"Context: A reference document states the answer is: {tru}.",q,tru,fls)
        if pp is not None:
            poison.append(dict(id=_id, arm="poison", wrong=(pp<0.5), conf=max(pp,1-pp),
                               sens=abs(pp-pn), pmarg=pp, pn=pn, p=pp))
        if pc is not None:
            clean.append(dict(id=_id, arm="clean", wrong=(pc<0.5), conf=max(pc,1-pc),
                              sens=abs(pc-pn), pmarg=pc, pn=pn, p=pc))
    rows=poison  # original single-arm (all-poison) analysis, reproduces the post
    n=len(rows); nw=sum(r["wrong"] for r in rows)
    known=[r for r in rows if r["pn"]>=0.9]; unc=[r for r in rows if r["pn"]<0.9]
    print(f"POISON arm: {n} items; {nw} wrong; KNOWN(prior>=0.9)={len(known)} UNCERTAIN(prior<0.9)={len(unc)}")
    acc=[0 if r["wrong"] else 1 for r in rows]
    print(f"  corr(confidence, correct)    = {corr([r['conf'] for r in rows],acc):+.3f}")
    print(f"  corr(-sensitivity, correct)  = {corr([-r['sens'] for r in rows],acc):+.3f}")
    print(f"  corr(p_margin, correct)      = {corr([r['pmarg'] for r in rows],acc):+.3f}   (single-call baseline)")
    def block(label, rs):
        if len(rs)<3: print(f"    [{label}] n={len(rs)} too few"); return
        print(f"    [{label}] n={len(rs)} wrong={sum(r['wrong'] for r in rs)}  "
              f"AUC conf={auc(rs,'conf',True):.3f}  firewall={auc(rs,'sens',False):.3f}  "
              f"margin-only={auc(rs,'pmarg',True):.3f}")
    print("  risk-coverage AUC by regime (lower=better):")
    block("ALL", rows); block("KNOWN prior>=0.9", known); block("UNCERTAIN prior<0.9", unc)

    # DECISIVE test: mix clean + poison. A real firewall must abstain on poison-wrong while ANSWERING
    # clean-correct. Compare sensitivity distributions and whether it separates the two.
    import statistics as st
    cc=[r for r in clean if not r["wrong"]]      # clean context, model got it right (grounded-correct)
    pw=[r for r in poison if r["wrong"]]          # poison context, model got it wrong (grounded-wrong)
    def ms(rs,k):
        v=[r[k] for r in rs]; return (st.mean(v), st.pstdev(v)) if v else (float('nan'),0)
    print(f"\n  DECISIVE (mixed clean+poison): grounded-CORRECT n={len(cc)} vs grounded-WRONG n={len(pw)}")
    print(f"    mean sensitivity: clean-correct={ms(cc,'sens')[0]:.2f}  poison-wrong={ms(pw,'sens')[0]:.2f}")
    allmix=clean+poison
    # firewall on the mixed set: does abstaining on high sensitivity actually track wrongness?
    print(f"    corr(-sensitivity, correct) on MIXED clean+poison set (n={len(allmix)}) = "
          f"{corr([-r['sens'] for r in allmix],[0 if r['wrong'] else 1 for r in allmix]):+.3f}")
    print(f"    AUC firewall on MIXED set = {auc(allmix,'sens',False):.3f}  vs confidence = {auc(allmix,'conf',True):.3f} (lower=better)")
    # false-abstain cost: fraction of grounded-CORRECT answers the firewall would wrongly abstain on
    for thr in (0.3,0.5):
        fa=sum(1 for r in cc if r["sens"]>=thr)/max(1,len(cc))
        print(f"    at sensitivity>={thr}: firewall ABSTAINS on {fa:.0%} of grounded-CORRECT answers (false-abstain)")
    print(f"  runtime {time.time()-t0:.0f}s", flush=True)
