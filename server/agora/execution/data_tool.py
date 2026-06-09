"""
Reality Bridge — ground ideas in REAL-WORLD DATA, not just papers.

Agora's research grounds claims in academic literature (arXiv/OpenAlex). This wires in live, free,
no-auth public data sources so a claim can be tested against ACTUAL data: how much a topic is really
discussed (Hacker News), the established facts (Wikipedia), real development/economic statistics
(World Bank), live crypto markets (CoinGecko). The flow per claim: ROUTE (which source + query) →
FETCH (real data) → JUDGE (does the data support it?). This is empirical IDEAOGENESIS — hypotheses
checked against reality, the natural next step from "agents as scientists" (test vs literature) to
"agents that measure the world".
"""
from __future__ import annotations

import asyncio
import json
import re
import urllib.parse
import urllib.request

_UA = {"User-Agent": "Agora-RealityBridge/1.0 (research agent)"}


def _get_json(url: str, timeout: int = 15):
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


# ── Data sources (all free, no auth) ───────────────────────────────────────

def fetch_hackernews(query: str, n: int = 6, **_) -> dict:
    """Real signal on how much + how strongly a (tech) topic is discussed."""
    url = (f"https://hn.algolia.com/api/v1/search?query={urllib.parse.quote(query)}"
           f"&tags=story&hitsPerPage={n}")
    d = _get_json(url)
    hits = d.get("hits", [])
    top = [{"title": h.get("title"), "points": h.get("points"), "comments": h.get("num_comments"),
            "date": (h.get("created_at") or "")[:10]} for h in hits if h.get("title")]
    return {"source": "Hacker News", "total_stories_ever": d.get("nbHits", 0), "top": top}


def fetch_wikipedia(query: str, **_) -> dict:
    """The established factual summary of a concept/entity (does it exist; what is it)."""
    title = urllib.parse.quote(query.strip().replace(" ", "_"))
    try:
        d = _get_json(f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}")
        return {"source": "Wikipedia", "title": d.get("title"), "exists": d.get("type") == "standard",
                "extract": (d.get("extract") or "")[:600]}
    except Exception:
        return {"source": "Wikipedia", "exists": False, "extract": "(no Wikipedia article found)"}


_WB_INDICATORS = {
    "gdp": "NY.GDP.MKTP.CD", "gdp_per_capita": "NY.GDP.PCAP.CD", "population": "SP.POP.TOTL",
    "life_expectancy": "SP.DYN.LE00.IN", "co2_per_capita": "EN.ATM.CO2E.PC",
    "internet_users": "IT.NET.USER.ZS", "unemployment": "SL.UEM.TOTL.ZS",
    "renewable_energy": "EG.FEC.RNEW.ZS",
}


def fetch_worldbank(query: str, indicator: str = "gdp", country: str = "WLD", **_) -> dict:
    """Real development/economic statistics over time (world or a country)."""
    code = _WB_INDICATORS.get((indicator or "gdp").lower(), "NY.GDP.MKTP.CD")
    c = (country or "WLD").upper()[:3]
    try:
        d = _get_json(f"https://api.worldbank.org/v2/country/{c}/indicator/{code}"
                      f"?format=json&per_page=12&date=2008:2023")
        series = [{"year": x["date"], "value": x["value"]}
                  for x in (d[1] if isinstance(d, list) and len(d) > 1 and d[1] else [])
                  if x.get("value") is not None]
        return {"source": "World Bank", "indicator": indicator, "country": c,
                "series": list(reversed(series))[:10]}
    except Exception as e:
        return {"source": "World Bank", "indicator": indicator, "series": [], "error": str(e)[:80]}


def fetch_crypto(query: str, **_) -> dict:
    """Live cryptocurrency market data (price + 24h change) via CoinGecko."""
    try:
        s = _get_json(f"https://api.coingecko.com/api/v3/search?query={urllib.parse.quote(query)}")
        coins = s.get("coins", [])
        if not coins:
            return {"source": "CoinGecko", "found": False}
        cid = coins[0]["id"]
        p = _get_json(f"https://api.coingecko.com/api/v3/simple/price?ids={cid}"
                      f"&vs_currencies=usd&include_24hr_change=true&include_market_cap=true")
        d = p.get(cid, {})
        return {"source": "CoinGecko", "found": True, "coin": coins[0].get("name"),
                "price_usd": d.get("usd"), "change_24h_pct": d.get("usd_24h_change"),
                "market_cap_usd": d.get("usd_market_cap")}
    except Exception as e:
        return {"source": "CoinGecko", "found": False, "error": str(e)[:80]}


