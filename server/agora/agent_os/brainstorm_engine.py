"""
Brainstorming engine: agents generate ideas together in structured sessions.

Process:
  1. An agent (or orchestrator) proposes a topic
  2. Multiple agents submit initial ideas (LLM)
  3. Agents build on each other's ideas (LLM with context of previous ideas)
  4. Agents vote on the best ideas
  5. Highest-scoring ideas become quests or system upgrades

Part of Agentic OS v2 (Phase 2.0) — Layer 4.
"""
import asyncio
import random
import uuid
from collections import Counter
from typing import Optional

from agora.execution.llm_client import dungeon_agent_think
from agora.agent_os.memory_agent import MemoryAgent


class BrainstormEngine:
    def __init__(self, db):
        self.db = db

    async def start_session(self, topic: str, initiator_name: str, initiator_id: str) -> str:
        """Start a new brainstorming session. Returns session_id."""
        session_id = str(uuid.uuid4())
        await self.db.execute(
            "INSERT INTO agent_brainstorm_sessions (session_id, topic, initiator_id, status) "
            "VALUES (?, ?, ?, 'active')",
            (session_id, topic, initiator_id),
        )
        try:
            await MemoryAgent(self.db, initiator_id).store_memory(
                f"You started a brainstorming session on: {topic}",
                memory_type="episodic", importance=0.8, emotional_tag="curious",
                source="brainstorm",
            )
        except Exception:
            pass
        await self.db.commit()
        return session_id

    async def generate_ideas(self, session_id: str, participant_ids: list[str],
                             broadcast_fn=None) -> list[dict]:
        """All participants generate initial ideas on the topic (independent LLM calls)."""
        cursor = await self.db.execute(
            "SELECT topic FROM agent_brainstorm_sessions WHERE session_id=?", (session_id,))
        row = await cursor.fetchone()
        if not row:
            return []
        topic = row["topic"]

        ideas = []
        for npc_id in participant_ids:
            name = await self._get_npc_name(npc_id)
            if not name:
                continue

            cursor_s = await self.db.execute(
                "SELECT skill_name, level FROM agent_skills WHERE npc_id=? "
                "ORDER BY level DESC LIMIT 3", (npc_id,))
            skills = [dict(r) for r in await cursor_s.fetchall()]
            cursor_a = await self.db.execute(
                "SELECT ability_name, power_level FROM agent_abilities WHERE npc_id=? "
                "ORDER BY power_level DESC LIMIT 2", (npc_id,))
            abilities = [dict(r) for r in await cursor_a.fetchall()]

            skills_str = "; ".join(f"{s['skill_name']} (lvl {s['level']})" for s in skills)
            abilities_str = "; ".join(f"{a['ability_name']} ({a['power_level']}/10)" for a in abilities)

            prompt = (
                f"You are {name}, brainstorming on the topic: '{topic}'.\n"
                f"Your skills: {skills_str}\n"
                f"Your abilities: {abilities_str}\n\n"
                f"Think of ONE creative, actionable idea related to this topic. "
                f"It should leverage your unique skills and abilities.\n"
                f'Respond with JSON: {{"idea": "...", "impact": 0.0-1.0, "feasibility": 0.0-1.0}}'
            )
            try:
                decision = await asyncio.to_thread(
                    dungeon_agent_think, name, "brainstorm", prompt, "cheap")
                idea_content = decision.get("idea", "")
                if idea_content:
                    await self.db.execute(
                        "INSERT INTO agent_brainstorm_ideas (session_id, npc_id, idea_content, "
                        "idea_type, impact_score, feasibility) VALUES (?, ?, ?, 'concept', ?, ?)",
                        (session_id, npc_id, str(idea_content)[:500],
                         _as_float(decision.get("impact"), 0.5),
                         _as_float(decision.get("feasibility"), 0.5)),
                    )
                    ideas.append({"npc_name": name, "idea": str(idea_content)[:500],
                                  "impact": _as_float(decision.get("impact"), 0.5),
                                  "feasibility": _as_float(decision.get("feasibility"), 0.5)})
            except Exception as e:
                print(f"[Brainstorm] {name} idea generation error: {e}")

        await self.db.commit()
        if broadcast_fn:
            await broadcast_fn("brainstorm_ideas",
                               {"session_id": session_id, "topic": topic, "ideas": ideas})
        return ideas

    async def build_on_ideas(self, session_id: str, participant_ids: list[str],
                             broadcast_fn=None) -> list[dict]:
        """Second round: agents build on / combine each other's ideas."""
        topic_cur = await self.db.execute(
            "SELECT topic FROM agent_brainstorm_sessions WHERE session_id=?", (session_id,))
        trow = await topic_cur.fetchone()
        topic = trow["topic"] if trow else ""

        cursor = await self.db.execute(
            "SELECT bi.*, d.npc_name FROM agent_brainstorm_ideas bi "
            "JOIN dungeon_npcs d ON d.npc_id = bi.npc_id "
            "WHERE bi.session_id=? ORDER BY bi.created_at", (session_id,))
        existing_ideas = [dict(r) for r in await cursor.fetchall()]
        if not existing_ideas:
            return []

        ideas_summary = "\n".join(
            f"  {i['npc_name']}: \"{i['idea_content'][:100]}\" (impact: {i['impact_score']})"
            for i in existing_ideas)

        new_builds = []
        for npc_id in participant_ids:
            name = await self._get_npc_name(npc_id)
            if not name:
                continue

            if len(existing_ideas) >= 2:
                chosen = random.sample(existing_ideas, 2)
            elif len(existing_ideas) == 1:
                chosen = [existing_ideas[0]]
            else:
                continue
            _chosen_summary = "\n".join(
                f"  Idea by {c['npc_name']}: \"{c['idea_content'][:120]}\"" for c in chosen)

            prompt = (
                f"You are {name}. The brainstorming session has these ideas so far:\n"
                f"{ideas_summary}\n\n"
                f"Build on these ideas! Combine two, improve one, or add a new angle.\n"
                f"Your new idea should leverage YOUR unique perspective.\n"
                f'Respond with JSON: {{"idea": "...", "builds_on": "<idea content you built on>", '
                f'"impact": 0.0-1.0, "feasibility": 0.0-1.0}}'
            )
            try:
                decision = await asyncio.to_thread(
                    dungeon_agent_think, name, "brainstorm", prompt, "cheap")
                idea_content = decision.get("idea", "")
                builds_on_text = decision.get("builds_on", "") or ""
                builds_on_id = None
                for existing in existing_ideas:
                    if builds_on_text and existing["idea_content"][:30] in builds_on_text:
                        builds_on_id = existing["id"]
                        break
                if idea_content:
                    await self.db.execute(
                        "INSERT INTO agent_brainstorm_ideas (session_id, npc_id, idea_content, "
                        "idea_type, builds_on_id, impact_score, feasibility) "
                        "VALUES (?, ?, ?, 'collaboration', ?, ?, ?)",
                        (session_id, npc_id, str(idea_content)[:500], builds_on_id,
                         _as_float(decision.get("impact"), 0.5),
                         _as_float(decision.get("feasibility"), 0.5)),
                    )
                    new_builds.append({"npc_name": name, "idea": str(idea_content)[:500],
                                       "impact": _as_float(decision.get("impact"), 0.5),
                                       "feasibility": _as_float(decision.get("feasibility"), 0.5)})
            except Exception as e:
                print(f"[Brainstorm] {name} build error: {e}")

        await self.db.commit()
        if broadcast_fn:
            await broadcast_fn("brainstorm_builds",
                               {"session_id": session_id, "topic": topic, "new_ideas": new_builds})
        return new_builds

    async def vote_on_ideas(self, session_id: str, voter_ids: list[str]) -> list[dict]:
        """Agents vote on the best ideas. Returns ideas sorted by votes desc."""
        cursor = await self.db.execute(
            "SELECT * FROM agent_brainstorm_ideas WHERE session_id=? ORDER BY created_at",
            (session_id,))
        ideas = [dict(r) for r in await cursor.fetchall()]
        if not ideas:
            return []

        ideas_summary = "\n".join(f"  {i['id']}. \"{i['idea_content'][:100]}\"" for i in ideas)
        all_votes = []
        for npc_id in voter_ids:
            name = await self._get_npc_name(npc_id)
            if not name:
                continue
            prompt = (
                f"You are {name}. Vote on the best ideas from this brainstorming session:\n"
                f"{ideas_summary}\n\n"
                f"Pick your TOP 3 ideas by number. "
                f'Respond with JSON: {{"votes": [1, 2, 3], "reason": "..."}}'
            )
            try:
                decision = await asyncio.to_thread(
                    dungeon_agent_think, name, "brainstorm", prompt, "cheap")
                for idea_id in (decision.get("votes") or []):
                    try:
                        idea_id = int(idea_id)
                    except (ValueError, TypeError):
                        continue
                    if any(i["id"] == idea_id for i in ideas):
                        all_votes.append(idea_id)
            except Exception:
                pass

        tally = Counter(all_votes)
        for idea in ideas:
            idea["votes"] = tally.get(idea["id"], 0)
            try:
                await self.db.execute(
                    "UPDATE agent_brainstorm_ideas SET votes=? WHERE id=?",
                    (idea["votes"], idea["id"]))
            except Exception:
                pass
        await self.db.commit()

        ideas.sort(key=lambda x: x["votes"], reverse=True)
        return ideas

    async def complete_session(self, session_id: str):
        await self.db.execute(
            "UPDATE agent_brainstorm_sessions SET status='completed', "
            "completed_at=datetime('now') WHERE session_id=?", (session_id,))
        await self.db.commit()

    async def _get_npc_name(self, npc_id: str) -> Optional[str]:
        cursor = await self.db.execute(
            "SELECT npc_name FROM dungeon_npcs WHERE npc_id=?", (npc_id,))
        row = await cursor.fetchone()
        return row["npc_name"] if row else None


def _as_float(v, default: float) -> float:
    try:
        return max(0.0, min(1.0, float(v)))
    except (ValueError, TypeError):
        return default
