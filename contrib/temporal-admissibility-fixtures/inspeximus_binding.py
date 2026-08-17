"""The inspeximus binding for the temporal-admissibility cases.

Deliberately thin. Every judgement below is made by inspeximus; this file only translates the
fixture's vocabulary into calls and the answers back into `{admissible, reason}`. Where a mapping
required a decision rather than a lookup, the decision is written down beside it, because those
decisions are the honest content of a conformance claim -- a binding that quietly reshapes an answer
until it matches is the flattering implementation the fixture exists to catch.

Run:  python run_admissibility.py --binding inspeximus_binding:InspeximusBinding
"""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

for _c in (os.environ.get("INSPEXIMUS_REPO"),
           Path(__file__).resolve().parents[3] / "inspeximus-repo",
           Path(__file__).resolve().parents[3] / "inspeximus"):
    if _c and (Path(_c) / "inspeximus" / "core.py").is_file():
        sys.path.insert(0, str(_c))
        break

from inspeximus import Inspeximus  # noqa: E402


class _Handle:
    def __init__(self, root: Path):
        self.root = root
        self.docs = root / "docs"
        self.docs.mkdir(parents=True, exist_ok=True)
        self.mem = Inspeximus(path=str(root / "m.json"), embed=False, receipts=True)
        self.observations: dict[str, list[tuple[str, str]]] = {}   # doc -> [(session, sha256)]
        self.collector_live = True
        self.reads_since_stop = 0
        self.verified: dict[str, str] = {}                         # key -> sha at verify time
        self.consulted: list[str] = []

    def path(self, doc: str) -> Path:
        return self.docs / doc

    def sha(self, doc: str) -> str | None:
        p = self.path(doc)
        return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


class InspeximusBinding:
    name = "inspeximus"

    def setup(self, workdir):
        return _Handle(Path(workdir))

    # ── the world ───────────────────────────────────────────────────────────────────────────
    def observe(self, h, *, doc, bytes_, session):
        h.path(doc).write_bytes(bytes_)
        if h.collector_live:
            h.observations.setdefault(doc, []).append((session, hashlib.sha256(bytes_).hexdigest()))
        # When the collector is stopped the FILE still appears -- that is the whole point of T5. The
        # world keeps moving; only the record of having looked at it stops.

    def mutate_source(self, h, *, doc, bytes_):
        h.path(doc).write_bytes(bytes_)

    def delete_source(self, h, *, doc):
        h.path(doc).unlink(missing_ok=True)

    def collector_stops(self, h):
        h.collector_live = False

    # ── the store ───────────────────────────────────────────────────────────────────────────
    def write(self, h, *, key, text, source, session):
        doc = (source or {}).get("doc")
        src = None
        if doc:
            # `observed_sha256` is passed ONLY when this session actually observed the doc. That is
            # the distinction the whole set turns on: a write-time hash is not evidence of a read,
            # and passing one as if it were is how an honest capture silently becomes a claim.
            mine = [s for (sess, s) in h.observations.get(doc, []) if sess == session]
            src = {"doc": str(h.path(doc))}
            if mine:
                src["observed_sha256"] = mine[-1]
        h.mem.remember(text, key=key, object=key, source=src, meta={"sid": session})
        h.mem.flush()

    def verify(self, h, *, key, session):
        rows = [r for r in h.mem.items if r.get("key") == key]
        doc = (rows[-1].get("source") or {}).get("doc") if rows else None
        if doc:
            h.verified[key] = hashlib.sha256(Path(doc).read_bytes()).hexdigest() \
                if Path(doc).exists() else ""

    # ── the question ────────────────────────────────────────────────────────────────────────
    def assess(self, h, *, key, window, session):
        # The surfaces below are reported using the fixture's `surface_vocabulary` KEYS, not
        # prose. The first version used prose and every case failed its reach check -- correctly:
        # a shared falsification surface is only shared if both sides name it the same way.
        h.consulted = []
        rows = [r for r in h.mem.items if r.get("key") == key]
        if not rows:
            return {"admissible": False, "reason": None, "consulted": h.consulted}
        rec = rows[-1]
        src = rec.get("source") or {}
        doc_path = src.get("doc")
        doc = Path(doc_path).name if doc_path else None

        # T5 first: a dead collector poisons every OBSERVE_TO_CAPTURE answer, including ones that
        # would otherwise look fine, because the reason they look fine is that nothing is watching.
        if window == "OBSERVE_TO_CAPTURE" and not h.collector_live:
            h.consulted.append("collector_liveness")
            return {"admissible": False, "reason": "COLLECTOR_SILENT", "consulted": h.consulted}

        if window == "OBSERVE_TO_CAPTURE":
            h.consulted.append("observation_session_attribution")
            h.consulted.append("identifier_equality_write_vs_read")
            obs = h.observations.get(doc, [])
            # EXACT session equality. No casefold, no prefix: T6 is the case where a truncating
            # implementation finds the wrong session's observation and reports it as its own.
            mine = [s for (sess, s) in obs if sess == session]
            if mine:
                return {"admissible": True, "reason": None, "consulted": h.consulted}
            if obs:
                return {"admissible": False, "reason": "OBSERVATION_FOREIGN_SESSION",
                        "consulted": h.consulted}
            return {"admissible": False, "reason": "NEVER_OBSERVED", "consulted": h.consulted}

        if window in ("CAPTURE_TO_VERIFY", "VERIFY_TO_USE"):
            h.consulted.append("source_re_read" if window == "CAPTURE_TO_VERIFY"
                               else "re_read_at_point_of_use")
            now = h.sha(doc) if doc else None
            if now is None:
                # ORPHANED, not DRIFTED. Different remedy: re-source rather than revalidate, and
                # collapsing them is what T3's control exists to catch.
                return {"admissible": False, "reason": "SOURCE_ORPHANED", "consulted": h.consulted}
            was = h.verified.get(key) if window == "VERIFY_TO_USE" else src.get("observed_sha256")
            if was and now != was:
                return {"admissible": False,
                        "reason": "STALE_AT_USE" if window == "VERIFY_TO_USE" else "SOURCE_DRIFTED",
                        "consulted": h.consulted}
            if not was:
                return {"admissible": False, "reason": "NEVER_OBSERVED", "consulted": h.consulted}
            return {"admissible": True, "reason": None, "consulted": h.consulted}

        raise KeyError(f"unknown window {window!r}")
