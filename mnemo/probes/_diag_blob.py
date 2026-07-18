import os, sys, asyncio
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import competitor_cells as C

ps = C.pairs(3)
print("=== GRAPHITI blob check (poison stream [A,B,A]) ===", flush=True)
async def gcheck():
    g = C._graphiti()
    await g.driver.execute_query("MATCH (n) WHERE n.group_id STARTS WITH 'diag_' DETACH DELETE n")
    for i,(k,A,B) in enumerate(ps):
        blob = await C._g_ingest_current(g, f"diag_{i}", [A,B,A], k)
        ans = C.judge(blob, k.rstrip(" ."))
        vA,vB = C.val_of(A,k).lower(), C.val_of(B,k).lower()
        print(f"[{i}] key={k!r}  vA={vA!r} vB={vB!r}", flush=True)
        print(f"    BLOB({len(blob)} chars)= {blob[:220]!r}", flush=True)
        print(f"    JUDGE= {ans!r}   held={(vB in ans and vA not in ans)}", flush=True)
    await g.close()
asyncio.run(gcheck())

print("\n=== MEM0 blob check ===", flush=True)
mem = C._mem0()
for i,(k,A,B) in enumerate(ps):
    uid=f"diag{i}"
    for w in (A,B,A):
        try: mem.add(w, user_id=uid)
        except Exception as e: print("add err",e)
    sr = mem.search(k, filters={"user_id":uid}, top_k=10)
    rows = sr.get("results",sr) if isinstance(sr,dict) else sr
    blob=" ".join((x.get("memory") or x.get("text") or str(x)) for x in (rows or [])).lower()
    ans=C.judge(blob,k.rstrip(" ."))
    vA,vB=C.val_of(A,k).lower(),C.val_of(B,k).lower()
    print(f"[{i}] key={k!r} vA={vA!r} vB={vB!r}", flush=True)
    print(f"    BLOB({len(blob)})= {blob[:220]!r}", flush=True)
    print(f"    JUDGE= {ans!r}  held={(vB in ans and vA not in ans)}", flush=True)
