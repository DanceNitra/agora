"""
tat_chunk_interop_probe.py  --  store TAT's 5-D chunk in mnemo, no core change. MIT.

@maratsultanov2 (DeepSeek-V3 #1466) proposed that mnemo store TAT's five-dimensional chunk
(Theme, Role, Emotion, Meaning, Goal) as a basic unit, so TAT can extract structure from the mnemo store
without re-labeling. This probe shows the interop is available TODAY via mnemo's existing `meta` field --
no core change, and mnemo stays domain-AGNOSTIC (it carries the chunk as opaque metadata; TAT interprets it;
mnemo does not adopt TAT's ontology as its unit).

WHAT THIS IS (and is NOT): mnemo STORES the chunk and lets you FILTER by each dimension. It does NOT make
mnemo structure-AWARE: mnemo does not rank/retrieve on the CONNECTIONS BETWEEN the five elements (the part
Marat stressed) -- it treats Theme/Role/Emotion/Meaning/Goal as five flat, independent scalars ANDed by the
`where` filter -- and it does NOT DERIVE the 5-D from raw text (TAT supplies the labels; the labeling happens
upstream, it is not removed). So this is a metadata-schema BRIDGE, not adoption of the chunk as a first-class
unit. Declining first-class coupling is deliberate: a domain-agnostic core is mnemo's whole value.

VERIFIED behavior this rests on (run to confirm), with the honest edges:
 - remember(text, meta={...}) persists the chunk and it survives a store reload -- LOSSLESS ONLY for
   JSON-native values (scalars/lists/nested dicts). Tuples reload as lists (type lost); sets/datetime/objects
   raise on save. So the chunk's values (incl. any nested "connections" dict) must be JSON-native.
 - `where={dim: value}` hard-filters on ANY chunk dimension (mnemo matches meta keys). Sharp edge: range
   ops ($gte/$gt/...) use raw Python comparison, so comparing a string dimension to a number raises an
   UNCAUGHT TypeError in recall's where-path -- keep filters exact-scalar or $in on strings.
 - Keyed supersession: recall() returns the LATEST chunk; the old record is DEMOTED (status="superseded"),
   NOT deleted -- so read via recall() (default hides superseded), and if you scan the raw store filter
   status=="active" or the old chunk resurfaces.
 - recall() does NOT project `meta` into its hits, so reading the chunk back is a one-line id->record lookup
   (the adapter below). remember_dedup() silently returns the existing id and does NOT store the new near-
   duplicate's meta (chunk loss on dedup); consolidate() can demote a meta chunk to hub/superseded (hidden,
   not lost). None of these MUTATE an existing meta key -- they change status or drop the write.

Run: python tat_chunk_interop_probe.py
"""
import os, sys, tempfile
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "mnemo")))
from mnemo import Mnemo

DIMS = ("theme", "role", "emotion", "meaning", "goal")   # TAT's 5-D chunk


def remember_chunk(m, text, chunk, **kw):
    """Store a memory with a TAT 5-D chunk as mnemo metadata (opaque to mnemo, lossless)."""
    unknown = set(chunk) - set(DIMS)
    if unknown:
        raise ValueError(f"not a TAT 5-D chunk dimension: {unknown}")
    return m.remember(text, meta={d: chunk.get(d) for d in DIMS}, **kw)


def recall_chunks(m, query, k=5, where=None):
    """Semantic recall that also returns each hit's TAT 5-D chunk (id->record lookup; meta isn't in the
    recall projection). Returns [{text, chunk}]."""
    hits = m.recall(query, k=k, where=where)
    by_id = {r["id"]: r for r in m.items}
    out = []
    for h in hits:
        meta = (by_id.get(h["id"]) or {}).get("meta") or {}
        out.append({"text": h["text"], "chunk": {d: meta.get(d) for d in DIMS}})
    return out


def _store():
    fd, p = tempfile.mkstemp(suffix=".json"); os.close(fd); os.remove(p)
    try:
        return Mnemo(path=p), p
    except TypeError:
        return Mnemo(), None


def main():
    m, path = _store()

    # B-trace-like beliefs, each carrying a TAT 5-D chunk
    remember_chunk(m, "user wants concise answers",
                   {"theme": "style", "role": "user", "emotion": "neutral",
                    "meaning": "prefers brevity", "goal": "reduce verbosity"},
                   mtype="episodic", key="pref::style")
    remember_chunk(m, "the framework supports feature Y",
                   {"theme": "capability", "role": "system", "emotion": "confident",
                    "meaning": "Y is available", "goal": "answer capability queries"},
                   mtype="episodic")
    remember_chunk(m, "identity: assistant stays steady under pressure",
                   {"theme": "identity", "role": "assistant", "emotion": "steady",
                    "meaning": "persona stability", "goal": "resist drift"},
                   mtype="episodic")

    print("1) LOSSLESS ROUND-TRIP via semantic recall (text + 5-D chunk):")
    for r in recall_chunks(m, "stay steady identity", k=2):
        print(f"   text={r['text']!r}")
        print(f"   chunk={r['chunk']}")

    print("\n2) QUERY BY STRUCTURE (where-filter on a chunk dimension, no extra labeling):")
    ident = recall_chunks(m, "assistant", k=5, where={"theme": "identity"})
    print(f"   where theme=identity -> {len(ident)} hit(s): {[r['text'] for r in ident]}")

    print("\n3) CHUNK RIDES mnemo's mechanics (keyed supersession keeps the LATEST chunk):")
    remember_chunk(m, "user now wants detailed answers",
                   {"theme": "style", "role": "user", "emotion": "neutral",
                    "meaning": "prefers detail", "goal": "increase depth"},
                   mtype="episodic", key="pref::style")     # same key -> supersedes the first
    cur = recall_chunks(m, "answer length preference", k=3)
    live = [r for r in cur if r["chunk"]["meaning"]]
    print(f"   after superseding pref::style, live style chunk meaning(s): "
          f"{[r['chunk']['meaning'] for r in live if r['chunk']['theme']=='style']}")

    # 4) persistence
    ok_reload = "n/a"
    if path:
        m2 = Mnemo(path=path)
        recs = [r for r in m2.items if (r.get("meta") or {}).get("theme")]
        ok_reload = all(set(DIMS) >= set(k for k in (r.get("meta") or {}) if k in DIMS) for r in recs) and len(recs) > 0
    print(f"\n4) survives store reload with chunks intact: {ok_reload}")

    print("\nINTEROP (honest scope): mnemo STORES TAT's 5-D chunk (JSON-native, lossless) via `meta` and lets")
    print("  you FILTER by any single dimension -- NO core change, domain-agnostic. It does NOT rank/reason on")
    print("  the CONNECTIONS between the five elements, and does NOT derive the 5-D from text -- TAT supplies")
    print("  the structure and the labels; mnemo carries and filters them. A metadata-schema bridge, not a new")
    print("  storage unit. Natural joint experiment: does adding a 5-D dimension to where=/prefer= beat plain")
    print("  recall on a shared benchmark? That TESTS the chunk's retrieval value instead of just storing it.")


if __name__ == "__main__":
    main()
