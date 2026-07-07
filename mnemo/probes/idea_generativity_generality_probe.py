"""
idea_generativity_generality_probe.py  --  does an idea's GENERALITY predict its generativity? MIT.

A public receipt for a two-part empirical result (Agora frontier program, 2026-07-07), reached after
refuting several tempting-but-wrong hypotheses. Two questions with DIFFERENT answers:

  (1) Does content-generality shape the SCOPE of generativity?  -> YES, real, replicated.
  (2) Does content-generality make generativity PREDICTABLE (intrinsic, low path-dependence)?  -> NO, null.

WHAT "generativity" means here: NOT citation count. It is how a work SPAWNS downstream build-on across the
research landscape -- operationalized as the ENTROPY of the subfields of the works that cite it (how broadly,
across distinct fields, later work builds on it), which is volume-robust (unlike raw citation count).

RESULT (1) -- SCOPE, real & replicated:
  content-generality (an LLM rates 1-6 how broadly a paper's core contribution could apply, from the ABSTRACT
  ONLY, blind to citations) predicts downstream cross-field spread, controlling for citation volume:
    AI field (n=60):        partial Spearman +0.536, 95% CI [+0.33, +0.70]
    Medicine (replication): partial Spearman +0.287, 95% CI [+0.04, +0.50]
  Both exclude 0. NON-CIRCULAR: the content signal (abstract) and the outcome signal (citer field-distribution)
  come from INDEPENDENT sources. General ideas get built on across MORE diverse fields (need-driven breadth).

RESULT (2) -- PREDICTABILITY, null:
  A "parallel-worlds" test (Salganik-Dodds-Watts design applied to ideas -- re-run an artificial idea-market
  with the SAME ideas but RANDOMIZED early visibility; across-world variance of an idea's generativity = its
  path-dependence). With build-on decisions made by a real LLM agent (not a set weight -> non-circular),
  generality did NOT significantly predict lower across-world variance (Spearman -0.16, 95% CI crosses 0,
  underpowered). So generativity stays PATH-DOMINATED even for general ideas -- consistent with
  Salganik-Dodds-Watts (Science 2006): success is largely path-dependent.

HONEST TRAIL (why to trust the +0.54, and the wrong turns that were caught):
  - artifact-vs-claim as the moderator: REFUTED across 3 methods (it was a red herring for generality).
  - a pure simulation with build-on weight == the generality measure: CIRCULAR (a stress-test killed it).
  - OpenAlex own-subfield-breadth -> spread of +0.56: a `per-page=1` group_by BUG + reference-informed
    subfield tagging leak; it did NOT survive a reference-blind check.
  - a crude keyword abstract-generality: +0.11 (too weak a measure). Only a real LLM rating (with a LARGE
    max_tokens budget -- thinking models truncate to empty otherwise) revealed the replicated signal.

CAVEATS kept on the label: n=60 per field, one era (2015-2017), single LLM rater; "generality" as an LLM
judges it may correlate with clarity/quality; the path-dependence test is underpowered (needs more worlds).

Run (documents the result, no keys):   python idea_generativity_generality_probe.py
Reproduce live (needs OpenAlex[free] + an OpenAI-compatible LLM via LLM_BASE_URL / LLM_API_KEY / LLM_MODEL):
                                        python idea_generativity_generality_probe.py --run --field C154945302
Prior art credited: Salganik-Dodds-Watts 2006; Wang-Song-Barabasi 2013; Uzzi et al 2013; Wu-Wang-Evans 2019.
"""
import os, sys, json, math, re, argparse

REPORTED = {
    "AI (C154945302)":       {"n": 60, "partial_rho": 0.536, "ci": (0.326, 0.695)},
    "Medicine (C71924100)":  {"n": 60, "partial_rho": 0.287, "ci": (0.036, 0.504)},
    "parallel-worlds path-dependence (real-LLM-agent)": {"n": 14, "partial_rho": -0.156, "ci": (-0.634, 0.408)},
}


def _spear(a, b):
    n = len(a)
    def rk(v):
        o = sorted(range(n), key=lambda i: v[i]); r = [0] * n
        for p, i in enumerate(o): r[i] = p
        return r
    ra, rb = rk(a), rk(b); ma = sum(ra) / n; mb = sum(rb) / n
    cov = sum((ra[i] - ma) * (rb[i] - mb) for i in range(n))
    sa = math.sqrt(sum((x - ma) ** 2 for x in ra)); sb = math.sqrt(sum((x - mb) ** 2 for x in rb))
    return cov / (sa * sb) if sa * sb > 0 else 0.0


