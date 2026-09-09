"""Text injection base class."""

from __future__ import annotations

from abc import ABC, abstractmethod


class TextInjector(ABC):
    """Insert text at the cursor of a target window."""

    @abstractmethod
    def insert(self, text: str, target_hwnd: int = 0) -> None:
        """Insert ``text`` into ``target_hwnd`` (0 = focused window)."""
