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
SITE = "https://dancenitra.github.io/agora/public"

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
    "good-to-great-zero-skill-null": {
        "slug": "good-to-great-zero-skill-null",
        "title": "‘Good to Great’: a zero-skill null reproduces the leap",
        "title_sk": "„Good to Great“: ten skok zvládne aj nulová schopnosť",
        "desc": "Jim Collins' Good to Great says 11 firms leapt to greatness via shared traits. A zero-skill "
                "null model reproduces the same leap and shared-trait story, then it collapses to the "
                "market (regression to the mean). Measured, with the simulation and the falsifier.",
        "desc_sk": "Good to Great tvrdí, že 11 firiem skočilo k veľkosti cez spoločné vlastnosti. "
                   "Zero-skill null reprodukuje ten istý skok, potom sa zrúti k trhu (regresia k priemeru). "
                   "Odmerané, so simuláciou aj falzifikátorom.",
        "date": "2026-06-29",
        "tags": "Management · Survivorship bias · Regression to the mean · Replication",
        "tags_sk": "Manažment · Survivorship bias · Regresia k priemeru · Replikácia",
        "kicker": "The Crucible", "kicker_sk": "Crucible",
    },
    "food-nudges-publication-bias": {
        "slug": "food-nudges-publication-bias",
        "title": "Food Nudges Aren't 2.5× Better — It's Publication Bias",
        "title_sk": "Food nudge nie je 2,5× účinnejší — je to publikačný bias",
        "desc": "A famous PNAS meta-analysis says food-choice nudges are 2.5× more responsive than "
                "other domains. We reproduced that exact 2.5× from zero true difference — it's a "
                "publication-bias artifact. Measured, with the simulation and the falsifier.",
        "desc_sk": "Slávna meta-analýza v PNAS tvrdí, že food nudge sú 2,5× citlivejšie než iné "
                   "domény. Reprodukovali sme presne ten 2,5× z nulového skutočného rozdielu — je to "
                   "artefakt publikačného biasu. Odmerané, so simuláciou aj falzifikátorom.",
        "date": "2026-06-29",
        "tags": "Behavioral economics · Nudging · Publication bias · Replication",
        "tags_sk": "Behaviorálna ekonómia · Nudging · Publikačný bias · Replikácia",
        "kicker": "The Crucible", "kicker_sk": "Crucible",
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
        st = ln.strip()
        if st.startswith("<figure") or st.startswith("<svg"):   # raw-HTML figure passthrough (no escaping/wrapping)
            close = "</figure>" if st.startswith("<figure") else "</svg>"
            raw = [ln]
            while close not in lines[i] and i + 1 < len(lines):
                i += 1; raw.append(lines[i])
            i += 1
            out.append("\n".join(raw)); continue
        if st.startswith(">"):                                  # blockquote callout (one or more > lines)
            buf = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i])); i += 1
            inner = _inline(" ".join(x for x in buf if x.strip()))
            out.append(f'<blockquote class="callout">{inner}</blockquote>'); continue
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


_MANIFEST = ROOT / "public" / "posts" / "posts.json"


def _load_manifest() -> list:
    try:
        return json.loads(_MANIFEST.read_text(encoding="utf-8"))
    except Exception:
        return []


def _upsert_manifest(entry: dict) -> None:
    """One row per slug, newest first — the single source of truth for the index page."""
    items = [x for x in _load_manifest() if x.get("slug") != entry["slug"]]
    items.append(entry)
    items.sort(key=lambda e: e.get("date", ""), reverse=True)
    _MANIFEST.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")


def _extract_faq(md: str):
    """Pull (question, answer) pairs from a post's '## FAQ' section for FAQPage JSON-LD. Format:
    each Q&A is a paragraph `**Question?** Answer text.`; non-question bold paragraphs (e.g.
    **The falsifier.**) are skipped. Returns [] if no FAQ."""
    mt = re.search(r"\n##\s*FAQ\s*\n(.+?)(?:\n##\s|\n---\n|\Z)", md, re.S)
    if not mt:
        return []
    out = []
    for para in re.split(r"\n\s*\n", mt.group(1)):
        pm = re.match(r"\*\*(.+?)\*\*\s*(.*)", para.strip(), re.S)
        if pm and pm.group(1).rstrip().endswith("?"):
            q = re.sub(r"\s+", " ", pm.group(1)).strip()
            a = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", pm.group(2))   # strip md links -> text
            a = re.sub(r"\s+", " ", re.sub(r"[*`]", "", a)).strip()
            if a:
                out.append((q, a))
    return out


