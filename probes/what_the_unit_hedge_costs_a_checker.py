"""@pjt222's dual-unit budget check is SAFE but not free. This prices the hedge.

agent-almanac#407 proposes a memory-index budget checker and deliberately refuses to pick a
unit, because the runtime's unit was unknown:

    text  = raw.decode('utf-8', 'replace').strip()
    chars = len(text)
    size  = max(len(raw), chars)          # conservative: whichever unit is larger
    usage = max(size / 25000, lines / 200)

That is the right call under uncertainty, and it fails safe: for UTF-8, byte count is
always >= UTF-16 unit count, so `max` never under-reports. But the unit is knowable --
measured on Claude Code v2.1.238, the quantity capped is UTF-16 code units -- and once it
is known the hedge stops being free. This computes both against fixtures whose true cut
position was measured, so the gap is a number rather than an argument.

No network, no model calls: pure arithmetic over
`is_the_cap_counted_in_bytes_or_utf16_units.result.json`, which holds the measured last
line loaded for each fixture.
"""
from __future__ import annotations
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "is_the_cap_counted_in_bytes_or_utf16_units.result.json")
CAP_UNITS, CAP_LINES = 25_000, 200


def main() -> int:
    rows = [r for r in json.load(open(SRC, encoding="utf-8"))["rows"] if "error" not in r]
    print(f"{'fixture':16s} {'bytes':>7} {'cps':>7} {'u16':>7} | "
          f"{'#407 usage':>10} {'true usage':>10} {'over-report':>11} | "
          f"{'#407 says fits':>14} {'really loaded':>13}")
    out = []
    for r in rows:
        b, cp, u16, lines = r["bytes"], r["code_points"], r["utf16_units"], r["lines"]
        size_407 = max(b, cp)                       # his conservative size
        usage_407 = max(size_407 / CAP_UNITS, lines / CAP_LINES)
        usage_true = max(u16 / CAP_UNITS, lines / CAP_LINES)
        over = usage_407 / usage_true
        # what each model predicts as the last line that loads
        pred_407 = min(lines, int(CAP_LINES), int(CAP_UNITS / (size_407 / lines)))
        measured = r["last_line_loaded"]
        out.append({"fixture": r["label"], "bytes": b, "code_points": cp, "utf16_units": u16,
                    "usage_407": round(usage_407, 3), "usage_true": round(usage_true, 3),
                    "over_report_x": round(over, 2), "pred_lines_407": pred_407,
                    "measured_last_line": measured,
                    "pred_407_understates_by_lines": measured - pred_407})
        print(f"{r['label']:16s} {b:7d} {cp:7d} {u16:7d} | {usage_407:10.2f} {usage_true:10.2f} "
              f"{over:10.2f}x | {pred_407:14d} {measured:13d}")

    v = {
        "hedge_never_under_reports": all(o["usage_407"] >= o["usage_true"] - 1e-9 for o in out),
        "hedge_over_reports_on_non_ascii": any(o["over_report_x"] > 1.5 for o in out),
        "worst_over_report_x": max(o["over_report_x"] for o in out),
        "hedge_would_prune_entries_that_fit": any(o["pred_407_understates_by_lines"] > 0 for o in out),
        "worst_understatement_lines": max(o["pred_407_understates_by_lines"] for o in out),
    }
    print("\n=== VERDICTS ===")
    for k, val in v.items():
        print(f"  {val}  {k}")
    dst = os.path.join(HERE, "what_the_unit_hedge_costs_a_checker.result.json")
    json.dump({"probe": "what_the_unit_hedge_costs_a_checker", "cap_units": CAP_UNITS,
               "cap_lines": CAP_LINES, "verdicts": v, "rows": out},
              open(dst, "w", encoding="utf-8"), indent=2)
    print(f"wrote {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
