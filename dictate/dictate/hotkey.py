"""Global hotkey listener with hold and toggle modes.

Matches keys by virtual-key code so left/right variants of modifiers
(ctrl_l vs ctrl_r) both work. pynput's Windows listener reports the
specific variant (Key.ctrl_l, vk 162), so generic names must expand to
all their VK codes.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from pynput import keyboard

logger = logging.getLogger(__name__)

# Virtual key codes for modifier aliases, including generic and variants.
_VK_ALIASES: dict[str, set[int]] = {
    "ctrl": {17, 162, 163},
    "alt": {18, 164, 165},
    "shift": {160, 161},
    "space": {32},
    "enter": {13},
    "tab": {9},
}


def _vk_codes(name: str) -> set[int]:
    """Return the set of VK codes that a combo element name matches."""
    name = name.strip().lower()
    if name in _VK_ALIASES:
        return _VK_ALIASES[name]
    if len(name) == 1:
        return {ord(name.upper())}
    if name.startswith("f") and name[1:].isdigit():
        number = int(name[1:])
        if 1 <= number <= 24:
            return {0x70 + number - 1}  # VK_F1 = 0x70
    raise ValueError(f"Unsupported hotkey element: {name!r}")


def _key_vks(key) -> set[int]:
    """Return the VK codes for a pynput press/release event."""
    if isinstance(key, keyboard.KeyCode):
        return {key.vk} if key.vk is not None else set()
    vk = getattr(key.value, "vk", None)
    return {vk} if vk is not None else set()


class HotkeyListener:
    """Listen for a global key combo with hold or toggle semantics.

    ``on_activate`` runs when the combo becomes active and
    ``on_deactivate`` when it ends. Callbacks run in the listener thread;
    they must be fast or dispatch work to another thread.
    """

    def __init__(
        self,
        combo: str,
        on_activate: Callable[[], None],
        on_deactivate: Callable[[], None],
        mode: str = "hold",
    ) -> None:
        parts = [p.strip().lower() for p in combo.split("+") if p.strip()]
        if len(parts) < 2:
            raise ValueError(f"Hotkey {combo!r} needs a modifier and a trigger")
        self.mode = mode
        self.on_activate = on_activate
        self.on_deactivate = on_deactivate
        self.modifier_vks: set[int] = set()
        for part in parts[:-1]:
            self.modifier_vks |= _vk_codes(part)
        self.trigger_vks = _vk_codes(parts[-1])
        self._listener: keyboard.Listener | None = None
        self._pressed: set[int] = set()
        self._active = False

    def _matches(self) -> bool:
        """Return True if all modifier VKs and the trigger are pressed."""
        return self.modifier_vks.issubset(self._pressed) and bool(
            self.trigger_vks & self._pressed
        )

    def _on_press(self, key) -> None:
        self._pressed |= _key_vks(key)
        if self._active:
            return
        if not self._matches():
            return
        self._active = True
        self.on_activate()

    def _on_release(self, key) -> None:
        self._pressed -= _key_vks(key)
        if self.mode == "hold":
            if (
                self._active
                and _key_vks(key) & self.trigger_vks
                and not self.trigger_vks & self._pressed
            ):
                self._active = False
                self.on_deactivate()
        else:  # toggle
            if _key_vks(key) & self.trigger_vks and self._active:
                self._active = False
                self.on_deactivate()

    def start(self) -> None:
        """Start listening for the hotkey."""
        if self._listener is None:
            self._listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release,
            )
            self._listener.start()

    def stop(self) -> None:
        """Stop listening."""
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
            self._pressed.clear()
            self._active = False

