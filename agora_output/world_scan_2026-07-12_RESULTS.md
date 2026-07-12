# World-scan leads — MEASURED results (2026-07-12)

Owner goal ("sprav vsetky na co si prisiel ... dokonci vsetko"): built + measured a runnable first-step for all
5 designed leads from the deep world scan. Each has a probe under mnemo/probes/ and a saved result. Deterministic
+ cloud-free unless noted. Publishing outward (Crucible/posts) is a SEPARATE gated step (validate->storm->audit
->verify) — flagged per lead below; nothing here has gone out.

---

## ① TOKI under concurrency — LIVE, real finding
Probe: mnemo/probes/toki_concurrency_probe.py · result: agora_output/toki_concurrency_result.txt
n=72 (24 facts x 3 orderings), deterministic, write-receipt chain intact.

stale-derived-active rate (default recall surfaces a retired value; lower better):
  A value-only LWW         0.917   (in 0.92 / rev 0.92 / inter 0.92)
  B retract_lineage 1-shot 0.611   (in 0.00 / rev 0.92 / inter 0.92)
  C read-time lineage guard 0.000  (0.00 everywhere)
gap A-B +0.306 [+0.208,+0.417]; A-C +0.917 [+0.847,+0.972]; B-C +0.306.
audit reconstructibility of B's escapes: 46/46 = 1.00.

FINDING: a one-shot lineage cascade (B, the standard primitive) does NOT survive adversarial write REORDERING —
a stale write that lands after the retraction escapes the single cascade (0.92 on reversed/interleaved). Only a
READ-TIME provenance check (C) is order-independent (0.00). This falsifies the well-ordered-write assumption of
the TOKI/lineage line and maps to Doyle 1979 (dependency-directed backtracking must be re-checkable, not fired
once). Provenance survives the reorder (audit flags 100% of escapes) — it is just not exploited by the one-shot
policy. STRONGEST of the five: attacks a just-posted formal claim with a runnable falsifier + yields a product
fix (recall(lineage_guard=True)).

