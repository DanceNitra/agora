"""
Dungeon canary -- a persistent, lightweight liveness watcher for the dungeon (:5174).

Why this exists: HTTP 200 on :5174 LIES (the HTTP server runs on its own thread and answers even
when the agent event-loop is frozen). The real liveness signal is loop_n advancing in
.dungeon_heartbeat. The /loop self-upgrade session only ticks every ~25 min; between ticks nothing
watches the dungeon. This canary samples loop_n every CHECK_S seconds and Telegrams the owner ONLY on
a confirmed freeze.

Hard rule (learned): ALERT, never restart. Manual restarts on false positives were the original churn
problem; relaunching is the brain watchdog's job. The canary's job is purely to notice and notify.

Run detached:  python -u tools/dungeon_canary.py   (logs -> _dungeon_canary.log)
"""
import os, sys, time, json, urllib.parse, urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
HEARTBEAT = os.path.join(BASE, "..", "agora-game-server", ".dungeon_heartbeat")
ENV = os.path.join(BASE, "..", "server", ".env")

CHECK_S = 300          # sample cadence (5 min)
SAMPLE_WINDOW_S = 18   # within a check, watch loop_n for this long
SAMPLE_STEP_S = 3
ALERT_COOLDOWN_S = 1800  # at most one alert per 30 min


def _read_loop_n():
    # heartbeat file is space-separated "ts loop_n" (matches tools/dungeon_health.py)
    try:
        ts, ln = open(HEARTBEAT, encoding="utf-8").read().split()
        return int(ln)
    except Exception:
        return None


def _telegram(text):
    try:
        txt = open(ENV, "rb").read().decode("utf-8", "replace")
        import re
        tok = re.search(r'TELEGRAM[_A-Z]*TOKEN\s*=\s*"?([^"\r\n]+)', txt).group(1).strip()
        chat = re.search(r'TELEGRAM[_A-Z]*CHAT[_A-Z]*ID\s*=\s*"?([^"\r\n]+)', txt).group(1).strip()
        data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
        urllib.request.urlopen("https://api.telegram.org/bot" + tok + "/sendMessage", data=data, timeout=30)
        return True
    except Exception as e:
        print(f"[canary] telegram failed: {e}", flush=True)
        return False


def sample_advance():
    """Return (advanced, worst_stall_s). advanced<=0 means frozen over the window."""
    n = max(2, int(SAMPLE_WINDOW_S / SAMPLE_STEP_S))
    pts = []
    for i in range(n):
        pts.append((time.time(), _read_loop_n()))
        if i < n - 1:
            time.sleep(SAMPLE_STEP_S)
    lns = [(t, ln) for t, ln in pts if ln is not None]
    if len(lns) < 2:
        return None, None  # unknown (no heartbeat file yet)
    adv = lns[-1][1] - lns[0][1]
    worst, start, last = 0.0, lns[0][0], lns[0][1]
    for t, ln in lns:
        if ln != last:
            worst = max(worst, t - start); start, last = t, ln
    worst = max(worst, lns[-1][0] - start)
    return adv, worst


def main():
    print(f"[canary] started; check every {CHECK_S}s, alert cooldown {ALERT_COOLDOWN_S}s", flush=True)
    last_alert = 0.0
    while True:
        adv, worst = sample_advance()
        if adv is None:
            print("[canary] UNKNOWN (no .dungeon_heartbeat)", flush=True)
        elif adv <= 0:
            # confirm with one more window before alerting (avoid a transient long LLM call)
            time.sleep(2)
            adv2, worst2 = sample_advance()
            if adv2 is not None and adv2 <= 0:
                now = time.time()
                if now - last_alert > ALERT_COOLDOWN_S:
                    msg = (f"DUNGEON CANARY: dungeon FROZEN - loop_n not advancing over "
                           f"~{2*SAMPLE_WINDOW_S}s (HTTP may still be 200). Real freeze, not a restart blip. "
                           f"Check py-spy on mcp_server + the inspeximus vec backfill.")
                    _telegram(msg)
                    last_alert = now
                    print("[canary] ALERT sent: FROZEN", flush=True)
                else:
                    print("[canary] FROZEN (in cooldown, no re-alert)", flush=True)
            else:
                print(f"[canary] transient (recovered: +{adv2})", flush=True)
        else:
            print(f"[canary] OK (+{adv} over window, worst stall {worst:.0f}s)", flush=True)
        time.sleep(CHECK_S)


if __name__ == "__main__":
    main()
