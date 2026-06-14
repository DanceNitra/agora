#!/usr/bin/env python3
"""
second_brain demo — what your agent sees when it thinks over your notes.

Runs the second_brain MCP tools against the bundled sample vault (examples/sample_vault) and prints
a narrated session. No MCP client, no API key, no embedder needed — zero config, lexical fallback.

    python examples/demo.py

This is the source for the README demo and the VHS recording (examples/demo.tape).
"""
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ.setdefault("NOTES_DIR", str(HERE / "sample_vault"))
os.environ.setdefault("SECOND_BRAIN_INDEX", str(HERE / ".demo_index.json"))
# fresh index each run so the demo is deterministic
try:
    Path(os.environ["SECOND_BRAIN_INDEX"]).unlink()
except OSError:
    pass

import sys
sys.path.insert(0, str(HERE.parent / "mnemo"))
import second_brain_mcp as sb  # noqa: E402


def show(label, value):
    print(f"\n\033[1;36m▸ {label}\033[0m")
    print(json.dumps(value, indent=2, ensure_ascii=False))


def main():
    print("\033[1msecond_brain — your notes, thinking\033[0m")
    print("(the server gives the agent retrieval + structure; the agent does the reasoning)\n")
    print("$ NOTES_DIR=examples/sample_vault python second_brain_mcp.py")

    show("index_status()  — what's loaded", sb.index_status())

    show('relevant_notes("how does feedback speed up learning", k=3)',
         sb.relevant_notes("how does feedback speed up learning", k=3))

    show("find_gaps()  — where the network is blind", sb.find_gaps())

    show('bridge_candidates("Deliberate Practice", k=3)  — non-obvious connections',
         sb.bridge_candidates("Deliberate Practice", k=3))

    show('extract_claims("Deliberate Practice")  — what an agent can ground/challenge',
         sb.extract_claims("Deliberate Practice"))

    methods = sb.idea_methods()
    show(f"idea_methods()  — {len(methods)} recipes to generate ideas (showing 3)", methods[:3])

    print("\n\033[1;32mThat's the substrate.\033[0m An agent now grounds the claims against real")
    print("literature, writes the bridge it just found, or generates an idea by a named method —")
    print("over YOUR notes, not a generic model's training data.\n")


if __name__ == "__main__":
    main()
