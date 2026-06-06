"""Research agent — a BaseAgent implementation specialized in research tasks."""

import json
import time
from typing import Any, Optional

from .base import BaseAgent


class ResearcherAgent(BaseAgent):
    """An agent specialised for research: gathering, analysing, and
    synthesising information from multiple sources.

    The researcher follows a three-phase loop:
      1. think()   — parse the research question, break into sub-queries.
      2. act()     — execute queries / gather data.
      3. reflect() — synthesise findings, score completeness.
    """

    def __init__(
        self,
        agent_id: str,
        genome: Optional[dict] = None,
        trust_score: float = 0.5,
        energy: float = 100.0,
        domain: str = "general",
    ):
        super().__init__(agent_id, genome, trust_score, energy)
        self._domain = domain
        self._research_log: list[dict] = []

    # ── Core agent loop ─────────────────────────────────────────

    def think(self, context: Optional[dict] = None) -> dict:
        """Analyse the research task and produce a plan.

        Context can contain:
          - query: the research question / topic.
          - depth: shallow | moderate | deep.
          - sources: preferred source list.

        Returns a plan dict with sub-queries and a strategy.
        """
        context = context or {}
        query = context.get("query", "")
        depth = context.get("depth", "moderate")

        # Decompose the query into sub-queries
        sub_queries = self._decompose_query(query, depth)

        plan = {
            "type": "research",
            "query": query,
            "sub_queries": sub_queries,
            "depth": depth,
            "sources": context.get("sources", ["web", "knowledge_base", "papers"]),
            "estimated_steps": len(sub_queries),
        }
        return plan

    def act(self, plan: dict) -> dict:
        """Execute the research plan — gather data for each sub-query.

        In this implementation, results are mocked. A real implementation
        would call search APIs, read documents, etc.
        """
        results = []
        for sq in plan.get("sub_queries", []):
            # Mock: "gather" data
            entry = {
                "sub_query": sq,
                "findings": self._mock_search(sq),
                "timestamp": time.time(),
            }
            results.append(entry)
            self._research_log.append(entry)

            # Consume energy per sub-query
            self.consume_energy(5.0)

        return {
            "query": plan["query"],
            "results": results,
            "total_findings": sum(len(r["findings"]) for r in results),
            "completed_at": time.time(),
        }

    def reflect(self, outcome: Any) -> dict:
        """Evaluate research quality and update agent state.

        Computes a completeness score based on the number of findings
        vs. sub-queries, and adjusts trust score accordingly.
        """
        if not isinstance(outcome, dict):
            return {"error": "Invalid outcome format"}

        results = outcome.get("results", [])
        total_sub_queries = len(results)
        total_findings = outcome.get("total_findings", 0)

        # Completeness heuristic: at least one finding per sub-query
        if total_sub_queries > 0:
            completeness = min(1.0, total_findings / total_sub_queries)
        else:
            completeness = 0.0

        # Adjust trust score slightly based on outcome
        delta = (completeness - 0.5) * 0.1  # [-0.05, +0.05]
        self.trust_score = self.trust_score + delta

        reflection = {
            "completeness": completeness,
            "trust_score_adjustment": round(delta, 4),
            "new_trust_score": self.trust_score,
            "energy_remaining": self.energy,
            "total_sub_queries": total_sub_queries,
            "total_findings": total_findings,
        }
        return reflection

    # ── Private helpers ─────────────────────────────────────────

    def _decompose_query(self, query: str, depth: str) -> list[str]:
        """Break a research query into sub-questions.

        Mock implementation — returns synthetic sub-queries.
        """
        if not query.strip():
            return ["general_information"]

        base = query.strip().rstrip("?")
        factor = {"shallow": 2, "moderate": 3, "deep": 5}.get(depth, 3)

        return [
            f"{base}: aspect_{i+1}"
            for i in range(factor)
        ]

    def _mock_search(self, sub_query: str) -> list[dict]:
        """Simulate a search result.

        Returns a short list of mock findings.
        """
        return [
            {
                "source": f"mock-source-{hash(sub_query) % 100}",
                "title": f"Result for '{sub_query[:40]}...'",
                "snippet": f"This is a mock finding related to {sub_query}.",
                "relevance": round(0.5 + (hash(sub_query) % 50) / 100, 2),
            },
            {
                "source": "knowledge_base",
                "title": f"KB entry: {sub_query[:40]}",
                "snippet": f"Structured knowledge about {sub_query}.",
                "relevance": 0.85,
            },
        ]

    def get_research_log(self) -> list[dict]:
        """Return the full research activity log."""
        return list(self._research_log)
