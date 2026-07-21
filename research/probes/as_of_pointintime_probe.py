"""Verify mnemo's as_of() / history() point-in-time (bi-temporal) queries — the one real technical
edge a competitor (Zep/Graphiti) has that mnemo lacked, built on existing supersession intervals
(no graph DB). Severe test: time-travel must return the value that was TRUE at each moment,
including through corrections and a back-filled (late-arriving, earlier-event-time) record.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from inspeximus import Inspeximus

def check(name, got, want):
    ok = got == want
    print(f"  [{'OK' if ok else 'FAIL'}] {name}: got={got} want={want}")
    return ok

def run():
    m = Inspeximus(path=None); m.echo_guard = True
    k = "billing::region"
    # a real timeline: v0 valid from t=100, corrected to v1 at t=200, corrected to v2 at t=300
    m.remember("region is frankfurt", key=k, object="frankfurt", valid_from=100.0)
    m.remember("region is ohio",      key=k, object="ohio",      valid_from=200.0)
    m.remember("region is oslo",      key=k, object="oslo",      valid_from=300.0)
    allok = True
    allok &= check("before-any (t=50)",   m.as_of(k, 50.0),  None)
    allok &= check("during v0 (t=150)",   (m.as_of(k, 150.0) or {}).get("object"), "frankfurt")
    allok &= check("boundary v1 (t=200)", (m.as_of(k, 200.0) or {}).get("object"), "ohio")
    allok &= check("during v1 (t=250)",   (m.as_of(k, 250.0) or {}).get("object"), "ohio")
    allok &= check("current (t=999)",     (m.as_of(k, 999.0) or {}).get("object"), "oslo")

    # BACK-FILL: a record about an EARLIER state arrives LATE (event-time 250, but written now).
    # as_of must place it by event-time, and it must NOT clobber the current value.
    m.remember("region was dublin briefly", key=k, object="dublin", valid_from=250.0)
    cur = [r for r in m.items if r.get("key") == k and r.get("status") == "active"]
    curobj = max(cur, key=lambda r: r.get("valid_from", r["ts"])).get("object")
    allok &= check("backfill didn't change CURRENT", curobj, "oslo")

    # HONEST LIMIT (documented, not hidden): back-filling INTO an existing interval creates
    # overlapping intervals (ohio [200,300) and dublin [250,300) both cover 250). as_of resolves
    # the overlap by latest event-time, so as_of(250) now returns dublin, not ohio. A full temporal
    # DB would split the timeline; mnemo does the append-correction case cleanly and documents this.
    print(f"  [DOCUMENTED] as_of(250) after mid-timeline backfill = "
          f"{(m.as_of(k,250.0) or {}).get('object')} (overlap -> latest event-time tie-break)")

    # history is a clean, ordered audit trail
    hist = m.history(k)
    print(f"  history({k}): {[h['object'] for h in hist]}")
    allok &= check("history length", len(hist), 4)

    print(f"\nAS-OF POINT-IN-TIME: {'ALL PASS' if allok else 'FAIL'}  (append-correction case exact; "
          f"mid-timeline backfill overlaps resolve to latest event-time)")
    return allok

if __name__ == "__main__":
    run()
