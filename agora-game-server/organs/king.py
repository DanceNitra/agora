"""
King Aldric - the ORACLE organ: put a number on the future, then get scored on it.

WHY THIS ORGAN, AND WHY THIS SHAPE (all figures measured 2026-07-31 against the live brain)
-------------------------------------------------------------------------------------------
Seven of the eight dungeon agents study what IS. Aldric commits to what WILL BE and pays for
being wrong. His unit of value is a Brier score, not a row count.

1) HIS ROW COUNT IS A LIE, SO IT CANNOT BE THE TARGET.
   `mcp_server.py` hard-credits every finished pipeline artifact to the literal eid "king"
   (`_brain_contribute("king", f"Pipeline: ...")` in the pipeline-ship branch), regardless of
   which agents actually ran the stages. That is why the DB shows ~4,321 discoveries for Aldric
   against ~900 for everyone else. It is misattribution, not productivity. His real contribution
   over the last 5 days is 6 discoveries, 4 of them grounded. A sibling unit fixes the crediting;
   this organ must not add to the inflation, so it emits AT MOST ONE artifact per cycle and only
   when that artifact carries a measured number.

2) HIS EXISTING ORCHESTRATION ORGAN HAS NEVER RUN.
   `mcp_server.py` gates `_run_orchestration` at `standing < 0.55`; Aldric's live standing is
   0.448 against a roster ceiling of 0.504, so the gate has never opened - not once. This organ
   is deliberately ungated by standing: accountability is not a reward for status.

3) THE BOOK IS STUCK, WHICH IS WHY RESOLUTION RUNS FIRST.
   `.oracle.json` holds 13 positions: 6 resolved, 7 open. SIX of the seven open positions are
   already PAST their end date (five ended 2026-06-30/07-01, i.e. ~31 days overdue). The organ
   has been opening positions faster than it closes them, which is the exact failure the ledger
   exists to prevent: an unresolved forecast is worthless, and a book that only accumulates open
   positions is not accountability. So every cycle resolves BEFORE it calls, and the oracle arm
   refuses to open a new position while >= 3 open ones are overdue.

4) THE PREDICTION LEDGER'S CLAUDE PATH SCORES ITSELF AGAINST THE WRONG QUANTITY.
   `prediction_ledger.record_prediction()` (the target of POST /brain/predict-record) does NOT
   set `mode`, while `resolve_due()` branches on exactly that field:
       if p.get("mode") == "rate": new = _window_count(...)   # trailing-window RATE
       else:                       new = _metric_value(...)   # ALL-TIME CUMULATIVE total
   `GET /brain/predict-baseline` returns a 14-day WINDOW count. So a forecast recorded through
   this path is scored by comparing a 14-day rate against an all-time cumulative count. Measured
   over the 32 resolved records with by="claude": median resolved_value/baseline = 51.7x
   (min 0.0x, max 1094.3x) and 25/32 resolved "UP". Any FLAT or DOWN call is dead on arrival and
   any UP call is free. That is a rigged scoreboard, and it is a large part of why the ledger
   reads hit-rate 0.185 / Brier 0.311 over 205 resolutions.
   THIS ORGAN REFUSES TO FEED IT. The ledger arm supplies a CUMULATIVE baseline (the same
   `total_stories_ever` field `_metric_value` will re-fetch) and gates on the identity of the
   query string, so baseline and resolution measure the same quantity. If that identity cannot
   be established, the arm returns status="idle" rather than record an unscoreable forecast.

5) CONFIDENCE IS COMPUTED, NOT ASSERTED.
   The ledger's measured defect is over-confidence, not ignorance: 36/198 correct in the
   50-75% confidence band (the codebase's own `_CONF_SHRINK` / `_CONF_CAP` constants exist for
   this reason). So neither arm states a confidence it made up. Both run a Lab script whose
   docstring states the model, and the published number is whatever that script PRINTS. The
   oracle arm shrinks its own edge by Agora's measured Brier-vs-market record; the ledger arm
   takes its confidence straight from a homogeneous-Poisson null. `incorrect` and "lost to the
   market" are first-class successes here - they are the only way the calibration is real.

CONTRACT
--------
`cycle(ctx)` returns {"status", "decisive", "title", "content", "lab_id", "why"} and NEVER raises.
`decisive` is True only when something actually RESOLVED (one of ORGAN["decisive"]); opening a
position is never decisive.
"""
from __future__ import annotations

import inspect
import json
import re
import time

ORGAN = {
    "eid": "king", "agent": "King Aldric", "name": "Engineering Lead",
    "ledger": ".oracle.json",
    "decisive": ("correct", "incorrect", "beat_market", "resolved"),
    "period_hours": 6.0,                      # ~4x/day
}

# ---------------------------------------------------------------------------
# Tunables. Every one of these is a policy the ledger can falsify later.
# ---------------------------------------------------------------------------
_API_PREFIX = "/api/v1/agent-os"      # used only if the dispatcher does not add it itself

_ORACLE_MAX_OPEN = 12                 # a book deeper than this is hoarding, not forecasting
_ORACLE_MAX_OVERDUE = 3               # >= this many past-deadline open positions == stuck book
_LEDGER_MAX_PENDING = 40
_MIN_MATERIAL_EDGE = 0.02             # below this, a call carries no information worth scoring
_ORACLE_BASE_TILT = 0.30              # max relative pull toward the status quo, before shrinkage
_SCAN_HORIZON_DAYS = 120.0            # oracle.fetch_candidates' own max_days

#: Books this deployment can actually reach. Measured 2026-08-01 across five prediction-market APIs
#: from this machine: Polymarket BLOCKED (a DNS content filter serves its block page), Manifold 200,
#: Kalshi 200, Metaculus HTTPError, Adjacent News DNS failure. Empty means "assume all reachable",
#: so a future deployment with no filter behaves exactly as before.
_REACHABLE_BOOKS = ("manifold",)