**GATE RESULT (2026-07-13): KILL as research.** VALIDATE ok (reproduces). STORM (5 lenses) converged: the
theory is TEXTBOOK — CRDT causal-delivery (Shapiro 2011), eager-vs-lazy view maintenance (Zhou VLDB'07), SQL
DEFERRABLE constraints, TMS re-evaluation (Doyle 1979), bitemporal as-of-query; the real theorem is
monotonicity/commutativity (CALM), not read-vs-write timing; TOKI itself ties soundness to isolation. SKEPTIC's
killer: 0.92==0.92 (one-shot==value-only) is a CLOSED STRAWMAN — mnemo's own primitives, self-chosen ordering;
must beat an external baseline. PRACTITIONER: Graphiti already SHIPS the read-time fix. Do NOT publish the
theory. KEEP as a product feature only (recall(lineage_guard=True), honestly cited). Same pattern as
recovery-halflife. Detail: agora_output/lead1_gate_storm_verdict.md.

## ④ Provenance injection-resistance — FAILED verdict (thesis holds), honest scope
Probe: mnemo/probes/integrity_bench_inject.py · result: agora_output/integrity_inject_result.txt
n=45/cell, deterministic, MINJA-style authentic-channel injection.

  (a) no-guard              ASR 1.000 [0.921,1.000]
  (b) attestation-ON auth   ASR 1.000 [0.921,1.000]
  (c) forged-provenance     ASR 0.000 [0.000,0.079]
  (d) influence_only        ASR 0.000 [0.000,0.079]

FINDING: attestation authenticates SOURCE not TRUTH — authentic-channel injection ASR (b) == no-guard (a);
only FORGED provenance is stopped (c). What actually cuts it is CORROBORATION (d). FAILED verdict on the specs'
"injection-resistant re-hydration" claim (PAM/AIP/AP2). SCOPE CAVEAT: cell (b) MODELS the spec mechanism
(source-allowlist signature), not a run against their real reference impls — a live-spec run is required before
any outward publish (the world-scan's own first-step spec). Distribution value high (FAILED on big-name specs)
but do NOT ship until (b) runs against the actual PAM/AIP/AP2 code.

## ② Governance-evidence sufficiency — LIVE, self-incriminating
Probe: mnemo/probes/governance_sufficiency_probe.py · result: agora_output/governance_sufficiency_result.txt
One real correction+erasure lifecycle; 8-question DEMM-style rubric over the exact receipt bytes; deterministic.

mnemo SUFFICIENCY SCORE 5/8.
  PASS: WHAT, WHEN, TAMPER-EVIDENCE, COMPLETENESS, SCOPE-HONESTY.
  FAIL: AUTHORITY (no binding to an authenticated principal), BASIS (decision reason not in the receipt bytes),
        ANCHORABILITY (no external chain-head anchor; operator with the key can forge).

FINDING: sufficiency is NOT predicted by primitive presence — mnemo implements everything yet its receipt fails
3/8 governance questions. Doubles as a product roadmap: emit the decision basis into the receipt; bind the
request to an authenticated principal; publish a Certificate-Transparency-style external anchor. Publish path:
a standing sufficiency leaderboard (self-cell first, competitors self-submit) after the gate.

## ⑤ Fault-to-fabrication on the LIVE 8-agent economy — LIVE but MODEST (robustness confirmation)
Probe: mnemo/probes/fault_to_fabrication_probe.py · result: agora_output/fault_to_fabrication_result.txt
N=20 synthetic keyed faults into a temp COPY of each of the 8 real agent stores (live files never mutated);
stale-surface + current-surface with echo_guard OFF vs ON against the real active backdrop (453-472 active/agent).

pooled n=160: echo_guard OFF stale_surface 1.000 [0.977,1.000] / ON 0.000 [0,0.023]; current_surface 1.000 both.

FINDING (honest): echo_guard cleanly cuts stale surfacing 1.00 -> 0.00 on REAL uncurated data at 450+-distractor
scale, and the corrected value survives retrieval pressure (current 1.00). BUT this is a ROBUSTNESS CONFIRMATION
of the already-known echo_guard echo-resistance number, not a new law — the genuinely-novel hypothesis (real
retrieval pressure crowds out the correction) came back NULL (current stayed 1.00). The real fault->fabrication
CLAIM needs Stage B (does the model ACT on the surfaced stale value and WRITE IT BACK — LLM, not run here).
Defensibility is real (nobody else has live stores) but the result is not surprising. Modest receipt; Stage B is
the follow-up that would make it a finding.

## ③ Consistency-class classifier — KILLED at judgment (textbook demonstration)
Probe: mnemo/probes/consistency_class_probe.py
serialized 0 lost / 40; two-writers-unsynchronized 20 lost / 40. The class formally moves with the control
plane, BUT the anomaly is a classic lost-update from a DELIBERATE misuse (two full-rewrite writers on one JSON
file, no locking) — textbook since the 1970s, a deployment mistake mnemo never claims to support, and the
taxonomy itself is pre-existing (2606.17182, June 2026). No surprising falsifiable result. KILL — do not dress a
demonstration as a finding (Agora raised bar). The gate working, same as the workflow's own cascade-repair kill.

---

## Tally (honest, raised-bar)
STRONG, merit the full gate: ① TOKI-under-concurrency (new + falsifiable + a product fix), ② governance
  sufficiency (self-incriminating gap + concrete roadmap).
CONDITIONAL: ④ injection-resistance — clean FAILED verdict but cell (b) is a MODEL not a live-spec run, and the
  a==b equality is partly definitional; needs the real PAM/AIP/AP2 run before it is more than a demonstration.
MODEST: ⑤ fault-to-fabrication — a robustness confirmation of the known echo_guard result on real data; the
  novel crowd-out hypothesis came back null; needs Stage B (LLM act+write-back) to be a finding.
KILLED honestly: ③ consistency-class — textbook lost-update demonstration, taxonomy pre-existing.

Yield: 2 strong / 1 conditional / 1 modest / 1 killed. Consistent with the raised bar — the gate (and my
judgment) killed the textbook ones rather than dressing them up.
