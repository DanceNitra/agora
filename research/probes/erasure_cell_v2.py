"""Erasure cell v2 — rebuilt after a red-team review killed v1's framing.

v1 measured bytes on disk and called it "is the value gone". Six defects were found and every one is
addressed here, because each of them could have turned a peer's honest design into a public
accusation:

  1. WRONG ENTRY POINT. v1 called kg.invalidate_fact() directly — the internal that delete() happens
     to call. The claim is about the PUBLIC api, so v2 calls memory_backend.delete().
  2. NEVER QUERIED. v1 read bytes and never asked whether the record was still RETRIEVABLE. That is
     the user-visible expectation and the first question any author would ask. v2 measures both, and
     reports them separately: `retrievable` and `on_disk` are different guarantees.
  3. ASYMMETRIC OPERATIONS. v1 compared a status toggle (wmm) against forget_subject() — our
     purpose-built eraser. That flatters us. v2 runs inspeximus TWICE: once through supersede (the
     matched analogue of invalidate) and once through forget_subject, and reports both rows.
  4. DEGENERATE CONTROL. v1's no-op control never called a delete, so it only proved the scanner can
     find plaintext in a plaintext file. v2 adds a NEGATIVE control (truncate the store — must report
     REMOVED, proving the scanner can see an absence) and an ENCRYPTED control (must report
     NOT_COMPUTABLE, never REMOVED, proving encryption is not mistaken for erasure).
  5. NO ARTIFACT SURVIVED. v1 rmtree'd the workdir in a finally and printed to console. The standing
     gate requires a re-runnable artifact with persisted output, so v2 writes erasure_cell_v2.json
     and keeps the store directory on failure.
  6. OVERSTATED SCOPE. "the whole package" was wrong — world-model-mcp's repo carries a real
     `DELETE FROM facts` in scripts/demo_seed.py, excluded from the wheel. The claim is about the
     SHIPPED package and says so.

Neither peer promises on-disk removal, and both are honest about what they do. This measures a
difference between designs, not a defect.
"""
import asyncio
import json
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "erasure_cell_v2.json")
SENTINEL = "ZQX" + format(int(time.time() * 1e6), "x") + "QZX"


def scan(root: str, token: str) -> list[str]:
    """Files whose RAW BYTES hold the token. Binary: a value inside a SQLite page still counts."""
    needle, hits = token.encode(), []
    for dp, _dn, fs in os.walk(root):
        for f in fs:
            try:
                with open(os.path.join(dp, f), "rb") as fh:
                    if needle in fh.read():
                        hits.append(os.path.relpath(os.path.join(dp, f), root))
            except Exception:
                continue
    return hits


def row(system, op, stored, retrievable_before, retrievable_after, disk_before, disk_after,
        note="", verdict=None):
    """One measured operation. `retrievable` and `on_disk` are DIFFERENT guarantees and are never
    merged into a single score — conflating them is how a status toggle gets called a data leak."""
    if verdict is None:
        if not stored:
            verdict = "NOT_COMPUTABLE"
        else:
            verdict = ("REMOVED FROM DISK" if not disk_after
                       else "ON DISK AFTER DELETE")
    return {"system": system, "operation": op, "stored_at_all": stored,
            "retrievable_before": retrievable_before, "retrievable_after": retrievable_after,
            "on_disk_before": disk_before, "on_disk_after": disk_after,
            "verdict": verdict, "note": note}


# ---------------------------------------------------------------- controls
def control_negative(work):
    """Truncating the store MUST read as REMOVED. If it does not, the scanner cannot see an absence
    and every REMOVED verdict in the run is meaningless."""
    d = os.path.join(work, "ctl_neg")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "store.txt")
    open(p, "w", encoding="utf-8").write(f"secret {SENTINEL}\n")
    before = scan(d, SENTINEL)
    open(p, "w", encoding="utf-8").write("")          # the "delete": truncate
    after = scan(d, SENTINEL)
    return row("CONTROL negative", "truncate the store", bool(before), None, None, before, after,
               note="MUST be REMOVED FROM DISK, else the scanner cannot detect absence")


