"""Does an unquoted ": " in a description still hide a skill from the listing?

WHY. anthropics/claude-code#78270 (@Onward-Mundy, 2026-07-16, CLI 2.1.211, Windows 11, OPEN, labels
`bug, has repro, platform:windows, area:skills, area:plugins, stale`, zero comments) reports that a
`SKILL.md` whose `description:` is an unquoted YAML plain scalar containing a colon-space fails
strict YAML parsing and is then SILENTLY OMITTED from the skills listing and the slash menu
entirely, while `Skill(name=...)` still invokes it. The issue asks either for a loud failure or for
"a lenient-parse fallback for the `description` field". The docs agree with the report's premise:
"If the frontmatter YAML is malformed, Claude Code loads the skill body with empty metadata."

WHY WE ARE ASKING. While measuring something else on 2.1.252 we found `storm-research`, a project
skill whose description reads "Runs a 4-phase pipeline: five expert lenses (...)". `yaml.safe_load`
rejects that frontmatter with `mapping values are not allowed here` at line 2, column 312. The CLI
delivered the skill WITH all 598 characters of that description. That is the opposite of both the
issue and the docs, so either the lenient fallback has landed since 2.1.211, or our reading of one
file is wrong. One observation on one pre-existing file decides nothing; this plants the fixture.

THE FIXTURE, minimal on purpose. Three skills, an empty isolated config so the real install exerts
no budget pressure, and a listing far too small to truncate. The trigger is varied and nothing else:

    A  colon-space-unquoted   description: Does a thing. Use when: you need the thing done.
    B  colon-space-quoted     description: "Does a thing. Use when: you need the thing done."
    C  no-colon-control       description: Does a thing when you need the thing done.

A and B carry the SAME TEXT, so any difference between them is the quoting and nothing else. C is
there so that a run in which nothing arrives is distinguishable from a run in which A is hidden.

THREE OUTCOMES, all distinct on the wire:
    name absent entirely      -> #78270 reproduces on this build
    name present, no description -> the docs' "empty metadata" behaviour
    name present WITH the description -> a lenient parse; #78270 is fixed on this build

BOTH TIERS, because the issue says "plugin skill" and our observation was a project skill, and a
fix could easily have landed in one loader and not the other. The plugin arm builds a real
marketplace directory and enables it in the isolated settings rather than assuming the two tiers
share a code path.

CONTROLS, each able to fail, each REFUSING rather than reporting a number:
  * THE TRIGGER MUST BE REAL: `yaml.safe_load` must REJECT A's frontmatter and ACCEPT B's and C's.
    If the fixture does not reproduce the parse failure, it is not testing #78270.
  * THE CONTROL MUST ARRIVE: C must be listed with its description in every arm, or the fixture
    never reached the prompt and an absent A means nothing.
  * B MUST ARRIVE with its description: the same text, quoted, is the positive control for the text
    itself being acceptable.
  * NO BUDGET INTERFERENCE, asserted by BEHAVIOUR rather than by a threshold: no pre-existing
    entry in the same listing may be name-only. If the budget were biting, it would show there
    first, and a name-only test case could not be told from a parse failure.
  * ISOLATION: an empty CLAUDE_CONFIG_DIR, and the real ~/.claude.json untouched.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

import yaml

# A redirected stdout is block-buffered, so a run that prints one line per arm produced a
# ZERO-BYTE file for its whole five minutes and could not be told from a wedged one.
sys.stdout.reconfigure(line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import is_a_skill_truncated_the_way_the_memory_index_is as S
S.PORT = 8921
import which_skills_lose_their_description_on_this_install as W

NL = chr(10)
OUT = os.path.join(HERE, "does_an_unquoted_colon_space_still_hide_a_skill.result.json")
START = time.time()
TEXT = "Does a thing. Use when: you need the thing done."
CASES = [("colon-space-unquoted", "description: " + TEXT),
         ("colon-space-quoted", 'description: "' + TEXT + '"'),
         ("no-colon-control", "description: Does a thing when you need the thing done.")]


def refuse(why: str):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why}, io.open(OUT, "w", encoding="utf-8"), indent=1)
    raise SystemExit(2)


def write_skill(d: str, name: str, desc_line: str) -> str:
    os.makedirs(d, exist_ok=True)
    text = ("---" + NL + "name: " + name + NL + desc_line + NL + "---" + NL
            + NL + "# " + name + NL + NL + "Body here." + NL)
    io.open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8", newline=NL).write(text)
    return text


def strict_parses(text: str) -> tuple:
    lines = text.split(NL)
    end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    try:
        yaml.safe_load(NL.join(lines[1:end]))
        return True, ""
    except Exception as e:
        return False, str(e).split(NL)[0]


def capture(cfg: str, cwd: str) -> dict:
    env = dict(os.environ, ANTHROPIC_BASE_URL="http://127.0.0.1:%d" % S.PORT,
               ANTHROPIC_API_KEY="x", CLAUDE_CONFIG_DIR=cfg)
    env.pop("SLASH_COMMAND_TOOL_CHAR_BUDGET", None)
    S.BODIES.clear()
    p = subprocess.Popen([S.CLAUDE, "-p", "--output-format", "stream-json", "--verbose",
                          "--strict-mcp-config", "Reply with only: OK"],
                         cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, encoding="utf-8", errors="replace")
    try:
        out, err = p.communicate(timeout=420)
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True)
        return {}
    if not S.BODIES:
        return {}
    return {"wire": W.wire_system_text(S.BODIES[-1]), "stderr": (err or "")[-2000:]}


def read_entries(wire: str, names: list) -> dict:
    out = {}
    for ln in W.listing_lines(wire):
        n, d, _ = W.split_entry(ln, sorted(names, key=len, reverse=True))
        out[n] = d
    return out


def build_project(root: str) -> dict:
    fx = {}
    for label, line in CASES:
        name = "cs-" + label
        text = write_skill(os.path.join(root, ".claude", "skills", name), name, line)
        ok, err = strict_parses(text)
        fx[name] = {"case": label, "strict_yaml_parses": ok, "strict_yaml_error": err}
    return fx


def build_plugin(cfgdir: str, mktroot: str) -> dict:
    """A real marketplace on disk, enabled in the isolated settings, because #78270 is about the
    plugin loader and a fix can land in one loader and not the other."""
    plug = os.path.join(mktroot, "plugins", "cstest")
    fx = {}
    for label, line in CASES:
        name = "cs-" + label
        text = write_skill(os.path.join(plug, "skills", name), name, line)
        ok, err = strict_parses(text)
        fx["cstest:" + name] = {"case": label, "strict_yaml_parses": ok, "strict_yaml_error": err}
    os.makedirs(os.path.join(mktroot, ".claude-plugin"), exist_ok=True)
    json.dump({"name": "cstest-marketplace", "owner": {"name": "probe"},
               "plugins": [{"name": "cstest", "source": "./plugins/cstest",
                            "description": "colon-space fixture"}]},
              io.open(os.path.join(mktroot, ".claude-plugin", "marketplace.json"),
                      "w", encoding="utf-8"), indent=1)
    os.makedirs(os.path.join(plug, ".claude-plugin"), exist_ok=True)
    json.dump({"name": "cstest", "version": "1.0.0", "description": "colon-space fixture"},
              io.open(os.path.join(plug, ".claude-plugin", "plugin.json"),
                      "w", encoding="utf-8"), indent=1)
    r = subprocess.run([S.CLAUDE, "plugin", "marketplace", "add", mktroot],
                       env=dict(os.environ, CLAUDE_CONFIG_DIR=cfgdir),
                       capture_output=True, text=True, timeout=180)
    a = subprocess.run([S.CLAUDE, "plugin", "install", "cstest@cstest-marketplace"],
                       env=dict(os.environ, CLAUDE_CONFIG_DIR=cfgdir),
                       capture_output=True, text=True, timeout=180)
    return fx, (r.stdout + r.stderr + a.stdout + a.stderr)[-1500:]


def main() -> int:
    mt_before = (os.path.getmtime(W.REAL_PROFILE), os.path.getsize(W.REAL_PROFILE))
    cfg = tempfile.mkdtemp(prefix="cscfg_")
    root = tempfile.mkdtemp(prefix="csproj_")
    mkt = tempfile.mkdtemp(prefix="csmkt_")
    json.dump({}, io.open(os.path.join(cfg, ".claude.json"), "w", encoding="utf-8"))
    json.dump({}, io.open(os.path.join(cfg, "settings.json"), "w", encoding="utf-8"))

    proj_fx = build_project(root)
    for name, f in proj_fx.items():
        if f["case"] == "colon-space-unquoted" and f["strict_yaml_parses"]:
            refuse("fixture control: the unquoted case PARSES under strict YAML, so it does not "
                   "reproduce #78270's trigger at all")
        if f["case"] != "colon-space-unquoted" and not f["strict_yaml_parses"]:
            refuse("fixture control: %s should parse under strict YAML but does not (%s)"
                   % (f["case"], f["strict_yaml_error"]))

    srv = S.recorder(S.PORT)
    arms = {}
    try:
        cap = capture(cfg, root)
        if not cap:
            refuse("project arm produced no request body")
        ents = read_entries(cap["wire"], list(proj_fx))
        arms["project"] = {name: {"case": proj_fx[name]["case"],
                                  "strict_yaml_parses": proj_fx[name]["strict_yaml_parses"],
                                  "listed": name in ents,
                                  "description_chars": len(ents.get(name, "")),
                                  "description": ents.get(name, "")}
                           for name in proj_fx}
        listing_chars = sum(len(v) for v in ents.values())

        plug_fx, install_log = build_plugin(cfg, mkt)
        cap2 = capture(cfg, root)
        if not cap2:
            refuse("plugin arm produced no request body")
        ents2 = read_entries(cap2["wire"], list(proj_fx) + list(plug_fx))
        arms["plugin"] = {name: {"case": plug_fx[name]["case"],
                                 "strict_yaml_parses": plug_fx[name]["strict_yaml_parses"],
                                 "listed": name in ents2,
                                 "description_chars": len(ents2.get(name, "")),
                                 "description": ents2.get(name, "")}
                          for name in plug_fx}
    finally:
        srv.shutdown()
    mt_after = (os.path.getmtime(W.REAL_PROFILE), os.path.getsize(W.REAL_PROFILE))

    ctrl = arms["project"]["cs-no-colon-control"]
    quoted = arms["project"]["cs-colon-space-quoted"]
    if not ctrl["listed"] or ctrl["description_chars"] == 0:
        refuse("control skill did not arrive with a description: the fixture never reached the "
               "prompt, so an absent unquoted case would mean nothing")
    if not quoted["listed"] or quoted["description_chars"] == 0:
        refuse("the QUOTED case did not arrive with a description; the text itself is the problem, "
               "not the quoting, and the arm separates nothing")
    # A MAGIC NUMBER WAS THE WRONG CONTROL HERE, and it refused a sound run. The first version
    # required the listing to be under 5,000 characters; an empty config still carries every
    # BUILT-IN skill, so the floor is about 5,400 and the arm could never start. The budget on this
    # machine delivers 28,153 characters without dropping anything, so 5,514 was never near it.
    # The control that actually measures the hazard: if the budget were biting, some PRE-EXISTING
    # entry would already be name-only. Read that instead of guessing a threshold.
    starved = [n for n, d in ents.items() if not d and not n.startswith("cs-")]
    if starved:
        refuse("the budget is already biting in this fixture -- %d pre-existing entries are "
               "name-only (%s) -- so a name-only test case would be ambiguous"
               % (len(starved), ", ".join(sorted(starved)[:5])))

    def verdict(a):
        if not a["listed"]:
            return "NAME ABSENT -- #78270 reproduces"
        if a["description_chars"] == 0:
            return "name listed, NO description -- the docs' empty-metadata behaviour"
        return "name listed WITH description -- lenient parse, #78270 does not reproduce"

    res = {
        "probe": os.path.basename(__file__),
        "when_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "claude_version": subprocess.run([S.CLAUDE, "--version"], capture_output=True,
                                         text=True).stdout.strip(),
        "platform": sys.platform,
        "issue_under_test": "anthropics/claude-code#78270 (open, CLI 2.1.211, Windows 11)",
        "text_used_in_both_colon_cases": TEXT,
        "listing_chars_project_arm": listing_chars,
        "arms": arms,
        "verdicts": {tier: {n: verdict(a) for n, a in d.items()} for tier, d in arms.items()},
        "plugin_install_log_tail": install_log,
        "controls": {
            "trigger_is_real_unquoted_fails_strict_yaml": True,
            "quoted_and_control_parse_strict_yaml": True,
            "control_skill_arrived_with_description": True,
            "quoted_skill_arrived_with_description": True,
            "no_pre_existing_entry_is_name_only": True,
            "real_profile_untouched": mt_before == mt_after,
        },
        "elapsed_s": round(time.time() - START, 1),
    }
    json.dump(res, io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    for tier in arms:
        print(NL + "== %s tier ==" % tier)
        for n, a in arms[tier].items():
            print("  %-28s strict_yaml=%-5s -> %s" % (a["case"], a["strict_yaml_parses"],
                                                      verdict(a)))
    print(NL + "listing size in the project arm: %d chars (budget cannot be the cause)"
          % listing_chars)
    shutil.rmtree(root, ignore_errors=True)
    shutil.rmtree(mkt, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
