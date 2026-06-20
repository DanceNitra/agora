"""
render_aiclaims.py - render the AI-Claim Crucible (agora_output/aiclaims/aiclaims.json) into a public page
at public/ai-claims/index.html. The differentiated subset: widely-repeated AI-ENGINEERING folklore rebuilt
as the smallest runnable test and ruled REPRODUCED / FAILED / NOT_COMPUTABLE. Every entry links its runnable
code (committed) and the live Folklore Index dataset (HF / pip / Zenodo). Re-run after any new entry.

Usage:  python -X utf8 tools/render_aiclaims.py
"""
import json, os, html, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = "https://github.com/DanceNitra/agora"
SITE = "https://dancenitra.github.io/agora"
SRC = os.path.join(ROOT, "agora_output", "aiclaims", "aiclaims.json")
OUT_DIR = os.path.join(ROOT, "public", "ai-claims")


def e(s):
    return html.escape(str(s or ""))


def code_url(lab):
    if not lab:
        return ""
    import re
    m = re.search(r"([\w./\\-]+\.py)", lab)
    if not m:
        return ""
    rel = m.group(1).replace("\\", "/")
    return f"{REPO}/blob/main/{rel}" if os.path.exists(os.path.join(ROOT, rel)) else ""


CARD = """      <article class="card {cls}">
        <div class="chead"><span class="cv {cls}">{verdict}</span><span class="cdate">{date}</span></div>
        <h3>{claim}</h3>
        <p class="csrc">{source}</p>
        <p class="cnote">{note}</p>
        <div class="cfoot">{codeline}</div>
      </article>"""


