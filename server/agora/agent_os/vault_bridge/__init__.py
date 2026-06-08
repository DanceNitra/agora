"""VaultBridge — connect dungeon agents to an Obsidian "second brain" vault.

Factory functions read the vault path from settings (AGORA_VAULT_PATH) with an
environment-variable fallback, so the server wires them with one call each.
"""
import os

from agora.agent_os.vault_bridge.vault_reader import VaultReader
from agora.agent_os.vault_bridge.vault_writer import VaultWriter

__all__ = ["VaultReader", "VaultWriter", "create_vault_reader", "create_vault_writer"]


def _vault_path(settings) -> str:
    return (getattr(settings, "vault_path", "") or os.environ.get("AGORA_VAULT_PATH", "")).strip()


def create_vault_reader(settings=None) -> VaultReader:
    return VaultReader(vault_path=_vault_path(settings) if settings is not None else
                       os.environ.get("AGORA_VAULT_PATH", "").strip())


def create_vault_writer(settings=None) -> VaultWriter:
    return VaultWriter(vault_path=_vault_path(settings) if settings is not None else
                       os.environ.get("AGORA_VAULT_PATH", "").strip())
