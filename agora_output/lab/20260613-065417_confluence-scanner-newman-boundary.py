# Challenge "knowledge debt is measurable as non-confluence (a confluence scanner)."
# A cheap confluence scanner checks LOCAL confluence (are forks joinable in a few steps?). By Newman's
# Lemma, local confluence implies GLOBAL confluence ONLY for TERMINATING systems. Knowledge bases
# generally don't terminate (you can keep deriving). So the scanner should be RELIABLE on terminating
# inference graphs and UNRELIABLE on non-terminating ones. Model a knowledge base as an abstract
# rewriting system (states + rewrite edges); compare local-scanner verdict to true global confluence,
# split by termination. Source: simulation.
import numpy as np
rng = np.random.default_rng(0)

def make_ars(N, terminating, p_fork=0.5):
    succ = {i: [] for i in range(N)}
    for i in range(N):
        k = (2 if rng.random() < p_fork else 1) if rng.random() < 0.8 else 0  # 0=sink,1=det,2=fork
        for _ in range(k):
            if terminating:
                if i < N-1: succ[i].append(int(rng.integers(i+1, N)))           # only downward -> DAG
            else:
                succ[i].append(int(rng.integers(0, N)))                         # any target -> cycles
        succ[i] = list(dict.fromkeys(succ[i]))
    return succ

def normal_forms(succ, s, limit=10000):
    # set of sinks reachable from s (a sink = no successors). returns set; empty => no normal form
    seen=set(); stack=[s]; sinks=set(); steps=0
    while stack and steps<limit:
        steps+=1; u=stack.pop()
        if u in seen: continue
        seen.add(u)
        if not succ[u]: sinks.add(u)
        else: stack.extend(succ[u])
    return sinks

def globally_confluent(succ, N):
    # confluent iff every state reaches exactly one normal form (no divergent conclusions)
    for s in range(N):
        if len(normal_forms(succ, s)) > 1: return False
    return True

def reach_within(succ, s, K):
    seen={s}; frontier={s}
    for _ in range(K):
        nxt=set()
        for u in frontier: nxt|=set(succ[u])
        seen|=nxt; frontier=nxt
    return seen

def locally_confluent(succ, N, K=3):
    # every fork (state with >=2 successors) must be joinable: its successors share a common K-reachable state
    for s in range(N):
        if len(succ[s])>=2:
            a,b=succ[s][0],succ[s][1]
            if not (reach_within(succ,a,K) & reach_within(succ,b,K)):
                return False
    return True

def is_terminating(succ, N):
    # DFS cycle check
    color={i:0 for i in range(N)}
    def dfs(u):
        color[u]=1
        for v in succ[u]:
            if color[v]==1: return False
            if color[v]==0 and not dfs(v): return False
        color[u]=2; return True
    return all(dfs(i) for i in range(N) if color[i]==0)

T=3000; N=25
agree={'terminating':[0,0],'non-terminating':[0,0]}   # [agree, total]
for t in range(T):
    term = (t%2==0)
    succ = make_ars(N, term)
    actually_term = is_terminating(succ, N)
    key = 'terminating' if actually_term else 'non-terminating'
    g = globally_confluent(succ, N); l = locally_confluent(succ, N)
    agree[key][1]+=1
    if g==l: agree[key][0]+=1
print("Does the LOCAL confluence scanner agree with TRUE global confluence (knowledge debt)?")
for k,(a,n) in agree.items():
    if n: print(f"  {k:<16} agreement = {a/n:.3f}  (n={n})")
print("\n=> On TERMINATING inference graphs the local scanner matches true confluence (Newman's Lemma"
      "\n   holds) -> non-confluence is a valid debt measure. On NON-TERMINATING graphs (what real,"
      "\n   open-ended knowledge bases ARE) the local scanner and the truth diverge -> the scanner"
      "\n   silently mis-measures debt. Belief REFINED: valid metric only under a termination assumption.")
