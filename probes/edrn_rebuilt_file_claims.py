"""Every figure in the 2026-09-23 reply to Guanghao, recomputed from the two manuscript files.

The seal on that reply certifies the FILE handed over in the gist, not the letter: its sha256, and
the seven marker counts of the table, before (his 22 September file) and after (the rebuilt file).
The tool runs this; I do not. Inputs come from AGORA_INPUT_DIR so the tool can point it at mutated
copies, which is how it shows the check can fail.
"""
import hashlib
import io
import os

B = chr(92)
D = os.environ["AGORA_INPUT_DIR"]
F = {"before": "guanghao_0922.tex", "after": "book_manuscript_2026-09-23_rebuilt.tex"}
GIST_SHA256 = "f9cf531d2ec133b31bd66b17abfa257b14d6279d2e7a40497762eced029bba31"
PAT = [("ref", B + "ref{"), ("label", B + "label{"), ("range", "84.7"),
       ("tensorrg", "张量RG"), ("issue1", "Issue " + B + "#1"),
       ("orbitcheck", "5430290397"), ("fivearm", "五臂")]
EXPECT = {"before": [0, 1, 3, 13, 0, 0, 5],
          "after":  [2, 2, 2, 8, 1, 1, 7]}

raw = {k: io.open(os.path.join(D, n), "rb").read() for k, n in F.items()}
text = {k: v.decode("utf-8", errors="replace") for k, v in raw.items()}

got_sha = hashlib.sha256(raw["after"]).hexdigest()
print("CLAIM gist_bytes %s the rebuilt file hashes to the gist's sha256 %s...; measured %s..."
      % ("PASS" if got_sha == GIST_SHA256 else "FAIL", GIST_SHA256[:16], got_sha[:16]))

for k in ("before", "after"):
    got = [text[k].count(p) for _, p in PAT]
    for (name, p), g, w in zip(PAT, got, EXPECT[k]):
        print("CLAIM %s_%s %s %s count in the %s file is %d; measured %d"
              % (k, name, "PASS" if g == w else "FAIL", name, k, w, g))
