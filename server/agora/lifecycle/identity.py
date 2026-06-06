"""Agent identity management using Ed25519 keypairs."""

import hashlib
import time
from typing import Optional

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PrivateFormat,
    PublicFormat,
    NoEncryption,
)


class AgentIdentityManager:
    """Manages agent identities with Ed25519 keypair generation and verification.

    Each agent gets a unique Ed25519 keypair used for signing and verifying
    messages, attestations, and transactions within the agora ecosystem.
    """

    def __init__(self):
        self._identities: dict[str, dict] = {}

    def create_identity(self, agent_id: str, meta: Optional[dict] = None) -> dict:
        """Create a new Ed25519 keypair and register the identity.

        Args:
            agent_id: Unique identifier for the agent.
            meta: Optional metadata to attach to the identity.

        Returns:
            Dict containing the agent_id, public key (bytes), status, and
            creation timestamp.
        """
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        private_bytes = private_key.private_bytes(
            Encoding.Raw, PrivateFormat.Raw, NoEncryption()
        )
        public_bytes = public_key.public_bytes(
            Encoding.Raw, PublicFormat.Raw
        )

        identity = {
            "agent_id": agent_id,
            "public_key": public_bytes,
            "private_key": private_bytes,
            "status": "active",
            "created_at": time.time(),
            "meta": meta or {},
        }
        self._identities[agent_id] = identity
        return {
            "agent_id": agent_id,
            "public_key": public_bytes,
            "status": "active",
            "created_at": identity["created_at"],
        }

    def verify_signature(
        self, agent_id: str, message: bytes, signature: bytes
    ) -> bool:
        """Verify a message signature for the given agent identity.

        Args:
            agent_id: The agent whose public key should be used.
            message: The original message bytes.
            signature: The purported signature over the message.

        Returns:
            True if the signature is valid, False otherwise.
        """
        identity = self._identities.get(agent_id)
        if not identity or identity["status"] != "active":
            return False

        try:
            public_key = ed25519.Ed25519PublicKey.from_public_bytes(
                identity["public_key"]
            )
            public_key.verify(signature, message)
            return True
        except Exception:
            return False

    def get_identity(self, agent_id: str) -> Optional[dict]:
        """Retrieve a registered identity.

        Args:
            agent_id: The agent identifier.

        Returns:
            Identity dict (without private key) or None.
        """
        identity = self._identities.get(agent_id)
        if identity is None:
            return None
        return {
            "agent_id": identity["agent_id"],
            "public_key": identity["public_key"],
            "status": identity["status"],
            "created_at": identity["created_at"],
            "meta": identity["meta"],
        }

    def deactivate_identity(self, agent_id: str) -> bool:
        """Deactivate an identity, preventing further signature verifications.

        Args:
            agent_id: The agent to deactivate.

        Returns:
            True if deactivated, False if not found.
        """
        identity = self._identities.get(agent_id)
        if identity is None:
            return False
        identity["status"] = "inactive"
        return True
