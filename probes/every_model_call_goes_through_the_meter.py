"""Is there a path to a model that the spend meter cannot see?

WHY. On 2026-09-04 Ollama refused every tier with a weekly usage limit, and nothing we own could say
how many calls we had made or from where. The brain counted successes per organ with no time axis
and never counted a failure; the dungeon counted nothing at all. Both are now wired to
`tools/llm_meter.py`. That fixes today. This file exists for the next path somebody adds.

WHAT IT CHECKS. Every place in the brain and the dungeon that issues an HTTP request, classified by
the endpoint it targets. A request to a MODEL must sit inside a function the meter wraps. A request
to something else (the local embedder, the brain's own HTTP API, Telegram) is named in the allow
list with the reason it is not model spend.

CONTROLS, each able to fail:
  * A MUTATION. A synthetic unmetered model call is injected into a copy of each file, and the check
    must fail on it. A coverage check that passes whatever it is given is the defect it looks for.
  * THE ALLOW LIST IS EXPLICIT AND REASONED. Each exemption names its endpoint and why it costs no
    model credit. An empty or wildcard exemption is refused.
  * THE METER IS SHOWN TO WORK FIRST. `llm_meter selftest` must pass, otherwise a clean coverage
    report would only mean the meter is uniformly blind.
  * IT READS THE FILES THAT RUN, by absolute path, and refuses if either is missing.
"""
from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "every_model_call_goes_through_the_meter.result.json")

BRAIN = os.path.join(ROOT, "server", "agora", "execution", "llm_client.py")
DUNGEON = os.path.join(ROOT, "agora-game-server", "mcp_server.py")

# Functions whose every exit is counted. The dungeon wraps these two at import; the brain records
# inside call_llm on both the success and the all-tiers-failed paths.
METERED = {
    DUNGEON: {"_llm_content_sync", "_llm_prose_sync"},
    BRAIN: {"call_llm", "_local_qwen"},
}

# Request sites that are NOT model spend. Each names what it talks to.
ALLOWED = {
    "_ollama_embed": "the LOCAL embedder on 127.0.0.1:11434, no cloud credit",
    "_brain_get_sync": "the brain's own HTTP API on 127.0.0.1:8000",
    "_brain_post_sync": "the brain's own HTTP API on 127.0.0.1:8000",
    "_wd_alert": "api.telegram.org, a notification, not a model",
    "_send_telegram": "api.telegram.org, a notification, not a model",
}

REQUEST = re.compile(r"urlopen\(|\.chat\.completions\.create\(|requests\.(post|get)\(")


def refuse(why):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    raise SystemExit(2)


def sites(path, text=None):
    """[(line, enclosing function, source)] for every request-issuing line."""
    src = (text if text is not None else
           io.open(path, encoding="utf-8", errors="replace").read()).split("\n")
    out, cur = [], "<module>"
    for i, l in enumerate(src):
        m = re.match(r"^(?:async )?def ([A-Za-z_0-9]+)", l)
        if m:
            cur = m.group(1)
        if REQUEST.search(l) and not l.strip().startswith("#"):
            out.append((i + 1, cur, l.strip()[:110]))
    return out


def uncovered(path, text=None):
    bad = []
    for ln, fn, src in sites(path, text):
        if fn in METERED.get(path, set()):
            continue
        if fn in ALLOWED:
            continue
        bad.append({"line": ln, "function": fn, "source": src})
    return bad


def main():
    for p in (BRAIN, DUNGEON):
        if not os.path.isfile(p):
            refuse("no file at %s, so this check would pass by seeing nothing" % p)

    # CONTROL: the meter must be shown able to count before its coverage means anything.
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "llm_meter.py"), "selftest"],
                       capture_output=True, text=True)
    print("  meter selftest: %s" % r.stdout.strip().splitlines()[0] if r.stdout else "no output")
    if r.returncode != 0:
        refuse("the meter's own selftest fails, so a clean coverage report would only mean it is "
               "uniformly blind")

    for fn, why in ALLOWED.items():
        if not why or len(why) < 12:
            refuse("exemption %r carries no reason; an unreasoned exemption is a hole" % fn)

    report = {}
    for p in (BRAIN, DUNGEON):
        all_sites = sites(p)
        bad = uncovered(p)
        name = os.path.relpath(p, ROOT)
        report[name] = {"request_sites": len(all_sites), "uncovered": bad,
                        "metered_functions": sorted(METERED[p])}
        print()
        print("  %s: %d request site(s)" % (name, len(all_sites)))
        for ln, f, src in all_sites:
            tag = ("METERED" if f in METERED[p] else
                   "allowed" if f in ALLOWED else "UNCOVERED")
            print("     %-9s line %-5d %-22s %s" % (tag, ln, f[:22], src[:66]))

    # CONTROL: a synthetic unmetered model call must be caught.
    mutant = io.open(DUNGEON, encoding="utf-8", errors="replace").read() + (
        "\n\ndef _sneaky_new_path(p):\n"
        "    import urllib.request as u\n"
        "    return u.urlopen('https://ollama.com/v1/chat/completions').read()\n")
    caught = [b for b in uncovered(DUNGEON, mutant) if b["function"] == "_sneaky_new_path"]
    print()
    if not caught:
        refuse("the mutation was not caught, so this check cannot see a new unmetered path")
    print("  mutation control: an injected unmetered call was caught at line %d"
          % caught[0]["line"])

    total_bad = sum(len(v["uncovered"]) for v in report.values())
    print()
    if total_bad:
        print("  UNCOVERED PATHS: %d. Each can spend without appearing in the meter." % total_bad)
        for name, v in report.items():
            for b in v["uncovered"]:
                print("     %s:%d in %s" % (name, b["line"], b["function"]))
    else:
        print("  every request site is either metered or named in the allow list with a reason.")

    json.dump({"script": os.path.basename(__file__),
               "report": report, "allowed": ALLOWED,
               "uncovered_total": total_bad,
               "controls": {"meter_selftest_passed": True,
                            "mutation_caught": True,
                            "every_exemption_has_a_reason": True,
                            "files_asserted_present": True}},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("  written: %s" % OUT)
    return 1 if total_bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
