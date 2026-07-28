"""What does check_code MISS? The other half of a guard: not its false alarms, its recall.

check_code over-flags deliberately (a mention in a string or comment counts) and says so. That half is
documented. The half nobody stated is which REAL resurrections slip through, and a guard that misses is
worse than one that over-flags: over-flagging is a nuisance the caller sees, missing is a clean verdict
about code that calls a function the refactor deleted.

The match is a whole-identifier regex over the recorded symbol string, so recall depends entirely on the
symbol being recorded in the SAME lexical form the code uses. Every case below is a resurrection a human
reviewer would call real; the question is which form of the record catches it.

Not a claim that the regex is wrong -- it is exactly what the docstring promises. The finding, if any, is
about the gap between what gets RECORDED by deprecate_symbol and what appears in generated code.
"""
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\Danculus\inspeximus-repo")
from inspeximus import Inspeximus  # noqa: E402
from inspeximus.code_guard import check_code, deprecate_symbol  # noqa: E402

#: (recorded symbol, generated code, is this a REAL resurrection a reviewer would flag?)
CASES = [
    ("old_fn", "x = old_fn(1)", True),
    ("old_fn", "x = obj.old_fn(1)", True),
    ("old_fn", "x = old_fn_v2(1)", False),                      # different symbol, must NOT flag
    ("old_fn", "x = my_old_fn(1)", False),                      # ditto
    ("old_fn", 'f = getattr(obj, "old_fn")', True),             # string form, over-flag is CORRECT here
    ("old_fn", "# TODO: stop using old_fn\nx = new_fn(1)", False),  # comment only: documented over-flag
    # the recorded-form gap: a refactor record written with its module path
    ("mod.old_fn", "from mod import old_fn\nx = old_fn(1)", True),
    ("mod.old_fn", "import mod\nx = mod.old_fn(1)", True),
    # ...and the reverse: recorded bare, used qualified
    ("old_fn", "import mod\nx = mod.old_fn(1)", True),
    # aliasing at import time
    ("old_fn", "from mod import old_fn as helper\nx = helper(1)", True),
    # a class method rename recorded as Class.method
    ("Session.close_all", "s = Session()\ns.close_all()", True),
]

print(f"{'recorded':18s} {'generated code':46s} {'real?':6s} flagged?  verdict")
misses, false_alarms = [], []
for sym, code, real in CASES:
    st = Inspeximus(path=None)
    deprecate_symbol(st, sym, "new_fn", reason="refactor")
    hit = bool(check_code(st, code))
    if real and not hit:
        verdict, _ = "MISS", misses.append((sym, code))
    elif hit and not real:
        verdict, _ = "FALSE ALARM", false_alarms.append((sym, code))
    else:
        verdict = "ok"
    shown = code.replace("\n", " | ")
    print(f"{sym:18s} {shown:46s} {str(real):6s} {str(hit):9s} {verdict}")

print(f"\nMISSES (real resurrection, guard said clean): {len(misses)}")
for sym, code in misses:
    print(f"   recorded {sym!r} -> code {code.replace(chr(10), ' | ')!r}")
print(f"FALSE ALARMS beyond the documented string/comment over-flag: {len(false_alarms)}")
for sym, code in false_alarms:
    print(f"   recorded {sym!r} -> code {code.replace(chr(10), ' | ')!r}")
