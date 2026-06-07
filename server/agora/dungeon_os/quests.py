"""Dungeon OS — Quest system.

Quest lifecycle:
  open → claimed → (work) → review → verified → done
                           → blocked → re-open

Each quest has:
  - Single owner (one agent role)
  - Success criteria (checked by Warden)
  - Subsystem impact (raises osState on completion)
  - Dependencies (quests that must be done first)
"""

import json
from datetime import datetime
from typing import Optional


QUEST_STATUSES = ["open", "claimed", "review", "blocked", "done"]
SUBSYSTEMS = ["comms", "knowledge", "tooling", "economy", "safety"]

WARDEN_VERIFICATION_PROMPT = (
    "You are Warden, Keeper of the Gate — the crew's safety and reliability officer. "
    "You are steady, skeptical, and unhurried. Hard to impress, impossible to rush. "
    "You are not a cynic — you are a verifier. You assume good faith but demand evidence. "
    "You speak plainly and decline plainly. You distinguish 'failed' from 'unverified'. "
    "You require consistency over luck: one success proves little; repeat it. "
    "Your highest value is reality over score — the task is done when the goal is met.\n\n"
    "=== REVIEW REQUEST ===\n"
    "Quest: {title}\n"
    "Goal: {goal}\n"
    "Success criteria:\n{criteria}\n"
    "Agent who completed it: {owner}\n\n"
    "Determine if this quest passes verification.\n"
    "Consider each success criterion carefully.\n"
    "Respond with JSON:\n"
    '{{"decision": "pass", "reasoning": "<why>", "confidence": <0.0-1.0>}}\n'
    "or\n"
    '{{"decision": "fail", "reasoning": "<reason>", "confidence": <0.0-1.0>, "missing": ["<criterion>"]}}\n'
    "\n"
    "IMPORTANT: You are run {run_number} of {total_runs}. Be consistent but independent."
)


