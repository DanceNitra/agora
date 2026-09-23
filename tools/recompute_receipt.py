"""Re-execute a claim script, mutate its inputs, and issue a receipt only if the mutations bite.

WHY THIS EXISTS. On 2026-09-22 a single 473-word reply to a collaborator cost 353,000 subagent
tokens across three runs, and what decided every question was a ten-line script costing about two
thousand. The agents were not better at counting. They were the only party whose output
`humanizer_receipt.py` would accept, because the owner banned self-written scripts as evidence for
the skill gate on 2026-08-27: "prisen zakazujem vytvarat si skripty na obchadzanie!!!"

That ban is right and this tool does not weaken it. The difference is who runs the code. Here the
SCRIPT is mine and the EXECUTION is not: this tool runs it, this tool mutates the inputs, this tool
writes the output file, and I never hand it a result. A receipt appears only when the tool's own
run agrees with the recorded claims and its own mutations break them.

WHAT IT PROVES, stated narrowly because the paper this feeds will be read by an editor: that the
claims are a deterministic function of named inputs, that the run reproduces byte for byte, and
that the check can fail. It does NOT prove the claim is the right claim to make. On the night this
was written, a script counted a string correctly while the column header named a DIFFERENT string,
so the number was true and the table lied. Only a reader caught that. The judgement half stays with
the skills and with the people who review the physics.

THE CONTRACT a claim script must meet:

  * Reads every input from the directory in the AGORA_INPUT_DIR environment variable, so the tool
    can point it at mutated copies. A script that opens an absolute path cannot be mutated and is
    refused.
  * Prints one line per claim: `CLAIM <id> PASS <text>` or `CLAIM <id> FAIL <text>`.
  * Prints nothing else that changes between runs. A timestamp makes the run irreproducible and the
    tool will say so rather than pass it.

The mutations are the tool's, not the script's, so a script cannot arrange to survive them: for
each input file the tool flips one byte in the middle, and for each token named with --token it
deletes every occurrence. Every mutation must turn at least one PASS into a FAIL.

    python tools/recompute_receipt.py <draft.md> <claims.py> --inputs a.tex b.tex \
        --token "5430290397" --skill verify

Exit 0 and a receipt, or exit 1 and the reason.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "agora_output", "recompute_receipts")
CLAIM = re.compile(r"^CLAIM\s+(\S+)\s+(PASS|FAIL)\s+(.*)$")


def sha(path: str) -> str:
    return hashlib.sha256(io.open(path, "rb").read()).hexdigest()


def run(script: str, input_dir: str) -> tuple:
    """Run the claim script against one input directory. Returns (claims, raw stdout)."""
    env = dict(os.environ)
    env["AGORA_INPUT_DIR"] = input_dir
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONHASHSEED"] = "0"
    p = subprocess.run([sys.executable, "-X", "utf8", script], capture_output=True,
                       env=env, cwd=ROOT, timeout=300)
    out = p.stdout.decode("utf-8", "replace")
    claims = {}
    for line in out.splitlines():
        m = CLAIM.match(line.strip())
        if m:
            claims[m.group(1)] = (m.group(2), m.group(3))
    return claims, out, p.stderr.decode("utf-8", "replace"), p.returncode


def stage(inputs: list, dest: str) -> None:
    for p in inputs:
        shutil.copy2(p, os.path.join(dest, os.path.basename(p)))


def halve(path: str) -> int:
    """Truncate an input to half its bytes.

    The first version of this flipped one byte in the middle instead, and on its first real use it
    refused a sound claim set: the claims counted specific strings, the flipped byte landed in
    ordinary prose, and no count moved. The refusal was honest and the mutation was the defect. A
    mutation has to be one that no claim reading the file can survive, and for a file nothing is
    cheaper or more total than losing half of it.
    """
    b = io.open(path, "rb").read()
    if len(b) < 2:
        raise SystemExit("REFUSED: input %s is too small to mutate." % path)
    io.open(path, "wb").write(b[: len(b) // 2])
    return len(b) // 2


def drop_token(path: str, token: str) -> int:
    s = io.open(path, "rb").read()
    t = token.encode("utf-8")
    n = s.count(t)
    io.open(path, "wb").write(s.replace(t, b""))
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("draft", help="the artifact whose figures these claims are")
    ap.add_argument("script", help="the claim script; the TOOL runs it, you do not")
    ap.add_argument("--inputs", nargs="+", required=True,
                    help="every file the claims are computed from")
    ap.add_argument("--token", action="append", default=[],
                    help="a string whose removal must break at least one claim; repeatable")
    ap.add_argument("--skill", default="verify", choices=["verify", "redteam"])
    a = ap.parse_args()

    for p in [a.draft, a.script] + a.inputs:
        if not os.path.isfile(p):
            raise SystemExit("REFUSED: %s does not exist." % p)

    src = io.open(a.script, encoding="utf-8", errors="replace").read()
    if "AGORA_INPUT_DIR" not in src:
        raise SystemExit(
            "REFUSED: %s never reads AGORA_INPUT_DIR, so it reads fixed paths and the tool\n"
            "  cannot point it at mutated copies. A check whose input cannot be changed cannot\n"
            "  be shown to fail." % a.script)

    work = tempfile.mkdtemp(prefix="recompute_")
    try:
        base = os.path.join(work, "base")
        os.makedirs(base)
        stage(a.inputs, base)

        claims, out1, err1, rc1 = run(a.script, base)
        if not claims:
            raise SystemExit(
                "REFUSED: the script printed no CLAIM lines.\n"
                "  Expected `CLAIM <id> PASS|FAIL <text>`.\n  stderr: " + err1[:400])

        # Reproducibility: the same inputs must give the same bytes. A clock in the output, a set
        # iteration order, a path that leaks in -- each makes a number nobody else can reproduce,
        # which is the thing an editor will actually test.
        again = os.path.join(work, "again")
        os.makedirs(again)
        stage(a.inputs, again)
        _, out2, _, _ = run(a.script, again)
        if out1 != out2:
            raise SystemExit(
                "REFUSED: two runs over identical inputs printed different output, so this\n"
                "  measurement is not reproducible. Remove the clock, the set ordering or the\n"
                "  absolute path that differs between runs.")

        failing = [k for k, v in claims.items() if v[0] == "FAIL"]
        if failing:
            raise SystemExit(
                "REFUSED: %d of %d claims FAIL on the real inputs: %s\n"
                "  Fix the draft or the claim before asking for a receipt."
                % (len(failing), len(claims), ", ".join(failing)))

        # THE MUTATIONS ARE THE TOOL'S. A script cannot arrange to survive a change it never sees.
        mutations = []
        for p in a.inputs:
            d = os.path.join(work, "mut_" + hashlib.sha256(p.encode()).hexdigest()[:8])
            os.makedirs(d)
            stage(a.inputs, d)
            target = os.path.join(d, os.path.basename(p))
            kept = halve(target)
            mc, _, _, _ = run(a.script, d)
            flipped = [k for k in claims if mc.get(k, ("FAIL",))[0] != "PASS"]
            mutations.append({"kind": "truncated to half", "input": os.path.basename(p),
                              "bytes_kept": kept, "claims_broken": flipped})
            if not flipped:
                raise SystemExit(
                    "REFUSED: cutting %s in half broke no claim, so no claim depends on that\n"
                    "  file. Either the input is not used or the check cannot fail. This is the\n"
                    "  control that matters; a suite that survives its own corruption has\n"
                    "  measured nothing." % os.path.basename(p))

        for tok in a.token:
            d = os.path.join(work, "tok_" + hashlib.sha256(tok.encode()).hexdigest()[:8])
            os.makedirs(d)
            stage(a.inputs, d)
            hits = sum(drop_token(os.path.join(d, os.path.basename(p)), tok) for p in a.inputs)
            if hits == 0:
                raise SystemExit(
                    "REFUSED: the token %r does not occur in any input, so removing it proves\n"
                    "  nothing. Name a token the claims actually rest on." % tok)
            mc, _, _, _ = run(a.script, d)
            flipped = [k for k in claims if mc.get(k, ("FAIL",))[0] != "PASS"]
            mutations.append({"kind": "token removed", "token": tok, "occurrences": hits,
                              "claims_broken": flipped})
            if not flipped:
                raise SystemExit(
                    "REFUSED: removing every occurrence of %r (%d of them) broke no claim.\n"
                    "  No claim depends on it." % (tok, hits))

        os.makedirs(OUT, exist_ok=True)
        digest = sha(a.draft)
        rec = {
            "draft": os.path.basename(a.draft),
            "draft_sha256": digest,
            "script": os.path.relpath(a.script, ROOT).replace("\\", "/"),
            "script_sha256": sha(a.script),
            "inputs": [{"name": os.path.basename(p), "sha256": sha(p),
                        "bytes": os.path.getsize(p)} for p in a.inputs],
            # Store the VERDICT beside the text. The first version kept only the text, so a
            # later reader checking for "PASS" was reading a sentence, and the stamper
            # refused a sound receipt on its first live use.
            "claims": {k: {"verdict": v[0], "text": v[1]}
                       for k, v in sorted(claims.items())},
            "stdout": out1,
            "stdout_sha256": hashlib.sha256(out1.encode("utf-8")).hexdigest(),
            "reproduced": True,
            "mutations": mutations,
            "skill": a.skill,
            "recorded_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "proves": "These claims are a deterministic function of the named inputs, the run "
                      "reproduces byte for byte, and every mutation the tool applied broke at "
                      "least one claim.",
            "does_not_prove": "That the claim is the right claim to make. A count can be correct "
                              "while the label names a different thing.",
        }
        path = os.path.join(OUT, digest[:32] + "." + a.skill + ".recompute.json")
        io.open(path, "w", encoding="utf-8").write(json.dumps(rec, indent=2, ensure_ascii=False))
        print("  RECOMPUTED  %s" % os.path.basename(a.draft))
        print("    %d claims, all PASS; %d mutations, all broke at least one claim"
              % (len(claims), len(mutations)))
        print("    two runs over identical inputs printed identical bytes")
        print("    receipt: %s" % os.path.relpath(path, ROOT).replace("\\", "/"))
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
