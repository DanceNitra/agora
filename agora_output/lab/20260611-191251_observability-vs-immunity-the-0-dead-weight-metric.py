import random
random.seed(42)

# CHALLENGE the deepened belief "observability is the immune system of a knowledge base", which cites
# a measured ~0% dead-weight baseline. The prior supersession said: an immune system DETECTS *and*
# RESPONDS; observability only DETECTS. Severe test: does the low-dead-weight metric come from
# OBSERVABILITY (seeing) or from PRUNING (the response)? Simulate a KB where notes arrive and decay
# (stop being retrieved); compare three policies and measure the dead-weight fraction. Source: simulation.

STEPS=400; ARRIVE=3; DECAY=0.02   # each step: 3 notes arrive; each note has 2%/step chance to go stale

def run(policy):
    notes=[]   # each: {'stale':bool, 'archived':bool}
    seen_stale=0
    for t in range(STEPS):
        for _ in range(ARRIVE): notes.append({'stale':False,'archived':False})
        for n in notes:
            if not n['stale'] and not n['archived'] and random.random()<DECAY:
                n['stale']=True
        live=[n for n in notes if not n['archived']]
        stale=[n for n in live if n['stale']]
        if policy=='observability':           # SEES stale (counts it) but takes no action
            seen_stale=len(stale)
        elif policy=='obs+prune':             # SEES and ARCHIVES stale (the response)
            for n in stale: n['archived']=True
    live=[n for n in notes if not n['archived']]
    dead=[n for n in live if n['stale']]
    return len(dead)/len(live) if live else 0, (len(dead) if policy!='blind' else None)

print("Knowledge base with note decay. Dead-weight fraction after 400 steps:\n")
for name,pol in [("blind (no observability)","blind"),
                 ("observability ONLY (detect, no action)","observability"),
                 ("observability + pruning (detect + respond)","obs+prune")]:
    frac,_=run(pol)
    print(f"  {name:42} dead-weight = {frac*100:5.1f}%")
print("\nVERDICT: observability-ONLY leaves dead weight ~unchanged (it merely SEES it); the ~0% metric")
print("is produced by the PRUNING response, not the observation. Reconfirms the supersession:")
print("observability is the SURVEILLANCE half of immunity; without a response (prune/consolidate) it is")
print("eyes, not an immune system. (inspeximus.consolidate() is exactly that response half.)")
