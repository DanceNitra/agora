"""Phase 4: Make the operation pay for itself

Generated from research:
Recorded income from verified quests exceeds recorded costs.
"""

import logging
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


class MakeTheOperationPayForIts:
    """Economy/resource management module for make the operation pay for its.

    Tracks resource quantities, manages transactions, and
    maintains balances for named accounts.
    """

    def __init__(self):
        self._accounts: dict[str, float] = {}
        self._resource_types: dict[str, dict[str, Any]] = {}
        self._transactions: list[dict[str, Any]] = []
        logger.info(f"Initialized {self.__class__.__name__}")

    def register_resource(self, name: str, initial_qty: float = 0.0, metadata: Optional[dict] = None):
        """Register a new resource type."""
        self._resource_types[name] = {
            "name": name,
            "initial_qty": initial_qty,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat(),
        }
        self._accounts[name] = initial_qty
        logger.info(f"Registered resource '{name}' (qty={initial_qty})")

    def credit(self, resource: str, amount: float, reason: str = "") -> dict[str, Any]:
        """Add resources to an account."""
        if resource not in self._accounts:
            raise ValueError(f"Unknown resource: {resource}")
        before = self._accounts[resource]
        self._accounts[resource] += amount
        tx = self._record(resource, "credit", amount, before, reason)
        return tx

    def debit(self, resource: str, amount: float, reason: str = "") -> dict[str, Any]:
        """Remove resources from an account."""
        if resource not in self._accounts:
            raise ValueError(f"Unknown resource: {resource}")
        before = self._accounts[resource]
        if before < amount:
            raise ValueError(f"Insufficient {resource}: have {before}, need {amount}")
        self._accounts[resource] -= amount
        tx = self._record(resource, "debit", amount, before, reason)
        return tx

    def balance(self, resource: str) -> float:
        """Get current balance of a resource."""
        return self._accounts.get(resource, 0.0)

    def all_balances(self) -> dict[str, float]:
        """Get all resource balances."""
        return dict(self._accounts)

    def _record(self, resource: str, tx_type: str, amount: float,
                before: float, reason: str) -> dict[str, Any]:
        """Record a transaction in the ledger."""
        tx: dict[str, Any] = {
            "resource": resource,
            "type": tx_type,
            "amount": amount,
            "balance_before": before,
            "balance_after": before + (amount if tx_type == "credit" else -amount),
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        }
        self._transactions.append(tx)
        return tx

    def history(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent transaction history."""
        return self._transactions[-limit:]

    def stats(self) -> dict[str, Any]:
        """Get module statistics."""
        return {
            "resources": len(self._resource_types),
            "accounts": len(self._accounts),
            "transactions": len(self._transactions),
            "total_value": sum(self._accounts.values()),
        }
