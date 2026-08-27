"""Does the privileged-write counter open a window for ANOTHER thread's caller write?

We recommended this shape to a collaborator on openclaw#7707 who is about to implement it: instead of
an allow-list of internal keys, a privileged-write helper bumps a counter on the instance inside a
try/finally and calls the ordinary write path. Reserved keys are honoured only while that counter is
up. The property that makes it attractive is that a new internal marker inherits privilege by
construction and nothing reachable from a caller can open the door.

That argument is about the CALL PATH. It says nothing about concurrency, and the counter is a single
attribute on a shared instance. If thread A is mid-privileged-write while thread B calls the ordinary
remember() with a forged reserved key, B may be inside A's window -- and the store would accept a
trust state the caller manufactured. Our own deployment shares one store across eight agents, so this
is not hypothetical for us either.

Measured rather than reasoned about, because the answer decides whether the advice we gave was
complete. A CONTROL runs the same forged write with no concurrent privileged writer at all: if the key
survives there too, the test is measuring a broken reservation rather than a race.

    python research/probes/does_a_privilege_counter_leak_across_threads.py
"""
import os
import sys
import tempfile
import threading
import time

sys.path.insert(0, "C:/Users/Danculus/inspeximus-repo")
from inspeximus import Inspeximus  # noqa: E402

FORGED = {"graduated_from_episodic": True}
ROUNDS = 400


def _forged_key_survived(store, mid):
    rec = [r for r in store.items if r["id"] == mid]
    return bool(rec) and "graduated_from_episodic" in (rec[0].get("meta") or {})


def control_no_concurrency():
    """No privileged writer anywhere. The forged key MUST be stripped -- if it is not, the reservation
    itself is broken and every 'leak' below would be that, not a race."""
    ix = Inspeximus(os.path.join(tempfile.mkdtemp(), "s.json"))
    survived = 0
    for _ in range(50):
        mid = ix.remember("a caller record", mtype="semantic", meta=dict(FORGED))
        if _forged_key_survived(ix, mid):
            survived += 1
    return survived


def race():
    """One thread hammers privileged writes; another writes forged caller records the whole time."""
    # IN-MEMORY on purpose. A file-backed store cannot even reach this race: the single-writer guard
    # (StoreChangedOnDisk) refuses the second writer loudly, which is itself the answer for that case.
    # path=None removes the disk check, leaving only the privilege counter -- so this isolates the
    # question actually asked, instead of measuring a different guard.
    ix = Inspeximus(path=None)
    stop = threading.Event()
    errors = []

    def privileged():
        while not stop.is_set():
            try:
                ix._stamp("internal marker", meta={"session_seq": 1})
            except Exception as e:      # a crash here would silently end the window and fake a pass
                errors.append(repr(e))
                return

    t = threading.Thread(target=privileged, daemon=True)
    t.start()
    time.sleep(0.05)                    # let the privileged writer get going

    leaked = 0
    ids = []
    for _ in range(ROUNDS):
        mid = ix.remember("a caller record", mtype="semantic", meta=dict(FORGED))
        ids.append(mid)
    stop.set()
    t.join(timeout=5)

    for mid in ids:
        if _forged_key_survived(ix, mid):
            leaked += 1
    return leaked, len(ids), errors


def main():
    ctrl = control_no_concurrency()
    print("CONTROL, no concurrent privileged writer: forged key survived %d/50" % ctrl)
    if ctrl:
        print("CONTROL FAILED: the reservation does not strip the key even single-threaded, so nothing")
        print("                below would be a race. Reporting nothing.")
        return 2
    print("  -> single-threaded, the reserved key is always stripped  [OK]")
    print()

    leaked, n, errors = race()
    if errors:
        print("the privileged writer raised (%s) -- its window closed early, so a clean result here" % errors[0][:80])
        print("would understate the exposure. Reporting nothing.")
        return 2

    print("RACE: forged reserved key survived on %d of %d caller writes made while another thread held"
          % (leaked, n))
    print("      the privileged window open.")
    print()
    if leaked:
        print("FINDING: the privilege counter is INSTANCE-WIDE, so one thread's privileged write is a")
        print("         window every other thread's caller write can walk through. The call-path argument")
        print("         is about WHICH CODE opens the door and says nothing about who else is standing")
        print("         in it. A shared store needs the counter to be thread-local (or the reserved-key")
        print("         decision taken from the call stack rather than from instance state).")
    else:
        print("NO LEAK on this run. Note what that does and does not show: absence of an observed race is")
        print("weak evidence, not a proof of exclusion -- it depends on interleaving this scheduler chose.")
        print("It does mean the shape is not trivially exploitable in a plain two-thread interleaving.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