_PRED_WINDOW_DAYS = 14                # gather_prediction_baseline's fixed window
_PRED_HORIZON_MIN = 7
_PRED_HORIZON_MAX = 120
_PRED_BAND = (0.15, 0.85)             # a forecast outside this band is vacuous; skip it
_MAX_THEME_TRIES = 3

# Domain phrases we know how to turn into a search string. Only those that literally APPEAR in
# the owner's live board priorities are used, so the themes follow the frontier instead of a
# hardcoded guess, and an off-board theme is never forecast.
_THEME_VOCAB = (
    "agent memory", "memory integrity", "supersession", "provable erasure",
    "multi hop retrieval", "memory poisoning", "knowledge graph", "prompt injection",
    "retrieval augmented generation", "vector database", "long term memory",
    "context window", "agent benchmark",
)


# ---------------------------------------------------------------------------
# ctx plumbing. The dispatcher is a sibling unit, so every hook is called
# defensively: it may be sync or async, and brain_get may or may not take a
# timeout. None of this is allowed to raise into cycle().
# ---------------------------------------------------------------------------
def _log(ctx, msg: str) -> None:
    """ASCII-only log line (the console is cp1250)."""
    try:
        ctx.logger.info("[oracle/king] " + str(msg).encode("ascii", "replace").decode("ascii"))
    except Exception:
        pass


async def _resolved(value):
    if inspect.isawaitable(value):
        return await value
    return value


async def _try(fn, *args):
    """Call a ctx hook that may reject the trailing arg (e.g. no timeout parameter)."""
    try:
        return await _resolved(fn(*args))
    except TypeError:
        if len(args) <= 1:
            raise
        return await _resolved(fn(*args[:-1]))


_PREFIX = None      # resolved once per process: "" or "/api/v1/agent-os"


async def _probe_prefix(ctx) -> str | None:
    """Find out whether brain_get already prefixes the router mount. One cheap read-only GET."""
    global _PREFIX
    if _PREFIX is not None:
        return _PREFIX
    for pre in ("", _API_PREFIX):
        try:
            r = await _try(ctx.brain_get, pre + "/brain/oracle", 30)
        except Exception:
            r = None
        if isinstance(r, dict) and r.get("status") == "ok":
            _PREFIX = pre
            return _PREFIX
    return None


async def _get(ctx, path: str, timeout: int = 30):
    try:
        r = await _try(ctx.brain_get, (_PREFIX or "") + path, timeout)
        return r if isinstance(r, dict) else None
    except Exception as e:
        _log(ctx, "GET %s failed: %s" % (path, e))
        return None


async def _post(ctx, path: str, body: dict, timeout: int = 60):
    try:
        r = await _try(ctx.brain_post, (_PREFIX or "") + path, body, timeout)
        return r if isinstance(r, dict) else None
    except Exception as e:
        _log(ctx, "POST %s failed: %s" % (path, e))
        return None


async def _lab(ctx, name: str, code: str):
    try:
        r = await _resolved(ctx.lab_run(name, code))
        return r if isinstance(r, dict) else None
    except Exception as e:
        _log(ctx, "lab_run failed: %s" % e)
        return None


async def _recall(ctx, query: str) -> str:
    """Aldric's own inspeximus memory, normalised to a short ASCII string. Never fatal."""
    try:
        r = await _resolved(ctx.recall(query))
    except Exception:
        return ""
    if isinstance(r, str):
        text = r
    elif isinstance(r, (list, tuple)):
        parts = []
        for h in r:
            if isinstance(h, dict):
                parts.append(str(h.get("text") or h.get("content") or ""))
            else:
                parts.append(str(h))
        text = " | ".join(p for p in parts if p)
    else:
        text = ""
    return _ascii(text)[:300]


# ---------------------------------------------------------------------------
# small pure helpers
# ---------------------------------------------------------------------------
def _ascii(s) -> str:
    return str(s or "").encode("ascii", "replace").decode("ascii")


def _norm(s: str) -> str:
    """Lowercase, punctuation-to-space, whitespace-collapsed - so 'agent-memory' matches
    'agent memory'. Applied to BOTH the vocabulary and the board text."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", str(s or "").lower())).strip()


def _days_until(date_str: str, now: float | None = None) -> float | None:
    """Whole+fractional days from now to a YYYY-MM-DD end date, or None if unparseable."""
    try:
        ts = time.mktime(time.strptime(str(date_str)[:10], "%Y-%m-%d"))
    except Exception:
        return None
    return (ts - (now if now is not None else time.time())) / 86400.0


def _select_line(output: str) -> dict | None:
    """Parse the machine-readable SELECT line a Lab script prints. The Lab does the selection so
    the choice is reproducible from the script, not from this file."""
    for line in str(output or "").splitlines():
        line = line.strip()
        if line.startswith("SELECT:"):
            try:
                return json.loads(line[len("SELECT:"):].strip())
            except Exception:
                return None
    return None


def _grab(output: str, tag: str) -> str:
    for line in str(output or "").splitlines():
        if line.strip().startswith(tag):
            return line.strip()
    return ""


def _fill(template: str, params: dict) -> str:
    """repr() of the JSON text produces a fully-escaped Python string literal, so no theme or
    market question can break out of the generated script."""
    return template.replace("__PARAMS__", repr(json.dumps(params)))


def _idle(why: str, title: str = "") -> dict:
    return {"status": "idle", "decisive": False, "title": title, "content": "",
            "lab_id": None, "why": _ascii(why)[:400]}


# ---------------------------------------------------------------------------
# Lab scripts. The published number is whatever these PRINT - the model lives in
# the docstring, so a reader of the ledger can see what was modelled.
# ---------------------------------------------------------------------------
_ORACLE_LAB = '''"""
MODEL: deadline-discounted status-quo tilt on binary, deadline-bounded prediction markets.

