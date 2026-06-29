"""
Self-improvement controller — the closed loop that keeps Agora improving itself.

Goal (owner, 2026-06-20): a mechanism that watches the agents' work; when they keep spinning in CHURN
(burning tokens, producing ~0 value) it triggers REBUILDING them toward real measured results; it keeps
scanning repos + forums for where we can apply ourselves; and it periodically researches the OS itself.

It does NOT rewrite code autonomously (too dangerous unattended). It is the DETECTOR + TRIGGER: it measures
per-organ ROI, and on persistent churn it queues a high-value, actionable task to the Claude inbox — the
heavy creative rebuild is done by Claude in the /loop (the architecture: flash/local do grunt work, the
hard leaps route to Claude). Sparse by design (per-item cooldowns) so it adds signal, not churn.

Run detached:  python -u tools/self_improvement_controller.py   (logs -> _self_improvement.log)
"""
import os, sys, time, json, re, urllib.request, urllib.parse

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
ENV = os.path.join(ROOT, "server", ".env")
STATE = os.path.join(BASE, ".self_improvement_state.json")
API = "http://127.0.0.1:8000/api/v1/agent-os/brain"

CHECK_S = 3600                 # evaluate hourly
CHURN_KTOK_GROWTH = 60.0       # an organ that burned >60k tok since last check ...
CHURN_VALUE_GAIN = 1.0         # ... and gained < 1 value point = churning
REBUILD_COOLDOWN_S = 86400     # re-flag a given organ for rebuild at most once/day
# Organs whose value is structurally attributed DOWNSTREAM: the group-cognition + promotion pipeline
# (seminar -> findings) credits its output to verify-findings / agent-dialogue / the produced notes, and
# `match` spend is the cost of the severe-test rule (see memory: match = cost of rigor, not a leak). These
# legitimately show ~0 metabolism "value" while the system keeps producing (research_findings ~40-70/day),
# so flagging them as "churning" off the narrow value signal is the same miscalibration fixed for the
# activity monitor in commit 8d2ff7e. Exempt them from the value-based churn alarm. (`unknown` is
# unactionable; `agent-think` is deleted and frozen.)
CHURN_EXEMPT = {"seminar", "vault-note", "promote-findings", "directions", "match", "unknown", "agent-think"}
SCOUT_STALE_S = 12 * 3600      # repo scan considered stale after 12h
OPP_EVERY_S = 12 * 3600        # opportunity (repos+forums+where-we-fit) sweep cadence
AUDIT_EVERY_S = 24 * 3600      # OS self-audit cadence
CRUCIBLE_EVERY_S = 3 * 24 * 3600  # Crucible-candidate hunt cadence (storm/artifact-debunk -> ledger)


def _get(path):
    try:
        return json.loads(urllib.request.urlopen(API + path, timeout=25).read())
    except Exception:
        return None


def _post(path, payload):
    try:
        r = urllib.request.Request(API + path, data=json.dumps(payload).encode(),
                                   headers={"Content-Type": "application/json"})
        return json.loads(urllib.request.urlopen(r, timeout=25).read())
    except Exception as e:
        print(f"[selfimp] post {path} failed: {e}", flush=True); return None


def _queue(text):
    return _post("/claude-inbox", {"text": text})


def _telegram(text):
    try:
        t = open(ENV, "rb").read().decode("utf-8", "replace")
        tok = re.search(r'TELEGRAM[_A-Z]*TOKEN\s*=\s*"?([^"\r\n]+)', t).group(1).strip()
        chat = re.search(r'TELEGRAM[_A-Z]*CHAT[_A-Z]*ID\s*=\s*"?([^"\r\n]+)', t).group(1).strip()
        data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
        urllib.request.urlopen("https://api.telegram.org/bot" + tok + "/sendMessage", data=data, timeout=30)
    except Exception:
        pass


def _load_state():
    try:
        return json.loads(open(STATE, encoding="utf-8").read())
    except Exception:
        return {"organs": {}, "rebuild_flagged": {}, "last_opp": 0, "last_audit": 0, "last_scout_alert": 0}


def _save_state(s):
    try:
        open(STATE, "w", encoding="utf-8").write(json.dumps(s, indent=1))
    except Exception:
        pass


