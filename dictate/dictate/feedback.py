"""Beep feedback for recording start/stop/error."""

from __future__ import annotations

import time


def beep_start(enabled: bool = True) -> None:
    """Two short beeps: recording has started."""
    if not enabled:
        return
    import winsound

    winsound.Beep(1200, 90)
    time.sleep(0.03)
    winsound.Beep(1200, 90)


def beep_stop(enabled: bool = True) -> None:
    """One long beep: recording has stopped."""
    if not enabled:
        return
    import winsound

    winsound.Beep(1600, 300)


def beep_error(enabled: bool = True) -> None:
    """One low beep: an error occurred or the take was discarded."""
    if not enabled:
        return
    import winsound

    winsound.Beep(400, 400)
