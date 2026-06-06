"""Abstract base agent with lifecycle properties and core methods."""

from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseAgent(ABC):
    """Abstract base class for all Agora agents.

    Provides the fundamental properties every agent must have:
      - agent_id: unique identifier
      - genome: encoded behavioral/structural genome
      - trust_score: reputation metric (0.0 – 1.0)
      - energy: action budget that depletes with work

    Subclasses must implement think(), act(), and reflect().
    """

    def __init__(
        self,
        agent_id: str,
        genome: Optional[dict] = None,
        trust_score: float = 0.5,
        energy: float = 100.0,
        meta: Optional[dict] = None,
    ):
        self._agent_id = agent_id
        self._genome = genome or {}
        self._trust_score = max(0.0, min(1.0, trust_score))
        self._energy = max(0.0, energy)
        self._meta = meta or {}
        self._state: dict[str, Any] = {}

    # ── Properties ──────────────────────────────────────────────

    @property
    def agent_id(self) -> str:
        """Unique identifier for this agent."""
        return self._agent_id

    @property
    def genome(self) -> dict:
        """The agent's encoded genome (traits, capabilities, weights)."""
        return dict(self._genome)

    @property
    def trust_score(self) -> float:
        """Reputation score in [0.0, 1.0]."""
        return self._trust_score

    @trust_score.setter
    def trust_score(self, value: float) -> None:
        self._trust_score = max(0.0, min(1.0, value))

    @property
    def energy(self) -> float:
        """Current energy level. Depletes on actions, replenished over time."""
        return self._energy

    def consume_energy(self, amount: float) -> bool:
        """Reduce energy by *amount*. Returns False if insufficient."""
        if self._energy < amount:
            return False
        self._energy -= amount
        return True

    def replenish_energy(self, amount: float) -> None:
        """Add energy up to a max of 100.0."""
        self._energy = min(100.0, self._energy + amount)

    # ── Abstract methods ───────────────────────────────────────

    @abstractmethod
    def think(self, context: Optional[dict] = None) -> dict:
        """Analyze the current situation and plan the next action.

        Args:
            context: Environmental or task context.

        Returns:
            A plan/decision dict.
        """
        ...

    @abstractmethod
    def act(self, plan: dict) -> Any:
        """Execute the decided action.

        Args:
            plan: The decision dict produced by think().

        Returns:
            Result of the action.
        """
        ...

    @abstractmethod
    def reflect(self, outcome: Any) -> dict:
        """Evaluate the outcome and update internal state / genome.

        Args:
            outcome: The result from act().

        Returns:
            Reflection dict (e.g. lessons learned, score adjustments).
        """
        ...

    # ── Utility ─────────────────────────────────────────────────

    def set_state(self, key: str, value: Any) -> None:
        """Store arbitrary agent-local state."""
        self._state[key] = value

    def get_state(self, key: str, default: Any = None) -> Any:
        """Retrieve agent-local state."""
        return self._state.get(key, default)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"agent_id={self._agent_id!r}, "
            f"trust_score={self._trust_score:.2f}, "
            f"energy={self._energy:.1f})"
        )
