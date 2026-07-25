"""
The Synthesis Detector — High Priest Orin's second sight.

The canon already holds the belief that grand syntheses are forecastable phase transitions:
before a knowledge base reorganizes around a new principle it emits precursors — rising
cross-coupling (bridges form faster), critical slowing (falsifiers stop closing), and theme
flickering. Orin instruments those precursors on Agora ITSELF and fires when they cross a
threshold, queueing Claude to attempt ONE new unifying principle that subsumes >=3 existing
insights into the Canon. This is the organism testing its own phase-transition hypothesis in
real time — the rare case where the detector and the thing detected are the same system.
"""
from __future__ import annotations

import time

_WINDOW = 2 * 86400          # 48h windows for the rate comparison
_MIN_BRIDGES = 3             # below this, an "acceleration" ratio is just a count of one


def _ledger_ts(items: list) -> list[float]:
    return sorted(x.get("ts", 0) for x in items if x.get("ts"))


def _rate_accel(ts_list: list[float], now: float) -> tuple[int, int, float]:
    """(recent count, prior count, acceleration ratio) across two adjacent 48h windows."""
    recent = sum(1 for t in ts_list if t >= now - _WINDOW)
    prior = sum(1 for t in ts_list if now - 2 * _WINDOW <= t < now - _WINDOW)
    accel = (recent + 1) / (prior + 1)
    return recent, prior, round(accel, 2)


def signals() -> dict:
    """Measure the three phase-transition precursors on Agora's own knowledge dynamics."""
    from agora.execution.analogy_forge import _load as _analogies
    from agora.execution.cartography import _load as _carto
    from agora.execution.flywheel import _load as _flywheel
    now = time.time()

    # 1) cross-coupling: bridges (analogy forgings + charted holes) forming faster?
    bridge_ts = _ledger_ts(_analogies()) + _ledger_ts(_carto())
    b_recent, b_prior, b_accel = _rate_accel(bridge_ts, now)

    # 2) critical slowing: are open falsifiers piling up (closure stalling)?
    #
    # MEASURED 2026-07-25, and this line was wrong in two ways at once. It counted ONE closure status,
    # `deepened`, whose only writer (_queue_deepening in the dungeon) is switched off by
    # AGORA_QUIET_GENERATORS=1 -- so across 200 flywheel questions the count was 0, had ALWAYS been 0, and
    # was mathematically unreachable. Sitting in the divisor, that pinned pressure to its maximum and made
    # the whole signal a ratchet: it could only climb, and it climbed from 35.33 to 53.0 in a single day.
    # Second, it filtered on `ts` -- the question's CREATION time -- not on when it was closed, so even a
    # working deepen path would have missed anything closed later than the window in which it was raised.
    #
    # Closure is not one status. The system closes a falsifier whenever it settles the question: a
    # replication runs, a belief is buried, the court kills one. Count all of them, on the timestamp of the
    # CLOSING event, so the divisor is reachable by any organ that actually does the work.
    fw = _flywheel()
    open_falsifiers = sum(1 for q in fw if q.get("status") == "open")

    def _closed_ts(q: dict) -> float:
        return q.get("deepened_ts") or q.get("closed_ts") or q.get("ts", 0)

    deepened_recent = sum(1 for q in fw
                          if q.get("status") not in ("open", None) and _closed_ts(q) >= now - _WINDOW)
    for _mod in ("replication", "graveyard", "bounty"):
        try:
            _m = __import__(f"agora.execution.{_mod}", fromlist=["_load"])
            deepened_recent += sum(1 for x in (_m._load() or [])
                                   if isinstance(x, dict) and (x.get("ts") or 0) >= now - _WINDOW)
        except Exception:
            pass                                  # a missing organ must not silently pin the divisor again

    # 3) flickering: insights accumulating without a newer unifying principle over them
    insight_ts = _ledger_ts([{"ts": q.get("ts")} for q in fw])  # falsifiers ~ insights proxy
    i_recent, _, _ = _rate_accel(insight_ts, now)

    # combined pressure: coupling accelerating AND closure not keeping up
    pressure = round(b_accel * (1 + open_falsifiers / 12) / (1 + deepened_recent), 2)
    # COOLDOWN: a synthesis RELIEVES the pressure it was built from — firing again from the same
    # elevated signal just re-requests a law we already wrote. Stay quiet for 3 days after the
    # last grand-synthesis vault note (the phase transition has already happened).
    cooled = _recent_synthesis_age() < 3 * 86400
    # A FLOOR ON THE BRIDGE COUNT. accel = (recent+1)/(prior+1), so a single bridge after a quiet window
    # scores exactly (1+1)/(0+1) = 2.0 and clears the >=1.5 gate on its own. That is not acceleration, it is
    # a count of one: measured 2026-07-25, the live "accel x2.0" was literally 1 event versus 0. Require a
    # real handful before the ratio is allowed to mean anything.
    due = ((not cooled) and b_recent >= _MIN_BRIDGES and b_accel >= 1.5
           and open_falsifiers >= 6 and pressure >= 1.8)
    return {"bridge_recent": b_recent, "bridge_prior": b_prior, "bridge_accel": b_accel,
            "open_falsifiers": open_falsifiers, "deepened_recent": deepened_recent,
            "insights_recent": i_recent, "pressure": pressure, "due": due, "cooled": cooled}


def _recent_synthesis_age() -> float:
    """Seconds since the most recent grand-synthesis note in the vault (huge if none)."""
    import time as _t
    from pathlib import Path as _P
    try:
        from agora.config import settings
        vault = _P(settings.vault_path or "C:/Users/Danculus/my-second-brain")
        notes = vault / "04 Resources" / "Concepts" / "Agora Agents"
        ages = [_t.time() - p.stat().st_mtime
                for p in notes.rglob("synthesis-*.md")]
        return min(ages) if ages else 1e12
    except Exception:
        return 1e12


def format_synthesis() -> str:
    s = signals()
    flag = "🌋 GRAND SYNTHESIS LIKELY" if s["due"] else "🌡 building"
    return (f"🔭 *Synthesis Detector* — {flag}\n"
            f"• cross-coupling (bridges 48h): {s['bridge_recent']} vs {s['bridge_prior']} "
            f"→ accel ×{s['bridge_accel']}\n"
            f"• critical slowing: {s['open_falsifiers']} open falsifiers, "
            f"{s['deepened_recent']} closed in 48h\n"
            f"• synthesis pressure: {s['pressure']} (fires ≥1.8)")
