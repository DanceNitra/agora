#!/usr/bin/env python3
"""Compatibility name. The tool moved to tools/channels_ops.py on 2026-09-21 when Reddit, X and Bluesky joined the ledger."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from channels_ops import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
