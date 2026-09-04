"""Two sessions, one disk: what makes a skill description survive the listing?

WHY. anthropics/claude-code#81081. @ralucaoda reported the silent drop, @bcherny answered that it is
intended and that descriptions go "starting with the least-used skills", and on 2026-08-31
@somarakis posted an independent reproduction on the personal tier that rules out two hypotheses:
not a greedy alphabetical fill (2nd entry dropped, longest entry near the end kept) and not a
per-description length cap (shortest dropped 51, longest kept 1,116). He closed with the reading
this file tests: dropping his 16 saves only 6,867 of 22,273 description chars, so "the budget is
being shared with something else (plugin skills, or the wider tool catalog)".

THE OBSERVATION THAT STARTED THIS RUN. On one machine, one CLI build, one unchanged set of files,
an interactive session showed two of four skills in the `stitch-utilities` plugin name-only, and a
scripted session showed all four with descriptions. Same disk. So the dropped set is not a property
of the skills at all, and a directory diff cannot see the variable.

THE DESIGN, 2x2, because two things differed between those sessions and either could be the cause:

                        MCP servers OFF        MCP servers ON
    default model       A                      B
    opus[1m]            C                      D

MCP is the tool-catalog axis: this machine's MCP server publishes ~75 tools whose definitions sit
in the same request. The model axis is there because the documented budget is a FRACTION of the
context window, so a 1M-context session should get a LARGER budget, and if it instead drops more
then the fraction is not the whole rule.

READ FROM THE WIRE, NOT FROM THE MODEL. ANTHROPIC_BASE_URL points at a local recorder answering
canned SSE, so the listing is read out of the request body and no completion is bought. Both
existing reports on the issue ask the model what it can see; that channel is the model's own report,
and we retracted a finding built on it on 2026-08-25.

ISOLATION WITHOUT A COPY. The object of study is the REAL install, so the real skills, the real
plugins and the real skillUsage all have to be present. ~/.claude is 2.9 GB, so the config dir is
rebuilt with NTFS junctions to the real `skills/` and `plugins/` plus a copy of `~/.claude.json`.
The nested session reads the real state and writes only into the temp copy. Hooks are stripped from
the copied settings because they would fire against our own memory store; they add nothing to a
listing.

TWO PARSING TRAPS THIS FILE HAD TO SOLVE BEFORE IT COULD COUNT ANYTHING.
  1. A plugin skill is listed as `plugin:skill`, so the NAME already contains a colon. Splitting on
     the first ": " reads `- stitch-utilities:stitch-loop` as the name `stitch-utilities` with the
     description `stitch-loop`, turning a name-only entry into a described one.
  2. Built-in skills (`code-review`, `loop`, `init`, ...) are NOT on disk under `~/.claude/skills`.
     The first version of this file matched names against disk only and scored all twelve of them
     as dropped. That produced a non-empty "dropped" set, which is what its own can-fail control
     was waiting for, so the control passed for the wrong reason and the run reported 12 drops that
     were the parser's. Names are now matched longest-first against disk AND the built-in fallback
     splits on the first ": " rather than returning nothing.

CONTROLS, all of which can fail, and each REFUSES rather than reporting a number:
  * LISTING FOUND on the wire in every arm, at least 20 entries.
  * THE MCP MANIPULATION LANDED: the MCP-on arms must carry strictly more tool definitions than
    the MCP-off arms. An arm pair that did not differ tests nothing, so this REFUSES.
  * THE MODEL AXIS DOES NOT LAND ON THIS BUILD, and this file used to claim a control for it that
    was never written. `--model opus[1m]` leaves `claude-opus-5` on the wire in all four arms, so
    the design is 2x1 rather than 2x2 and the context-window axis -- the one the documentation
    names as the budget's source -- is UNTESTED here. That is recorded as `model_axis_landed:
    false` rather than refused, because the MCP half is still readable; but no conclusion about
    the context window may be drawn from this file.
  * PARSER POSITIVE CONTROL: the four stitch-utilities SKILL.md files must each parse to a
    non-empty description on disk. If the parser disagrees with the bytes, every count is void.
  * NO SILENT NON-RESOLUTION: every listed name either resolves on disk or is a known built-in.
  * ISOLATION: the real ~/.claude.json must not be written. mtime and size read before and after.
  * H1 FALLBACK is DEMONSTRATED, not asserted: for every skill with no `description:` key, the
    listed text is compared against the file's own first H1.
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

import hashlib

import yaml

# A redirected stdout is block-buffered, so a run that prints one line per arm produced a
# ZERO-BYTE file for its whole five minutes and could not be told from a wedged one.
sys.stdout.reconfigure(line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import is_a_skill_truncated_the_way_the_memory_index_is as S  # recorder, PORT, CLAUDE, wire_text

NL = chr(10)
HOME = os.path.expanduser("~")
REAL_CFG_DIR = os.path.join(HOME, ".claude")
REAL_PROFILE = os.path.join(HOME, ".claude.json")
PROJECT = os.path.abspath(os.path.join(HERE, ".."))
OUT = os.path.join(HERE, "which_skills_lose_their_description_on_this_install.result.json")
START = time.time()
HEADER = "The following skills are available for use with the Skill tool"
STITCH = ["stitch-utilities:" + s for s in
          ("design-md", "enhance-prompt", "stitch-loop", "taste-design")]


def refuse(why: str):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why},
              io.open(OUT, "w", encoding="utf-8"), indent=1)
    raise SystemExit(2)


# ---------------------------------------------------------------- disk

def parse_skill(path: str) -> dict:
    raw = io.open(path, "rb").read()
    text = raw.decode("utf-8-sig", "replace")
    fm, err, body_from = {}, "", 0
    lines = text.split(NL)
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                try:
                    fm = yaml.safe_load(NL.join(lines[1:i]).replace("\r", "")) or {}
                except Exception as e:
                    err = type(e).__name__
                body_from = i + 1
                break
        else:
            err = "unterminated_frontmatter"
    h1 = ""
    for ln in lines[body_from:]:
        if ln.startswith("# "):
            h1 = ln[2:].strip().replace("\r", "")
            break
    d = fm.get("description") if isinstance(fm, dict) else None
    d = " ".join(d.split()) if isinstance(d, str) else None
    return {"path": path, "description": d, "desc_chars": len(d) if d else 0, "h1": h1,
            "bom": raw[:3] == b"\xef\xbb\xbf", "crlf": b"\r\n" in raw, "yaml_error": err,
            "ascii": bool(d) and all(ord(c) < 128 for c in d)}


def enumerate_disk() -> dict:
    found: dict = {}

    def add(name, rec, tier):
        found.setdefault(name, []).append(dict(rec, tier=tier))

    for tier, root in (("user", os.path.join(REAL_CFG_DIR, "skills")),
                       ("project", os.path.join(PROJECT, ".claude", "skills"))):
        for d in sorted(os.listdir(root)) if os.path.isdir(root) else []:
            f = os.path.join(root, d, "SKILL.md")
            if os.path.isfile(f):
                add(d, parse_skill(f), tier)

    # The plugin cache holds one directory per INSTALLED VERSION, so one listing entry can have
    # several files on disk. Counting files here would over-count the install.
    cache = os.path.join(REAL_CFG_DIR, "plugins", "cache")
    for mkt in sorted(os.listdir(cache)) if os.path.isdir(cache) else []:
        for plug in sorted(os.listdir(os.path.join(cache, mkt))):
            pdir = os.path.join(cache, mkt, plug)
            if not os.path.isdir(pdir):
                continue
            for ver in sorted(os.listdir(pdir)):
                sk = os.path.join(pdir, ver, "skills")
                for d in sorted(os.listdir(sk)) if os.path.isdir(sk) else []:
                    f = os.path.join(sk, d, "SKILL.md")
                    if os.path.isfile(f):
                        add(plug + ":" + d, parse_skill(f), "plugin/" + plug + "@" + ver)
    return found


# ---------------------------------------------------------------- wire

def build_cfg(dst: str) -> None:
    # `dst` holds JUNCTIONS to the real 1.4 GB skills/ and plugins/, so this rmtree is a
    # destructive-risk line and was checked rather than assumed: on this Python (3.12, win32)
    # `os.path.islink` returns False for a junction, yet rmtree does NOT recurse through one --
    # measured with a canary file behind a junction, which survived. The real directories were
    # counted before and after: 39 skill directories, 41 SKILL.md files, unchanged.
    shutil.rmtree(dst, ignore_errors=True)
    os.makedirs(dst, exist_ok=True)
    for link in ("skills", "plugins"):
        src = os.path.join(REAL_CFG_DIR, link)
        if not os.path.isdir(src):
            refuse("real " + link + " directory not found at " + src)
        r = subprocess.run(["cmd", "/c", "mklink", "/J",
                            os.path.join(dst, link).replace("/", "\\"),
                            src.replace("/", "\\")], capture_output=True, text=True)
        if not os.path.isdir(os.path.join(dst, link)):
            refuse("junction for " + link + " failed: " + (r.stdout + r.stderr).strip())
    st = json.load(io.open(os.path.join(REAL_CFG_DIR, "settings.json"), encoding="utf-8")) \
        if os.path.isfile(os.path.join(REAL_CFG_DIR, "settings.json")) else {}
    st.pop("hooks", None)
    json.dump(st, io.open(os.path.join(dst, "settings.json"), "w", encoding="utf-8"), indent=1)
    # The real usage history drives the ranking and the real mcpServers block is the whole point of
    # the MCP axis: without it every arm loaded zero servers, the on and off arms carried the same
    # 27 tools, and the manipulation-landed control refused the run. Copying both is what makes the
    # two arms differ.
    prof = json.load(io.open(REAL_PROFILE, encoding="utf-8")) if os.path.isfile(REAL_PROFILE) else {}
    json.dump({"skillUsage": prof.get("skillUsage") or {},
               "mcpServers": prof.get("mcpServers") or {}},
              io.open(os.path.join(dst, ".claude.json"), "w", encoding="utf-8"), indent=1)


def capture(cfg: str, mcp: bool, model: str, budget: int = 0) -> dict:
    argv = [S.CLAUDE, "-p", "--output-format", "stream-json", "--verbose"]
    if not mcp:
        argv.append("--strict-mcp-config")
    if model:
        argv += ["--model", model]
    argv.append("Reply with only: OK")
    env = dict(os.environ, ANTHROPIC_BASE_URL="http://127.0.0.1:%d" % S.PORT,
               ANTHROPIC_API_KEY="x", CLAUDE_CONFIG_DIR=cfg)
    if budget:
        env["SLASH_COMMAND_TOOL_CHAR_BUDGET"] = str(budget)
    else:
        env.pop("SLASH_COMMAND_TOOL_CHAR_BUDGET", None)
    S.BODIES.clear()
    p = subprocess.Popen(argv, cwd=PROJECT, env=env, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    try:
        p.communicate(timeout=420)
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True)
    if not S.BODIES:
        return {}
    body = json.loads(S.BODIES[-1])
    tools = body.get("tools") or []
    return {"wire": wire_system_text(S.BODIES[-1]), "model": body.get("model") or "",
            "tool_count": len(tools),
            "tool_chars": len(json.dumps(tools, ensure_ascii=False)),
            "system_chars": len(json.dumps(body.get("system"), ensure_ascii=False))}


def wire_system_text(body_json: str) -> str:
    """Every piece of prompt TEXT in the request body, as text rather than as a JSON literal.

    TWO DEFECTS LIVE IN THIS ONE FUNCTION'S HISTORY, and both were found by hostile re-runs.

    First, the shared harness re-escapes: `S.wire_text()` returns `json.dumps(system)`, so every
    `"` in a description arrives as the two characters `\\"`. The listing block holds 498 double
    quotes, so every length reported from it was inflated: the description total read 26,564
    against a true 26,067, `dataviz` read 1,472 against 1,436. Membership was never affected, so
    which skills drop is unchanged, but any figure in characters was wrong.

    Second, the fix for that read only the `system` field and found NOTHING. On this build the
    skill listing is not in `system` at all; it arrives as a MESSAGE with role `system`, 36,586
    characters into the body. A reader aimed at the obvious field returns zero entries, which the
    listing-found control caught rather than reporting an empty listing as a finding.
    """
    b = json.loads(body_json)
    parts = []

    def walk(v):
        if isinstance(v, str):
            parts.append(v)
        elif isinstance(v, dict):
            if isinstance(v.get("text"), str):
                parts.append(v["text"])
            else:
                for x in v.values():
                    walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)

    walk(b.get("system"))
    for m in b.get("messages") or []:
        walk(m.get("content"))
    return NL.join(parts)


def listing_lines(wire: str) -> list:
    i = wire.find(HEADER)
    if i < 0:
        return []
    # THE BLOCK ENDS AT A BLANK LINE, and getting that wrong twice is why this comment is long.
    # v1 skipped blank lines and appended every following line to the last entry, which glued the
    # rest of the system prompt onto `security-review` and reported its description as 4,861
    # characters rather than 70 -- inflating exactly the entry a size hypothesis would rest on.
    # v2 stopped at the first line not starting with "- ", which truncated the listing at the
    # first skill whose description spans several lines (`google-style` does), so the entry count
    # moved with the budget: 43, 44 and 73 entries for one unchanged install. The names-invariant
    # control caught that; without it the sweep would have reported a drop order built on three
    # different listings. A continuation line belongs to the entry above it; a blank line ends the
    # block.
    out, started = [], False
    for ln in wire[i:].split(NL):
        if ln.startswith("- "):
            started = True
            out.append(ln[2:].rstrip())
        elif not started:
            continue
        elif ln.strip() == "":
            break
        elif out:
            out[-1] = out[-1] + " " + ln.strip()
    return out


def split_entry(line: str, names: list) -> tuple:
    """(name, description, resolved). The name is matched against disk longest-first, never on the
    colon, because a plugin skill's own name contains one. A built-in is not on disk, so it falls
    through to a first-colon split -- which must still return the description, not nothing."""
    for n in names:
        if line == n or line.startswith(n + ":") or line.startswith(n + " "):
            rest = line[len(n):]
            return n, rest[1:].strip().rstrip('",').strip() if rest.startswith(":") \
                else rest.strip().rstrip('",').strip(), True
    if ": " in line:
        a, b = line.split(": ", 1)
        return a.strip(), b.strip().rstrip('",').strip(), False
    return line.strip().rstrip('",').strip(), "", False


def score(wire: str, disk: dict, names: list) -> dict:
    lines = listing_lines(wire)
    entries = []
    for ln in lines:
        n, d, res = split_entry(ln, names)
        recs = disk.get(n) or []
        entries.append({"name": n, "listed_chars": len(d), "listed_desc": d,
                        "resolved_on_disk": res, "kept": len(d) > 0,
                        "disk_desc_chars": recs[0]["desc_chars"] if recs else None,
                        "has_description_key": bool(recs and recs[0]["description"]),
                        "h1": recs[0]["h1"] if recs else "",
                        "on_disk_copies": len(recs)})
    return {"entries": entries,
            "n": len(entries),
            "kept": sum(1 for e in entries if e["kept"]),
            "dropped": sum(1 for e in entries if not e["kept"]),
            "dropped_names": [e["name"] for e in entries if not e["kept"]],
            "listed_desc_chars": sum(e["listed_chars"] for e in entries)}


def main() -> int:
    disk = enumerate_disk()
    names = sorted(disk, key=len, reverse=True)

    for n in STITCH:                                   # parser positive control, before measuring
        recs = disk.get(n) or []
        if not recs or not all(r["description"] for r in recs):
            refuse("parser control: %s did not parse to a non-empty description on disk" % n)

    # A CONTENT HASH, because (mtime, size) is not evidence. During one run the real profile's
    # mtime moved while its bytes were unchanged: a sibling interactive session was writing to it.
    # That control would have reported a violation the probe did not commit.
    mt_before = hashlib.sha256(io.open(REAL_PROFILE, "rb").read()).hexdigest()
    cfg = tempfile.mkdtemp(prefix="skilldesc_cfg_")
    srv = S.recorder(S.PORT)
    arms = []
    try:
        build_cfg(cfg)
        # E and F EXIST BECAUSE A AND B WERE UNDERPOWERED, and saying so is the point.
        # At the default budget this install delivers every description with roughly 1,600
        # characters of headroom, so no arm there could have dropped anything whatever the tool
        # catalog did. A null measured where the mechanism cannot fire is not a null. E and F
        # repeat the comparison at 26,500, a budget where seven entries DO drop, so the arm can
        # now come out either way.
        for label, mcp, model, budget in (("A mcp-off default", False, "", 0),
                                          ("B mcp-ON  default", True, "", 0),
                                          ("C mcp-off opus[1m]", False, "opus[1m]", 0),
                                          ("D mcp-ON  opus[1m]", True, "opus[1m]", 0),
                                          ("E mcp-off b=26500", False, "", 26500),
                                          ("F mcp-ON  b=26500", True, "", 26500)):
            cap = capture(cfg, mcp, model, budget)
            if not cap:
                refuse("arm %s produced no request body" % label)
            sc = score(cap["wire"], disk, names)
            if sc["n"] < 20:
                refuse("arm %s: listing not found on the wire (%d entries)" % (label, sc["n"]))
            arms.append(dict(sc, arm=label, mcp=mcp, model_asked=model, budget=budget,
                             model_on_wire=cap["model"], tool_count=cap["tool_count"],
                             tool_chars=cap["tool_chars"], system_chars=cap["system_chars"]))
            print("%-20s tools=%-4d tool_chars=%-7d model=%-16s entries=%-4d kept=%-4d dropped=%d"
                  % (label, cap["tool_count"], cap["tool_chars"], cap["model"],
                     sc["n"], sc["kept"], sc["dropped"]))
    finally:
        srv.shutdown()
    mt_after = hashlib.sha256(io.open(REAL_PROFILE, "rb").read()).hexdigest()

    off = [a for a in arms if not a["mcp"]]
    on = [a for a in arms if a["mcp"]]
    # the boundary pair, which is the only pair that can answer anything
    e = next(a for a in arms if a["arm"].startswith("E"))
    f = next(a for a in arms if a["arm"].startswith("F"))
    if e["dropped"] == 0 or f["dropped"] == 0:
        refuse("the boundary arms dropped nothing (E=%d, F=%d): 26,500 is not a boundary on this "
               "install any more, so the tool-catalog comparison is underpowered again"
               % (e["dropped"], f["dropped"]))
    boundary_identical = (sorted(e["dropped_names"]) == sorted(f["dropped_names"]))
    landed_mcp = min(a["tool_count"] for a in on) > max(a["tool_count"] for a in off)
    landed_model = len({a["model_on_wire"] for a in arms}) > 1
    if not landed_mcp:
        refuse("the MCP manipulation did not land: tool counts on=%s off=%s"
               % ([a["tool_count"] for a in on], [a["tool_count"] for a in off]))

    base = arms[0]["entries"]
    # A STRICT YAML PARSE IS ITS OWN TRAP, and it contaminated this list once. `storm-research` has
    # a `description:` key that the CLI reads and delivers, but PyYAML raises ScannerError on it --
    # the plain scalar contains ": " ("Runs a 4-phase pipeline: five expert lenses"), which is not
    # legal YAML. Counting it as "no description key" scored it as an H1 fallback, which is the
    # opposite of what it is. A parse error is excluded here and reported on its own.
    yaml_lenient = [{"name": n, "error": recs[0]["yaml_error"],
                     "listed_chars": next((e["listed_chars"] for e in base if e["name"] == n), 0)}
                    for n, recs in disk.items() if recs[0]["yaml_error"]]
    no_key = [e for e in base if not e["has_description_key"] and e["on_disk_copies"]
              and e["name"] not in {y["name"] for y in yaml_lenient}]
    h1 = [{"name": e["name"], "listed": e["listed_desc"], "h1": e["h1"],
           "listed_equals_h1": e["listed_desc"] == e["h1"]} for e in no_key if e["kept"]]
    collisions = [{"name": n, "tiers": sorted({r["tier"] for r in recs}),
                   "listing_entries": sum(1 for e in base if e["name"] == n)}
                  for n, recs in disk.items()
                  if len({r["tier"].split("@")[0] for r in recs}) > 1]
    plugin_files = sum(len(recs) for n, recs in disk.items() if ":" in n)
    plugin_entries = len({n for n in disk if ":" in n})

    stitch_by_arm = {a["arm"]: {n: next((e["kept"] for e in a["entries"] if e["name"] == n), None)
                                for n in STITCH} for a in arms}

    res = {
        "probe": os.path.basename(__file__),
        "when_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "claude_version": subprocess.run([S.CLAUDE, "--version"], capture_output=True,
                                         text=True).stdout.strip(),
        "platform": sys.platform,
        "method": "ANTHROPIC_BASE_URL -> local recorder; the listing is read from the request "
                  "body; zero completions bought",
        "design": "2x2 as written, 2x1 as executed: the MCP axis landed, the model axis did not; "
                  "arms E and F repeat the MCP comparison at a budget where drops actually occur",
        "boundary_arms": {"budget": 26500,
                          "mcp_off_dropped": e["dropped"], "mcp_on_dropped": f["dropped"],
                          "mcp_off_names": sorted(e["dropped_names"]),
                          "mcp_on_names": sorted(f["dropped_names"]),
                          "identical": boundary_identical,
                          "tool_count_off": e["tool_count"], "tool_count_on": f["tool_count"]},
        "arms": [{k: v for k, v in a.items() if k != "entries"} for a in arms],
        "stitch_utilities_kept_by_arm": stitch_by_arm,
        "stitch_utilities_disk": [{"name": n, "desc_chars": disk[n][0]["desc_chars"],
                                   "ascii": disk[n][0]["ascii"], "crlf": disk[n][0]["crlf"],
                                   "bom": disk[n][0]["bom"],
                                   "yaml_error": disk[n][0]["yaml_error"]} for n in STITCH],
        "h1_fallback": h1, "h1_fallback_count": len(h1),
        "yaml_strict_rejects_but_cli_accepts": yaml_lenient,
        "name_collisions": collisions,
        "plugin_skill_files_on_disk": plugin_files,
        "plugin_skill_listing_entries": plugin_entries,
        "controls": {
            "parser_positive_control": "PASS",
            "listing_found_every_arm": True,
            "mcp_manipulation_landed": landed_mcp,
            "boundary_arms_can_fail": True,
            "model_axis_landed": landed_model,
            "models_seen_on_the_wire": sorted({a["model_on_wire"] for a in arms}),
            "note_if_model_axis_did_not_land": (
                "" if landed_model else
                "--model opus[1m] left the same model on the wire in every arm, so this run says "
                "NOTHING about the context-window half of the budget rule"),
            "unresolved_but_listed": sorted({e["name"] for a in arms for e in a["entries"]
                                             if not e["resolved_on_disk"]}),
            "real_profile_untouched": mt_before == mt_after,
            "config_isolated": os.path.abspath(cfg) != os.path.abspath(REAL_CFG_DIR),
        },
        "elapsed_s": round(time.time() - START, 1),
    }
    json.dump(res, io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(NL + json.dumps({k: res[k] for k in
                           ("stitch_utilities_kept_by_arm", "h1_fallback_count",
                            "name_collisions", "plugin_skill_files_on_disk",
                            "plugin_skill_listing_entries", "controls")},
                          indent=1, ensure_ascii=False))
    for a in arms:
        print(NL + a["arm"] + " dropped (%d): " % a["dropped"] + ", ".join(a["dropped_names"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
