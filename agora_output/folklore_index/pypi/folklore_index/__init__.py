"""The Folklore Index - a runnable benchmark of AI / data-science claims.

>>> import folklore_index as fi
>>> fi.verdicts()            # {'REPRODUCED': .., 'FAILED': .., 'NOT_COMPUTABLE': ..}
>>> fi.get("FI-0001")        # one claim by its permanent citation key
"""
import json, os

_DATA = os.path.join(os.path.dirname(__file__), "folklore_index.json")


def load():
    """Return the full dataset (metadata + entries)."""
    with open(_DATA, encoding="utf-8") as f:
        return json.load(f)


def claims():
    """Return the list of claim entries."""
    return load()["entries"]


def get(key):
    """Return one claim by its permanent FI-NNNN key, or None."""
    return next((e for e in claims() if e.get("key") == key), None)


def verdicts():
    """Return the verdict counts."""
    return load()["counts"]["by_verdict"]


__version__ = load().get("version", "0")
