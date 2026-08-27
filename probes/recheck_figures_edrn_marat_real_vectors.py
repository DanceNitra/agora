# -*- coding: utf-8 -*-
"""ONE CHECK INSIDE **VALIDATE**. NOT the gate. The gate is validate -> stress-claim -> verify-claims
-> humanizer, and every one of those is a SKILL.

The first version of this file passed 17/17 on a draft that was wrong twice, because it only asked
whether the draft's digits matched the receipt. It never asked whether the receipt's LABELS meant
what the draft said they meant. `exact_max_over_doublet` is a 401x401 grid scan whose phi = 0 line
IS the real family, so the draft's "computed rather than sampled" and its claim of independent
agreement were both false while every digit matched. This version therefore RE-DERIVES the physics
instead of reading it, and refuses any decimal the draft prints that it cannot reproduce.
"""
import io, json, re, sys, importlib.util
import numpy as np

DRAFT = 'agora_output/drafts/reply_edrn_marat_real_vectors_are_forced.md'
PROBE = 'probes/edrn_the_orbit_floor_holds_across_the_symmetry_spectrum.py'
RECEIPT = PROBE.replace('.py', '.result.json')

text = ' '.join(io.open(DRAFT, encoding='utf-8').read().split())   # wrap-proof, see the first version
ring = json.load(io.open(RECEIPT, encoding='utf-8'))['ring']
src = io.open(PROBE, encoding='utf-8').read()

spec = importlib.util.spec_from_file_location('orb', PROBE)
m = importlib.util.module_from_spec(spec); m.__name__ = 'orb'
try: spec.loader.exec_module(m)
except SystemExit: pass

Er = [(i, (i + 1) % 15) for i in range(15)]
H7, b7 = m.build_H(15, Er, [1.0] * len(Er), 7)
d7, V7, e7 = m.ground_manifold(H7)
sp7 = m.sp_table(b7, Er)
H8, b8 = m.build_H(15, Er, [1.0] * len(Er), 8)
d8, V8, e8 = m.ground_manifold(H8)
E1 = lambda v: float(np.sqrt(np.var(sp7 @ (np.abs(v) ** 2))))

# --- RE-DERIVE the closed form the draft asserts, from scratch
kp = (V7[:, 0] + 1j * V7[:, 1]) / np.sqrt(2)
km = (V7[:, 0] - 1j * V7[:, 1]) / np.sqrt(2)
rng = np.random.default_rng(11)
pairs = []
for _ in range(500):
    a = rng.standard_normal() + 1j * rng.standard_normal()
    b = rng.standard_normal() + 1j * rng.standard_normal()
    n = np.sqrt(abs(a) ** 2 + abs(b) ** 2); a, b = a / n, b / n
    pairs.append((2 * abs(a) * abs(b), E1(a * kp + b * km)))
arr = np.array(pairs); msk = arr[:, 0] > 1e-6
C = float(np.median(arr[msk, 1] / arr[msk, 0]))
dev = float(np.max(np.abs(arr[:, 1] - C * arr[:, 0])))
mom = E1(kp)

v = {}
v['CONTROL_the_rederivation_ran'] = d7 == 2 and len(pairs) == 500
v['closed_form_constant_matches_draft'] = ('0.13097935486622' in text
                                           and abs(C - 0.13097935486622) < 1e-13)
v['draft_deviation_figure_is_real'] = '4.4e-16' in text and dev < 5e-16
v['draft_momentum_zero_is_real'] = '7.1e-16' in text and mom < 1e-14
v['real_vector_attains_the_constant'] = abs(E1(V7[:, 0]) - C) < 1e-13
v['CONTROL_a_wrong_constant_would_FAIL'] = not (abs((C * 1.01) - 0.13097935486622) < 1e-13)
v['CONTROL_the_law_can_be_broken'] = np.max(np.abs(arr[:, 1] - (C * 1.05) * arr[:, 0])) > 1e-6

# --- the sector claim, from the receipt
sd = ring.get('sector_dependence') or {}
v['sector_numbers_match_draft'] = all(
    x in text for x in ('0.1310', '0.1622', '0.1814')) and (
    abs(sd.get('Sz=-0.5', 0) - 0.1310) < 1e-3 and abs(sd.get('Sz=-1.5', 0) - 0.1622) < 1e-3
    and abs(sd.get('Sz=-2.5', 0) - 0.1814) < 1e-3)

# --- the four-fold degeneracy and the energy the draft prints
v['four_fold_level_is_real'] = (d7 + d8 == 4) and abs(e7 - e8) < 1e-9
v['draft_energy_matches'] = '-26.134670289863' in text and abs(e7 - (-26.134670289863)) < 1e-9

# --- the self-correction the draft makes must itself be true
v['the_grid_really_is_401x401'] = '401' in text and '401' in src
v['the_grid_phi_zero_line_is_real'] = ('phi = 0' in text) and ('np.exp(1j * _ph)' in src)

# --- NOTHING the draft prints may lack a source
printed = set(re.findall(r'-?\b\d+\.\d{4,}\b', text))
# DERIVED, never hand-listed: a hand-written allow-list is a second place for the truth to live,
# and the first version of it was already incomplete (it omitted the three sector figures, which the
# receipt does carry). Everything admissible comes from the receipt or from this run.
allowed = {'%.14f' % C, '%.12f' % e7}
allowed |= {('%.4f' % x) for x in sd.values()}
v['no_unsourced_decimals'] = printed <= allowed

# --- the figure a subagent supplied and I could NOT reproduce must be absent
v['the_unreproducible_range_is_gone'] = '0.0015' not in text

v = {k: bool(x) for k, x in v.items()}   # numpy bool_ is not JSON serializable
io.open('probes/recheck_figures_edrn_marat_real_vectors.result.json', 'w', encoding='utf-8').write(
    json.dumps({'draft': DRAFT, 'rederived_C': C, 'max_dev': dev, 'momentum_E1': mom,
                'printed_decimals': sorted(printed), 'verdicts': v}, indent=2))
for k, ok in v.items():
    print('%-42s %s' % (k, 'PASS' if ok else 'FAIL'))
print('\n%d/%d' % (sum(v.values()), len(v)))
sys.exit(0 if all(v.values()) else 1)
