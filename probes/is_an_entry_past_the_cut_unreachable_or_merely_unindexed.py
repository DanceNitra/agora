"""An entry past the cut is absent from the index. Is the KNOWLEDGE still reachable?

This closes the caveat I named myself on anthropics/claude-code#82056 and then could not
answer: "I measured position and opening, never value. No session in the sample is checked
for a downstream cost traceable to a memory that got cut. 'Below the cut' is treated as
harm by assumption. If sessions recover missing context by other means, this is an index
inefficiency rather than a correctness defect, and I cannot currently tell those two apart."

The two are separable by experiment. A fact lives in a topic file on disk; the index line
pointing at it sits either inside the load window or outside it; the file is present either
way. Then ask a question only that file answers.

  INSIDE   index line at line 50 of 400   -> the pointer is in context
  OUTSIDE  index line at line 300 of 400  -> the pointer is not; the file still exists
  ABSENT   no topic file at all           -> the negative control

If OUTSIDE answers, the entry was unindexed but not unreachable: the session found the file
some other way, and losing index membership costs search effort rather than knowledge. If
OUTSIDE fails while INSIDE succeeds, membership loss is knowledge loss, and the arithmetic
about which cap binds is about correctness rather than efficiency.

ABSENT is what makes the other two mean anything. If the model answers with the fact when
no file holds it, it is producing the answer from the question and every arm is void.

Tools are allowed (Read/Grep/Glob) precisely because the interesting case is a session that
goes looking. Denying it tools would guarantee the answer I expect.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from the_cost_curve_across_the_truncation_boundary import build_index, claude_bin  # noqa: E402

CLAUDE = None
_t0 = time.time()

# A fact no model can know and no question can imply: an arbitrary number attached to an
# arbitrary named procedure. If it comes back, it was read.
FACT_FILE = "rotation-policy.md"
FACT_BODY = (
    "---\nname: rotation-policy\ndescription: how often the Halberd deploy key is rotated\n---\n\n"
    "The Halberd deploy key is rotated every 47 days, and the rotation is performed by the "
    "Cartographer role rather than the Engineering lead. This was decided after a 3-day outage.\n"
)
INDEX_LINE = ("- [Halberd deploy key rotation](rotation-policy.md) — how often the Halberd deploy "
              "key rotates and who performs it")
QUESTION = ("How often is the Halberd deploy key rotated, and who performs the rotation? "
            "Answer in one short sentence. If you do not know, reply exactly: I DO NOT KNOW.")


def log(m: str) -> None:
    print(f"[{time.time() - _t0:6.1f}s] {m}", flush=True)


def run(cwd: str, prompt: str, allow_tools: bool) -> dict:
    cmd = [CLAUDE, "-p", "--output-format", "stream-json", "--verbose"]
    if allow_tools:
        cmd += ["--allowedTools", "Read,Grep,Glob"]
    p = subprocess.run(cmd, cwd=cwd, input=prompt, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=900)
    out = {"store": None, "answer": None, "tools": [], "returncode": p.returncode}
    for line in (p.stdout or "").splitlines():
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("type") == "system" and d.get("subtype") == "init":
            out["store"] = (d.get("memory_paths") or {}).get("auto")
        elif d.get("type") == "assistant":
            for blk in (d.get("message") or {}).get("content") or []:
                if isinstance(blk, dict) and blk.get("type") == "tool_use":
                    out["tools"].append(blk.get("name"))
        elif d.get("type") == "result":
            out["answer"] = str(d.get("result") or "")
    return out


def arm(root: str, label: str, place: str | None, allow_tools: bool) -> dict:
    """place: 'inside' | 'outside' | None (no topic file, no index line)."""
    cwd = os.path.join(root, f"{label}_{'tools' if allow_tools else 'notools'}")
    os.makedirs(cwd, exist_ok=True)
    boot = run(cwd, "Reply with only: INIT", False)
    store = boot["store"]
    if not store:
        return {"label": label, "error": "store not resolved"}
    os.makedirs(store, exist_ok=True)

    text, _ = build_index(400, 60)          # 400 lines: the cut lands at line 200
    lines = text.split("\n")
    if place is not None:
        at = 50 if place == "inside" else 300
        lines[at - 1] = INDEX_LINE
        with open(os.path.join(store, FACT_FILE), "w", encoding="utf-8", newline="\n") as f:
            f.write(FACT_BODY)
    with open(os.path.join(store, "MEMORY.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))

    r = run(cwd, QUESTION, allow_tools)
    ans = (r["answer"] or "")
    got_days = "47" in ans
    got_role = "cartograph" in ans.lower()
    row = {
        "label": label, "place": place, "tools_allowed": allow_tools,
        "index_line_at": (50 if place == "inside" else 300) if place else None,
        "topic_file_present": place is not None,
        "answer": ans[:300], "tools_used": r["tools"],
        "found_days": got_days, "found_role": got_role,
        "answered": got_days and got_role,
        "said_dont_know": "DO NOT KNOW" in ans.upper(),
    }
    log(f"  {label:26s} tools={allow_tools!s:5s} answered={row['answered']!s:5s} "
        f"tools_used={r['tools']} | {ans[:80]!r}")
    return row


def main() -> int:
    global CLAUDE
    CLAUDE = claude_bin()
    root = tempfile.mkdtemp(prefix="reachable_")
    log(f"workspace={root}")
    rows = []
    for allow in (True, False):
        rows.append(arm(root, "A_inside_window", "inside", allow))
        rows.append(arm(root, "B_outside_window", "outside", allow))
        rows.append(arm(root, "C_no_file_at_all", None, allow))

    by = {(r["label"], r["tools_allowed"]): r for r in rows if "error" not in r}
    verdicts = {}
    for allow in (True, False):
        a, b, c = (by.get(("A_inside_window", allow)), by.get(("B_outside_window", allow)),
                   by.get(("C_no_file_at_all", allow)))
        if not (a and b and c):
            continue
        tag = "with_tools" if allow else "without_tools"
        verdicts[f"{tag}__negative_control_clean"] = not c["answered"]
        verdicts[f"{tag}__inside_answers"] = a["answered"]
        verdicts[f"{tag}__outside_answers"] = b["answered"]
        verdicts[f"{tag}__membership_loss_is_knowledge_loss"] = a["answered"] and not b["answered"]

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "is_an_entry_past_the_cut_unreachable_or_merely_unindexed.result.json")
    json.dump({"probe": "is_an_entry_past_the_cut_unreachable_or_merely_unindexed",
               "question": QUESTION, "fact_file": FACT_FILE,
               "claude_version": subprocess.run([CLAUDE, "--version"], capture_output=True,
                                                text=True).stdout.strip(),
               "verdicts": verdicts, "rows": rows},
              open(out, "w", encoding="utf-8"), indent=2)

    print("\n=== ROWS ===")
    for r in rows:
        if "error" in r:
            print(f"{r['label']:26s} ERROR {r['error']}")
            continue
        print(f"{r['label']:26s} tools={r['tools_allowed']!s:5s} line={str(r['index_line_at']):>4} "
              f"answered={r['answered']!s:5s} used={r['tools_used']}")
        print(f"    {r['answer'][:150]!r}")
    print("\n=== VERDICTS ===")
    for k, v in verdicts.items():
        print(f"  {'YES' if v else 'no ':3s}  {k}")
    log(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
