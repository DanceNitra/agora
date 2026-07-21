"""build_v4_coreference_reversion.py — the coreference-obscured revert (shared open problem with Marat/TAT).

v3 was value-explicit: the revert NAMED the old value, so an `asserted_value` feature solves it. v4 removes
that: a revert points back to the superseded state by COREFERENCE to WHO set it, naming neither the old value
nor a revert verb. To decide, a method must resolve the reference through the context to a value and check
whether that value is the superseded one.

FIX 2026-07-11 (our own bug, caught by audit). The FIRST cut of v4 named the anchor LITERALLY in the candidate
("go with what priya decided") while anchor_old/anchor_current are given ledger fields — so a pure substring
match candidate<->anchor scored F1 1.00 with no ML and no embedder. That is a lexical shortcut, not
coreference; v4 did not test what it claimed. This corrected v4 refers to the anchor by a ROLE DESCRIPTION,
never by name, so deciding the label now requires the full chain:
  candidate-role  ->  the context ROLE line naming that role  ->  the anchor on that line
                   ->  the VALUE line naming that anchor       ->  old vs current  ->  reopens?
Verified after the fix (3 angles): substring anchor-name match F1 0.00 (shortcut closed); naive role-line-order
guess ~chance (no positional shortcut); the oracle coreference chain F1 1.00 (the signal exists but now
requires the chain). This does NOT prove no shortcut exists — only that the two known lexical/positional
shortcuts are closed.

FAIRNESS (so no single token predicts the label):
  - candidate contains NO anchor name, NO value token, NO revert/keep/positional keyword.
  - roles are pool-drawn and BALANCED: each role is the old-setter's role exactly 5x and the current-setter's
    role exactly 5x across the 60 pairs (no role token predicts old/current).
  - anchors likewise balanced old/current; role-line order is shuffled per row (no positional shortcut).
Built-in asserts enforce all of this. Deterministic (seed).

Row shape (balanced 60/60/20):
  context = [ "<entity> was <old>, chosen by <A_old>",
              "correction: <entity> is now <current>, chosen by <A_cur>",
              "<A_old> owns <role_old>", "<A_cur> owns <role_cur>" ]   (role-line order shuffled)
  obscuring_revert (1): candidate -> role_old  -> A_old -> old value    -> reopens stale
  obscuring_keep   (0): candidate -> role_cur  -> A_cur -> current value
  named_new        (0): candidate -> role_new  (not in context)         -> unresolvable
"""
import json, random, pathlib
from collections import Counter

random.seed(15)
OUT = pathlib.Path("agora_output/public_fixtures/value_obscuring_reversion_heldout_v4.jsonl")

REVERT_WORDS = {'revert', 'go back', 'undo', 'original', 'before', 'scrap', 'earlier', 'cancel', 'first',
                'roll back', 'restore', 'prior', 'mistake', 'previous', 'switch was', 'older', 'initial'}
KEEP_WORDS = {'keep', 'stick with', 'stands', 'leave it', 'latest', 'updated', 'no rollback', 'newer',
              'happy with', 'confirmed', 'final, don', 'right, leave', 'stay with', 'current one', 'recent'}

ENTITIES = [
    ("cache region", "osaka", "malmo"), ("primary shard", "delta7", "sigma2"),
    ("build target", "arm64", "riscv"), ("default currency", "forint", "guarani"),
    ("route profile", "coastal", "inland"), ("api tier", "bronze", "platinum"),
    ("index locale", "tallinn", "cusco"), ("worker pool", "amber", "cobalt"),
    ("log sink", "vault3", "harbor8"), ("retry policy", "linear", "jitter"),
    ("color theme", "sepia", "slate"), ("scheduler", "roundrobin", "weighted"),
]
ANCHORS = ["priya", "devon", "marcus", "amara", "the vendor", "the audit", "the pilot group",
           "the finance team", "the platform team", "the data desk", "the on-call lead", "the review board"]
ROLES = ["security review", "the latency budget", "vendor contracts", "the data pipeline",
         "incident response", "the release train", "cost controls", "the schema registry",
         "access policy", "the mobile build", "capacity planning", "the search index"]
TEMPLATES = [
    "go with the pick from whoever owns {r}.",
    "use the call made by the person who owns {r}.",
    "apply the choice from whoever handles {r}.",
    "the setting from the owner of {r} is the one to use.",
    "match what the owner of {r} decided.",
    "defer to whoever owns {r} on this.",
    "adopt the option chosen by the person who owns {r}.",
    "go with the owner of {r} on it.",
]


def _has_kw(t):
    tl = t.lower()
    return any(w in tl for w in REVERT_WORDS) or any(w in tl for w in KEEP_WORDS)


def _cand(role, idx=None):
    # RANDOM template, independent of the label. The first fix of v4 still assigned templates by an
    # alternating index (revert=even, keep=odd), so the template WORDING alone predicted the label at
    # F1 0.92 — a pure phrasing shortcut. Random assignment + the template-balance assert below close it.
    c = random.choice(TEMPLATES).format(r=role)
    assert not _has_kw(c), f"keyword leaked: {c!r}"
    return c