# Registry of routable sources. NOTE: fetch_crypto (CoinGecko) is intentionally NOT registered here —
# it works as code but CoinGecko's TLS chain fails to verify in this environment; re-add it once that
# is resolved (or behind a verified SSL context). The three below verify cleanly and cover trends,
# facts, and real statistics.
def fetch_github(query: str, **_) -> dict:
    """Real-world SOFTWARE adoption of a technology/idea — repo count + stars (is it actually built?)."""
    url = (f"https://api.github.com/search/repositories?q={urllib.parse.quote(query)}"
           f"&sort=stars&per_page=5")
    d = _get_json(url)
    top = [{"repo": i.get("full_name"), "stars": i.get("stargazers_count"),
            "desc": (i.get("description") or "")[:70]} for i in d.get("items", [])]
    return {"source": "GitHub", "total_repos": d.get("total_count", 0), "top": top}


def fetch_pubmed(query: str, **_) -> dict:
    """Volume of peer-reviewed BIOMEDICAL/life-science research on a topic (health, neuro, biology)."""
    url = (f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed"
           f"&term={urllib.parse.quote(query)}&retmode=json&retmax=3&sort=relevance")
    d = _get_json(url)
    er = d.get("esearchresult", {})
    return {"source": "PubMed", "paper_count": er.get("count", "0"),
            "sample_pmids": er.get("idlist", [])[:3]}


def fetch_restcountries(query: str, **_) -> dict:
    """Demographic/geographic facts about a country (population, region, area)."""
    try:
        d = _get_json(f"https://restcountries.com/v3.1/name/{urllib.parse.quote(query)}"
                      f"?fields=name,population,region,area,languages")
        c = d[0] if isinstance(d, list) and d else {}
        return {"source": "REST Countries", "country": (c.get("name") or {}).get("common"),
                "population": c.get("population"), "region": c.get("region"), "area_km2": c.get("area")}
    except Exception:
        return {"source": "REST Countries", "found": False}


def fetch_climate(query: str = "", **_) -> dict:
    """Real GLOBAL temperature/climate trend (NASA GISTEMP land anomaly) — for climate/warming claims."""
    try:
        d = _get_json("https://global-warming.org/api/temperature-api")
        res = d.get("result", [])
        if not res:
            return {"source": "Global Temperature (NASA GISTEMP)", "series": []}
        latest = res[-1]
        decade_ago = res[-121] if len(res) > 121 else res[0]
        return {"source": "Global Temperature (NASA GISTEMP)", "latest": latest,
                "ten_years_ago": decade_ago,
                "note": "land temperature anomaly (degrees C) vs the 1951-1980 baseline"}
    except Exception as e:
        return {"source": "Global Temperature", "error": str(e)[:80]}


def traction_check(topic: str, **_) -> dict:
    """Real-world TRACTION of a topic via Hacker News — is it actively discussed right now? Always
    returns a signal (the reliable fallback when a claim isn't directly testable): ACTIVE (lots of
    recent discussion), EMERGING (some), or DORMANT (little/none)."""
    d = fetch_hackernews(topic, n=20)
    top = d.get("top", [])
    total = d.get("total_stories_ever", 0)
    recent = sum(1 for h in top if (h.get("date") or "") >= "2023")
    points = sum((h.get("points") or 0) for h in top)
    if total >= 50 and recent >= 2:
        verdict = "ACTIVE"
    elif total >= 5:
        verdict = "EMERGING"
    else:
        verdict = "DORMANT"
    ev = (f"{total} Hacker News stories ever, {recent} of the top {len(top)} since 2023, "
          f"{points} combined points — real-world discussion of '{topic[:50]}'")
    return {"source": "Hacker News (traction)", "verdict": verdict, "evidence": ev,
            "mode": "traction", "data": d}


