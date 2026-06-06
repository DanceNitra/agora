"""
Agent Lifecycle Manager — death when energy hits 0, rebirth with mutation after N ticks.

Runs inside the tick loop. Handles:
  - Death detection: energy ≤ 0 → status='dead'
  - Rebirth: dead for REBIRTH_TICKS → status='active' with mutated genome
  - Death spiral protection: agents that die too often get easier rebirth
"""
import json
import time
from typing import Any, Optional

from agora.lifecycle.genome_bridge import GenomeBridge

REBIRTH_TICKS = 5  # ticks an agent stays dead before rebirth


class AgentLifecycle:
    """Manages agent death and rebirth lifecycle."""

    def __init__(self, db):
        self.db = db
        # Track death ticks in memory (death_tick → agent_id)
        self._dead_agents: dict[str, int] = {}  # agent_id → tick_number_when_died
        self._death_counts: dict[str, int] = {}  # agent_id → total deaths
        self._tick_count: int = 0

    async def tick(self, app) -> list[dict]:
        """Run one lifecycle tick. Returns event list to broadcast."""
        events = []
        db = self.db
        self._tick_count += 1

        # 1. DETECT DEATH — agents with energy ≤ 0
        cursor = await db.execute(
            "SELECT agent_id, role, energy_balance, generation, genome "
            "FROM agent_identities WHERE status='active' AND energy_balance <= 0"
        )
        dying = await cursor.fetchall()

        for agent in dying:
            aid = agent["agent_id"]
            if aid in self._dead_agents:
                continue  # already marked for death

            genome = json.loads(agent["genome"] or "{}")
            self._dead_agents[aid] = self._tick_count
            self._death_counts[aid] = self._death_counts.get(aid, 0) + 1

            await db.execute(
                "UPDATE agent_identities SET status='dead', updated_at=datetime('now') WHERE agent_id=?",
                (aid,),
            )
            await db.commit()

            events.append({
                "type": "agent_died",
                "payload": {
                    "agent_id": aid[:8],
                    "role": agent["role"],
                    "generation": agent["generation"],
                    "total_deaths": self._death_counts[aid],
                }
            })

            # Store death event in DB
            await db.execute(
                "INSERT INTO events (event_type, source_id, aggregate_type, aggregate_id, payload) "
                "VALUES ('agent_died', ?, 'agent', ?, ?)",
                (aid, aid, json.dumps({
                    "role": agent["role"],
                    "generation": agent["generation"],
                    "energy_at_death": agent["energy_balance"],
                    "death_count": self._death_counts[aid],
                })),
            )
            await db.commit()

        # 2. REBIRTH — agents dead for REBIRTH_TICKS
        ready_to_rebirth = [
            (aid, died_at) for aid, died_at in self._dead_agents.items()
            if self._tick_count - died_at >= REBIRTH_TICKS
        ]

        for aid, died_at in ready_to_rebirth:
            result = await self._rebirth_agent(aid, db)
            if result:
                del self._dead_agents[aid]
                events.append({
                    "type": "agent_reborn",
                    "payload": result,
                })

        return events

    async def _rebirth_agent(self, agent_id: str, db) -> Optional[dict]:
        """Rebirth a dead agent with mutated genome and reset stats."""
        cursor = await db.execute(
            "SELECT agent_id, role, generation, genome FROM agent_identities WHERE agent_id=? AND status='dead'",
            (agent_id,),
        )
        agent = await cursor.fetchone()
        if not agent:
            return None

        old_genome = json.loads(agent["genome"] or "{}")
        gen = agent["generation"]
        role = agent["role"]

        # Mutate genome via GenesisForge (Gaussian drift, skill mutations, mode switches)
        new_genome = GenomeBridge.mutate_db_genome(old_genome, role, gen + 1)

        # Death spiral protection: more deaths → easier rebirth (higher starting energy)
        death_count = self._death_counts.get(agent_id, 0)
        starting_energy = min(50 + death_count * 5, 80)
        starting_trust = max(0.2, 0.3 - death_count * 0.02)

        await db.execute(
            "UPDATE agent_identities SET status='active', energy_balance=?, trust_score=?, "
            "generation=generation+1, genome=?, updated_at=datetime('now') WHERE agent_id=?",
            (starting_energy, starting_trust, json.dumps(new_genome), agent_id),
        )

        # Log rebirth event
        await db.execute(
            "INSERT INTO events (event_type, source_id, aggregate_type, aggregate_id, payload) "
            "VALUES ('agent_reborn', ?, 'agent', ?, ?)",
            (agent_id, agent_id, json.dumps({
                "new_generation": gen + 1,
                "new_energy": starting_energy,
                "new_trust": round(starting_trust, 3),
                "mutations": new_genome.get("_mutations_applied", 0),
                "death_count": death_count,
            })),
        )
        await db.commit()

        return {
            "agent_id": agent_id[:8],
            "role": role,
            "new_generation": gen + 1,
            "starting_energy": starting_energy,
            "starting_trust": round(starting_trust, 3),
            "death_count": death_count,
        }

    async def force_death(self, agent_id: str, db) -> bool:
        """Force an agent to die (for God Console !kill)."""
        cursor = await db.execute(
            "SELECT agent_id, role FROM agent_identities WHERE agent_id=? AND status='active'",
            (agent_id,),
        )
        if not await cursor.fetchone():
            return False
        await db.execute(
            "UPDATE agent_identities SET energy_balance=0, updated_at=datetime('now') WHERE agent_id=?",
            (agent_id,),
        )
        self._dead_agents[agent_id] = self._tick_count
        self._death_counts[agent_id] = self._death_counts.get(agent_id, 0) + 1
        await db.commit()
        return True

    async def get_stats(self) -> dict:
        """Return lifecycle stats."""
        return {
            "dead_count": len(self._dead_agents),
            "dead_agents": {k[:8]: v for k, v in self._dead_agents.items()},
            "total_deaths_by_agent": {k[:8]: v for k, v in self._death_counts.items()},
            "tick": self._tick_count,
        }
