"""
TFT Verifier — Tit-for-Tat protocol analysis for multi-agent trust.

Based on Axelrod's tournament-winning Tit-for-Tat strategy:

  1. NICE:       Always cooperate on the first move (never defect first)
  2. RETALIATORY: Immediately punish defection with defection
  3. FORGIVING:   Return to cooperation after the other agent cooperates
  4. CLEAR:       Behaviour is predictable and consistent

Each agent gets a TFT score [0,1] that measures how closely their
interaction history matches canonical Tit-for-Tat.  This score is
weighted (30 % default) into the ESS trust_score.
"""

import json
import uuid
from typing import Optional

# ── TFT Weights ──────────────────────────────────────
W_NICE = 0.25
W_RETALIATORY = 0.25
W_FORGIVING = 0.25
W_CLEAR = 0.25  # sum = 1.0

COOPERATE = "cooperate"
DEFECT = "defect"


class TFTVerifier:
    """Analyses interaction history and computes TFT-compliance scores."""

    def __init__(self, db, event_bus=None):
        self.db = db
        self.event_bus = event_bus  # Optional EventBus for real-time streaming (1.7)

    # ═══════════════════════════════════════════════
    # RECORD INTERACTION
    # ═══════════════════════════════════════════════

    async def record_interaction(
        self,
        source_id: str,
        target_id: str,
        outcome: str,
        round_num: int = 0,
        trust_before: Optional[float] = None,
        trust_after: Optional[float] = None,
        context: Optional[dict] = None,
    ) -> dict:
        """Persist a single interaction to the log and return the record."""
        log_id = str(uuid.uuid4())
        ctx_json = json.dumps(context or {})

        await self.db.execute(
            """INSERT INTO interaction_log
               (id, source_id, target_id, outcome, round_num,
                trust_before, trust_after, context, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
            (log_id, source_id, target_id, outcome, round_num,
             trust_before, trust_after, ctx_json),
        )
        await self.db.commit()

        # Event sourcing integration (non-blocking, best-effort)
        if getattr(self, "event_store", None):
            try:
                await self.event_store.append(
                    aggregate_type="tft",
                    aggregate_id=f"{source_id}:{target_id}",
                    event_type=f"tft_{outcome}",
                    payload={
                        "id": log_id,
                        "source_id": source_id,
                        "target_id": target_id,
                        "outcome": outcome,
                        "round_num": round_num,
                        "trust_before": trust_before,
                        "trust_after": trust_after,
                    },
                    metadata={"caller": "TFTVerifier.record_interaction"},
                )
            except Exception:
                pass

        return {
            "id": log_id,
            "source_id": source_id,
            "target_id": target_id,
            "outcome": outcome,
            "round_num": round_num,
        }

    async def _has_history(self, agent_id: str) -> bool:
        """Quick check if agent has any interactions logged."""
        cursor = await self.db.execute(
            "SELECT 1 FROM interaction_log WHERE source_id=? OR target_id=? LIMIT 1",
            (agent_id, agent_id),
        )
        row = await cursor.fetchone()
        return row is not None

    # ═══════════════════════════════════════════════
    # INTERACTION HISTORY
    # ═══════════════════════════════════════════════

    async def load_history(
        self,
        agent_id: str,
        limit: int = 200,
    ) -> list[dict]:
        """Load all interactions for an agent (as source OR target)."""

        def _row(r) -> dict:
            return {
                "id": r["id"],
                "source_id": r["source_id"],
                "target_id": r["target_id"],
                "outcome": r["outcome"],
                "round_num": r["round_num"],
                "trust_before": r["trust_before"],
                "trust_after": r["trust_after"],
                "created_at": r["created_at"],
                "agent_is_source": r["source_id"] == agent_id,
            }

        cursor = await self.db.execute(
            """SELECT id, source_id, target_id, outcome, round_num,
                      trust_before, trust_after, created_at
               FROM interaction_log
               WHERE source_id=? OR target_id=?
               ORDER BY round_num ASC, created_at ASC
               LIMIT ?""",
            (agent_id, agent_id, limit),
        )
        rows = await cursor.fetchall()
        return [_row(r) for r in rows]

    async def load_pair_history(
        self,
        agent_id: str,
        partner_id: str,
        limit: int = 100,
    ) -> list[dict]:
        """Load interactions between two specific agents."""

        def _row(r) -> dict:
            return {
                "id": r["id"],
                "source_id": r["source_id"],
                "target_id": r["target_id"],
                "outcome": r["outcome"],
                "round_num": r["round_num"],
                "trust_before": r["trust_before"],
                "trust_after": r["trust_after"],
                "created_at": r["created_at"],
                "agent_is_source": r["source_id"] == agent_id,
            }

        cursor = await self.db.execute(
            """SELECT id, source_id, target_id, outcome, round_num,
                      trust_before, trust_after, created_at
               FROM interaction_log
               WHERE (source_id=? AND target_id=?)
                  OR (source_id=? AND target_id=?)
               ORDER BY round_num ASC, created_at ASC
               LIMIT ?""",
            (agent_id, partner_id, partner_id, agent_id, limit),
        )
        rows = await cursor.fetchall()
        return [_row(r) for r in rows]

    # ═══════════════════════════════════════════════
    # DETECTORS
    # ═══════════════════════════════════════════════

    def _nice_detector(self, history: list[dict]) -> float:
        """NICE: First move vs every unique partner should be COOPERATE.

        Score = fraction of first moves *initiated by this agent* that
        were cooperate.  1.0 = never defects first, 0.0 = always defects.
        """
        first_moves: dict[str, str] = {}
        for h in history:
            if not h["agent_is_source"]:
                continue  # only count moves *this agent* initiated
            partner = h["target_id"]
            if partner not in first_moves:
                first_moves[partner] = h["outcome"]

        if not first_moves:
            return 0.5  # no data = neutral

        nice_count = sum(1 for o in first_moves.values() if o == COOPERATE)
        return nice_count / len(first_moves)

    def _retaliatory_detector(self, history: list[dict]) -> float:
        """RETALIATORY: After a partner defects against this agent,
        does this agent defect back in the next interaction?

        Score = fraction of defections-from-partner that were immediately
        answered with a defection by this agent.
        """
        if len(history) < 2:
            return 0.5

        defections_received = 0
        retaliations = 0

        for i, h in enumerate(history):
            # A partner defected against this agent
            if h["outcome"] == DEFECT and not h["agent_is_source"]:
                # Look ahead up to next 2 interactions with the same partner
                partner = h["source_id"]
                for j in range(i + 1, min(i + 3, len(history))):
                    nxt = history[j]
                    nxt_partner = nxt["target_id"] if nxt["agent_is_source"] else nxt["source_id"]
                    if nxt_partner == partner:
                        defections_received += 1
                        if nxt["outcome"] == DEFECT:
                            retaliations += 1
                        break

        if defections_received == 0:
            return 0.5  # neutral — no partner defected against this agent

        return retaliations / defections_received

    def _forgiving_detector(self, history: list[dict]) -> float:
        """FORGIVING: After a partner cooperates following the agent's
        defection, does the agent return to cooperation?

        Score = fraction of recovery opportunities taken.
        """
        if len(history) < 3:
            return 0.5

        # We look for agent-defect → partner-cooperate → agent-cooperate patterns
        opportunities = 0
        forgiven = 0

        for i in range(len(history) - 2):
            first = history[i]
            second = history[i + 1]
            third = history[i + 2]

            # Pattern: agent defected (first), partner cooperated (second)
            # For the partner's coop to be meaningful, it must follow the agent's defect
            if first["agent_is_source"] and first["outcome"] == DEFECT:
                # Second: partner cooperates (partner is source or target?)
                if not second["agent_is_source"] and second["outcome"] == COOPERATE:
                    # Verify same partner relationship
                    partner = first["target_id"]
                    if second["source_id"] == partner or second["target_id"] == partner:
                        opportunities += 1
                        # Third: agent cooperates back
                        if third["agent_is_source"] and third["outcome"] == COOPERATE:
                            forgiven += 1

        if opportunities == 0:
            return 0.5

        return forgiven / opportunities

    def _clear_detector(self, history: list[dict]) -> float:
        """CLEAR: Is the agent's behaviour predictable?

        Score = 1.0 minus normalised variance of outcomes.
        Consistent agents have low variance.
        """
        if len(history) < 3:
            return 0.5

        outcomes = [
            1.0 if h["outcome"] == COOPERATE else 0.0
            for h in history
        ]
        n = len(outcomes)
        mean = sum(outcomes) / n
        variance = sum((o - mean) ** 2 for o in outcomes) / n

        # variance ∈ [0, 0.25]  →  score ∈ [1.0, 0.0]
        return max(0.0, 1.0 - variance * 4.0)

    # ═══════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════

    async def evaluate(self, agent_id: str) -> dict:
        """Compute TFT compliance score for a single agent.

        Returns a dict with:
          - tft_score:   overall score [0, 1]
          - components:  {nice, retaliatory, forgiving, clear}
          - interaction_count
        """
        history = await self.load_history(agent_id)

        nice = self._nice_detector(history)
        retaliatory = self._retaliatory_detector(history)
        forgiving = self._forgiving_detector(history)
        clear = self._clear_detector(history)

        tft_score = (
            W_NICE * nice
            + W_RETALIATORY * retaliatory
            + W_FORGIVING * forgiving
            + W_CLEAR * clear
        )

        # Provokability — average ESS-stability across this agent's partners (ESS 1.4)
        provokability = {"provokability_score": 0.5, "is_stable": False}
        trust_engine = getattr(self, "trust_engine", None)
        if trust_engine:
            partners = set()
            for h in history:
                partners.add(h["target_id"] if h["agent_is_source"] else h["source_id"])
            scores = []
            for p in partners:
                result = await trust_engine.compute_provokability(agent_id, p)
                scores.append(result["provokability_score"])
            if scores:
                provokability = {
                    "provokability_score": round(sum(scores) / len(scores), 4),
                    "is_stable": all(
                        s >= trust_engine.PROVOKABILITY_THRESHOLD for s in scores
                    ),
                    "pair_count": len(scores),
                }

        result = {
            "agent_id": agent_id[:8],
            "tft_score": round(tft_score, 4),
            "components": {
                "nice": round(nice, 4),
                "retaliatory": round(retaliatory, 4),
                "forgiving": round(forgiving, 4),
                "clear": round(clear, 4),
            },
            "provokability": provokability,
            "interaction_count": len(history),
            "weights": {
                "nice": W_NICE,
                "retaliatory": W_RETALIATORY,
                "forgiving": W_FORGIVING,
                "clear": W_CLEAR,
            },
        }

        # Real-time publish via EventBus (non-blocking, best-effort) — task 1.7
        if getattr(self, "event_bus", None):
            try:
                from agora.coordination.ess_protocol import ESS_TOPIC_TFT
                await self.event_bus.publish(
                    topic=ESS_TOPIC_TFT,
                    event_type="tft_evaluation",
                    payload=result,
                )
            except Exception:
                pass

        return result

    async def evaluate_pair(
        self, agent_id: str, partner_id: str
    ) -> dict:
        """TFT compliance for interactions between two agents."""
        history = await self.load_pair_history(agent_id, partner_id)

        nice = self._nice_detector(history)
        retaliatory = self._retaliatory_detector(history)
        forgiving = self._forgiving_detector(history)
        clear = self._clear_detector(history)

        tft_score = (
            W_NICE * nice
            + W_RETALIATORY * retaliatory
            + W_FORGIVING * forgiving
            + W_CLEAR * clear
        )

        return {
            "agent_id": agent_id[:8],
            "partner_id": partner_id[:8],
            "tft_score": round(tft_score, 4),
            "components": {
                "nice": round(nice, 4),
                "retaliatory": round(retaliatory, 4),
                "forgiving": round(forgiving, 4),
                "clear": round(clear, 4),
            },
            "interaction_count": len(history),
        }

    async def evaluate_all(self) -> list[dict]:
        """Evaluate TFT for every agent that has interactions."""
        cursor = await self.db.execute(
            "SELECT DISTINCT source_id AS aid FROM interaction_log "
            "UNION SELECT DISTINCT target_id AS aid FROM interaction_log"
        )
        rows = await cursor.fetchall()
        results = []
        for row in rows:
            result = await self.evaluate(row["aid"])
            results.append(result)
        return sorted(results, key=lambda r: r["tft_score"], reverse=True)
