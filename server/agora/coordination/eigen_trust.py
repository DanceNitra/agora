"""
EigenTrust — global trust scoring via eigenvector centrality.

Based on the EigenTrust algorithm (Kamvar et al., 2003):
  t^(k+1) = (1-d)·e + d·C^T·t^(k)

Where:
  - C: normalised N×N trust matrix (each row sums to 1)
  - d: damping factor (default 0.85)
  - e: initial/pre-trusted vector (uniform by default)
  - t: global trust vector (converges after ~20-50 iterations)

The result is a PageRank-like score for each agent measuring how much
the collective trusts them.
"""

import json
from datetime import datetime
from typing import Optional

import numpy as np


class EigenTrustSolver:
    """Builds trust matrix from DB and computes eigenvector centrality."""

    def __init__(self, db):
        self.db = db
        self._cache: Optional[dict] = None  # (timestamp, agents, matrix, vector)

    # ── Matrix Builder ───────────────────────────────────────

    async def build_matrix(self, min_interactions: int = 0) -> dict:
        """Build the N×N trust matrix from DB trust_scores.

        Returns:
          {
            "agents": [{"id": str, "role": str, ...}, ...],
            "agent_index": {agent_id: index},
            "matrix": np.ndarray  (N×N, float),
            "normalized": np.ndarray  (row-stochastic, N×N),
            "shape": (N, N),
            "pair_count": int,
          }
        """
        # Get all active agents
        cursor = await self.db.execute(
            "SELECT agent_id, role, trust_score, energy_balance, generation "
            "FROM agent_identities WHERE status='active' ORDER BY agent_id"
        )
        agents = [dict(r) for r in await cursor.fetchall()]
        agent_ids = [a["agent_id"] for a in agents]
        N = len(agent_ids)
        id_to_idx = {aid: i for i, aid in enumerate(agent_ids)}

        # Get all trust scores
        cursor = await self.db.execute(
            "SELECT source_id, target_id, score, interaction_count "
            "FROM trust_scores ORDER BY source_id, target_id"
        )
        pairs = [dict(r) for r in await cursor.fetchall()]

        # Build N×N matrix
        matrix = np.full((N, N), 0.5 / (N - 1) if N > 1 else 0.5,
                         dtype=np.float64)

        for pair in pairs:
            src = pair["source_id"]
            tgt = pair["target_id"]
            score = pair["score"]
            count = pair["interaction_count"]

            if src in id_to_idx and tgt in id_to_idx:
                if count >= min_interactions:
                    i, j = id_to_idx[src], id_to_idx[tgt]
                    matrix[i][j] = score

        # Row-stochastic normalisation
        row_sums = matrix.sum(axis=1, keepdims=True)
        row_sums = np.where(row_sums == 0, 1.0, row_sums)
        normalized = matrix / row_sums

        return {
            "agents": agents,
            "agent_ids": agent_ids,
            "agent_index": id_to_idx,
            "matrix": matrix,
            "normalized": normalized,
            "shape": (N, N),
            "pair_count": len(pairs),
        }

    # ── EigenTrust Solver ────────────────────────────────────

    def solve(
        self,
        normalized: np.ndarray,
        damping: float = 0.85,
        max_iter: int = 100,
        tol: float = 1e-6,
        pre_trusted: Optional[list[int]] = None,
    ) -> np.ndarray:
        """Compute global trust vector using iterative EigenTrust.

        Args:
          normalized: N×N row-stochastic trust matrix
          damping:    probability of following trust links (vs jumping)
          max_iter:   max iterations before force-stop
          tol:        convergence threshold (L1 norm of delta)
          pre_trusted: indices of pre-trusted agents (or None = uniform)

        Returns:
          trust_vector: np.ndarray of shape (N,) summing to 1
        """
        N = normalized.shape[0]
        if N == 0:
            return np.array([])

        # Transpose: C^T for the iterative formula
        C_T = normalized.T

        # Initial trust vector (uniform or pre-trusted)
        if pre_trusted:
            e = np.zeros(N)
            e[pre_trusted] = 1.0 / len(pre_trusted)
        else:
            e = np.full(N, 1.0 / N)

        t = e.copy()

        for iteration in range(max_iter):
            t_next = (1 - damping) * e + damping * C_T @ t
            # L1 convergence check
            delta = np.sum(np.abs(t_next - t))
            t = t_next
            if delta < tol:
                break

        # Normalise to sum to 1
        total = np.sum(t)
        if total > 0:
            t = t / total

        return t

    # ── Full Pipeline ────────────────────────────────────────

    async def compute(
        self,
        damping: float = 0.85,
        min_interactions: int = 0,
        pre_trusted_ids: Optional[list[str]] = None,
    ) -> dict:
        """Full pipeline: build matrix → compute eigenvector → return result.

        Returns:
          {
            "agents": [...],
            "trust_vector": {agent_id_truncated: score, ...},
            "top_agents": [...],
            "iterations": int,
            "matrix_stats": {...},
            "computed_at": str,
          }
        """
        start = datetime.utcnow()

        data = await self.build_matrix(min_interactions=min_interactions)
        N = data["shape"][0]

        if N == 0:
            return {"agents": [], "trust_vector": {}, "top_agents": [],
                    "iterations": 0, "error": "No active agents"}

        # Pre-trusted indices
        pre_idx = None
        if pre_trusted_ids:
            idx = data["agent_index"]
            pre_idx = [idx[pid] for pid in pre_trusted_ids if pid in idx]

        vector = self.solve(
            data["normalized"],
            damping=damping,
            pre_trusted=pre_idx,
        )

        # Map vector back to agent IDs
        trust_scores = {}
        agent_details = []
        for i, agent in enumerate(data["agents"]):
            score = round(float(vector[i]), 4)
            trust_scores[agent["agent_id"][:8]] = score
            agent_details.append({
                "id": agent["agent_id"][:8],
                "role": agent["role"],
                "eigen_trust": score,
                "ess_trust": round(agent["trust_score"], 4),
            })

        # Sort by eigen trust descending
        agent_details.sort(key=lambda a: a["eigen_trust"], reverse=True)

        # Matrix stats
        matrix = data["matrix"]
        norm = data["normalized"]

        elapsed = (datetime.utcnow() - start).total_seconds()

        return {
            "agents": agent_details,
            "trust_vector": trust_scores,
            "top_agents": agent_details[:5],
            "iterations": min(100, 100),
            "matrix_stats": {
                "n": N,
                "pairs": data["pair_count"],
                "density": round(float(np.count_nonzero(norm)) / max(N * N, 1), 4),
                "mean_trust": round(float(np.mean(matrix)), 4),
                "max_trust": round(float(np.max(matrix)), 4),
                "min_trust": round(float(np.min(matrix)), 4),
            },
            "computed_at": start.isoformat(),
            "elapsed_seconds": round(elapsed, 3),
        }

    # ── Raw Matrix Access ───────────────────────────────────

    async def get_raw_matrix(self, min_interactions: int = 1) -> dict:
        """Return the raw trust matrix for API consumption (JSON-safe)."""
        data = await self.build_matrix(min_interactions=min_interactions)
        agents = data["agents"]
        ids = [a["agent_id"][:8] for a in agents]
        roles = [a["role"] for a in agents]
        matrix_list = data["matrix"].tolist()
        norm_list = data["normalized"].tolist()

        return {
            "agents": ids,
            "roles": roles,
            "n": data["shape"][0],
            "pairs": data["pair_count"],
            "matrix": matrix_list,
            "normalized": norm_list,
        }

    # ── Blending ─────────────────────────────────────────────

    @staticmethod
    def blend_trust(
        ess_scores: dict[str, float],
        eigen_scores: dict[str, float],
        eigen_weight: float = 0.3,
    ) -> dict[str, float]:
        """Blend ESS trust with EigenTrust scores.

        final = (1 - eigen_weight) * ess + eigen_weight * eigen
        """
        blended = {}
        for agent_id in set(ess_scores) | set(eigen_scores):
            ess = ess_scores.get(agent_id, 0.5)
            eigen = eigen_scores.get(agent_id, 0.5)
            blended[agent_id] = round(
                (1 - eigen_weight) * ess + eigen_weight * eigen, 4
            )
        return blended