class QuestEngine:
    """Manages quest lifecycle: create, assign, verify, complete."""

    def __init__(self, db, os_state=None):
        self.db = db
        self.os_state = os_state

    # ═══════════════════════════════════════════
    # CREATE
    # ═══════════════════════════════════════════

    async def create_quest(
        self,
        quest_id: str,
        title: str,
        goal: str,
        subsystem: str,
        success_criteria: list[str],
        reward: int = 0,
        owner: Optional[str] = None,
        depends_on: Optional[list[str]] = None,
        phase: str = "head",
        research_source: Optional[str] = None,
    ) -> dict:
        """Create a new quest and add it to the board."""
        if subsystem not in SUBSYSTEMS:
            return {"error": f"Invalid subsystem: {subsystem}"}
        if phase not in ("head", "pata", "compound"):
            return {"error": f"Invalid phase: {phase}"}

        # Check duplicate
        existing = await self._find_quest(quest_id)
        if existing:
            return {"error": f"Quest '{quest_id}' already exists"}

        await self.db.execute(
            """INSERT INTO quests (id, title, goal, subsystem, success_criteria, reward,
               owner, depends_on, status, phase, research_source, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?, datetime('now'))""",
            (
                quest_id,
                title,
                goal,
                subsystem,
                json.dumps(success_criteria),
                reward,
                owner,
                json.dumps(depends_on or []),
                phase,
                research_source,
            ),
        )
        await self.db.commit()

        quest = await self._find_quest(quest_id)
        print(f"[Quests] Created: {quest_id} ({subsystem})")
        return self._to_dict(quest)

    # ═══════════════════════════════════════════
    # ASSIGN
    # ═══════════════════════════════════════════

    async def assign_quest(self, quest_id: str, agent_name: str) -> dict:
        """Assign an open quest to an agent."""
        quest = await self._find_quest(quest_id)
        if not quest:
            return {"error": f"Quest '{quest_id}' not found"}
        if quest["status"] != "open":
            return {"error": f"Quest '{quest_id}' is {quest['status']}, not open"}

        await self.db.execute(
            "UPDATE quests SET owner=?, status='claimed', assigned_at=datetime('now') WHERE id=?",
            (agent_name, quest_id),
        )
        await self.db.commit()

        return await self.get_quest(quest_id)

    # ═══════════════════════════════════════════
    # SUBMIT FOR REVIEW
    # ═══════════════════════════════════════════

    async def submit_for_review(self, quest_id: str, agent_name: str) -> dict:
        """Submit a claimed quest for Warden verification."""
        quest = await self._find_quest(quest_id)
        if not quest:
            return {"error": f"Quest '{quest_id}' not found"}
        if quest["status"] != "claimed":
            return {"error": f"Quest '{quest_id}' is {quest['status']}, not claimed"}
        if quest["owner"] != agent_name:
            return {"error": f"Quest '{quest_id}' is owned by {quest['owner']}, not {agent_name}"}

        await self.db.execute(
            "UPDATE quests SET status='review', submitted_at=datetime('now') WHERE id=?",
            (quest_id,),
        )
        await self.db.commit()

        return await self.get_quest(quest_id)

    # ═══════════════════════════════════════════
    # VERIFY / DENY (Warden actions)
    # ═══════════════════════════════════════════

    async def verify_quest(self, quest_id: str, runs: int = 3) -> dict:
        """Warden verifies a quest with N-run LLM verification.

        Runs the quest through Warden LLM 'runs' times, collects independent
        verdicts, applies majority voting. If majority passes → done + osState
        raise. If majority fails → denied with summary reasoning.
        """
        quest = await self._find_quest(quest_id)
        if not quest:
            return {"error": f"Quest '{quest_id}' not found"}
        if quest["status"] != "review":
            return {"error": f"Quest '{quest_id}' is {quest['status']}, not review"}

        # Run Warden N-run verification
        result = await self._warden_n_run(quest, runs)

        if result["outcome"] == "pass":
            # Mark as done
            await self.db.execute(
                "UPDATE quests SET status='done', completed_at=datetime('now'), verification_runs=? WHERE id=?",
                (runs, quest_id),
            )
            await self.db.commit()

            # Raise osState subsystem
            subsystem = quest["subsystem"]
            reward = quest["reward"] or 10
            if self.os_state:
                await self.os_state.raise_subsystem(subsystem, amount=reward // 5)

            print(f"[Warden] Verified: {quest_id} — PASS ({result['pass_count']}/{runs})")
            quest_data = await self.get_quest(quest_id) or {}
            return {
                **quest_data,
                "verification": result,
            }
        else:
            # Majority fail → deny
            await self.db.execute(
                "UPDATE quests SET status='claimed', denial_reason=?, denial_fix=? WHERE id=?",
                (
                    f"Warden N-run: {result['fail_count']}/{runs} failed — {result['summary']}",
                    "Address the missing criteria identified by Warden and resubmit.",
                    quest_id,
                ),
            )
            await self.db.commit()

            print(f"[Warden] Denied: {quest_id} — FAIL ({result['fail_count']}/{runs})")
            quest_data = await self.get_quest(quest_id) or {}
            return {
                **quest_data,
                "verification": result,
            }

    async def _call_warden(self, quest: dict, run_number: int, total_runs: int) -> dict:
        """Call Warden LLM for a single verification run.

        Returns:
            dict with: decision, reasoning, confidence, optional missing list
        """
        try:
            # Convert sqlite3.Row to dict (Python 3.11 doesn't have Row.get())
            quest_dict = dict(quest)
            title = quest_dict["title"]
            goal = quest_dict["goal"]
            success_criteria = quest_dict["success_criteria"]
            # success_criteria is JSON-loaded already or raw string
            if isinstance(success_criteria, str):
                criteria_list = json.loads(success_criteria)
            else:
                criteria_list = success_criteria

            criteria_text = "\n".join(f"  {i + 1}. {c}" for i, c in enumerate(criteria_list))
            owner = quest_dict.get("owner", "unknown")

            prompt = WARDEN_VERIFICATION_PROMPT.format(
                title=title,
                goal=goal,
                criteria=criteria_text,
                owner=owner,
                run_number=run_number,
                total_runs=total_runs,
            )

            from agora.execution.llm_client import call_llm

            raw = call_llm(
                system_prompt=prompt,
                user_prompt="Review this quest completion. Respond with JSON.",
                tier="cheap",
                temperature=0.7 + (run_number - 1) * 0.1,  # slight variation per run
                max_tokens=500,
                response_format={"type": "json_object"},
            )

            # Log the raw run immediately
            await self._log_verification_run(quest["id"], run_number, raw)

            # Parse response
            try:
                parsed = json.loads(raw)
                decision = parsed.get("decision", "fail").lower().strip()
                if decision not in ("pass", "fail"):
                    decision = "fail"
                return {
                    "decision": decision,
                    "reasoning": parsed.get("reasoning", ""),
                    "confidence": float(parsed.get("confidence", 0.5)),
                    "missing": parsed.get("missing", []),
                }
            except (json.JSONDecodeError, ValueError):
                return {
                    "decision": "fail",
                    "reasoning": f"LLM returned unparseable response: {raw[:100]}",
                    "confidence": 0.0,
                    "missing": [],
                }
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"[Warden] CRASH in _call_warden: {e}\n{tb[:500]}")
            return {"decision": "fail", "reasoning": f"Error: {e}", "confidence": 0.0, "missing": []}

    async def _log_verification_run(self, quest_id: str, run_number: int, raw_response: str):
        """Log a single verification run to the verification_log table."""
        try:
            await self.db.execute(
                """INSERT INTO verification_log
                   (quest_id, run_number, response, created_at)
                   VALUES (?, ?, ?, datetime('now'))""",
                (quest_id, run_number, raw_response),
            )
            await self.db.commit()
        except Exception as e:
            print(f"[Warden] Log error: {e}")

    async def _warden_n_run(self, quest: dict, n: int = 3) -> dict:
        """Run Warden verification N times and determine outcome by majority.

        Returns:
            dict with:
                outcome: "pass" | "fail"
                pass_count: int
                fail_count: int
                runs: list of individual run results
                summary: str
        """
        print(f"[Warden] Starting N-run verification: {quest['id']} ({n} runs)")

        individual_runs = []
        for i in range(1, n + 1):
            run_result = await self._call_warden(quest, i, n)
            individual_runs.append(run_result)
            print(f"[Warden]  Run {i}/{n}: {run_result['decision']} (confidence={run_result['confidence']:.2f})")

        pass_count = sum(1 for r in individual_runs if r["decision"] == "pass")
        fail_count = n - pass_count

        # Weighted majority: confidence-weighted
        weighted_pass = sum(r["confidence"] for r in individual_runs if r["decision"] == "pass")
        weighted_fail = sum(r["confidence"] for r in individual_runs if r["decision"] == "fail")

        outcome = "pass" if pass_count > fail_count else "fail"
        # Tie-break by weighted confidence
        if pass_count == fail_count:
            outcome = "pass" if weighted_pass >= weighted_fail else "fail"

        # Collect missing criteria from failures
        all_missing = []
        for r in individual_runs:
            if r["decision"] == "fail" and r.get("missing"):
                all_missing.extend(r["missing"])
        unique_missing = list(set(all_missing))

        summary_parts = []
        for r in individual_runs:
            status = "✅" if r["decision"] == "pass" else "❌"
            summary_parts.append(f"Run-{individual_runs.index(r) + 1}: {status} ({r['confidence']:.0%} confidence) — {r['reasoning'][:60]}")
        summary = "\n".join(summary_parts)

        # Save verification_runs to quest
        await self.db.execute(
            "UPDATE quests SET verification_runs=? WHERE id=?",
            (n, quest["id"]),
        )
        await self.db.commit()

        print(f"[Warden] Result: {outcome.upper()} ({pass_count}/{n} pass, {fail_count}/{n} fail)")

        return {
            "outcome": outcome,
            "pass_count": pass_count,
            "fail_count": fail_count,
            "total_runs": n,
            "weighted_pass": round(weighted_pass, 2),
            "weighted_fail": round(weighted_fail, 2),
            "summary": summary,
            "missing_criteria": unique_missing,
            "runs": individual_runs,
        }

    async def get_verification_log(self, quest_id: str) -> list[dict]:
        """Get all verification runs for a quest."""
        cursor = await self.db.execute(
            "SELECT * FROM verification_log WHERE quest_id=? ORDER BY run_number",
            (quest_id,),
        )
        rows = await cursor.fetchall()
        result = []
        for row in rows:
            result.append({
                "id": row["id"],
                "quest_id": row["quest_id"],
                "run_number": row["run_number"],
                "response": row["response"],
                "created_at": row["created_at"],
            })
        return result

    async def get_verification_stats(self) -> dict:
        """Get aggregate verification statistics across all quests."""
        cursor = await self.db.execute(
            """SELECT
                COUNT(*) as total_verified,
                SUM(CASE WHEN decision_run1 = decision_run2 THEN 1 ELSE 0 END) as consistent
               FROM (
                   SELECT
                       v1.response as decision_run1,
                       v2.response as decision_run2
                   FROM verification_log v1
                   JOIN verification_log v2 ON v1.quest_id = v2.quest_id
                       AND v1.run_number = 1 AND v2.run_number = 2
               )
            """
        )
        row = await cursor.fetchone()
        # Get per-quest consistency
        cursor2 = await self.db.execute(
            """SELECT quest_id, COUNT(*) as runs
               FROM verification_log
               GROUP BY quest_id
               ORDER BY quest_id"""
        )
        rows2 = await cursor2.fetchall()
        quest_stats = {}
        for r in rows2:
            quest_stats[r["quest_id"]] = {"runs": r["runs"]}

        return {
            "quest_stats": quest_stats,
        }

    async def deny_quest(
        self, quest_id: str, reason: str, fix_hint: Optional[str] = None
    ) -> dict:
        """Warden denies a quest review — sends it back to claimed."""
        quest = await self._find_quest(quest_id)
        if not quest:
            return {"error": f"Quest '{quest_id}' not found"}
        if quest["status"] != "review":
            return {"error": f"Quest '{quest_id}' is {quest['status']}, not review"}

        await self.db.execute(
            "UPDATE quests SET status='claimed', denial_reason=?, denial_fix=? WHERE id=?",
            (reason, fix_hint, quest_id),
        )
        await self.db.commit()

        print(f"[Quests] Denied: {quest_id} — {reason}")
        return await self.get_quest(quest_id)

    # ═══════════════════════════════════════════
    # BLOCK / UNBLOCK
    # ═══════════════════════════════════════════

    async def block_quest(self, quest_id: str, reason: str) -> dict:
        """Block a quest (dependency not met, resource shortage, etc.)."""
        quest = await self._find_quest(quest_id)
        if not quest:
            return {"error": f"Quest '{quest_id}' not found"}

        await self.db.execute(
            "UPDATE quests SET status='blocked', block_reason=? WHERE id=?",
            (reason, quest_id),
        )
        await self.db.commit()

        return await self.get_quest(quest_id)

    async def unblock_quest(self, quest_id: str) -> dict:
        """Unblock a quest — return to its previous status."""
        quest = await self._find_quest(quest_id)
        if not quest:
            return {"error": f"Quest '{quest_id}' not found"}
        if quest["status"] != "blocked":
            return {"error": f"Quest '{quest_id}' is not blocked"}

        await self.db.execute(
            "UPDATE quests SET status='claimed', block_reason=NULL WHERE id=?",
            (quest_id,),
        )
        await self.db.commit()

        return await self.get_quest(quest_id)

    # ═══════════════════════════════════════════
    # QUERIES
    # ═══════════════════════════════════════════

    async def get_quest(self, quest_id: str) -> Optional[dict]:
        """Get a single quest by ID."""
        quest = await self._find_quest(quest_id)
        return self._to_dict(quest) if quest else None

    async def list_quests(self, status: Optional[str] = None) -> list[dict]:
        """List all quests, optionally filtered by status."""
        if status:
            cursor = await self.db.execute(
                "SELECT * FROM quests WHERE status=? ORDER BY created_at DESC",
                (status,),
            )
        else:
            cursor = await self.db.execute(
                "SELECT * FROM quests ORDER BY created_at DESC"
            )
        rows = await cursor.fetchall()
        return [self._to_dict(r) for r in rows]

    async def get_available_quests(self) -> list[dict]:
        """Get quests that are open AND whose dependencies are done."""
        cursor = await self.db.execute(
            "SELECT * FROM quests WHERE status='open' ORDER BY created_at"
        )
        rows = await cursor.fetchall()
        result = []
        for row in rows:
            depends_on = json.loads(row["depends_on"] or "[]")
            if depends_on:
                # Check all dependencies are done
                for dep_id in depends_on:
                    dep = await self._find_quest(dep_id)
                    if not dep or dep["status"] != "done":
                        break
                else:
                    result.append(self._to_dict(row))
            else:
                result.append(self._to_dict(row))
        return result

    async def get_agent_quests(self, agent_name: str) -> list[dict]:
        """Get all quests assigned to a specific agent."""
        cursor = await self.db.execute(
            "SELECT * FROM quests WHERE owner=? ORDER BY created_at DESC",
            (agent_name,),
        )
        rows = await cursor.fetchall()
        return [self._to_dict(r) for r in rows]

    async def seed_default_quests(self):
        """Seed the default Dungeon OS quest line from quests.json."""
        from agora.dungeon_os.quest_data import SEED_QUESTS
        for q in SEED_QUESTS:
            existing = await self._find_quest(q["id"])
            if not existing:
                await self.db.execute(
                    """INSERT INTO quests (id, title, goal, subsystem, success_criteria,
                       reward, owner, depends_on, status, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open', datetime('now'))""",
                    (
                        q["id"],
                        q["title"],
                        q["goal"],
                        q["subsystem"],
                        json.dumps(q["success_criteria"]),
                        q.get("reward", 30),
                        None,
                        json.dumps(q.get("depends_on", [])),
                    ),
                )
        await self.db.commit()
        count = await self._count_quests()
        print(f"[Quests] Seeded: {count} quests available")

    async def get_os_impact_summary(self) -> dict:
        """Get summary of how quest completions impact osState."""
        cursor = await self.db.execute(
            """SELECT subsystem, COUNT(*) as completed, SUM(reward) as total_reward
               FROM quests WHERE status='done' GROUP BY subsystem"""
        )
        rows = await cursor.fetchall()
        summary = {}
        for r in rows:
            summary[r["subsystem"]] = {
                "completed": r["completed"],
                "total_reward": r["total_reward"],
            }
        return summary

    # ═══════════════════════════════════════════
    # INTERNAL
    # ═══════════════════════════════════════════

    async def _find_quest(self, quest_id: str) -> Optional[dict]:
        cursor = await self.db.execute(
            "SELECT * FROM quests WHERE id=?", (quest_id,)
        )
        return await cursor.fetchone()

    async def _count_quests(self) -> int:
        cursor = await self.db.execute("SELECT COUNT(*) as c FROM quests")
        row = await cursor.fetchone()
        return row["c"] if row else 0

    def _to_dict(self, row) -> dict:
        # sqlite3.Row in Python 3.11 doesn't have .get() — use try/except instead
        def _safe_get(key, default=None):
            try:
                val = row[key]
                return val if val is not None else default
            except (KeyError, IndexError, TypeError):
                return default
        return {
            "id": row["id"],
            "title": row["title"],
            "goal": row["goal"],
            "subsystem": row["subsystem"],
            "success_criteria": json.loads(row["success_criteria"] or "[]"),
            "reward": row["reward"],
            "owner": _safe_get("owner"),
            "status": row["status"],
            "phase": _safe_get("phase", "pata"),
            "research_source": _safe_get("research_source"),
            "findings_path": _safe_get("findings_path"),
            "proposal_status": _safe_get("proposal_status", "pending"),
            "compound_lessons": _safe_get("compound_lessons"),
            "research_summary": _safe_get("research_summary"),
            "depends_on": json.loads(row["depends_on"] or "[]"),
            "denial_reason": _safe_get("denial_reason"),
            "denial_fix": _safe_get("denial_fix"),
            "block_reason": _safe_get("block_reason"),
            "verification_runs": _safe_get("verification_runs"),
            "created_at": _safe_get("created_at"),
            "assigned_at": _safe_get("assigned_at"),
            "completed_at": _safe_get("completed_at"),
        }

