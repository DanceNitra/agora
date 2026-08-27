"""CLAUDE.md must declare exactly ONE current LLM state, and it must be the cloud one.

Written 2026-08-24, after the file carried TWO blocks both labelled `(current)` for two days: a
local-GPU block dated 2026-08-22 and an all-cloud block dated 2026-08-08, each asserting that it
superseded the other. Reading order decided which one won. I read the local one, reported local
models to the owner as though that were the design, and the dungeon sat dead for a full day while
Ollama Cloud was answering in 1.10 s the whole time.

The owner's standing rule is that nothing runs locally except embeddings, because he pays for the
cloud models the dungeon uses. That rule lived only in memory, so a dated status line in the repo
quietly outranked it. This probe puts the rule where the contradiction was.

Three checks, and the second is the one that would have caught the real defect:

  1. The standing rule is present and says embeddings are the only local thing.
  2. Exactly one block is labelled as the current state, and no block says `(current` as a status
     tag any more. Two competing "(current)" labels is the failure, not either label alone.
  3. The block that IS current names the cloud endpoint, not a localhost one.

stdlib only. Run it after any edit to the LLM section.
"""
from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DOC = os.path.join(os.path.dirname(HERE), "CLAUDE.md")
CURRENT_TAG = "THIS IS THE CURRENT STATE"
FALLBACK_TAG = "FALLBACK ONLY, NOT CURRENT"
RULE = "NOTHING RUNS LOCALLY EXCEPT"


def main() -> int:
    if not os.path.exists(DOC):
        raise SystemExit(f"REFUSED: {DOC} is absent; nothing here would be evidence")
    t = open(DOC, encoding="utf-8").read()
    sec = t.split("### LLM + data", 1)[1].split("\n---", 1)[0] if "### LLM + data" in t else ""

    # A status tag is a bullet that OPENS with the label. The two occurrences inside the
    # explanatory paragraph are prose about the rule and must not count, which is why this
    # looks for the bullet form rather than the bare substring.
    status_tags = re.findall(r"^- \*\*[^\n]*\(current[,)]", sec, re.M)
    current_blocks = re.findall(r"^- \*\*[^\n]*" + re.escape(CURRENT_TAG), sec, re.M)
    fallback_blocks = re.findall(r"^- \*\*[^\n]*" + re.escape(FALLBACK_TAG), sec, re.M)

    cur_body = sec.split(CURRENT_TAG, 1)[1].split("\n- **", 1)[0] if current_blocks else ""

    v: dict[str, bool] = {}
    v["the_llm_section_exists"] = bool(sec)
    v["the_standing_rule_is_stated_first"] = (
        RULE in sec and sec.index(RULE) < (sec.index(CURRENT_TAG) if current_blocks else len(sec)))
    v["the_rule_names_embeddings_as_the_only_local_thing"] = bool(
        re.search(r"NOTHING RUNS LOCALLY EXCEPT\s+EMBEDDINGS", sec))
    v["exactly_one_block_claims_to_be_current"] = len(current_blocks) == 1
    v["no_block_still_uses_the_ambiguous_current_tag"] = len(status_tags) == 0
    v["the_local_block_is_labelled_a_fallback"] = len(fallback_blocks) == 1
    v["the_current_block_points_at_the_cloud"] = "ollama.com" in cur_body
    v["the_current_block_does_not_point_at_localhost"] = "localhost:11434/v1\n" not in cur_body[:400]
    # control: the check must fail if a second current label is introduced
    mutated = sec.replace(FALLBACK_TAG, CURRENT_TAG, 1)
    v["CONTROL_a_second_current_label_would_be_caught"] = len(
        re.findall(r"^- \*\*[^\n]*" + re.escape(CURRENT_TAG), mutated, re.M)) == 2

    for k, ok in v.items():
        print(f"  {'YES' if ok else 'no '}  {k}")
    bad = [k for k, ok in v.items() if not ok]
    print(f"\n  blocks tagged current: {len(current_blocks)}   "
          f"fallback: {len(fallback_blocks)}   ambiguous '(current': {len(status_tags)}")
    if bad:
        print("  FAILED: " + ", ".join(bad))
    json.dump({"probe": os.path.basename(__file__), "verdicts": v,
               "current_blocks": len(current_blocks), "fallback_blocks": len(fallback_blocks),
               "ambiguous_tags": len(status_tags)},
              open(os.path.join(HERE, "claude_md_declares_exactly_one_current_llm_state.result.json"),
                   "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
