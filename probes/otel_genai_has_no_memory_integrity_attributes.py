"""Does the OpenTelemetry GenAI semantic-convention work define memory INTEGRITY attributes?

The claim we would put in front of a standards body, so it has to be measured against the
AUTHORITATIVE files, not against the text of one proposal. Measured 2026-08-08.

Checked, in order of authority:
  1. `semantic-conventions-genai` registry -- the attribute list itself
  2. its gen-ai docs (spans, events, metrics, agent spans)
  3. `semantic-conventions/docs/gen-ai` -- the older, stable home
  4. issue #35, the live proposal that names memory as a first-class concept

`memory` appears throughout. The question is whether anything says whether a recalled value is
CURRENT, where it CAME FROM, or whether it was ERASED -- the lifecycle, not the read.

Downloads over raw.githubusercontent (no API quota). Prints MEASURED:/VERDICT:.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAW = "https://raw.githubusercontent.com"
SOURCES = [
    ("registry/gen-ai", f"{RAW}/open-telemetry/semantic-conventions-genai/main/docs/registry/attributes/gen-ai.md"),
    ("genai/gen-ai-spans", f"{RAW}/open-telemetry/semantic-conventions-genai/main/docs/gen-ai/gen-ai-spans.md"),
    ("genai/gen-ai-events", f"{RAW}/open-telemetry/semantic-conventions-genai/main/docs/gen-ai/gen-ai-events.md"),
    ("genai/gen-ai-metrics", f"{RAW}/open-telemetry/semantic-conventions-genai/main/docs/gen-ai/gen-ai-metrics.md"),
    ("semconv/gen-ai-agent-spans", f"{RAW}/open-telemetry/semantic-conventions/main/docs/gen-ai/gen-ai-agent-spans.md"),
    ("semconv/gen-ai-spans", f"{RAW}/open-telemetry/semantic-conventions/main/docs/gen-ai/gen-ai-spans.md"),
]

#: The lifecycle vocabulary. If a standard means to describe memory INTEGRITY, at least one of these
#: has to appear somewhere -- these are the plain English words for the ideas, not our jargon.
INTEGRITY = ("supersed", "provenance", "erasure", "erase", "forget", "retention", "integrity",
             "audit", "stale", "outdated", "revert", "rollback", "tombstone", "correction")


def get(url: str) -> str:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "agora-probe"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        print("MEASURED: could not fetch %s (%s)" % (url, str(e)[:60]))
        return ""


def main() -> int:
    fetched, total_chars = [], 0
    mem_total = 0
    integrity_hits: dict[str, int] = {}
    attr_names: set[str] = set()

    for name, url in SOURCES:
        t = get(url)
        if not t:
            continue
        fetched.append(name)
        total_chars += len(t)
        mem_total += len(re.findall(r"memory", t, re.I))
        for w in INTEGRITY:
            n = len(re.findall(w, t, re.I))
            if n:
                integrity_hits[w] = integrity_hits.get(w, 0) + n
        attr_names |= {m.lower() for m in
                       re.findall(r"`(gen_ai\.[a-z0-9_.]+)`", t, re.I)}

    if len(fetched) < 3:
        print("MEASURED: only %d of %d sources fetched" % (len(fetched), len(SOURCES)))
        print("VERDICT: NOT_COMPUTABLE")
        return 0

    mem_attrs = sorted(a for a in attr_names if "memory" in a)
    print("MEASURED: read %d authoritative files, %d chars: %s"
          % (len(fetched), total_chars, ", ".join(fetched)))
    print("MEASURED: 'memory' appears %d times across them" % mem_total)
    print("MEASURED: distinct gen_ai.* attributes found: %d, of which naming memory: %d %s"
          % (len(attr_names), len(mem_attrs), mem_attrs or ""))
    print("MEASURED: memory-INTEGRITY vocabulary hits: %s"
          % (integrity_hits or "NONE of %s" % (", ".join(INTEGRITY))))

    # The control: the probe must be able to FIND these words when they are present.
    control = "A superseded value has provenance; erasure leaves a tombstone and an audit record."
    found = [w for w in INTEGRITY if re.search(w, control, re.I)]
    print("MEASURED: positive control -- the same scan finds %d/%d terms in a sentence that "
          "contains them" % (len(found), 5))
    if len(found) < 5:
        print("VERDICT: NOT_COMPUTABLE -- the scanner cannot see its own target")
        return 0

    if not integrity_hits:
        print("VERDICT: REPRODUCED -- the GenAI conventions describe memory as a thing to trace "
              "(%d mentions) and define NO attribute for whether a recalled value is current, "
              "where it came from, or whether it was erased" % mem_total)
    else:
        print("VERDICT: FAILED -- integrity vocabulary IS present (%s); the gap claim must be "
              "narrowed or dropped" % integrity_hits)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
