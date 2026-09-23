"""Every figure in the reply to Guanghao, recomputed from the three manuscript files.

The tool runs this; I do not. Inputs come from AGORA_INPUT_DIR so the tool can point it at
mutated copies, which is how it proves the check can fail.
"""
import io
import os

B = chr(92)
D = os.environ["AGORA_INPUT_DIR"]
F = {"base": "book_manuscript_2026-09-18.tex",
     "ours": "book_manuscript_2026-09-21_edits.tex",
     "theirs": "guanghao_0922.tex"}
PAT = [("ref", B + "ref{"), ("label", B + "label{"), ("range", "84.7"),
       ("tensorrg", "张量RG"), ("issue1", "Issue " + B + "#1"),
       ("orbitcheck", "5430290397"), ("fivearm", "五臂")]
EXPECT = {"base":   [0, 0, 3, 13, 0, 0, 5],
          "ours":   [2, 2, 2, 8, 1, 1, 7],
          "theirs": [0, 1, 3, 13, 0, 0, 5]}

counts = {}
for k, name in F.items():
    s = io.open(os.path.join(D, name), encoding="utf-8", errors="replace").read()
    counts[k] = [s.count(p) for _, p in PAT]

for k in ("base", "ours", "theirs"):
    got, want = counts[k], EXPECT[k]
    ok = got == want
    print("CLAIM row_%s %s the %s row of the table reads %s; measured %s"
          % (k, "PASS" if ok else "FAIL", k, want, got))

diff = sum(1 for x, y in zip(counts["base"], counts["theirs"]) if x != y)
print("CLAIM one_marker %s their file differs from the base on exactly one marker; measured %d"
      % ("PASS" if diff == 1 else "FAIL", diff))

print("CLAIM range_thrice %s the range sentence appears three times in their file; measured %d"
      % ("PASS" if counts["theirs"][2] == 3 else "FAIL", counts["theirs"][2]))

print("CLAIM no_refs %s their file carries no ref commands; measured %d"
      % ("PASS" if counts["theirs"][0] == 0 else "FAIL", counts["theirs"][0]))
