"""Does a `description:` written as a YAML block scalar (`>`, `>-`, `|`, or a plain multi-line) reach the model?

WHY. anthropics/claude-code#81081, comment of 2026-09-15 by @tonydzi: on a shelf of 189 skills,
"68 of those 189 descriptions arrived as a heading rather than as text - they were written as a YAML
folded block scalar (description: >), so the trigger words never reached the model at all", and
converting 5 of 5 to a quoted one-liner brought them back. If true it is a second, format-shaped
route to the same silent loss the issue is about, and it would be indistinguishable from the budget
drop from the author's chair. It is also a one-fixture measurement, so it is measured here rather
than repeated.

THE FIXTURE, minimal on purpose. One text, five spellings, and nothing else varies:

    F  folded          description: >          (two indented lines)
    S  folded-strip    description: >-         (two indented lines)
    L  literal         description: |          (two indented lines)
    P  plain-multiline description: first line, then one indented continuation line
    Q  quoted-control  description: "the text on one line"

All five parse under strict YAML to the same words (the block styles differ only in line ending
handling), which the probe asserts before running anything. Q is the positive control: it is the
spelling the comment says works. Two tiers, project (`.claude/skills`) and user (`<config>/skills`),
because a loader difference between them is exactly what a one-shelf report cannot see.

READ FROM THE WIRE, NOT FROM THE MODEL. `ANTHROPIC_BASE_URL` points at a local recorder; the listing
is read out of the request body's system text. An empty isolated `CLAUDE_CONFIG_DIR` so no budget
pressure from the real install, asserted by behaviour: no pre-existing entry may be name-only.

OUTCOMES per case, computed from the wire: ARRIVES (the words are there), DROPPED (name listed,
no description), ALTERED (description present but not the same words), ABSENT (name not listed).
"""
from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time

import yaml

sys.stdout.reconfigure(line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import is_a_skill_truncated_the_way_the_memory_index_is as S  # noqa: E402
S.PORT = 8923
import which_skills_lose_their_description_on_this_install as W  # noqa: E402
import does_an_unquoted_colon_space_still_hide_a_skill as C  # noqa: E402

NL = chr(10)
OUT = os.path.join(HERE, "does_a_folded_scalar_description_arrive_at_the_model.result.json")
START = time.time()
LINE1 = "Audits a deploy plan for rollback gaps and names the step that cannot be undone."
LINE2 = "Use when a plan touches production data or a schema and no one has listed the reversal."
WORDS = (LINE1 + " " + LINE2).split()

CASES = [
    ("folded", "description: >" + NL + "  " + LINE1 + NL + "  " + LINE2),
    ("folded-strip", "description: >-" + NL + "  " + LINE1 + NL + "  " + LINE2),
    ("literal", "description: |" + NL + "  " + LINE1 + NL + "  " + LINE2),
    ("plain-multiline", "description: " + LINE1 + NL + "  " + LINE2),
    ("quoted-control", 'description: "' + LINE1 + " " + LINE2 + '"'),
]


def refuse(why: str):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why}, io.open(OUT, "w", encoding="utf-8"), indent=1)
    raise SystemExit(2)


def parsed_words(text: str) -> list:
    lines = text.split(NL)
    end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    return str(yaml.safe_load(NL.join(lines[1:end]))["description"]).split()


def build(dirs: dict) -> dict:
    """dirs: tier -> skills directory. Returns tier -> {name: case}."""
    fx = {}
    for tier, skills_dir in dirs.items():
        fx[tier] = {}
        for label, block in CASES:
            name = "bs-%s-%s" % (tier[0], label)
            text = C.write_skill(os.path.join(skills_dir, name), name, block)
            if parsed_words(text) != WORDS:
                refuse("fixture control: %s/%s does not parse under strict YAML to the fixture's words"
                       % (tier, label))
            fx[tier][name] = label
    return fx