def control_encrypted(work):
    """An encrypted store must read as NOT_COMPUTABLE, never REMOVED. Mistaking encryption for
    erasure is the single most dangerous false positive this cell can produce."""
    import base64
    d = os.path.join(work, "ctl_enc")
    os.makedirs(d, exist_ok=True)
    blob = base64.b64encode(f"secret {SENTINEL}".encode()).decode()
    open(os.path.join(d, "store.enc"), "w", encoding="utf-8").write(blob)
    before = scan(d, SENTINEL)
    return row("CONTROL encrypted", "none (store is obfuscated at rest)", bool(before), None, None,
               before, before,
               verdict="NOT_COMPUTABLE" if not before else "SCANNER SAW THROUGH ENCODING",
               note="MUST be NOT_COMPUTABLE: a plaintext scan cannot speak about an encrypted store")


# ---------------------------------------------------------------- arms
async def arm_wmm(work):
    """world-model-mcp through its PUBLIC api only: create() -> delete() / purge().

    THREE HARNESS DEFECTS FIXED HERE, all of which flattered or falsified the result:

      a. FIXTURE BUILT INTERNALLY. Earlier versions created the record with kg.create_fact(). delete()
         and purge() resolve a record by _normalize_path() + _latest_fact_for(), so a hand-built Fact is
         not reachable from them: both returned "No memory at hr/x.md" and the arm measured a no-op while
         reporting a verdict. v2's own defect #1 was calling an internal; the fixture had the same bug one
         level down.
      b. TRUTHINESS. Retrievability was read as bool(kg.query_facts(...)). That returns a QueryFactResult
         object, which is truthy whether it holds one fact or none -- so `retrievable` was True by
         construction and measured nothing. It now counts result.facts.
      c. READ CONTAMINATION. Opening sqlite3 connections to facts.db alongside the live KnowledgeGraph
         made a later query_facts() return a stale snapshot: purge showed 0 rows in both tables AND
         1 retrievable fact in the same run. Isolated, purge reports 0. No side-channel reads here.
    """
    try:
        from world_model_server.knowledge_graph import KnowledgeGraph
        from world_model_server.memory_backend import WorldModelMemoryBackend
    except Exception as e:
        return [row("world-model-mcp", "import", False, None, None, [], [],
                    note=f"import failed: {str(e)[:110]}", verdict="NOT_COMPUTABLE")]

    async def one(op, sentinel, tag):
        d = os.path.join(work, f"wmm_{op}")
        os.makedirs(d, exist_ok=True)
        kg = KnowledgeGraph(d)
        await kg.initialize()
        mb = WorldModelMemoryBackend(kg)
        if not hasattr(mb, op):
            return row("world-model-mcp", f"{op}()", False, None, None, [], [],
                       note=f"{op}() absent -- pre-0.15.6 wheel", verdict="NOT_COMPUTABLE")

        async def n_facts():
            r = await kg.query_facts(sentinel)
            f = getattr(r, "facts", None)
            return None if f is None else len(f)

        await mb.create("hr/x.md", f"recovery phrase {sentinel}")
        before_n, before_d = await n_facts(), scan(d, sentinel)
        if not before_d:
            return row("world-model-mcp", f"{op}()", False, before_n not in (0, None), None, [], [],
                       note="PRECONDITION FAILED: never reached disk -- our harness")
        ret = await getattr(mb, op)("hr/x.md")
        if isinstance(ret, str) and ret.lower().startswith("no memory at"):
            return row("world-model-mcp", f"{op}()", False, before_n not in (0, None), None, [], [],
                       note=f"PRECONDITION FAILED: {op}() did not resolve the path -- our harness",
                       verdict="NOT_COMPUTABLE")
        after_n = await n_facts()                     # SAME instance -- the reader that queried first
        kg2 = KnowledgeGraph(d)
        await kg2.initialize()
        r2 = await kg2.query_facts(sentinel)
        f2 = getattr(r2, "facts", None)
        fresh_n = None if f2 is None else len(f2)     # a reader that did NOT query before

        # Both read paths, because they DISAGREE for purge and that disagreement is the finding:
        # KnowledgeGraph caches query results with a TTL and purge_fact()/invalidate_fact()/
        # supersede_fact() do not call _cache_invalidate() (create_fact() does). So a caller that
        # searched before erasing keeps getting the erased fact from the same instance, while the row
        # is genuinely gone from `facts` and `facts_fts`.
        return row("world-model-mcp", f"memory_backend.{op}()  [{tag}]", True,
                   before_n not in (0, None), after_n not in (0, None),
                   before_d, scan(d, sentinel),
                   note=f'returns: "{str(ret)[:80]}" | same-instance reader: '
                        f'{after_n} fact(s) | fresh reader: {fresh_n} fact(s)')

    return [await one("delete", SENTINEL[:-3] + "DEL", "soft-invalidate, by design"),
            await one("purge", SENTINEL[:-3] + "PRG", "hard erase, v0.15.6+")]


