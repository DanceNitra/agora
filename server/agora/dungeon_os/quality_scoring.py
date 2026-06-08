"""Quality Scoring — trust and quality tracking for research outputs.

Phase 3: Each research finding, CEO/CTO evaluation, and compound lesson
gets a quality score. This enables:
  - Tracking research quality trends over time
  - Identifying which researchers produce the best output
  - Detecting quality degradation before it hurts decisions
  - Weighting corporation memory by source quality
"""

import json
from datetime import datetime


class QualityTracker:
    """Tracks quality scores for all research outputs and evaluations.

    Adds quality_score columns to research_findings and tracks
    evaluation quality over time for trend analysis.

    Schema additions (done via ensure_tables):
      - research_findings.quality_score REAL DEFAULT 0.5
      - research_findings.evaluator_feedback TEXT
      - evaluation_quality table (per-cycle stats)
    """

    QUALITY_SCHEMA = """
    CREATE TABLE IF NOT EXISTS evaluation_quality (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        quest_id        TEXT NOT NULL,
        evaluator_role  TEXT NOT NULL,       -- ceo | cto
        approved        INTEGER NOT NULL,
        score           REAL NOT NULL,       -- the raw score from evaluation
        quality_weight  REAL DEFAULT 1.0,    -- confidence in this evaluation
        response_time   REAL,                -- seconds to respond
        created_at      TEXT DEFAULT (datetime('now'))
    );
    CREATE INDEX IF NOT EXISTS idx_eval_quality_quest ON evaluation_quality(quest_id);

    -- Add quality_score column to research_findings if not exists
    -- Managed via ALTER TABLE in ensure_tables
    """

    TREND_SCHEMA = """
    CREATE TABLE IF NOT EXISTS quality_trends (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        tick_count      INTEGER NOT NULL,
        metric_name     TEXT NOT NULL,        -- approval_rate | avg_score | memory_impact
        metric_value    REAL NOT NULL,
        sample_size     INTEGER NOT NULL,
        created_at      TEXT DEFAULT (datetime('now'))
    );
    CREATE INDEX IF NOT EXISTS idx_quality_trends ON quality_trends(tick_count);
    """

    def __init__(self, db):
        self.db = db

    async def ensure_tables(self):
        """Create quality tracking tables."""
        # aiosqlite can only execute one statement at a time
        for schema_name, schema in [("QUALITY", self.QUALITY_SCHEMA), ("TREND", self.TREND_SCHEMA)]:
            statements = [s.strip() for s in schema.split(";") if s.strip()]
            for stmt in statements:
                try:
                    await self.db.execute(stmt)
                except Exception as e:
                    print(f"[Quality] {schema_name} stmt skipped: {e}")
        await self.db.commit()

        # Add quality_score to research_findings if missing
        try:
            await self.db.execute(
                "ALTER TABLE research_findings ADD COLUMN quality_score REAL DEFAULT 0.5"
            )
            await self.db.commit()
        except Exception:
            pass  # Already exists

        try:
            await self.db.execute(
                "ALTER TABLE research_findings ADD COLUMN evaluator_feedback TEXT"
            )
            await self.db.commit()
        except Exception:
            pass  # Already exists

    async def record_evaluation(
        self,
        quest_id: str,
        evaluator_role: str,
        approved: bool,
        score: float,
        quality_weight: float = 1.0,
        response_time: float = 0.0,
    ):
        """Record an evaluation quality entry."""
        await self.ensure_tables()
        await self.db.execute(
            """INSERT INTO evaluation_quality
               (quest_id, evaluator_role, approved, score, quality_weight, response_time)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (quest_id, evaluator_role, 1 if approved else 0, score, quality_weight, response_time),
        )
        await self.db.commit()

    async def record_trend(
        self, tick_count: int, metric_name: str, metric_value: float, sample_size: int
    ):
        """Record a quality trend data point."""
        await self.ensure_tables()
        await self.db.execute(
            """INSERT INTO quality_trends
               (tick_count, metric_name, metric_value, sample_size)
               VALUES (?, ?, ?, ?)""",
            (tick_count, metric_name, metric_value, sample_size),
        )
        await self.db.commit()

    async def update_finding_quality(
        self, quest_id: str, quality_score: float, feedback: str = ""
    ):
        """Update quality score for research findings linked to a quest."""
        await self.ensure_tables()
        await self.db.execute(
            "UPDATE research_findings SET quality_score=?, evaluator_feedback=? WHERE quest_id=?",
            (quality_score, feedback, quest_id),
        )
        await self.db.commit()

    async def get_approval_rate(self, window_quests: int = 20) -> dict:
        """Get CEO/CTO approval rate over recent evaluations."""
        await self.ensure_tables()
        cursor = await self.db.execute(
            "SELECT evaluator_role, approved, COUNT(*) as cnt "
            "FROM evaluation_quality "
            "GROUP BY evaluator_role, approved "
            "ORDER BY evaluator_role"
        )
        rows = await cursor.fetchall()

        stats = {"total": 0, "approved": 0, "by_role": {}}
        for r in rows:
            role = r["evaluator_role"]
            approved = r["approved"]
            cnt = r["cnt"]
            if role not in stats["by_role"]:
                stats["by_role"][role] = {"total": 0, "approved": 0}
            stats["by_role"][role]["total"] += cnt
            stats["total"] += cnt
            if approved:
                stats["by_role"][role]["approved"] += cnt
                stats["approved"] += cnt

        if stats["total"] > 0:
            stats["approval_rate"] = round(stats["approved"] / stats["total"], 3)
            for role in stats["by_role"]:
                r = stats["by_role"][role]
                r["rate"] = round(r["approved"] / r["total"], 3) if r["total"] > 0 else 0
        else:
            stats["approval_rate"] = 0

        return stats

    async def get_average_quality(self) -> dict:
        """Get average quality scores across all research findings."""
        await self.ensure_tables()
        cursor = await self.db.execute(
            "SELECT AVG(quality_score) as avg_q, COUNT(*) as total, "
            "MIN(quality_score) as min_q, MAX(quality_score) as max_q "
            "FROM research_findings WHERE quality_score > 0"
        )
        row = await cursor.fetchone()
        if row and row[0]:
            return {
                "avg_quality": round(row[0], 3),
                "total": row[1],
                "min_quality": row[2],
                "max_quality": row[3],
            }
        return {"avg_quality": 0, "total": 0, "min_quality": 0, "max_quality": 0}

    async def get_trends(self, metric: str = "", limit: int = 20) -> list[dict]:
        """Get quality trend data over recent ticks."""
        await self.ensure_tables()
        if metric:
            cursor = await self.db.execute(
                "SELECT * FROM quality_trends WHERE metric_name=? ORDER BY id DESC LIMIT ?",
                (metric, limit),
            )
        else:
            cursor = await self.db.execute(
                "SELECT * FROM quality_trends ORDER BY id DESC LIMIT ?", (limit,)
            )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def compute_quality_summary(self, tick_count: int) -> dict:
        """Compute and record a comprehensive quality snapshot.

        Called periodically to build the quality trend chart.
        """
        await self.ensure_tables()

        # 1. Approval rate
        approval_stats = await self.get_approval_rate()
        approval_rate = approval_stats.get("approval_rate", 0)

        # Record trend
        if approval_stats["total"] > 0:
            await self.record_trend(
                tick_count, "approval_rate", approval_rate, approval_stats["total"]
            )

        # 2. Average quality score
        quality_stats = await self.get_average_quality()
        if quality_stats["total"] > 0:
            await self.record_trend(
                tick_count, "avg_quality", quality_stats["avg_quality"], quality_stats["total"]
            )

        return {
            "approval_rate": approval_stats,
            "quality": quality_stats,
            "tick": tick_count,
        }
