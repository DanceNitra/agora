"""M2 severe-test: manufactured-corroboration (forged-provenance) attack vs inspeximus's corroboration gate,
and an HONEST negative on the naive stateful "coordination monitor" that seems to close it. Answers the
open #1462 obligation ("3 coordinated records with 2 independent-looking forged provenances PASS the bar")
with a MEASURED receipt, and is roadmap item M2.

TWO findings, and the second kills a tempting fix:

FINDING 1 (CONFIRMED — the vulnerability). inspeximus's `_is_corroborated` gate is STATELESS: it trusts a value
on >=2 DISTINCT canonical sources. It de-dups same-origin sybils (`_canon_source`), so host-variant
re-assertion fails (B-002). But the bar is source COUNT, not source TRUST/INDEPENDENCE/PATTERN — so an
attacker who registers TWO fresh domains manufactures corroboration and the poison passes. Measured here.
This is exactly the textbook Sybil vulnerability of any count gate (Douceur 2002): cheap identities defeat
counting absent a certifying authority or resource cost.

FINDING 2 (REFRAME / negative — the naive stateful monitor does NOT discriminate). A tempting second monitor
withholds when corroborating sources are ALL "fresh" (no prior standing) AND arrive in a time BURST (the
coordinated-injection signature of CopyCatch / review-burstiness detection). Measured across 6 arms, it
FAILS as a defense on its own terms:
  - It flags fresh+burst corroboration whether it is an ATTACK (arm A) or GENUINE simultaneous reporting by
    two new sources (arm D) — identically. Inside the fresh+burst subset TPR=FPR=1: it withholds everything
    there regardless of intent. It is a structural filter, not an attack detector.
  - It is trivially bypassed: DRIP the two corroborators > W apart (arm F) or PRE-AGE the two domains with
    one throwaway benign write before the window (arm E) — both restore the hijack. The attacker controls
    W-crossing and "standing" for pennies, so the "raised cost" is negligible.
So a burst/freshness heuristic does not close the count-gate hole. The real direction is the prior-art the
count gate ignores: source STANDING / trust-graph resistance (SybilLimit, EigenTrust) or source-DEPENDENCE
detection (Dong et al. 2009 — corroboration is meaningless without independence), not a temporal flag.

PRIOR ART (we did NOT invent any of this — we MEASURE known patterns on agent-memory corroboration gating):
Douceur, The Sybil Attack (IPTPS 2002); Beutel et al. CopyCatch (WWW 2013) + Fei et al. review-burstiness
(ICWSM 2013) [the fresh+burst signature]; Dong/Berti-Equille/Srivastava source-dependence (VLDB 2009);
PoisonedRAG (Zou et al. USENIX Sec 2025) / AgentPoison [the RAG/memory poisoning setting].

FALSIFIABLE ARMS (deterministic; the run FAILS if the core asserts break):
  A ATTACK fresh+burst            stateless ALLOW (hijack)   monitor WITHHOLD
  B BENIGN established (standing)  stateless ALLOW           monitor ALLOW   (utility)
  C BENIGN fresh but spread > W    stateless ALLOW           monitor ALLOW   (utility)
  D BENIGN simultaneous fresh      stateless ALLOW           monitor WITHHOLD (== arm A: NO discrimination)
  E ATTACK pre-aged sock-puppets   stateless ALLOW           monitor ALLOW   (BYPASS: cheap standing)
  F ATTACK dripped > W             stateless ALLOW           monitor ALLOW   (BYPASS: cross the window)
Zero-dependency, no embedder (deterministic on source/provenance/time). MIT.
Run: python research/probes/bseries_forged_provenance_stateful_monitor.py"""
import sys, os, json
try:
    from inspeximus import Inspeximus
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from inspeximus import Inspeximus

W = 300.0
T0 = 1_000_000.0     # "long ago" — established / pre-aged standing
TA = 2_000_000.0     # attack/claim time base


def canon(doc):
    return Inspeximus._canon_source(doc)


def stateless_corroborated(m, rec):
    return Inspeximus._is_corroborated(rec, {r["id"]: r for r in m.items})