def arm_inspeximus(work):
    """BOTH operations, so the comparison is matched: supersede is the analogue of invalidate;
    forget_subject is the purpose-built eraser and is not a fair comparator for a status toggle."""
    try:
        sys.path.insert(0, r"C:\Users\Danculus\inspeximus-repo")
        from inspeximus import Inspeximus
    except Exception as e:
        return [row("inspeximus", "import", False, None, None, [], [],
                    note=f"import failed: {str(e)[:110]}", verdict="NOT_COMPUTABLE")]
    out = []
    for op in ("supersede (matched to invalidate)", "forget_subject (purpose-built erasure)"):
        d = os.path.join(work, "insp_" + ("sup" if op.startswith("supersede") else "forget"))
        os.makedirs(d, exist_ok=True)
        try:
            m = Inspeximus(path=os.path.join(d, "store.json"))
            m.remember(f"recovery phrase {SENTINEL}", source={"doc": "hr/alice"})

            def retr():
                try:
                    return any(SENTINEL in json.dumps(x) for x in (m.recall(SENTINEL) or []))
                except Exception:
                    return None

            before_r, before_d = retr(), scan(d, SENTINEL)
            if not before_d:
                out.append(row("inspeximus", op, False, before_r, None, [], [],
                               note="PRECONDITION FAILED: never reached disk"))
                continue
            if op.startswith("supersede"):
                m.remember("recovery phrase retracted", source={"doc": "hr/alice"},
                           supersedes_subject="hr/alice") if "supersedes_subject" in \
                    getattr(m.remember, "__code__", type("x", (), {"co_varnames": ()})).co_varnames \
                    else m.remember("recovery phrase retracted", source={"doc": "hr/alice"})
            else:
                m.forget_subject("hr/alice")
            out.append(row("inspeximus", op, True, before_r, retr(), before_d, scan(d, SENTINEL)))
        except Exception as e:
            out.append(row("inspeximus", op, False, None, None, [], [],
                           note=f"OUR harness first: {type(e).__name__}: {str(e)[:120]}",
                           verdict="NOT_COMPUTABLE"))
    return out


async def main():
    work = os.path.join(HERE, "_erasure_v2_work")
    os.makedirs(work, exist_ok=True)
    rows = [control_negative(work), control_encrypted(work)]
    rows += arm_inspeximus(work)
    rows += await arm_wmm(work)

    neg = rows[0]["verdict"] == "REMOVED FROM DISK"
    enc = rows[1]["verdict"] == "NOT_COMPUTABLE"
    result = {"sentinel": SENTINEL, "controls_passed": neg and enc,
              "control_negative": rows[0]["verdict"], "control_encrypted": rows[1]["verdict"],
              "rows": rows,
              "scope_note": "world-model-mcp claims are about the SHIPPED wheel. The repo carries a "
                            "real DELETE FROM facts in scripts/demo_seed.py, excluded via "
                            "pyproject packages=['world_model_server']."}
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)

    print(f"sentinel {SENTINEL}\ncontrols: negative={rows[0]['verdict']}  "
          f"encrypted={rows[1]['verdict']}  -> {'PASSED' if neg and enc else 'FAILED (run is VOID)'}\n")
    for r in rows[2:]:
        print(f"--- {r['system']}  [{r['operation']}]")
        print(f"    verdict      : {r['verdict']}")
        print(f"    retrievable  : before={r['retrievable_before']}  after={r['retrievable_after']}")
        print(f"    on disk after: {r['on_disk_after'] or 'nothing'}")
        if r["note"]:
            print(f"    note         : {r['note']}")
    print(f"\nartifact: {OUT}")


asyncio.run(main())
