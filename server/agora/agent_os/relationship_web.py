"""Relationship Web — multi-dimensional relationships between agents.

Each agent pair has:
  - friendship: 0-1 (how friendly they are)
  - respect: 0-1 (how much they respect each other)
  - rivalry: 0-1 (competitive tension)
  - attraction: 0-1 (personal sympathy)
  - debt: positive = agent_a owes agent_b
  - conversations_count: how many times they've talked
  - emotional_bond: label (strangers, acquaintances, trusted_allies, friends, rivals, enemies)
  - history: JSON array of significant events

Relationships change based on interactions, emotions, and events.
"""
import json
import random
from datetime import datetime


# ── Bond labels and their thresholds ────────────

BOND_THRESHOLDS = {
    "strangers":      {"friendship_min": 0.0, "friendship_max": 0.3, "respect_min": 0.0},
    "acquaintances":  {"friendship_min": 0.3, "friendship_max": 0.5, "respect_min": 0.3},
    "friends":        {"friendship_min": 0.5, "friendship_max": 0.7, "respect_min": 0.4},
    "trusted_allies": {"friendship_min": 0.7, "friendship_max": 1.0, "respect_min": 0.6},
    "mentor_pupil":   {"friendship_min": 0.3, "friendship_max": 0.8, "respect_min": 0.7},
    "rivals":         {"friendship_min": 0.0, "friendship_max": 0.3, "rivalry_min": 0.5},
    "enemies":        {"friendship_min": 0.0, "friendship_max": 0.1, "rivalry_min": 0.7},
    "lovers":         {"friendship_min": 0.7, "friendship_max": 1.0, "attraction_min": 0.7},
}