def main():
    ds = json.load(open(SRC, encoding="utf-8"))
    entries = ds.get("entries", [])
    by = {"REPRODUCED": 0, "FAILED": 0, "NOT_COMPUTABLE": 0}
    for x in entries:
        by[x.get("verdict", "")] = by.get(x.get("verdict", ""), 0) + 1
    # newest first
    entries = sorted(entries, key=lambda x: x.get("date", ""), reverse=True)
    cards = []
    for x in entries:
        v = x.get("verdict", "")
        cls = {"REPRODUCED": "ok", "FAILED": "fail", "NOT_COMPUTABLE": "nc"}.get(v, "nc")
        url = code_url(x.get("lab"))
        codeline = (f'<a class="code" href="{url}" target="_blank" rel="noopener">Read the runnable test &rarr;</a>'
                    if url else '<span class="nocode">code link pending</span>')
        cards.append(CARD.format(cls=cls, verdict=e(v), date=e(x.get("date", "")), claim=e(x.get("claim", "")),
                                 source=e(x.get("source", "")), note=e(x.get("note", "")), codeline=codeline))
    page = TEMPLATE.format(site=SITE, repo=REPO, R=by["REPRODUCED"], F=by["FAILED"], NC=by["NOT_COMPUTABLE"],
                           total=len(entries), updated=time.strftime("%Y-%m-%d"), cards="\n".join(cards))
    os.makedirs(OUT_DIR, exist_ok=True)
    open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8").write(page)
    print("rendered public/ai-claims/index.html — %dR/%dF/%dNC, %d claims"
          % (by["REPRODUCED"], by["FAILED"], by["NOT_COMPUTABLE"], len(entries)))


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The AI-Claim Crucible &middot; AI-engineering folklore, tested in code &middot; Agora</title>
<meta name="description" content="A public ledger of widely-repeated AI-engineering claims rebuilt as the smallest runnable test and ruled REPRODUCED, FAILED, or NOT_COMPUTABLE: smaller-chunks-for-RAG, rerankers, the time-horizon headline, LLM conservatism, poison-deference and more. Every verdict ships a measured number and runnable code.">
<link rel="canonical" href="{site}/public/ai-claims/">
<meta property="og:type" content="website">
<meta property="og:title" content="The AI-Claim Crucible — AI folklore, tested in code">
<meta property="og:description" content="We rebuild repeated AI-engineering claims as runnable tests and publish the verdict — failures included. Measured numbers + code.">
<meta property="og:url" content="{site}/public/ai-claims/">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root{{--paper:#faf7f0;--paper2:#f2eee4;--ink:#17150f;--text:#4d493f;--faint:#938d7f;--line:#e3ddcf;
    --acc:#0c7a55;--acc-soft:#e1f1ea;--bad:#b1361f;--bad-soft:#f8e6e0;--gold:#9a7b1e;--gold-soft:#f4ecd6;
    --serif:"Newsreader",Georgia,serif;--mono:"JetBrains Mono",ui-monospace,Consolas,monospace;}}
  *{{box-sizing:border-box;margin:0}} html{{scroll-behavior:smooth}}
  body{{background:var(--paper);color:var(--ink);font-family:var(--serif);-webkit-font-smoothing:antialiased;
    background-image:radial-gradient(circle at 12% -8%,#fff 0%,transparent 42%);}}
  a{{color:inherit;text-decoration:none}} .wrap{{max-width:1060px;margin:0 auto;padding:0 28px}}
  .nav{{position:sticky;top:0;z-index:20;background:rgba(250,247,240,.85);backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}}
  .nav .wrap{{display:flex;justify-content:space-between;align-items:center;padding:15px 28px;font-family:var(--mono);font-size:12.5px;letter-spacing:.04em}}
  .brand{{font-weight:600}} .navr a{{color:var(--faint);margin-left:18px}} .navr a:hover{{color:var(--acc)}}
  .mast{{padding:68px 0 30px}}
  .kick{{font-family:var(--mono);font-size:12px;letter-spacing:.3em;text-transform:uppercase;color:var(--acc);margin-bottom:22px}}
  .mast h1{{font-weight:500;font-size:clamp(40px,7vw,72px);line-height:1.02;letter-spacing:-.03em;max-width:16ch}}
  .lede{{margin-top:22px;font-size:19px;line-height:1.55;color:var(--text);max-width:62ch}}
  .lede b{{color:var(--ink);font-weight:600}}
  .tally{{display:flex;gap:30px;margin-top:30px;font-family:var(--mono)}}
  .t .num{{font-size:30px;font-weight:600}} .t .lbl{{font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--faint)}}
  .t.ok .num{{color:var(--acc)}} .t.fail .num{{color:var(--bad)}}
  .dataset{{margin-top:24px;font-family:var(--mono);font-size:13px;color:var(--faint)}}
  .dataset a{{color:var(--acc);border-bottom:1px solid var(--acc-soft)}} .dataset code{{background:var(--paper2);border:1px solid var(--line);border-radius:5px;padding:2px 7px;font-size:12px}}
  .grid{{margin:36px 0 60px;display:grid;gap:18px}}
  .card{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:22px 24px;box-shadow:0 1px 0 #00000008}}
  .card.fail{{border-left:3px solid var(--bad)}} .card.ok{{border-left:3px solid var(--acc)}} .card.nc{{border-left:3px solid var(--gold)}}
  .chead{{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}}
  .cv{{font-family:var(--mono);font-size:11px;font-weight:600;letter-spacing:.1em;padding:3px 9px;border-radius:20px}}
  .cv.fail{{color:var(--bad);background:var(--bad-soft)}} .cv.ok{{color:var(--acc);background:var(--acc-soft)}} .cv.nc{{color:var(--gold);background:var(--gold-soft)}}
  .cdate{{font-family:var(--mono);font-size:11px;color:var(--faint)}}
  .card h3{{font-weight:600;font-size:21px;line-height:1.3;letter-spacing:-.01em}}
  .csrc{{font-size:13.5px;color:var(--faint);font-style:italic;margin-top:6px}}
  .cnote{{margin-top:12px;font-size:15.5px;line-height:1.6;color:var(--text)}}
  .cfoot{{margin-top:14px;font-family:var(--mono);font-size:12.5px}}
  .cfoot .code{{color:var(--acc);border-bottom:1px solid var(--acc-soft)}} .cfoot .nocode{{color:var(--faint)}}
  footer{{border-top:1px solid var(--line);padding:26px 0 50px;font-family:var(--mono);font-size:12px;color:var(--faint)}}
  footer a{{color:var(--acc)}}
</style>
</head>
<body>
<nav class="nav"><div class="wrap">
  <a class="brand" href="{site}/">Agora</a>
  <div class="navr"><a href="{site}/public/crucible/">The Crucible</a><a href="https://huggingface.co/datasets/Danchi17/folklore-index" target="_blank" rel="noopener">Dataset</a><a href="{site}/posts/">Writing</a></div>
</div></nav>
<header class="mast"><div class="wrap">
  <div class="kick">The AI-Claim Crucible</div>
  <h1>AI folklore, <em>tested in code.</em></h1>
  <p class="lede">The field repeats a lot of engineering folklore &mdash; <b>&ldquo;chunk smaller for RAG&rdquo;</b>, <b>&ldquo;a reranker never hurts&rdquo;</b>, <b>&ldquo;trust the model&rsquo;s confidence&rdquo;</b> &mdash; with little runnable verification. We rebuild each claim as the <b>smallest test that could settle it</b>, run it on frontier models, and publish the verdict: <b>reproduced</b>, <b>failed</b>, or <b>not computable</b>. Every entry ships a measured number and the code.</p>
  <div class="tally">
    <div class="t ok"><div class="num">{R}</div><div class="lbl">Reproduced</div></div>
    <div class="t fail"><div class="num">{F}</div><div class="lbl">Failed</div></div>
    <div class="t"><div class="num">{NC}</div><div class="lbl">Not computable</div></div>
  </div>
  <div class="dataset">Part of the Folklore Index &mdash; <a href="https://huggingface.co/datasets/Danchi17/folklore-index" target="_blank" rel="noopener">dataset on Hugging Face</a> &middot; <code>pip install folklore-index</code> &middot; <a href="https://doi.org/10.5281/zenodo.20771544" target="_blank" rel="noopener">DOI</a></div>
</div></header>
<section><div class="wrap"><div class="grid">
{cards}
</div></div></section>
<footer><div class="wrap">A public, machine-readable ledger &middot; updated {updated} &middot; <a href="{repo}" target="_blank" rel="noopener">source + runnable tests</a> &middot; submit a claim: <a href="{repo}/issues/new?title=AI-claim%20submission:%20&body=Claim:%0ASource/where%20it%27s%20repeated:%0AWhy%20FAILED%20is%20plausible:" target="_blank" rel="noopener">open an issue &rarr;</a></div></footer>
</body>
</html>"""


if __name__ == "__main__":
    main()
