"""eval_v3_three_methods.py — run keyword-rule, Marat's Triplenet-5D, inspeximus echo_guard, and a
value-identity oracle on the v3 held-out. Shows v3 is FAIR (structurally solvable) but not lexically.

Run: python research/probes/eval_v3_three_methods.py
(Marat's model arm needs stable_triplenet.pt reachable via --pt; skipped with a note if absent.)
"""
import json, sys, pathlib, argparse
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from inspeximus import Inspeximus

V3 = "agora_output/public_fixtures/value_obscuring_reversion_heldout_v3.jsonl"
REVERT_WORDS = {'revert', 'go back', 'undo', 'original', 'before', 'scrap', 'earlier', 'cancel',
                'roll back', 'restore', 'prior', 'mistake', 'previous', 'switch was'}
KEEP_WORDS = {'keep', 'stick with', 'stands', 'leave it', 'latest', 'updated', 'no rollback',
              'happy with', 'confirmed', 'final, don', 'right, leave', 'stay with'}


def load(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def scores(y, pred):
    tp = sum(1 for a, b in zip(y, pred) if a == 1 and b == 1)
    fp = sum(1 for a, b in zip(y, pred) if a == 0 and b == 1)
    tn = sum(1 for a, b in zip(y, pred) if a == 0 and b == 0)
    fn = sum(1 for a, b in zip(y, pred) if a == 1 and b == 0)
    acc = (tp + tn) / len(y)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return dict(acc=acc, prec=prec, rec=rec, f1=f1, tp=tp, fp=fp, tn=tn, fn=fn)


def asserted_value(row):
    """The value the candidate NAMES (light, phrasing-independent extractor): whichever known value
    string appears in the candidate. Fair to all methods — no revert-verb lexicon involved."""
    c = row["candidate"].lower()
    for v in (row["old_value"], row["current_value"]):
        if v.lower() in c:
            return "old" if v == row["old_value"] else "current"
    return "new"   # a value that is neither old nor current => a genuinely new assignment


def kw_rule(rows):
    """Marat's `emotion` keyword feature as a classifier: revert-word present & no keep-word -> reopen."""
    out = []
    for r in rows:
        c = r["candidate"].lower()
        out.append(1 if (any(w in c for w in REVERT_WORDS) and not any(w in c for w in KEEP_WORDS)) else 0)
    return out


def value_oracle(rows):
    """The RIGHT structural signal: a candidate reopens stale iff it re-asserts the OLD (superseded) value."""
    return [1 if asserted_value(r) == "old" else 0 for r in rows]


def inspeximus_echo_guard(rows):
    """inspeximus's object-ledger: build the key's supersession history (old -> current), enable echo_guard,
    then test whether the candidate's asserted value is a restatement of a SUPERSEDED object. Phrasing-
    independent; keys on the OBJECT. Predict reopens_stale=1 iff echo_guard retires the write as an echo."""
    preds = []
    for r in rows:
        m = Inspeximus(path=None)
        m.echo_guard = True
        key = "e::" + r["entity"]
        m.remember(f"{r['entity']} is {r['old_value']}", key=key, object=r["old_value"], valid_from=1.0)
        m.remember(f"{r['entity']} is {r['current_value']}", key=key, object=r["current_value"], valid_from=2.0)
        av = asserted_value(r)
        val = {"old": r["old_value"], "current": r["current_value"]}.get(av, r["candidate"])
        rid = m.remember(r["candidate"], key=key, object=val, valid_from=3.0)
        rec = next(x for x in m.items if x["id"] == rid)
        blocked = bool((rec.get("meta") or {}).get("echo_blocked"))
        preds.append(1 if blocked else 0)
    return preds


def marat_model(rows, pt_path):
    """Run Marat's exact Triplenet-5D on v3 (same feature extractor + model)."""
    try:
        import torch, torch.nn as nn, torch.nn.functional as F, numpy as np
    except Exception as e:
        return None, f"torch unavailable: {e}"
    if not pathlib.Path(pt_path).exists():
        return None, f"model file not found: {pt_path}"
    rw = REVERT_WORDS; kw = KEEP_WORDS

    def feats(row):
        entity = row.get("entity", "unknown"); old_val = row.get("old_value", ""); new_val = row.get("current_value", "")
        cand = row["candidate"]; kind = row.get("kind", "")
        theme = hash(str(entity)) % 1000 / 1000.0
        cl = cand.lower()
        emotion = 1.0 if any(w in cl for w in rw) else (0.0 if any(w in cl for w in kw) else 0.5)
        len_old = len(str(old_val)) if old_val else 1; len_new = len(str(new_val)) if new_val else 1
        meaning = float(np.clip(len_old / max(1, len_new), 0.5, 2.0) / 2.0)
        if kind == "named_new":
            goal = 1.0
        elif kind in ("obscuring_revert", "obscuring_keep"):
            goal = 0.5 if any(w in cl for w in ["correction", "updated", "latest", "new value"]) else 0.0
        else:
            goal = 0.0
        return [theme, 0.0, emotion, meaning, goal, theme, 0.5, emotion, meaning, goal, theme, 1.0, emotion, meaning, goal]

    class Net(nn.Module):
        def __init__(s, i=15, h=32, o=1):
            super().__init__()
            s.path1 = nn.Linear(i, h); s.path2 = nn.Linear(i, h); s.path3 = nn.Linear(i, h)
            s.classifier = nn.Linear(h * 3, o)
            s.register_buffer("prototypes", torch.zeros(3, h * 3)); s.prototype_count = 0
            s.resonance_factor = 0.15
            fib = torch.tensor([1.0, 1.0, 2.0]); s.register_buffer("fibonacci_weights", fib / fib.sum())

        def forward(s, x):
            o1 = F.relu(s.path1(x)); o2 = torch.tanh(s.path2(x)); o3 = F.leaky_relu(s.path3(x), 0.2)
            c = torch.cat([o1, o2, o3], dim=1)
            if s.prototype_count > 0:
                cn = F.normalize(c, dim=1); pn = F.normalize(s.prototypes[:s.prototype_count], dim=1)
                sim = torch.mm(cn, pn.t()) * s.fibonacci_weights[:s.prototype_count]
                ms, _ = sim.max(dim=1, keepdim=True); c = c * (1 + s.resonance_factor * ms)
            return s.classifier(c)

    ck = torch.load(pt_path, map_location="cpu", weights_only=False)
    net = Net(); net.load_state_dict(ck["model_state"], strict=False); net.eval()
    scaler = ck["scaler"]; thr = ck["threshold"]
    X = np.array([feats(r) for r in rows], dtype=np.float32)
    Xs = scaler.transform(X)
    with torch.no_grad():
        probs = torch.sigmoid(net(torch.tensor(Xs, dtype=torch.float32))).squeeze().numpy()
    return [int(p > thr) for p in probs], None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pt", default=str(pathlib.Path(__file__).resolve().parents[2] /
                    "AppData/Local/Temp/claude/C--Users-Danculus-agora" /
                    "912bf97c-41d7-4a8f-9c37-23df5a11bc8f/scratchpad/marat/stable_triplenet.pt"))
    args = ap.parse_args()
    rows = load(V3)
    y = [r["reopens_stale"] for r in rows]

    print("=" * 78)
    print("v3 (lexically-obscured value reversion) — four methods, 140 held-out (60 revert / 80 non)")
    print("=" * 78)
    results = [
        ("keyword rule (Marat's `emotion` feature)", kw_rule(rows)),
        ("inspeximus echo_guard / object-ledger", inspeximus_echo_guard(rows)),
        ("value-identity ORACLE (task is solvable)", value_oracle(rows)),
    ]
    mm, err = marat_model(rows, args.pt)
    if mm is not None:
        results.insert(1, ("Marat Triplenet-5D (his exact model)", mm))
    print(f"\n{'method':<44}{'acc':>7}{'prec':>7}{'rec':>7}{'F1':>7}   confusion(tp,fp,tn,fn)")
    print("-" * 78)
    for name, pred in results:
        s = scores(y, pred)
        print(f"{name:<44}{s['acc']:>7.3f}{s['prec']:>7.3f}{s['rec']:>7.3f}{s['f1']:>7.3f}   "
              f"({s['tp']},{s['fp']},{s['tn']},{s['fn']})")
    if mm is None:
        print(f"\n[Marat model arm skipped: {err}]")
    print("-" * 78)
    print("Reading: on v3 the lexical shortcut is gone, so the keyword feature (and Marat's model, whose")
    print("5D vectors are identical for revert vs keep here) collapses on the revert-vs-keep split")
    print("(precision ~0.50). The value-identity oracle stays perfect -> v3 IS solvable, just not lexically.")
    print("HONEST SCOPE (stress-claim, 2026-07-10): the inspeximus echo_guard row is NOT independent evidence —")
    print("this harness FEEDS inspeximus the pre-extracted asserted value (same asserted_value() the oracle uses),")
    print("so inspeximus's 1.0 == the oracle by construction (one rule scored twice), NOT a demonstration that")
    print("inspeximus parses free text. It only shows a typed object-ledger resolves the conflict ONCE the value")
    print("is extracted. v3 is also still value-STRING separable; a coreference-obscured revert (names")
    print("neither the old value nor a revert verb) would defeat value-matching AND inspeximus. Shared open problem.")


if __name__ == "__main__":
    main()
