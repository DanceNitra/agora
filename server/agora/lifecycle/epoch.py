"""
EpochManager — epoch lifecycle and phase advancement.

Part of the Lifecycle (L) layer in the Agora 5-layer architecture.
Controls the simulation clock: epoch counting, phase transitions
(fork / evolve / cull / reset), and seed-agent bootstrapping.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from agora.lifecycle.genesis import AgentGenome, AgentSpawnRecord, GenesisForge


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class EpochPhase(str, Enum):
    """The four phases of a single epoch."""
    FORK = "fork"         # spawn child agents from survivors
    EVOLVE = "evolve"     # agents act / mutate / interact
    CULL = "cull"         # remove under-performing agents
    RESET = "reset"       # prepare for next epoch


@dataclass
class EpochState:
    """Snapshot of the system at a given epoch."""
    number: int = 0
    phase: EpochPhase = EpochPhase.FORK
    started_at: float = 0.0
    phase_deadline: float = 0.0
    agent_count: int = 0
    metadata: Dict[str, object] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# EpochManager
# ---------------------------------------------------------------------------

class EpochManager:
    """Manages epoch counting, phase progression, and seed-agent creation.

    Typical usage::

        mgr = EpochManager(epoch_duration=300.0)
        mgr._create_seed_agents(count=10)
        phase = mgr.get_current_epoch()
        mgr.advance_phase()        # FORK → EVOLVE → CULL → RESET → next FORK
    """

    # Default configuration
    DEFAULT_EPOCH_DURATION: float = 300.0       # 5 minutes
    DEFAULT_PHASE_RATIOS: Dict[EpochPhase, float] = {
        EpochPhase.FORK: 0.10,     # 10%  of epoch
        EpochPhase.EVOLVE: 0.60,   # 60%
        EpochPhase.CULL: 0.20,     # 20%
        EpochPhase.RESET: 0.10,    # 10%
    }
    DEFAULT_SEED_SKILLS: List[str] = [
        "file_read", "file_write", "web_search", "summarise",
    ]
    DEFAULT_SEED_TRAITS: Dict[str, float] = {
        "curiosity": 0.7,
        "cooperation": 0.6,
        "assertiveness": 0.5,
        "thoroughness": 0.8,
    }

    def __init__(
        self,
        epoch_duration: Optional[float] = None,
        phase_ratios: Optional[Dict[EpochPhase, float]] = None,
        forge: Optional[GenesisForge] = None,
    ) -> None:
        self._forge = forge or GenesisForge()
        self._epoch_duration = epoch_duration or self.DEFAULT_EPOCH_DURATION
        self._phase_ratios = phase_ratios or dict(self.DEFAULT_PHASE_RATIOS)

        self._state = EpochState()
        self._seed_records: List[AgentSpawnRecord] = []
        self._current_agent_ids: List[str] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_current_epoch(self) -> EpochState:
        """Return the current :class:`EpochState` snapshot.

        The phase is automatically recomputed based on elapsed time
        within the current epoch.
        """
        if self._state.started_at == 0.0:
            self._state.started_at = time.time()
            self._state.phase_deadline = (
                self._state.started_at + self._phase_ratios[EpochPhase.FORK] * self._epoch_duration
            )

        elapsed = time.time() - self._state.started_at
        epoch_time = elapsed % self._epoch_duration

        # Determine phase by accumulated time
        cumulative = 0.0
        for phase in EpochPhase:
            ratio = self._phase_ratios.get(phase, 0.25)
            cumulative += ratio * self._epoch_duration
            if epoch_time < cumulative:
                self._state.phase = phase
                self._state.phase_deadline = (
                    self._state.started_at
                    + (elapsed // self._epoch_duration) * self._epoch_duration
                    + cumulative
                )
                break
        else:
            self._state.phase = EpochPhase.RESET

        self._state.number = int(elapsed // self._epoch_duration)
        self._state.agent_count = len(self._current_agent_ids)
        return self._state

    def advance_phase(self) -> EpochPhase:
        """Force-advance to the next phase, resetting the phase clock.

        Phases cycle: FORK → EVOLVE → CULL → RESET → (increment epoch) → FORK.

        Returns the new active phase.
        """
        phases = list(EpochPhase)
        current_idx = phases.index(self._state.phase)
        next_idx = (current_idx + 1) % len(phases)
        new_phase = phases[next_idx]

        # If we wrap around to FORK, the epoch number increments
        if new_phase == EpochPhase.FORK:
            self._state.number += 1

        self._state.phase = new_phase
        self._state.started_at = time.time()
        self._state.phase_deadline = (
            self._state.started_at
            + self._phase_ratios.get(new_phase, 0.25) * self._epoch_duration
        )
        return new_phase

    def reset_epoch(self, hard: bool = False) -> None:
        """Reset the epoch clock.

        Args:
            hard: If ``True``, also clears seed records and agent list.
                  If ``False``, only resets the timer while preserving state.
        """
        self._state = EpochState()
        if hard:
            self._seed_records.clear()
            self._current_agent_ids.clear()
        self._state.started_at = time.time()
        self._state.phase_deadline = (
            self._state.started_at
            + self._phase_ratios[EpochPhase.FORK] * self._epoch_duration
        )

    # ------------------------------------------------------------------
    # Seed-agent creation
    # ------------------------------------------------------------------

    def _create_seed_agents(
        self,
        count: int = 10,
        custom_skills: Optional[List[str]] = None,
        custom_traits: Optional[Dict[str, float]] = None,
    ) -> List[AgentSpawnRecord]:
        """Bootstrap the first generation of agents (generation 0).

        Each seed agent is spawned by :class:`GenesisForge` without a
        parent, starting from the default gene pool (optionally customised).

        Args:
            count:  Number of seed agents to create.
            custom_skills:  Override default skill list.
            custom_traits:  Override default trait dictionary.

        Returns:
            List of :class:`AgentSpawnRecord` instances.
        """
        self._seed_records.clear()
        self._current_agent_ids.clear()

        for _ in range(count):
            record = self._forge.spawn_agent(
                parent_genome=None,
                parent_id=None,
                generation=0,
                custom_traits=custom_traits,
            )
            self._seed_records.append(record)
            self._current_agent_ids.append(record.identity.agent_id)

        return list(self._seed_records)

    # ------------------------------------------------------------------
    # Agent tracking helpers
    # ------------------------------------------------------------------

    def register_agent(self, agent_id: str) -> None:
        """Register an agent for epoch tracking."""
        if agent_id not in self._current_agent_ids:
            self._current_agent_ids.append(agent_id)

    def unregister_agent(self, agent_id: str) -> None:
        """Remove an agent from epoch tracking (e.g. after culling)."""
        if agent_id in self._current_agent_ids:
            self._current_agent_ids.remove(agent_id)

    @property
    def active_agent_count(self) -> int:
        """Number of agents currently tracked."""
        return len(self._current_agent_ids)

    @property
    def seed_agent_count(self) -> int:
        """Number of seed agents spawned."""
        return len(self._seed_records)
