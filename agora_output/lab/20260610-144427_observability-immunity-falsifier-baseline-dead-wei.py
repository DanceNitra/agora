
import sys, time
sys.path.insert(0, r'C:/Users/Danculus/agora/server')
from agora.execution.memory_economy import score_notes, prune_candidates
notes = score_notes(r'C:/Users/Danculus/my-second-brain')
cands = prune_candidates(r'C:/Users/Danculus/my-second-brain', 999)
n = len(notes)
dwf = len(cands) / max(1, n)
# value-distribution proxy for 'is the vault accruing dead weight or staying lean?'
import collections
hist = collections.Counter(x['value'] for x in notes)
low = sum(v for k, v in hist.items() if k <= 3)
print('FALSIFIER BASELINE %s (observability-as-immunity):' % time.strftime('%Y-%m-%d'))
print('  notes=%d dead_weight=%d dead_weight_fraction=%.4f%%' % (n, len(cands), 100*dwf))
print('  low-value(<=3) notes=%d (%.2f%%)' % (low, 100*low/max(1,n)))
print('  PREDICTION: with the Memory Economy + Night Shift instrumented, dead-weight fraction')
print('  should stay BOUNDED over coming weeks; an instrumented system converts decay into')
print('  signal faster than it accrues. Re-measure monthly; rising DWF would FALSIFY.')
