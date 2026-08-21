import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tex = open(os.path.join(ROOT, "agora_output", "edrn_final", "_main_snapshot.tex"),
           encoding="utf-8").read()

for m in re.finditer(r"\\begin\{table\*?\}(.*?)\\end\{table\*?\}", tex, re.S):
    blk = m.group(1)
    lab = re.search(r"\\label\{([^}]*)\}", blk)
    cap = re.search(r"\\caption\{(.*?)\}\s*\n", blk, re.S)
    tab = re.search(r"\\begin\{tabular\}\{([^}]*)\}(.*?)\\end\{tabular\}", blk, re.S)
    print("=" * 96)
    print("LABEL :", lab.group(1) if lab else "(none)")
    print("COLS  :", tab.group(1) if tab else "?")
    print("CAP   :", re.sub(r"\s+", " ", cap.group(1))[:190] if cap else "?")
    for line in (tab.group(2) if tab else "").splitlines():
        line = line.strip()
        if line and not re.match(r"\\(top|mid|bottom)rule", line):
            print("   ", line[:150])

print("\n" + "=" * 96)
print("GRAPH CONSTRUCTIONS mentioned in the text:")
for pat in (r"[^.]*ring[^.]*\.", r"[^.]*tree[^.]*\.", r"[^.]*random graph[^.]*\."):
    for mm in list(re.finditer(pat, tex, re.I))[:3]:
        s = re.sub(r"\s+", " ", mm.group(0)).strip()
        if len(s) > 40:
            print("  -", s[:230])
