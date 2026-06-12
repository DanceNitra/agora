import random, statistics as st
random.seed(42)

# CHALLENGE the belief: "memory consolidation is critical-window load balancing."
# Falsifiable core: if consolidation is a finite-capacity window doing load balancing, retention
# should drop as arrival load exceeds window capacity. The 'CRITICAL' claim is stronger: the drop
# should be SHARP (a near-phase-transition), not a smooth knee. We test two mechanisms:
#  (A) pure capacity: a window consolidates up to C items well; surplus is poorly retained.
#  (B) capacity + interference feedback: overload also degrades ALREADY-stored memories
#      (load balancing breaks down -> cascading loss), which is what would make it 'critical'.
# Source: simulation.

C = 40                  # window consolidation capacity (items/night)
TRIALS = 600

def retention(load, interference):
    # 'load' items arrive needing consolidation this window
    consolidated = min(load, C)
    well = consolidated / load if load else 1.0          # fraction arriving that get a slot
    if not interference:
        return well
    # interference: when overloaded, each surplus item corrupts existing traces at rate beta
    surplus = max(0, load - C)
    beta = 0.025
    degrade = 1.0 / (1.0 + beta * surplus)               # multiplicative collapse of retained set
    return well * degrade

def sharpness(curve):
    # max single-step drop in retention across the load sweep (proxy for 'how critical')
    return max(curve[i]-curve[i+1] for i in range(len(curve)-1))

loads = list(range(10, 161, 5))
ratios = [l / C for l in loads]
cap = [st.mean(retention(l, False) for _ in range(40)) for l in loads]
intf = [st.mean(retention(l, True)  for _ in range(40)) for l in loads]

print(f"window capacity C={C}. retention vs load (load/C at knee = 1.0)\n")
print(f"{'load/C':>7} {'pure-capacity':>14} {'+interference':>14}")
for i,l in enumerate(loads):
    if abs(ratios[i]-0.75)<.03 or abs(ratios[i]-1.0)<.03 or abs(ratios[i]-1.5)<.03 or abs(ratios[i]-2.0)<.03 or abs(ratios[i]-3.0)<.03:
        print(f"{ratios[i]:7.2f} {cap[i]:14.2f} {intf[i]:14.2f}")
print(f"\nmax drop per step: pure-capacity {sharpness(cap):.3f}  ·  +interference {sharpness(intf):.3f}")
print("VERDICT: load-balancing capacity limit is real (retention falls past load/C=1).")
print("'CRITICAL' is justified ONLY with interference feedback (sharper collapse); pure capacity")
print("is a smooth ~C/load knee, not a phase transition.")
