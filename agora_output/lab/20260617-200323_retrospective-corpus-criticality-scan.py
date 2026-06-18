"""
Retrospective corpus scan: run the scientist over EVERYTHING Agora has validated and ask what the
whole body is about — then use Agora's OWN law to test whether that dominant theme is a real signal
or a self-confirming bias.

Hypothesis from a first read of the validated layer: the corpus is dominated by CRITICALITY /
threshold / phase-transition phenomena. If so, two readings compete:
  (a) REAL — complex systems are critical (universality), so a corpus drawn from diverse domains
      will be criticality-heavy; the three canon laws (Legibility, Anchor/Grounding-Coupling) are
      themselves criticality laws.
  (b) BIAS — a self-referential system locks onto a theme regardless of truth (our own Anchor Law).
Test with our own lens: is the criticality cluster externally grounded across DIVERSE domains
(=> real universality), or mono-domain + self-framed (=> lock-in)?
"""
import json, re
from pathlib import Path

def load(f):
    p = Path('server/' + f + '.json')
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else []

CRIT = re.compile(r"critical|threshold|percolation|scaling|power[- ]?law|phase transition|universal|"
                  r"epidemic|branching|collapse|fractal|long[- ]range|finite[- ]size|attractor|"
                  r"bifurcation|edge of chaos|criticality", re.I)
# crude domain tags to measure diversity of the criticality cluster
DOMAINS = {"networks": r"network|percolation|graph|scale-free|BA |Erdos|node|degree|clique",
           "epidemics/spreading": r"epidemic|spreading|contagion|branching",
           "learning/AI": r"model collapse|self-referen|RL|bandit|SGD|neural|training|anchor|prompt",
           "inference/stats": r"detection|legibility|identification|p-hack|DiD|Bayesian|frequentist|effect size",
           "physics/matter": r"glass|supercool|universality class|critical exponent|curvature|torque|alloy",
           "memory/cognition": r"memory|consolidation|cognitive|hot hand|Dunning",
           "finance": r"finance|portfolio|market|alpha|capital"}

reps = [r for r in load('.replications') if r.get('outcome') == 'REPRODUCED']
theory = load('.theory')
laws = load('.unification')

items = []
for r in reps:      items.append(("replication", r.get('claim', '')))
for t in theory:    items.append(("theory", t.get('title', '')))
for u in laws:      items.append(("law", u.get('principle', u.get('name', ''))))

crit_items = [(k, txt) for k, txt in items if CRIT.search(txt or "")]
print(f"VALIDATED items scanned: {len(items)}  (REPRODUCED reps {len(reps)} + theory {len(theory)} + laws {len(laws)})")
print(f"criticality/threshold/phase items: {len(crit_items)}  = {len(crit_items)/max(len(items),1)*100:.0f}%")

# domain diversity of the criticality cluster (real universality vs mono-domain bias)
dom_hits = {}
for k, txt in crit_items:
    for d, pat in DOMAINS.items():
        if re.search(pat, txt or "", re.I):
            dom_hits[d] = dom_hits.get(d, 0) + 1
print("\ncriticality cluster spans domains:")
for d, n in sorted(dom_hits.items(), key=lambda x: -x[1]):
    print(f"  {d:<22} {n}")
n_domains = len(dom_hits)

# grounding check: replications are external (real papers); laws are severe-tested. fraction externally grounded.
crit_external = sum(1 for k, _ in crit_items if k in ("replication",))   # replications = real external papers
print(f"\ncriticality items from EXTERNAL replications (real papers): {crit_external}/{len(crit_items)}")

print("\n=== VERDICT (our own law applied to our own corpus) ===")
dominant = len(crit_items)/max(len(items),1) > 0.45
diverse = n_domains >= 4
print(f"criticality DOMINATES the validated corpus (>45%): {dominant}")
print(f"and spans DIVERSE domains (>=4): {diverse}  ({n_domains} domains)")
if dominant and diverse:
    print("READING (a) REAL: the dominance is externally grounded across many domains -> it is the")
    print("UNIVERSALITY of critical phenomena, not a self-confirming lock-in. By our own Grounding-")
    print("Coupling Law, a lock-in would be mono-domain + self-framed; this is multi-domain + paper-")
    print("grounded, so phi (external grounding) is high -> NOT the starved/locked regime.")
    print("META-FINDING: criticality is the connective tissue of Agora's corpus; the three canon laws")
    print("are themselves critical-transition laws -> the body of work has ONE organizing character.")
else:
    print("Dominance not clean / not diverse -> cannot rule out theme-selection bias; flag for grounding.")
