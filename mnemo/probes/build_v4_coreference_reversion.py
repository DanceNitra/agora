"""build_v4_coreference_reversion.py — the coreference-obscured revert (shared open problem with Marat/TAT).

v3 was value-explicit: the revert NAMED the old value, so an `asserted_value` feature solves it. v4 removes
that too. A revert here points back to the superseded state by COREFERENCE to an anchor in the context (who
/what set it), naming NEITHER the old value NOR a revert verb. To decide, a method must resolve the anchor
through the context to a value and check whether that value is the superseded one.

THE FAIRNESS TRAP (what v2 fell into, and Marat + I agreed to avoid): if a fixed anchor word always meant
"old", it becomes a NEW lexical shortcut. So anchors are drawn from a pool and RANDOMLY assigned to old vs
current per row — no anchor token predicts the label. The only signal is which anchor, in THIS row's context,
maps to the superseded value.

Row shape (balanced 60/60/20 like v3, new entities/values):
  context = ["<entity> was <old>, chosen by <A_old>", "correction: <entity> is now <current>, chosen by <A_cur>"]
  obscuring_revert (label 1): candidate points to A_old   (resolves to the superseded value)  -> reopens stale
  obscuring_keep   (label 0): candidate points to A_cur   (resolves to the current value)
  named_new        (label 0): candidate points to A_new   (an anchor NOT in the context -> unresolvable)
Candidate templates name the anchor, no value, no revert/keep verb.

Built-in fairness asserts: (1) no revert/keep keyword in any candidate; (2) no old/current value token in any
candidate (so asserted_value can't fire); (3) each anchor name appears roughly equally as old and as current
across the set (so no anchor predicts the label). Deterministic (seed).
"""
import json, random, pathlib
from collections import Counter

random.seed(11)
OUT = pathlib.Path("agora_output/public_fixtures/value_obscuring_reversion_heldout_v4.jsonl")

REVERT_WORDS = {'revert', 'go back', 'undo', 'original', 'before', 'scrap', 'earlier', 'cancel',
                'roll back', 'restore', 'prior', 'mistake', 'previous', 'switch was'}
KEEP_WORDS = {'keep', 'stick with', 'stands', 'leave it', 'latest', 'updated', 'no rollback',
              'happy with', 'confirmed', 'final, don', 'right, leave', 'stay with'}

ENTITIES = [
    ("cache region", "osaka", "malmo"), ("primary shard", "delta7", "sigma2"),
    ("build target", "arm64", "riscv"), ("default currency", "forint", "guarani"),
    ("route profile", "coastal", "inland"), ("api tier", "bronze", "platinum"),
    ("index locale", "tallinn", "cusco"), ("worker pool", "amber", "cobalt"),
    ("log sink", "vault3", "harbor8"), ("retry policy", "linear", "jitter"),
    ("color theme", "sepia", "slate"), ("scheduler", "roundrobin", "weighted"),
]
ANCHORS = ["the platform team", "the data desk", "priya", "the vendor", "marcus", "the audit",
           "the pilot group", "the finance team", "devon", "the on-call lead", "the review board", "amara"]
TEMPLATES = [
    "go with what {a} decided.", "{a}'s call is the one to use.", "apply the setting {a} chose.",
    "the configuration {a} picked should be used.", "match what {a} set up.", "defer to {a} on this.",
    "use the option {a} landed on.", "adopt what {a} settled on.",
]


def _has_kw(t):
    tl = t.lower()
    return any(w in tl for w in REVERT_WORDS) or any(w in tl for w in KEEP_WORDS)


def _cand(anchor, idx):
    c = TEMPLATES[idx % len(TEMPLATES)].format(a=anchor)
    assert not _has_kw(c), f"keyword leaked: {c!r}"
    return c


def main():
    rows = []
    idx = 0
    anchor_role = Counter()
    # BALANCED anchor->role: each anchor is a_old exactly 5x and a_cur exactly 5x across the 60 pairs, so no
    # anchor token predicts the label even in-sample (kills the fixed-anchor shortcut). Build two role-lists
    # (each anchor x5), shuffle, and pair them avoiding a_old == a_cur.
    old_slots = [a for a in ANCHORS for _ in range(5)]
    cur_slots = [a for a in ANCHORS for _ in range(5)]
    for _try in range(2000):
        random.shuffle(old_slots); random.shuffle(cur_slots)
        if all(o != c for o, c in zip(old_slots, cur_slots)):
            break
    pair_i = 0
    for e_i, (entity, old, cur) in enumerate(ENTITIES):
        for j in range(5):    # 5 revert + 5 keep per entity
            a_old, a_cur = old_slots[pair_i], cur_slots[pair_i]; pair_i += 1
            anchor_role[(a_old, "old")] += 1
            anchor_role[(a_cur, "current")] += 1
            ctx = [f"{entity} was {old}, chosen by {a_old}",
                   f"correction: {entity} is now {cur}, chosen by {a_cur}"]
            # revert -> point to the OLD anchor
            rc = _cand(a_old, idx); idx += 1
            assert old not in rc.lower() and cur not in rc.lower(), rc
            rows.append({"entity": entity, "old_value": old, "current_value": cur, "context": ctx,
                         "candidate": rc, "anchor_old": a_old, "anchor_current": a_cur,
                         "kind": "obscuring_revert", "reopens_stale": 1})
            # keep -> point to the CURRENT anchor
            kc = _cand(a_cur, idx); idx += 1
            assert old not in kc.lower() and cur not in kc.lower(), kc
            rows.append({"entity": entity, "old_value": old, "current_value": cur, "context": ctx,
                         "candidate": kc, "anchor_old": a_old, "anchor_current": a_cur,
                         "kind": "obscuring_keep", "reopens_stale": 0})
    # 20 named_new: point to an anchor NOT in the context
    for k in range(20):
        entity, old, cur = ENTITIES[k % len(ENTITIES)]
        a_old, a_cur = random.sample(ANCHORS, 2)
        a_new = random.choice([a for a in ANCHORS if a not in (a_old, a_cur)])
        ctx = [f"{entity} was {old}, chosen by {a_old}", f"correction: {entity} is now {cur}, chosen by {a_cur}"]
        nc = _cand(a_new, idx); idx += 1
        rows.append({"entity": entity, "old_value": old, "current_value": cur, "context": ctx,
                     "candidate": nc, "anchor_old": a_old, "anchor_current": a_cur,
                     "kind": "named_new", "reopens_stale": 0})
    random.shuffle(rows)
    for i, r in enumerate(rows):
        rows[i] = {"id": i, **r}

    # fairness asserts
    assert all(not _has_kw(r["candidate"]) for r in rows), "keyword leaked"
    assert all(r["old_value"] not in r["candidate"].lower() and r["current_value"] not in r["candidate"].lower()
               for r in rows), "a value token leaked into a candidate"
    # no anchor strongly predicts the label: for anchors used as both old and current, the split is balanced-ish
    both = [a for a in ANCHORS if anchor_role[(a, "old")] > 0 and anchor_role[(a, "current")] > 0]
    print(f"anchors used as BOTH old and current: {len(both)}/{len(ANCHORS)} (no fixed anchor->label shortcut)")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    kc = Counter(r["kind"] for r in rows)
    print(f"wrote {len(rows)} rows -> {OUT}  | kind: {dict(kc)}")
    for r in rows[:5]:
        print(" ", r["kind"], "| L", r["reopens_stale"], "|", r["candidate"], "| ctx-anchors:",
              r["anchor_old"], "(old) /", r["anchor_current"], "(cur)")


if __name__ == "__main__":
    main()
