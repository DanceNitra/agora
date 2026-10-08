"""Every figure in the 2026-09-24 reply to Guanghao on "Same Orbit Implies Same Response", recomputed.

Each claim reads the number from its source file AND checks that the letter states the same number,
so a figure that drifts in either place fails. Sources: our result files from
probes/edrn_orbit_response_independent_check.py and probes/edrn_window_boundary_check.py, and
Guanghao's own v12 and v16 JSON files and his N=7 script. tools/recompute_receipt.py runs this and
mutates the inputs; inputs come only from AGORA_INPUT_DIR.
"""
import io
import json
import os

D = os.environ["AGORA_INPUT_DIR"]


def load(name):
    try:
        return json.load(io.open(os.path.join(D, name), encoding="utf-8"))
    except Exception:
        return None


def text(name):
    try:
        return io.open(os.path.join(D, name), encoding="utf-8", errors="replace").read()
    except Exception:
        return ""


letter = text("letter.md")
A = load("edrn_orbit_response_independent_check.A.result.json") or {}
H = load("edrn_orbit_response_independent_check.H.result.json") or {}
F = load("edrn_orbit_response_independent_check.result.json") or {}
W = load("edrn_window_boundary_check.result.json") or {}
v12 = (load("guanghao_v12_N7_pS.json") or {}).get("resonances", [])
v16 = (load("guanghao_v16_N7_degenerate.json") or {}).get("resonances", [])
script = text("guanghao_N7_full_check.py")


def claim(cid, ok, desc, stated):
    ok = bool(ok) and all(s in letter for s in stated)
    print("CLAIM %s %s %s" % (cid, "PASS" if ok else "FAIL", desc))


def g(d, *keys):
    for k in keys:
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


claim("table_kept", g(A, "A_N7_table_skip_naut_gt_500") == {"so_same": 6504, "so_diff": 0, "do_same": 382, "do_diff": 44142},
      "with his n_aut>500 skip the N=7 table is 6504/0/382/44142", ["6504 / 0 / 382 / 44142"])
claim("table_all", g(A, "A_N7_table_all_853") == {"so_same": 6729, "so_diff": 0, "do_same": 382, "do_diff": 44142},
      "with all 853 graphs the table is 6729/0/382/44142", ["6729 / 0 / 382 / 44142", "225 pairs"])
claim("skipped", g(A, "A_N7_graphs_with_naut_gt_500") == [0, 852] and "if n_aut > 500:" in script,
      "his script skips n_aut>500, which is atlas ids 0 and 852", ["index 0", "index 852", "if n_aut > 500: continue"])
pts = (g(H, "H_N6", "points_tested") or 0) + (g(H, "H_N7", "points_tested") or 0)
err = max(g(H, "H_N6", "max_abs_err") or 1, g(H, "H_N7", "max_abs_err") or 1)
claim("hellmann_feynman", pts == 31509 and err < 1.71e-8,
      "dE0/ds matches <sigma.sigma> to 1.7e-8 on 31,509 points", ["1.7e-8", "31,509 points"])
edges = (g(F, "BC_N6", "edges") or 0) + (g(F, "BC_N7", "edges") or 0)
drops = (g(F, "BC_N6", "edges_with_pS_drop_gt_1e-9") or 0) + (g(F, "BC_N7", "edges_with_pS_drop_gt_1e-9") or 0)
claim("monotone", edges == 10503 and drops == 0 and g(F, "BC_N6") is not None,
      "p_S never decreases on 10,503 defect edges", ["10,503 defect edges"])
d15, d25 = g(F, "D_N7_sector_formula_by_S", "1.5") or {}, g(F, "D_N7_sector_formula_by_S", "2.5") or {}
claim("sector_formula", (d15.get("diff_gt_1e-9"), d15.get("states")) == (915, 937)
      and round(d15.get("max_diff", 0), 2) == 0.45 and (d25.get("diff_gt_1e-9"), d25.get("states")) == (16, 16),
      "(1-3zz)/4 off by up to 0.45 in 915/937 S=3/2 and 16/16 S=5/2 states", ["0.45", "915 of 937", "all 16"])

nd = [r for r in v12 if r.get("deg") == 1]
miss = [r for r in nd if abs(r["mean_sigdot"] + 1) >= 1e-8]
half = lambda r: abs(r["p_S"] - 0.5) < 1e-6
spin = lambda r: max(round(x * 2) / 2 for x in r["per_state_S"])
hi_spin = sum(1 for r in miss if half(r) and spin(r) >= 1.5)
jumps = [r for r in miss if not half(r)]
tol = [r for r in miss if half(r) and spin(r) < 1.5]
claim("v12_hits", (len(nd), len(nd) - len(miss)) == (7903, 7486), "v12: 7486 hits of 7903 at 1e-8", ["94.7%"])
claim("v12_misses", (len(miss), hi_spin, len(jumps), len(tol)) == (417, 206, 184, 27),
      "the 417 misses split 206 high-spin, 184 jump roots, 27 tolerance", ["417 misses", "206 are", "184 are", "27 are"])
claim("tolerance_roots", tol and all(abs(r["mean_sigdot"] + 1) < 1e-6 for r in tol),
      "the 27 tolerance misses are true roots within 1e-6", ["hit tolerance"])
claim("jump_range", jumps and (round(min(r["p_S"] for r in jumps), 2), round(max(r["p_S"] for r in jumps), 2)) == (0.34, 0.66),
      "jump roots have p_S from 0.34 to 0.66", ["0.34 to 0.66"])
claim("two_runs", (len(v12), len(v16)) == (9314, 9485), "v12 and v16 hold 9314 and 9485 resonances", ["9314 and 9485"])

br = {k: [r.get("breaks_at") for r in W.get(k, [])] for k in ("38", "60", "103")}
chg = lambda k: sum(1 for r in W.get(k, []) if any(tuple(a) != tuple(b) for a, b in zip(r["spin_below"], r["spin_above"])))
claim("window_breaks", br["38"] == [0.0] * 6 and sorted(br["60"]) == [0.0, 0.0, 0.0, 1.0, 1.0] and br["103"] == [1.001] * 3,
      "every scanned equality ends at s=0 or s=1", ["s = 0", "s = 1", "steps of one thousandth"])
claim("spin_change", (chg("38"), len(W.get("38", [])), chg("60"), len(W.get("60", []))) == (6, 6, 4, 5),
      "spin changes at the break for 6/6 pairs of graph 38 and 4/5 of graph 60", ["all six pairs of graph 38", "four of the five pairs of graph 60"])
