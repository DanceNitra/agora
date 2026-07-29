"""Does 'delete' remove the VALUE from disk? Measured at runtime, not read from source.

Static reading said world-model-mcp's delete() calls invalidate_fact(), which is
`UPDATE facts SET invalid_at = ?` — a status change. That is a reading, not a measurement. This runs
it: write a rare sentinel string, call the system's own delete, then open the storage file in binary
and look for the sentinel. Bytes on disk are the only witness that cannot be argued with.

THE CONTROL IS THE POINT. A cell that reports "value still present" for a store that never stored it
in the first place proves nothing, so every arm must first pass `stored_at_all` — the sentinel must
be found BEFORE the delete. An arm that fails that precondition is reported as NOT_COMPUTABLE, never
as a finding against the system. My mem0 adapter once scored 0.00 purely because a rejected API call
failed inside a bare `except`, and I nearly published a false accusation off it.

Neither peer here promises on-disk removal. This measures a documented design difference between
three honest positions, not a defect in anyone's product.
"""
import asyncio
import os
import shutil
import sys
import tempfile
import uuid

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

#: Long and random so a hit cannot be a coincidence of ordinary text.
SENTINEL = "ZQX" + uuid.uuid4().hex + "QZX"


def sentinel_on_disk(root: str, token: str) -> list[str]:
    """Every file under root whose RAW BYTES contain the token. Binary, not text: a value inside a
    SQLite page, a WAL frame or a compressed blob still counts as present."""
    needle = token.encode()
    hits = []
    for dp, _dn, fs in os.walk(root):
        for f in fs:
            p = os.path.join(dp, f)
            try:
                with open(p, "rb") as fh:
                    if needle in fh.read():
                        hits.append(os.path.relpath(p, root))
            except Exception:
                continue
    return hits


async def arm_world_model_mcp(workdir: str) -> dict:
    """Write a fact, delete it through the public API, then look for the value on disk."""
    try:
        from world_model_server.knowledge_graph import KnowledgeGraph
        from world_model_server.models import Fact
    except Exception as e:
        return {"system": "world-model-mcp", "verdict": "NOT_COMPUTABLE",
                "why": f"import failed: {str(e)[:120]}"}

    try:
        kg = KnowledgeGraph(workdir)
        if hasattr(kg, "initialize"):
            await kg.initialize()
        elif hasattr(kg, "init_db"):
            await kg.init_db()

        # Build from the model's OWN required fields rather than my guess at them. The first run
        # died on a missing `evidence_path` — my adapter's defect, not their system's, and exactly
        # the failure the NOT_COMPUTABLE branch exists to absorb instead of blaming the peer.
        required = [n for n, f in Fact.model_fields.items() if f.is_required()]
        kw = {"fact_text": f"The account holder's recovery phrase is {SENTINEL}.",
              "evidence_type": "session", "status": "canonical",
              "evidence_path": "hr/alice.md", "subject": "hr/alice",
              "predicate": "has_recovery_phrase", "object": SENTINEL}
        kw = {k: v for k, v in kw.items() if k in Fact.model_fields}
        for n in required:
            kw.setdefault(n, "hr/alice.md" if "path" in n else SENTINEL)
        fact = Fact(**kw)
        fid = await kg.create_fact(fact)   # NOT add_fact — read the API, do not guess it
        fid = fid if isinstance(fid, str) else getattr(fact, "id", None)

        before = sentinel_on_disk(workdir, SENTINEL)
        if not before:
            return {"system": "world-model-mcp", "verdict": "NOT_COMPUTABLE",
                    "why": "PRECONDITION FAILED: the value was never on disk before the delete, so "
                           "its absence afterwards would prove nothing about deletion."}

        await kg.invalidate_fact(fid)
        after = sentinel_on_disk(workdir, SENTINEL)
        return {"system": "world-model-mcp", "stored_at_all": True,
                "files_before": before, "files_after": after,
                "verdict": "VALUE REMAINS ON DISK" if after else "VALUE REMOVED"}
    except Exception as e:
        return {"system": "world-model-mcp", "verdict": "NOT_COMPUTABLE",
                "why": f"runtime error, treat as OUR adapter's fault first: {type(e).__name__}: "
                       f"{str(e)[:160]}"}


def arm_inspeximus(workdir: str) -> dict:
    """The same question asked of our own store, in the same cycle. Both ends of the delta."""
    try:
        sys.path.insert(0, r"C:\Users\Danculus\inspeximus-repo")
        from inspeximus import Inspeximus
    except Exception as e:
        return {"system": "inspeximus", "verdict": "NOT_COMPUTABLE",
                "why": f"import failed: {str(e)[:120]}"}
    try:
        path = os.path.join(workdir, "insp.json")
        m = Inspeximus(path=path)
        m.remember(f"The account holder's recovery phrase is {SENTINEL}.",
                   source={"doc": "hr/alice"})
        before = sentinel_on_disk(workdir, SENTINEL)
        if not before:
            return {"system": "inspeximus", "verdict": "NOT_COMPUTABLE",
                    "why": "PRECONDITION FAILED: value never reached disk."}
        m.forget_subject("hr/alice")
        after = sentinel_on_disk(workdir, SENTINEL)
        return {"system": "inspeximus", "stored_at_all": True,
                "files_before": before, "files_after": after,
                "verdict": "VALUE REMAINS ON DISK" if after else "VALUE REMOVED"}
    except Exception as e:
        return {"system": "inspeximus", "verdict": "NOT_COMPUTABLE",
                "why": f"{type(e).__name__}: {str(e)[:160]}"}


def arm_noop_control(workdir: str) -> dict:
    """THE FALSIFICATION CONTROL. A store whose 'delete' does nothing at all must be reported as
    retaining the value. If this arm ever says REMOVED, the cell is measuring nothing and every
    other verdict in the run is void."""
    p = os.path.join(workdir, "noop.txt")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(f"recovery phrase {SENTINEL}\n")
    before = sentinel_on_disk(workdir, SENTINEL)
    # the "delete": a no-op, exactly as a broken adapter would behave
    after = sentinel_on_disk(workdir, SENTINEL)
    return {"system": "NO-OP CONTROL", "stored_at_all": bool(before),
            "verdict": "VALUE REMAINS ON DISK" if after else "VALUE REMOVED",
            "expected": "VALUE REMAINS ON DISK"}


async def main():
    print(f"sentinel: {SENTINEL}\n")
    results = []
    for name, fn in (("noop", arm_noop_control), ("inspeximus", arm_inspeximus),
                     ("wmm", arm_world_model_mcp)):
        d = tempfile.mkdtemp(prefix=f"erasure_{name}_")
        try:
            r = await fn(d) if asyncio.iscoroutinefunction(fn) else fn(d)
        finally:
            shutil.rmtree(d, ignore_errors=True)
        results.append(r)

    for r in results:
        print(f"--- {r['system']}")
        print(f"    verdict: {r['verdict']}")
        if r.get("why"):
            print(f"    {r['why']}")
        if r.get("files_after") is not None:
            print(f"    files holding the value after delete: {r['files_after'] or 'none'}")
    ctrl = next(r for r in results if r["system"] == "NO-OP CONTROL")
    ok = ctrl["verdict"] == ctrl["expected"]
    print(f"\nCONTROL {'PASSED' if ok else 'FAILED'} — "
          f"{'a no-op delete is correctly reported as retaining the value.' if ok else
             'the cell cannot detect retention; every verdict above is VOID.'}")


asyncio.run(main())
