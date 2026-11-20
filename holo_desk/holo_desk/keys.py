"""The Anthropic key lives in Windows Credential Manager, entered once in a masked dialog."""

from __future__ import annotations

import os

import keyring

SERVICE = "holo-desk"
ACCOUNT = "anthropic-api-key"


def anthropic_key() -> str | None:
    """Return the key from the environment, Credential Manager, or a one-time prompt."""
    key = os.environ.get("ANTHROPIC_API_KEY") or keyring.get_password(SERVICE, ACCOUNT)
    if key:
        return key
    key = _prompt()
    if key:
        keyring.set_password(SERVICE, ACCOUNT, key)
    return key


def _prompt() -> str | None:
    import tkinter as tk
    from tkinter import simpledialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    key = simpledialog.askstring(
        "Yuki: Claude API key",
        "Paste the Anthropic API key (sk-ant-...). It is saved in Windows Credential Manager.",
        show="*", parent=root)
    root.destroy()
    key = (key or "").strip()
    return key if key.startswith("sk-ant-") else None
