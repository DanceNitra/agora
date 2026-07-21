"""
dungeon_health.py - REAL dungeon liveness, not the HTTP-200 lie.

The dungeon's HTTP server runs on its own thread, so `curl :5174` returns 200 even when the agent
ambient-life loop is frozen or starved. The honest signal is whether the loop COUNTER in
.dungeon_heartbeat advances - and CONSISTENTLY, not just once (the freeze is intermittent: it can advance
for a few seconds then stall for tens of seconds, so a single start/end sample can be fooled by a lucky
window - which is exactly how a "healthy" check missed a frozen world on 2026-06-20).

Multi-samples the heartbeat across a window and reports the worst stall + average rate:
  FROZEN  - loop_n never advanced
  STARVED - advanced but a single stall exceeded the stall budget, or avg slower than ~6s/loop
  OK      - advancing steadily
Exit: 0 OK, 1 STARVED, 2 FROZEN/unknown.

Usage:  python tools/dungeon_health.py [window_seconds]   (default 45)
"""
import os, sys, time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HB = os.path.join(HERE, "agora-game-server", ".dungeon_heartbeat")
STALL_BUDGET_S = 25.0   # a no-advance gap longer than this = a stall the user would see as "frozen"
AVG_SEC_PER_LOOP_OK = 6.0


def _read():
    try:
        ts, ln = open(HB, encoding="utf-8").read().split()
        return int(ts), int(ln)
    except Exception:
        return None, None


def main():
    window = float(sys.argv[1]) if len(sys.argv) > 1 else 45.0
    step = 3.0
    n = max(2, int(window / step))
    samples = []
    for i in range(n):
        _, ln = _read()
        samples.append((time.time(), ln))
        if i < n - 1:
            time.sleep(step)
    lns = [s[1] for s in samples if s[1] is not None]
    if len(lns) < 2:
        print("dungeon: UNKNOWN (no .dungeon_heartbeat)"); sys.exit(2)
    total_adv = lns[-1] - lns[0]
    elapsed = samples[-1][0] - samples[0][0]
    # worst stall: longest stretch with no loop_n change
    worst_stall, stall_start, last_ln = 0.0, samples[0][0], lns[0]
    for t, ln in samples:
        if ln is None:
            continue
        if ln != last_ln:
            worst_stall = max(worst_stall, t - stall_start)
            stall_start, last_ln = t, ln
    worst_stall = max(worst_stall, samples[-1][0] - stall_start)   # trailing no-advance
    sec_per_loop = (elapsed / total_adv) if total_adv > 0 else float("inf")

    if total_adv <= 0:
        verdict, code = "FROZEN", 2
    elif worst_stall > STALL_BUDGET_S or sec_per_loop > AVG_SEC_PER_LOOP_OK:
        verdict, code = "STARVED", 1
    else:
        verdict, code = "OK", 0
    print(f"dungeon: {verdict}  (loop_n +{total_adv} over {elapsed:.0f}s ~ {sec_per_loop:.1f}s/loop, "
          f"worst stall {worst_stall:.0f}s)")
    if verdict != "OK":
        print("  -> agent loop not progressing healthily despite HTTP 200. Likely GPU/brain contention "
              "(check the inspeximus-vec backfill + brain endpoint latency); py-spy the process for the real frame.")
    sys.exit(code)


if __name__ == "__main__":
    main()
