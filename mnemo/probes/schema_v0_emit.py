"""Reference emitter: a real mnemo record -> the schema_v0 fact-record interchange (mnemo/schema_v0.json).

Makes the DanceNitra/agora Discussion #2 contract (mnemo write-side -> a bitemporal read-side ledger,
e.g. MemStrata / arXiv:2606.26511) runnable and HONEST: it shows exactly which schema_v0 fields mnemo
stores directly vs derives, so the claim "mnemo emits schema_v0" is checkable, not asserted.

Field provenance (verified against mnemo.py):
  STORED directly on a mnemo record : id, valid_from, ts (-> recorded_at), key, text, source, mtype, status, links
  DERIVED here                      : subject/relation  = key.split("::")               (key is the stored "subject::relation")
                                      sources[]         = this record's source + its corroborating links' sources, deduped
                                      corroboration_count = number of DISTINCT sources (record + links)
                                      effective_value   = mnemo._effective_value(record, now)  (value * 0.5^(age/half_life), clock reset on access)
  NOT stored separately             : object  -> null. mnemo keys on (subject, relation) but keeps the VALUE in `text`,
                                      it does not store a separate object slot. The reader takes the value from `text`.

Zero deps beyond mnemo (+ numpy if the store has vectors). MIT. Run: python mnemo/probes/schema_v0_emit.py
"""
import sys, os, json, time

try:
    from mnemo import Mnemo
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from mnemo import Mnemo


def _norm_source(src):
    """mnemo stores a single `source` dict (or str) per record. Normalize to {channel, principal}."""
    if not src:
        return None
    if isinstance(src, dict):
        principal = (src.get("principal") or src.get("doc") or src.get("id")
                     or json.dumps(src, sort_keys=True))
        channel = src.get("channel") or ("doc" if src.get("doc") else "unknown")
    else:
        principal, channel = str(src), "unknown"
    return {"channel": channel, "principal": str(principal)}


def emit_schema_v0(m: "Mnemo", record: dict) -> dict:
    """Serialize ONE mnemo record to a schema_v0 payload. Corroboration = this record's source plus the
    sources of its corroborating links, entity-deduped by principal (mirrors mnemo's _distinct_sources)."""
    by_id = {r["id"]: r for r in m.items}
    key = record.get("key")
    subject, relation = (key.split("::", 1) + [None])[:2] if key else (None, None)

    sources, seen = [], set()
    for src in [record.get("source")] + [by_id[l].get("source") for l in record.get("links", []) if l in by_id]:
        ns = _norm_source(src)
        if ns and ns["principal"] not in seen:
            seen.add(ns["principal"]); sources.append(ns)

    return {
        "version": "schema_v0",
        "fact_record": {
            "id": record["id"],
            "valid_from": record.get("valid_from", record["ts"]),   # STORED (event / valid-time)
            "recorded_at": record["ts"],                            # STORED as ts (ingest / system-time)
            "key": key,                                             # STORED ("subject::relation")
            "subject": subject,                                     # DERIVED from key
            "relation": relation,                                   # DERIVED from key
            "object": None,                                         # NOT stored separately (value lives in text)
            "text": record["text"],                                 # STORED (carries the value)
            "sources": sources,                                     # DERIVED (record + linked sources, deduped)
            "corroboration_count": len(sources),                   # DERIVED (distinct sources)
            "effective_value": round(m._effective_value(record, time.time()), 4),  # DERIVED (decayed value)
            "mtype": record.get("mtype"),                          # STORED
            "status": record["status"],                            # STORED (mnemo's local view)
        },
    }


def _demo():
    """A real mnemo write with a key + a corroborating linked record, serialized to schema_v0."""
    m = Mnemo()
    # primary fact (keyed) with a source
    fid = m.remember("The billing API authenticates with API keys.",
                     key="billing-api::auth-method", mtype="semantic",
                     source={"channel": "doc", "principal": "runbook#auth"})
    # a second, independent corroborating record, linked to the primary
    cid = m.remember("Billing API auth is done via API keys per the KMS rotation job.",
                     mtype="semantic", source={"channel": "tool", "principal": "kms:rotate-job"})
    primary = next(r for r in m.items if r["id"] == fid)
    primary["links"] = [cid]                                        # corroboration link (what consolidate() would set)

    payload = emit_schema_v0(m, primary)
    print("=== schema_v0 emitter: a real mnemo record -> the interchange payload ===\n")
    print(json.dumps(payload, indent=2))
    # validate against the pinned schema if jsonschema is available (optional; skipped cleanly if absent)
    try:
        import jsonschema  # noqa
        here = os.path.dirname(__file__)
        schema = json.load(open(os.path.join(here, "..", "schema_v0.json"), encoding="utf-8"))
        jsonschema.validate(payload, schema)
        print("\n[validate] payload conforms to mnemo/schema_v0.json")
    except ImportError:
        print("\n[validate] jsonschema not installed - skipped (payload shape shown above)")
    except Exception as e:
        print(f"\n[validate] SCHEMA MISMATCH: {e}")


if __name__ == "__main__":
    _demo()
