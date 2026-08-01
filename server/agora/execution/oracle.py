"""
The Oracle — skin in the game.

Every metric so far was a proxy the system grades itself on. The Oracle ends that: Agora
reads LIVE prediction markets (Polymarket Gamma, public, no auth), forms its OWN independent
probability with its research engine, logs the EDGE against the market price as a paper
position — and when the market resolves, it is scored by Brier against hard reality, head to
head with the market. Calibration against truth that does not belong to the system.
"""
from __future__ import annotations

import json
import re
import time
import urllib.request
from pathlib import Path

_STORE = Path(__file__).resolve().parents[2] / ".oracle.json"
_GAMMA = "https://gamma-api.polymarket.com/markets"
# the owner's domains — markets must match one of these to be considered
# Only markets where Agora's knowledge base gives a genuine ANALYTICAL edge — AI / technology /
# science / research outcomes. Deliberately EXCLUDES efficient crypto + macro-finance price markets
# (bitcoin, Fed, inflation, S&P): forecasting those is gambling against an efficient crowd, which is
# exactly why our first rigorous calls went 0/3 vs the market. Edge, not volume, builds a credible record.
_DOMAIN_RX = re.compile(
    r"\b(AI|AGI|GPT|OpenAI|Anthropic|Claude|Gemini|Llama|Grok|LLM|model|benchmark|"
    r"chip|GPU|NVIDIA|semiconductor|robot|robotaxi|self[- ]?driving|autonomous|agent|"
    r"SpaceX|rocket|NASA|fusion|quantum|superconduct|vaccine|FDA|clinical|drug|"
    r"Nobel|breakthrough|open[- ]?source|research|paper|reproduc|dataset)\b", re.I)


