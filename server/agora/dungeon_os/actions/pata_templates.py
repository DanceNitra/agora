"""Phase 4 PATA code templates — instant, real Python code generation.

Instead of waiting for slow LLM calls, each subsystem has a
pre-built template that generates real, working Python code
with proper imports, async support, and FastAPI patterns.

The LLM path still exists for optional upgrade when a fast model is available.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional


# ═══════════════════════════════════════════
# CODE TEMPLATES — one per subsystem
# ═══════════════════════════════════════════

def generate_code(subsystem: str, title: str, research: str, target_dir: str) -> dict:
    """Generate real Python code from templates based on subsystem.

    Args:
        subsystem: 'tooling', 'knowledge', 'economy', 'safety', 'comms'
        title: Quest title (used for class/file naming)
        research: Research summary (embedded in docstring)
        target_dir: Where to write the file

    Returns:
        dict with status, files list, description
    """
    safe_name = _make_safe_name(title)
    filename = f"phase4_{safe_name}.py"
    full_path = os.path.join(target_dir, filename)

    # Pick template by subsystem
    generators = {
        "tooling": _template_tooling,
        "knowledge": _template_knowledge,
        "economy": _template_economy,
        "safety": _template_safety,
        "comms": _template_comms,
    }
    gen = generators.get(subsystem, _template_generic)
    content = gen(safe_name, title, research)

    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w") as f:
        f.write(content)

    print(f"[Developer] Template: wrote {full_path} ({len(content)} chars) — {subsystem}")
    return {
        "status": "ok",
        "files": [full_path],
        "description": f"Template-generated {subsystem} module: {safe_name}",
    }


def _make_safe_name(title: str) -> str:
    """Convert a quest title into a valid Python identifier."""
    # Take the last meaningful part after ":"
    name = title.split(":")[-1].strip().lower().replace(" ", "_")
    # Remove special chars
    safe = "".join(c if c.isalnum() or c == "_" else "_" for c in name)[:30]
    return safe.strip("_") or "implementation"


def _template_tooling(safe_name: str, title: str, research: str) -> str:
    """Template: FastAPI router/endpoint for tooling subsystem."""
    api_name = safe_name.replace("_", " ")
    router_name = safe_name
    return f'''"""Phase 4: {title}

Generated from research:
{research[:400]}
"""

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/{router_name}", tags=["{router_name}"])


# ── Models ──────────────────────────────────────────────

class {safe_name.title().replace("_", "")}Request(BaseModel):
    """Request model for {api_name}."""
    action: str
    params: dict[str, Any] = {{}}


class {safe_name.title().replace("_", "")}Response(BaseModel):
    """Response model for {api_name}."""
    status: str
    data: Optional[dict[str, Any]] = None
    message: str = ""


# ── State ──────────────────────────────────────────────

_state: dict[str, Any] = {{}}


@router.get("/status", response_model={safe_name.title().replace("_", "")}Response)
async def get_status():
    """Get current {api_name} status."""
    return {{
        "status": "ok",
        "data": {{
            "active": True,
            "items": len(_state),
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        }},
        "message": "{api_name} is operational",
    }}


@router.post("/execute", response_model={safe_name.title().replace("_", "")}Response)
async def execute_action(request: {safe_name.title().replace("_", "")}Request):
    """Execute an action in the {api_name} subsystem."""
    try:
        result = _handle_action(request.action, request.params)
        logger.info(f"Executed {{request.action}}: {{result}}")
        return {{
            "status": "ok",
            "data": result,
            "message": f"Action '{{request.action}}' completed",
        }}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Action failed: {{e}}")
        raise HTTPException(status_code=500, detail=str(e))


def _handle_action(action: str, params: dict) -> dict:
    """Route an action to its handler."""
    handlers = {{
        "init": _action_init,
        "reset": _action_reset,
        "status": _action_status,
    }}
    handler = handlers.get(action)
    if not handler:
        raise ValueError(f"Unknown action: {{action}}")
    return handler(params)


def _action_init(params: dict) -> dict:
    """Initialize the {api_name} subsystem."""
    _state.clear()
    _state["initialized_at"] = __import__("datetime").datetime.now().isoformat()
    _state["config"] = params
    return {{"initialized": True, "config": params}}


def _action_reset(params: dict) -> dict:
    """Reset the {api_name} subsystem to defaults."""
    _state.clear()
    return {{"reset": True}}


def _action_status(params: dict) -> dict:
    """Report current state of the {api_name} subsystem."""
    return {{
        "initialized": "initialized_at" in _state,
        "state_size": len(_state),
        "state_keys": list(_state.keys()),
    }}
'''


def _template_knowledge(safe_name: str, title: str, research: str) -> str:
    """Template: knowledge/CRUD module."""
    api_name = safe_name.replace("_", " ")
    class_name = safe_name.title().replace("_", "")
    return f'''"""Phase 4: {title}

