"""Can a record written through the MCP server ever be erased by subject, or audited for lineage?

The MCP server is THE product surface -- it is how any Claude/Cursor/agent uses inspeximus as memory. Its
`remember` takes text, tags, value, mtype, key, object, reaffirm, and the three scope ids. It does NOT take
`source`, `derived_from`, `pii`, `derived`, `attestation` or `identity_confidence`.

Every compliance guarantee the README and docs/AI_ACT.md sell rides on the first two:

    forget_subject(subject)   selects by SOURCE, then cascades along derived_from
    erasure_audit(subject)    walks DECLARED derived_from edges; with none it returns `unaudited`
    slash(ids, scope=source)  forfeits the standing of a SOURCE

If a record written through MCP carries no source, then a DSAR through this surface reaches nothing, and
the audit that is supposed to notice reports on a store where nothing was ever declared. That is not a
"clean verdict about input never examined" in a single function -- it is the same shape one layer up, on
the surface the product is actually used through.

MEASURED, not inferred. Arms:
  P1  write via the MCP tool, then forget_subject on the obvious subject -> how many erased?
  P2  CONTROL: the identical write via the library WITH source -> must erase, else the probe proves nothing
  P3  what does erasure_audit say about the MCP-written store?
  P4  is there ANY MCP tool that can attach a source after the fact?
"""
import json
import os
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = r"C:\Users\Danculus\inspeximus-repo"
sys.path.insert(0, REPO)

os.environ["INSPEXIMUS_PATH"] = os.path.join(tempfile.mkdtemp(), "mcp.json")
from inspeximus import Inspeximus  # noqa: E402
import inspeximus.mcp_server as mcp  # noqa: E402

print("=== P1: a record written through the MCP tool ===")
out = mcp.remember("alice home address is 5 Elm St", key="addr::alice", object="5 Elm St")
print(f"   mcp.remember -> {json.dumps(out, default=str)[:160]}")

st = mcp._store() if hasattr(mcp, "_store") else Inspeximus(path=os.environ["INSPEXIMUS_PATH"])
for r in st.items:
    print(f"   stored record: source={r.get('source')!r} taint={r.get('taint')!r} "
          f"derived_from={r.get('derived_from')!r}")

for subj in ("alice", "hr/alice", "5 Elm St"):
    st2 = Inspeximus(path=os.environ["INSPEXIMUS_PATH"], receipts=True)
    res = st2.forget_subject(subj, request_id=f"dsar-{subj}", basis="art17", dry_run=True)
    print(f"   forget_subject({subj!r}, dry_run) -> would_erase={res['would_erase']}")

print("\n=== P2 CONTROL: the same write through the LIBRARY, with a source ===")
lib = Inspeximus(path=os.path.join(tempfile.mkdtemp(), "lib.json"), receipts=True)
lib.remember("alice home address is 5 Elm St", key="addr::alice", object="5 Elm St",
             source={"doc": "hr/alice"})
res = lib.forget_subject("hr/alice", request_id="dsar", basis="art17", dry_run=True)
print(f"   forget_subject('hr/alice', dry_run) -> would_erase={res['would_erase']}")
print("   -> must be 1. If it were 0 too, the probe would be measuring a broken fixture, not the surface.")

print("\n=== P3: what does the audit say about the MCP-written store? ===")
st3 = Inspeximus(path=os.environ["INSPEXIMUS_PATH"], receipts=True)
aud = st3.erasure_audit("alice")
print(f"   verdict={aud['verdict']!r}  coverage={aud['coverage']}")
print("   -> `unaudited` is the honest answer and the right one. The question is whether the PRODUCT")
print("      surface can ever produce a store where it is not the answer.")

print("\n=== P4: can any MCP tool attach provenance at all? ===")
names = [n for n in dir(mcp) if not n.startswith("_") and callable(getattr(mcp, n))]
hits = []
for n in names:
    try:
        import inspect
        params = list(inspect.signature(getattr(mcp, n)).parameters)
    except (TypeError, ValueError):
        continue
    prov = [p for p in params if p in ("source", "derived_from", "derived", "attestation", "pii")]
    if prov:
        hits.append((n, prov))
for n, prov in hits:
    print(f"   {n}: {prov}")
if not hits:
    print("   NONE. No MCP tool accepts source or derived_from, so no store written purely through the")
    print("   product surface can ever be subject-erased or lineage-audited.")
