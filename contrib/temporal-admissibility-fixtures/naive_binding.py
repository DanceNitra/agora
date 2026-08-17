"""A store with no temporal admissibility at all. It MUST score badly, and that is its job.

WHY THIS FILE EXISTS. The author of these cases also wrote the inspeximus binding, which scores 6/6.
That number is worth nothing on its own: a fixture set graded by the party that wrote both halves is
exactly the arrangement where everything passes and nothing was measured. The claim "these cases have
teeth" needs an implementation the cases BITE.

So this is an ordinary, reasonable-looking store. It records text under a key, keeps the locator it
came from, and answers questions about it. It is not a strawman -- it is what most memory layers
actually are, and every judgement it skips is one a normal implementation has no reason to make until
someone shows it a failure. It records a digest at WRITE time, which feels like provenance and is the
precise thing that is not.

If this ever scores above 0/6, the fixture has stopped discriminating and the inspeximus result must
be re-read as unearned until it is fixed.

    python run_admissibility.py --binding naive_binding:NaiveBinding
"""
from __future__ import annotations

import hashlib
from pathlib import Path


class _Store:
    def __init__(self, root: Path):
        self.docs = root / "docs"
        self.docs.mkdir(parents=True, exist_ok=True)
        self.records: dict[str, dict] = {}

    def path(self, doc):
        return self.docs / doc


class NaiveBinding:
    name = "naive-store (must fail)"

    def setup(self, workdir):
        return _Store(Path(workdir))

    def observe(self, h, *, doc, bytes_, session):
        # It writes the file. It does not record WHO read it or WHEN -- there is no observation
        # ledger, because nothing has ever needed one.
        h.path(doc).write_bytes(bytes_)

    def write(self, h, *, key, text, source, session):
        doc = (source or {}).get("doc")
        p = h.path(doc) if doc else None
        h.records[key] = {
            "text": text, "doc": doc, "session": session,
            # A WRITE-TIME digest. This is the flattering move, and it is not dishonest so much as
            # untested: it looks like provenance, is cheap, and answers the wrong question.
            "sha": hashlib.sha256(p.read_bytes()).hexdigest() if p and p.exists() else None,
        }

    def mutate_source(self, h, *, doc, bytes_):
        h.path(doc).write_bytes(bytes_)

    def delete_source(self, h, *, doc):
        h.path(doc).unlink(missing_ok=True)

    def collector_stops(self, h):
        pass                       # there is no collector to stop, so nothing can notice one stopping

    def verify(self, h, *, key, session):
        pass                       # verification is not a moment this store has a name for

    def assess(self, h, *, key, window, session):
        rec = h.records.get(key)
        if not rec:
            return {"admissible": False, "reason": None, "consulted": []}
        # "We stored a digest, so we have provenance." The record exists, the digest is on it, and
        # the answer is yes. Every boundary in the fixture is invisible from here.
        return {"admissible": True, "reason": None, "consulted": []}
