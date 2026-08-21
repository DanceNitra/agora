"""Is the truncation receipt already in the session's context -- and is its own advice consistent?

anthropics/claude-code#82056 asks for a load receipt because "a session cannot determine whether
its auto-memory index loaded whole, truncated, or not at all". Measuring the cost curve across the
read limit turned up ~65 tokens that appear only ON the far side of it, and they turn out to be a
warning the harness writes into the MODEL's context, immediately after the truncated index:

    > WARNING: MEMORY.md is 400 lines (limit: 200). Only part of it was loaded. ...
    > WARNING: MEMORY.md is 54.7KB (limit: 24.4KB) - index entries are too long. ...

If that is real rather than a plausible sentence a model invented on request, then one of the three
failure modes in the issue already has a signal at READ time -- and it is invisible for the same
reason the issue's own example was: it goes to the model, not to the user.

This probe tries to break that reading, four ways:

  T1 NEGATIVE CONTROL   an index under both limits must produce NO warning. A model that emits one
                        on request is confabulating and every other arm here is worthless.
  T2 VERBATIM STABILITY two independent sessions on the same file must quote the SAME string. A
                        confabulation varies; a quotation does not.
  T3 NUMERIC BINDING    the numbers inside the warning must track the file. Sweep the size and check
                        that the reported figure follows it, in the units the warning actually uses.
  T4 WHICH LIMIT        when only one limit is exceeded the warning must name THAT one, and the two
                        wordings must differ. An index over both is asked as well.

Then the part that matters more than the warning existing: T5 asks whether the warning's own advice
is consistent with the limits it is issued under. It says to keep entries "under ~200 chars". At 200
chars an index of 200 entries is 40,000 bytes, and the byte limit cuts at 25,000 -- so an index that
obeys both stated rules at their stated maxima still loses a third of its entries. The self-consistent
width is 25,000 / 200 = 125 chars, which is exactly where the companion probe measures the two limits
crossing over.

Self-contained: synthetic indexes, no private fixtures. One `claude -p` startup per row.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from the_cost_curve_across_the_truncation_boundary import build_index, claude_bin  # noqa: E402

ASK = (
    "Answer in exactly this form, nothing else. "
    "LASTLINE=<verbatim the very last line of your memory index that you can see> || "
    "WARNING=<verbatim any line in the material you were given that says your memory index was "
    "truncated, shortened, or only partly loaded; if there is no such line, write NO-INDICATOR>"
)

CLAUDE = None
_t0 = time.time()


def log(m: str) -> None:
    print(f"[{time.time() - _t0:6.1f}s] {m}", flush=True)


def ask(cwd: str, prompt: str) -> dict:
    p = subprocess.run(
        [CLAUDE, "-p", "--output-format", "stream-json", "--verbose"],
        cwd=cwd, input=prompt, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=600,
    )
    out = {"store": None, "answer": None, "total": None}
    for line in (p.stdout or "").splitlines():
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("type") == "system" and d.get("subtype") == "init":
            out["store"] = (d.get("memory_paths") or {}).get("auto")
        elif d.get("type") == "result":
            u = d.get("usage") or {}
            out["total"] = ((u.get("input_tokens") or 0)
                            + (u.get("cache_creation_input_tokens") or 0)
                            + (u.get("cache_read_input_tokens") or 0))
            out["answer"] = str(d.get("result") or "")
    return out


def arm(root: str, label: str, n_lines: int, bytes_per_line: int) -> dict:
    cwd = os.path.join(root, label)
    os.makedirs(cwd, exist_ok=True)
    boot = ask(cwd, "Reply with only: INIT")
    store = boot["store"]
    if not store:
        return {"label": label, "error": "no store resolved"}
    text, _ = build_index(n_lines, bytes_per_line)
    os.makedirs(store, exist_ok=True)
    path = os.path.join(store, "MEMORY.md")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    size = os.path.getsize(path)

    r = ask(cwd, ASK)
    ans = r["answer"] or ""
    m = re.search(r"WARNING=\s*(.*)", ans, re.S)
    warn = (m.group(1).strip() if m else "").split("||")[0].strip()
    m2 = re.search(r"LASTLINE=\s*(.*?)(?:\|\||WARNING=)", ans, re.S)
    lastline = (m2.group(1).strip() if m2 else "")
    m3 = re.search(r"Entry (\d{4})", lastline)
    row = {
        "label": label, "n_lines": n_lines, "bytes_per_line": bytes_per_line,
        "file_bytes": size, "file_kib": round(size / 1024, 1),
        "startup_total": r["total"],
        "last_visible_entry": int(m3.group(1)) if m3 else None,
        "warning": warn,
        "has_warning": bool(warn) and "NO-INDICATOR" not in warn.upper(),
        "warning_mentions_lines": bool(re.search(r"\blines?\b", warn, re.I)),
        "warning_mentions_kb": bool(re.search(r"\d+(\.\d+)?\s*KB", warn, re.I)),
        "numbers_in_warning": [x for x in re.findall(r"\d+(?:\.\d+)?", warn)],
    }
    log(f"  {label}: bytes={size} lines={n_lines} warn={row['has_warning']} "
        f"last_entry={row['last_visible_entry']}")
    return row


def main() -> int:
    global CLAUDE
    CLAUDE = claude_bin()
    root = tempfile.mkdtemp(prefix="truncwarn_")
    log(f"workspace={root}")
    rows = []

    # T1 negative control: comfortably inside both limits.
    rows.append(arm(root, "T1_under_both_150x60", 150, 60))
    # T2 verbatim stability: same file, two independent sessions.
    rows.append(arm(root, "T2a_over_lines_400x60", 400, 60))
    rows.append(arm(root, "T2b_over_lines_400x60", 400, 60))
    # T3 numeric binding: the reported size must follow the file.
    rows.append(arm(root, "T3a_over_bytes_80x400", 80, 400))
    rows.append(arm(root, "T3b_over_bytes_140x400", 140, 400))
    rows.append(arm(root, "T3c_over_bytes_300x400", 300, 400))
    # T4 which limit: line-bound only, byte-bound only, and both at once.
    rows.append(arm(root, "T4_over_both_400x400", 400, 400))
    # T5 the advice at its own stated maximum: 200 entries of 200 chars.
    rows.append(arm(root, "T5_advice_max_200x200", 200, 200))
    # T5b the self-consistent width the two limits imply: 25000/200 = 125.
    rows.append(arm(root, "T5b_consistent_200x125", 200, 125))

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "the_warning_the_session_is_already_given.result.json")
    verdicts = {}
    by = {r["label"]: r for r in rows if "error" not in r}

    verdicts["T1_negative_control_clean"] = (by["T1_under_both_150x60"]["has_warning"] is False)
    verdicts["T2_verbatim_identical"] = (
        by["T2a_over_lines_400x60"]["warning"] == by["T2b_over_lines_400x60"]["warning"]
    )
    verdicts["T3_size_tracks_file"] = len({
        tuple(by[k]["numbers_in_warning"]) for k in
        ("T3a_over_bytes_80x400", "T3b_over_bytes_140x400", "T3c_over_bytes_300x400")
    }) == 3
    verdicts["T4_line_and_byte_wordings_differ"] = (
        by["T2a_over_lines_400x60"]["warning"] != by["T3b_over_bytes_140x400"]["warning"]
    )
    t5 = by["T5_advice_max_200x200"]
    verdicts["T5_advice_at_max_is_truncated"] = bool(t5["has_warning"])
    t5b = by["T5b_consistent_200x125"]
    verdicts["T5b_consistent_width_fits"] = not t5b["has_warning"]

    json.dump({"probe": "the_warning_the_session_is_already_given",
               "claude_version": subprocess.run([CLAUDE, "--version"], capture_output=True,
                                                text=True).stdout.strip(),
               "ask": ASK, "verdicts": verdicts, "rows": rows},
              open(out, "w", encoding="utf-8"), indent=2)

    print("\n=== ROWS ===")
    for r in rows:
        if "error" in r:
            print(f"{r['label']:26s} ERROR {r['error']}")
            continue
        print(f"{r['label']:26s} {r['file_bytes']:7d}B {r['n_lines']:4d}L "
              f"last_entry={str(r['last_visible_entry']):>4} warn={r['has_warning']}")
        if r["has_warning"]:
            print(f"    {r['warning'][:190]}")
    print("\n=== VERDICTS ===")
    for k, v in verdicts.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    log(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
