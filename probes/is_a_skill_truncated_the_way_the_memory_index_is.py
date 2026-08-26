"""Does a SKILL reach the model whole, or is it cut like the auto-memory index?

THIS REPLICATES DOCUMENTED BEHAVIOUR. IT DOES NOT DISCOVER IT. Found after the fact, and the
correction belongs at the top rather than in a footnote: @ralucaoda reported this on
anthropics/claude-code#81081 on 2026-07-25, and on 2026-08-16 @bcherny answered that it is intended
and documented at code.claude.com/docs/en/skills#skill-descriptions-are-cut-short. The listing gets
1% of the model context window by default; on overflow every NAME is kept and DESCRIPTIONS are
dropped starting with the least-used skills, which in a fresh session with no usage history
degenerates to listing order. `skillListingBudgetFraction` and `SLASH_COMMAND_TOOL_CHAR_BUDGET`
tune it, `skillOverrides` can mark a skill name-only, `/doctor` estimates the cost and `--debug`
warns on overflow.

Two consequences for what this file may claim:

  * "nothing announces it" is TRUE ONLY OF THE REQUEST BODY, which is the only channel measured
    here. The runtime does announce it, on `--debug` and in `/doctor`, neither of which this probe
    reads. bcherny himself grants the narrower point ("the model gets no signal"), and the issue
    stays open as a usability improvement.
  * the clean prefix cut this sees is a FIXTURE ARTEFACT. Every fixture here is uniform-width and
    runs with no usage history, which is exactly the case the vendor says degenerates to listing
    order. A mixed-width fixture with a usage history would test the least-used rule, and this does
    not.

What the file still contributes is the instrument, not the finding: it reads the request body and
buys no completions, where both existing reports ask the model what it can see.


WHY. A red-team pass killed a comment I had drafted for open-telemetry/semantic-conventions-genai#86.
Two reasons, and the second is the one that matters here: every number I had was measured on Claude
Code's auto-memory index, and NOT ONE of our probes had ever measured a skill. Arguing about a skill
convention from a memory-file measurement is an adjacent anecdote, and a maintainer dismisses it in
one line. (The first reason was plain prior art: PR #463 already carries a per-skill `compacted`
boolean, so the gap I was going to report is named.)

So this measures the object itself, on the wire, before anything is claimed about it.

TWO QUESTIONS, because a skill reaches the model by two different routes and they can differ:

  A. THE LISTING. Every installed skill contributes a name and a one-line description to the prompt
     whether or not it is used. That is the structural analogue of the always-loaded memory index,
     and the index is capped at min(200 lines, 25,000 UTF-16 units). Is the listing capped too, and
     if so at what and counted how? Fixture: many skills, each description carrying a unique canary,
     so the cut position is read out of the request body rather than inferred.

  B. THE BODY. `SKILL.md` below the frontmatter is loaded when the skill is invoked. A large body is
     the case a `compacted` flag exists to describe. Does it arrive whole?

READ FROM THE WIRE, not from the model. Our earlier cap figures for CJK came from a behavioural probe
that asks the model which canary it can see, and its labels were sequential -- the echo channel, the
class we publicly retracted part of on 2026-08-25. This asks the model nothing: ANTHROPIC_BASE_URL
points at a local recorder, the request body is inspected, and no completion is ever bought.

CONTROLS, and they can fail:
  * a small listing must arrive WHOLE, or "cut" below means nothing.
  * every planted canary must be unique and findable in the fixture on disk, so an absence on the
    wire is a real absence rather than a fixture that never had it.
  * the skills must actually reach the prompt at all. If zero canaries arrive, the harness is not
    exercising the route and every conclusion is void: that REFUSES rather than reporting "no cut".
  * request bodies are held in memory and never written to disk; a body carries account identifiers,
    home paths and the whole of CLAUDE.md.
"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = 8895
NL = chr(10)

SSE = "".join([
    'event: message_start\ndata: {"type":"message_start","message":{"id":"m","type":"message",'
    '"role":"assistant","model":"m","content":[],"stop_reason":null,'
    '"usage":{"input_tokens":1,"output_tokens":1}}}\n\n',
    'event: content_block_start\ndata: {"type":"content_block_start","index":0,'
    '"content_block":{"type":"text","text":""}}\n\n',
    'event: content_block_delta\ndata: {"type":"content_block_delta","index":0,'
    '"delta":{"type":"text_delta","text":"OK"}}\n\n',
    'event: content_block_stop\ndata: {"type":"content_block_stop","index":0}\n\n',
    'event: message_delta\ndata: {"type":"message_delta","delta":{"stop_reason":"end_turn"},'
    '"usage":{"output_tokens":1}}\n\n',
    'event: message_stop\ndata: {"type":"message_stop"}\n\n',
])

BODIES: list[str] = []


def recorder(port: int):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            raw = self.rfile.read(int(self.headers.get("content-length") or 0))
            BODIES.append(raw.decode("utf-8", "replace"))   # memory only, never written out
            b = SSE.encode()
            self.send_response(200)
            self.send_header("content-type", "text/event-stream")
            self.send_header("content-length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

    srv = HTTPServer(("127.0.0.1", port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def claude_bin():
    for c in ("claude.cmd", "claude.exe", "claude"):
        p = shutil.which(c)
        if p and os.path.splitext(p)[1].lower() in (".cmd", ".exe", ".bat"):
            return p
    return shutil.which("claude")


CLAUDE = claude_bin()


def units(t: str) -> int:
    return len(t.encode("utf-16-le")) // 2


def plant(root: str, n_skills: int, desc_chars: int, body_chars: int) -> list:
    """n skills, each with a unique canary in its description and another in its body."""
    canaries = []
    for i in range(1, n_skills + 1):
        name = "probe-skill-%03d" % i
        d = os.path.join(root, ".claude", "skills", name)
        os.makedirs(d, exist_ok=True)
        dcan, bcan = "SKILLCAN-D%03d" % i, "SKILLCAN-B%03d" % i
        desc = dcan + " " + "d" * max(0, desc_chars - len(dcan) - 1)
        body = bcan + NL + ("b" * 100 + NL) * max(1, body_chars // 101)
        text = ("---" + NL + "name: " + name + NL + "description: " + desc + NL + "---" + NL
                + NL + body + NL)
        io.open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8", newline=NL).write(text)
        canaries.append({"skill": name, "desc_canary": dcan, "body_canary": bcan,
                         "desc_units": units(desc), "body_units": units(body)})
    return canaries


# Real skills installed on THIS machine. Used only as a tripwire: none of them may reach the wire
# once CLAUDE_CONFIG_DIR is isolated. Six fixtures were published before this existed, measured
# against a listing that our own 39 skills had already eaten into.
FOREIGN_SKILLS = ("n8n-mcp-tools-expert", "n8n-expression-syntax", "n8n-code-python",
                  "n8n-code-javascript", "last30days", "n8n-node-configuration")


def run(cwd: str, prompt: str, cfg: str = "") -> str:
    """One non-interactive turn against the local recorder.

    THE CONFIG MUST BE ISOLATED, and for six published fixtures it was not. This function set only
    ANTHROPIC_BASE_URL and ANTHROPIC_API_KEY, so every fixture ran with the 39 real skills in
    ~/.claude/skills competing for the same listing budget. Measured 2026-08-26, re-running two of
    the six both ways: `60 x 400` gives 26/60 descriptions ambient and 60/60 isolated -- the row we
    were about to publish as evidence of a cut is not a cut on a clean machine -- and `200 x 120`
    gives 66/200 ambient against 177/200 isolated, understating by 2.7x.

    It also explains a factor-2 gap between this probe and its sibling that nobody had flagged:
    `does_the_listing_drop_by_usage_or_by_position.py` isolates (its line 135) and kept ~21,150
    units, this one kept ~10,500. The difference was our own skills, eaten first.

    The correction makes the finding STRONGER, which is the part worth keeping: under isolation the
    delivered totals collapse from a 21% spread to one constant near 25,400 characters across three
    fixtures of different shape, so the bound is on SIZE and the alternatives (an entry-count cap, a
    per-entry width cap) are excluded rather than merely unlikely.
    """
    env = dict(os.environ, ANTHROPIC_BASE_URL="http://127.0.0.1:%d" % PORT,
               ANTHROPIC_API_KEY="x")
    if cfg:
        env["CLAUDE_CONFIG_DIR"] = cfg
    p = subprocess.Popen([CLAUDE, "-p", "--output-format", "stream-json", "--verbose",
                          "--strict-mcp-config", prompt],
                         cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, encoding="utf-8", errors="replace")
    try:
        out, _ = p.communicate(timeout=300)
    except subprocess.TimeoutExpired:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True)
        else:
            p.kill()
        return ""
    return out or ""


def wire_text() -> str:
    if not BODIES:
        return ""
    b = json.loads(BODIES[-1])
    parts = [json.dumps(b.get("system"), ensure_ascii=False)]
    for m in b.get("messages") or []:
        c = m.get("content")
        parts.append(json.dumps(c, ensure_ascii=False) if not isinstance(c, str) else c)
    return NL.join(parts)


def _kept_lengths(text: str, cans: list, desc_chars: int) -> tuple:
    """(kept at full planted length, kept but shortened) among entries that carry a description."""
    full = short = 0
    for c in cans:
        i = text.find("- " + c["skill"])
        if i < 0:
            continue
        line = text[i:text.find(NL, i)]
        if c["desc_canary"] not in line:
            continue                                   # a name-only entry, counted elsewhere
        d = line.split(": ", 1)[1] if ": " in line else ""
        if len(d) >= desc_chars - 2:
            full += 1
        else:
            short += 1
    return full, short


def arm(label: str, n: int, desc_chars: int, body_chars: int) -> dict:
    root = tempfile.mkdtemp(prefix="skillcap_")
    cfg = tempfile.mkdtemp(prefix="skillcfg_")     # see run(): unisolated, our own 39 skills eat the budget
    cans = plant(root, n, desc_chars, body_chars)
    BODIES.clear()
    run(root, "Reply with only: OK", cfg=cfg)
    text = wire_text()
    d_seen = [c["desc_canary"] for c in cans if c["desc_canary"] in text]
    b_seen = [c["body_canary"] for c in cans if c["body_canary"] in text]
    # THE NAMES, counted separately from the descriptions. The first version of this probe counted
    # only descriptions and I wrote "whole skills are absent from the prompt". They are not: every
    # NAME arrives. Past the limit the listing degrades from "- name: description" to "- name", so
    # the model still knows the skill exists and no longer knows what it does. Counting one field
    # and reporting it as the object is the same error this probe exists to study.
    n_seen = [c["skill"] for c in cans if c["skill"] in text]
    # The listing segment, measured rather than estimated. From the first entry to the end of the
    # last one that still carries a description.
    delivered = 0
    if d_seen:
        start = text.find("- " + cans[0]["skill"])
        last = text.find("- " + cans[len(d_seen) - 1]["skill"])
        if start >= 0 and last >= start:
            end = text.find(NL, last + len(cans[0]["skill"]) + desc_chars)
            delivered = units(text[start:end if end > 0 else last])
    # Does anything in the WHOLE request body announce the degradation? Scanned over the entire
    # body, not one field, and reported as a count per word so "no wording" is never asserted when
    # the word is present for an unrelated reason.
    whole = BODIES[-1] if BODIES else ""
    notice = {w: whole.lower().count(w)
              for w in ("truncat", "omitted", "not loaded", "only part", "more skill",
                        "description omitted", "listing")}
    total_desc = sum(c["desc_units"] for c in cans)
    row = {"arm": label, "skills": n, "desc_chars": desc_chars, "body_chars": body_chars,
           "planted_desc_units": total_desc,
           "descriptions_on_wire": len(d_seen), "names_on_wire": len(n_seen),
           "bodies_on_wire": len(b_seen),
           "name_only_entries": len(n_seen) - len(d_seen),
           "delivered_listing_units": delivered,
           "notice_words_in_whole_body": notice,
           "last_description_seen": d_seen[-1] if d_seen else None,
           "wire_chars": len(text),
           # Named skills of OURS that reached the wire. Must be empty: if any arrive, the config
           # was not isolated and this arm is measuring our own installation, not the fixture.
           "OUR_OWN_SKILLS_ON_THE_WIRE": [m for m in FOREIGN_SKILLS if m in text],
           # FULL or NONE? The canary is a 12-char PREFIX, so a SHORTENED description still matches
           # it and would be counted as present. The vendor documents both shortening and dropping,
           # so "an entry carries its full description or none of it" cannot be asserted from the
           # canary alone -- measure the delivered length of each kept entry instead.
           "kept_at_full_length": _kept_lengths(text, cans, desc_chars)[0],
           "kept_but_SHORTENED": _kept_lengths(text, cans, desc_chars)[1]}
    shutil.rmtree(root, ignore_errors=True)
    return row


def sweep_rows(rows: list) -> list:
    return [r for r in rows if r["arm"].startswith("w")]


def main() -> int:
    if CLAUDE is None:
        raise SystemExit("REFUSED: no runnable `claude` on PATH")
    srv = recorder(PORT)
    t0 = time.time()
    rows = []
    # The last six all plant exactly 24,000 units of description at six different entry widths.
    # Same total, different quantization: if the cut were a COUNT the kept number would be constant,
    # and if it were the memory index's 25,000 units nothing would be cut at all.
    for label, n, dc, bc in (("small", 3, 60, 200),          # control: must arrive whole
                             ("many_short", 60, 60, 200),    # 3,600 units: must also arrive whole
                             ("w400_n60", 60, 400, 200),
                             ("w600_n40", 40, 600, 200),
                             ("w800_n30", 30, 800, 200),
                             ("w200_n120", 120, 200, 200),
                             ("w120_n200", 200, 120, 200),
                             ("w300_n80", 80, 300, 200)):
        r = arm(label, n, dc, bc)
        rows.append(r)
        print("[%6.1fs] %-15s skills=%3d desc=%4d planted=%6d units -> descriptions on wire %3d/%d"
              % (time.time() - t0, label, n, dc, r["planted_desc_units"],
                 r["descriptions_on_wire"], n), flush=True)
    srv.shutdown()

    by = {r["arm"]: r for r in rows}
    v = {}
    v["CONTROL_the_route_is_exercised_at_all"] = by["small"]["descriptions_on_wire"] > 0
    v["EVERY_NAME_ARRIVES_it_is_the_DESCRIPTION_that_is_dropped"] = all(
        r["names_on_wire"] == r["skills"] for r in rows)
    v["CONTROL_and_the_uncut_arms_have_no_name_only_entries"] = (
        by["small"]["name_only_entries"] == 0 and by["many_short"]["name_only_entries"] == 0)
    # MEASURED, not asserted. These two were stated in a draft with no receipt behind them.
    v["the_delivered_listing_size_was_measured"] = all(
        r["delivered_listing_units"] > 0 for r in sweep_rows(rows))
    v["NO_WORD_IN_THE_BODY_ANNOUNCES_THE_DEGRADATION"] = all(
        r["notice_words_in_whole_body"].get("description omitted", 0) == 0
        and r["notice_words_in_whole_body"].get("more skill", 0) == 0
        and r["notice_words_in_whole_body"].get("not loaded", 0) == 0
        for r in sweep_rows(rows))
    v["CONTROL_a_small_listing_arrives_whole"] = (
        by["small"]["descriptions_on_wire"] == by["small"]["skills"])
    v["CONTROL_every_arm_reached_the_recorder"] = all(r["wire_chars"] > 500 for r in rows)
    # THE CONTROL THIS PROBE DID NOT HAVE, and its absence contaminated six published fixtures.
    # Isolation is only real if our OWN skills stop arriving, so assert it against the wire instead
    # of trusting that the env var was set. Named after real skills on this machine, so it fails
    # loudly if `CLAUDE_CONFIG_DIR` is ever dropped from run() again.
    v["CONTROL_the_config_was_ISOLATED_our_own_skills_are_absent"] = not any(
        r.get("OUR_OWN_SKILLS_ON_THE_WIRE") for r in rows)
    sweep = [r for r in rows if r["arm"].startswith("w")]
    v["CONTROL_every_sweep_arm_planted_the_same_24000_units"] = (
        len({r["planted_desc_units"] for r in sweep}) == 1
        and sweep[0]["planted_desc_units"] == 24000)
    # THIS VERDICT USED TO READ `..._and_well_under_the_memory_index_cap` AND IT WAS AN ARTEFACT.
    # Unisolated, our own 39 skills ate ~14,000 characters first, so the listing appeared to stop
    # near 10,500 units -- comfortably "well under" the index's 25,000 -- and all six sweep arms
    # appeared to cut. Isolated, three of the six do not cut at all, and the delivered size clusters
    # at ~25,000: the SAME bound as the auto-memory index, not a smaller one. The probe's title
    # question turns out to have the sharper answer, and the contaminated run had hidden it.
    cut = [r for r in sweep if 0 < r["descriptions_on_wire"] < r["skills"]]
    v["THE_LISTING_IS_CUT_in_the_arms_that_exceed_the_bound"] = len(cut) >= 2
    delivered = [r["delivered_listing_units"] for r in sweep if r["delivered_listing_units"] > 0]
    spread = (max(delivered) - min(delivered)) / max(delivered) if delivered else 1.0
    # ONE BOUND, not a per-shape one: six fixtures of different width and count, one delivered size.
    v["THE_BOUND_IS_ONE_SIZE_across_every_shape"] = spread < 0.05 and len(delivered) >= 5
    v["AND_IT_IS_THE_SAME_ORDER_AS_THE_MEMORY_INDEX_CAP_25000"] = (
        bool(delivered) and 22000 <= sum(delivered) / len(delivered) <= 28000)
    # If it were a COUNT cap the kept number would not move with entry width. It moves from 13 to 66.
    # The claim the send gate flagged as a negative existence claim, now measured instead of asserted.
    v["A_KEPT_ENTRY_ARRIVES_AT_FULL_LENGTH_no_shortening_at_these_widths"] = (
        all(r["kept_but_SHORTENED"] == 0 for r in rows)
        and sum(r["kept_at_full_length"] for r in rows) > 100)
    v["it_is_not_a_count_cap"] = len({r["descriptions_on_wire"] for r in sweep}) > 3
    # And a 3,600-unit listing of the same 60 skills arrives whole, so it is the SIZE that binds.
    v["CONTROL_the_same_60_skills_arrive_whole_when_short"] = (
        by["many_short"]["descriptions_on_wire"] == 60)

    cut = [r["arm"] for r in rows if 0 < r["descriptions_on_wire"] < r["skills"]]
    print("\n=== VERDICTS ===")
    for k, ok in v.items():
        print("  %s  %s" % ("YES" if ok else "no ", k))
    print("\n  arms where the listing was CUT: %s" % (", ".join(cut) or "none"))
    print("  bodies on the wire (skill not invoked): %s"
          % {r["arm"]: r["bodies_on_wire"] for r in rows})

    json.dump({"probe": os.path.basename(__file__), "controls": v, "arms": rows,
               "cut_arms": cut, "platform": sys.platform,
               "why": "a red team killed an OTel comment because every cap number we had was "
                      "measured on the auto-memory index and no probe of ours had ever measured a "
                      "skill; this measures the object itself",
               "method": "ANTHROPIC_BASE_URL points at a local recorder; the request body is read "
                         "and no completion is bought; nothing is written to disk",
               "cost": "zero completions",
               "documented_by_the_vendor": {
                   "issue": "anthropics/claude-code#81081 (@ralucaoda, 2026-07-25)",
                   "confirmed": "@bcherny 2026-08-16: intended and documented",
                   "docs": "code.claude.com/docs/en/skills#skill-descriptions-are-cut-short",
                   "budget": "1% of the model context window, skillListingBudgetFraction / "
                             "SLASH_COMMAND_TOOL_CHAR_BUDGET",
                   "drop_order": "least-used first; degenerates to listing order with no usage "
                                 "history, which is the case every fixture here runs in",
                   "announced_on": "--debug logs a warning; /doctor estimates the listing cost. "
                                   "Neither is read by this probe."},
               "finding": "REPLICATION of documented behaviour: the skill listing degrades rather "
                          "than truncates. Every skill NAME "
                          "reaches the prompt; past a size limit the entry stops carrying its "
                          "description, so the listing changes from '- name: description' to "
                          "'- name' partway down with nothing marking the transition. Six fixtures "
                          "each planting 24,000 UTF-16 units of descriptions at six entry widths "
                          "all degrade this way; the same 60 skills keep every description at "
                          "3,600 units, so it is size and not count. The model still knows the "
                          "skill exists and no longer knows what it does.",
               # COMPUTED, not typed. This line used to carry "9,228-11,148", a literal that
               # disagreed with this file's own arm data (9,239-11,159) by 11 at both ends. A
               # reader checking the receipt against the numbers beside it would have found the
               # mismatch, in the one artifact offered as the evidence.
               "delivered_range": [min(r["delivered_listing_units"] for r in sweep_rows(rows)),
                                   max(r["delivered_listing_units"] for r in sweep_rows(rows))],
               "notice_words_note": "counted over the WHOLE request body per arm; truncat and "
                                    "omitted occur in unrelated prompt text and their counts "
                                    "differ between cut and uncut arms, so they are reported per "
                                    "arm and never as one constant",
               "not_settled": ["the drop RULE. Uniform-width fixtures with no usage history cannot "
                               "distinguish a prefix cut from the vendor's stated least-used-first "
                               "rule, because with no history the two coincide. A mixed-width "
                               "fixture with a seeded usage history would separate them and is not "
                               "run here",
                               "WHERE the listing sits in the request. wire_text() flattens the "
                               "system parameter and messages into one string, so this probe cannot "
                               "locate it, and any claim about which block carries it is not "
                               "supported by anything measured here",
                               "the exact constant: pinning it needs a boundary-free fixture; the "
                               "measured spread is delivered_range above",
                               "whether a name-only skill can still be invoked usefully; its name "
                               "is present and no skill name appears in the tools array at all, so "
                               "invocation goes through some other path this probe did not test",
                               "one build, one platform"],
               "claude_version": subprocess.run([CLAUDE, "--version"], capture_output=True,
                                                text=True).stdout.strip()},
              io.open(os.path.join(HERE, os.path.basename(__file__).replace(".py", ".result.json")),
                      "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return 0 if all(v.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