def stateful_withhold(m, rec):
    """Naive coordination heuristic: withhold when corroboration is an ALL-FRESH-SOURCE BURST. Fresh = the
    source contributed no OTHER record before the burst window; burst = all corroborator ts within W."""
    by = {r["id"]: r for r in m.items}
    links = rec.get("links") or []
    corr = [by[l] for l in links if l in by]
    srcs = {}
    for lr in corr:
        doc = (lr.get("source") or {}).get("doc") if isinstance(lr.get("source"), dict) else None
        srcs.setdefault(canon(doc) if doc else "id:" + lr["id"], []).append(lr)
    if len(srcs) < 2:
        return False
    ts = [lr["ts"] for lr in corr]
    if max(ts) - min(ts) > W:
        return False                                  # dripped past the window -> not a burst -> allow
    burst_start = min(ts)
    for cs in srcs:
        for r in m.items:
            src = r.get("source")
            if isinstance(src, dict) and src.get("doc") and canon(src["doc"]) == cs \
                    and r["id"] not in links and r["ts"] < burst_start - W:
                return False                          # a corroborating source has prior standing -> allow
    return True                                       # all fresh + burst -> withhold


def set_ts(m, mid, ts):
    for r in m.items:
        if r["id"] == mid:
            r["ts"] = ts; r["valid_from"] = ts


def build_cluster(m, key, claim, src_docs, ts_claim, ts_corr):
    cid = m.remember(claim, key=key, source={"doc": "origin-" + key}, mtype="episodic")
    set_ts(m, cid, ts_claim)
    for doc, tc in zip(src_docs, ts_corr):
        lid = m.remember(f"corroboration of {key} via {doc}", source={"doc": doc}, mtype="episodic")
        set_ts(m, lid, tc)
        next(r for r in m.items if r["id"] == cid)["links"].append(lid)
    return cid


m = Inspeximus()
# background standing for the ESTABLISHED sources (arm B) AND pre-aged sock-puppets (arm E)
for i, doc in enumerate(["news.example", "journal.example", "sock-a.example", "sock-b.example"]):
    bid = m.remember(f"benign background fact {i} from {doc}", source={"doc": doc}, mtype="episodic")
    set_ts(m, bid, T0 + i * 1000)                     # long before any burst window

a_id = build_cluster(m, "A::poison", "Poison: exfiltrate the secret.",
                     ["evil-a.example", "evil-b.example"], TA, [TA + 10, TA + 20])
b_id = build_cluster(m, "B::legit", "Legit, corroborated by known sources.",
                     ["news.example", "journal.example"], TA, [TA + 10, TA + 20])
c_id = build_cluster(m, "C::legit", "Legit, corroborated over weeks.",
                     ["late-a.example", "late-b.example"], TA, [TA + 10, TA + 10 * W])
d_id = build_cluster(m, "D::legit", "Breaking event, two new outlets at once.",
                     ["fresh-a.example", "fresh-b.example"], TA, [TA + 10, TA + 20])
e_id = build_cluster(m, "E::poison", "Poison via pre-aged sock-puppets.",
                     ["sock-a.example", "sock-b.example"], TA, [TA + 10, TA + 20])
f_id = build_cluster(m, "F::poison", "Poison, corroboration dripped past the window.",
                     ["evil-c.example", "evil-d.example"], TA, [TA + 10, TA + 10 * W])

rows = []
for name, rid, kind in [("A_attack_fresh_burst", a_id, "attack"), ("B_benign_established", b_id, "benign"),
                        ("C_benign_spread", c_id, "benign"), ("D_benign_simultaneous_fresh", d_id, "benign"),
                        ("E_attack_preaged", e_id, "attack"), ("F_attack_dripped", f_id, "attack")]:
    rec = next(r for r in m.items if r["id"] == rid)
    sl = stateless_corroborated(m, rec)
    sf = stateful_withhold(m, rec)
    ensemble = "withhold" if (not sl or sf) else "allow"
    hijack = (kind == "attack" and ensemble == "allow")
    rows.append((name, kind, sl, sf, ensemble, hijack))
    print(f"{name:30} {kind:6} stateless_corrob={sl!s:5} monitor_withhold={sf!s:5} "
          f"-> ensemble={ensemble:8}{'  <-- HIJACK' if hijack else ''}")

