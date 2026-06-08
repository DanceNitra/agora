"""Vault Company OS — every agent is a vault employee with role, skills, soul, tools."""
from .agent_definitions import (
    VAULT_ROLES, VAULT_DEPARTMENTS, VAULT_ROLE_SKILLS, VAULT_SOUL,
    VAULT_TOOLS, AGENT_VAULT_DEFS, VAULT_SKILL_DESCRIPTIONS,
    VAULT_COMPANY_ORG_CHART,
)
from .vault_company_engine import VaultCompanyEngine

__all__ = [
    "VAULT_ROLES", "VAULT_DEPARTMENTS", "VAULT_ROLE_SKILLS", "VAULT_SOUL",
    "VAULT_TOOLS", "AGENT_VAULT_DEFS", "VAULT_SKILL_DESCRIPTIONS",
    "VAULT_COMPANY_ORG_CHART", "VaultCompanyEngine",
]