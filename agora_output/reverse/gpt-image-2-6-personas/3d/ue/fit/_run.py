import sys,io,contextlib,os
sys.path.insert(0,os.getcwd())
import fit_lib, ue_py
b=io.StringIO()
with contextlib.redirect_stdout(b): ue_py.run_file(sys.argv[1],timeout=int(sys.argv[2]) if len(sys.argv)>2 else 600)
o=b.getvalue(); print("\n".join(l for l in o.splitlines() if l.startswith(("PRM","WI","SET","COL","LOOK","BUILT","SMILE","LID","MRQ","PRESET","LASHES","LASHCARD","LASHGROOM","LIGHT","BROWPOST","BROW","BROWGROOM","HIDEBROWS","NOBROWS","SAVEDIR","RMBROW","PATCH","BOUND","OK","LIPS","RIGTEX","MAKEUP","BODYP")) or "rror" in l)[:8000])