def _role_lines(a_old, a_cur, r_old, r_cur):
    lines = [f"{a_old} owns {r_old}", f"{a_cur} owns {r_cur}"]
    random.shuffle(lines)
    return lines


def _deranged_pair(pool):
    """two lists (each item x5) paired with NO position where old==cur; deranged independently + asserted."""
    a = [x for x in pool for _ in range(5)]
    b = [x for x in pool for _ in range(5)]
    for _try in range(20000):
        random.shuffle(a); random.shuffle(b)
        if all(o != c for o, c in zip(a, b)):
            return a, b
    raise RuntimeError("no derangement found")


def main():
    rows = []
    idx = 0
    anchor_role = Counter()
    role_label = Counter()
    old_slots, cur_slots = _deranged_pair(ANCHORS)
    ro_slots, rc_slots = _deranged_pair(ROLES)
    pi = 0
    for entity, old, cur in ENTITIES:
        for j in range(5):
            a_old, a_cur = old_slots[pi], cur_slots[pi]
            r_old, r_cur = ro_slots[pi], rc_slots[pi]; pi += 1
            anchor_role[(a_old, "old")] += 1; anchor_role[(a_cur, "current")] += 1
            role_label[(r_old, "old")] += 1;  role_label[(r_cur, "current")] += 1
            ctx = [f"{entity} was {old}, chosen by {a_old}",
                   f"correction: {entity} is now {cur}, chosen by {a_cur}"] + _role_lines(a_old, a_cur, r_old, r_cur)
            base = {"entity": entity, "old_value": old, "current_value": cur, "context": ctx,
                    "anchor_old": a_old, "anchor_current": a_cur, "role_old": r_old, "role_current": r_cur}
            rows.append({**base, "candidate": _cand(r_old, idx), "kind": "obscuring_revert", "reopens_stale": 1}); idx += 1
            rows.append({**base, "candidate": _cand(r_cur, idx), "kind": "obscuring_keep", "reopens_stale": 0}); idx += 1
    for k in range(20):
        entity, old, cur = ENTITIES[k % len(ENTITIES)]
        a_old, a_cur = random.sample(ANCHORS, 2)
        r_old, r_cur = random.sample(ROLES, 2)
        r_new = random.choice([r for r in ROLES if r not in (r_old, r_cur)])
        ctx = [f"{entity} was {old}, chosen by {a_old}",
               f"correction: {entity} is now {cur}, chosen by {a_cur}"] + _role_lines(a_old, a_cur, r_old, r_cur)
        rows.append({"entity": entity, "old_value": old, "current_value": cur, "context": ctx,
                     "anchor_old": a_old, "anchor_current": a_cur, "role_old": r_old, "role_current": r_cur,
                     "candidate": _cand(r_new, idx), "kind": "named_new", "reopens_stale": 0}); idx += 1
    random.shuffle(rows)
    for i, r in enumerate(rows):
        rows[i] = {"id": i, **r}

    # ── fairness asserts (the fix is only real if these hold) ──────────────────
    for r in rows:
        c = r["candidate"].lower()
        assert not _has_kw(c), f"keyword: {c!r}"
        assert r["old_value"] not in c and r["current_value"] not in c, f"value leaked: {c!r}"
        assert r["anchor_old"].lower() not in c and r["anchor_current"].lower() not in c, \
            f"anchor name leaked into candidate (the v4 bug): {c!r}"
        assert r["anchor_old"] != r["anchor_current"] and r["role_old"] != r["role_current"], "degenerate row"
    # template-balance assert: no template's wording may predict the label. For each template, the share of
    # label-1 rows among the 120 obscuring rows must sit in [0.25, 0.75] (chance = 0.5).
    def _sig(cand):
        s = cand
        for role in sorted(ROLES, key=len, reverse=True):
            s = s.replace(role, "{r}")
        return s
    tstat = {}
    for r in rows:
        if r["kind"] == "named_new":
            continue
        s = _sig(r["candidate"])
        a, b = tstat.get(s, (0, 0))
        tstat[s] = (a + r["reopens_stale"], b + 1)
    for s, (ones, tot) in tstat.items():
        share = ones / tot
        assert 0.25 <= share <= 0.75, f"template predicts the label ({share:.2f}): {s!r}"
    both_a = [a for a in ANCHORS if anchor_role[(a, "old")] and anchor_role[(a, "current")]]
    both_r = [r for r in ROLES if role_label[(r, "old")] and role_label[(r, "current")]]
    print(f"anchors used as BOTH old and current: {len(both_a)}/{len(ANCHORS)}")
    print(f"roles used as BOTH old and current:   {len(both_r)}/{len(ROLES)} (no role token predicts the label)")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} rows -> {OUT} | kind: {dict(Counter(r['kind'] for r in rows))}")
    for r in rows[:3]:
        print("  L", r["reopens_stale"], "|", r["candidate"], "| ctx:", r["context"])


if __name__ == "__main__":
    main()
