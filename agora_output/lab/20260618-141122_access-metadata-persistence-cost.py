
import sqlite3, time, random, os, tempfile

random.seed(7)
N = 100_000          # memories in the store
M = 500_000          # search hits to record
# Zipf-ish access: a few memories get hit a lot (realistic retrieval)
ids = [int(N * (random.random()**2)) for _ in range(M)]  # skewed toward low ids

# (a) in-memory dict (current "best-effort" model)
mem = {}
t0 = time.perf_counter()
for i in ids:
    h, _ = mem.get(i, (0, 0.0))
    mem[i] = (h + 1, t0)
t_mem = (time.perf_counter() - t0) / M * 1e6   # us/hit

# (b) SQLite sidecar, WAL, batched commit every 1000 hits
db = os.path.join(tempfile.gettempdir(), "_access_meta.db")
if os.path.exists(db): os.remove(db)
con = sqlite3.connect(db)
con.execute("PRAGMA journal_mode=WAL")
con.execute("PRAGMA synchronous=NORMAL")
con.execute("CREATE TABLE access(id INTEGER PRIMARY KEY, hit_count INTEGER, last_access REAL)")
con.commit()
t0 = time.perf_counter()
for k, i in enumerate(ids):
    con.execute(
        "INSERT INTO access(id,hit_count,last_access) VALUES(?,1,?) "
        "ON CONFLICT(id) DO UPDATE SET hit_count=hit_count+1, last_access=excluded.last_access",
        (i, t0))
    if k % 1000 == 0:
        con.commit()
con.commit()
t_sql = (time.perf_counter() - t0) / M * 1e6   # us/hit
size_mb = os.path.getsize(db) / 1e6
rows = con.execute("SELECT COUNT(*) FROM access").fetchone()[0]
total_hits = con.execute("SELECT SUM(hit_count) FROM access").fetchone()[0]
con.close()

# (c) survives restart? reopen and re-read
con2 = sqlite3.connect(db)
rows2 = con2.execute("SELECT COUNT(*) FROM access").fetchone()[0]
con2.close()
os.remove(db)

print(json._x if False else "")
import json as J
print(J.dumps({
  "in_memory_us_per_hit": round(t_mem,3),
  "sqlite_sidecar_us_per_hit": round(t_sql,3),
  "sqlite_file_MB_for_100k": round(size_mb,2),
  "distinct_memories_tracked": rows,
  "total_hits_recorded": total_hits,
  "rows_after_reopen": rows2,
  "survives_restart": rows2 == rows,
  "typical_vector_search_ms": "~1-10 (embedding+ANN), so persistence cost is <1% of a query"
}, indent=2))