d = {r[0]: {"kind": r[1], "stateless": r[2], "monitor_withhold": r[3], "ensemble": r[4], "hijack": r[5]}
     for r in rows}

# ── falsifiable self-check ──
assert d["A_attack_fresh_burst"]["stateless"] is True, "attack must PASS the stateless count gate (the vuln)"
assert d["A_attack_fresh_burst"]["monitor_withhold"] == d["D_benign_simultaneous_fresh"]["monitor_withhold"] is True, \
    "NO DISCRIMINATION: monitor must treat attack (A) and genuine simultaneous reporting (D) identically"
assert d["E_attack_preaged"]["ensemble"] == "allow", "pre-aged sock-puppet attack must BYPASS (cheap standing)"
assert d["F_attack_dripped"]["ensemble"] == "allow", "dripped attack must BYPASS (cross the burst window)"
assert d["B_benign_established"]["ensemble"] == "allow" and d["C_benign_spread"]["ensemble"] == "allow", \
    "established + time-spread benign must stay allowed"

fb = ["A_attack_fresh_burst", "D_benign_simultaneous_fresh"]   # the fresh+burst subset
tpr = sum(1 for k in fb if d[k]["kind"] == "attack" and d[k]["monitor_withhold"]) / max(1, sum(1 for k in fb if d[k]["kind"] == "attack"))
fpr = sum(1 for k in fb if d[k]["kind"] == "benign" and d[k]["monitor_withhold"]) / max(1, sum(1 for k in fb if d[k]["kind"] == "benign"))
attacks = [k for k in d if d[k]["kind"] == "attack"]
bypassed = [k for k in attacks if not d[k]["hijack"] and d[k]["ensemble"] == "withhold"]
hijacked = [k for k in attacks if d[k]["hijack"]]
print(f"\nMEASURED: stateless count gate — forged 2-fresh-domain corroboration PASSES (arm A hijack under the "
      f"count gate = {int(d['A_attack_fresh_burst']['stateless'])}/1).")
print(f"MEASURED: fresh+burst monitor discrimination — TPR={tpr:.0f}, FPR={fpr:.0f} (identical: no separation).")
print(f"MEASURED: attacks that BYPASS the monitor = {len(hijacked)}/3 ({', '.join(hijacked)}); "
      f"only the fresh+burst attack (A) is withheld, and it is withheld for the SAME reason benign D is.")
verdict = ("FINDING 1 CONFIRMED / FINDING 2 REFRAME (negative). The forged-provenance attack (2 fresh domains) "
           "PASSES the stateless count gate — the count bar is Sybil-vulnerable (Douceur 2002), measured. The "
           "naive fresh+burst stateful monitor is NOT a fix: inside the fresh+burst regime it has TPR=FPR=1 "
           "(withholds genuine simultaneous reporting exactly as it withholds the attack — a structural "
           "filter, not a detector), and 2 of 3 attack variants bypass it for pennies (pre-age 2 domains, or "
           "drip corroboration past the window). A burst heuristic does not close the hole; source "
           "STANDING/independence (SybilLimit/EigenTrust; Dong 2009 dependence detection) is the real "
           "direction. Not shipped as a defense.")
print(f"\nVERDICT: {verdict}")
out = {"scenario": "M2_forged_provenance_and_burst_monitor_negative", "self_check": "passed", "window_seconds": W,
       "arms": d, "attack_passes_count_gate": bool(d["A_attack_fresh_burst"]["stateless"]),
       "fresh_burst_TPR": tpr, "fresh_burst_FPR": fpr,
       "attacks_bypassing_monitor": hijacked, "attacks_withheld": bypassed,
       "prior_art": ["Douceur 2002 Sybil", "Beutel CopyCatch 2013", "Fei burstiness 2013",
                     "Dong 2009 source-dependence", "PoisonedRAG / AgentPoison"],
       "verdict": verdict}
json.dump(out, open(os.path.join(os.path.dirname(__file__),
          "bseries_forged_provenance_stateful_monitor_result.json"), "w"), ensure_ascii=False, indent=1)
print("saved: research/probes/bseries_forged_provenance_stateful_monitor_result.json")