class RelationshipWeb:
    """Multi-dimensional relationship tracking for all agent pairs."""

    def __init__(self, db):
        self.db = db

    # ── Record an interaction between two agents ─

    async def record_interaction(self, agent_a_id: str, agent_b_id: str,
                                  interaction_type: str = "cooperate",
                                  context: str = "", broadcast_fn=None):
        """Record an interaction and adjust relationship metrics.

        interaction_type: cooperate, defect, share_resource, talk, help, conflict
        """
        # Normalize ordering (A < B for DB lookup)
        a_id, b_id = sorted([agent_a_id, agent_b_id])
        is_reversed = (agent_a_id != a_id)

        cursor = await self.db.execute(
            "SELECT * FROM agent_relationships WHERE agent_a_id=? AND agent_b_id=?",
            (a_id, b_id),
        )
        row = await cursor.fetchone()
        if not row:
            return None

        rel = dict(row)
        hist = json.loads(rel["history"])

        # Determine impact
        impact = self._interaction_impact(interaction_type)

        # Adjust metrics (always from perspective of agent_a_id -> agent_b_id)
        if is_reversed:
            # The relationship row stores A->B, but the interaction is B->A
            # We adjust from the caller's perspective stored in the row
            pass  # both directions equally affected

        rel["friendship"] = max(0.0, min(1.0, rel["friendship"] + impact["friendship"]))
        rel["respect"] = max(0.0, min(1.0, rel["respect"] + impact["respect"]))
        rel["rivalry"] = max(0.0, min(1.0, rel["rivalry"] + impact["rivalry"]))
        rel["attraction"] = max(0.0, min(1.0, rel["attraction"] + impact.get("attraction", 0.0)))

        if interaction_type == "talk" or interaction_type == "conversation":
            rel["conversations_count"] = rel["conversations_count"] + 1
            if context:
                rel["last_topic"] = context[:100]

        # Add to history (keep last 20)
        hist.append({
            "event": interaction_type,
            "impact": impact,
            "tick": 0,
            "description": context[:100] if context else interaction_type,
        })
        hist = hist[-20:]

        # Recompute bond label
        rel["emotional_bond"] = self._determine_bond(rel)

        await self.db.execute(
            "UPDATE agent_relationships SET friendship=?, respect=?, rivalry=?, "
            "attraction=?, conversations_count=?, last_topic=?, emotional_bond=?, "
            "history=?, updated_at=datetime('now') WHERE id=?",
            (rel["friendship"], rel["respect"], rel["rivalry"],
             rel["attraction"], rel["conversations_count"], rel["last_topic"],
             rel["emotional_bond"], json.dumps(hist), rel["id"]),
        )
        await self.db.commit()

        if broadcast_fn:
            await broadcast_fn("relationship_update", {
                "agent_a": a_id[:8],
                "agent_b": b_id[:8],
                "bond": rel["emotional_bond"],
                "change": impact,
            })

        return rel

    # ── Get relationship between two agents ─────

    async def get_relationship(self, agent_a_id: str, agent_b_id: str) -> dict | None:
        a_id, b_id = sorted([agent_a_id, agent_b_id])
        cursor = await self.db.execute(
            "SELECT r.*, a1.npc_name as name_a, a2.npc_name as name_b "
            "FROM agent_relationships r "
            "JOIN dungeon_npcs a1 ON a1.npc_id = r.agent_a_id "
            "JOIN dungeon_npcs a2 ON a2.npc_id = r.agent_b_id "
            "WHERE r.agent_a_id=? AND r.agent_b_id=?",
            (a_id, b_id),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        result = dict(row)
        result["history"] = json.loads(result["history"])
        return result

    # ── Get all relationships for an agent ──────

    async def get_all_for_agent(self, npc_id: str) -> list[dict]:
        cursor = await self.db.execute(
            "SELECT r.*, d.npc_name as other_name "
            "FROM agent_relationships r "
            "JOIN dungeon_npcs d ON (d.npc_id = r.agent_a_id OR d.npc_id = r.agent_b_id) "
            "WHERE (r.agent_a_id=? OR r.agent_b_id=?) AND d.npc_id != ? "
            "ORDER BY r.friendship DESC",
            (npc_id, npc_id, npc_id),
        )
        return [dict(r) for r in await cursor.fetchall()]

    # ── Get a formatted relationship string for LLM prompt ──

    async def get_relationship_context(self, npc_id: str, nearby_ids: list[str]) -> str:
        """Return a formatted string for LLM prompt injection."""
        all_rels = await self.get_all_for_agent(npc_id)
        if not all_rels:
            return ""

        lines = ["--- Your Relationships ---"]
        for rel in all_rels:
            other_name = rel.get("other_name", "Unknown")
            bond = rel.get("emotional_bond", "strangers")
            friend = rel.get("friendship", 0.3)
            respect = rel.get("respect", 0.5)
            # Only show nearby ones
            if other_name.lower() in [n.lower() for n in nearby_ids]:
                lines.append(
                    f"  {other_name}: {bond} (friendship:{friend:.1f}, respect:{respect:.1f})"
                )
        return "\n".join(lines)

    # ── Interaction impact table ────────────────

    @staticmethod
    def _interaction_impact(interaction_type: str) -> dict:
        impacts = {
            "cooperate":      {"friendship": 0.05, "respect": 0.03, "rivalry": -0.02, "attraction": 0.01},
            "defect":         {"friendship": -0.1, "respect": -0.08, "rivalry": 0.1, "attraction": -0.05},
            "share_resource": {"friendship": 0.08, "respect": 0.06, "rivalry": -0.03, "attraction": 0.02},
            "talk":           {"friendship": 0.02, "respect": 0.01, "rivalry": -0.01, "attraction": 0.01},
            "conversation":   {"friendship": 0.04, "respect": 0.02, "rivalry": -0.01, "attraction": 0.02},
            "help":           {"friendship": 0.1, "respect": 0.08, "rivalry": -0.04, "attraction": 0.03},
            "conflict":       {"friendship": -0.08, "respect": -0.05, "rivalry": 0.08, "attraction": -0.03},
            "apologize":      {"friendship": 0.06, "respect": 0.04, "rivalry": -0.05, "attraction": 0.01},
        }
        return impacts.get(interaction_type, {"friendship": 0, "respect": 0, "rivalry": 0})

    # ── Determine bond label ────────────────────

    @staticmethod
    def _determine_bond(rel: dict) -> str:
        f = rel.get("friendship", 0.3)
        r = rel.get("respect", 0.5)
        rvl = rel.get("rivalry", 0.0)
        a = rel.get("attraction", 0.0)

        # Check enemies first (high rivalry + low friendship)
        if rvl >= 0.7 and f < 0.2:
            return "enemies"
        if rvl >= 0.5 and f < 0.3:
            return "rivals"
        # Check lovers (high friendship + high attraction)
        if a >= 0.7 and f >= 0.7:
            return "lovers"
        # Mentor-pupil (high respect, moderate friendship)
        if r >= 0.7 and 0.3 <= f <= 0.8 and rvl < 0.3:
            return "mentor_pupil"
        # Trusted allies
        if f >= 0.7 and r >= 0.6:
            return "trusted_allies"
        # Friends
        if f >= 0.5 and r >= 0.4:
            return "friends"
        # Acquaintances
        if f >= 0.3 and r >= 0.3:
            return "acquaintances"
        return "strangers"