def _load() -> list:
    try:
        return json.loads(_STORE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(items: list) -> None:
    try:
        _STORE.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def _get(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "agora-oracle/1.0"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read())


def fetch_candidates(pages: int = 5, max_days: int = 120) -> list[dict]:
    """Open, liquid, in-domain, binary markets resolving within the horizon. The Gamma API
    caps at 100/page, so paginate — informative markets live deeper than the top of the book."""
    markets = []
    for off in range(0, pages * 100, 100):
        try:
            markets += _get(f"{_GAMMA}?closed=false&limit=100&offset={off}"
                            f"&order=volume24hr&ascending=false") or []
        except Exception:
            break
    held = {p.get("market_id") for p in _load()}
    out = []
    now = time.time()
    for m in markets or []:
        q = (m.get("question") or "").strip()
        if not q or m.get("id") in held or not _DOMAIN_RX.search(q):
            continue
        try:
            prices = json.loads(m.get("outcomePrices") or "[]")
            outcomes = json.loads(m.get("outcomes") or "[]")
            yes_i = outcomes.index("Yes")
            market_prob = float(prices[yes_i])
        except Exception:
            continue
        if not (0.03 <= market_prob <= 0.97):
            continue                                   # near-settled: no information in a call
        end = m.get("endDate") or ""
        try:
            ends_ts = time.mktime(time.strptime(end[:19], "%Y-%m-%dT%H:%M:%S"))
        except Exception:
            continue
        if not (now < ends_ts < now + max_days * 86400):
            continue
        out.append({"market_id": m.get("id"), "question": q[:200],
                    "market_prob": round(market_prob, 4), "ends": end[:10],
                    "volume24h": round(float(m.get("volume24hr") or 0))})
    return out[:10]


def record_call(market_id: str, question: str, market_prob: float, ends: str,
                agora_prob: float, reasoning: str) -> dict:
    """Log Agora's independent probability as a paper position; the edge is the thesis."""
    p = max(0.01, min(0.99, float(agora_prob)))
    rec = {"id": str(market_id), "market_id": str(market_id), "question": question[:200],
           "market_prob": round(float(market_prob), 4), "agora_prob": round(p, 4),
           "edge": round(p - float(market_prob), 4),
           "side": "YES" if p > market_prob else "NO",
           "reasoning": (reasoning or "")[:400], "ends": ends,
           "ts": time.time(), "status": "open"}
    items = _load()
    items.append(rec)
    _save(items[-100:])
    return rec


def _who_serves(url: str) -> str:
    """The subject of the certificate the host actually presents, for diagnosis only.

    Verification is deliberately OFF here and this value is NEVER used to decide whether to trust
    anything -- it is read, recorded and shown to a human. It exists because the failure message
    ("certificate verify failed") named the symptom and sent the reader to the certificate store,
    while the certificate itself named a DNS content filter blocking the domain.
    """
    import socket as _sock
    import ssl as _ssl
    from urllib.parse import urlparse as _urlparse
    host = _urlparse(url).hostname or ""
    if not host:
        return ""
    try:
        ctx = _ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = _ssl.CERT_NONE          # inspection only; nothing is trusted on this path
        with _sock.create_connection((host, 443), timeout=10) as sk:
            with ctx.wrap_socket(sk, server_hostname=host) as ss:
                der = ss.getpeercert(binary_form=True)
    except Exception as e:
        return "could not read the served certificate (%s)" % type(e).__name__
    try:                                          # decode without a hard dependency on cryptography
        import re as _re
        txt = der.decode("latin-1")
        cn = _re.findall(r"[ -~]{6,}", txt)
        pick = [c for c in cn if "." in c or c.isalpha()]
        return " | ".join(pick[-6:])[:200]
    except Exception:
        return "certificate served but not decodable"


#: Why the last resolve pass could not score the open book. Read by the endpoint so an UNREACHABLE
#: market is never reported as an unresolved one.
LAST_RESOLVE_DIAG: dict = {"checked": 0, "unreachable": 0, "still_open": 0, "unparseable": 0,
                           "overdue_unreachable": 0, "errors": []}


def resolve_open() -> list[dict]:
    """Check open positions against the market; score resolved ones by Brier, vs the market.

    EVERY FAILURE PATH USED TO BE A SILENT `continue`, so a network error, a changed response shape
    and a market that has simply not closed yet were indistinguishable from outside: the endpoint
    answered `resolved: 0` for all three and King Aldric reported an honest-looking idle.

    Measured 2026-08-01: all 7 overdue positions fail with
    `SSL: CERTIFICATE_VERIFY_FAILED -- self-signed certificate in certificate chain`.

    THE BLOCKER IS NAMED, because "TLS is broken" was the wrong diagnosis and nearly shipped as the
    right one. Python HTTPS on this machine is fine: api.github.com, export.arxiv.org and
    api.openalex.org all return 200 from the same interpreter in the same second. Only Polymarket
    fails, and reading the certificate it actually serves says why:

        CN=sad.certificate.that.cannot.be.valid.com, O=Whalebone, L=Brno, C=CZ

    Whalebone is a DNS-level content filter, and that CN is its block page. api.github.com gets a
    genuine Sectigo certificate over the same connection path. So this is not a machine-wide
    interception and not a certificate-store problem: something on the network is blocking
    polymarket.com by category. It is fixed by allow-listing the domain in that filter -- an owner
    decision -- or by retiring the Oracle. It is NOT fixed by disabling certificate verification,
    which would make a number appear while turning the check into decoration.

    What is fixed HERE is our blindness. Seven forecasts sat past their end date, unscoreable and
    unreported, while every dashboard showed an empty queue.
    """
    items = _load()
    resolved = []
    diag = {"checked": 0, "unreachable": 0, "still_open": 0, "unparseable": 0,
            "overdue_unreachable": 0, "errors": []}
    today = time.strftime("%Y-%m-%d")
    for p in items:
        if p.get("status") != "open":
            continue
        diag["checked"] += 1
        overdue = bool(p.get("ends")) and str(p.get("ends")) < today
        try:
            m = _get(f"{_GAMMA}/{p['market_id']}")
        except Exception as e:
            diag["unreachable"] += 1
            diag["overdue_unreachable"] += 1 if overdue else 0
            msg = "%s: %s" % (type(e).__name__, str(e)[:90])
            if msg not in diag["errors"]:
                diag["errors"].append(msg)
            # NAME THE BLOCKER RATHER THAN THE SYMPTOM. "certificate verify failed" was read as a
            # broken machine; the certificate actually served identifies a DNS content filter
            # blocking the domain, while every other HTTPS host on the same interpreter answers 200.
            # A diagnostic that reports the symptom sends the reader to the wrong repair.
            if not diag.get("served_by") and "CERTIFICATE_VERIFY" in str(e).upper():
                diag["served_by"] = _who_serves(_GAMMA)
            continue
        if not (m.get("closed") or m.get("umaResolutionStatus") == "resolved"):
            diag["still_open"] += 1
            continue
        try:
            prices = json.loads(m.get("outcomePrices") or "[]")
            outcomes = json.loads(m.get("outcomes") or "[]")
            final_yes = float(prices[outcomes.index("Yes")])
        except Exception as e:
            diag["unparseable"] += 1
            msg = "outcome parse %s: %s" % (type(e).__name__, str(e)[:70])
            if msg not in diag["errors"]:
                diag["errors"].append(msg)
            continue
        outcome = 1.0 if final_yes > 0.5 else 0.0
        p["status"] = "resolved"
        p["outcome"] = outcome
        p["brier_agora"] = round((p["agora_prob"] - outcome) ** 2, 4)
        p["brier_market"] = round((p["market_prob"] - outcome) ** 2, 4)
        p["beat_market"] = p["brier_agora"] < p["brier_market"]
        p["resolved_ts"] = time.time()
        resolved.append(p)
    if resolved:
        _save(items)
    LAST_RESOLVE_DIAG.clear()
    LAST_RESOLVE_DIAG.update(diag)
    return resolved


def scorecard() -> dict:
    done = [p for p in _load() if p.get("status") == "resolved"]
    if not done:
        return {"resolved": 0}
    ba = sum(p["brier_agora"] for p in done) / len(done)
    bm = sum(p["brier_market"] for p in done) / len(done)
    return {"resolved": len(done), "brier_agora": round(ba, 4), "brier_market": round(bm, 4),
            "beat_market": sum(1 for p in done if p["beat_market"])}


def format_oracle(n: int = 8) -> str:
    items = _load()
    if not items:
        return "🔮 _No oracle positions yet._"
    sc = scorecard()
    head = f"🔮 *The Oracle* — {len([p for p in items if p['status'] == 'open'])} open positions"
    if sc.get("resolved"):
        head += (f" · resolved {sc['resolved']}: Brier {sc['brier_agora']} vs market "
                 f"{sc['brier_market']} ({sc['beat_market']} beat)")
    lines = [head]
    for p in items[-n:]:
        mark = "⏳" if p["status"] == "open" else ("🏆" if p.get("beat_market") else "📉")
        lines.append(f"{mark} {p['question'][:64]}")
        lines.append(f"   market {p['market_prob']:.0%} | agora {p['agora_prob']:.0%} "
                     f"(edge {p['edge']:+.0%}, {p['side']}) · ends {p['ends']}")
    return "\n".join(lines)
