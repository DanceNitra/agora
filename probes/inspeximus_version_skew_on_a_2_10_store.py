"""Does an OLDER inspeximus mishandle a store written by 2.10.0? Run with the 2.9.1 interpreter.

WHY. SECURITY.md documents "MIXED LIBRARY VERSIONS ON ONE STORE FILE SILENTLY LOSE WRITES" as a known
footgun. 2.10.0 shipped hours ago and adds things an older reader has never seen:

  * two new record statuses, `provisional` (written but unretrievable until confirmed) and
    `discarded` (a verifier rejected it),
  * `confirmed_by` / `confirmed_at` on a confirmed record,
  * `amend_reason` inside the receipt hash preimage.

Each is a question an older reader answers by itself, and the answers are not obviously safe:

  Q1  Does 2.9.1 RETURN a provisional record from recall()? 2.10.0's whole guarantee is that an
      unconfirmed sentence -- "J." from a bad splitter -- never reaches a context window. If the old
      reader has no concept of the status, its recall filter may treat it as ordinary, and the
      guarantee lasts exactly as long as nobody opens the store with last month's version. That is
      not a hypothetical: an MCP server pinned by uvx to a cached archive is how this project already
      lost 290 records once.

  Q2  Does 2.9.1 SILENTLY DROP the new fields when it writes? If it round-trips a record and loses
      `confirmed_by`, or drops `amend_reason` from a receipt, the receipt hash no longer matches its
      own preimage and the chain breaks -- or worse, verifies against a weaker one.

  Q3  Does 2.9.1's verify_writes() report clean on a 2.10.0 chain it cannot fully re-derive?
      A verifier that cannot see a preimage field and says OK anyway is the vacuous pass this
      codebase keeps producing.

WHAT WOULD MAKE EACH ANSWER BAD, stated before running so the result cannot be rationalised after:
  Q1 bad = the provisional text appears in the old reader's recall output.
  Q2 bad = a field present before the old writer touches the store is absent after.
  Q3 bad = old verify_writes() returns True on a chain whose receipts carry a field it ignores.

This file is run by BOTH interpreters: `--write` with 2.10.0 to build the store, then plain with
2.9.1 to read it. It asserts nothing on its own; it prints what each version did.
"""
from __future__ import annotations

import json
import os
import sys

import inspeximus
from inspeximus import Inspeximus

STORE = os.path.join(os.environ.get("TEMP", "/tmp"), "vskew", "store.json")


def write_with_new() -> None:
    os.makedirs(os.path.dirname(STORE), exist_ok=True)
    for p in (STORE, STORE + ".receipts.json"):
        if os.path.exists(p):
            os.remove(p)
    ix = Inspeximus(path=STORE, receipts=True)
    a = ix.remember("The staging database is db-7.internal.", key="db.staging", mtype="semantic")
    a = a if isinstance(a, str) else a["id"]
    p = ix.remember("R. R. Tolkien was born in Bloemfontein", mtype="semantic", provisional=True)
    p = p if isinstance(p, str) else p["id"]
    c = ix.remember("A confirmed fragment", mtype="semantic", provisional=True)
    c = c if isinstance(c, str) else c["id"]
    ix.confirm(c, by="corroborated against the parent chunk")
    d = ix.remember("A rejected fragment", mtype="semantic", provisional=True)
    d = d if isinstance(d, str) else d["id"]
    ix.discard_provisional(d, basis="the splitter invented it")
    ix.slash([a], scope="memory", reason="corrected: wrong fixture")
    print(f"[2.10.0] wrote store: provisional={p} confirmed={c} discarded={d}")
    print(f"[2.10.0] verify_writes -> {ix.verify_writes()}")
    print(f"[2.10.0] recall sees provisional text: "
          f"{any('Bloemfontein' in (h.get('text') or '') for h in (ix.recall('Tolkien born') or []))}")


def read_with_old() -> None:
    print(f"[reader] inspeximus {inspeximus.__version__}")
    raw = json.load(open(STORE, encoding="utf-8"))
    items = raw if isinstance(raw, list) else (raw.get("items") or raw.get("records") or [])
    before = {r["id"]: dict(r) for r in items if isinstance(r, dict) and "id" in r}
    print(f"[reader] store on disk: {len(before)} record(s); statuses "
          f"{sorted({r.get('status') for r in before.values()})}")

    ix = Inspeximus(path=STORE, receipts=True)

    # Q1 -- does the old reader hand back a record 2.10.0 says must not be retrieved?
    hits = [h.get("text") or "" for h in (ix.recall("Tolkien born") or [])]
    leaked = any("Bloemfontein" in t for t in hits)
    print(f"\nQ1  provisional text returned by recall(): {leaked}"
          + ("   <-- LEAK: the guarantee does not survive an older reader" if leaked else "   ok"))
    for kw in ({"include_superseded": True}, {"as_of": 9e9}):
        h2 = [x.get("text") or "" for x in (ix.recall("Tolkien born", **kw) or [])]
        if any("Bloemfontein" in t for t in h2):
            print(f"     also visible with {kw}")

    # Q2 -- does an ordinary write by the old version drop the new fields?
    ix.remember("an ordinary write by the old version", mtype="semantic")
    try:
        ix._save(force=True)
    except Exception:
        pass
    raw2 = json.load(open(STORE, encoding="utf-8"))
    items2 = raw2 if isinstance(raw2, list) else (raw2.get("items") or raw2.get("records") or [])
    after = {r["id"]: dict(r) for r in items2 if isinstance(r, dict) and "id" in r}
    lost = []
    for rid, rec in before.items():
        if rid not in after:
            lost.append((rid, "RECORD GONE"))
            continue
        for k in ("status", "confirmed_by", "confirmed_at", "discard_basis"):
            if k in rec and k not in after[rid]:
                lost.append((rid, f"field '{k}' dropped"))
            elif k == "status" and rec.get(k) != after[rid].get(k):
                lost.append((rid, f"status {rec.get(k)!r} -> {after[rid].get(k)!r}"))
    print(f"\nQ2  fields/records lost by an old-version write: {len(lost)}")
    for rid, what in lost:
        print(f"     {rid}: {what}")

    # Q3 -- does the old verifier pass a chain carrying a field it does not know?
    try:
        v = ix.verify_writes()
    except Exception as e:
        v = f"raised {type(e).__name__}: {e}"
    print(f"\nQ3  old verify_writes() on a 2.10.0 chain -> {v}")
    rpath = STORE + ".receipts.json"
    if os.path.exists(rpath):
        rec = json.load(open(rpath, encoding="utf-8"))
        rl = rec if isinstance(rec, list) else (rec.get("receipts") or [])
        amend = [r for r in rl if isinstance(r, dict) and r.get("amends")]
        print(f"     receipts on disk: {len(rl)}, amending: {len(amend)}, "
              f"carrying amend_reason: {sum(1 for r in amend if 'amend_reason' in r)}")


if __name__ == "__main__":
    (write_with_new if "--write" in sys.argv else read_with_old)()
