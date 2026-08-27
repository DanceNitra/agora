"""The selector arm scored below word-matching. This is the control that says why, and it was the size.

WHAT HAPPENED. In `can_the_right_memory_be_selected_from_one_index_line.py`, arm C -- the model given
the whole 30 KB index and asked which files to open -- reached recall@3 = 0.067, BELOW plain BM25 over
the same index lines (0.208) and barely above a random floor. A reader that understands language
cannot be three times worse than counting shared words on the identical text, so that number was an
instrument failure wearing the costume of a finding. The tell was in the outputs: 117 of 120 answers
named three files, and the same three reddit notes came back for "why does my script hang" and "how
do I start the dungeon" alike. It was not reading the question.

THE CONTROL. Identical model, identical queries, identical one-line surface -- only the haystack
shrinks, from all 315 candidates to 30 (the target plus 29 drawn at random). If the line were the
problem, nothing would change. Measured: recall@1 0.583, recall@3 0.658, and 98 distinct answers
across 120 queries instead of one constant triple.

So the collapse was the size of the haystack for THIS model, not the information in the line, and
arm C at full scale measures deepseek-v4-flash rather than the design. It says nothing about a
stronger reader, which is exactly why nothing was filed on the strength of it.

Run: python probes/the_selector_collapsed_on_haystack_size_not_on_the_line.py
"""
import json, os, pathlib, random, re, sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
ROOT = pathlib.Path(r"C:\Users\Danculus\agora")
sys.path.insert(0, str(ROOT/"server"))
for l in (ROOT/"server"/".env").read_text(encoding="utf-8").splitlines():
    if "=" in l and not l.lstrip().startswith("#"):
        k,v=l.split("=",1); os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
from agora.execution.llm_client import call_llm
d=json.load(open(ROOT/'probes/can_the_right_memory_be_selected_from_one_index_line.result.json',encoding='utf-8'))
rows=d['rows']
MEM=pathlib.Path(r"C:\Users\Danculus\.claude\projects\C--Users-Danculus-agora\memory")
idx=(MEM/"MEMORY.md").read_text(encoding="utf-8")+"\n"+(MEM/"MEMORY_ARCHIVE.md").read_text(encoding="utf-8")
line_for={}
for raw in idx.splitlines():
    for fn in re.findall(r"\]\(([^)]+\.md)\)", raw): line_for.setdefault(fn, raw.strip())
PICK=("You are choosing which memory files to open. Below are candidate index lines. "
      "Given the question, name up to THREE file names from them most likely to answer it. "
      "Output only file names, one per line, best first.")
rng=random.Random(7)
def run(r):
    others=rng.sample([f for f in line_for if f!=r['file']], 29)
    cands=[r['file']]+others; rng.shuffle(cands)
    block="\n".join(line_for[c] for c in cands)
    out=call_llm(PICK,"CANDIDATES:\n%s\n\nQUESTION: %s"%(block,r['query']),"cheap",0.0,16000) or ""
    got=[n for n in re.findall(r"[a-z0-9][a-z0-9._-]*\.md", out.lower()) if n in line_for][:3]
    return r['file'] in got[:1], r['file'] in got, got
hits1=hits3=0; outs=[]
with ThreadPoolExecutor(max_workers=10) as ex:
    for i,(h1,h3,got) in enumerate(ex.map(run, rows),1):
        hits1+=h1; hits3+=h3; outs.append(got)
        if i%20==0: print("  %d/%d"%(i,len(rows)), flush=True)
n=len(rows)
print("\nCONTROL -- 30 candidates instead of 315, same queries, same model, same one-line surface")
print("  recall@1 %.3f   recall@3 %.3f   (chance: 0.033 / 0.100)"%(hits1/n, hits3/n))
c=Counter(tuple(g) for g in outs)
print("  most repeated answer: %d of %d gave the identical triple"%(c.most_common(1)[0][1], n))
print("  distinct answers: %d"%len(c))
json.dump({"recall1":hits1/n,"recall3":hits3/n,"n":n,"distinct":len(c),
           "max_repeat":c.most_common(1)[0][1]},
          open(ROOT/'probes/can_the_right_memory_be_selected_from_one_index_line.control30.json','w'), indent=1)
