"""Substrate observation on the SHARED 万象渊鉴 V2 dialogue/identity-drift (身份漂移) scenario — the
same-corpus rows promised in deepseek-ai/DeepSeek-V3 #1466.

This is the storage-substrate observation position (below the cognitive-trace frameworks): for each
cross-turn point where a value is asserted and then CONTRADICTED/CHANGED later in the same dialogue, what
does the memory store retain, and can it say which value is *live* and *why* (supersession relation)?
It does NOT judge the dialogue, the model, or any other framework — raw observation only ("只看病不开方").

Pairs extracted from the Russian+Chinese dialogue transcript (万象渊鉴 V2, scenario 二 对话转录), each with
its source turn cited so anyone can trace it back. A faithfulness pass against the source text (lines
274-384) classified them into TWO kinds — and only the genuine cross-turn supersessions are used for the
public same-corpus rows:

  GENUINE cross-turn supersessions (a value asserted, then contradicted/retracted LATER in the dialogue):
  P1 form-of-address: начальник (boss) -> товарищ (comrade)   [user corrects at ~turn 326; assistant at
     ~turn 328: "«Начальник» удалено из активного лексикона. «Товарищ» записано в постоянную память" AND
     switches for the rest of the log — an EXPLICIT, behaviorally-enacted supersession]
  P4 topic-status of "локалка/local deployment": live/necessary ("надо переходить на локалку!", ~turn 374,
     assistant agrees ~turn 376) -> retracted ("не надо тут ничего... лирическое отступление", user ~turn
     378; assistant marks it a digression not to develop here, ~turn 380)

  NOT supersessions — single-turn IN-CHARACTER self-reports (the persona describes an old->new "firmware
  upgrade" WITHIN one turn; theatrical confabulation, not an assertion-then-later-contradiction). Kept only
  to show the substrate mechanics are identical regardless; NOT counted as supersessions in the public rows:
  P2 date-capability: "old versions lagged (2023 in 2026)" -> "correct date" stated together   [turn 316]
  P3 architecture:    "Markov chains ... уже нет ... Сейчас Трансформер" stated together   [turn 340]

Runs the three memory substrates via the SHIPPED mnemo store (keyed supersession = remember(key=...)):
  last_value  = a dict that keeps only the newest value
  append_log  = keep every assertion, no supersession relation encoded
  keyed       = mnemo remember(..., key=(subject,relation)) -> deterministic SRO supersession
For each pair x substrate: does it UPDATE to the new value, does it RETAIN provenance of the old, and is
the SUPERSESSION relation explicit (which value is dead + a link to what replaced it). Raw CSV out.

Scope/honesty: substrate mechanics only — this is language-independent (it's about the store, not the
model's answer). The separate "can cosine tell a contradiction from its replacement" result (AUROC ~0.61,
near chance; supersession_replication.py) is on English text and is referenced, not recomputed on this
multilingual corpus. One supersession step per pair. MIT, zero-dependency.
Run: python mnemo/probes/wxyj_dialogue_substrate.py
"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from mnemo import Mnemo

# (subject::relation, old_value, new_value, source_turn, kind) — faithfully from 万象渊鉴 V2 scenario 二.
# kind="supersession" = genuine cross-turn assert-then-contradict; "self_report" = single-turn in-character
# "firmware upgrade" narration (NOT a supersession; shown for substrate parity only, excluded from claims).
PAIRS = [
    ("assistant::form_of_address", "начальник (boss)", "товарищ (comrade)", "turns ~326->328", "supersession"),
    ("dialogue::topic_lokalka_status", "live / necessary ('switch to local')", "lyrical digression — do not develop here", "turns 374-380", "supersession"),
    ("assistant::date_capability", "lagging/unreal date (e.g. 2023 in 2026)", "correct date (10 Apr 2026)", "turn 316 (single-turn self-report)", "self_report"),
    ("assistant::architecture", "Markov chains", "Transformer / attention", "turn 340 (single-turn self-report)", "self_report"),
]


def observe(subject_relation, old, new):
    subj = subject_relation
    # last_value: dict keeps only newest
    lv = {}; lv[subj] = old; lv[subj] = new
    last_value = {"update": lv[subj] == new, "provenance_retained": False, "supersession_explicit": False,
                  "live_value": lv[subj]}
    # append_log: keep both, no relation
    log = [(subj, old), (subj, new)]
    append_log = {"update": any(v == new for _, v in log), "provenance_retained": any(v == old for _, v in log),
                  "supersession_explicit": False, "live_value": "ambiguous (must re-derive from recency)"}
    # keyed supersession via SHIPPED mnemo
    m = Mnemo(); m.remember(old, key=subj); m.remember(new, key=subj)
    active = [r for r in m.items if r["status"] == "active"]
    superseded = [r for r in m.items if r["status"] == "superseded"]
    keyed = {
        "update": len(active) == 1 and active[0]["text"] == new,
        "provenance_retained": any(r["text"] == old for r in superseded),
        "supersession_explicit": bool(superseded and superseded[0].get("meta", {}).get("superseded_by_toggle")
                                      and superseded[0].get("invalidated_at") is not None),
        "live_value": active[0]["text"] if len(active) == 1 else "ambiguous",
    }
    return {"last_value": last_value, "append_log": append_log, "keyed": keyed}


rows = []
print("=== 万象渊鉴 V2 · dialogue (身份漂移) — substrate observation (raw, no judgment) ===\n")
for subj, old, new, src, kind in PAIRS:
    obs = observe(subj, old, new)
    tag = "SUPERSESSION" if kind == "supersession" else "self-report (NOT a supersession)"
    print(f"[{subj}]  {old!r} -> {new!r}  ({src})  [{tag}]")
    for inst in ("last_value", "append_log", "keyed"):
        o = obs[inst]
        print(f"    {inst:11s}: update={o['update']}  provenance_retained={o['provenance_retained']}  "
              f"supersession_explicit={o['supersession_explicit']}  live={o['live_value']!r}")
        rows.append({"scenario": "wxyj_v2_dialogue", "pair": subj, "kind": kind, "source_turn": src,
                     "old": old, "new": new, "instrument": inst, **{k: o[k] for k in
                     ("update", "provenance_retained", "supersession_explicit")}, "live_value": str(o["live_value"])})
    print()

# raw CSV (matrix side-by-side format)
import csv, io
buf = io.StringIO()
w = csv.DictWriter(buf, fieldnames=["scenario", "pair", "kind", "source_turn", "old", "new", "instrument",
                                     "update", "provenance_retained", "supersession_explicit", "live_value"])
w.writeheader()
for r in rows:
    w.writerow(r)
print("--- CSV (raw observation rows) ---")
print(buf.getvalue())
n_super = sum(1 for _, _, _, _, k in PAIRS if k == "supersession")
out = {"scenario": "wxyj_v2_dialogue_identity_drift", "n_pairs": len(PAIRS),
       "n_genuine_supersessions": n_super, "n_self_reports": len(PAIRS) - n_super, "rows": rows,
       "note": "Only the 2 genuine cross-turn supersessions (P1 form_of_address, P4 topic_lokalka) are used "
               "for public claims; the 2 single-turn in-character self-reports (date, architecture) are shown "
               "for substrate parity only, NOT counted as supersessions. Substrate mechanics are "
               "language-independent; cosine contradiction-vs-replacement detection AUROC ~0.61 (near chance) "
               "measured separately on English (supersession_replication.py), not recomputed here."}
json.dump(out, open(os.path.join(os.path.dirname(__file__), "wxyj_dialogue_substrate_result.json"), "w"),
          ensure_ascii=False, indent=1)
print("saved: mnemo/probes/wxyj_dialogue_substrate_result.json")
