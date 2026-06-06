"""Circuit breaker pattern with per-tool instances and half-open state."""

import time
import threading
from typing import Optional


class CircuitState:
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Per-tool circuit breaker with configurable threshold and cooldown.

    Tracks consecutive failures for each named tool. After *threshold*
    failures the circuit opens; after *cooldown* seconds it transitions
    to half-open, allowing a single probe call to decide whether to
    close or re-open.
    """

    def __init__(self, threshold: int = 3, cooldown: float = 5.0):
        self._threshold = threshold
        self._cooldown = cooldown
        self._lock = threading.Lock()

        # Per-tool state
        self._failures: dict[str, int] = {}
        self._states: dict[str, str] = {}
        self._last_open_time: dict[str, float] = {}

    def _ensure_tool(self, tool_name: str) -> None:
        if tool_name not in self._states:
            self._states[tool_name] = CircuitState.CLOSED
            self._failures[tool_name] = 0

    def record_failure(self, tool_name: str) -> str:
        """Record a failure for the given tool and return the new state."""
        with self._lock:
            self._ensure_tool(tool_name)
            self._failures[tool_name] += 1
            if self._failures[tool_name] >= self._threshold:
                self._states[tool_name] = CircuitState.OPEN
                self._last_open_time[tool_name] = time.time()
            return self._states[tool_name]

    def record_success(self, tool_name: str) -> str:
        """Record a success for the given tool and reset failure count."""
        with self._lock:
            self._ensure_tool(tool_name)
            self._failures[tool_name] = 0
            self._states[tool_name] = CircuitState.CLOSED
            return self._states[tool_name]

    def allow_request(self, tool_name: str) -> bool:
        """Check whether a request to the given tool should be allowed.

        Transitions to HALF_OPEN automatically when cooldown has elapsed.
        """
        with self._lock:
            self._ensure_tool(tool_name)
            state = self._states[tool_name]

            if state == CircuitState.CLOSED:
                return True

            if state == CircuitState.OPEN:
                last_open = self._last_open_time.get(tool_name, 0.0)
                if time.time() - last_open >= self._cooldown:
                    # Transition to half-open
                    self._states[tool_name] = CircuitState.HALF_OPEN
                    return True
                return False

            # HALF_OPEN — allow exactly one probe
            return True

    def get_state(self, tool_name: str) -> str:
        """Return the current circuit state for a tool."""
        with self._lock:
            self._ensure_tool(tool_name)
            return self._states[tool_name]

    def get_failure_count(self, tool_name: str) -> int:
        """Return the current failure count for a tool."""
        with self._lock:
            self._ensure_tool(tool_name)
            return self._failures[tool_name]

    def reset(self, tool_name: Optional[str] = None) -> None:
        """Reset circuit state. If tool_name is None, reset all tools."""
        with self._lock:
            if tool_name:
                self._ensure_tool(tool_name)
                self._states[tool_name] = CircuitState.CLOSED
                self._failures[tool_name] = 0
                self._last_open_time.pop(tool_name, None)
            else:
                self._failures.clear()
                self._states.clear()
                self._last_open_time.clear()