def outcome(listed: bool, desc: str) -> str:
    if not listed:
        return "ABSENT"
    if not desc.strip():
        return "DROPPED"
    return "ARRIVES" if desc.split() == WORDS else "ALTERED"


def main() -> int:
    mt_before = (os.path.getmtime(W.REAL_PROFILE), os.path.getsize(W.REAL_PROFILE))
    cfg = tempfile.mkdtemp(prefix="bscfg_")
    root = tempfile.mkdtemp(prefix="bsproj_")
    json.dump({}, io.open(os.path.join(cfg, ".claude.json"), "w", encoding="utf-8"))
    json.dump({}, io.open(os.path.join(cfg, "settings.json"), "w", encoding="utf-8"))
    fx = build({"project": os.path.join(root, ".claude", "skills"),
                "user": os.path.join(cfg, "skills")})
    names = [n for tier in fx.values() for n in tier]

    srv = S.recorder(S.PORT)
    try:
        cap = C.capture(cfg, root)
    finally:
        srv.shutdown()
    if not cap:
        refuse("the session produced no request body")
    ents = C.read_entries(cap["wire"], names)
    starved = [n for n, d in ents.items() if not d and not n.startswith("bs-")]
    if starved:
        refuse("the budget is already biting in this fixture: %d pre-existing entries are name-only (%s)"
               % (len(starved), ", ".join(sorted(starved)[:5])))
    arms = {}
    for tier, cases in fx.items():
        arms[tier] = {}
        for name, label in cases.items():
            d = ents.get(name, "")
            arms[tier][label] = {"listed": name in ents, "description_chars": len(d),
                                 "outcome": outcome(name in ents, d), "description": d[:220]}
    for tier in arms:
        if arms[tier]["quoted-control"]["outcome"] != "ARRIVES":
            refuse("%s tier: the quoted one-liner control did not arrive (%s); the fixture never reached "
                   "the prompt or the text itself is refused, so the block cases separate nothing"
                   % (tier, arms[tier]["quoted-control"]["outcome"]))
    mt_after = (os.path.getmtime(W.REAL_PROFILE), os.path.getsize(W.REAL_PROFILE))
    if mt_after != mt_before:
        refuse("the real ~/.claude.json changed during the run; isolation failed")

    lost = sorted({label for tier in arms for label, a in arms[tier].items() if a["outcome"] != "ARRIVES"})
    per_tier_differs = any(arms["project"][l]["outcome"] != arms["user"][l]["outcome"] for _, l in
                           [(0, c[0]) for c in CASES])
    if not lost:
        verdict = ("every block-scalar spelling arrives with its full text on both tiers on this build; the "
                   "folded-scalar route does not reproduce here")
    else:
        verdict = "these spellings do not arrive intact: " + ", ".join(
            "%s (%s/%s)" % (l, arms["project"][l]["outcome"], arms["user"][l]["outcome"]) for l in lost)
    res = {
        "probe": os.path.basename(__file__),
        "when_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "claude_version": subprocess.run([S.CLAUDE, "--version"], capture_output=True, text=True).stdout.strip(),
        "platform": sys.platform,
        "claim_under_test": "anthropics/claude-code#81081, @tonydzi 2026-09-15: a `description: >` folded "
                            "scalar arrives as a heading, 68 of 189 on their shelf",
        "fixture_words": len(WORDS),
        "listing_entries_on_wire": len(ents),
        "arms": arms,
        "tiers_differ": per_tier_differs,
        "controls": {"all_five_parse_to_the_same_words": True,
                     "quoted_control_arrives_on_both_tiers": True,
                     "no_preexisting_entry_name_only": True,
                     "real_profile_untouched": True},
        "elapsed_s": round(time.time() - START, 1),
        "verdict": verdict,
    }
    for tier in arms:
        for label, a in arms[tier].items():
            print("  %-8s %-16s %-8s %4d chars" % (tier, label, a["outcome"], a["description_chars"]))
    print("  " + verdict)
    json.dump(res, io.open(OUT, "w", encoding="utf-8"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
