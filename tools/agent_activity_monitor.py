"""
Agent activity monitor — are the agents actually WORKING, and WHAT are they producing?

Distinct from the dungeon canary (which only checks liveness): this tracks the VALUE the agents produce.
Every 30 min it snapshots the production signals and logs the delta; every ~3 h it Telegrams a summary; it
alerts immediately if the loop stalls (agents frozen) or if a long window produced ZERO value (busy-but-idle
- the exact failure the redesign targets).

Signals (deltas since the last snapshot) — "value produced" is ANY of these rising, because our real
output is bursty and most of it is NOT citation-grounded discoveries (it's Lab-measured findings + vault
notes). Counting only funnel-grounded+shipped (which move ~a few times a DAY) against a 1h alarm window
made the monitor cry "busy-but-idle" during totally normal operation — the recurring false alarm. The fix
is honest (count the real work, don't mute it) + a realistic multi-hour window + a diagnostic message.
  - loop_n            : dungeon agent-loop progress (are they alive + moving)
  - findings          : research_findings rows (the MOST active real signal, ~tens/day, bursty)
  - discoveries       : collective_knowledge rows (hypotheses + discoveries incl. Lab MEASURED/VERDICT)
  - grounded          : citation-grounded discoveries (funnel; rare, ~a few/day)
  - curated           : curated assets / vault notes (funnel)
  - shipped           : shipped value (funnel; rarest)
  - method_runs       : severe-test Lab runs via the Methods Library (Rooke's real measured tests)

Run detached:  python -u tools/agent_activity_monitor.py   (logs -> _agent_activity.log)
"""
import os, sys, time, json, re, sqlite3, urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
HEARTBEAT = os.path.join(ROOT, "agora-game-server", ".dungeon_heartbeat")
METHODS = os.path.join(ROOT, "server", ".methods.json")   # the Methods ledger lives under server/
ENV = os.path.join(ROOT, "server", ".env")
DB = os.path.join(ROOT, "server", "agora.db")             # brain DB: research_findings + collective_knowledge
STATE = os.path.join(BASE, ".agent_activity_state.json")
API = "http://127.0.0.1:8000/api/v1/agent-os/brain"

CHECK_S = 1800            # snapshot every 30 min
REPORT_EVERY = 6          # Telegram a summary every 6 checks (~3 h)
# Real value is bursty with normal multi-hour gaps (findings ~tens/day, discoveries ~a dozen/day, notes
# ~a few/day). Only a GENUINE stall keeps ALL signals flat this long, so alert after 6h, not 1h.
STALL_ALERT_S = 21600     # if NO value (across all signals) for this long, warn once


def _loop_n():
    try:
        return int(open(HEARTBEAT, encoding="utf-8").read().split()[1])
    except Exception:
        return None


def _funnel():
    try:
        d = json.loads(urllib.request.urlopen(API + "/funnel", timeout=20).read())
        g = {s["label"]: s["count"] for s in d.get("stages", [])}
        return g.get("Grounded knowledge", 0), g.get("Curated assets", 0), g.get("Shipped value", 0)
    except Exception:
        return None, None, None


def _db_counts():
    """The most active REAL production signals, read straight from the brain DB: research_findings (tens/
    day) + collective_knowledge (discoveries/hypotheses, incl. Lab MEASURED/VERDICT the funnel's
    citation-only 'grounded' never counts). Read-only; returns (None, None) if the DB can't be opened."""
    try:
        c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=10)
        try:
            f = c.execute("SELECT COUNT(*) FROM research_findings").fetchone()[0]
            d = c.execute("SELECT COUNT(*) FROM collective_knowledge").fetchone()[0]
            return f, d
        finally:
            c.close()
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
    g, cur, s = _funnel()
    f, d = _db_counts()
    return {"t": time.time(), "loop_n": _loop_n(), "grounded": g, "curated": cur, "shipped": s,
            "findings": f, "discoveries": d, "method_runs": _method_runs()}


def _delta(cur, last, key):
    """Delta of a signal between snapshots, or None if either side is missing (don't fabricate a 0)."""
    a, b = cur.get(key), last.get(key)
    return (a - b) if (a is not None and b is not None) else None


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
        df = _delta(cur, last, "findings")
        dd = _delta(cur, last, "discoveries")
        dg = _delta(cur, last, "grounded")
        dc = _delta(cur, last, "curated")
        ds = _delta(cur, last, "shipped")
        dr = cur["method_runs"] - last["method_runs"]
        print(f"[activity] 30m delta: loop+{dloop} findings+{df} discoveries+{dd} grounded+{dg} "
              f"curated+{dc} lab_tests+{dr} shipped+{ds}", flush=True)

        # value = ANY real production signal rising (not just the rare citation-grounded + shipped ones).
        produced = sum(x for x in (df, dd, dg, dc, ds, dr) if x and x > 0)
        if produced > 0:
            last_value_t = time.time(); stalled_warned = False
        # alerts: agents frozen, or a GENUINE stall (every value signal flat for the full window)
        if dloop == 0:
            _telegram("AGENT MONITOR: dungeon loop_n NOT advancing - agents may be frozen (check canary/py-spy).")
        elif (time.time() - last_value_t) > STALL_ALERT_S and not stalled_warned:
            hrs = int((time.time() - last_value_t) / 3600)
            _telegram(f"AGENT MONITOR: genuine stall - ZERO value across ALL signals for ~{hrs}h "
                      f"(findings+{df} discoveries+{dd} grounded+{dg} notes+{dc} lab+{dr} shipped+{ds}; "
                      f"loop moving). Check: LLM tier returns content? grounded pool non-empty? promote-findings?")
            stalled_warned = True

        # periodic summary
        if n % REPORT_EVERY == 0:
            bf = _delta(cur, base, "findings")
            bd = _delta(cur, base, "discoveries")
            bc = _delta(cur, base, "curated")
            br = cur["method_runs"] - base["method_runs"]
            bl = (cur["loop_n"] - base["loop_n"]) if (cur["loop_n"] and base["loop_n"]) else "?"
            _telegram(f"Agent activity (~3h): loop +{bl} (active), +{bf} findings, +{bd} discoveries, "
                      f"+{bc} curated notes, +{br} severe-test Lab runs. "
                      f"[findings={cur['findings']} discoveries={cur['discoveries']} notes={cur['curated']}]")
            base = dict(cur)
        last = cur


if __name__ == "__main__":
    main()
