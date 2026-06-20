"""
Agent activity monitor — are the agents actually WORKING, and WHAT are they producing?

Distinct from the dungeon canary (which only checks liveness): this tracks the VALUE the agents produce.
Every 30 min it snapshots the production signals and logs the delta; every ~3 h it Telegrams a summary; it
alerts immediately if the loop stalls (agents frozen) or if a long window produced ZERO value (busy-but-idle
- the exact failure the redesign targets).

Signals (deltas since the last snapshot):
  - loop_n            : dungeon agent-loop progress (are they alive + moving)
  - grounded          : honestly-grounded findings (funnel; post-redesign metric)
  - shipped           : shipped value (funnel)
  - method_runs       : severe-test Lab runs via the Methods Library (Rooke's real measured tests)

Run detached:  python -u tools/agent_activity_monitor.py   (logs -> _agent_activity.log)
"""
import os, sys, time, json, re, urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
HEARTBEAT = os.path.join(ROOT, "agora-game-server", ".dungeon_heartbeat")
METHODS = os.path.join(ROOT, "server", ".methods.json")   # the Methods ledger lives under server/
ENV = os.path.join(ROOT, "server", ".env")
STATE = os.path.join(BASE, ".agent_activity_state.json")
API = "http://127.0.0.1:8000/api/v1/agent-os/brain"

CHECK_S = 1800            # snapshot every 30 min
REPORT_EVERY = 6          # Telegram a summary every 6 checks (~3 h)
STALL_ALERT_S = 3600      # if no value produced for this long, warn once


def _loop_n():
    try:
        return int(open(HEARTBEAT, encoding="utf-8").read().split()[1])
    except Exception:
        return None


def _funnel():
    try:
        d = json.loads(urllib.request.urlopen(API + "/funnel", timeout=20).read())
        g = {s["label"]: s["count"] for s in d.get("stages", [])}
        return g.get("Grounded knowledge", 0), g.get("Shipped value", 0)
    except Exception:
        return None, None


def _method_runs():
    try:
        return len(json.loads(open(METHODS, encoding="utf-8").read()))
    except Exception:
        return 0


def _telegram(text):
    try:
        txt = open(ENV, "rb").read().decode("utf-8", "replace")
        tok = re.search(r'TELEGRAM[_A-Z]*TOKEN\s*=\s*"?([^"\r\n]+)', txt).group(1).strip()
        chat = re.search(r'TELEGRAM[_A-Z]*CHAT[_A-Z]*ID\s*=\s*"?([^"\r\n]+)', txt).group(1).strip()
        import urllib.parse
        data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
        urllib.request.urlopen("https://api.telegram.org/bot" + tok + "/sendMessage", data=data, timeout=30)
    except Exception as e:
        print(f"[activity] telegram failed: {e}", flush=True)


def _snap():
    g, s = _funnel()
    return {"t": time.time(), "loop_n": _loop_n(), "grounded": g, "shipped": s, "method_runs": _method_runs()}


def main():
    print(f"[activity] started; snapshot every {CHECK_S}s, summary every ~{CHECK_S*REPORT_EVERY//3600}h", flush=True)
    last = _snap()
    base = dict(last)          # rolling base for the ~3h summary
    n = 0
    last_value_t = time.time()
    stalled_warned = False
    while True:
        time.sleep(CHECK_S)
        cur = _snap()
        n += 1
        dloop = (cur["loop_n"] - last["loop_n"]) if (cur["loop_n"] and last["loop_n"]) else None
        dg = (cur["grounded"] - last["grounded"]) if (cur["grounded"] is not None and last["grounded"] is not None) else None
        dr = cur["method_runs"] - last["method_runs"]
        ds = (cur["shipped"] - last["shipped"]) if (cur["shipped"] is not None and last["shipped"] is not None) else None
        print(f"[activity] 30m delta: loop+{dloop} grounded+{dg} lab_tests+{dr} shipped+{ds}", flush=True)

        produced = (dg or 0) + dr + (ds or 0)
        if produced > 0:
            last_value_t = time.time(); stalled_warned = False
        # alerts: agents frozen, or busy-but-idle (no value for a long window)
        if dloop == 0:
            _telegram("AGENT MONITOR: dungeon loop_n NOT advancing - agents may be frozen (check canary/py-spy).")
        elif (time.time() - last_value_t) > STALL_ALERT_S and not stalled_warned:
            _telegram(f"AGENT MONITOR: agents alive (loop moving) but produced ZERO value (grounded/lab/shipped) "
                      f"for ~{int((time.time()-last_value_t)/3600)}h - busy-but-idle, the redesign's target failure.")
            stalled_warned = True

        # periodic summary
        if n % REPORT_EVERY == 0:
            bg = (cur["grounded"] - base["grounded"]) if (cur["grounded"] is not None and base["grounded"] is not None) else "?"
            br = cur["method_runs"] - base["method_runs"]
            bs = (cur["shipped"] - base["shipped"]) if (cur["shipped"] is not None and base["shipped"] is not None) else "?"
            bl = (cur["loop_n"] - base["loop_n"]) if (cur["loop_n"] and base["loop_n"]) else "?"
            _telegram(f"Agent activity (~3h): loop +{bl} (active), +{bg} grounded findings, +{br} severe-test "
                      f"Lab runs, +{bs} shipped. [grounded={cur['grounded']} shipped={cur['shipped']}]")
            base = dict(cur)
        last = cur


if __name__ == "__main__":
    main()