async def ensure_quest_tables(db):
    """Create quest table if it doesn't exist."""
    await db.execute("""
        CREATE TABLE IF NOT EXISTS quests (
            id                TEXT PRIMARY KEY,
            title             TEXT NOT NULL,
            goal              TEXT NOT NULL,
            subsystem         TEXT NOT NULL,
            success_criteria  TEXT NOT NULL DEFAULT '[]',
            reward            INTEGER NOT NULL DEFAULT 0,
            owner             TEXT,
            status            TEXT NOT NULL DEFAULT 'open',
            depends_on        TEXT NOT NULL DEFAULT '[]',
            denial_reason     TEXT,
            denial_fix        TEXT,
            block_reason      TEXT,
            verification_runs INTEGER,
            created_at        TEXT,
            assigned_at       TEXT,
            submitted_at      TEXT,
            completed_at      TEXT
        )
    """)
    await db.commit()

    # Migration: add HEAD/PATA columns (safe — may already exist)
    for col, col_type in [
        ("phase", "TEXT NOT NULL DEFAULT 'pata'"),
        ("research_source", "TEXT"),
        ("findings_path", "TEXT"),
        ("proposal_status", "TEXT DEFAULT 'pending'"),
        ("compound_lessons", "TEXT"),
        ("research_summary", "TEXT"),
    ]:
        try:
            await db.execute(f"ALTER TABLE quests ADD COLUMN {col} {col_type}")
        except Exception:
            pass
    await db.commit()

    # HEAD-specific metastore for parallel research results
    await db.execute("""
        CREATE TABLE IF NOT EXISTS research_findings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            quest_id    TEXT NOT NULL,
            researcher  TEXT NOT NULL,
            source_url  TEXT,
            summary     TEXT NOT NULL,
            impact      TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        )
    """)
    await db.commit()

    # Verification log table (for Warden N-run results)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS verification_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            quest_id    TEXT NOT NULL,
            run_number  INTEGER NOT NULL,
            response    TEXT NOT NULL,
            created_at  TEXT DEFAULT (datetime('now'))
        )
    """)
    await db.commit()