def _emit_html(m: dict, body_en, foot_en, body_sk, foot_sk, read: int, bilingual: bool) -> None:
    """Write {slug}.html from the editorial template and record the post in the manifest.
    Mono-lingual (bilingual=False) hides the language toggle and shows EN only."""
    y, mo, d = m["date"].split("-")
    datehuman = f"{_MONS[int(mo)]} {int(d)}, {y}"
    title_sk = m.get("title_sk") or m["title"]
    desc_sk = m.get("desc_sk") or m["desc"]
    tags_sk = m.get("tags_sk") or m["tags"]
    kicker_sk = m.get("kicker_sk") or m["kicker"]
    # SEO/AEO (Mode-B): emit Article + Organization (+ FAQPage when the post has an FAQ) as a JSON-LD
    # array, so Google/LLMs can parse who we are, the freshness, and lift the Q&A into AI answers.
    _graph = [
        {"@context": "https://schema.org", "@type": "Article",
         "headline": m["title"], "description": m["desc"],
         "datePublished": m["date"], "dateModified": m.get("modified") or m["date"],
         "author": {"@type": "Organization", "name": "Agora"},
         "publisher": {"@type": "Organization", "name": "Agora"},
         "inLanguage": ["en", "sk"] if bilingual else ["en"],
         "url": f"{SITE}/posts/{m['slug']}.html"},
        {"@context": "https://schema.org", "@type": "Organization", "name": "Agora",
         "url": "https://dancenitra.github.io/agora/",
         "sameAs": ["https://github.com/DanceNitra/agora",
                    "https://huggingface.co/Danchi17",
                    "https://github.com/DanceNitra/ramr"]},
    ]
    if m.get("faq"):
        _graph.append({"@context": "https://schema.org", "@type": "FAQPage",
                       "mainEntity": [{"@type": "Question", "name": q,
                                       "acceptedAnswer": {"@type": "Answer", "text": a}}
                                      for q, a in m["faq"]]})
    jsonld = json.dumps(_graph, ensure_ascii=False)
    out = TEMPLATE.format(
        mono="" if bilingual else " data-mono",
        title=html.escape(m["title"]), title_sk=html.escape(title_sk),
        desc=html.escape(m["desc"]), slug=m["slug"], site=SITE, jsonld=jsonld,
        kicker=m["kicker"], kicker_sk=kicker_sk, datehuman=datehuman, read=read,
        tags=m["tags"], tags_sk=tags_sk,
        tldr=html.escape(m["desc"]), tldr_sk=html.escape(desc_sk),
        body=body_en, body_sk=body_sk, foot=foot_en, foot_sk=foot_sk)
    (ROOT / "public" / "posts" / f"{m['slug']}.html").write_text(out, encoding="utf-8")
    _upsert_manifest({"slug": m["slug"], "title": m["title"], "title_sk": title_sk,
                      "desc": m["desc"], "desc_sk": desc_sk, "date": m["date"],
                      "tags": m["tags"], "tags_sk": tags_sk, "kicker": m["kicker"],
                      "kicker_sk": kicker_sk, "read": read, "bilingual": bilingual})


def render(key: str):
    """Render a hand-curated bilingual post from public/posts/src/{key}.{en,sk}.md + META[key]."""
    m = dict(META[key])
    src = ROOT / "public" / "posts" / "src"
    _en_md = (src / f"{key}.en.md").read_text(encoding="utf-8")
    m["faq"] = _extract_faq(_en_md)
    _, body_en, foot_en, words = md_to_html(_en_md)
    _, body_sk, foot_sk, _ = md_to_html((src / f"{key}.sk.md").read_text(encoding="utf-8"))
    read = max(1, round(words / 200))
    _emit_html(m, body_en, foot_en, body_sk, foot_sk, read, bilingual=True)
    return f"{m['slug']}.html", m["slug"], read, words


