"""Entry point for the packaged setup wizard."""

import sys

from dictate.log import ensure_streams

ensure_streams()

from dictate.setup_wizard import main  # noqa: E402  streams first

if __name__ == "__main__":
    # --help-page opens the instructions directly, for the Start menu shortcut.
    raise SystemExit(main(page=3 if "--help-page" in sys.argv else 0))
