"""Can an ordinary maintenance call silently disarm the code guard?

check_code() only considers deprecation records whose status is "active" (_deprecations in code_guard.py).
That is correct for re-deprecation -- a later deprecate_symbol of the same `old` supersedes the earlier
one and the new replacement wins. But `status` is not owned by the code guard: consolidate() and sleep()
retire records too, by similarity and by decay, and they know nothing about refactor bookkeeping.

If either can stale a deprecation record, then check_code() returns [] -- "clean" -- for a snippet that
resurrects a symbol the refactor really did delete, which is the exact failure the tool exists to prevent
and the one the docstring calls "the single most common coding-loop memory failure".

Deprecations are highly self-similar by construction ("<old> was replaced by <new>" over and over), which
is precisely the shape a duplicate/hub pass collapses. Today's consolidate() defect was found the same
way, so the hypothesis is not idle.

CONTROL: before any maintenance call the guard must FLAG the symbol. A probe where the guard never fired
would report "no disarm" for the wrong reason.
"""
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\Danculus\inspeximus-repo")
from inspeximus import Inspeximus  # noqa: E402
from inspeximus.code_guard import _PREFIX, check_code, deprecate_symbol  # noqa: E402

PAIRS = [(f"old_api_fn_{i}", f"new_api_fn_{i}") for i in range(30)]
SNIPPET = "result = old_api_fn_0(payload)\nvalue = old_api_fn_7(config)\n"


def fresh(**kw):
    st = Inspeximus(path=None, **kw)
    for old, new in PAIRS:
        deprecate_symbol(st, old, new, reason="renamed in the 2026-07 refactor")
    return st


def flagged(st):
    return sorted(h["symbol"] for h in check_code(st, SNIPPET))


def active_deps(st):
    # the REAL keyspace, read from the module rather than guessed. The first run of this probe guessed
    # "code::deprecated::" and printed 0 active records in the control -- while the guard was flagging
    # both symbols. A counter that reads zero next to a working guard is a broken instrument, and its
    # number would have gone into the finding unchallenged.
    return len([r for r in st.items
                if r.get("status") == "active" and (r.get("key") or "").startswith(_PREFIX)])


st = fresh()
base = flagged(st)
print(f"CONTROL before maintenance: flags {base}   (active deprecation records: {active_deps(st)})")
if len(base) != 2:
    print("PROBE BROKEN: the guard did not flag both symbols to begin with")
    raise SystemExit(1)

# capacity is the LIVE path: it hard-evicts the lowest-value active records on ordinary writes, with no
# maintenance call at all, so a store configured with it disarms the guard just by being used.
def _capacity_arm():
    st = fresh(capacity=8)
    for i in range(10):
        st.remember(f"unrelated operational note number {i}", key=f"note{i}", object=str(i))
    return st, "evicted by capacity=8 during ordinary writes"


for label, call in (("consolidate()", lambda s: s.consolidate()),
                    ("consolidate(keep=5)", lambda s: s.consolidate(keep=5)),
                    ("consolidate_clusters()", lambda s: s.consolidate_clusters()),
                    ("sleep()", lambda s: s.sleep()),
                    ("capacity=8 + 10 writes", None)):
    if call is None:
        st, rep = _capacity_arm()
        after, n = flagged(st), active_deps(st)
        lost = sorted(set(base) - set(after))
        print(f"\n{label:24s} -> active deprecation records 30 -> {n}")
        print(f"{'':24s}    check_code flags {after}   {'DISARMED' if lost else 'guard intact'}")
        if lost:
            print(f"{'':24s}    SILENTLY STOPPED FLAGGING: {lost}  ({rep})")
        continue
    st = fresh()
    try:
        rep = call(st)
    except Exception as e:
        print(f"\n{label:24s} raised {type(e).__name__}: {e}")
        continue
    after = flagged(st)
    n = active_deps(st)
    lost = sorted(set(base) - set(after))
    verdict = "DISARMED" if lost else "guard intact"
    print(f"\n{label:24s} -> active deprecation records {30} -> {n}")
    print(f"{'':24s}    check_code flags {after}   {verdict}")
    if lost:
        print(f"{'':24s}    SILENTLY STOPPED FLAGGING: {lost}")
        print(f"{'':24s}    report was: {rep}")
