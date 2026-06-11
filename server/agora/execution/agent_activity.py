"""
Agent activity feed — the real work of every agent, surfaced for the live build log.

The dungeon's build log used to show essentially one agent (Dame Elara tending the vault graph,
which runs on a ~minute cadence), because every OTHER agent's real work happens through the brain
(replications, analogies, bridges, belief rulings, theory runs, outreach) and never reached the
log. This reads the ledgers each organ already keeps, attributes each entry to the agent who owns
that organ, and returns a unified, time-sorted feed the dungeon can broadcast — so the keep shows
ALL its agents working, with their genuine output, not a single curator on a loop.
"""
from __future__ import annotations

import json
from pathlib import Path

_SERVER = Path(__file__).resolve().parents[2]


def _load(name: str) -> list:
    try:
        d = json.loads((_SERVER / name).read_text(encoding="utf-8"))
        return d if isinstance(d, list) else d.get("items", [])
    except Exception:
        return []


def _clip(s: str, n: int = 48) -> str:
    s = (s or "").strip().replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"


def recent(n: int = 8) -> list[dict]:
    """Recent agent-attributed work across the organ ledgers, newest first.
    Each event: {ts, agent, eid, text}. eid maps to the dungeon entity when one exists."""
    ev: list[dict] = []

    def add(ts, agent, eid, text):
        if ts:
            ev.append({"ts": float(ts), "agent": agent, "eid": eid, "text": text})

    for r in _load(".replications.json"):
        add(r.get("ts"), "Artificer Rooke", "artificer",
            f"replicated a claim → {r.get('outcome', '?')}: {_clip(r.get('claim', ''))}")
    for a in _load(".analogies.json"):
        out = a.get("outcome", "")
        verb = "forged an analogy" if "no viable" not in out.lower() else "tested (and buried) an analogy"
        add(a.get("ts"), "Sage Mira", "scholar",
            f"{verb}: {_clip(a.get('mechanism', ''), 26)} → {_clip(a.get('target', ''), 26)}")
    for c in _load(".cartography.json"):
        add(c.get("ts"), "Cartographer Wren", "cartographer",
            f"charted a structural hole: {_clip(c.get('a', ''), 22)} ↔ {_clip(c.get('b', ''), 22)} ({c.get('outcome', '')})")
    for b in _load(".bounty.json"):
        verb = "killed a belief" if b.get("kill") else f"ruled {b.get('verdict', '')}"
        add(b.get("ts"), b.get("by") or "Sergeant Voss", "guard_l",
            f"{verb} under challenge: {_clip(b.get('target', ''))}")
    for t in _load(".theory.json"):
        add(t.get("ts"), "High Priest Orin", "priest",
            f"modeled a belief → {t.get('verdict', '')}: {_clip(t.get('title', ''))}")
    for s in _load(".scout.json"):
        add(s.get("ts"), "Shadow Kael", "rogue",
            f"scouted {s.get('repo', '')}#{s.get('issue', '')} → {s.get('outcome', '')}")
    for o in _load(".oracle.json"):
        add(o.get("ts"), "King Aldric", "king",
            f"called {o.get('side', '')} on a market ({o.get('agora_prob', '')} vs {o.get('market_prob', '')})")
    for p in _load(".press.json"):
        add(p.get("ts"), "Sage Mira", "scholar",
            f"drafted a public piece ({p.get('status', '')}): {_clip(p.get('title', ''))}")

    ev.sort(key=lambda e: e["ts"], reverse=True)
    return ev[:n]
