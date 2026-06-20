"""
Verify the benchmark we cited publicly on mem0#5611 (verify-before-citing): a pluggable AccessStore for
mem0 (hit_count + last_access), persistence decoupled from the 30+ vector backends. We claimed: SQLite
sidecar (WAL, synchronous=NORMAL, batched commit) ~6.4us/recorded hit, ~2.0MB on disk for 100k memories,
full survival across restart; in-memory ~0.27us/hit. Re-measure honestly under a Zipf-ish access pattern.
This doubles as the benchmark TEST for the focused PR we offered (AccessStore interface + InMemory + SQLite).
"""
import os, sqlite3, tempfile, time, math, random

N_MEM = 100_000
N_HITS = 500_000
FLUSH_EVERY = 5_000          # write-behind: amortize SQLite writes
random.seed(0)


def _zipf_ids(n_ids, n_draws, s=1.07):
    """Skewed (Zipf-ish) access: a few memories get most of the hits."""
    ranks = list(range(1, n_ids + 1))
    weights = [1.0 / (r ** s) for r in ranks]
    # precompute cumulative for fast sampling
    tot = sum(weights)
    cum = []
    acc = 0.0
    for w in weights:
        acc += w / tot
        cum.append(acc)
    import bisect
    return [bisect.bisect_left(cum, random.random()) for _ in range(n_draws)]


class InMemoryAccessStore:
    def __init__(self):
        self.d = {}

    def record_hit(self, mid, ts):
        h = self.d.get(mid)
        if h:
            h[0] += 1; h[1] = ts
        else:
            self.d[mid] = [1, ts]

    def flush(self):
        pass


class SQLiteAccessStore:
    """File-backed, survives restart, no vector-backend changes. Write-behind buffer + batched UPSERT."""
    def __init__(self, path):
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("CREATE TABLE IF NOT EXISTS access "
                          "(memory_id INTEGER PRIMARY KEY, hit_count INTEGER, last_access REAL)")
        self.conn.commit()
        self.buf = {}

    def record_hit(self, mid, ts):
        h = self.buf.get(mid)
        if h:
            h[0] += 1; h[1] = ts
        else:
            self.buf[mid] = [1, ts]
        if len(self.buf) >= FLUSH_EVERY:
            self.flush()

    def flush(self):
        if not self.buf:
            return
        rows = [(mid, hc, la) for mid, (hc, la) in self.buf.items()]
        self.conn.executemany(
            "INSERT INTO access(memory_id,hit_count,last_access) VALUES(?,?,?) "
            "ON CONFLICT(memory_id) DO UPDATE SET hit_count=hit_count+excluded.hit_count, "
            "last_access=excluded.last_access", rows)
        self.conn.commit()
        self.buf.clear()

    def count(self, mid):
        r = self.conn.execute("SELECT hit_count FROM access WHERE memory_id=?", (mid,)).fetchone()
        return r[0] if r else 0


def bench(store, hits):
    t0 = time.perf_counter()
    base = time.time()
    for i, mid in enumerate(hits):
        store.record_hit(mid, base + i * 1e-6)
    store.flush()
    return (time.perf_counter() - t0) / len(hits) * 1e6   # us per hit


if __name__ == "__main__":
    print("compile OK", flush=True)
    print(f"building {N_HITS:,} Zipf-ish hits over {N_MEM:,} memories ...", flush=True)
    hits = _zipf_ids(N_MEM, N_HITS)
    distinct = len(set(hits))
    top = max(hits, key=hits.count) if N_HITS < 1 else None  # skip slow count

    mem = InMemoryAccessStore()
    us_mem = bench(mem, hits)

    tmp = os.path.join(tempfile.gettempdir(), "agora_mem0_accessstore_bench.db")
    for ext in ("", "-wal", "-shm"):
        try: os.remove(tmp + ext)
        except OSError: pass
    sq = SQLiteAccessStore(tmp)
    us_sq = bench(sq, hits)
    # checkpoint WAL into the main db so size reflects the real on-disk footprint
    sq.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    sq.conn.commit()
    size_mb = os.path.getsize(tmp) / 1e6

    # restart survival: pick a few ids, record their counts, close, reopen, verify
    sample = list(sq.buf.keys())[:0] or [hits[0], hits[1], hits[-1]]
    before = {mid: sq.count(mid) for mid in sample}
    sq.conn.close()
    sq2 = SQLiteAccessStore(tmp)
    after = {mid: sq2.count(mid) for mid in sample}
    survived = before == after and all(v > 0 for v in after.values())
    sq2.conn.close()

    print("\n=== mem0 AccessStore benchmark (re-measured) ===", flush=True)
    print(f"  distinct memories hit: {distinct:,} / {N_MEM:,}")
    print(f"  in-memory:        {us_mem:.2f} us / recorded hit")
    print(f"  SQLite (WAL, synchronous=NORMAL, write-behind {FLUSH_EVERY}): {us_sq:.2f} us / recorded hit")
    print(f"  on-disk size for {N_MEM:,} tracked memories: {size_mb:.1f} MB")
    print(f"  restart survival (counts intact after close+reopen): {survived}  ({before} -> {after})")
    print(f"\n  vs vector search ~1-10 ms -> persistence overhead per query: {us_sq/1000:.4f} ms "
          f"({us_sq/1000/1.0*100:.2f}% of a 1ms search)")
    print("\n=== COMPARE TO POSTED CLAIM (#5611) ===")
    print(f"  claimed: ~6.4 us/hit SQLite, ~0.27 us/hit in-mem, ~2.0 MB/100k, survives restart")
    print(f"  measured: {us_sq:.2f} us/hit SQLite, {us_mem:.2f} us/hit in-mem, {size_mb:.1f} MB, survives={survived}")