def _check_churn(st, now):
    """Flag organs that grew in spend but not in value since last check -> queue a rebuild (cooldowned)."""
    m = _get("/metabolism")
    if not m or "organs" not in m:
        return
    prev = st.get("organs", {})
    cur = {k: {"ktok": v.get("ktok", 0), "value": v.get("value", 0)} for k, v in m["organs"].items()}
    for organ, o in cur.items():
        if organ in CHURN_EXEMPT:
            continue
        p = prev.get(organ)
        if not p:
            continue
        dktok = o["ktok"] - p["ktok"]
        dval = o["value"] - p["value"]
        if dktok >= CHURN_KTOK_GROWTH and dval < CHURN_VALUE_GAIN:
            last = st["rebuild_flagged"].get(organ, 0)
            if now - last > REBUILD_COOLDOWN_S:
                st["rebuild_flagged"][organ] = now
                _queue(f"AUTO-REBUILD (self-improvement controller): organ '{organ}' is CHURNING — burned "
                       f"~{dktok:.0f}k tokens in the last hour for <{CHURN_VALUE_GAIN} value points (ROI ~0). "
                       f"Diagnose it and rebuild it toward a measured, value-producing form (severe-test / "
                       f"real receipt), or throttle/quiet it if it can't earn its keep. One change, verify, commit.")
                _telegram(f"Self-improvement: '{organ}' churning (+{dktok:.0f}k tok, ~0 value) -> queued a rebuild task.")
                print(f"[selfimp] churn flagged: {organ} +{dktok:.0f}k tok / +{dval:.1f} value", flush=True)
    st["organs"] = cur


def _check_scout(st, now):
    s = _get("/scout/status")
    if not s:
        return
    ls = s.get("last_scan_unix")
    if ls and (now - ls) > SCOUT_STALE_S and (now - st.get("last_scout_alert", 0)) > SCOUT_STALE_S:
        st["last_scout_alert"] = now
        _queue("Repo/issue SCAN is stale (>12h since the Scout last recorded one). Run an outreach-discovery "
               "pass: GET /brain/scout-target for a fresh fit, and bias toward small/active repos where a "
               "maintainer replies; draft gated if we genuinely answer with evidence.")
        print(f"[selfimp] scout stale ({(now-ls)/3600:.0f}h) -> queued a scan task", flush=True)


def _periodic(st, now):
    if now - st.get("last_opp", 0) > OPP_EVERY_S:
        st["last_opp"] = now
        _queue("OPPORTUNITY SCAN (where can we apply ourselves): sweep GitHub repos + forums (HN, "
               "r/LocalLLaMA, r/MachineLearning) for live pain that fits our assets (mnemo memory layer, "
               "grounding-firewall, the AI-claim Crucible, freelance RAG-hardening). Surface 3-5 concrete, "
               "evidenced fits with links; draft gated outreach only where we genuinely answer.")
        print("[selfimp] queued opportunity scan", flush=True)
    if now - st.get("last_audit", 0) > AUDIT_EVERY_S:
        st["last_audit"] = now
        _queue("SELF-RESEARCH (improve the OS): read the funnel + metabolism + agent_redesign_tracker and "
               "name the SINGLE highest-leverage next improvement to Agora's operating system (the biggest "
               "ROI-0 leak or the weakest stage of activity->grounded->curated->shipped), with the concrete "
               "change. One data-backed recommendation.")
        print("[selfimp] queued OS self-audit", flush=True)
    if now - st.get("last_crucible", 0) > CRUCIBLE_EVERY_S:
        st["last_crucible"] = now
        _queue("CRUCIBLE-CANDIDATE HUNT (feed the ledger): run a fresh hunt for famous, quantitative, "
               "falsifiable claims where a runnable null/strong-baseline could give a FAILED — prefer the "
               "AI/LLM-engineering folklore lane (dev-actionable + public data). Use the ai-folklore-batch / "
               "artifact-debunk-pipeline workflow to surface + prior-art-vet candidates, then RED-TEAM the "
               "top pick with the stress-claim skill and VERIFY any cited numbers with verify-claims BEFORE "
               "recording. Severe-test the strongest computable one (Lab baseline same cycle); record to the "
               "Crucible only if it passes both gates. Gated publish stays owner-approved.")
        print("[selfimp] queued Crucible-candidate hunt", flush=True)


def main():
    print(f"[selfimp] started; evaluate every {CHECK_S}s (churn-detect -> rebuild queue; scout; opp; audit)", flush=True)
    st = _load_state()
    # seed the metabolism baseline immediately so the first churn delta is meaningful next cycle
    m = _get("/metabolism")
    if m and "organs" in m and not st.get("organs"):
        st["organs"] = {k: {"ktok": v.get("ktok", 0), "value": v.get("value", 0)} for k, v in m["organs"].items()}
        _save_state(st)
    while True:
        time.sleep(CHECK_S)
        now = time.time()
        try:
            _check_churn(st, now)
            _check_scout(st, now)
            _periodic(st, now)
            _save_state(st)
        except Exception as e:
            print(f"[selfimp] cycle error: {e}", flush=True)


if __name__ == "__main__":
    main()
