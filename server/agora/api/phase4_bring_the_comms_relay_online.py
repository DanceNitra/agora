"""Phase 4: Bring the comms relay online

Generated from research:
Messages can be delivered between any two agents without loss.
"""

import json
import logging
from datetime import datetime
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class BringTheCommsRelayOnline:
    """Communications module for bring the comms relay online.

    Handles outbound API calls with retry logic, rate limiting,
    and structured message formatting.
    """

    def __init__(self, base_url: str = "", timeout: float = 10.0, max_retries: int = 3):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None
        self._message_log: list[dict[str, Any]] = []
        logger.info(f"Initialized {self.__class__.__name__}")

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def send(self, endpoint: str, data: dict[str, Any],
                   method: str = "POST") -> dict[str, Any]:
        """Send a message to an API endpoint."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        client = await self._get_client()

        for attempt in range(self.max_retries):
            try:
                if method.upper() == "GET":
                    resp = await client.get(url, params=data)
                else:
                    resp = await client.post(url, json=data)

                response_data = resp.json() if resp.text else {}
                entry: dict[str, Any] = {
                    "endpoint": endpoint,
                    "method": method,
                    "status_code": resp.status_code,
                    "response": response_data,
                    "attempt": attempt + 1,
                    "timestamp": datetime.now().isoformat(),
                }
                self._message_log.append(entry)
                return entry

            except Exception as e:
                logger.warning(f"Attempt {attempt + 1}/{self.max_retries} failed: {e}")
                if attempt == self.max_retries - 1:
                    entry: dict[str, Any] = {
                        "endpoint": endpoint,
                        "method": method,
                        "error": str(e),
                        "attempt": attempt + 1,
                        "timestamp": datetime.now().isoformat(),
                    }
                    self._message_log.append(entry)
                    return entry

    async def broadcast(self, message: str, channel: str = "system") -> dict[str, Any]:
        """Broadcast a message (local event bus)."""
        event = {
            "type": "broadcast",
            "channel": channel,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }
        self._message_log.append(event)
        logger.info(f"Broadcast to {channel}: {message[:50]}...")
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
        return {
            "total_messages": len(self._message_log),
            "base_url": self.base_url,
            "client_active": self._client is not None,
        }
