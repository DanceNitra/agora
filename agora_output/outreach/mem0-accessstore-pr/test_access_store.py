"""Tests for the pluggable AccessStore (hit tracking + eviction policy + persistence).

Pure-stdlib; runnable directly (`python tests/memory/test_access_store.py`) or under pytest.
Includes the benchmark cited in the feature request so the performance claim is reproducible.
"""
import os
import tempfile
import time

try:                                                      # normal path (mem0 installed)
    from mem0.memory.access_store import InMemoryAccessStore, SQLiteAccessStore
except Exception:                                         # standalone path (module is stdlib-only)
    import importlib.util
    _p = os.path.join(os.path.dirname(__file__), "..", "..", "mem0", "memory", "access_store.py")
    _spec = importlib.util.spec_from_file_location("access_store", _p)
    _m = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_m)
    InMemoryAccessStore, SQLiteAccessStore = _m.InMemoryAccessStore, _m.SQLiteAccessStore


def _fresh(tmp, name):
    """An InMemory store and a fresh SQLite store (caller closes the SQLite one)."""
    return InMemoryAccessStore(), SQLiteAccessStore(os.path.join(tmp, name), flush_every=2)


def test_record_and_stats():
    with tempfile.TemporaryDirectory() as tmp:
        a, b = _fresh(tmp, "stats.db")
        try:
            for st in (a, b):
                st.record_hit("a", ts=100.0); st.record_hit("a", ts=200.0); st.record_hit("b", ts=150.0)
                assert st.get_stats("a") == (2, 200.0)
                assert st.get_stats("b") == (1, 150.0)
                assert st.get_stats("missing") is None
                assert set(st.all_stats()) == {"a", "b"}
        finally:
            b.close()


def test_evict_policies():
    now = 1_000_000.0
    with tempfile.TemporaryDirectory() as tmp:
        a, b = _fresh(tmp, "evict.db")
        try:
            for st in (a, b):
                for _ in range(20):
                    st.record_hit("stale_star", ts=now - 30 * 86400)   # 20 hits, 30d ago
                for _ in range(3):
                    st.record_hit("newbie", ts=now - 10)               # 3 hits, just now
                st.record_hit("deadweight", ts=now - 25 * 86400)       # 1 hit, 25d ago
                # LRU: oldest last_access first
                assert st.evict_candidates("lru", max_items=2, now=now)[0] == "stale_star"
                # LFU: fewest hits first
                assert st.evict_candidates("lfu", max_items=2, now=now)[0] == "deadweight"
                # DECAY: recency-weighted frequency; 1 ancient hit is worst
                assert st.evict_candidates("decay", max_items=2, now=now)[0] == "deadweight"
                # max_age: both >5d-old are candidates, the just-now one is not
                stale = set(st.evict_candidates("lru", max_age=5 * 86400, now=now))
                assert stale == {"stale_star", "deadweight"}
        finally:
            b.close()


def test_sqlite_survives_restart():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "persist.db")
        s = SQLiteAccessStore(path, flush_every=1)
        s.record_hit("x", ts=42.0); s.record_hit("x", ts=43.0)
        s.close()
        s2 = SQLiteAccessStore(path)
        try:
            assert s2.get_stats("x") == (2, 43.0)         # counts intact after restart
        finally:
            s2.close()


def test_forget():
    st = InMemoryAccessStore()
    st.record_hit("a"); st.record_hit("b")
    st.forget(["a"])
    assert st.get_stats("a") is None and st.get_stats("b") is not None


def _benchmark(n_mem=100_000, n_hits=500_000, flush_every=5000):
    import bisect, random
    random.seed(0)
    w = [1.0 / (r ** 1.07) for r in range(1, n_mem + 1)]
    tot = sum(w); cum = []; acc = 0.0
    for x in w:
        acc += x / tot; cum.append(acc)
    hits = [bisect.bisect_left(cum, random.random()) for _ in range(n_hits)]
    base = time.time()

    mem = InMemoryAccessStore()
    t0 = time.perf_counter()
    for i, x in enumerate(hits):
        mem.record_hit(str(x), base + i * 1e-6)
    us_mem = (time.perf_counter() - t0) / n_hits * 1e6

    tmp = os.path.join(tempfile.gettempdir(), "mem0_as_bench.db")
    for e in ("", "-wal", "-shm"):
        try: os.remove(tmp + e)
        except OSError: pass
    sq = SQLiteAccessStore(tmp, flush_every=flush_every)
    t0 = time.perf_counter()
    for i, x in enumerate(hits):
        sq.record_hit(str(x), base + i * 1e-6)
    sq.flush()
    us_sq = (time.perf_counter() - t0) / n_hits * 1e6
    sq._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)"); sq._conn.commit()
    mb = os.path.getsize(tmp) / 1e6
    distinct = len(set(hits)); sq.close()
    return us_mem, us_sq, mb, distinct


if __name__ == "__main__":
    test_record_and_stats(); test_evict_policies(); test_sqlite_survives_restart(); test_forget()
    print("functional tests: PASS")
    um, us, mb, distinct = _benchmark()
    print(f"benchmark: in-mem {um:.2f} us/hit | SQLite {us:.2f} us/hit | "
          f"{mb:.1f} MB / {distinct:,} tracked -> ~{mb / distinct * 100000:.1f} MB / 100k")
