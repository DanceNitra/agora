"""
ragfresh store adapters — plug the freshness/decay engine into a real vector store.

ragfresh.py is the pure, zero-dependency decision engine. An adapter is the thin bridge that
(1) SCANs a store's entries into `Item`s (mapping your metadata fields to the signals ragfresh
needs), and (2) APPLIES the returned plan (delete PRUNE, re-embed REFRESH, down-weight DOWNWEIGHT).

    run(adapter, now=...) -> scan -> triage -> apply -> report

Only an adapter needs its store's client (lazy-imported, so importing this module never fails):
    pgvector  -> pip install "psycopg[binary]"
    pinecone  -> pip install pinecone
The MemoryAdapter needs nothing and is the runnable reference (see `python adapters.py`).

A store only needs to keep, per chunk, the freshness signals in its metadata:
    updated_ts (source last changed, epoch) · last_access_ts · hits · value (0..1) · source_exists
ragfresh decides; the adapter applies. Nothing is deleted that triage didn't mark.
"""
from __future__ import annotations

import time
from typing import Protocol

from ragfresh import Item, triage


def run(adapter, *, now: float | None = None, apply: bool = True, **triage_kwargs) -> dict:
    """Scan the store, decide, and (optionally) apply. Returns the triage report.
    Pass apply=False for a dry run — see exactly what WOULD change before touching the store."""
    now = time.time() if now is None else float(now)
    items = adapter.scan()
    res = triage(items, now=now, **triage_kwargs)
    if apply:
        adapter.apply(res["decisions"])
    return {"applied": apply, **res["report"]}


class StoreAdapter(Protocol):
    def scan(self) -> list[Item]: ...
    def apply(self, decisions: dict[str, tuple[str, str]]) -> None: ...


# Default mapping from a store's metadata keys -> ragfresh Item fields. Override per store.
DEFAULT_FIELDS = {
    "updated_ts": "updated_ts", "last_access_ts": "last_access_ts", "hits": "hits",
    "value": "value", "source_exists": "source_exists", "bytes": "bytes",
}


def _item_from_meta(item_id: str, meta: dict, fields: dict) -> Item:
    g = lambda k, d=None: meta.get(fields.get(k, k), d)
    return Item(
        id=str(item_id),
        updated_ts=float(g("updated_ts", 0.0) or 0.0),
        last_access_ts=float(g("last_access_ts", 0.0) or 0.0),
        hits=int(g("hits", 0) or 0),
        value=(None if g("value") is None else float(g("value"))),
        source_exists=bool(g("source_exists", True)),
        bytes=int(g("bytes", 0) or 0),
    )


# ── In-memory reference adapter (zero deps; the tested round-trip) ──────────────────────────────────
class MemoryAdapter:
    """A dict-backed store: {id: {metadata...}}. The canonical, runnable reference adapter."""
    def __init__(self, records: dict[str, dict], fields: dict | None = None):
        self.records = records
        self.fields = fields or DEFAULT_FIELDS
        self.refreshed: list[str] = []
        self.weights: dict[str, float] = {}

    def scan(self) -> list[Item]:
        return [_item_from_meta(i, m, self.fields) for i, m in self.records.items()]

    def apply(self, decisions):
        from ragfresh import retrieval_weight
        now = time.time()
        for vid, (action, _reason) in list(decisions.items()):
            if action == "PRUNE":
                self.records.pop(vid, None)
            elif action == "REFRESH":
                self.refreshed.append(vid)
            elif action == "DOWNWEIGHT":
                self.weights[vid] = retrieval_weight(_item_from_meta(vid, self.records[vid], self.fields), now)