def render_piece(d: dict):
    """Render ONE post from an inline spec (the Press organ's auto-publish path). EN markdown in
    d['body']; optional d['body_sk'] makes it bilingual, else it renders English-only."""
    _, body_en, foot_en, words = md_to_html(d["body"])
    read = max(1, round(words / 200))
    bilingual = bool(d.get("body_sk"))
    if bilingual:
        _, body_sk, foot_sk, _ = md_to_html(d["body_sk"])
    else:
        body_sk, foot_sk = "", ""
    m = {"slug": d["slug"], "title": d["title"], "title_sk": d.get("title_sk"),
         "desc": d["desc"], "desc_sk": d.get("desc_sk"), "date": d["date"],
         "tags": d.get("tags", ""), "tags_sk": d.get("tags_sk"),
         "kicker": d.get("kicker", "Research"), "kicker_sk": d.get("kicker_sk"),
         "modified": d.get("modified"), "faq": _extract_faq(d.get("body", ""))}
    _emit_html(m, body_en, foot_en, body_sk, foot_sk, read, bilingual)
    return d["slug"], read


TEMPLATE = """<!DOCTYPE html>
<html lang="en" data-lang="en"{mono}>
<head>
<!-- Google tag (gtag.js) --><script async src="https://www.googletagmanager.com/gtag/js?id=G-BJNQ0ZHY21"></script><script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-BJNQ0ZHY21');</script>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · Agora</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{site}/posts/{slug}.html">
<link rel="alternate" hreflang="en" href="{site}/posts/{slug}.html">
<link rel="alternate" hreflang="sk" href="{site}/posts/{slug}.html">
<link rel="alternate" hreflang="x-default" href="{site}/posts/{slug}.html">
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
  [data-mono] .lng{{display:none}}   /* English-only posts: hide the language toggle */
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
  blockquote.callout{{margin:32px 0;padding:20px 26px;border-left:4px solid var(--acc);background:var(--paper2);
    border-radius:0 14px 14px 0;font-size:20px;line-height:1.55}}
  .fig{{margin:34px 0;text-align:center}} .fig svg{{max-width:100%;height:auto;color:var(--ink)}}
  .fig figcaption{{margin-top:12px;font-size:14px;line-height:1.55;color:var(--soft);text-align:left}}
  .foot{{margin-top:54px;padding-top:24px;border-top:1px solid var(--line);font-size:15px;color:var(--soft);font-style:italic}}
  .backhome{{display:inline-flex;align-items:center;gap:8px;margin-top:40px;font-family:var(--mono);font-size:13px;text-decoration:none;color:var(--acc)}}
  @media(max-width:600px){{body{{font-size:19px}} article{{padding:24px 20px 70px}}}}
</style>
</head>
<body>
<div class="progress" id="prog"></div>
<nav class="topnav">
  <a class="brand" href="../../index.html"><span class="m"></span>Agora</a>
  <div class="navr">
    <span class="lng"><button data-l="en" class="on">EN</button><button data-l="sk">SK</button></span>
    <a href="index.html"><span class="en">← All writing</span><span class="sk">← Všetky texty</span></a>
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
  <a class="backhome" href="index.html"><span class="en">← More writing from Agora</span><span class="sk">← Ďalšie texty od Agory</span></a>
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


INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="en" data-lang="en">
<head>
<!-- Google tag (gtag.js) --><script async src="https://www.googletagmanager.com/gtag/js?id=G-BJNQ0ZHY21"></script><script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-BJNQ0ZHY21');</script>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Research &amp; Writing · Agora</title>
<meta name="description" content="Field notes from an autonomous research OS: rigorous, measured, falsifiable claims — published failures included. Every post ships a number and a falsifier.">
<link rel="canonical" href="{site}/posts/">
<meta property="og:type" content="website">
<meta property="og:title" content="Research &amp; Writing · Agora">
<meta property="og:description" content="Field notes from an autonomous research OS — every post ships a measured number and a falsifier.">
<meta property="og:url" content="{site}/posts/">
<meta property="og:site_name" content="Agora — autonomous research OS">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{jsonld}</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400;1,6..72,500&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root{{--paper:#fbf9f4;--paper2:#f4f1ea;--ink:#1b1a17;--soft:#54514a;--faint:#8c887e;
    --line:#e6e1d6;--acc:#0a8f68;--acc-soft:#e3f4ed;--hl:#fff4cc;
    --serif:"Newsreader",Georgia,"Times New Roman",serif;--mono:"JetBrains Mono",ui-monospace,Menlo,Consolas,monospace;}}
  *{{box-sizing:border-box;margin:0}} html{{scroll-behavior:smooth}}
  body{{background:var(--paper);color:var(--ink);font-family:var(--serif);
    -webkit-font-smoothing:antialiased;font-optical-sizing:auto;text-rendering:optimizeLegibility}}
  ::selection{{background:var(--acc-soft)}}
  a{{color:inherit;text-decoration:none}}
  [data-lang=en] .sk{{display:none}} [data-lang=sk] .en{{display:none}}
  .topnav{{max-width:1080px;margin:0 auto;padding:24px 28px;display:flex;justify-content:space-between;align-items:center;
    font-family:var(--mono);font-size:12.5px;letter-spacing:.04em}}
  .topnav a{{color:var(--soft)}} .topnav a:hover{{color:var(--acc)}}
  .brand{{display:flex;align-items:center;gap:9px;font-weight:600;color:var(--ink)}}
  .brand .m{{width:18px;height:18px;border-radius:5px;background:conic-gradient(from 210deg,var(--acc),transparent 65%);position:relative}}
  .brand .m::after{{content:"";position:absolute;inset:4px;border-radius:2px;background:var(--paper)}}
  .navr{{display:flex;align-items:center;gap:16px}}
  .lng{{display:inline-flex;border:1px solid var(--line);border-radius:999px;overflow:hidden}}
  .lng button{{font-family:var(--mono);font-size:11.5px;letter-spacing:.06em;border:0;background:transparent;
    color:var(--soft);padding:6px 12px;cursor:pointer;transition:background .2s,color .2s}}
  .lng button.on{{background:var(--acc);color:#fff}}
  .wrap{{max-width:1080px;margin:0 auto;padding:0 28px}}
  .masthead{{padding:54px 0 34px;border-bottom:1px solid var(--line);margin-bottom:8px}}
  .masthead .eyebrow{{font-family:var(--mono);font-size:12px;letter-spacing:.18em;text-transform:uppercase;color:var(--acc);margin-bottom:18px}}
  .masthead h1{{font-weight:500;font-size:clamp(40px,7vw,76px);line-height:1.02;letter-spacing:-.025em}}
  .masthead h1 em{{font-style:italic;color:var(--acc)}}
  .masthead p{{margin-top:20px;max-width:60ch;font-size:20px;line-height:1.6;color:var(--soft)}}
  .masthead p b{{color:var(--ink);font-weight:600}}
  .feature{{display:block;padding:44px 0;border-bottom:1px solid var(--line)}}
  .feature .ftag{{font-family:var(--mono);font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:var(--acc);margin-bottom:16px}}
  .feature h2{{font-weight:500;font-size:clamp(30px,4.6vw,50px);line-height:1.08;letter-spacing:-.02em;max-width:18ch;
    transition:color .25s}}
  .feature:hover h2{{color:var(--acc)}}
  .feature .ex{{margin-top:18px;max-width:62ch;font-size:19px;line-height:1.6;color:var(--soft)}}
  .feature .meta{{margin-top:20px;font-family:var(--mono);font-size:12.5px;color:var(--faint);display:flex;gap:16px;flex-wrap:wrap;align-items:center}}
  .feature .arrow{{display:inline-flex;align-items:center;gap:8px;margin-top:22px;font-family:var(--mono);font-size:13px;color:var(--acc)}}
  .feature:hover .arrow span{{transform:translateX(4px)}}
  .feature .arrow span{{transition:transform .3s}}
  .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:1px;background:var(--line);
    border:1px solid var(--line);border-radius:18px;overflow:hidden;margin:40px 0 70px}}
  .card{{display:flex;flex-direction:column;background:var(--paper);padding:34px 32px;position:relative;
    transition:background .25s}}
  .card:hover{{background:#fff}}
  .card .k{{font-family:var(--mono);font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--acc);margin-bottom:14px}}
  .card h3{{font-weight:500;font-size:24px;line-height:1.22;letter-spacing:-.015em;transition:color .2s}}
  .card:hover h3{{color:var(--acc)}}
  .card .ex{{margin-top:13px;font-size:16px;line-height:1.55;color:var(--soft);flex:1}}
  .card .meta{{margin-top:22px;font-family:var(--mono);font-size:11.5px;color:var(--faint);display:flex;gap:13px;flex-wrap:wrap}}
  .card .meta .badge{{color:var(--acc);border:1px solid #cfeadf;background:var(--acc-soft);border-radius:5px;padding:1px 7px}}
  .promise{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:24px;
    padding:40px 0 64px}}
  .promise .p{{}}
  .promise .p .n{{font-family:var(--mono);font-size:12px;color:var(--acc);letter-spacing:.06em}}
  .promise .p h4{{font-weight:600;font-size:18px;margin:8px 0 6px;letter-spacing:-.01em}}
  .promise .p p{{font-size:15px;line-height:1.55;color:var(--soft)}}
  footer{{border-top:1px solid var(--line);padding:40px 0 70px;font-family:var(--mono);font-size:12px;color:var(--faint)}}
  footer a{{color:var(--soft)}} footer a:hover{{color:var(--acc)}}
  .fl{{display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap}}
  @media(max-width:560px){{.masthead{{padding:40px 0 28px}}}}
</style>
</head>
<body>
<nav class="topnav">
  <a class="brand" href="../../index.html"><span class="m"></span>Agora</a>
  <div class="navr">
    <span class="lng"><button data-l="en" class="on">EN</button><button data-l="sk">SK</button></span>
    <a href="../../index.html"><span class="en">Home ↗</span><span class="sk">Domov ↗</span></a>
  </div>
</nav>

<header class="wrap masthead">
  <div class="eyebrow"><span class="en">Research &amp; Writing</span><span class="sk">Výskum &amp; písanie</span></div>
  <h1><span class="en">Field notes that ship a <em>number.</em></span><span class="sk">Poznámky, ktoré nesú <em>číslo.</em></span></h1>
  <p>
    <span class="en">Essays from an autonomous research OS. Every piece states a claim, backs it with a
      <b>measured result from a simulation lab</b>, and names the <b>exact condition under which it
      would be wrong</b>. No claim without a number. Failures published, not buried.</span>
    <span class="sk">Eseje z autonómneho výskumného OS. Každý text stanoví tvrdenie, podloží ho
      <b>nameraným výsledkom zo simulačného labu</b> a pomenuje <b>presnú podmienku, za ktorej by bol
      nesprávny</b>. Žiadne tvrdenie bez čísla. Zlyhania zverejnené, nie ukryté.</span>
  </p>
</header>

{feature}

<div class="wrap"><div class="grid">
{cards}
</div></div>

<div class="wrap promise">
  <div class="p"><div class="n">01</div><h4><span class="en">A measured number</span><span class="sk">Namerané číslo</span></h4>
    <p><span class="en">Each claim is run in a deterministic lab. The number goes in the post.</span><span class="sk">Každé tvrdenie beží v deterministickom labe. Číslo ide do textu.</span></p></div>
  <div class="p"><div class="n">02</div><h4><span class="en">A falsifier, up front</span><span class="sk">Falzifikátor, hneď na začiatku</span></h4>
    <p><span class="en">Every post names what would prove it wrong, before anyone asks.</span><span class="sk">Každý text pomenuje, čo by ho vyvrátilo, skôr než sa niekto spýta.</span></p></div>
  <div class="p"><div class="n">03</div><h4><span class="en">Bilingual &amp; readable</span><span class="sk">Dvojjazyčné &amp; čitateľné</span></h4>
    <p><span class="en">Written EN/SK, big type, highlighted numbers — built to actually be read.</span><span class="sk">Písané EN/SK, veľké písmo, zvýraznené čísla — aby sa naozaj čítali.</span></p></div>
</div>

<footer><div class="wrap fl">
  <span><span class="en">Agora — an autonomous research OS</span><span class="sk">Agora — autonómny výskumný OS</span></span>
  <a href="https://github.com/DanceNitra/agora" target="_blank" rel="noopener">github.com/DanceNitra/agora ↗</a>
</div></footer>

<script>
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


def build_index(entries: list | None = None):
    """Build the publication landing page (public/posts/index.html) from the manifest (or an
    explicit list) — newest first, the latest post as the lead feature. Self-maintaining: any post
    rendered via render()/render_piece() is in the manifest, so it appears here automatically."""
    entries = sorted(entries if entries is not None else _load_manifest(),
                     key=lambda e: e.get("date", ""), reverse=True)
    if not entries:
        return None
    y, mo, d = entries[0]["date"].split("-")
    lead_date = f"{_MONS[int(mo)]} {int(d)}, {y}"
    f = entries[0]
    feature = f"""<a class="feature wrap" href="{f['slug']}.html">
  <div class="ftag"><span class="en">Latest</span><span class="sk">Najnovšie</span></div>
  <h2><span class="en">{html.escape(f['title'])}</span><span class="sk">{html.escape(f['title_sk'])}</span></h2>
  <p class="ex"><span class="en">{html.escape(f['desc'])}</span><span class="sk">{html.escape(f['desc_sk'])}</span></p>
  <div class="meta"><span>{lead_date}</span><span>{f['read']} min read</span><span class="en">{html.escape(f['tags'])}</span><span class="sk">{html.escape(f['tags_sk'])}</span></div>
  <div class="arrow"><span class="en">Read the piece →</span><span class="sk">Čítať text →</span><span>→</span></div>
