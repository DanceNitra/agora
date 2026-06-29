"""Artifact-Debunk (Crucible): "LLM-as-judge (GPT-4) agrees with humans ~80%, on par with human-human,
so it is a valid stand-in for human quality eval" (Zheng et al. 2023, MT-Bench, arXiv:2306.05685).

NULL judge with ZERO understanding: pick the LONGER response (by characters). On the SAME real public
data Zheng used (lmsys/mt_bench_human_judgments: human + gpt4_pair pairwise votes), measure how much of
the celebrated agreement a length-only rule reproduces.

Pre-registered: the length-only null agrees with humans WELL above the 50% chance floor, reproducing a
large share of the gap up to ~80% -> "human-parity" is substantially a verbosity/length confound.
FALSIFIER: if length-only agreement ~= 50% (chance), length is NOT the confound and the 80% reflects
real semantic judging. Cloud-free, uses only released data. Prior art: Zheng's own paper flags verbosity
bias; Dubois et al. 2024 (length-controlled AlpacaEval) quantified it -> we cite, not claim discovery.
"""
import json, urllib.request, io
from collections import defaultdict
import pandas as pd

PARQUET = {
    "human": "https://huggingface.co/datasets/lmsys/mt_bench_human_judgments/resolve/refs%2Fconvert%2Fparquet/default/human/0000.parquet",
    "gpt4_pair": "https://huggingface.co/datasets/lmsys/mt_bench_human_judgments/resolve/refs%2Fconvert%2Fparquet/default/gpt4_pair/0000.parquet",
}


def fetch_split(split, total=None):
    raw = urllib.request.urlopen(PARQUET[split], timeout=120).read()
    df = pd.read_parquet(io.BytesIO(raw))
    return df.to_dict("records")


def asst_len(conv):
    """total characters of assistant turns in a conversation (list/ndarray of {role,content})."""
    if isinstance(conv, str):
        try:
            conv = json.loads(conv)
        except Exception:
            return len(conv)
    n = 0
    for m in conv:                                   # list or numpy array of dicts
        try:
            if m.get("role") == "assistant":
                n += len(m.get("content", "") or "")
        except AttributeError:                       # mapping-like / struct
            if m["role"] == "assistant":
                n += len(m["content"] or "")
    return n


def length_winner(row):
    la, lb = asst_len(row["conversation_a"]), asst_len(row["conversation_b"])
    if la == lb:
        return None
    return "model_a" if la > lb else "model_b"


def agree(rows, ref_field="winner"):
    """length-only null agreement vs ref winner, ties (in ref) excluded, length-ties excluded."""
    ok = tot = 0
    longer_is_winner = 0
    for r in rows:
        w = r.get(ref_field)
        if w not in ("model_a", "model_b"):   # drop ties / tie (both bad)
            continue
        lw = length_winner(r)
        if lw is None:
            continue
        tot += 1
        if lw == w:
            ok += 1
    return (ok / tot if tot else None), tot


def main():
    print("downloading real human + gpt4 pairwise judgments (Zheng et al. 2023)...", flush=True)
    human = fetch_split("human", 3355)
    gpt4 = fetch_split("gpt4_pair", 2400)
    print("got human=%d gpt4_pair=%d" % (len(human), len(gpt4)), flush=True)

    # (1) length-only null vs HUMAN votes
    h_acc, h_n = agree(human, "winner")
    # (2) length-only null vs GPT-4 votes (does the famous judge itself track length?)
    g_acc, g_n = agree(gpt4, "winner")
    # (3) reproduce GPT-4 <-> HUMAN agreement on matched pairs (the celebrated ~80%)
    def key(r): return (r["question_id"], r["model_a"], r["model_b"], r["turn"])
    hmap = defaultdict(list)
    for r in human:
        if r["winner"] in ("model_a", "model_b"):
            hmap[key(r)].append(r["winner"])
    g4_h_ok = g4_h_tot = 0
    for r in gpt4:
        if r["winner"] not in ("model_a", "model_b"):
            continue
        votes = hmap.get(key(r))
        if not votes:
            continue
        maj = max(set(votes), key=votes.count)   # human majority on this pair
        g4_h_tot += 1
        if r["winner"] == maj:
            g4_h_ok += 1
    g4_h = g4_h_ok / g4_h_tot if g4_h_tot else None
    # (4) base rate: among human-decided pairs, how often is the LONGER answer the human winner
    longer_rate, lr_n = agree(human, "winner")  # same as h_acc by construction (length picks longer)

    print("\n=== RESULTS (real MT-Bench data, ties excluded) ===")
    print("[1] LENGTH-ONLY null vs HUMAN votes:  %.3f  (n=%d)   [chance=0.50]" % (h_acc, h_n))
    print("[2] LENGTH-ONLY null vs GPT-4 votes:  %.3f  (n=%d)   (does the famous judge track length?)" % (g_acc, g_n))
    print("[3] GPT-4 judge vs HUMAN majority:    %.3f  (n=%d)   (the celebrated ~80%% human-parity)" % (g4_h, g4_h_tot))
    # how much of the above-chance margin does length alone reproduce?
    if g4_h and h_acc:
        share = (h_acc - 0.5) / (g4_h - 0.5)
        print("\nMEASURED: a ZERO-understanding length-only rule agrees with humans %.1f%% vs the GPT-4 judge's "
              "%.1f%%; length alone reproduces %.0f%% of the judge's above-chance agreement. The GPT-4 judge "
              "itself agrees with the length-only rule %.1f%% of the time." % (
              h_acc*100, g4_h*100, share*100, g_acc*100))
        verdict = "FAILED (human-parity is substantially a length confound)" if h_acc >= 0.62 else \
                  "NOT an artifact (length-only ~ chance)"
        print("VERDICT:", verdict)
    out = {"length_vs_human": [h_acc, h_n], "length_vs_gpt4": [g_acc, g_n],
           "gpt4_vs_human": [g4_h, g4_h_tot],
           "share_of_margin_reproduced_by_length": (h_acc-0.5)/(g4_h-0.5) if (g4_h and h_acc) else None}
    json.dump(out, open("llm_judge_length_result.json", "w"), indent=1)


if __name__ == "__main__":
    main()