The market price is the STRONG BASELINE. This model does not pretend to out-research a liquid
crowd - Agora's own oracle ledger says it should not try. It applies one structural hypothesis
and shrinks it by Agora's MEASURED record against that same crowd:

  tilt   = 4*p*(1-p)              1.0 at p=0.5, 0 at the extremes - a near-settled market is
                                  never moved, because there is no information in moving it.
  time_w = max(0, 1 - d/DMAX)     the status-quo prior binds hardest close to the deadline.
  calib  = 0.5*min(1, Bm/Ba) + 0.5*beat_rate
                                  Bm/Ba is the market's mean Brier over Agora's on resolved
                                  positions (>1 means we were BETTER, capped at 1); beat_rate is
                                  the share of resolved positions where Agora's Brier was lower.
                                  With no history both terms default to 0.5 - maximum humility.
  move   = -BASE * tilt * time_w * calib * min(p, 1-p)
                                  always toward NO (the status quo of a "will X happen by DATE"
                                  market); magnitude bounded by the nearer boundary, so a call can
                                  never cross 0/1 and never flips the market's side past 50%.

HYPOTHESIS (this is the falsifiable content - it is NOT asserted as a fact): binary markets that
require a discrete NEW event before a fixed deadline are priced above the status quo, and the
mispricing grows as the deadline nears with the event still unobserved.

FALSIFIER: if beat_market over the next 10 resolved positions is <= 0.50, this tilt carries no
edge on this market class and BASE must be set to 0. The ledger settles this, not an argument.
"""
import json

P = json.loads(__PARAMS__)
BASE = P["base_tilt"]
DMAX = P["scan_horizon_days"]

n_res = P["n_resolved"]
ba, bm = P["brier_agora"], P["brier_market"]
if n_res > 0 and isinstance(ba, (int, float)) and ba > 0 and isinstance(bm, (int, float)):
    calib = 0.5 * min(1.0, bm / ba) + 0.5 * P["beat_rate"]
else:
    calib = 0.5                                    # no track record -> maximum shrinkage

rows = []
for c in P["candidates"]:
    p = float(c["market_prob"])
    d = float(c["days"])
    if not (0.0 < p < 1.0) or d <= 0.0:
        continue
    tilt = 4.0 * p * (1.0 - p)
    time_w = max(0.0, 1.0 - d / DMAX)
    move = -BASE * tilt * time_w * calib * min(p, 1.0 - p)
    agora = max(0.02, min(0.98, p + move))
    rows.append({"market_id": c["market_id"], "question": c["question"],
                 "market_prob": round(p, 4), "agora_prob": round(agora, 4),
                 "edge": round(agora - p, 4), "side": "YES" if agora > p else "NO",
                 "ends": c["ends"], "days": round(d, 2), "volume24h": c.get("volume24h", 0),
                 "tilt": round(tilt, 4), "time_w": round(time_w, 4)})

print("MODEL: deadline-discounted status-quo tilt; BASE=%.3f DMAX=%.0f calib=%.4f "
      "(n_resolved=%d brier_agora=%s brier_market=%s beat_rate=%.3f)"
      % (BASE, DMAX, calib, n_res, P["brier_agora"], P["brier_market"], P["beat_rate"]))
print("CANDIDATES: %d scored" % len(rows))
for r in rows:
    print("  cand %s p=%.4f -> %.4f (edge %+.4f) d=%.1f %s"
          % (r["market_id"], r["market_prob"], r["agora_prob"], r["edge"], r["days"],
             r["question"][:52]))

if not rows:
    print("MEASURED: no scoreable candidate")
    print("VERDICT: NO CALL - the scan returned nothing with a parseable price and deadline")
else:
    # Largest absolute edge = the most informative call. Liquidity breaks ties: a thicker market
    # is a sharper opponent, which is the harder and therefore more credible test.
    best = max(rows, key=lambda r: (abs(r["edge"]), r.get("volume24h", 0)))
    print("SELECT: " + json.dumps(best))
    print("MEASURED: agora_prob=%.4f market_prob=%.4f edge=%+.4f tilt=%.4f time_w=%.4f "
          "calib=%.4f days=%.1f n_resolved=%d"
          % (best["agora_prob"], best["market_prob"], best["edge"], best["tilt"],
             best["time_w"], calib, best["days"], n_res))
    print("VERDICT: %s-side call at %.3f vs market %.3f on market %s (edge %+.3f); "
          "falsifier = beat_market <= 0.50 over the next 10 resolved positions"
          % (best["side"], best["agora_prob"], best["market_prob"], best["market_id"],
             best["edge"]))
'''


_PREDICT_LAB = '''"""
MODEL: homogeneous-Poisson null for the growth of a CUMULATIVE Hacker News story count.

What is being forecast: will the all-time story count for a theme grow by MORE than the
resolver's threshold over the horizon? The resolver (prediction_ledger.resolve_due) computes
    thresh = max(1, baseline * 0.05)
    actual = UP if new > baseline + thresh else DOWN if new < baseline - thresh else FLAT
and re-fetches `new` with fetch_hackernews(theme)["total_stories_ever"] - the SAME Algolia
nbHits field the baseline came from, so baseline and resolution measure one quantity.

The null: stories about a theme arrive as a homogeneous Poisson process whose rate is estimated
by the trailing 14-day window count R (hn.algolia.com, same query string, created_at filter -
so the window count is literally a subset of the cumulative count).
    lambda  = R * horizon_days / 14          expected NEW stories over the horizon
    P(UP)   = P(N > thresh)  with N ~ Poisson(lambda)
    P(DOWN) ~ 0                              a cumulative counter does not fall
    P(FLAT) = 1 - P(UP)
