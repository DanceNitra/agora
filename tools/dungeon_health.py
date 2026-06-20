"""
dungeon_health.py - REAL dungeon liveness, not the HTTP-200 lie.

The dungeon's HTTP server runs on its own thread, so `curl :5174` returns 200 even when the agent
ambient-life loop is frozen or starved (e.g. its LLM calls are queued behind other ollama.com traffic).
The honest signal is whether the loop COUNTER in .dungeon_heartbeat is advancing, and how fast.

Samples the heartbeat twice over a window and reports loops/sec + a verdict:
  FROZEN  - loop_n did not advance at all
  STARVED - advancing but slower than ~1 loop / 10s (LLM-contended; world looks frozen)
  OK      - advancing at a healthy rate
Exit code: 0 OK, 1 STARVED, 2 FROZEN/unknown - so it can gate "is the dungeon really healthy?".

Usage:  python tools/dungeon_health.py [window_seconds]   (default 12)
"""
import os, sys, time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HB = os.path.join(HERE, "agora-game-server", ".dungeon_heartbeat")
STARVED_LOOP_S = 10.0   # slower than 1 loop / 10s = starved (healthy is a few s/loop)


def _read():
    try:
        ts, ln = open(HB, encoding="utf-8").read().split()
        return int(ts), int(ln)
    except Exception:
        return None, None


def main():
    window = float(sys.argv[1]) if len(sys.argv) > 1 else 12.0
    ts0, ln0 = _read()
    if ln0 is None:
        print("dungeon: UNKNOWN (no .dungeon_heartbeat)"); sys.exit(2)
    age = int(time.time()) - ts0
    time.sleep(window)
    ts1, ln1 = _read()
    dl = (ln1 - ln0) if (ln1 is not None) else 0
    # heartbeat is written every 5 loops, so loop delta is approximate at this resolution
    sec_per_loop = (window / dl) if dl > 0 else float("inf")
    if dl <= 0:
        verdict, code = "FROZEN", 2
    elif sec_per_loop > STARVED_LOOP_S:
        verdict, code = "STARVED", 1
    else:
        verdict, code = "OK", 0
    print(f"dungeon: {verdict}  (loop_n {ln0}->{ln1}, +{dl} in {window:.0f}s ~ {sec_per_loop:.1f}s/loop, "
          f"heartbeat age at start {age}s)")
    if verdict != "OK":
        print("  -> the agent loop is not progressing healthily even if HTTP :5174 returns 200. "
              "Likely LLM/GPU contention (check for competing heavy LLM jobs) before restarting.")
    sys.exit(code)


if __name__ == "__main__":
    main()
