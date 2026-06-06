"""
GenesisForge — agent birth and genome mutation engine.

Part of the Lifecycle (L) layer in the Agora 5-layer architecture.
Responsible for spawning new agents with cryptographically signed
identities and mutated genomes drawn from the global gene pool.
"""

from __future__ import annotations

import hashlib
import json
import random
import secrets
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class AgentGenome:
    """The mutable instruction set of an agent — its 'DNA'."""
    skills: List[str] = field(default_factory=list)
    traits: Dict[str, float] = field(default_factory=dict)
    max_tool_depth: int = 3
    memory_ttl: int = 3600
    coordination_mode: str = "peer"  # peer | hierarchical | swarm
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentIdentity:
    """Cryptographic identity for an agent."""
    agent_id: str
    public_key: bytes
    private_key: bytes  # kept in-memory only; never serialised to disk


@dataclass
class AgentSpawnRecord:
    """Full record of a spawned agent."""
    identity: AgentIdentity
    genome: AgentGenome
    parent_id: Optional[str]
    generation: int
    spawned_at: float
    signature: bytes


# ---------------------------------------------------------------------------
# GenesisForge
# ---------------------------------------------------------------------------

class GenesisForge:
    """Factory for creating new agents with cryptographic identities.

    Typical usage::

        forge = GenesisForge()
        record = forge.spawn_agent(
            parent_genome=parent.genome,
            parent_id=parent.identity.agent_id,
            generation=parent.generation + 1,
        )
    """

    # Default gene pool used when no parent genome is supplied (seed agents).
    DEFAULT_GENE_POOL = {
        "skills": [
            "file_read", "file_write", "web_search", "code_execute",
            "data_analyse", "summarise",
        ],
        "traits": {
            "curiosity": 0.7,
            "cooperation": 0.6,
            "assertiveness": 0.5,
            "thoroughness": 0.8,
        },
    }

    def __init__(self, seed: Optional[int] = None) -> None:
        self._rng = secrets.SystemRandom()
        if seed is not None:
            self._rng = random.Random(seed)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def spawn_agent(
        self,
        parent_genome: Optional[AgentGenome] = None,
        parent_id: Optional[str] = None,
        generation: int = 0,
        custom_traits: Optional[Dict[str, float]] = None,
    ) -> AgentSpawnRecord:
        """Create a new agent, optionally inheriting from a parent genome.

        Args:
            parent_genome: Genome of the parent agent (``None`` for seed agents).
            parent_id:  Agent ID of the parent (``None`` for seed agents).
            generation: Generation number (0 for seed agents).
            custom_traits: Override or augment traits before mutation.

        Returns:
            Fully populated :class:`AgentSpawnRecord`.
        """
        # 1. Derive base genome
        if parent_genome is not None:
            genome = AgentGenome(
                skills=list(parent_genome.skills),
                traits=dict(parent_genome.traits),
                max_tool_depth=parent_genome.max_tool_depth,
                memory_ttl=parent_genome.memory_ttl,
                coordination_mode=parent_genome.coordination_mode,
            )
        else:
            genome = AgentGenome(
                skills=list(self.DEFAULT_GENE_POOL["skills"]),
                traits=dict(self.DEFAULT_GENE_POOL["traits"]),
            )

        # Apply custom trait overrides
        if custom_traits:
            genome.traits.update(custom_traits)

        # 2. Mutate
        genome = self._mutate_genome(genome)

        # 3. Generate keypair
        identity = self._generate_keypair()

        # 4. Sign the record
        payload = self._signature_payload(identity.agent_id, genome, parent_id, generation)
        signing_key = ed25519.Ed25519PrivateKey.from_private_bytes(identity.private_key)
        signature = signing_key.sign(payload)

        return AgentSpawnRecord(
            identity=identity,
            genome=genome,
            parent_id=parent_id,
            generation=generation,
            spawned_at=time.time(),
            signature=signature,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _mutate_genome(self, genome: AgentGenome) -> AgentGenome:
        """Apply random mutations to the genome.

        Mutations include:
        * Small trait value drifts (Gaussian noise).
        * Occasional skill additions or removals.
        * Rare coordination-mode switches.
        """
        # --- Trait drift ---
        for trait in genome.traits:
            delta = self._rng.gauss(0, 0.05)
            genome.traits[trait] = max(0.0, min(1.0, genome.traits[trait] + delta))

        # --- Skill mutations ---
        if self._rng.random() < 0.15 and self.DEFAULT_GENE_POOL["skills"]:
            # Add a random skill from the pool (if not already present)
            candidate = self._rng.choice(self.DEFAULT_GENE_POOL["skills"])
            if candidate not in genome.skills:
                genome.skills.append(candidate)

        if self._rng.random() < 0.05 and len(genome.skills) > 1:
            genome.skills.pop(self._rng.randrange(len(genome.skills)))

        # --- Coordination-mode switch ---
        if self._rng.random() < 0.02:
            modes = ["peer", "hierarchical", "swarm"]
            genome.coordination_mode = self._rng.choice(modes)

        # --- numeric parameter tweaks ---
        if self._rng.random() < 0.1:
            genome.max_tool_depth = max(1, genome.max_tool_depth + self._rng.choice([-1, 1]))
        if self._rng.random() < 0.1:
            genome.memory_ttl = max(60, genome.memory_ttl + self._rng.randint(-300, 300))

        return genome

    def _generate_keypair(self) -> AgentIdentity:
        """Generate a Ed25519 keypair and derive a human-readable agent ID.

        The agent ID is the hex-encoded SHA-256 digest of the public key,
        truncated to 16 characters for readability.
        """
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        raw_pub = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        agent_id = hashlib.sha256(raw_pub).hexdigest()[:16]

        return AgentIdentity(
            agent_id=agent_id,
            public_key=raw_pub,
            private_key=private_key.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption(),
            ),
        )

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _signature_payload(
        agent_id: str,
        genome: AgentGenome,
        parent_id: Optional[str],
        generation: int,
    ) -> bytes:
        """Deterministic payload used for signing / verification."""
        payload = {
            "agent_id": agent_id,
            "genome": {
                "skills": sorted(genome.skills),
                "traits": {k: round(v, 4) for k, v in sorted(genome.traits.items())},
                "max_tool_depth": genome.max_tool_depth,
                "memory_ttl": genome.memory_ttl,
                "coordination_mode": genome.coordination_mode,
            },
            "parent_id": parent_id,
            "generation": generation,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()

    @staticmethod
    def verify_spawn(record: AgentSpawnRecord) -> bool:
        """Verify the cryptographic signature on a spawn record.

        Returns ``True`` if the signature is valid for the claimed identity.
        """
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        payload = GenesisForge._signature_payload(
            record.identity.agent_id,
            record.genome,
            record.parent_id,
            record.generation,
        )
        try:
            pub_key = Ed25519PublicKey.from_public_bytes(record.identity.public_key)
            pub_key.verify(record.signature, payload)
            return True
        except Exception:
            return False