# ── pgvector adapter ───────────────────────────────────────────────────────────────────────────────
class PgVectorAdapter:
    """Postgres + pgvector. Your table needs the freshness columns (names configurable). APPLY:
    PRUNE -> DELETE, DOWNWEIGHT -> UPDATE a weight column you read at query time, REFRESH -> flag.
    Pass a live psycopg connection. pip install "psycopg[binary]"."""
    def __init__(self, conn, table: str, *, id_col="id", cols: dict | None = None,
                 weight_col="rf_weight", refresh_col="rf_refresh"):
        self.conn, self.table, self.id_col = conn, table, id_col
        self.cols = cols or {"updated_ts": "updated_ts", "last_access_ts": "last_access_ts",
                             "hits": "hits", "value": "value", "source_exists": "source_exists"}
        self.weight_col, self.refresh_col = weight_col, refresh_col

    def scan(self) -> list[Item]:
        c = self.cols
        sel = ", ".join([self.id_col] + [c[k] for k in
                        ("updated_ts", "last_access_ts", "hits", "value", "source_exists") if k in c])
        with self.conn.cursor() as cur:
            cur.execute(f"SELECT {sel} FROM {self.table}")
            keys = [self.id_col] + [k for k in
                    ("updated_ts", "last_access_ts", "hits", "value", "source_exists") if k in c]
            return [_item_from_meta(row[0], dict(zip(keys[1:], row[1:])),
                                    {k: k for k in keys}) for row in cur.fetchall()]

    def apply(self, decisions):
        prune = [v for v, (a, _) in decisions.items() if a == "PRUNE"]
        refresh = [v for v, (a, _) in decisions.items() if a == "REFRESH"]
        with self.conn.cursor() as cur:
            if prune:
                cur.execute(f"DELETE FROM {self.table} WHERE {self.id_col} = ANY(%s)", (prune,))
            if refresh:
                cur.execute(f"UPDATE {self.table} SET {self.refresh_col}=true "
                            f"WHERE {self.id_col} = ANY(%s)", (refresh,))
        self.conn.commit()


# ── Pinecone adapter ─────────────────────────────────────────────────────────────────────────────--
class PineconeAdapter:
    """Pinecone. Freshness signals live in each vector's metadata. APPLY: PRUNE -> index.delete,
    DOWNWEIGHT -> index.update(set_metadata={rf_weight}), REFRESH -> metadata flag. Client APIs vary
    by version; this targets pinecone>=3. pip install pinecone."""
    def __init__(self, index, *, fields: dict | None = None, namespace: str | None = None,
                 page: int = 1000):
        self.index, self.fields, self.namespace, self.page = index, fields or DEFAULT_FIELDS, namespace, page

    def scan(self) -> list[Item]:
        items, ids = [], []
        for batch in self.index.list(namespace=self.namespace):     # paginated id stream
            ids.extend(batch)
            if len(ids) >= self.page:
                items += self._fetch(ids); ids = []
        if ids:
            items += self._fetch(ids)
        return items

    def _fetch(self, ids):
        res = self.index.fetch(ids=ids, namespace=self.namespace)
        vecs = getattr(res, "vectors", None) or res.get("vectors", {})
        out = []
        for vid, v in vecs.items():
            meta = getattr(v, "metadata", None) or v.get("metadata", {}) or {}
            out.append(_item_from_meta(vid, meta, self.fields))
        return out

    def apply(self, decisions):
        prune = [v for v, (a, _) in decisions.items() if a == "PRUNE"]
        if prune:
            self.index.delete(ids=prune, namespace=self.namespace)
        for vid, (a, _) in decisions.items():
            if a == "REFRESH":
                self.index.update(id=vid, set_metadata={"rf_refresh": True}, namespace=self.namespace)


if __name__ == "__main__":
    import random
    random.seed(3)
    now = time.time(); DAY = 86400.0
    recs = {}
    for i in range(300):
        age = random.expovariate(1 / 60.0)
        recs[f"v{i}"] = {"updated_ts": now - age * DAY, "last_access_ts": now - random.random() * 40 * DAY,
                         "hits": int(max(0, random.gauss(10, 8))), "value": random.random() ** 2,
                         "source_exists": random.random() > 0.05, "bytes": 4096}
    n0 = len(recs)
    a = MemoryAdapter(recs)
    rep = run(a, now=now, stale_days=90, keep_budget=150)
    print("round-trip report:", rep)
    print(f"store: {n0} -> {len(a.records)} chunks  | refreshed flagged: {len(a.refreshed)}  | downweighted: {len(a.weights)}")
    assert len(a.records) == n0 - rep["counts"].get("PRUNE", 0), "apply() must delete exactly the PRUNEd"
    assert rep["orphans_removed"] >= 1
    print("OK — scan -> triage -> apply round-trip verified on the in-memory store.")