SOURCES = {
    "hackernews": ("how much + how strongly a tech/idea topic is actually discussed online "
                   "(real story counts, points, comments)", fetch_hackernews),
    "wikipedia": ("the established factual definition/summary of a concept or entity", fetch_wikipedia),
    "worldbank": ("real development/economic statistics over time — pick an indicator from "
                  + ", ".join(_WB_INDICATORS) + " and optionally a 3-letter country code (default WLD)",
                  fetch_worldbank),
    "github": ("real-world SOFTWARE adoption of a technology/tool/idea — how many repositories exist "
               "and their stars (is it actually built and used?)", fetch_github),
    "pubmed": ("the VOLUME of peer-reviewed biomedical / life-science / health / neuroscience research "
               "on a topic (how much real science backs it)", fetch_pubmed),
    "restcountries": ("demographic / geographic facts about a country (population, region, area)",
                      fetch_restcountries),
    "climate": ("real global temperature / climate-warming trend data (for any climate or global-"
                "warming claim)", fetch_climate),
}


def _compact(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False)[:1100]


async def empirical_test(claim: str) -> dict:
    """ROUTE → FETCH → JUDGE: test a claim against real-world data from a free public API."""
    from agora.execution.llm_client import call_llm

    catalog = "\n".join(f"- {k}: {desc}" for k, (desc, _) in SOURCES.items())
    route_raw = await asyncio.to_thread(
        call_llm,
        "You route a claim to ONE real-world data source that could empirically test it. Sources:\n"
        f"{catalog}\n\nReply ONLY JSON: "
        '{"source":"<key>","query":"<search/topic/coin>","indicator":"<worldbank only>","country":"<worldbank 3-letter, optional>"}.'
        " Choose the source whose live data most directly bears on the claim.",
        f"CLAIM: {claim[:300]}", "cheap", 0.2, 150) or ""
    m = re.search(r"\{.*\}", route_raw, re.DOTALL)
    route = {}
    if m:
        try:
            route = json.loads(m.group(0))
        except Exception:
            pass
    source = str(route.get("source", "")).lower().strip()
    if source not in SOURCES:
        source = "hackernews"                       # robust default — general-purpose signal
    query = str(route.get("query") or claim)[:120]

    desc, fn = SOURCES[source]
    data = await asyncio.to_thread(
        fn, query, indicator=route.get("indicator", "gdp"), country=route.get("country", "WLD"))

    verdict_raw = await asyncio.to_thread(
        call_llm,
        "Judge whether the REAL DATA below supports the CLAIM. Be empirical and specific — cite the "
        "actual numbers/facts from the data. Reply ONLY JSON "
        '{"verdict":"SUPPORTED|REFUTED|MIXED|INSUFFICIENT","evidence":"<one sentence citing the data>"}.',
        f"CLAIM: {claim[:300]}\n\nREAL DATA (from {data.get('source')}):\n{_compact(data)}",
        "cheap", 0.1, 200) or ""
    vm = re.search(r"\{.*\}", verdict_raw, re.DOTALL)
    verdict, evidence = "INSUFFICIENT", "no judgment returned"
    if vm:
        try:
            vd = json.loads(vm.group(0))
            verdict = str(vd.get("verdict", "INSUFFICIENT")).upper().strip()
            evidence = str(vd.get("evidence", ""))[:240]
        except Exception:
            pass
    if verdict not in ("SUPPORTED", "REFUTED", "MIXED", "INSUFFICIENT"):
        verdict = "INSUFFICIENT"
    if verdict == "INSUFFICIENT":
        # the claim isn't directly testable against this data → fall back to the topic's real-world
        # TRACTION (Hacker News always returns a signal), so every reality check yields something.
        tr = await asyncio.to_thread(traction_check, query)
        return {"claim": claim, "source": tr["source"], "query": query, "mode": "traction",
                "verdict": tr["verdict"], "evidence": tr["evidence"], "data": tr["data"]}
    return {"claim": claim, "source": data.get("source"), "query": query, "mode": "claim",
            "verdict": verdict, "evidence": evidence, "data": data}


def format_empirical(r: dict) -> str:
    icon = {"SUPPORTED": "✅", "REFUTED": "❌", "MIXED": "🟡", "INSUFFICIENT": "⚪",
            "ACTIVE": "🔥", "EMERGING": "🌱", "DORMANT": "💤"}
    kind = "real-world traction" if r.get("mode") == "traction" else "vs real data"
    lines = [f"🌐 *Reality check* — _{r['claim'][:120]}_\n",
             f"{icon.get(r['verdict'], '•')} *{r['verdict']}* ({kind}, {r['source']})",
             f"_{r['evidence']}_"]
    return "\n".join(lines)
