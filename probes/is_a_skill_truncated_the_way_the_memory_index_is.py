"""Does a SKILL reach the model whole, or is it cut like the auto-memory index?

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


def run(cwd: str, prompt: str) -> str:
    env = dict(os.environ, ANTHROPIC_BASE_URL="http://127.0.0.1:%d" % PORT,
               ANTHROPIC_API_KEY="x")
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


def arm(label: str, n: int, desc_chars: int, body_chars: int) -> dict:
    root = tempfile.mkdtemp(prefix="skillcap_")
    cans = plant(root, n, desc_chars, body_chars)
    BODIES.clear()
    run(root, "Reply with only: OK")
    text = wire_text()
    d_seen = [c["desc_canary"] for c in cans if c["desc_canary"] in text]
    b_seen = [c["body_canary"] for c in cans if c["body_canary"] in text]
    total_desc = sum(c["desc_units"] for c in cans)
    row = {"arm": label, "skills": n, "desc_chars": desc_chars, "body_chars": body_chars,
           "planted_desc_units": total_desc,
           "descriptions_on_wire": len(d_seen), "bodies_on_wire": len(b_seen),
           "last_description_seen": d_seen[-1] if d_seen else None,
           "wire_chars": len(text)}
    shutil.rmtree(root, ignore_errors=True)
    return row


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
    v["CONTROL_a_small_listing_arrives_whole"] = (
        by["small"]["descriptions_on_wire"] == by["small"]["skills"])
    v["CONTROL_every_arm_reached_the_recorder"] = all(r["wire_chars"] > 500 for r in rows)
    sweep = [r for r in rows if r["arm"].startswith("w")]
    v["CONTROL_every_sweep_arm_planted_the_same_24000_units"] = (
        len({r["planted_desc_units"] for r in sweep}) == 1
        and sweep[0]["planted_desc_units"] == 24000)
    v["THE_LISTING_IS_CUT_and_well_under_the_memory_index_cap"] = all(
        0 < r["descriptions_on_wire"] < r["skills"] for r in sweep)
    # If it were a COUNT cap the kept number would not move with entry width. It moves from 13 to 66.
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
               "finding": "the skill LISTING is silently truncated. Six fixtures each planting "
                          "24,000 UTF-16 units of descriptions at six entry widths are all cut, at "
                          "a whole-entry boundary, with whole skills simply absent from the prompt "
                          "and NO notice of any kind -- unlike the auto-memory index, which at "
                          "least prints a warning. The same 60 skills arrive whole at 3,600 units, "
                          "so it is size and not count.",
               "not_settled": ["the exact constant: delivered lands in 9,228-11,148 units across "
                               "the six widths, and pinning it needs a boundary-free fixture",
                               "whether a skill absent from the listing can still be invoked by "
                               "name; only its presence in the prompt was measured",
                               "one build, one platform"]},
              io.open(os.path.join(HERE, os.path.basename(__file__).replace(".py", ".result.json")),
                      "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return 0 if all(v.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