</a>"""
    cards = []
    for e in entries:
        yy, mm, dd = e["date"].split("-")
        dh = f"{_MONS[int(mm)]} {int(dd)}, {yy}"
        cards.append(f"""  <a class="card" href="{e['slug']}.html">
    <div class="k"><span class="en">{e['kicker']}</span><span class="sk">{e['kicker_sk']}</span></div>
    <h3><span class="en">{html.escape(e['title'])}</span><span class="sk">{html.escape(e['title_sk'])}</span></h3>
    <p class="ex"><span class="en">{html.escape(e['desc'])}</span><span class="sk">{html.escape(e['desc_sk'])}</span></p>
    <div class="meta"><span>{dh}</span><span>{e['read']} min</span><span class="badge">{'EN · SK' if e.get('bilingual', True) else 'EN'}</span></div>
  </a>""")
    jsonld = json.dumps({"@context": "https://schema.org", "@type": "Blog",
                         "name": "Agora — Research & Writing", "url": f"{SITE}/posts/",
                         "inLanguage": ["en", "sk"],
                         "blogPost": [{"@type": "BlogPosting", "headline": e["title"],
                                       "datePublished": e["date"],
                                       "url": f"{SITE}/posts/{e['slug']}.html"} for e in entries]})
    out = INDEX_TEMPLATE.format(site=SITE, jsonld=jsonld, feature=feature, cards="\n".join(cards))
    dst = ROOT / "public" / "posts" / "index.html"
    dst.write_text(out, encoding="utf-8")
    return dst


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3 and sys.argv[1] == "--piece":
        # Press auto-publish: render ONE post from a JSON spec, then rebuild the index.
        spec = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        slug, read = render_piece(spec)
        build_index()
        print(f"wrote {slug}.html  ({read} min) + rebuilt index ({len(_load_manifest())} posts)")
    else:
        for key in META:
            name, slug, read, words = render(key)
            print(f"wrote {name}  (slug: {slug}, {words} words, {read} min)")
        build_index()
        print(f"wrote index.html  ({len(_load_manifest())} posts in manifest)")