Generated from research:
{research[:400]}
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class {class_name}:
    """Knowledge management module for {api_name}.

    Provides persistent storage and retrieval for structured
    knowledge entries backed by the filesystem (JSON).
    """

    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = Path(storage_dir or "/tmp/hermes-knowledge")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, dict[str, Any]] = {{}}
        self._load_all()
        logger.info(f"Initialized {{self.__class__.__name__}} ({{len(self._cache)}} cached items)")

    # ── CRUD Operations ──────────────────────────────

    def create(self, key: str, data: dict[str, Any], tags: Optional[list[str]] = None) -> dict[str, Any]:
        """Store a knowledge entry."""
        entry: dict[str, Any] = {{
            "key": key,
            "data": data,
            "tags": tags or [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }}
        self._cache[key] = entry
        self._persist(key)
        return entry

    def read(self, key: str) -> Optional[dict[str, Any]]:
        """Retrieve a knowledge entry by key."""
        return self._cache.get(key)

    def update(self, key: str, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Update an existing knowledge entry."""
        entry = self._cache.get(key)
        if not entry:
            return None
        entry["data"].update(data)
        entry["updated_at"] = datetime.now().isoformat()
        self._persist(key)
        return entry

    def delete(self, key: str) -> bool:
        """Delete a knowledge entry."""
        if key in self._cache:
            del self._cache[key]
            self._remove_file(key)
            return True
        return False

    def search(self, query: str) -> list[dict[str, Any]]:
        """Search knowledge entries by text in data or tags."""
        results = []
        q = query.lower()
        for entry in self._cache.values():
            text = json.dumps(entry["data"]).lower()
            tag_text = " ".join(entry.get("tags", [])).lower()
            if q in text or q in tag_text:
                results.append(entry)
        return results

    # ── Persistence ──────────────────────────────

    def _load_all(self):
        """Load all entries from storage directory."""
        for fpath in self.storage_dir.glob("*.json"):
            try:
                with open(fpath) as f:
                    entry = json.load(f)
                    self._cache[entry["key"]] = entry
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Skipping corrupt file {{fpath.name}}: {{e}}")

    def _persist(self, key: str):
        """Write a single entry to disk."""
        entry = self._cache.get(key)
        if not entry:
            return
        fpath = self.storage_dir / f"{key}.json"
        with open(fpath, "w") as f:
            json.dump(entry, f, indent=2)

    def _remove_file(self, key: str):
        """Remove a persisted entry from disk."""
        fpath = self.storage_dir / f"{key}.json"
        if fpath.exists():
            fpath.unlink()

    def stats(self) -> dict[str, Any]:
        """Return module statistics."""
        return {{
            "total_entries": len(self._cache),
            "storage_path": str(self.storage_dir),
            "tags": list(set(t for e in self._cache.values() for t in e.get("tags", []))),
        }}
'''


def _template_economy(safe_name: str, title: str, research: str) -> str:
    """Template: economy/resource module."""
    api_name = safe_name.replace("_", " ")
    class_name = safe_name.title().replace("_", "")
    return f'''"""Phase 4: {title}

Generated from research:
{research[:400]}
"""

import logging
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


class {class_name}:
    """Economy/resource management module for {api_name}.

    Tracks resource quantities, manages transactions, and
    maintains balances for named accounts.
    """

    def __init__(self):
        self._accounts: dict[str, float] = {{}}
        self._resource_types: dict[str, dict[str, Any]] = {{}}
        self._transactions: list[dict[str, Any]] = []
        logger.info(f"Initialized {{self.__class__.__name__}}")

    def register_resource(self, name: str, initial_qty: float = 0.0, metadata: Optional[dict] = None):
        """Register a new resource type."""
        self._resource_types[name] = {{
            "name": name,
            "initial_qty": initial_qty,
            "metadata": metadata or {{}},
            "created_at": datetime.now().isoformat(),
        }}
        self._accounts[name] = initial_qty
        logger.info(f"Registered resource '{{name}}' (qty={{initial_qty}})")

    def credit(self, resource: str, amount: float, reason: str = "") -> dict[str, Any]:
        """Add resources to an account."""
        if resource not in self._accounts:
            raise ValueError(f"Unknown resource: {{resource}}")
        before = self._accounts[resource]
        self._accounts[resource] += amount
        tx = self._record(resource, "credit", amount, before, reason)
        return tx

    def debit(self, resource: str, amount: float, reason: str = "") -> dict[str, Any]:
        """Remove resources from an account."""
        if resource not in self._accounts:
            raise ValueError(f"Unknown resource: {{resource}}")
        before = self._accounts[resource]
        if before < amount:
            raise ValueError(f"Insufficient {{resource}}: have {{before}}, need {{amount}}")
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
        tx: dict[str, Any] = {{
            "resource": resource,
            "type": tx_type,
            "amount": amount,
            "balance_before": before,
            "balance_after": before + (amount if tx_type == "credit" else -amount),
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        }}
        self._transactions.append(tx)
        return tx

    def history(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent transaction history."""
        return self._transactions[-limit:]

    def stats(self) -> dict[str, Any]:
        """Get module statistics."""
        return {{
            "resources": len(self._resource_types),
            "accounts": len(self._accounts),
            "transactions": len(self._transactions),
            "total_value": sum(self._accounts.values()),
        }}
'''


def _template_safety(safe_name: str, title: str, research: str) -> str:
    """Template: safety/monitoring module."""
    api_name = safe_name.replace("_", " ")
    class_name = safe_name.title().replace("_", "")
    return f'''"""Phase 4: {title}

Generated from research:
{research[:400]}
"""

import logging
import statistics
from collections import deque
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


class {class_name}:
    """Safety and monitoring module for {api_name}.

    Tracks metrics, detects anomalies using z-score analysis,
    and maintains a rolling window of observations.
    """

    def __init__(self, window_size: int = 100, z_threshold: float = 3.0):
        self.window_size = window_size
        self.z_threshold = z_threshold
        self._metrics: dict[str, deque[float]] = {{}}
        self._alerts: list[dict[str, Any]] = []
        logger.info(f"Initialized {{self.__class__.__name__}} (window={{window_size}}, z_threshold={{z_threshold}})")

    def push_metric(self, name: str, value: float):
        """Push a metric observation."""
        if name not in self._metrics:
            self._metrics[name] = deque(maxlen=self.window_size)
        self._metrics[name].append(value)

        # Check for anomaly
        if len(self._metrics[name]) >= 10:
            z = self._compute_z(name, value)
            if abs(z) > self.z_threshold:
                self._alerts.append({{
                    "metric": name,
                    "value": value,
                    "z_score": round(z, 2),
                    "timestamp": datetime.now().isoformat(),
                    "severity": "CRITICAL" if abs(z) > self.z_threshold * 1.5 else "WARNING",
                }})

    def get_metric(self, name: str) -> Optional[dict[str, Any]]:
        """Get statistics for a named metric."""
        values = self._metrics.get(name)
        if not values or len(values) < 2:
            return None
        return {{
            "name": name,
            "count": len(values),
            "mean": round(statistics.mean(values), 3),
            "stdev": round(statistics.stdev(values), 3),
            "min": round(min(values), 3),
            "max": round(max(values), 3),
            "latest": values[-1],
        }}

    def _compute_z(self, name: str, value: float) -> float:
        """Compute z-score for a value against its metric history."""
        values = list(self._metrics[name])
        if len(values) < 2:
            return 0.0
        mean = statistics.mean(values)
        stdev = statistics.stdev(values)
        if stdev == 0:
            return 0.0
        return (value - mean) / stdev

    def get_alerts(self, severity: Optional[str] = None, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent alerts, optionally filtered by severity."""
        if severity:
            return [a for a in self._alerts[-limit:] if a["severity"] == severity]
        return self._alerts[-limit:]

    def all_metrics(self) -> list[str]:
        """List all tracked metric names."""
        return list(self._metrics.keys())

    def stats(self) -> dict[str, Any]:
        """Get module statistics."""
        return {{
            "metrics_tracked": len(self._metrics),
            "total_observations": sum(len(v) for v in self._metrics.values()),
            "active_alerts": len(self._alerts),
            "window_size": self.window_size,
        }}
'''


def _template_comms(safe_name: str, title: str, research: str) -> str:
    """Template: communications/API module."""
    api_name = safe_name.replace("_", " ")
    class_name = safe_name.title().replace("_", "")
    return f'''"""Phase 4: {title}

Generated from research:
{research[:400]}
"""

import json
import logging
from datetime import datetime
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class {class_name}:
    """Communications module for {api_name}.

    Handles outbound API calls with retry logic, rate limiting,
    and structured message formatting.
    """

    def __init__(self, base_url: str = "", timeout: float = 10.0, max_retries: int = 3):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None
        self._message_log: list[dict[str, Any]] = []
        logger.info(f"Initialized {{self.__class__.__name__}}")

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def send(self, endpoint: str, data: dict[str, Any],
                   method: str = "POST") -> dict[str, Any]:
        """Send a message to an API endpoint."""
        url = f"{{self.base_url}}/{{endpoint.lstrip('/')}}"
        client = await self._get_client()

        for attempt in range(self.max_retries):
            try:
                if method.upper() == "GET":
                    resp = await client.get(url, params=data)
                else:
                    resp = await client.post(url, json=data)

                response_data = resp.json() if resp.text else {{}}
                entry: dict[str, Any] = {{
                    "endpoint": endpoint,
                    "method": method,
                    "status_code": resp.status_code,
                    "response": response_data,
                    "attempt": attempt + 1,
                    "timestamp": datetime.now().isoformat(),
                }}
                self._message_log.append(entry)
                return entry

            except Exception as e:
                logger.warning(f"Attempt {{attempt + 1}}/{{self.max_retries}} failed: {{e}}")
                if attempt == self.max_retries - 1:
                    entry: dict[str, Any] = {{
                        "endpoint": endpoint,
                        "method": method,
                        "error": str(e),
                        "attempt": attempt + 1,
                        "timestamp": datetime.now().isoformat(),
                    }}
                    self._message_log.append(entry)
                    return entry

    async def broadcast(self, message: str, channel: str = "system") -> dict[str, Any]:
        """Broadcast a message (local event bus)."""
        event = {{
            "type": "broadcast",
            "channel": channel,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }}
        self._message_log.append(event)
        logger.info(f"Broadcast to {{channel}}: {{message[:50]}}...")
        return event

    def get_log(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent message log entries."""
        return self._message_log[-limit:]

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def stats(self) -> dict[str, Any]:
        """Get module statistics."""
        return {{
            "total_messages": len(self._message_log),
            "base_url": self.base_url,
            "client_active": self._client is not None,
        }}
'''


def _template_generic(safe_name: str, title: str, research: str) -> str:
    """Generic template for unknown subsystems."""
    class_name = safe_name.title().replace("_", "")
    return f'''"""Phase 4: {title}

Generated from research:
{research[:400]}
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class {class_name}:
    """Module for {title}.

    Generic implementation — adapt based on actual subsystem requirements.
    """

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {{}}
        self._state: dict[str, Any] = {{}}
        logger.info(f"Initialized {{self.__class__.__name__}}")

    async def execute(self, action: str, params: Optional[dict] = None) -> dict[str, Any]:
        """Execute an action in this module."""
        handler = getattr(self, f"_action_{{action}}", None)
        if not handler:
            return {{"status": "error", "message": f"Unknown action: {{action}}"}}
        return handler(params or {{}})

    def _action_init(self, params: dict) -> dict[str, Any]:
        self._state.update(params)
        return {{"status": "ok", "initialized": True}}

    def _action_status(self, params: dict) -> dict[str, Any]:
        return {{
            "status": "ok",
            "state_keys": list(self._state.keys()),
            "state_size": len(self._state),
        }}

    def _action_reset(self, params: dict) -> dict[str, Any]:
        self._state.clear()
        return {{"status": "ok", "reset": True}}

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} state={{len(self._state)}}>"
'''