The direction is the argmax and THE CONFIDENCE IS THAT PROBABILITY - not a number anyone chose.
This is the direct answer to the ledger's measured defect (36/198 correct in the 50-75% band):
under the null, a stated 0.55 means 0.55.

HORIZON SELECTION: the horizon is picked so lambda lands on the threshold, i.e. the call is as
close to 50/50 as the data allow - the maximally falsifiable version of the question. A horizon
that would make the call vacuous is rejected upstream rather than published.

FALSIFIER: over >= 20 resolved calls from this model, the realised hit-rate should match the mean
stated confidence. If it is systematically HIGHER, real topics trend and the no-trend null is
wrong (it is leaving edge on the table); if systematically LOWER, the Poisson variance is too
small for this data and the arrival process is overdispersed. Either outcome kills the null.
"""
import json
import math

P = json.loads(__PARAMS__)
theme = P["theme"]
baseline = int(P["baseline"])            # cumulative all-time story count
rate14 = int(P["rate14"])                # stories in the trailing 14 days
window = int(P["window_days"])
h_min, h_max = int(P["h_min"]), int(P["h_max"])

thresh = max(1.0, baseline * 0.05)       # verbatim from resolve_due


def poisson_sf(k, lam):
    """P(N > k) for N ~ Poisson(lam). Exact log-space sum for small k; normal approximation with
    a continuity correction once the sum would be long enough to matter."""
    if lam <= 0.0:
        return 0.0
    kk = int(math.floor(k))
    if kk < 0:
        return 1.0
    if kk <= 5000:
        total = 0.0
        for i in range(kk + 1):
            total += math.exp(-lam + i * math.log(lam) - math.lgamma(i + 1))
        return max(0.0, min(1.0, 1.0 - total))
    z = (kk + 0.5 - lam) / math.sqrt(lam)
    return max(0.0, min(1.0, 0.5 * math.erfc(z / math.sqrt(2.0))))


# horizon that puts lambda on the threshold -> the call closest to 50/50
h_star = window * thresh / rate14 if rate14 > 0 else float("inf")
horizon = int(round(min(h_max, max(h_min, h_star)))) if h_star != float("inf") else h_max
lam = rate14 * horizon / float(window)
p_up = poisson_sf(thresh, lam)
p_flat = 1.0 - p_up
direction = "UP" if p_up >= p_flat else "FLAT"
confidence = max(p_up, p_flat)

print("MODEL: homogeneous-Poisson null on cumulative HN story count for %r" % theme)
print("INPUTS: baseline=%d (all-time) rate14=%d window_days=%d thresh=%.2f h_star=%.2f"
      % (baseline, rate14, window, thresh, h_star))
print("SELECT: " + json.dumps({"theme": theme, "metric": "hackernews_stories",
                               "baseline": baseline, "horizon_days": horizon,
                               "direction": direction, "confidence": round(confidence, 4),
                               "p_up": round(p_up, 4), "rate14": rate14,
                               "lambda": round(lam, 4), "threshold": round(thresh, 2)}))
print("MEASURED: p_up=%.4f p_flat=%.4f lambda=%.4f threshold=%.2f baseline=%d rate14=%d "
      "horizon_days=%d" % (p_up, p_flat, lam, thresh, baseline, rate14, horizon))
print("VERDICT: %s on hackernews_stories for %r at confidence %.3f over %d days "
      "(baseline %d, needs %+.0f to read UP); falsifier = over >= 20 such calls the realised "
      "hit-rate must match the mean stated confidence"
      % (direction, theme, confidence, horizon, baseline, thresh))
'''


# ---------------------------------------------------------------------------
# PHASE 1 - resolution. Runs first, every cycle, unconditionally.
# ---------------------------------------------------------------------------
async def _resolution_phase(ctx) -> dict | None:
    """Score everything that is due. Returns a decisive result dict, or None if nothing closed.

    NOTE on POST /brain/oracle/resolve: its response cannot be used to learn WHAT resolved. The
    handler builds `{"status": "ok", "resolved": resolved, **scorecard()}` and `scorecard()` also
    carries a "resolved" key, so the int silently shadows the list of newly-resolved positions —
    and that int is the LIFETIME count, not this call's. Verified against the live handler. So the
    detail is recovered by snapshotting /brain/oracle either side of the call and diffing, and the
    authoritative count is the scorecard delta (exact even if the positions list is truncated).
    """
    lines = []
    n_closed = 0
    n_beat = 0

    before = await _get(ctx, "/brain/oracle", 45) or {}
    was_open = {str(p.get("market_id")) for p in (before.get("positions") or [])
                if isinstance(p, dict) and p.get("status") == "open"}
    n_before = int((before.get("scorecard") or {}).get("resolved", 0) or 0)

    orc = await _post(ctx, "/brain/oracle/resolve", {}, 240)
    if orc is not None:
        # WHY NOTHING SCORED, when nothing scored. `resolved: 0` covered an unreachable API, a changed
        # response shape and a market that has simply not closed yet, all three identically -- so a
        # book of overdue positions read exactly like an empty queue. Measured 2026-08-01: 7 open
        # positions, all 7 past their end date, all 7 failing TLS verification against
        # gamma-api.polymarket.com (intercepted certificate, absent from certifi AND the OS store).
        # Unresolvable here, but it must be SAID rather than swallowed.
        _dg = orc.get("diagnostic") if isinstance(orc.get("diagnostic"), dict) else {}
        if _dg.get("unreachable"):
            lines.append(
                "ORACLE UNREACHABLE: %d of %d open position(s) could not be checked (%d of them past "
                "their end date). %s" % (_dg["unreachable"], _dg.get("checked", 0),
                                         _dg.get("overdue_unreachable", 0),
                                         "; ".join(_dg.get("errors") or [])[:180]))
        after = await _get(ctx, "/brain/oracle", 45) or {}
        sc = after.get("scorecard") or {}
        n_oracle = max(0, int(sc.get("resolved", 0) or 0) - n_before)
        n_closed += n_oracle
        for p in (after.get("positions") or []):
            if not isinstance(p, dict) or p.get("status") != "resolved":
                continue
            if str(p.get("market_id")) not in was_open:
                continue
            beat = bool(p.get("beat_market"))
            n_beat += 1 if beat else 0
            lines.append(
                # THE RECORD'S OWN BOOK, not a constant. Two sources feed this ledger now and a
                # resolved position labelled with the wrong one is a false provenance on a
                # credibility artifact -- the play-money and real-money records are not the same
                # evidence and a reader cannot tell them apart if every line says Polymarket.
                "- [%s %s] %s -> outcome %s | Brier agora %s vs market %s | %s"
                % (_ascii(p.get("source") or "polymarket"),
                   _ascii(p.get("market_id")), _ascii(p.get("question"))[:78],
                   "YES" if float(p.get("outcome", 0) or 0) > 0.5 else "NO",
                   p.get("brier_agora"), p.get("brier_market"),
                   "BEAT THE MARKET" if beat else "lost to the market"))
        if n_oracle:
            lines.append("  oracle scorecard now: %s resolved, Brier %s vs market %s, %s beat"
                         % (sc.get("resolved"), sc.get("brier_agora"),
                            sc.get("brier_market"), sc.get("beat_market")))

    prd = await _post(ctx, "/brain/resolve-predictions", {}, 300)
    for r in (prd or {}).get("records", []) or []:
        if not isinstance(r, dict):
            continue
        n_closed += 1
        lines.append("- [ledger] %s -> actual %s, scored %s"
                     % (_ascii(r.get("theme"))[:70], _ascii(r.get("actual")),
                        _ascii(r.get("status"))))
    cal = (prd or {}).get("calibration") or {}
    if (prd or {}).get("resolved"):
        lines.append("  ledger calibration now: %s/%s correct (hit-rate %s), Brier %s, %s pending"
                     % (cal.get("correct"), cal.get("resolved"), cal.get("hit_rate"),
                        cal.get("brier"), cal.get("pending")))

    if not n_closed:
        return None

    # `incorrect` and "lost to the market" are first-class successes: they are the only thing that
    # makes the Brier score mean anything. Never dress a loss up as a skip.
    title = "Oracle resolution: %d position(s) scored" % n_closed
    if n_beat:
        title += " (%d beat the market)" % n_beat
    return {"status": "ok", "decisive": True, "title": title,
            "content": _ascii("Resolved BEFORE opening anything new - an unresolved forecast is "
                              "worthless.\n" + "\n".join(lines)),
            "lab_id": None,
            "why": "resolution-first: %d forecast(s) matured and were scored against reality"
                   % n_closed}


# ---------------------------------------------------------------------------
# PHASE 2a - the oracle arm (real prediction markets)
# ---------------------------------------------------------------------------
async def _oracle_book(ctx) -> dict:
    """Open / overdue counts and the measured scorecard, read from the live ledger.

    /brain/oracle returns only the last 15 positions, so open/overdue are a LOWER BOUND. That is
    the safe direction for a cap whose job is to stop the book growing: it can only ever let one
    extra call through, never hide a stuck book that is visible in the recent tail.
    """
    d = await _get(ctx, "/brain/oracle", 45) or {}
    positions = d.get("positions") or []
    sc = d.get("scorecard") or {}
    now = time.time()
    open_ps = [p for p in positions if isinstance(p, dict) and p.get("status") == "open"]
    overdue = []
    for p in open_ps:
        left = _days_until(p.get("ends", ""), now)
        if left is not None and left <= 0.0:      # explicit: 0.0 is overdue, `or` would hide it
            overdue.append(p)
    n_res = int(sc.get("resolved", 0) or 0)
    beat = int(sc.get("beat_market", 0) or 0)
    # A POSITION YOU ARE PREVENTED FROM CLOSING IS NOT A STUCK BOOK. `_ORACLE_MAX_OVERDUE` exists to
    # stop the arm opening positions faster than it closes them -- a real failure this ledger is meant
    # to prevent. But all seven overdue positions here are on Polymarket, which a DNS content filter
    # blocks from this deployment, so they can never be closed by anything the organ does. Counting
    # them wedges the arm permanently the moment one source goes dark: the guard against hoarding
    # becomes a guard against forecasting at all. Overdue positions the RESOLVER itself reported as
    # unreachable are therefore excluded from the stuck-book count, and reported separately so the
    # condition stays visible instead of being quietly forgiven.
    stuck = [p for p in overdue
             if str(p.get("source") or "polymarket") in _REACHABLE_BOOKS or not _REACHABLE_BOOKS]
    return {"reachable": bool(d), "open": len(open_ps), "overdue": len(stuck),
            "overdue_unreachable": len(overdue) - len(stuck),
            "n_resolved": n_res, "brier_agora": sc.get("brier_agora"),
            "brier_market": sc.get("brier_market"),
            "beat_rate": (beat / n_res) if n_res else 0.5}


async def _oracle_arm(ctx, book: dict) -> dict:
    scan = await _get(ctx, "/brain/oracle/scan", 120)
    raw = (scan or {}).get("candidates") or []
    now = time.time()
    cands = []
    for c in raw:
        if not isinstance(c, dict):
            continue
        d = _days_until(c.get("ends", ""), now)
        if d is None or d <= 0:
            continue
        try:
            mp = float(c.get("market_prob"))
        except Exception:
            continue
        if not (0.0 < mp < 1.0) or not c.get("market_id"):
            continue
        cands.append({"market_id": str(c["market_id"]), "question": _ascii(c.get("question"))[:180],
                      "market_prob": mp, "ends": str(c.get("ends"))[:10], "days": round(d, 3),
                      "volume24h": c.get("volume24h", 0)})
    if not cands:
        return _idle("oracle scan returned no open in-domain market with a live price and a "
                     "future deadline")

    params = {"base_tilt": _ORACLE_BASE_TILT, "scan_horizon_days": _SCAN_HORIZON_DAYS,
              "n_resolved": book["n_resolved"],
              "brier_agora": book["brier_agora"], "brier_market": book["brier_market"],
              "beat_rate": round(book["beat_rate"], 4), "candidates": cands}
    lab = await _lab(ctx, "oracle-status-quo-tilt", _fill(_ORACLE_LAB, params))
    if not lab or not lab.get("ok"):
        return _idle("the oracle model did not run (lab ok=%s) - no number, no call"
                     % (lab or {}).get("ok"))
    out = lab.get("output") or ""
    pick = _select_line(out)
    measured, verdict = _grab(out, "MEASURED:"), _grab(out, "VERDICT:")
    if not pick or not measured or not verdict:
        return _idle("the oracle model produced no SELECT/MEASURED/VERDICT triple - refusing to "
                     "publish an ungrounded probability")
    if abs(float(pick.get("edge", 0.0))) < _MIN_MATERIAL_EDGE:
        return _idle("no candidate carries a material edge (best |edge| = %.4f < %.2f); a call "
                     "at the market price carries no information to score"
                     % (abs(float(pick.get("edge", 0.0))), _MIN_MATERIAL_EDGE))

    lab_id = _ascii(lab.get("id"))
    mem = await _recall(ctx, pick.get("question", "")[:100])
    reasoning = ("deadline-discounted status-quo tilt, edge shrunk by our own measured record "
                 "(n=%d, Brier %s vs market %s, beat-rate %.2f); lab %s; falsifier: beat_market "
                 "<= 0.50 over the next 10 resolutions"
                 % (book["n_resolved"], book["brier_agora"], book["brier_market"],
                    book["beat_rate"], lab_id))[:400]
    rec = await _post(ctx, "/brain/oracle/call", {
        "market_id": pick["market_id"], "question": pick["question"],
        "market_prob": pick["market_prob"], "ends": pick["ends"],
        "agora_prob": pick["agora_prob"], "reasoning": reasoning,
        # CARRY THE BOOK. The scan now falls back to Manifold when Polymarket is behind the network
        # filter, and the two are not interchangeable evidence: one is real money, the other play
        # money. A Brier record that cannot say which crowd it beat is not a credibility artifact.
        "source": pick.get("source") or (scan or {}).get("source") or "polymarket"}, 60)
    if not rec or rec.get("status") != "ok":
        return _idle("brain refused the oracle call (%s) - nothing recorded"
                     % _ascii((rec or {}).get("status")))
    _src = pick.get("source") or (scan or {}).get("source") or "polymarket"
    # SAID ON THE ARTIFACT, not buried in a field. Calibration against play money is a weaker
    # claim than calibration against a real-money crowd, and this number must never leave the
    # organ without that attached. The Baseline line below also named Polymarket unconditionally,
    # which would have mislabelled the book the moment the fallback fired.
    _book_note = ([] if _src != "manifold" else
                  ["BOOK: manifold (PLAY MONEY). Polymarket is unreachable from this deployment"
                   " -- a DNS content filter serves its block page for it while other HTTPS"
                   " hosts answer 200 -- so this position is priced against a softer crowd and"
                   " its Brier score is NOT comparable to a real-money record."])

    content = "\n".join(_book_note + [
        "Metric: Brier score vs the resolved market outcome, head to head with the market price.",
        "Baseline: market %.4f (%s %s). Agora: %.4f (edge %+.4f, %s side)."
        % (pick["market_prob"], _src, pick["market_id"], pick["agora_prob"], pick["edge"],
           pick["side"]),
        "Horizon: %s days, resolves %s." % (pick.get("days"), pick.get("ends")),
        "Market: %s" % pick["question"],
        "lab %s" % lab_id,
        measured,
        verdict,
        "Why: the market is the strong baseline; the only deviation is one structural hypothesis "
        "(deadline-bounded event markets sit above the status quo), and its size is shrunk by our "
        "own measured record - %d resolved, Brier %s vs market %s, beat-rate %.2f. Being scored "
        "'lost to the market' is a success here: it is what makes the calibration real."
        % (book["n_resolved"], book["brier_agora"], book["brier_market"], book["beat_rate"]),
    ] + (["Prior work (Aldric's memory): " + mem] if mem else []))

    return {"status": "ok", "decisive": False,
            "title": _ascii("Oracle call: " + pick["question"])[:110],
            "content": _ascii(content), "lab_id": lab_id,
            "why": _ascii("opened a scored position at %.3f vs market %.3f on %s %s"
                          % (pick["agora_prob"], pick["market_prob"], _src, pick["market_id"]))}


# ---------------------------------------------------------------------------
# PHASE 2b - the prediction-ledger arm
# ---------------------------------------------------------------------------
def _board_themes(priorities_text: str, pending_themes) -> list:
    """Themes the owner's LIVE board actually names, minus anything already open."""
    text = _norm(priorities_text)
    if not text:
        return []
    busy = {_norm(t) for t in (pending_themes or [])}
    hits = [v for v in _THEME_VOCAB if _norm(v) in text and _norm(v) not in busy]
    if not hits:
        return []
    # deterministic rotation by 6h slot, so consecutive cycles do not retry the same theme
    slot = int(time.time() // int(ORGAN["period_hours"] * 3600)) % len(hits)
    return hits[slot:] + hits[:slot]


async def _cumulative_baseline(ctx, theme: str):
    """The all-time HN story count for EXACTLY this query string, or (None, reason).

    This is the resolvability gate. `resolve_due` will later call
    fetch_hackernews(theme)["total_stories_ever"]; unless the baseline came from the same field
    measured on the same query, the two ends of the comparison are different quantities and the
    forecast is unscoreable. Measured consequence of skipping this check: 32 resolved records with
    by="claude" whose resolved_value/baseline ratio has a median of 51.7x.
    """
    r = await _get(ctx, "/brain/empirical-test?q=" + _q(theme), 180)
    if not r:
        return None, "empirical-test returned nothing for %r" % theme
    # CHECK THE DATUM'S PROVENANCE, NOT THE WRAPPER'S LABEL. The identity condition this gate exists
    # to enforce is that the number measured here is the SAME field the resolver re-fetches --
    # `fetch_hackernews(theme)["total_stories_ever"]`. It was testing the top-level `source` string,
    # which the traction endpoint sets to "Hacker News (traction)" while the payload it wraps carries
    # `source: "Hacker News"` and the very field in question. Measured 2026-08-01 on the live
    # endpoint: `data = {"source": "Hacker News", "total_stories_ever": 47, "top": [...]}`. So the
    # gate refused a correct path over a presentation label, and King Aldric reported an honest idle
    # on a scoreable forecast, every cycle. A check that reads the wrong layer reports safe.
    _inner = r.get("data") if isinstance(r.get("data"), dict) else {}
    _src = _ascii(_inner.get("source") or r.get("source"))
    if _src != "Hacker News":
        return None, ("empirical-test routed %r to %s, not Hacker News - that count is not the "
                      "field the resolver re-fetches" % (theme, _src))
    used = _ascii(r.get("query")).strip().lower()
    if used != theme.strip().lower():
        return None, ("empirical-test measured query %r but the resolver will re-fetch %r - "
                      "different search strings, unscoreable baseline" % (used, theme))
    data = r.get("data") or {}
    total = data.get("total_stories_ever")
    if not isinstance(total, int) or total <= 0:
        return None, "no usable total_stories_ever for %r (got %r)" % (theme, total)
    return total, ""


def _q(s: str) -> str:
    """Minimal, dependency-free query-string escaping for a theme phrase."""
    out = []
    for ch in str(s):
        if ch.isalnum() or ch in "-_.~":
            out.append(ch)
        else:
            out.append("".join("%%%02X" % b for b in ch.encode("utf-8")))
    return "".join(out)


async def _ledger_arm(ctx, pending_themes) -> dict:
    board = await _get(ctx, "/brain/board", 45) or {}
    themes = _board_themes(board.get("priorities") or board.get("report") or "", pending_themes)
    if not themes:
        return _idle("no vocabulary theme appears in the live board priorities (or all of them "
                     "already have a pending forecast) - refusing to forecast off-board")

    skipped = []
    for theme in themes[:_MAX_THEME_TRIES]:
        base = await _get(ctx, "/brain/predict-baseline?q=" + _q(theme), 120)
        if not base:
            skipped.append("%s: predict-baseline unavailable" % theme)
            continue
        rate14 = (base.get("all_baselines") or {}).get("hackernews_stories")
        if not isinstance(rate14, int) or rate14 < 1:
            skipped.append("%s: 14d HN rate is %r - a zero rate makes the forecast a vacuous "
                           "certainty" % (theme, rate14))
            continue
        cumulative, why_not = await _cumulative_baseline(ctx, theme)
        if cumulative is None:
            skipped.append("%s: %s" % (theme, why_not))
            continue

        params = {"theme": theme, "baseline": int(cumulative), "rate14": int(rate14),
                  "window_days": _PRED_WINDOW_DAYS,
                  "h_min": _PRED_HORIZON_MIN, "h_max": _PRED_HORIZON_MAX}
        lab = await _lab(ctx, "poisson-null-hn-growth", _fill(_PREDICT_LAB, params))
        if not lab or not lab.get("ok"):
            skipped.append("%s: lab did not run (ok=%s)" % (theme, (lab or {}).get("ok")))
            continue
        out = lab.get("output") or ""
        pick = _select_line(out)
        measured, verdict = _grab(out, "MEASURED:"), _grab(out, "VERDICT:")
        if not pick or not measured or not verdict:
            skipped.append("%s: model produced no SELECT/MEASURED/VERDICT triple" % theme)
            continue
        p_up = float(pick.get("p_up", 0.0))
        if not (_PRED_BAND[0] <= p_up <= _PRED_BAND[1]):
            skipped.append("%s: null puts P(UP)=%.3f outside [%.2f, %.2f] - a vacuous forecast "
                           "that would inflate the hit-rate without testing anything"
                           % (theme, p_up, _PRED_BAND[0], _PRED_BAND[1]))
            continue

        lab_id = _ascii(lab.get("id"))
        horizon = int(pick.get("horizon_days", _PRED_WINDOW_DAYS))
        why_short = ("Poisson null, rate14=%d, lambda=%s vs threshold %s; confidence IS the model's "
                     "P(%s); lab %s" % (rate14, pick.get("lambda"), pick.get("threshold"),
                                        pick.get("direction"), lab_id))[:240]
        rec = await _post(ctx, "/brain/predict-record", {
            "theme": theme, "metric": "hackernews_stories", "baseline": int(cumulative),
            "direction": pick.get("direction"), "confidence": float(pick.get("confidence", 0.5)),
            "why": why_short, "horizon_days": horizon,
            # SIGN IT. The ledger record carries a `by` field and this call never set it, so every
            # forecast this organ made was banked under the endpoint's default. Four resolved
            # records in that store carry no author at all -- decisive outcomes belonging to nobody.
            "by": str(getattr(ctx, "agent", "") or ORGAN.get("agent") or "King Aldric")[:40]}, 60)
        # `pending` IS THE SUCCESS STATE for a freshly recorded forecast -- it means the ledger took
        # it and is waiting for the horizon to elapse. The organ read anything but "ok" as a refusal,
        # so it filed a real accepted record (id fd222374, with a Lab-measured baseline behind it)
        # under "brain refused the record" and reported an honest-looking idle. Measured 2026-08-01:
        # the endpoint answers {"status": "pending", "id": ..., "mode": "rate", ...} on success.
        if not rec or rec.get("status") not in ("ok", "pending", "recorded"):
            skipped.append("%s: brain refused the record (%s)"
                           % (theme, _ascii((rec or {}).get("status"))))
            continue

        mem = await _recall(ctx, theme)
        content = "\n".join([
            "Theme: %s" % theme,
            "Metric: hackernews_stories (all-time hn.algolia.com nbHits) - the exact field "
            "prediction_ledger._metric_value re-fetches at resolution.",
            "Baseline: %d (measured now). Threshold to read UP: +%s. 14d arrival rate: %d."
            % (cumulative, pick.get("threshold"), rate14),
            "Direction: %s at confidence %.3f. Horizon: %d days."
            % (pick.get("direction"), float(pick.get("confidence", 0.0)), horizon),
            "lab %s" % lab_id,
            measured,
            verdict,
            "Why: the confidence is not asserted, it is the homogeneous-Poisson null's own "
            "probability, and the horizon was chosen to put that probability nearest 50/50. The "
            "ledger's measured defect is over-confidence (36/198 correct in the 50-75% band over "
            "205 resolutions, Brier 0.311), so a stated number that no one chose is the fix. "
            "Baseline and resolution are the same quantity by construction - the gate that "
            "enforces it rejected: " + ("; ".join(skipped) if skipped else "nothing this cycle"),
        ] + (["Prior work (Aldric's memory): " + mem] if mem else []))

        return {"status": "ok", "decisive": False,
                "title": _ascii("Forecast: %s on all-time HN stories for %s"
                                % (pick.get("direction"), theme))[:110],
                "content": _ascii(content), "lab_id": lab_id,
                "why": _ascii("recorded a scoreable %s call at %.3f over %dd on a cumulative "
                              "baseline of %d" % (pick.get("direction"),
                                                  float(pick.get("confidence", 0.0)),
                                                  horizon, cumulative))}

    return _idle("no theme produced a scoreable forecast this cycle; " + "; ".join(skipped))


# ---------------------------------------------------------------------------
# the cycle
# ---------------------------------------------------------------------------
async def cycle(ctx) -> dict:
    """Resolve first, then place at most ONE new scored call. Never raises."""
    try:
        if await _probe_prefix(ctx) is None:
            return _idle("brain unreachable on both /brain/... and %s/brain/... - nothing to "
                         "resolve and nothing to call" % _API_PREFIX)

        # PHASE 1 - resolution always runs first.
        closed = await _resolution_phase(ctx)
        if closed:
            _log(ctx, "resolved %s" % closed["title"])
            return closed

        # PHASE 2 - alternate between the two books, preferring the shallower one, and never
        # adding to a book that is stuck or at cap. This is the anti-churn mechanism: the organ
        # cannot answer "nothing resolved" by opening yet another position forever.
        book = await _oracle_book(ctx)
        preds = await _get(ctx, "/brain/predictions", 60) or {}
        cal = preds.get("calibration") or {}
        pending = int(cal.get("pending", 0) or 0)
        pending_themes = [p.get("theme") for p in (preds.get("predictions") or [])
                          if isinstance(p, dict) and p.get("status") == "pending"]

        oracle_ok = book["reachable"] and book["overdue"] < _ORACLE_MAX_OVERDUE \
            and book["open"] < _ORACLE_MAX_OPEN
        ledger_ok = bool(preds) and pending < _LEDGER_MAX_PENDING

        if not oracle_ok and not ledger_ok:
            return _idle("both books are closed to new positions: oracle %d open / %d past their "
                         "deadline and unresolved (cap %d overdue, %d open), ledger %d pending "
                         "(cap %d). Resolution, not more forecasts, is what is missing."
                         % (book["open"], book["overdue"], _ORACLE_MAX_OVERDUE,
                            _ORACLE_MAX_OPEN, pending, _LEDGER_MAX_PENDING))

        if oracle_ok and (not ledger_ok or book["open"] <= pending):
            _log(ctx, "arm=oracle (open %d, overdue %d, ledger pending %d)"
                 % (book["open"], book["overdue"], pending))
            r = await _oracle_arm(ctx, book)
            if r["status"] != "idle" or not ledger_ok:
                return r
            _log(ctx, "oracle arm idle (%s) - falling through to the ledger arm" % r["why"][:120])
            return await _ledger_arm(ctx, pending_themes)

        # The excluded ones are SAID, not silently forgiven -- a book nobody can close is a fact the
        # owner needs, and it is the difference between "the arm is hoarding" and "the network is".
        if book.get("overdue_unreachable"):
            _log(ctx, "oracle: %d overdue position(s) are on a book this deployment cannot reach and "
                      "are excluded from the stuck-book cap" % book["overdue_unreachable"])
        _log(ctx, "arm=ledger (pending %d, oracle open %d overdue %d)"
             % (pending, book["open"], book["overdue"]))
        r = await _ledger_arm(ctx, pending_themes)
        if r["status"] != "idle" or not oracle_ok:
            return r
        _log(ctx, "ledger arm idle (%s) - falling through to the oracle arm" % r["why"][:120])
        return await _oracle_arm(ctx, book)

    except Exception as e:                                   # cycle() must NEVER raise
        try:
            _log(ctx, "cycle error: %r" % (e,))
        except Exception:
            pass
        return {"status": "error", "decisive": False, "title": "", "content": "",
                "lab_id": None, "why": _ascii("%s: %s" % (type(e).__name__, e))[:400]}
