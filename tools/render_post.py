#!/usr/bin/env python3
"""Render Agora's research posts into beautiful, ADHD-friendly, SEO-strong, bilingual (EN/SK) HTML.

Reads {name}.en.md and {name}.sk.md from public/posts/src/, renders both into one page with an
EN/SK toggle (persisted), an editorial template (warm paper, Newsreader serif, big readable type,
highlighted measured numbers, takeaway box, pull-quoted falsifier, reading progress, COMPUTED
read-time), and full SEO/Open-Graph/JSON-LD. Writes a clean-slug .html.
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = "https://dancenitra.github.io/agora"

META = {
    "pre-trends": {
        "slug": "pre-trends-test-weak-evidence",
        "title": "Passing a Pre-Trends Test Is Weak Evidence — We Measured It",
        "title_sk": "Prejsť testom pre-trendov je slabý dôkaz — odmerali sme to",
        "desc": "A difference-in-differences pre-trends test catches only about one-third of the "
                "violations that ruin your estimate. Measured, with the simulation and the falsifier.",
        "desc_sk": "Test pre-trendov v difference-in-differences zachytí len asi tretinu porušení, "
                   "ktoré zničia tvoj odhad. Odmerané, so simuláciou aj falzifikátorom.",
        "date": "2026-06-11",
        "tags": "Causal inference · Difference-in-differences · Parallel trends",
        "tags_sk": "Kauzálna inferencia · Difference-in-differences · Paralelné trendy",
        "kicker": "Causal inference", "kicker_sk": "Kauzálna inferencia",
    },
    "phase-diagram": {
        "slug": "causal-inference-phase-diagram",
        "title": "Causal Inference Has a Phase Diagram: Even Randomized Experiments Fail Near Criticality",
        "title_sk": "Kauzálna inferencia má fázový diagram: aj randomizované experimenty zlyhávajú pri kritickom bode",
        "desc": "Near a critical point, even a perfectly randomized experiment overstates the effect — "
                "by up to 96%. The bias comes from interference, not confounding. Measured on a lattice.",
        "desc_sk": "Pri kritickom bode aj dokonale randomizovaný experiment nadhodnotí efekt — až o 96 %. "
                   "Skreslenie pochádza z interferencie, nie zo zmätenia. Odmerané na mriežke.",
        "date": "2026-06-10",
        "tags": "Causal inference · Interference · Complexity",
        "tags_sk": "Kauzálna inferencia · Interferencia · Komplexita",
        "kicker": "Causal inference", "kicker_sk": "Kauzálna inferencia",
    },
}

_STAT = re.compile(r"^[+\-−]?[\d.,\s]+(?:%|×|x|SD|σ)?$|^\d+[\s,]*(?:[–-]\s*\d+)?\s*%$")
_MONS = ["", "January", "February", "March", "April", "May", "June", "July", "August",
         "September", "October", "November", "December"]


def _inline(s: str) -> str:
    s = html.escape(s, quote=False)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    def bold(m):
        inner = m.group(1)
        cls = "stat" if _STAT.match(inner.strip()) else "b"
        return f'<strong class="{cls}">{inner}</strong>'
    s = re.sub(r"\*\*([^*]+)\*\*", bold, s)
    s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", s)
    return s


def _hl(cell: str) -> str:
    if _STAT.match(html.unescape(re.sub(r"<[^>]+>", "", cell)).strip()):
        return f'<span class="cellnum">{cell}</span>'
    return cell


def md_to_html(md: str):
    body, foot = (md.rsplit("\n---\n", 1) + [""])[:2] if "\n---\n" in md else (md, "")
    lines = body.split("\n")
    out, i, title, words = [], 0, "", 0
    while i < len(lines):
        ln = lines[i]
        words += len(ln.split())
        if ln.startswith("# "):
            title = ln[2:].strip(); i += 1; continue
        if ln.startswith("## "):
            out.append(f"<h2>{_inline(ln[3:].strip())}</h2>"); i += 1; continue
        if ln.strip().startswith("|") and i + 1 < len(lines) and set(lines[i+1].replace("|", "").strip()) <= set("-: "):
            head = [c.strip() for c in ln.strip().strip("|").split("|")]
            i += 2; rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")]); i += 1
            th = "".join(f"<th>{_inline(h)}</th>" for h in head)
            trs = "".join("<tr>" + "".join(f"<td>{_hl(_inline(c))}</td>" for c in r) + "</tr>" for r in rows)
            out.append(f'<div class="tablewrap"><table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>')
            continue
        if re.match(r"^\d+\.\s", ln):
            items = []
            while i < len(lines) and re.match(r"^\d+\.\s", lines[i]):
                items.append(f"<li>{_inline(re.sub(r'^\\d+\\.\\s', '', lines[i]))}</li>"); i += 1
            out.append(f"<ol>{''.join(items)}</ol>"); continue
        if ln.strip().startswith("- "):
            items = []
            while i < len(lines) and lines[i].strip().startswith("- "):
                items.append(f"<li>{_inline(lines[i].strip()[2:])}</li>"); i += 1
            out.append(f"<ul>{''.join(items)}</ul>"); continue
        if not ln.strip():
            i += 1; continue
        para = [ln]; i += 1
        while i < len(lines) and lines[i].strip() and not lines[i].startswith(("#", "|")) and not re.match(r"^\d+\.\s", lines[i]) and not lines[i].strip().startswith("- "):
            para.append(lines[i]); words += len(lines[i].split()); i += 1
        text = " ".join(para).strip()
        low = text.lower()
        if low.startswith("**the falsifier") or low.startswith("**falzifikátor"):
            lab = "The falsifier" if "falsifier" in low else "Falzifikátor"
            rest = text.split(".**", 1)[1] if ".**" in text else text
            out.append(f'<blockquote class="falsifier"><span class="ql">{lab}</span>{_inline(rest.strip())}</blockquote>')
        else:
            out.append(f"<p>{_inline(text)}</p>")
    foot_html = _inline(foot.strip().lstrip("*").rstrip("*").strip())
    return title, "\n".join(out), foot_html, words


def render(key: str):
    m = META[key]
    src = ROOT / "public" / "posts" / "src"
    _, body_en, foot_en, words = md_to_html((src / f"{key}.en.md").read_text(encoding="utf-8"))
    _, body_sk, foot_sk, _ = md_to_html((src / f"{key}.sk.md").read_text(encoding="utf-8"))
    read = max(1, round(words / 200))
    y, mo, d = m["date"].split("-")
    datehuman = f"{_MONS[int(mo)]} {int(d)}, {y}"
    jsonld = json.dumps({"@context": "https://schema.org", "@type": "Article",
                         "headline": m["title"], "description": m["desc"], "datePublished": m["date"],
                         "author": {"@type": "Organization", "name": "Agora"},
                         "inLanguage": ["en", "sk"], "url": f"{SITE}/posts/{m['slug']}.html"})
    out = TEMPLATE.format(
        title=html.escape(m["title"]), title_sk=html.escape(m["title_sk"]),
        desc=html.escape(m["desc"]), slug=m["slug"], site=SITE, jsonld=jsonld,
        kicker=m["kicker"], kicker_sk=m["kicker_sk"], datehuman=datehuman, read=read,
        tags=m["tags"], tags_sk=m["tags_sk"],
        tldr=html.escape(m["desc"]), tldr_sk=html.escape(m["desc_sk"]),
        body=body_en, body_sk=body_sk, foot=foot_en, foot_sk=foot_sk)
    dst = ROOT / "public" / "posts" / f"{m['slug']}.html"
    dst.write_text(out, encoding="utf-8")
    return dst.name, m["slug"], read, words


TEMPLATE = """<!DOCTYPE html>
<html lang="en" data-lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · Agora</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{site}/posts/{slug}.html">
<meta property="og:type" content="article">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{site}/posts/{slug}.html">
<meta property="og:site_name" content="Agora — autonomous research OS">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{desc}">
<script type="application/ld+json">{jsonld}</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400;1,6..72,500&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root{{--paper:#fbf9f4;--paper2:#f4f1ea;--ink:#1b1a17;--soft:#54514a;--faint:#8c887e;
    --line:#e6e1d6;--acc:#0a8f68;--acc-soft:#e3f4ed;--hl:#fff4cc;
    --serif:"Newsreader",Georgia,"Times New Roman",serif;--mono:"JetBrains Mono",ui-monospace,Menlo,Consolas,monospace;}}
  *{{box-sizing:border-box;margin:0}} html{{scroll-behavior:smooth}}
  body{{background:var(--paper);color:var(--ink);font-family:var(--serif);font-size:21px;line-height:1.75;
    -webkit-font-smoothing:antialiased;font-optical-sizing:auto;text-rendering:optimizeLegibility}}
  ::selection{{background:var(--acc-soft)}}
  a{{color:var(--acc);text-underline-offset:3px;text-decoration-thickness:1px}}
  [data-lang=en] .sk{{display:none}} [data-lang=sk] .en{{display:none}}
  .progress{{position:fixed;top:0;left:0;height:3px;width:0;background:var(--acc);z-index:50;transition:width .1s linear}}
  .topnav{{max-width:760px;margin:0 auto;padding:24px 24px;display:flex;justify-content:space-between;align-items:center;
    font-family:var(--mono);font-size:12.5px;letter-spacing:.04em}}
  .topnav a{{text-decoration:none;color:var(--soft)}} .topnav a:hover{{color:var(--acc)}}
  .brand{{display:flex;align-items:center;gap:9px;font-weight:600;color:var(--ink)}}
  .brand .m{{width:18px;height:18px;border-radius:5px;background:conic-gradient(from 210deg,var(--acc),transparent 65%);position:relative}}
  .brand .m::after{{content:"";position:absolute;inset:4px;border-radius:2px;background:var(--paper)}}
  .navr{{display:flex;align-items:center;gap:16px}}
  .lng{{display:inline-flex;border:1px solid var(--line);border-radius:999px;overflow:hidden}}
  .lng button{{font-family:var(--mono);font-size:11.5px;letter-spacing:.06em;border:0;background:transparent;
    color:var(--soft);padding:6px 12px;cursor:pointer;transition:background .2s,color .2s}}
  .lng button.on{{background:var(--acc);color:#fff}}
  article{{max-width:680px;margin:0 auto;padding:30px 24px 90px}}
  .kicker{{font-family:var(--mono);font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:var(--acc);margin-bottom:18px}}
  h1{{font-weight:500;font-size:clamp(34px,5.2vw,52px);line-height:1.1;letter-spacing:-.018em;margin:0 0 18px}}
  .meta{{font-family:var(--mono);font-size:13px;color:var(--faint);display:flex;gap:16px;flex-wrap:wrap;
    padding-bottom:26px;border-bottom:1px solid var(--line)}}
  .tldr{{background:var(--acc-soft);border:1px solid #cfeadf;border-radius:14px;padding:20px 24px;margin:30px 0 8px}}
  .tldr .lab{{font-family:var(--mono);font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:var(--acc);margin-bottom:8px}}
  .tldr p{{margin:0;font-size:20px;line-height:1.6}}
  article p{{margin:22px 0}}
  article h2{{font-weight:600;font-size:28px;letter-spacing:-.01em;margin:46px 0 6px}}
  strong.b{{font-weight:600}}
  strong.stat{{font-weight:600;color:var(--acc);background:var(--hl);padding:0 .18em;border-radius:4px;
    box-decoration-break:clone;-webkit-box-decoration-break:clone}}
  em{{font-style:italic}}
  ol,ul{{margin:22px 0;padding-left:1.3em}} li{{margin:12px 0}}
  ol li::marker{{font-family:var(--mono);font-size:14px;color:var(--acc)}}
  code{{font-family:var(--mono);font-size:.82em;background:var(--paper2);padding:2px 6px;border-radius:5px}}
  .tablewrap{{overflow-x:auto;margin:30px 0;border:1px solid var(--line);border-radius:14px}}
  table{{border-collapse:collapse;width:100%;font-size:15px;background:#fff}}
  th,td{{text-align:left;padding:13px 16px;border-bottom:1px solid var(--line)}}
  th{{font-family:var(--mono);font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--soft);background:var(--paper2)}}
  tbody tr:last-child td{{border-bottom:0}} tbody tr:hover{{background:var(--paper2)}}
  td{{font-variant-numeric:tabular-nums}} .cellnum{{font-family:var(--mono);font-weight:500}}
  blockquote.falsifier{{margin:40px 0;padding:24px 28px;border-left:4px solid var(--acc);
    background:var(--paper2);border-radius:0 14px 14px 0;font-size:21px;line-height:1.6}}
  blockquote.falsifier .ql{{display:block;font-family:var(--mono);font-size:11px;letter-spacing:.16em;
    text-transform:uppercase;color:var(--acc);margin-bottom:8px}}
  .foot{{margin-top:54px;padding-top:24px;border-top:1px solid var(--line);font-size:15px;color:var(--soft);font-style:italic}}
  .backhome{{display:inline-flex;align-items:center;gap:8px;margin-top:40px;font-family:var(--mono);font-size:13px;text-decoration:none;color:var(--acc)}}
  @media(max-width:600px){{body{{font-size:19px}} article{{padding:24px 20px 70px}}}}
</style>
</head>
<body>
<div class="progress" id="prog"></div>
<nav class="topnav">
  <a class="brand" href="../index.html"><span class="m"></span>Agora</a>
  <div class="navr">
    <span class="lng"><button data-l="en" class="on">EN</button><button data-l="sk">SK</button></span>
    <a href="../index.html#research"><span class="en">← All research</span><span class="sk">← Späť na výskum</span></a>
  </div>
</nav>
<article>
  <div class="kicker"><span class="en">{kicker}</span><span class="sk">{kicker_sk}</span></div>
  <h1><span class="en">{title}</span><span class="sk">{title_sk}</span></h1>
  <div class="meta"><span>{datehuman}</span><span>{read} min read</span><span class="en">{tags}</span><span class="sk">{tags_sk}</span></div>
  <div class="tldr"><div class="lab"><span class="en">The takeaway</span><span class="sk">Zhrnutie</span></div>
    <p><span class="en">{tldr}</span><span class="sk">{tldr_sk}</span></p></div>
  <div class="en">{body}</div>
  <div class="sk">{body_sk}</div>
  <div class="foot"><span class="en">{foot}</span><span class="sk">{foot_sk}</span></div>
  <a class="backhome" href="../index.html#research"><span class="en">← Back to the track record</span><span class="sk">← Späť na track record</span></a>
</article>
<script>
  var p=document.getElementById('prog');
  addEventListener('scroll',function(){{var h=document.documentElement,b=document.body;
    var st=h.scrollTop||b.scrollTop,sh=(h.scrollHeight||b.scrollHeight)-h.clientHeight;
    p.style.width=(sh>0?(st/sh*100):0)+'%';}},{{passive:true}});
  var root=document.documentElement, btns=document.querySelectorAll('.lng button');
  function setLang(l){{root.setAttribute('data-lang',l);root.setAttribute('lang',l);
    btns.forEach(function(b){{b.classList.toggle('on',b.getAttribute('data-l')===l);}});
    try{{localStorage.setItem('agora-lang',l);}}catch(e){{}}}}
  btns.forEach(function(b){{b.addEventListener('click',function(){{setLang(b.getAttribute('data-l'));}});}});
  try{{var s=localStorage.getItem('agora-lang');if(s)setLang(s);}}catch(e){{}}
</script>
</body>
</html>
"""


if __name__ == "__main__":
    for key in META:
        name, slug, read, words = render(key)
        print(f"wrote {name}  (slug: {slug}, {words} words, {read} min)")
