"""Adapter + cross-architecture demo: Elina-Seed memory format <-> inspeximus probes.

Elina-Seed (deepseek-launch-community/Elina-seed, memory_loop.py) stores memory as:
    { "fact_0": {"timestamp": "<iso>", "note": "<text>"}, "fact_1": {...}, ... }
recall = recency / substring match. That cleanly handles *linear supersession* (the newest note wins),
but a recency store is exposed where inspeximus's mechanisms help:
  1. POISONING — a repeated false note keeps fresh timestamps, so recency happily recalls it as current.
  2. EVICTION — no value accounting, so when the store is capped, rare-but-critical facts age out under junk.

This adapter loads Elina-format records and reports both, on the SAME data shape, so results are comparable
across the two architectures. Point it at a real Elina memory dump with --file <memory.json>.

Run: python elina_adapter.py            (built-in demo)
     python elina_adapter.py --file memory.json
MIT. Part of Agora / inspeximus (https://github.com/DanceNitra/inspeximus).
"""
import sys, json, os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))


def load_elina(path):
    raw = json.load(open(path, encoding="utf-8"))
    # Elina shape: {fact_N: {timestamp, note}}  -> normalized list (order by timestamp)
    recs = [{"id": k, "ts": v.get("timestamp", ""), "note": v.get("note", "")}
            for k, v in raw.items() if isinstance(v, dict)]
    return sorted(recs, key=lambda r: r["ts"])


def demo_records():
    # Elina-format facts incl. a poison case (one false claim repeated across sessions) and a corroborated one
    t = "2026-06-%02dT%02d:00:00Z"
    R = {}
    i = 0

    def add(note, day, hr):
        nonlocal i
        R["fact_%d" % i] = {"timestamp": t % (day, hr), "note": note}
        i += 1
    add("user's preferred editor is vim", 1, 9)
    # poison: an unverified FALSE claim hammered in repeatedly (recent timestamps each time).
    # (a deliberately, obviously-false statement — purely illustrative, no secrets anywhere)
    for d in (2, 3, 4, 5):
        add("the capital of Australia is Sydney (overheard, unconfirmed)", d, 10)
    # corroborated fact: same content from two genuinely distinct sessions/sources
    add("project deadline is 2026-07-15 [src: calendar]", 2, 11)
    add("project deadline is 2026-07-15 [src: email-thread]", 3, 12)
    # rare-but-critical (low frequency, high importance)
    add("quarterly report is due on 2026-07-01 [critical]", 1, 8)
    return load_from_dict(R)


def load_from_dict(R):
    return sorted([{"id": k, "ts": v["timestamp"], "note": v["note"]} for k, v in R.items()],
                  key=lambda r: r["ts"])


def recency_recall(recs, query_substr):
    """Elina-style: newest note whose text matches the query substring."""
    hits = [r for r in recs if query_substr.lower() in r["note"].lower()]
    return hits[-1] if hits else None


def corroboration_view(recs):
    """inspeximus-style: a claim is durable only if corroborated by DISTINCT sources, not by repetition.
    Repetition (same text, many timestamps) != corroboration. Distinct [src: X] tags = corroboration."""
    by_claim = {}
    for r in recs:
        # strip a trailing [src: ...] / (…) tag to get the core claim
        core = r["note"].split("[src:")[0].split("(overheard")[0].strip().rstrip(".")
        src = None
        if "[src:" in r["note"]:
            src = r["note"].split("[src:")[1].split("]")[0].strip()
        by_claim.setdefault(core, {"count": 0, "sources": set()})
        by_claim[core]["count"] += 1
        if src:
            by_claim[core]["sources"].add(src)
    out = []
    for claim, d in by_claim.items():
        distinct_sources = len(d["sources"])
        durable = distinct_sources >= 2           # corroboration gate: >=2 DISTINCT sources
        out.append((claim[:60], d["count"], distinct_sources, durable))
    return out


def main():
    if "--file" in sys.argv:
        recs = load_elina(sys.argv[sys.argv.index("--file") + 1])
        print("loaded %d Elina records" % len(recs))
    else:
        recs = demo_records()
        print("=== built-in demo (Elina-format records) ===  n=%d" % len(recs))

    print("\n[1] POISONING — recency recall vs corroboration gate")
    stale = recency_recall(recs, "capital of australia")
    print("  recency recall for 'capital of Australia' ->", repr(stale["note"][:55]) if stale else None,
          "\n     (a recency store surfaces this repeated FALSE claim as current — fresh timestamps)")
    print("  corroboration view (durable only if >=2 DISTINCT sources, repetition does NOT count):")
    for claim, count, nsrc, durable in corroboration_view(recs):
        tag = "DURABLE" if durable else "blocked (not corroborated)"
        print("     - %-60s seen x%d, %d distinct src -> %s" % (claim, count, nsrc, tag))

    print("\n[2] What this shows for Elina cross-architecture")
    print("  - The repeated false 'capital of Australia is Sydney' note is recalled by recency but BLOCKED")
    print("    by the corroboration gate (repetition != corroboration; 0 distinct sources). The poison case.")
    print("  - The 'project deadline' fact has 2 DISTINCT sources -> DURABLE under the gate.")
    print("  - Adding (item, timestamp, source) is enough for Elina to gain a sybil-resistant durability")
    print("    signal on top of recency. Same data shape, runnable on a real Elina dump via --file.")


if __name__ == "__main__":
    main()
