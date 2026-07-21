"""
THE EXAPTATION SCANNER — the OUTWARD turn (idea-forge run 001, idea #4).

Agora's research has been INWARD: arXiv + OpenAlex + the owner's vault. This organ turns it
OUTWARD. It is a two-sided engine:

    SUPPLY  = our PROVEN mechanisms (Lab-measured), abstracted to their structural invariant.
    DEMAND  = real unmet need in the live world (forums, Reddit, HN, YouTube, the open web),
              harvested as actual threads where people describe the matching pain.
    MATCH   = a structural pairing (same skeleton, different flesh — Kauffman's exaptation /
              Johnson's adjacent possible) → a product wedge that already has a first customer:
              the people who are complaining.

Division of labour, as everywhere in Agora: this module is the GATHER + LEDGER half. It serves
the supply registry (with ready-made search queries) and records discovered demand→supply
matches. CLAUDE runs the actual world-search (via WebSearch) and does the structural match —
the creative judgment. NOTHING here reaches outward: recording a match is DISCOVERY only; any
real outreach still goes through the existing GATED correspondent/draft flow (owner approves).

State: its own ledger (.exaptation.json). Read-only over everything else.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_STORE = _ROOT / ".exaptation.json"

# SUPPLY: our proven mechanisms, each abstracted to its transferable invariant + the unmet need
# it solves + DISTANT domains it may exapt into + ready-made world-search queries. Seeded from
# Agora's own Lab-measured results. Add a mechanism here whenever a new result is proven.
SUPPLY = [
    {
        "id": "drawdown_exit",
        "name": "Drawdown-exit theta (when to quit a depleting vein)",
        "invariant": "Exit a depleting yield process when its yield falls a fixed fraction theta below "
                     "its running peak; there is an interior optimum (too-tight and too-loose both lose).",
        "unmet_need": "People know to 'set exit criteria and ignore sunk cost' but have NO measured "
                      "threshold for when to quit/kill an effort.",
        "lab": "565aa7 (theta~0.6 beats mine-to-depletion +239%)",
        "exapts_to": ["R&D / project kill decisions", "ad-spend cutoff", "content-series abandonment",
                      "grant/research-line reallocation", "founder pivot timing"],
        "queries": [
            "when to kill a project diminishing returns how to decide",
            "when to stop spending on an ad campaign that is not working",
            "how do I know when to quit my startup sunk cost reddit",
            "when to abandon a research direction PhD diminishing returns",
        ],
    },
    {
        "id": "value_ranked_decay",
        "name": "Value-ranked per-type memory decay",
        "invariant": "Rank a scarce, perishable inventory by future-retrieval-value x per-type half-life; "
                     "let low-value items lapse instead of cleaning by recency or access-count.",
        "unmet_need": "Stores silently fill with stale, low-value items that degrade retrieval; cleanup "
                      "is done by recency/frequency, not by future value.",
        "lab": "inspeximus recall benchmark + per-type decay (dogfooded on dungeon inspeximus)",
        "exapts_to": ["AI agent memory / context rot", "RAG chunk freshness", "feature-flag cleanup",
                      "alert/notification fatigue", "CRM record decay"],
        "queries": [
            "AI agent context rot long conversation forgetting fix",
            "RAG retrieval stale outdated chunks ranking problem",
            "too many feature flags cleanup which to remove",
            "alert fatigue too many notifications which matter",
        ],
    },
    {
        "id": "loop_lock_governor",
        "name": "Self-Reference Governor (loop-lock insurance)",
        "invariant": "Keep a system's self-derived fraction below the self-confirmation lock threshold "
                     "(effective self-trust exponent p<1, external-evidence anchor >=~5%).",
        "unmet_need": "Systems that consume their own output drift / collapse / self-confirm, and nobody "
                      "measures the live self-reference level in production.",
        "lab": "75db49 (strange-loop attractor: 50% bias lock at p=2; needs >=3-5% external anchor)",
        "exapts_to": ["model collapse on synthetic data", "agent memory self-confirmation",
                      "RAG over the system's own prior generations", "recommender feedback loops"],
        "queries": [
            "model collapse training on synthetic AI generated data",
            "agent hallucination compounding over long run feedback loop",
            "recommender system feedback loop filter bubble degradation",
        ],
    },
    {
        "id": "null_model_attacker",
        "name": "Null-model attacker (credit only effect minus its own null)",
        "invariant": "Credit a claimed effect only by the margin it beats its own matched zero-effect "
                     "null model; a number that a random/null baseline reproduces carries no signal.",
        "unmet_need": "People can't tell whether a measured number is real or what a random baseline "
                      "would have produced anyway.",
        "lab": "matched-null firewall (manufactured-conclusion auditor)",
        "exapts_to": ["A/B test auditing", "marketing-claim verification", "dashboard metric trust",
                      "PE/CFO claim diligence", "scientific-claim screening"],
        "queries": [
            "is my A/B test result real or noise significance reddit",
            "how to verify a marketing performance claim is real",
            "dashboard metric went up but is it actually meaningful",
        ],
    },
    {
        "id": "identification_quality",
        "name": "Identification-quality score (a control is a claim about the graph)",
        "invariant": "The causal answer lives in the structure you identify with, not the surface "
                     "statistic; identification quality (not effect size) decides whether a number is trustworthy.",
        "unmet_need": "Attribution/causal numbers are trusted by their size, not by whether they are "
                      "actually identified; 'control for everything' injects bias.",
        "lab": "3a7e67 (causal phase diagram) + 940649 (collider-bias injection)",
        "exapts_to": ["marketing attribution", "PE/CFO claim diligence", "observational-study trust",
                      "policy-impact evaluation", "incrementality testing"],
        "queries": [
            "marketing attribution model overcounting wrong how to trust",
            "observational study causal claim is it actually identified",
            "incrementality test vs attribution which to believe",
        ],
    },
]


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


def supply_registry() -> dict:
    """The SUPPLY side + ready-made world-search queries — what Claude takes out into the world."""
    return {"supply": SUPPLY, "count": len(SUPPLY),
            "recent_match_urls": recent_match_urls()}


def recent_match_urls(days: int = 90) -> list[str]:
    cut = time.time() - days * 86400
    return [x.get("url", "") for x in _load() if x.get("ts", 0) >= cut and x.get("url")]


def record_match(mechanism_id: str, pain_title: str, url: str = "", community: str = "",
                 score: int = 0, note: str = "") -> dict:
    """Record one discovered DEMAND->SUPPLY match (discovery only — NOT outreach)."""
    items = _load()
    mech = next((m for m in SUPPLY if m["id"] == mechanism_id), None)
    rec = {
        "mechanism_id": (mechanism_id or "").strip(),
        "mechanism": mech["name"] if mech else (mechanism_id or ""),
        "pain_title": (pain_title or "").strip()[:200],
        "url": (url or "").strip()[:400],
        "community": (community or "").strip()[:60],
        "score": int(score) if str(score).lstrip("-").isdigit() else 0,
        "note": (note or "").strip()[:400],
        "ts": time.time(),
    }
    items.append(rec)
    _save(items)
    return {"recorded": rec["pain_title"], "mechanism": rec["mechanism"],
            "score": rec["score"], "total": len(items)}


def format_pipeline(n: int = 15) -> str:
    items = sorted(_load(), key=lambda x: x.get("score", 0), reverse=True)[:n]
    if not items:
        return "🌍 Exaptation Scanner — no real-world matches harvested yet."
    lines = ["🌍 *Exaptation Scanner* — real-world pain matched to our proven mechanisms:"]
    for it in items:
        lines.append(f"• [{it.get('score',0)}] {it.get('pain_title','')} → {it.get('mechanism','')} "
                     f"({it.get('community','')})")
    return "\n".join(lines)
