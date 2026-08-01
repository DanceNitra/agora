#!/usr/bin/env python3
"""Render Agora's research posts into beautiful, ADHD-friendly, SEO-strong, bilingual (EN/SK) HTML.

Reads {name}.en.md and {name}.sk.md from public/posts/src/, renders both into one page with an
EN/SK toggle (persisted), an editorial template (warm paper, Newsreader serif, big readable type,
highlighted measured numbers, takeaway box, pull-quoted falsifier, reading progress, COMPUTED
read-time), and full SEO/Open-Graph/JSON-LD. Writes a clean-slug .html.

PUBLISH GATE: run /stress-claim (argument) + /verify-claims (facts) on the source BEFORE rendering.
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = "https://dancenitra.github.io/agora/public"

META = {
    "self-audit-32": {
        "slug": "labels-failed-more-than-measurements",
        "title": "Labels failed more than measurements: severe-testing our AI's 32 confident findings",
        "title_sk": "Labely zlyhali viac než merania: prísny test 32 sebavedomých zistení našej AI",
        "desc": "Our autonomous AI pipeline published 32 findings as confident 'discoveries.' Under a full "
                "adversarial audit the labels failed (53% textbook-relabeled) more than the measurements "
                "(34% wrong); 13% were already honest. Reproducible, with a positive control.",
        "desc_sk": "Náš autonómny AI pipeline publikoval 32 zistení ako sebavedomé „objavy“. Pod plným "
                   "adversariálnym auditom labely zlyhali (53 % učebnicový relabel) viac než merania "
                   "(34 % zlé); 13 % bolo už čestných. Reprodukovateľné, s pozitívnou kontrolou.",
        "date": "2026-07-05", "modified": "2026-07-05",
        "tags": "AI research · Self-audit · Meta-science · Autonomous agents · Reproducibility",
        "tags_sk": "AI výskum · Sebaaudit · Meta-veda · Autonómni agenti · Reprodukovateľnosť",
        "kicker": "Meta · self-audit", "kicker_sk": "Meta · sebaaudit",
    },
    "defenses-that-failed-their-own-control": {
        "slug": "defenses-that-failed-their-own-control",
        "title": "The control is the number: four memory-poisoning defenses that failed, including one of ours",
        "title_sk": "Kontrola je to číslo: štyri obrany proti otrave pamäte, ktoré zlyhali — vrátane našej",
        "desc": "We published an 88-100% memory-poisoning hijack without printing its control: a RANDOM "
                "five-word trigger reaches 65-90% on the same fixture, and our own probe records "
                "optimization_margin_over_random = 0.0. Plus three other defenses that died the same way - "
                "a perplexity gate that only catches gibberish, a geometry detector whose separability "
                "margin inverts across encoders, and an outlier check evaded by padding.",
        "desc_sk": "Publikovali sme únos pamäte 88-100 % bez toho, aby sme vytlačili jeho kontrolu: "
                   "NÁHODNÝ päťslovný spúšťač dosiahne na tom istom fixture 65-90 % a naša vlastná sonda "
                   "má zapísané optimization_margin_over_random = 0.0. K tomu tri ďalšie obrany, ktoré "
                   "zomreli rovnako.",
        "date": "2026-07-30", "modified": "2026-07-30",
        "tags": "AI agents · Memory · Security · Poisoning · Negative results · Controls · inspeximus",
        "tags_sk": "AI agenti · Pamäť · Bezpečnosť · Poisoning · Negatívne výsledky · Kontroly · inspeximus",
        "kicker": "Security · negative results", "kicker_sk": "Bezpečnosť · negatívne výsledky",
    },
    "memory-defense-veracity-gap": {
        "slug": "agent-memory-defense-provenance-not-truth",
        "title": "Agent memory poisoning: provenance can't buy truth",
        "title_sk": "Otrava pamäte agenta: proveniencia nekúpi pravdu",
        "desc": "An adaptive attacker beats four AI-agent memory defenses: every content-only signal falls, "
                "and provenance authenticates the source, not the truth.",
        "desc_sk": "Adaptívny útočník porazí štyri obrany pamäte AI agenta: každý iba-obsahový signál padne "
                   "a proveniencia overuje zdroj, nie pravdu.",
        "date": "2026-07-05", "modified": "2026-07-05",
        "tags": "AI agents · Memory · Security · Poisoning · inspeximus · Provenance",
        "tags_sk": "AI agenti · Pamäť · Bezpečnosť · Poisoning · inspeximus · Proveniencia",
        "kicker": "Agent memory security", "kicker_sk": "Bezpečnosť pamäte agentov",
    },
    "agent-memory-poisoning-influence-gate": {
        "slug": "agent-memory-poisoning-influence-gate",
        "title": "One Plain Sentence Hijacks AI-Agent Memory Retrieval — and the Fix Isn't a Better Retriever",
        "title_sk": "Jedna obyčajná veta unesie retrieval pamäte AI agenta — a riešením nie je lepší retriever",
        "desc": "One poisoned memory with a plain-English trigger hijacks AI-agent retrieval 88–100%, even "
                "at 10k. Gating influence by corroboration drops it to 0%.",
        "desc_sk": "Jedna otrávená spomienka s triggerom z obyčajnej vety unesie retrieval AI agenta na "
                   "88–100% aj pri 10k. Gejtovanie vplyvu korroboráciou ho zrazí na 0%.",
        "date": "2026-07-02", "modified": "2026-07-02",
        "tags": "AI agents · Memory · Security · Poisoning · inspeximus",
        "tags_sk": "AI agenti · Pamäť · Bezpečnosť · Poisoning · inspeximus",
        "kicker": "Agent memory security", "kicker_sk": "Bezpečnosť pamäte agentov",
    },
    "agent-memory-retrieval": {
        "slug": "agent-memory-retrieval-bm25-vector-hybrid",
        "title": "Agent-memory retrieval, measured: recency 0.024, a vector DB ties BM25, the cheap hybrid wins",
        "title_sk": "Retrieval pre agent memory, odmerané: recency 0,024, vector DB len remizuje s BM25, lacný hybrid vyhráva",
        "desc": "We benchmarked 6 self-hostable retrievers for AI agent memory on LoCoMo. Recency (the "
                "'last-N' default) scored 0.024 recall@20; a vector DB didn't beat zero-dependency BM25 (a tie); "
                "the cheap BM25+embedder hybrid won.",
        "desc_sk": "Odmerali sme 6 self-hostovateľných retrieverov pre pamäť AI agentov na LoCoMo. Recency "
                   "(default 'posledných N') dosiahol 0,024 recall@20; samotný vektorový index neporazil "
                   "zero-dependency BM25 (remíza); lacný BM25+embedder hybrid vyhral.",
        "date": "2026-06-30", "modified": "2026-06-30",
        "tags": "AI agents · Memory · Retrieval · BM25 vs vector · Hybrid",
        "tags_sk": "AI agenti · Pamäť · Retrieval · BM25 vs vektory · Hybrid",
        "kicker": "AI agent memory", "kicker_sk": "Pamäť AI agentov",
    },
    "pre-trends": {
        "slug": "pre-trends-test-weak-evidence",
        "title": "Passing a Pre-Trends Test Is Weak Evidence — We Measured It",
        "title_sk": "Prejsť testom pre-trendov je slabý dôkaz — odmerali sme to",
        "desc": "A difference-in-differences pre-trends test catches only about one in six of the "
                "violations that ruin your estimate (it misses ~5 of 6). Measured, with the simulation and the falsifier.",
        "desc_sk": "Test pre-trendov v difference-in-differences zachytí len asi jedno zo šiestich porušení, "
                   "ktoré zničia tvoj odhad (prehliadne ~5 zo 6). Odmerané, so simuláciou aj falzifikátorom.",
        "date": "2026-06-11", "modified": "2026-06-30",
        "tags": "Causal inference · Difference-in-differences · Parallel trends",
        "tags_sk": "Kauzálna inferencia · Difference-in-differences · Paralelné trendy",
        "kicker": "Causal inference", "kicker_sk": "Kauzálna inferencia",
    },
    "ai-coding-productivity-operating-point": {
        "slug": "ai-coding-productivity-operating-point",
        "title": "The “55% Faster” AI Coding Claim Is an Operating-Point Trap",
        "title_sk": "Tvrdenie „55% rýchlejšie“ o AI kódení je operating-point trap",
        "desc": "The famous '55% faster' AI coding number is a vendor preprint on one greenfield task; the "
                "only independent RCT on experienced devs found -19%. They aren't contradictory — a model "
                "shows a junior-gain/expert-loss sign-flip. The universal claim fails. Verified, with the falsifier.",
        "desc_sk": "Slávnych '55% faster' o AI kódení je vendor preprint na jednom greenfield tasku; jediný "
                   "nezávislý RCT na skúsených devoch našiel -19%. Nie sú v spore — model ukazuje junior-zisk/"
                   "expert-strata sign-flip. Univerzálny claim zlyháva. Overené, s falzifikátorom.",
        "date": "2026-06-29", "modified": "2026-07-23",
        "tags": "AI · Future of Work · Developer productivity · Replication",
        "tags_sk": "AI · Future of Work · Produktivita vývojárov · Replikácia",
        "kicker": "The Crucible", "kicker_sk": "Crucible",
    },
    "chatbot-arena-style-not-skill": {
        "slug": "chatbot-arena-style-not-skill",
        "title": "How Much of Chatbot Arena Is Style? The Votes Are Biased; the Order Mostly Isn't",
        "title_sk": "Koľko z Chatbot Areny je štýl? Hlasy sú zaujaté; poradie väčšinou nie",
        "desc": "Two tests on real Arena votes. At the vote level style is a real bias: a style-only judge "
                "(no model identity) predicts the winner 61.5%, and the longer answer wins ~62% even between "
                "the same two models. But at the leaderboard level style mostly isn't ranked: the style-only "
                "ρ=0.74 is a correlational ceiling, and LMSYS's style-controlled Elo reorders only modestly.",
        "desc_sk": "Dva testy na reálnych Arena hlasoch. Na úrovni hlasov je štýl reálny bias: style-only "
                   "sudca (bez identity modelu) predpovedá víťaza 61,5% a dlhšia odpoveď vyhráva ~62% aj medzi "
                   "tými istými modelmi. Ale na úrovni leaderboardu sa štýl väčšinou nehodnotí: ρ=0,74 je "
                   "korelačný strop a LMSYS style-controlled Elo reorderuje len mierne.",
        "date": "2026-06-29",
        "tags": "AI evaluation · Chatbot Arena · Verbosity bias · Confound vs proxy · Replication",
        "tags_sk": "AI hodnotenie · Chatbot Arena · Verbosity bias · Confound vs proxy · Replikácia",
        "kicker": "The Crucible", "kicker_sk": "Crucible",
    },
    "verifiable-agent-receipts": {
        "slug": "verifiable-agent-receipts",
        "title": "AI Agent MCP Receipts: Your Logs Aren't Proof",
        "title_sk": "Účtenky pre MCP volania AI agentov: logy nie sú dôkaz",
        "desc": "An AI agent's logs are self-reported claims. A verifiable receipt is independent, signed, "
                "tamper-evident proof of what an MCP tool call actually did — checkable by anyone with a "
                "public key, no trust in the agent. We built the smallest runnable version and mapped the field.",
        "desc_sk": "Logy AI agenta sú self-reported tvrdenia. Overiteľná účtenka je nezávislý, podpísaný, "
                   "tamper-evident dôkaz toho, čo MCP volanie nástroja naozaj urobilo — overiteľný hocikým s "
                   "verejným kľúčom, bez dôvery v agenta. Postavili sme najmenšiu spustiteľnú verziu a zmapovali pole.",
        "date": "2026-06-29",
        "tags": "AI agents · MCP · verifiable receipts · cryptography · agent security",
        "tags_sk": "AI agenti · MCP · overiteľné účtenky · kryptografia · bezpečnosť agentov",
        "kicker": "Build", "kicker_sk": "Build",
    },
    "founder-led-survivorship-null": {
        "slug": "founder-led-survivorship-null",
        "title": "Founder-Led Firms' 3.1× Edge: How Much Is Survivorship, How Much Is Real",
        "title_sk": "Náskok 3,1× founder firiem: koľko je survivorship a koľko je reálne",
        "desc": "Bain's founder-led 3.1× is built on current index membership, so survivorship can inflate "
                "it a lot — a zero-skill null reproduces 26–179% of it depending on an unmeasured volatility "
                "assumption. But it doesn't dispose of the question: a controlled study (Fahlenbrach 2009) "
                "finds a real ~+4.4%/yr founder-CEO alpha. Inflated raw number, smaller real premium.",
        "desc_sk": "Bainov founder 3,1× je postavený na súčasnom členstve v indexe, takže survivorship ho vie "
                   "poriadne nafúknuť — zero-skill null reprodukuje 26–179% podľa nemeraného predpokladu "
                   "volatility. Ale nevybavuje otázku: kontrolovaná štúdia (Fahlenbrach 2009) nachádza reálnu "
                   "~+4,4%/rok founder-CEO alfu. Nafúknuté surové číslo, menšie reálne premium.",
        "date": "2026-06-29",
        "tags": "Management · Survivorship bias · Founder premium · Replication",
        "tags_sk": "Manažment · Survivorship bias · Founder premium · Replikácia",
        "kicker": "The Crucible", "kicker_sk": "Crucible",
    },
    "llm-as-judge-length-confound": {
        "slug": "llm-as-judge-length-confound",
        "title": "We Tried to Debunk LLM-as-Judge as a Length Trick. Our Own Control Refuted It.",
        "title_sk": "Skúsili sme debunknúť LLM-as-judge ako trik s dĺžkou. Náš vlastný test nás vyvrátil.",
        "desc": "A length-only null recovers half of GPT-4's above-chance agreement with humans on MT-Bench "
                "(68% vs 86%), which looks like a verbosity confound. But our pre-registered control — "
                "length-matched pairs — refuted it: with length neutralized, GPT-4 still agrees ~80% while "
                "the null drops to chance. The agreement is largely semantic. A debunk that debunked itself.",
        "desc_sk": "Length-only null obnoví polovicu nadnáhodného súhlasu GPT-4 s ľuďmi na MT-Bench (68% vs "
                   "86%), čo vyzerá ako verbosity confound. Ale naša predregistrovaná kontrola — length-matched "
                   "páry — to vyvrátila: pri neutralizovanej dĺžke GPT-4 stále súhlasí ~80%, kým null padne na "
                   "náhodu. Súhlas je z veľkej časti sémantický. Debunk, čo zdebunkoval sám seba.",
        "date": "2026-06-29",
        "tags": "AI evaluation · LLM-as-judge · Verbosity bias · Self-correction · Replication",
        "tags_sk": "AI hodnotenie · LLM-as-judge · Verbosity bias · Sebaoprava · Replikácia",
        "kicker": "The Crucible", "kicker_sk": "Crucible",
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
    "verify-agent-memory-deletion": {
        "slug": "verify-agent-memory-deletion",
        "title": "Verify AI agent memory deletion: can you prove it is gone?",
        "title_sk": "Overenie mazania v agentovej pamäti: vieš dokázať, že je preč?",
        "desc": "Your agent's delete() returns success - that does not mean the data left. Run a free "
                "self-check on your own store and see what your delete really removed.",
        "desc_sk": "delete() tvojho agenta vráti úspech - to neznamená, že dáta odišli. Spusti si voľnú "
                   "kontrolu na vlastnom úložisku a zisti, čo tvoje mazanie naozaj odstránilo.",
        "date": "2026-08-01",
        "tags": "Agent memory · GDPR Article 17 · Right to erasure · Verification",
        "tags_sk": "Agentová pamäť · GDPR článok 17 · Právo na vymazanie · Overovanie",
        "kicker": "Tools", "kicker_sk": "Nástroje",
    },
    "food-nudges-publication-bias": {
        "slug": "food-nudges-publication-bias",
        "title": "Food Nudges Aren't 2.5× Better — Food Is the Small-Study Domain",
        "title_sk": "Food nudge nie je 2,5× účinnejší — jedlo je len doména malých štúdií",
        "desc": "A famous PNAS meta-analysis ranked food the most nudgeable domain (~2.7× the lowest). "
                "In the authors' own data food is by far the smallest-study domain (~113 vs ~861+ "
                "participants) — a size gap that reproduces the whole ratio from zero true difference. "
                "The honest twist: small-study fragility, not proven publication bias. Runnable.",
        "desc_sk": "Slávna PNAS meta-analýza označila jedlo za najnudge-ovateľnejšiu doménu (~2,7× nad "
                   "najnižšou). V dátach autorov je jedlo zďaleka doména najmenších štúdií (~113 vs "
                   "~861+ účastníkov) — asymetria, ktorá reprodukuje celý pomer z nulového rozdielu. "
                   "Poctivý zvrat: small-study krehkosť, nie preukázaný publikačný bias. Spustiteľné.",
        "date": "2026-06-29",
        "tags": "Behavioral economics · Nudging · Publication bias · Replication",
        "tags_sk": "Behaviorálna ekonómia · Nudging · Publikačný bias · Replikácia",
        "kicker": "The Crucible", "kicker_sk": "Crucible",
    },
    "phase-diagram": {
        "slug": "causal-inference-phase-diagram",
        "title": "Spillovers Don't Bias Your Experiment — They Change the Estimand",
        "title_sk": "Spillovery nezaujatkujú experiment — menia estimand",
        "desc": "When units interfere, a randomized difference-in-means doesn't break — it consistently "
                "estimates the TOTAL effect, not the direct one, and the gap grows with coupling (to ~96% of "
                "the direct effect near criticality). The fix: choose your estimand and a design that targets it. Corrected re-publication.",
        "desc_sk": "Keď jednotky interferujú, randomizovaný difference-in-means sa nerozbije — konzistentne "
                   "meria TOTAL efekt, nie priamy, a rozdiel rastie s previazanosťou (~96% priameho efektu pri "
                   "kriticite). Oprava: vyber estimand a dizajn, ktorý naň mieri. Opravená re-publikácia.",
        "date": "2026-06-10", "modified": "2026-06-29",
        "tags": "Causal inference · Interference · Estimand · Spillovers",
        "tags_sk": "Kauzálna inferencia · Interferencia · Estimand · Spillovery",
        "kicker": "Causal inference", "kicker_sk": "Kauzálna inferencia",
    },
    "reality-check-ai-memory-method-wins": {
        "slug": "reality-check-ai-memory-method-wins",
        "title": "A reality-check for AI-memory ‘method wins’: four of ours were resource confounds",
        "title_sk": "Reality-check pre „method wins“ v AI pamäti: štyri naše boli resource confoundy",
        "desc": "Four AI-memory ‘method wins’ were resource confounds: a norm re-ranker was length "
                "(norm−length CI crosses 0), a decomposition gain was tokens (Δ=0 at matched compute). The "
                "reality-check — variance, compute-match, proxy — plus a runnable helper and public receipts.",
        "desc_sk": "Štyri „method wins“ v AI pamäti boli resource confoundy: norm re-ranker bola dĺžka "
                   "(norma−dĺžka CI cez 0), zisk dekompozície boli tokeny (Δ=0 pri matchnutom compute). "
                   "Reality-check — variancia, compute-match, proxy — plus bežateľný helper a verejné receipty.",
        "date": "2026-07-03", "modified": "2026-07-03",
        "tags": "AI memory · RAG · Reality check · Strong baselines · inspeximus",
        "tags_sk": "AI pamäť · RAG · Reality check · Strong baselines · inspeximus",
        "kicker": "Method-win reality check", "kicker_sk": "Reality-check method-wins",
    },
    "agent-memory-poisoning-layered-defense-residual": {
        "slug": "agent-memory-poisoning-layered-defense-residual",
        "title": "A reality-check on agent-memory poisoning defenses: you price the residual, you don't close it",
        "title_sk": "Reality-check pre obrany proti otrave pamäte agentov: rezíduum oceníš, nezavrieš",
        "desc": "Layered defenses against agent-memory poisoning don't multiply into a wall. Four composition "
                "claims verified against the dependability, Sybil and change-point literature — all correct and "
                "all textbook — leave a priced, appealable residual on top of provenance that survives "
                "transformation. Plus five shipped inspeximus primitives, each limit in the code.",
        "desc_sk": "Vrstvené obrany proti otrave pamäte agentov sa nevynásobia do steny. Štyri kompozičné "
                   "tvrdenia overené proti literatúre spoľahlivosti, Sybil a change-point — všetky správne a "
                   "učebnicové — nechávajú oceniteľné, odvolateľné rezíduum nad provenance, čo prežije "
                   "transformáciu. Plus päť shipnutých inspeximus primitív, každý limit v kóde.",
        "date": "2026-07-04", "modified": "2026-07-04",
        "tags": "Agent memory · Memory poisoning · Security · Sybil · inspeximus",
        "tags_sk": "Pamäť agentov · Otrava pamäte · Bezpečnosť · Sybil · inspeximus",
        "kicker": "Agent memory security", "kicker_sk": "Bezpečnosť pamäte agentov",
    },
}

_STAT = re.compile(r"^[+\-−]?[\d.,\s]+(?:%|×|x|SD|σ)?$|^\d+[\s,]*(?:[–-]\s*\d+)?\s*%$")
_MONS = ["", "January", "February", "March", "April", "May", "June", "July", "August",
         "September", "October", "November", "December"]
#: Slovak months in the GENITIVE, which is the case a day-first date takes ("1. augusta 2026").
#: The nominative ("august") is wrong here and reads as a typo to a Slovak reader.
_MONS_SK = ["", "januára", "februára", "marca", "apríla", "mája", "júna", "júla", "augusta",
            "septembra", "októbra", "novembra", "decembra"]


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
    datehuman_sk = f"{int(d)}. {_MONS_SK[int(mo)]} {y}"
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
         # PARITY: the deployed pages carry all eight. The renderer emitted three, so re-running it
         # silently stripped the inspeximus / PyPI / Zenodo-DOI entity links from every post.
         "sameAs": ["https://github.com/DanceNitra/agora",
                    "https://huggingface.co/Danchi17",
                    "https://github.com/DanceNitra/ramr",
                    "https://github.com/DanceNitra/inspeximus",
                    "https://pypi.org/project/inspeximus/",
                    "https://dancenitra.github.io/inspeximus/",
                    "https://dancenitra.github.io/",
                    "https://doi.org/10.5281/zenodo.21648053"]},
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
        kicker=m["kicker"], kicker_sk=kicker_sk, datehuman=datehuman, datehuman_sk=datehuman_sk, read=read,
        tags=m["tags"], tags_sk=tags_sk,
        tldr=html.escape(m["desc"]), tldr_sk=html.escape(desc_sk),
        body=body_en, body_sk=body_sk, foot=foot_en, foot_sk=foot_sk)
    dest = ROOT / "public" / "posts" / f"{m['slug']}.html"
    dest.write_text(out, encoding="utf-8")
    # ONE URL PER LANGUAGE. This template emits both languages into one document, CSS-toggled -- which is
    # what put the two languages into one extracted text blob, gave hreflang two annotations pointing at
    # the same URL, and left every Slovak element declared lang="en". The site was split on 2026-07-28
    # (EN in place, SK under /agora/sk/); without this call the very next post rendered would reintroduce
    # the bilingual document the split removed, one page at a time and unnoticed.
    if bilingual:
        try:
            import split_languages
            split_languages.split_one(dest)
        except Exception as e:                                    # never fail a render over the mirror
            print(f"  [warn] SK mirror not written for {m['slug']}: {type(e).__name__}: {e}")
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
<link rel="icon" type="image/png" href="data:image/png;base64,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">
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
<style>@font-face{{font-family:"Newsreader-fallback";src:local("Georgia"),local("Times New Roman");size-adjust:95.18%;ascent-override:77.22%;descent-override:27.84%;line-gap-override:0%}}
  :root{{--paper:#fbf9f4;--paper2:#f4f1ea;--ink:#1b1a17;--soft:#54514a;--faint:#8c887e;
    --line:#e6e1d6;--acc:#0a8f68;--acc-soft:#e3f4ed;--hl:#fff4cc;
    --serif:"Newsreader","Newsreader-fallback",Georgia,"Times New Roman",serif;--mono:"JetBrains Mono",ui-monospace,Menlo,Consolas,monospace;}}
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
  /* split_languages.py rewrites the button pair into <a hreflang> links once there is one language
     per document. The rules above only ever matched <button>, so after the split the toggle lost its
     padding (EN and SK rendered flush as "ENSK") and the active-language highlight never appeared on
     any post. Two tools each correct, nobody owning the seam between them. */
  .lng a{{font-family:var(--mono);font-size:11.5px;letter-spacing:.06em;padding:6px 12px;
    color:var(--soft);text-decoration:none;border:0;line-height:1}}
  .lng a+a{{border-left:1px solid var(--line)}}
  .lng a.on{{background:var(--acc);color:#fff}}
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
  <div class="meta"><span class="en">{datehuman}</span><span class="sk">{datehuman_sk}</span><span class="en">{read} min read</span><span class="sk">{read} min čítania</span><span class="en">{tags}</span><span class="sk">{tags_sk}</span></div>
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
<link rel="icon" type="image/png" href="data:image/png;base64,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">
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
<style>@font-face{{font-family:"Newsreader-fallback";src:local("Georgia"),local("Times New Roman");size-adjust:95.18%;ascent-override:77.22%;descent-override:27.84%;line-gap-override:0%}}
  :root{{--paper:#fbf9f4;--paper2:#f4f1ea;--ink:#1b1a17;--soft:#54514a;--faint:#8c887e;
    --line:#e6e1d6;--acc:#0a8f68;--acc-soft:#e3f4ed;--hl:#fff4cc;
    --serif:"Newsreader","Newsreader-fallback",Georgia,"Times New Roman",serif;--mono:"JetBrains Mono",ui-monospace,Menlo,Consolas,monospace;}}
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
  /* split_languages.py rewrites the button pair into <a hreflang> links once there is one language
     per document. The rules above only ever matched <button>, so after the split the toggle lost its
     padding (EN and SK rendered flush as "ENSK") and the active-language highlight never appeared on
     any post. Two tools each correct, nobody owning the seam between them. */
  .lng a{{font-family:var(--mono);font-size:11.5px;letter-spacing:.06em;padding:6px 12px;
    color:var(--soft);text-decoration:none;border:0;line-height:1}}
  .lng a+a{{border-left:1px solid var(--line)}}
  .lng a.on{{background:var(--acc);color:#fff}}
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
    lead_date_sk = f"{int(d)}. {_MONS_SK[int(mo)]} {y}"
    f = entries[0]
    feature = f"""<a class="feature wrap" href="{f['slug']}.html">
  <div class="ftag"><span class="en">Latest</span><span class="sk">Najnovšie</span></div>
  <h2><span class="en">{html.escape(f['title'])}</span><span class="sk">{html.escape(f['title_sk'])}</span></h2>
  <p class="ex"><span class="en">{html.escape(f['desc'])}</span><span class="sk">{html.escape(f['desc_sk'])}</span></p>
  <div class="meta"><span class="en">{lead_date}</span><span class="sk">{lead_date_sk}</span><span class="en">{f['read']} min read</span><span class="sk">{f['read']} min čítania</span><span class="en">{html.escape(f['tags'])}</span><span class="sk">{html.escape(f['tags_sk'])}</span></div>
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
