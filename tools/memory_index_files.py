"""Which files in the memory directory are the INDEX, and which are data rows.

ONE DEFINITION, because the wrong one shipped four times. Every probe that reads the memory store
had its own copy of the test, and every copy said "the name starts with `memory`". That is the
index (`MEMORY.md`), the archive (`MEMORY_ARCHIVE.md`) and the `MEMORY.md.bak-*` snapshots -- and
also `memorygraft-crucible-candidate`, `memory-scan-product-backlog` and
`memory-tipping-ews-killed`, which are ordinary notes.

WHAT IT COST. Measured 2026-09-08. The exclusion form hid a row that had left the index by sharing
a line with a judged neighbour, so a cohort published on anthropics/claude-code#91188 as 15 rows was
16, and four more figures in the same comment were wrong with it. The pre-send check recomputed
those figures independently rather than quoting them, and passed 24 of 24 -- because it carried the
same filter. A second reader that shares one defect with the first is not a second reader.

The inclusion form has the mirror defect: a filesystem sweep looking for index files by the same
prefix collects data notes as candidate indexes.

USE THESE, never a fresh `startswith`. `is_index_file` for "skip the container", `looks_like_an_index`
for "find the containers".
"""
from __future__ import annotations

import os

# The two real index documents. Snapshots are `MEMORY.md.bak-<stamp>`, matched by prefix on the
# FULL index name, which no data row can collide with because no slug contains ".md.bak".
INDEX_NAMES = {"memory.md", "memory_archive.md"}
SNAPSHOT_PREFIX = "memory.md.bak"
MANIFEST_NAMES = {"memory_archive_manifest.jsonl"}


def is_index_file(name: str) -> bool:
    """True for the index, the archive, a snapshot or the manifest. False for every data row."""
    n = os.path.basename(str(name)).lower()
    return n in INDEX_NAMES or n in MANIFEST_NAMES or n.startswith(SNAPSHOT_PREFIX)


def looks_like_an_index(name: str) -> bool:
    """True for a filename that could BE an index document, for a filesystem sweep.

    The mirror of `is_index_file`: same set, stated as a search rather than as a skip. A sweep that
    used the bare prefix collected data notes whose slug begins with "memory".
    """
    n = os.path.basename(str(name)).lower()
    return n in INDEX_NAMES or n.startswith(SNAPSHOT_PREFIX)


def slug_is_index(slug: str) -> bool:
    """`is_index_file` for a bare slug that carries no extension."""
    return is_index_file(str(slug) + ".md")


def _self_check() -> None:
    """The definition must reach both containers and neither data row. Call it in any probe.

    A control, not a unit test: if this ever stops distinguishing the two, every count built on it
    is void, and the probe that calls it should refuse rather than report a number.
    """
    must_be_index = ["MEMORY.md", "memory.md", "MEMORY_ARCHIVE.md",
                     "MEMORY.md.bak-20260904-pretrim", "MEMORY.md.bak-20260819-prewindowfit-3"]
    must_be_data = ["memorygraft-crucible-candidate.md", "memory-scan-product-backlog.md",
                    "memory-tipping-ews-killed.md", "a-guard-you-must-choose-to-use.md"]
    bad = [n for n in must_be_index if not is_index_file(n)]
    bad += [n for n in must_be_data if is_index_file(n)]
    if bad:
        raise SystemExit("REFUSED: the index/data test is wrong for %r, so every count built on "
                         "it is void" % (bad,))
    if not all(looks_like_an_index(n) for n in must_be_index):
        raise SystemExit("REFUSED: the index sweep cannot find its own targets")
    if any(looks_like_an_index(n) for n in must_be_data):
        raise SystemExit("REFUSED: the index sweep collects data notes")


# RUN AT IMPORT, not on request. A control a caller must remember to invoke is a control that is
# absent from the call site that needed it. This costs eight string comparisons.
_self_check()


if __name__ == "__main__":
    print("index/data test holds for both containers and all named data rows")
