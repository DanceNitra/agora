"""Does the startup cost of an auto-memory index keep rising past the read limit?

CONTEXT (anthropics/claude-code#82056). @yacb2 measured the startup cost of `MEMORY.md`
with Claude's own token accounting and fitted `122 + 0.435 tok/byte` over four indexes of
335 - 11,206 bytes. Every one of those four sits BELOW the documented read limit ("the
first 200 lines of MEMORY.md, or the first 25KB, whichever comes first"). This probe asks
what the same instrument reports on the other side of that limit, and what a session can
still see there.

Two claims are under test, and they are separable:

  H1 (COST)       cost is linear in bytes below the limit and FLAT above it, because the
                  bytes above the cut are never read. If true, the startup delta is a
                  free load receipt while you are under the limit -- and stops being one
                  at exactly the moment you cross, which is when you need it.

  H2 (MEMBERSHIP) which limit binds -- 200 lines or 25 KB -- depends on the SHAPE of the
                  index, and the two give opposite advice. Under a byte-bound index,
                  shortening entries buys membership. Under a line-bound one it buys
                  nothing at all: entry 201 is absent whatever it weighs.

Two sweeps on orthogonal axes, the method @yacb2 used to separate per-byte from per-entry:

  LINE sweep   60 B/line, 50..400 lines  -> crosses 200 lines while staying under 25 KB
  BYTE sweep  400 B/line, 20..140 lines  -> crosses 25 KB while staying under 200 lines

MEMBERSHIP is measured, not inferred. Every 10th line carries a self-describing canary
`CANARY-Lnnnn` naming its own line number, and the session is asked to echo the first and
the last one it can see. The last canary IS the cut position, read out of the model's
context rather than computed from the file.

CONTROLS, because an instrument that never sees its target reports SAFE:
  C1 store resolution -- the store path is READ from the harness (`memory_paths.auto` in
     the stream-json init event), never constructed from the project path. This is the
     failure that recorded `MEMORY.md = 0 bytes` for 24 projects in @yacb2's own inventory
     and produced "a clean negative result that happened to be false". Asserted per arm.
  C2 positive control -- CANARY-L0001 must come back on every index arm. If the first line
     of the file is not visible, the instrument is not reading the index at all.
  C3 negative control -- any canary echoed that was never written is a hallucination; the
     arm is marked invalid rather than averaged in.
  C4 baseline adjacency -- every arm measures its own empty baseline in its own fresh
     project directory, immediately before the index run, so hook and environment cost
     cancels in the delta rather than being assumed constant.
  C5 determinism -- REPEATS re-runs whole arms end to end and reports the spread.

Self-contained: the indexes are synthetic, so this runs on anyone's machine with no
private fixtures. Costs one `claude -p` startup per run.

Usage:  python probes/the_cost_curve_across_the_truncation_boundary.py [--workers N] [--repeats N]
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time

# One line, and delivered on stdin: a multi-line -p argument is mangled by the Windows
# .CMD shim and silently drops --output-format, which returns prose instead of stream-json.
PROMPT = (
    "Your memory index contains lines carrying tokens of the form CANARY-Lnnnn. "
    "Respond with only these three assignments, space separated, nothing else: "
    "FIRST=<the first such token you can see> LAST=<the last such token you can see> "
    "COUNT=<how many you can see>. If you can see none: FIRST=NONE LAST=NONE COUNT=0."
)

CANARY_EVERY = 10
CANARY_RE = re.compile(r"CANARY-L(\d{4})")

# The documented limit, for reference lines in the report only -- nothing here assumes it.
DOC_LINE_LIMIT = 200
DOC_BYTE_LIMIT = 25_000

_print_lock = threading.Lock()
_t0 = time.time()


def log(msg: str) -> None:
    with _print_lock:
        print(f"[{time.time() - _t0:7.1f}s] {msg}", flush=True)


def claude_bin() -> str:
    for cand in ("claude", "claude.cmd", "claude.CMD"):
        p = shutil.which(cand)
        if p:
            return p
    raise SystemExit("claude CLI not found on PATH")


CLAUDE = None  # resolved in main()


def build_index(n_lines: int, bytes_per_line: int, canary_every: int = CANARY_EVERY) -> tuple[str, list[int]]:
    """A synthetic index shaped like a real one: `- [Title](slug.md) - hook`.

    Every CANARY_EVERY-th line (and line 1) carries a canary naming its own line number.
    Lines are padded to bytes_per_line so that byte count and line count move independently.
    """
    lines: list[str] = []
    canary_lines: list[int] = []
    for i in range(1, n_lines + 1):
        canary = ""
        if i == 1 or i % canary_every == 0:
            canary = f"CANARY-L{i:04d} "
            canary_lines.append(i)
        head = f"- [Entry {i:04d}](entry-{i:04d}.md) - {canary}"
        pad = bytes_per_line - len(head) - 1  # -1 for the newline
        if pad < 0:
            raise ValueError(f"bytes_per_line={bytes_per_line} too small for line {i}")
        # filler that reads like prose rather than a repeated character
        filler = ("measured note about entry state and why it mattered " * 40)[:pad]
        lines.append(head + filler)
    return "\n".join(lines) + "\n", canary_lines


def run_claude(cwd: str) -> dict:
    """One `claude -p` turn. Returns startup token total, the answer, and the resolved store."""
    cmd = [CLAUDE, "-p", "--output-format", "stream-json", "--verbose"]
    t = time.time()
    proc = subprocess.run(
        cmd, cwd=cwd, input=PROMPT, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=600,
    )
    out = {
        "elapsed_s": round(time.time() - t, 2),
        "startup_total": None,
        "usage": None,
        "answer": None,
        "memory_path": None,
        "hook_stdout_bytes": 0,
        "returncode": proc.returncode,
        "stderr_tail": (proc.stderr or "")[-300:],
    }
    for line in (proc.stdout or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("type") == "system":
            if d.get("subtype") == "init":
                mp = d.get("memory_paths") or {}
                out["memory_path"] = mp.get("auto")
            elif d.get("subtype") == "hook_response":
                out["hook_stdout_bytes"] += len(d.get("stdout") or "")
        elif d.get("type") == "result":
            u = d.get("usage") or {}
            out["usage"] = {
                k: u.get(k) for k in
                ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")
            }
            out["startup_total"] = (
                (u.get("input_tokens") or 0)
                + (u.get("cache_creation_input_tokens") or 0)
                + (u.get("cache_read_input_tokens") or 0)
            )
            out["answer"] = str(d.get("result") or "")
    return out


def parse_canaries(answer: str) -> dict:
    first = last = None
    m = re.search(r"FIRST=\s*(\S+)", answer or "")
    if m:
        first = m.group(1)
    m = re.search(r"LAST=\s*(\S+)", answer or "")
    if m:
        last = m.group(1)
    m = re.search(r"COUNT=\s*(\d+)", answer or "")
    count = int(m.group(1)) if m else None

    def lineno(tok):
        if not tok:
            return None
        mm = CANARY_RE.search(tok)
        return int(mm.group(1)) if mm else None

    return {
        "first_token": first, "last_token": last, "count_reported": count,
        "first_line": lineno(first), "last_line": lineno(last),
        "all_seen": sorted({int(x) for x in CANARY_RE.findall(answer or "")}),
    }


def run_arm(arm: dict, root: str, tag: str) -> dict:
    """baseline (fresh dir, no index) -> learn the store from the harness -> write index -> measure."""
    name = f"{tag}_{arm['sweep']}_{arm['n_lines']}x{arm['bytes_per_line']}c{arm.get('canary_every', CANARY_EVERY)}"
    cwd = os.path.join(root, name)
    os.makedirs(cwd, exist_ok=True)
    res = dict(arm)
    res["arm"] = name

    base = run_claude(cwd)                                    # C4: own baseline, adjacent
    res["baseline_total"] = base["startup_total"]
    res["baseline_hook_bytes"] = base["hook_stdout_bytes"]
    store = base["memory_path"]                               # C1: ASK, never construct
    res["store_path"] = store
    if not store or base["startup_total"] is None:
        res["valid"] = False
        res["invalid_reason"] = f"baseline failed rc={base['returncode']} {base['stderr_tail']}"
        log(f"  !! {name}: {res['invalid_reason']}")
        return res

    text, canary_lines = build_index(arm["n_lines"], arm["bytes_per_line"], arm.get("canary_every", CANARY_EVERY))
    os.makedirs(store, exist_ok=True)
    path = os.path.join(store, "MEMORY.md")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    res["index_bytes"] = os.path.getsize(path)
    res["index_lines"] = arm["n_lines"]
    res["canary_lines"] = canary_lines

    idx = run_claude(cwd)
    res["index_total"] = idx["startup_total"]
    res["index_hook_bytes"] = idx["hook_stdout_bytes"]
    res["answer"] = (idx["answer"] or "")[:400]
    res["elapsed_s"] = base["elapsed_s"] + idx["elapsed_s"]

    if idx["startup_total"] is None:
        res["valid"] = False
        res["invalid_reason"] = f"index run failed rc={idx['returncode']} {idx['stderr_tail']}"
        log(f"  !! {name}: {res['invalid_reason']}")
        return res

    # C1: the store the index run resolved must be the store we wrote to.
    res["store_matches"] = (idx["memory_path"] == store)
    res["delta"] = idx["startup_total"] - base["startup_total"]

    c = parse_canaries(idx["answer"] or "")
    res.update({f"canary_{k}": v for k, v in c.items()})
    top = canary_lines[:2]                                               # C2
    res["pos_control_first_line_seen"] = (c["first_line"] in top)
    hallucinated = [x for x in c["all_seen"] if x not in canary_lines]   # C3
    res["hallucinated_canaries"] = hallucinated
    res["hook_bytes_stable"] = (base["hook_stdout_bytes"] == idx["hook_stdout_bytes"])

    res["valid"] = bool(
        res["store_matches"] and res["pos_control_first_line_seen"] and not hallucinated
    )
    if not res["valid"]:
        res["invalid_reason"] = (
            f"store_matches={res['store_matches']} pos_control={res['pos_control_first_line_seen']} "
            f"hallucinated={hallucinated}"
        )
    log(
        f"  {name}: bytes={res['index_bytes']:6d} lines={arm['n_lines']:4d} "
        f"delta={res['delta']:+7d} last_canary_line={c['last_line']} valid={res['valid']}"
    )
    return res


def main() -> int:
    global CLAUDE
    ap = argparse.ArgumentParser()
    # Serial by default ON PURPOSE: concurrent `claude -p` runs share the prompt cache,
    # which is the quantity being measured. Membership (canaries) is unaffected by
    # concurrency; the token deltas are not.
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--repeats", type=int, default=1, help="whole-probe repeats for C5")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    CLAUDE = claude_bin()

    arms: list[dict] = []
    # LINE sweep: crosses the 200-line limit while every index stays under 25 KB.
    for n in (50, 100, 150, 200, 250, 300, 400):
        arms.append({"sweep": "line", "n_lines": n, "bytes_per_line": 60})
    # BYTE sweep: crosses 25 KB while every index stays under 200 lines.
    for n in (20, 40, 60, 80, 100, 140):
        arms.append({"sweep": "byte", "n_lines": n, "bytes_per_line": 400})
    # SHAPE sweep: total bytes held far above BOTH limits, only the line WIDTH varies.
    # If the two limits are min()-combined, the cut lands at min(200, 25000/width) --
    # so the same 36 KB file loses entry 201 at width 60 and entry 126 at width 200.
    # Canaries every 2 lines here: the prediction is a position, not a direction.
    for bpl in (60, 100, 125, 150, 200, 400):
        arms.append({"sweep": "shape", "n_lines": max(210, 36000 // bpl),
                     "bytes_per_line": bpl, "canary_every": 2})

    for a in arms:
        a["nominal_bytes"] = a["n_lines"] * a["bytes_per_line"]

    root = tempfile.mkdtemp(prefix="idxcost_")
    log(f"claude={CLAUDE}")
    log(f"workspace={root}")
    log(f"arms={len(arms)} repeats={args.repeats} workers={args.workers} "
        f"-> {len(arms) * args.repeats * 2} claude startups")

    rows: list[dict] = []
    jobs = [(a, f"r{r}") for r in range(args.repeats) for a in arms]
    done = 0
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(run_arm, a, root, tag): (a, tag) for a, tag in jobs}
        for fut in cf.as_completed(futs):
            a, tag = futs[fut]
            done += 1
            try:
                rows.append(fut.result())
            except Exception as e:  # noqa: BLE001
                rows.append({**a, "arm": f"{tag}_{a['sweep']}_{a['n_lines']}",
                             "valid": False, "invalid_reason": f"exception: {e!r}"})
                log(f"  !! exception on {a}: {e!r}")
            log(f"progress {done}/{len(jobs)}")

    # C6: robust baseline. Empty-project startup is near-constant, so an outlier is
    # detectable rather than absorbed. Deltas are reported against BOTH the arm's own
    # adjacent baseline (C4) and the median across arms, and any arm whose own baseline
    # departs from the median is marked invalid with the reason kept, not dropped.
    bl = sorted(r["baseline_total"] for r in rows if r.get("baseline_total") is not None)
    med = bl[len(bl) // 2] if bl else None
    tol = 500
    for r in rows:
        r["baseline_median"] = med
        b = r.get("baseline_total")
        if med is None or b is None or r.get("index_total") is None:
            continue
        r["baseline_offset"] = b - med
        r["delta_vs_median"] = r["index_total"] - med
        if abs(b - med) > tol:
            r["valid"] = False
            r["invalid_reason"] = (
                f"{r.get('invalid_reason', '')} baseline_outlier={b} vs median={med}".strip()
            )
            log(f"  !! {r['arm']}: baseline outlier {b} vs median {med} -> arm invalidated")

    out_path = args.out or os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "the_cost_curve_across_the_truncation_boundary.result.json",
    )
    payload = {
        "probe": "the_cost_curve_across_the_truncation_boundary",
        "prompt": PROMPT,
        "canary_every": CANARY_EVERY,
        "doc_limits": {"lines": DOC_LINE_LIMIT, "bytes": DOC_BYTE_LIMIT},
        "workspace": root,
        "claude_version": subprocess.run(
            [CLAUDE, "--version"], capture_output=True, text=True
        ).stdout.strip(),
        "rows": sorted(rows, key=lambda r: (r.get("sweep", ""), r.get("n_lines", 0), r.get("arm", ""))),
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    log(f"wrote {out_path}")

    valid = [r for r in rows if r.get("valid")]
    log(f"valid arms: {len(valid)}/{len(rows)}")
    for sweep in ("line", "byte"):
        sel = sorted([r for r in valid if r["sweep"] == sweep], key=lambda r: r["index_bytes"])
        if not sel:
            continue
        print(f"\n=== {sweep.upper()} sweep ===")
        print(f"{'bytes':>7} {'lines':>6} {'B/line':>7} {'delta':>8} {'tok/byte':>9} "
              f"{'cut_line':>9} {'predicted':>10}")
        for r in sel:
            pred = min(DOC_LINE_LIMIT, DOC_BYTE_LIMIT // r['bytes_per_line'])
            pred = min(pred, r['index_lines'])
            dm = r.get("delta_vs_median")
            print(f"{r['index_bytes']:7d} {r['index_lines']:6d} {r['bytes_per_line']:7d} {dm:8d} "
                  f"{dm / r['index_bytes']:9.3f} {str(r.get('canary_last_line')):>9} {pred:10d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