def report():
    print("=== idea generativity vs generality -- reported result (two questions, two answers) ===\n")
    print("(1) SCOPE: content-generality -> cross-field generativity spread (volume-controlled), REPLICATED:")
    for k, v in REPORTED.items():
        if "path" in k: continue
        print(f"    {k:26} n={v['n']}  partial rho={v['partial_rho']:+.3f}  95% CI [{v['ci'][0]:+.2f},{v['ci'][1]:+.2f}]  -> excludes 0")
    print("\n(2) PREDICTABILITY: generality -> LOW across-world variance (path-dependence), NULL:")
    v = REPORTED["parallel-worlds path-dependence (real-LLM-agent)"]
    print(f"    real-LLM-agent parallel worlds  n={v['n']}  rho={v['partial_rho']:+.3f}  95% CI [{v['ci'][0]:+.2f},{v['ci'][1]:+.2f}]  -> CROSSES 0")
    print("\nHEADLINE: content-generality determines the cross-field SCOPE of generativity (real), but NOT its")
    print("predictability -- generativity stays path-dominated even for general ideas (Salganik-consistent).")
    print("Run with --run to reproduce the SCOPE pipeline live (needs OpenAlex + an OpenAI-compatible LLM).")


def run_live(field, n_target=60):
    import urllib.request
    from concurrent.futures import ThreadPoolExecutor
    BASE = os.environ.get("LLM_BASE_URL"); KEY = os.environ.get("LLM_API_KEY"); MODEL = os.environ.get("LLM_MODEL", "kimi-k2.7-code")
    if not (BASE and KEY):
        print("Set LLM_BASE_URL / LLM_API_KEY / LLM_MODEL to reproduce live."); return
    def get(u): return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'agora'}), timeout=45))
    def rate(a):
        body = json.dumps({"model": MODEL, "temperature": 0.0, "max_tokens": 8000, "messages": [{"role": "user",
                "content": "Rate how broadly this paper's core contribution could apply across research subfields. "
                "End with a line exactly 'ANSWER: N', N=1(narrow)-6(broad). Content only, ignore citations.\n\nAbstract: " + a}]}).encode()
        try:
            c = json.load(urllib.request.urlopen(urllib.request.Request(BASE.rstrip('/') + "/chat/completions", data=body,
                headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"}), timeout=120))["choices"][0]["message"]["content"]
            m = re.search(r'ANSWER:\s*([1-6])', c); return int(m.group(1)) if m else None
        except Exception:
            return None
    def entropy(cs):
        tot = sum(cs); return -sum((x / tot) * math.log(x / tot) for x in cs if x > 0) if tot > 0 else 0.0
    def abstract(w):
        inv = w.get("abstract_inverted_index");
        if not inv: return ""
        pos = {}
        for tok, idxs in inv.items():
            for i in idxs: pos[i] = tok
        return " ".join(pos[i] for i in sorted(pos))
    url = (f"https://api.openalex.org/works?filter=concepts.id:{field},from_publication_date:2015-01-01,"
           f"to_publication_date:2017-12-31,type:article,has_abstract:true,cited_by_count:>40&sample=200&seed=11"
           f"&select=id,cited_by_count,abstract_inverted_index&per-page=200&mailto=research@agora.dev")
    works = get(url + "&page=1").get("results", [])
    data = []
    for w in works:
        a = abstract(w)
        if len(a) < 80: continue
        wid = w["id"].split("/")[-1]
        try:
            g = get(f"https://api.openalex.org/works?filter=cites:{wid}&group_by=primary_topic.subfield.id&mailto=research@agora.dev")
            grp = [x["count"] for x in g.get("group_by", []) if x.get("count")]
        except Exception:
            continue
        if not grp: continue
        data.append({"a": a[:600], "H": entropy(grp), "logc": math.log(w.get("cited_by_count", 1))})
        if len(data) >= n_target: break
    with ThreadPoolExecutor(max_workers=12) as ex:
        sc = list(ex.map(rate, [d["a"] for d in data]))
    rows = [(data[i], sc[i]) for i in range(len(data)) if sc[i] is not None]; n = len(rows)
    LG = [r[1] for r in rows]; H = [r[0]["H"] for r in rows]; CC = [r[0]["logc"] for r in rows]
    # partial: residualize H on log-count (rank), then correlate with generality
    def rk(v):
        o = sorted(range(n), key=lambda i: v[i]); r = [0] * n
        for p, i in enumerate(o): r[i] = p
        return r
    rH, rC = rk(H), rk(CC); mC = sum(rC) / n; mH = sum(rH) / n
    bb = sum((rC[i] - mC) * (rH[i] - mH) for i in range(n)) / (sum((rC[i] - mC) ** 2 for i in range(n)) or 1)
    res = [rH[i] - bb * (rC[i] - mC) for i in range(n)]
    rp = _spear(LG, res)
    z = 0.5 * math.log((1 + rp) / (1 - rp)); se = 1 / math.sqrt(n - 3)
    print(f"LIVE field={field}: n={n}  partial Spearman(LLM-generality -> cross-field spread | volume) = {rp:+.3f}")
    print(f"  ~95% CI [{math.tanh(z - 1.96 * se):+.3f}, {math.tanh(z + 1.96 * se):+.3f}]")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true"); ap.add_argument("--field", default="C154945302")
    a = ap.parse_args()
    if a.run:
        run_live(a.field)
    else:
        report()


if __name__ == "__main__":
    main()
