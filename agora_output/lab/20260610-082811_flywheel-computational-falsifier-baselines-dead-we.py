
import sys, json, time
sys.path.insert(0, r'C:/Users/Danculus/agora/server')
# Falsifier 1: dead-weight fraction (observability-as-immunity hypothesis)
from agora.execution.memory_economy import score_notes, prune_candidates
notes = score_notes(r'C:/Users/Danculus/my-second-brain')
cands = prune_candidates(r'C:/Users/Danculus/my-second-brain', 999)
print('DEAD-WEIGHT FRACTION %s: %d / %d = %.4f%%' % (
    time.strftime('%Y-%m-%d'), len(cands), len(notes), 100.0*len(cands)/max(1,len(notes))))
# Falsifier 2: bridge-formation proxy = link density (avg in+out wikilinks per note)
links = sum(n['inlinks']+n['outlinks'] for n in notes)
print('LINK DENSITY (bridge proxy): %.2f links/note over %d notes' % (links/max(1,len(notes)), len(notes)))
orphans = sum(1 for n in notes if n['inlinks']+n['outlinks']==0)
print('ORPHAN FRACTION: %d (%.3f%%)' % (orphans, 100.0*orphans/max(1,len(notes))))
print('Baseline for monthly tracking established.')
