"""Would `strict_corroboration=True` as a DEFAULT protect anything, or just silence a tier?

Read-only. Before flipping that default we need one number: how many records in the stores this
deployment actually runs carry a VERIFIED KEY. With the flag ON, a corroborating link only counts if
it carries an attestation, so:

    attestation coverage ~0  ==>  `_distinct` collapses to <2 for essentially every record
                             ==>  the `corroborated` tier stops occurring at all
                             ==>  every record that used to read `corroborated` now reads `unwarranted`

That is not a safer default, it is a tier deleted by omission -- the same shape as the measured
`slash(scope='source')` failure, where the default scope resolved on a field no writer ever set and
returned ok on 261,673 records. A lever that selects on an unfilled field reports success.

This counts, per store: total records, how many carry any `source`, how many carry an attestation /
verified key, and how many carry >=2 links at all. It changes nothing on disk.

Run: python -X utf8 research/probes/attestation_coverage_before_flipping_strict.py
"""
from __future__ import annotations

import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

STORES = [
    ROOT / ".inspeximus" / "coding_memory.json",
    ROOT / "server" / ".inspeximus" / "coding_memory.json",
    ROOT / "agora-game-server" / ".agent_memory" / "artificer.json",
    ROOT / "agora-game-server" / ".agent_memory" / "cartographer.json",
    ROOT / "agora-game-server" / ".agent_memory" / "king.json",
    ROOT / "agora-game-server" / ".agent_memory" / "scholar.json",
]

# ONLY the field the library actually gates on. The first version of this list included "key", which
# is the SUPERSESSION key (`decision::<topic>`, `cmd:a973f713`) present on most records -- so it
# reported 7751/7751 = 100% attestation coverage on a store with none at all, and I nearly published
# that. A coverage probe whose matcher over-matches invents the very coverage it was built to doubt.
ATTEST_KEYS = ("attested_key",)


def records(obj):
    if isinstance(obj, list):
        return [r for r in obj if isinstance(r, dict)]
    if isinstance(obj, dict):
        for k in ("items", "records", "memories", "data"):
            v = obj.get(k)
            if isinstance(v, list):
                return [r for r in v if isinstance(r, dict)]
    return []


def has_attestation(r) -> bool:
    """Any field on the record (or its links) that could carry a verifiable key."""
    for k in ATTEST_KEYS:
        v = r.get(k)
        if v:
            return True
    src = r.get("source")
    if isinstance(src, dict) and any(src.get(k) for k in ATTEST_KEYS):
        return True
    for ln in (r.get("links") or []):
        if isinstance(ln, dict) and any(ln.get(k) for k in ATTEST_KEYS):
            return True
    return False


def main() -> int:
    grand = dict(n=0, src=0, att=0, links2=0)
    print("%-46s %9s %9s %9s %9s" % ("store", "records", "w/source", "w/attest", ">=2 links"))
    for p in STORES:
        if not p.exists():
            print("%-46s %9s" % (p.name + "  (absent)", "-"))
            continue
        try:
            obj = json.load(io.open(p, encoding="utf-8", errors="replace"))
        except Exception as ex:
            print("%-46s  UNREADABLE: %s" % (p.name, type(ex).__name__))
            continue
        rs = records(obj)
        n = len(rs)
        src = sum(1 for r in rs if r.get("source"))
        att = sum(1 for r in rs if has_attestation(r))
        l2 = sum(1 for r in rs if len(r.get("links") or []) >= 2)
        grand["n"] += n; grand["src"] += src; grand["att"] += att; grand["links2"] += l2
        print("%-46s %9d %9d %9d %9d" % (p.name[:46], n, src, att, l2))

    n = grand["n"] or 1
    print("\nTOTAL records: %d" % grand["n"])
    print("  carrying any `source`      : %7d  (%.3f%%)" % (grand["src"], 100.0 * grand["src"] / n))
    print("  carrying an ATTESTATION    : %7d  (%.3f%%)" % (grand["att"], 100.0 * grand["att"] / n))
    print("  carrying >=2 links at all  : %7d  (%.3f%%)" % (grand["links2"], 100.0 * grand["links2"] / n))

    print("\nVERDICT:")
    if grand["att"] == 0:
        print("  NO record in any store carries a verifiable key. With strict_corroboration ON by")
        print("  DEFAULT, `corroborated` becomes unreachable for this entire deployment -- the tier")
        print("  would not be hardened, it would be deleted. Ship it opt-in, or ship attestation")
        print("  coverage first and flip the default after.")
        return 1
    print("  %d record(s) carry a verifiable key (%.3f%%); a default flip is defensible only if that"
          % (grand["att"], 100.0 * grand["att"] / n))
    print("  coverage is where corroboration is actually expected to come from.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
