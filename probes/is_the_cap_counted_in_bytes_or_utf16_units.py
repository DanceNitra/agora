"""`MAX_ENTRYPOINT_BYTES` is not bytes. Measured from outside, three ways.

The auto-memory index cap is documented as "the first 25KB", the constant is named
MAX_ENTRYPOINT_BYTES, and the load-time warning prints `(limit: 24.4KB)`. A public mirror
of `src/memdir/memdir.ts` computes the quantity being capped as `const byteCount =
trimmed.length` -- and in JavaScript, `String.prototype.length` is UTF-16 code units.

That distinction is invisible to an ASCII fixture, which is exactly why every measurement
of this cap I had made until now was blind to it: for ASCII, bytes == code points ==
UTF-16 units, so all three hypotheses predict the same cut and the experiment decides
nothing. Three fillers separate them:

  filler      per char:  UTF-8 bytes   code points   UTF-16 units
  ASCII 'x'                    1            1             1
  CJK   '中'                    3            1             1        <- separates bytes from units
  emoji '😀'                    4            1             2        <- separates code points from units

Each arm is 200 lines of a fixed character width, with a canary on EVERY line naming its
own line number, so the cut position is read out of the model's context at single-line
resolution rather than inferred from the file.

  If the cap counts BYTES        the CJK arm (61,600 B) cuts far earlier than the ASCII arm.
  If it counts CODE POINTS       the emoji arm cuts in the same place as the CJK arm.
  If it counts UTF-16 UNITS      CJK cuts with ASCII, and emoji cuts much earlier than both.

A fourth arm (CJK at 60 chars/line) sits under every reading of the cap and must load
whole; it is the negative control that would catch an instrument that truncates for some
reason unrelated to size.
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
from the_cost_curve_across_the_truncation_boundary import claude_bin  # noqa: E402

ASK = ("Respond with only: LAST=<the last CANARY-Lnnnn token you can see> || "
       "WARNING=<verbatim any line saying your index was truncated or partly loaded; "
       "else NO-INDICATOR>")

CASES = {
    # label            lines  width  filler         what it separates
    "ascii_200x125":   (200, 125, "x"),           # control: all three readings coincide
    "cjk_200x125":     (200, 125, "中"),      # bytes vs units
    "cjk_200x60":      (200, 60, "中"),       # negative control: under the cap either way
    "emoji_200x125":   (200, 125, "\U0001F600"),  # code points vs units
}

CLAUDE = None
_t0 = time.time()


def log(m: str) -> None:
    print(f"[{time.time() - _t0:6.1f}s] {m}", flush=True)


def run(cwd: str, prompt: str) -> tuple[str | None, str | None]:
    out = subprocess.run([CLAUDE, "-p", "--output-format", "stream-json", "--verbose"],
                         cwd=cwd, input=prompt, capture_output=True, text=True,
                         encoding="utf-8", errors="replace", timeout=900).stdout or ""
    store = ans = None
    for line in out.splitlines():
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("type") == "system" and d.get("subtype") == "init":
            store = (d.get("memory_paths") or {}).get("auto")
        elif d.get("type") == "result":
            ans = str(d.get("result") or "")
    return store, ans


def make(n_lines: int, width_chars: int, filler: str) -> str:
    lines = []
    for i in range(1, n_lines + 1):
        head = f"- [E{i:04d}](e-{i:04d}.md) CANARY-L{i:04d} "
        lines.append(head + filler * max(0, width_chars - len(head)))
    return "\n".join(lines) + "\n"


def main() -> int:
    global CLAUDE
    CLAUDE = claude_bin()
    root = tempfile.mkdtemp(prefix="unitprobe_")
    log(f"workspace={root}")
    rows = []
    for label, (n, w, ch) in CASES.items():
        cwd = os.path.join(root, label)
        os.makedirs(cwd, exist_ok=True)
        store, _ = run(cwd, "Reply with only: INIT")     # the store is READ, never constructed
        if not store:
            rows.append({"label": label, "error": "store not resolved"})
            continue
        text = make(n, w, ch)
        os.makedirs(store, exist_ok=True)
        path = os.path.join(store, "MEMORY.md")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        _, ans = run(cwd, ASK)
        head = (ans or "").split("WARNING")[0]
        m = re.search(r"CANARY-L(\d{4})", head)
        row = {
            "label": label, "lines": n, "width_chars": w, "filler_codepoint": ord(ch[0]),
            "bytes": os.path.getsize(path),
            "code_points": len(text),
            "utf16_units": len(text.encode("utf-16-le")) // 2,
            "last_line_loaded": int(m.group(1)) if m else None,
            "warned": "NO-INDICATOR" not in (ans or "").upper(),
            "answer": (ans or "")[:220],
        }
        rows.append(row)
        log(f"  {label:16s} bytes={row['bytes']:7d} cp={row['code_points']:7d} "
            f"u16={row['utf16_units']:7d} warned={row['warned']!s:5s} last={row['last_line_loaded']}")

    by = {r["label"]: r for r in rows if "error" not in r}
    v = {}
    if {"ascii_200x125", "cjk_200x125", "emoji_200x125", "cjk_200x60"} <= set(by):
        a, c, e, n = (by["ascii_200x125"], by["cjk_200x125"],
                      by["emoji_200x125"], by["cjk_200x60"])
        v["negative_control_loads_whole"] = (n["warned"] is False
                                             and n["last_line_loaded"] == n["lines"])
        v["not_bytes__cjk_cuts_where_ascii_cuts"] = (
            c["last_line_loaded"] == a["last_line_loaded"] and c["bytes"] > 2 * a["bytes"])
        v["not_code_points__emoji_cuts_earlier_at_equal_code_points"] = (
            e["code_points"] == c["code_points"]
            and e["last_line_loaded"] < c["last_line_loaded"])
        v["utf16_units_predict_both_cuts"] = all(
            abs(r["last_line_loaded"] - min(r["lines"], int(25000 / (r["utf16_units"] / r["lines"])))) <= 3
            for r in (a, c, e))
        v["warning_reports_units_over_1024_not_kb"] = bool(
            re.search(r"is (\d+\.\d+)KB", c["answer"]) and
            abs(float(re.search(r"is (\d+\.\d+)KB", c["answer"]).group(1))
                - c["utf16_units"] / 1024) < 0.6)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "is_the_cap_counted_in_bytes_or_utf16_units.result.json")
    json.dump({"probe": "is_the_cap_counted_in_bytes_or_utf16_units",
               "claude_version": subprocess.run([CLAUDE, "--version"], capture_output=True,
                                                text=True).stdout.strip(),
               "ask": ASK, "verdicts": v, "rows": rows},
              open(out, "w", encoding="utf-8"), indent=2)

    print("\n=== ROWS ===")
    print(f"{'arm':16s} {'bytes':>8} {'code pts':>9} {'utf16':>8} {'last line':>10}  warned")
    for r in rows:
        if "error" in r:
            print(f"{r['label']:16s} ERROR {r['error']}")
            continue
        print(f"{r['label']:16s} {r['bytes']:8d} {r['code_points']:9d} {r['utf16_units']:8d} "
              f"{str(r['last_line_loaded']):>10}  {r['warned']}")
    print("\n=== VERDICTS ===")
    for k, val in v.items():
        print(f"  {'YES' if val else 'no '}  {k}")
    log(f"wrote {out}")
    return 0 if all(v.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
