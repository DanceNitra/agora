"""Entry point for the packaged setup wizard."""

import sys

from dictate.setup_wizard import main

if __name__ == "__main__":
    # --help-page opens the instructions directly, for the Start menu shortcut.
    raise SystemExit(main(page=3 if "--help-page" in sys.argv else 0))
