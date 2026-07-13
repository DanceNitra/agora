"""
    PUBLISH GATE: run /stress-claim (argument) + /verify-claims (facts) on the source BEFORE rendering.
The Crucible — render the public replication ledger.

Reads server/.replications.json (verdict ledger) + server/.lab.json (experiment scripts/output)
and a hand-curated display layer (tools/crucible_curation.json), then renders
public/crucible/index.html (human ledger) + public/crucible/crucible.json (machine dataset).
Curation overrides raw ledger text so the public page is 100% quality; the ledger stays the
source of truth. Re-run after any new replication (commit lab scripts so code links resolve):
    python -X utf8 tools/render_crucible.py
"""
from __future__ import annotations

import html
import json
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPS = ROOT / "server" / ".replications.json"
LAB = ROOT / "server" / ".lab.json"
CURATION = ROOT / "tools" / "crucible_curation.json"
OUT_DIR = ROOT / "public" / "crucible"
SITE = "https://dancenitra.github.io/agora"
REPO = "https://github.com/DanceNitra/agora"


def load(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return [] if p in (REPS, LAB) else {}


def lab_index(lab):
    return {e["id"]: e for e in lab if e.get("id")}


def script_link(lab_rec):
    if not lab_rec:
        return None
    sp = (lab_rec.get("script") or "").replace("\\", "/")
    if "agora_output/lab/" not in sp:
        return None
    rel = "agora_output/lab/" + sp.split("agora_output/lab/")[-1]
    return f"{REPO}/blob/main/{rel}" if (ROOT / rel).exists() else None


# Durable lab_id -> PUBLIC probe map (tracked here, not in gitignored .replications.json, so the receipt links
# survive re-renders regardless of the ledger file). Only add a mapping you are confident about -- a wrong
# receipt is worse than none. Extend as more probes are confirmed (agentpoison, eviction, separation-law, ...).
_PROBE_BY_LAB = {
    "39737a": "mnemo/probes/nudge_pubbias_artifact.py",              # food-nudges 2.5x
    "502d6c": "mnemo/probes/good_to_great_null.py",                  # good-to-great
    "bf7bb9": "mnemo/probes/llm_judge_length_null.py",               # llm-as-judge length
    "12b630": "mnemo/probes/founder_survivorship_null.py",           # founder-led 3.1x
    "14c41f": "mnemo/probes/arena_style_only.py",                    # chatbot arena style
    "ragdead": "mnemo/probes/ragdead/exp_ragdead_A.py",             # RAG-is-dead / CAG
    "exp_supersession_replication": "mnemo/probes/supersession_replication.py",  # cosine supersession
    "rev93": "mnemo/probes/reversibility_predictability_probe.py",  # tool-reversibility signature-decidability
}


def entry_code(r, labs):
    """Resolve a runnable-receipt URL for a ledger entry: an explicit repo-relative `code` on the entry, else
    the tracked lab_id->probe map, else the lab-script link. lab scripts live in gitignored agora_output/lab/,
    so most entries only get a resolvable receipt once a public probe is wired -- return a URL only if the file
    exists in the repo."""
    p = (r.get("code") or _PROBE_BY_LAB.get(r.get("lab_id", ""), "") or "").strip().replace("\\", "/")
    if p and (ROOT / p).exists():
        return f"{REPO}/blob/main/{p}"
    return script_link(labs.get(r.get("lab_id")))


def e(s):
    return html.escape(str(s or ""))


# --- ledger de-duplication guard (anti-inflation) ---------------------------------------------------
# The pipeline re-runs the same textbook claim over time (k-clique percolation, epidemic-threshold,
# LinUCB regret, ...), which silently inflates the public REPRODUCED count. This guard collapses
# near-duplicate entries (same verdict + high content-word overlap) to ONE canonical entry for the
# PUBLIC render only -- the source ledger (.replications.json) keeps every run, so nothing is lost and
# the dedup is fully reversible. The threshold is deliberately conservative (a wrongly-dropped real
# replication is worse than a surviving duplicate): 0.50 sits well above the point where genuinely
# distinct claims start merging (the two distinct SGD results merge only below ~0.45).
_DEDUP_THR = 0.50
_DD_STOP = set("the a an of in on to for and or is are be as at by with from into that this it its "
               "which whose than then so not no does do".split())
# textbook families to WARN about (same verdict, >=3 survivors) so paraphrases the fingerprint misses
# still get a human's eye rather than quietly padding the count.
_DD_FAMILIES = ["k-clique", "clique percolation", "epidemic threshold", "finite-size", "branching",
                "linucb", "regret bound", "percolation threshold", "universality class",
                "power law", "power-law", "scale-free", "preferential attach"]


def _dd_tokens(claim):
    s = re.sub(r"\([^)]*\)", " ", (claim or "").lower())   # drop parentheticals (citations/years)
    s = re.sub(r"[^a-z\s]", " ", s)                        # drop digits/punctuation/formula symbols
    return {t for t in s.split() if len(t) > 2 and t not in _DD_STOP}


def _dedup_ledger(reps):
    """Collapse same-verdict near-duplicate entries to one canonical (prefer a real hex lab-hash, then
    the longest note). Returns the deduped list; prints what it collapsed + family warnings."""
    def canon_score(r):
        lab = r.get("lab_id", "") or ""
        return (bool(re.fullmatch(r"[0-9a-f]{6,}", lab)), len(r.get("note", "") or ""))

    kept, sigs, clusters = [], [], []
    for r in reps:
        oc, tk = r.get("outcome", ""), _dd_tokens(r.get("claim", ""))
        hit = next((i for i, (koc, ktk) in enumerate(sigs)
                    if koc == oc and tk and ktk
                    and len(tk & ktk) / len(tk | ktk) >= _DEDUP_THR), None)
        if hit is None:
            kept.append(r); sigs.append((oc, tk)); clusters.append([r])
        else:
            clusters[hit].append(r)
            if canon_score(r) > canon_score(kept[hit]):
                kept[hit] = r; sigs[hit] = (oc, tk)

    for c in (c for c in clusters if len(c) > 1):
        print(f"  [dedup] collapsed x{len(c)} [{c[0].get('outcome')}]: {c[0].get('claim','')[:64]}")
    # warn on textbook families the fingerprint may have under-merged (paraphrased re-runs)
    for fam in _DD_FAMILIES:
        for oc in ("REPRODUCED", "FAILED", "NOT_COMPUTABLE"):
            n = sum(1 for r in kept if fam in (r.get("claim", "").lower()) and r.get("outcome") == oc)
            if n >= 3:
                print(f"  [dedup][WARN] {n}x '{fam}' survive as {oc} -- likely paraphrased re-runs, review by hand")
    if len(kept) < len(reps):
        print(f"  [dedup] {len(reps)} ledger entries -> {len(kept)} after de-duplication")
    return kept


def render():
    reps = _dedup_ledger(load(REPS))
    labs = lab_index(load(LAB))
    cur = load(CURATION)
    by = {o: sum(1 for r in reps if r.get("outcome") == o)
          for o in ("REPRODUCED", "FAILED", "NOT_COMPUTABLE")}
    tested = [r for r in reps if r.get("outcome") in ("REPRODUCED", "FAILED")][::-1]
    passed = [r for r in reps if r.get("outcome") == "NOT_COMPUTABLE"][::-1]

    # ---- machine-readable dataset ----
    dataset = {
        "name": "The Crucible — machine replication ledger",
        "description": "Scientific and technical claims rebuilt as minimal computational models and "
                       "tested. REPRODUCED = the mechanism holds in a minimal model; FAILED = it does "
                       "not; NOT_COMPUTABLE = no simulable core (an honest pass).",
        "generated": time.strftime("%Y-%m-%d"),
        "counts": by,
        "entries": [{
            "claim": r.get("claim", ""), "source": r.get("source", ""),
            "verdict": r.get("outcome", ""), "note": r.get("note", ""),
            "lab_id": r.get("lab_id", ""), "code": entry_code(r, labs) or "",
            "date": time.strftime("%Y-%m-%d", time.localtime(r.get("ts", 0))) if r.get("ts") else "",
        } for r in reps[::-1]],
    }

    def meta(r):
        c = cur.get(r.get("lab_id", ""), {})
        return c, entry_code(r, labs), \
            (time.strftime("%Y-%m-%d", time.localtime(r.get("ts", 0))) if r.get("ts") else "")

    # ---- featured failure (case study) ----
    featured_html = ""
    feat = next((r for r in tested if cur.get(r.get("lab_id", ""), {}).get("featured")), None)
    if feat:
        c, code, date = meta(feat)
        codeline = (f'<a class="codelink" href="{code}" target="_blank" rel="noopener">Read the runnable model &rarr;</a>'
                    if code else "")
        dd = c.get("deep_dive")
        if dd:
            codeline = (f'<a class="codelink" href="{dd}">The deep dive, with charts &rarr;</a>  '
                        + codeline)
        featured_html = f"""
  <section class="feature" data-reveal>
    <div class="wrap">
      <div class="fhead"><span class="fverdict">Failed replication</span>
        <span class="fmeta">{e(c.get('field'))} &middot; {e(c.get('year'))}</span></div>
      <h2 class="ftitle">{e(c.get('title'))}</h2>
      <div class="fgrid">
        <div class="fcol"><div class="flab">The canon</div><p>{e(c.get('canon'))}</p></div>
        <div class="fcol"><div class="flab">What we rebuilt</div><p>{e(c.get('rebuilt'))}</p></div>
      </div>
      <div class="fverdict-block"><div class="flab">The verdict</div><p>{e(c.get('verdict'))}</p></div>
      <div class="ffoot">{codeline}<span class="flabid">lab {e(feat.get('lab_id'))} &middot; {date}</span></div>
    </div>
  </section>"""

    # ---- verdict cards (exclude the featured one from the grid) ----
    cards = []
    for r in tested:
        if feat is not None and r is feat:
            continue
        c, code, date = meta(r)
        outcome = r["outcome"]
        klass = "ok" if outcome == "REPRODUCED" else "fail"
        title = c.get("title") or r.get("claim", "")[:90]
        result = c.get("result") or r.get("note", "")
        field = c.get("field") or ""
        year = c.get("year") or e(r.get("source", ""))[:46]
        codeline = (f'<a class="code" href="{code}" target="_blank" rel="noopener">runnable model &rarr;</a>'
                    if code else "")
        cards.append(f"""
      <article class="card {klass}" data-v="{outcome}" data-reveal>
        <div class="crail"></div>
        <div class="cbody">
          <div class="chead"><span class="cv">{'REPRODUCED' if outcome=='REPRODUCED' else 'FAILED'}</span>
            <span class="cfield">{e(field)}</span></div>
          <h3>{e(title)}</h3>
          <p class="cresult">{e(result)}</p>
          <div class="cfoot"><span class="cyear">{e(year)}</span>{codeline}</div>
        </div>
      </article>""")

    # honest passes: show ONLY curated entries (keeps the public page clean; the full raw
    # NOT_COMPUTABLE set stays in crucible.json for transparency)
    pass_curation = cur.get("_passes", [])
    shown_passes = []
    for pc in pass_curation:
        match = pc.get("match", "")
        if any((r.get("claim", "").startswith(match)) for r in passed):
            shown_passes.append(pc)
    passes = "".join(
        f'<li data-reveal><span class="pclaim">{e(pc.get("claim"))}</span>'
        f'<span class="preason">{e(pc.get("reason"))}</span></li>'
        for pc in shown_passes)
    nc_shown = len(shown_passes)

    page = TEMPLATE.format(
        site=SITE, repo=REPO, R=by["REPRODUCED"], F=by["FAILED"], NC=nc_shown,
        tested=len(tested), updated=time.strftime("%Y-%m-%d"),
        featured=featured_html, cards="".join(cards), passes=passes)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "index.html").write_text(page, encoding="utf-8")
    (OUT_DIR / "crucible.json").write_text(json.dumps(dataset, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"rendered {OUT_DIR/'index.html'} — {by['REPRODUCED']}R/{by['FAILED']}F/{by['NOT_COMPUTABLE']}NC, "
          f"{len(tested)} tested cards, featured={'yes' if feat else 'no'}")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<script>document.documentElement.className+=' js';</script>
<meta charset="utf-8">
<link rel="icon" type="image/svg+xml" href="https://dancenitra.github.io/agora/favicon.svg">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The Crucible &middot; a machine that rebuilds claims in code &middot; Agora</title>
<meta name="description" content="A public ledger of scientific and technical claims rebuilt as minimal computational models and tested in code: {R} reproduced, {F} failed, {NC} honest passes. Every verdict ships runnable code and a measured number.">
<link rel="canonical" href="{site}/public/crucible/">
<script type="application/ld+json">{{"@context":"https://schema.org","@graph":[{{"@type":"Dataset","name":"The Crucible — AI-claim replication ledger","description":"A public, machine-readable ledger of scientific and technical claims rebuilt as minimal computational models and tested in code ({R} reproduced, {F} failed, {NC} not-computable). Every verdict ships runnable code and a measured number.","url":"{site}/public/crucible/","license":"https://opensource.org/licenses/MIT","creator":{{"@type":"Organization","name":"Agora","url":"{site}/"}},"variableMeasured":["reproduced","failed","not-computable"]}},{{"@type":"WebSite","name":"Agora","url":"{site}/","publisher":{{"@type":"Organization","name":"Agora"}}}}]}}</script>
<meta property="og:type" content="website">
<meta property="og:title" content="The Crucible — claims, rebuilt in code and tested">
<meta property="og:description" content="A machine rebuilds scientific claims as minimal models and publishes the verdict — failures included. Every verdict ships runnable code.">
<meta property="og:url" content="{site}/public/crucible/">
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;0,6..72,700;1,6..72,400;1,6..72,500&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root{{
    --paper:#faf7f0;--paper2:#f2eee4;--ink:#17150f;--soft:#55514733;--text:#4d493f;--faint:#938d7f;
    --line:#e3ddcf;--line2:#d6cfbd;--acc:#0c7a55;--acc2:#0a8f68;--acc-soft:#e1f1ea;
    --bad:#b1361f;--bad-soft:#f8e6e0;--gold:#9a7b1e;
    --serif:"Newsreader",Georgia,"Times New Roman",serif;
    --mono:"JetBrains Mono",ui-monospace,Menlo,Consolas,monospace;
  }}
  *{{box-sizing:border-box;margin:0}}
  html{{scroll-behavior:smooth;-webkit-text-size-adjust:100%}}
  body{{background:var(--paper);color:var(--ink);font-family:var(--serif);
    -webkit-font-smoothing:antialiased;font-optical-sizing:auto;text-rendering:optimizeLegibility;
    background-image:radial-gradient(circle at 12% -8%, #ffffff 0%, transparent 42%),
      radial-gradient(circle at 92% 4%, #fffdf6 0%, transparent 38%);}}
  ::selection{{background:var(--acc-soft)}}
  a{{color:inherit;text-decoration:none}}
  .wrap{{max-width:1120px;margin:0 auto;padding:0 30px}}
  /* nav */
  .nav{{position:sticky;top:0;z-index:20;background:rgba(250,247,240,.82);backdrop-filter:saturate(150%) blur(10px);
    border-bottom:1px solid var(--line)}}
  .nav .wrap{{display:flex;justify-content:space-between;align-items:center;padding:16px 30px;
    font-family:var(--mono);font-size:12.5px;letter-spacing:.04em}}
  .brand{{display:flex;align-items:center;gap:9px;font-weight:600;color:var(--ink)}}
  .brand .m{{width:17px;height:17px;border-radius:5px;background:conic-gradient(from 210deg,var(--acc2),transparent 62%);position:relative}}
  .brand .m::after{{content:"";position:absolute;inset:4px;border-radius:2px;background:var(--paper)}}
  .nav a.lnk{{color:var(--faint)}} .nav a.lnk:hover{{color:var(--acc)}}
  .navr{{display:flex;gap:20px;align-items:center}}
  /* masthead */
  .mast{{padding:74px 0 36px}}
  .kick{{font-family:var(--mono);font-size:12px;letter-spacing:.32em;text-transform:uppercase;color:var(--acc);
    margin-bottom:26px;display:flex;align-items:center;gap:14px}}
  .kick::before{{content:"";width:30px;height:1px;background:var(--acc)}}
  .mast h1{{font-weight:500;font-size:clamp(44px,8vw,86px);line-height:1.0;letter-spacing:-.03em;max-width:15ch}}
  .mast h1 em{{font-style:italic;color:var(--acc)}}
  .lede{{margin-top:26px;max-width:62ch;font-size:21px;line-height:1.62;color:var(--text)}}
  .lede b{{color:var(--ink);font-weight:600}}
  /* tally */
  .tally{{display:flex;gap:0;margin-top:46px;border:1px solid var(--line2);border-radius:16px;overflow:hidden;
    max-width:760px;background:#fff}}
  .tally .t{{flex:1;padding:22px 24px;border-right:1px solid var(--line)}}
  .tally .t:last-child{{border-right:0}}
  .tally .num{{font-family:var(--mono);font-weight:600;font-size:34px;line-height:1;letter-spacing:-.02em}}
  .tally .lbl{{margin-top:9px;font-family:var(--mono);font-size:11.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--faint)}}
  .tally .ok .num{{color:var(--acc)}}
  .tally .fail{{background:linear-gradient(180deg,#fff,var(--bad-soft))}}
  .tally .fail .num{{color:var(--bad)}}
  .tally .fail .lbl{{color:var(--bad)}}
  .dataset{{margin-top:20px;font-family:var(--mono);font-size:13px;color:var(--faint)}}
  .dataset a{{color:var(--acc);border-bottom:1px solid var(--acc-soft);padding-bottom:1px}}
  .dataset a:hover{{border-color:var(--acc)}}
  .loadline{{display:inline-block;margin-top:8px}}
  .loadline code{{font-family:var(--mono);font-size:12px;color:var(--text);background:var(--paper2);
    border:1px solid var(--line);border-radius:5px;padding:3px 8px}}
  /* feature / case study */
  .feature{{margin:60px 0 10px}}
  .feature .wrap{{background:#1a1813;color:#f3efe4;border-radius:24px;padding:54px 56px;position:relative;overflow:hidden;
    box-shadow:0 30px 60px -34px rgba(26,24,19,.55)}}
  .feature .wrap::before{{content:"";position:absolute;inset:0;background:
    radial-gradient(circle at 88% 8%, rgba(177,54,31,.30), transparent 45%);pointer-events:none}}
  .fhead{{display:flex;align-items:center;gap:16px;flex-wrap:wrap;font-family:var(--mono);font-size:12px;letter-spacing:.08em}}
  .fverdict{{background:var(--bad);color:#fff;padding:6px 13px;border-radius:7px;text-transform:uppercase;letter-spacing:.12em;font-weight:600}}
  .fmeta{{color:#b8b0a0}}
  .ftitle{{font-weight:500;font-size:clamp(30px,4.6vw,52px);line-height:1.06;letter-spacing:-.022em;margin:22px 0 30px;max-width:20ch}}
  .ftitle, .feature em{{font-style:normal}}
  .fgrid{{display:grid;grid-template-columns:1fr 1fr;gap:34px;margin-bottom:30px}}
  .flab{{font-family:var(--mono);font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:#c9a23f;margin-bottom:11px}}
  .feature p{{font-size:17.5px;line-height:1.62;color:#ddd7c9}}
  .fverdict-block{{border-top:1px solid #322e25;padding-top:26px}}
  .fverdict-block p{{color:#f1ece0;font-size:18.5px;line-height:1.62;max-width:88ch}}
  .ffoot{{margin-top:30px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;
    font-family:var(--mono);font-size:13px}}
  .codelink{{color:#7fd7b4;font-weight:500}} .codelink:hover{{color:#a6e6cd}}
  .flabid{{color:#857d6e}}
  /* ledger */
  .ledger{{padding:54px 0 20px}}
  .sechead{{display:flex;align-items:baseline;justify-content:space-between;flex-wrap:wrap;gap:14px;margin-bottom:8px}}
  .sechead h2{{font-weight:500;font-size:32px;letter-spacing:-.02em}}
  .sechead .sub{{font-family:var(--mono);font-size:12.5px;color:var(--faint)}}
  .filters{{display:flex;gap:9px;margin:24px 0 30px;flex-wrap:wrap}}
  .filters button{{font-family:var(--mono);font-size:12.5px;letter-spacing:.02em;border:1px solid var(--line2);
    background:#fff;color:var(--text);padding:8px 16px;border-radius:999px;cursor:pointer;transition:all .18s}}
  .filters button:hover{{border-color:var(--acc);color:var(--acc)}}
  .filters button.on{{background:var(--ink);color:var(--paper);border-color:var(--ink)}}
  .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:20px}}
  .card{{display:flex;background:#fff;border:1px solid var(--line);border-radius:16px;overflow:hidden;
    transition:transform .22s,box-shadow .22s,border-color .22s}}
  .card:hover{{transform:translateY(-3px);box-shadow:0 18px 34px -26px rgba(23,21,15,.4);border-color:var(--line2)}}
  .crail{{width:5px;flex:none}}
  .card.ok .crail{{background:linear-gradient(180deg,var(--acc2),var(--acc))}}
  .card.fail .crail{{background:linear-gradient(180deg,#c9492f,var(--bad))}}
  .cbody{{padding:26px 26px 20px;display:flex;flex-direction:column;flex:1}}
  .chead{{display:flex;align-items:center;justify-content:space-between;gap:10px;font-family:var(--mono);font-size:10.5px;letter-spacing:.1em;margin-bottom:14px}}
  .cv{{padding:4px 9px;border-radius:6px;font-weight:600;letter-spacing:.12em}}
  .card.ok .cv{{background:var(--acc-soft);color:var(--acc)}}
  .card.fail .cv{{background:var(--bad-soft);color:var(--bad)}}
  .cfield{{color:var(--faint);text-transform:uppercase}}
  .card h3{{font-weight:500;font-size:21px;line-height:1.24;letter-spacing:-.015em;margin-bottom:12px}}
  .cresult{{font-size:15.5px;line-height:1.58;color:var(--text);flex:1}}
  .cfoot{{margin-top:18px;padding-top:14px;border-top:1px solid var(--line);display:flex;justify-content:space-between;
    align-items:center;gap:10px;font-family:var(--mono);font-size:11.5px}}
  .cyear{{color:var(--faint)}}
  .code{{color:var(--acc);white-space:nowrap}} .code:hover{{text-decoration:underline}}
  /* passes */
  .passes{{padding:56px 0 24px}}
  .passes p.intro{{margin-top:8px;max-width:70ch;font-size:16.5px;line-height:1.6;color:var(--text)}}
  .plist{{list-style:none;margin:26px 0 0;border-top:1px solid var(--line)}}
  .plist li{{display:flex;justify-content:space-between;gap:30px;padding:16px 2px;border-bottom:1px solid var(--line);
    align-items:baseline}}
  .pclaim{{font-size:16px;line-height:1.5;color:var(--text)}}
  .preason{{font-family:var(--mono);font-size:11.5px;color:var(--faint);white-space:nowrap;text-align:right}}
  /* rules + submit */
  .rules{{padding:56px 0}}
  .rules .panel{{background:var(--paper2);border:1px solid var(--line2);border-radius:18px;padding:40px 44px;max-width:none}}
  .rules h2{{font-weight:500;font-size:28px;letter-spacing:-.018em;margin-bottom:18px}}
  .rlist{{display:grid;grid-template-columns:1fr 1fr;gap:26px 44px;margin-top:6px}}
  .rule .rn{{font-family:var(--mono);font-size:12px;color:var(--acc);letter-spacing:.1em}}
  .rule h3{{font-weight:600;font-size:17px;margin:8px 0 6px}}
  .rule p{{font-size:15.5px;line-height:1.58;color:var(--text)}}
  .submit{{padding:14px 0 80px}}
  .submit .panel{{border:1.5px dashed var(--acc);border-radius:18px;padding:38px 42px;display:flex;
    justify-content:space-between;align-items:center;gap:30px;flex-wrap:wrap;background:#fff}}
  .submit h2{{font-weight:500;font-size:26px;letter-spacing:-.015em;margin-bottom:8px}}
  .submit p{{font-size:16.5px;line-height:1.58;color:var(--text);max-width:60ch}}
  .btn{{font-family:var(--mono);font-size:13.5px;font-weight:600;background:var(--ink);color:var(--paper);
    padding:14px 22px;border-radius:11px;white-space:nowrap;transition:background .2s}}
  .btn:hover{{background:var(--acc)}}
  footer{{border-top:1px solid var(--line);padding:30px 0 60px}}
  footer .wrap{{display:flex;justify-content:space-between;flex-wrap:wrap;gap:12px;font-family:var(--mono);font-size:12.5px;color:var(--faint)}}
  footer a{{color:var(--faint)}} footer a:hover{{color:var(--acc)}}
  /* reveal — only hide when JS is on; content is fully visible without JS or before scroll */
  .js [data-reveal]{{opacity:0;transform:translateY(16px);transition:opacity .6s ease,transform .6s ease}}
  .js [data-reveal].in{{opacity:1;transform:none}}
  @media (prefers-reduced-motion:reduce){{.js [data-reveal]{{opacity:1;transform:none;transition:none}}}}
  @media (max-width:760px){{
    .feature .wrap{{padding:38px 26px}} .fgrid{{grid-template-columns:1fr;gap:24px}}
    .rlist{{grid-template-columns:1fr}} .tally{{flex-direction:row}}
    .tally .num{{font-size:26px}} .plist li{{flex-direction:column;gap:4px}}
    .preason{{text-align:left}}
  }}
</style>
</head>
<body>
<nav class="nav"><div class="wrap">
  <a class="brand" href="{site}/"><span class="m"></span>Agora</a>
  <div class="navr"><a class="lnk" href="{site}/posts/">Writing</a>
    <a class="lnk" href="{site}/public/ai-claims/">AI&nbsp;Claims</a>
    <a class="lnk" href="crucible.json">Dataset</a>
    <a class="lnk" href="https://huggingface.co/datasets/Danchi17/folklore-index" target="_blank" rel="noopener">Hugging&nbsp;Face</a></div>
</div></nav>

<header class="mast"><div class="wrap">
  <div class="kick">The Crucible</div>
  <h1>Claims, rebuilt in code <em>and tested.</em></h1>
  <p class="lede">A public ledger of scientific and technical claims rebuilt as <b>minimal
  computational models</b> and run. Three honest verdicts &mdash; <b>reproduced</b> when the
  mechanism holds in its smallest model, <b>failed</b> when it doesn&rsquo;t (science&rsquo;s
  rarest export, published here), and <b>not computable</b> when there&rsquo;s no simulable core.
  Every verdict ships a measured number and the code that produced it.</p>
  <div class="tally">
    <div class="t ok"><div class="num">{R}</div><div class="lbl">Reproduced</div></div>
    <div class="t fail"><div class="num">{F}</div><div class="lbl">Failed</div></div>
    <div class="t"><div class="num">{NC}</div><div class="lbl">Honest passes</div></div>
  </div>
  <div class="dataset">Open data &mdash; <a href="crucible.json">the full ledger as JSON</a> &middot; now a citable dataset on <a href="https://huggingface.co/datasets/Danchi17/folklore-index" target="_blank" rel="noopener">Hugging&nbsp;Face &rarr;</a><br><span class="loadline"><code>datasets.load_dataset("Danchi17/folklore-index")</code></span></div>
</div></header>
{featured}
<section class="ledger"><div class="wrap">
  <div class="sechead"><h2>The ledger</h2><div class="sub">{tested} claims rebuilt &amp; tested &middot; newest first</div></div>
  <div class="filters">
    <button class="on" data-f="all">All</button>
    <button data-f="REPRODUCED">Reproduced</button>
    <button data-f="FAILED">Failed</button>
  </div>
  <div class="grid" id="grid">{cards}
  </div>
</div></section>

<section class="passes"><div class="wrap">
  <div class="sechead"><h2>Honest passes</h2><div class="sub">no simulable core &mdash; on the record anyway</div></div>
  <p class="intro">Not every claim has a computable mechanism. When a claim is descriptive rather
  than mechanistic, the honest verdict is <em>not computable</em> &mdash; recorded, not quietly dropped.</p>
  <ul class="plist">{passes}</ul>
</div></section>

<section class="rules"><div class="wrap"><div class="panel" data-reveal>
  <h2>How a verdict is earned</h2>
  <div class="rlist">
    <div class="rule"><div class="rn">01</div><h3>Model before verdict</h3>
      <p>The smallest model of the claim&rsquo;s stated mechanism is built first, scoped to that
      mechanism &mdash; not reverse-engineered to a desired answer.</p></div>
    <div class="rule"><div class="rn">02</div><h3>A number, not a vibe</h3>
      <p>Every verdict is a measured quantity with a direction that could refute it &mdash; an
      effect size, a threshold, an exponent, a bias.</p></div>
    <div class="rule"><div class="rn">03</div><h3>Re-runnable</h3>
      <p>The code ships with the verdict. A <em>reproduced</em> means the minimal mechanism
      computes; it does not certify the original paper beyond doubt.</p></div>
    <div class="rule"><div class="rn">04</div><h3>Failures are the point</h3>
      <p>A <em>failed</em> means the stated mechanism didn&rsquo;t survive its smallest honest
      model, with the discrepancy measured. Those stay published.</p></div>
  </div>
</div></div></section>

<section class="submit"><div class="wrap"><div class="panel" data-reveal>
  <div><h2>Have a claim that deserves the bench?</h2>
    <p>Send a quantitative, mechanism-bearing claim &mdash; a number, a threshold, an exponent, a
    rate. If it has a simulable core, it gets a model and a public verdict, whichever way it lands.</p></div>
  <a class="btn" href="{repo}/issues" target="_blank" rel="noopener">Submit a claim &rarr;</a>
</div></div></section>

<footer><div class="wrap">
  <span>Agora &mdash; autonomous research OS &middot; The Crucible</span>
  <span>updated {updated} &middot; <a href="{repo}" target="_blank" rel="noopener">source</a></span>
</div></footer>

<script>
  // filter
  const grid = document.getElementById('grid');
  document.querySelectorAll('.filters button').forEach(b => b.addEventListener('click', () => {{
    document.querySelectorAll('.filters button').forEach(x => x.classList.remove('on'));
    b.classList.add('on');
    const f = b.dataset.f;
    grid.querySelectorAll('.card').forEach(c => {{
      c.style.display = (f === 'all' || c.dataset.v === f) ? '' : 'none';
    }});
  }}));
  // reveal on scroll
  const io = new IntersectionObserver((es) => es.forEach(en => {{
    if (en.isIntersecting) {{ en.target.classList.add('in'); io.unobserve(en.target); }}
  }}), {{rootMargin: '0px 0px -8% 0px', threshold: .08}});
  document.querySelectorAll('[data-reveal]').forEach((el, i) => {{
    el.style.transitionDelay = (Math.min(i, 6) * 45) + 'ms';
    io.observe(el);
  }});
  // safety net: reveal anything still hidden shortly after load (covers no-scroll / headless / IO misses)
  window.addEventListener('load', () => setTimeout(() => {{
    document.querySelectorAll('[data-reveal]:not(.in)').forEach(el => el.classList.add('in'));
  }}, 700));
</script>
</body>
</html>"""


if __name__ == "__main__":
    render()
