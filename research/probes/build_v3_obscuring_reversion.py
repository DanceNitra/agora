"""build_v3_obscuring_reversion.py — a FAIR, harder held-out for value-obscuring reversion.

WHY v3. v2 (value_obscuring_reversion_heldout_v2.jsonl) is memorization-proof on ENTITIES/VALUES
(new phrasings, new entities) but it is LEXICALLY separable: every obscuring_revert candidate carries
explicit revert vocabulary ("restore the previous", "roll it back originally", "prior configuration"),
so a 27-word keyword list scores F1 1.0 with NO model (measured). That means AUROC 1.0 on v2 proves
LEXICAL recall of revert verbs, not a structural invariant.

v3 removes the lexical shortcut and tests the RIGHT signal: VALUE IDENTITY. Every candidate is a plain
assignment that NAMES a value, with NO revert/keep verb. The class is decided only by WHICH value is
re-asserted relative to the ledger:
  obscuring_revert -> re-asserts the OLD (already-superseded) value  -> reopens_stale = 1
  obscuring_keep   -> re-asserts the CURRENT (active) value          -> reopens_stale = 0
  named_new        -> asserts a genuinely NEW value                  -> reopens_stale = 0
Revert and keep share the SAME phrasings and differ ONLY by the value token, so no surface cue exists.
A method must recover the asserted value and compare it to the ledger. This is fair to everyone: a
genuine structural feature (value identity) passes; a lexical keyword feature cannot; inspeximus's
object-ledger passes by design (it keys on the object, not the phrasing).

Balanced 140 to mirror v2: 60 revert / 60 keep / 20 named_new. New entities/values (memorization-proof).
Built-in safety asserts: (1) NO candidate contains any of Marat's revert/keep keywords; (2) the asserted
value token IS present in the candidate (so a value-matcher CAN win). Deterministic (fixed seed).
"""
import json, random, pathlib

random.seed(7)
OUT = pathlib.Path("agora_output/public_fixtures/value_obscuring_reversion_heldout_v3.jsonl")

# Marat's keyword lists (test_on_v2.py) — v3 candidates must contain NONE of these.
REVERT_WORDS = {'revert', 'go back', 'undo', 'original', 'before', 'scrap', 'earlier', 'cancel',
                'roll back', 'restore', 'prior', 'mistake', 'previous', 'switch was'}
KEEP_WORDS = {'keep', 'stick with', 'stands', 'leave it', 'latest', 'updated', 'no rollback',
              'happy with', 'confirmed', 'final, don', 'right, leave', 'stay with'}

# new entities with (old, current) values — none reuse v2's search-replica/lyon/quito
ENTITIES = [
    ("cache region", "osaka", "malmo", "reykjavik"),
    ("primary shard", "delta7", "sigma2", "omega9"),
    ("build target", "arm64", "riscv", "wasm32"),
    ("default currency", "forint", "guarani", "kwacha"),
    ("route profile", "coastal", "inland", "alpine"),
    ("api tier", "bronze", "platinum", "obsidian"),
    ("index locale", "tallinn", "cusco", "hobart"),
    ("worker pool", "amber", "cobalt", "saffron"),
    ("log sink", "vault3", "harbor8", "atlas1"),
    ("retry policy", "linear", "jitter", "fibonacci"),
    ("color theme", "sepia", "slate", "verdant"),
    ("scheduler", "roundrobin", "weighted", "lottery"),
]

# plain assignment templates that NAME a value and carry NO revert/keep verb.
TEMPLATES = [
    "set {e} to {v}.",
    "{e} should be {v}.",
    "make {e} {v}.",
    "point {e} at {v}.",
    "{v} is the value for {e}.",
    "configure {e} as {v}.",
    "put {e} on {v}.",
    "let's use {v} for {e}.",
    "{e}: {v}.",
    "i'd have {e} at {v}.",
]


def _has_kw(text):
    t = text.lower()
    return any(w in t for w in REVERT_WORDS) or any(w in t for w in KEEP_WORDS)


def _mk(entity, old, cur, val, kind, label, idx):
    tmpl = TEMPLATES[idx % len(TEMPLATES)]
    cand = tmpl.format(e=entity, v=val)
    assert not _has_kw(cand), f"keyword leaked into candidate: {cand!r}"
    assert val.lower() in cand.lower(), f"value token missing from candidate: {cand!r}"
    return {"entity": entity, "old_value": old, "current_value": cur,
            "context": [f"{entity} is {old}", f"correction: {entity} is now {cur}"],
            "candidate": cand, "kind": kind, "reopens_stale": label}


def main():
    rows = []
    # 60 revert + 60 keep: 5 of each per entity across 12 entities; varied templates
    for e_i, (entity, old, cur, new) in enumerate(ENTITIES):
        for j in range(5):
            rows.append(_mk(entity, old, cur, old, "obscuring_revert", 1, e_i * 5 + j))
            rows.append(_mk(entity, old, cur, cur, "obscuring_keep", 0, e_i * 5 + j + 3))
    # 20 named_new (asserts a brand-new value, not old/current) across the first 20 slots
    for k in range(20):
        entity, old, cur, new = ENTITIES[k % len(ENTITIES)]
        rows.append(_mk(entity, old, cur, new, "named_new", 0, k + 1))
    random.shuffle(rows)
    for i, r in enumerate(rows):
        r_id = {"id": i}; r_id.update(r); rows[i] = r_id

    # summary + safety verification
    from collections import Counter
    kc = Counter(r["kind"] for r in rows); lc = Counter(r["reopens_stale"] for r in rows)
    assert kc["obscuring_revert"] == 60 and kc["obscuring_keep"] == 60 and kc["named_new"] == 20
    assert all(not _has_kw(r["candidate"]) for r in rows), "a keyword leaked"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} rows -> {OUT}")
    print("kind:", dict(kc), "| label:", dict(lc))
    print("keyword-safety: 0 candidates contain any revert/keep keyword (asserted).")
    print("value-present:  every candidate names its asserted value (asserted).")
    for r in rows[:6]:
        print("  ", r["kind"], "| L", r["reopens_stale"], "|", r["candidate"])


if __name__ == "__main__":
    main()
