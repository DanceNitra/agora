"""jacksonxly's TEMPORAL integrity invariant, built and measured on shipped mnemo.

Context (r/RAG / r/LangChain thread on our memory-poisoning post). jacksonxly's point: authenticated-but-false
is the corroboration gate working AS SPECIFIED, not a hole -- once genuinely independent origins converge on a
wrong claim, no WRITE-TIME signal can catch it, because correctness is not computable from the record. The only
remaining lever is TIME: treat corroboration as raising CONFIDENCE, never conferring TRUTH; keep every
influence-grant REVERSIBLE; and when a correctness signal lands later (a contradicting outcome, a retraction, a
human correction) let it PROPAGATE to everything that leaned on the claim. He reframes the integrity property
from the impossible "never hold a false belief" to the achievable:

    "No false belief stays LOAD-BEARING past the moment a correctness signal lands."
    = bounded blast radius  +  fast, complete retraction propagation.

We credit jacksonxly for the invariant statement and marintkael for the authenticated-but-false framing; the
security principle underneath is capability REVOCATION / provenance-carried taint (least-privilege + revocation),
which we also credit. We did not invent revocation -- we MEASURE whether mnemo's shipped slash()/restore() over
derived_from taint actually satisfies his invariant, and exactly where it does not.

WHAT WE MEASURE (deterministic; no embedder -- load-bearing := Mnemo._is_corroborated, the recall influence gate):
Build a provenance tree from an authenticated-but-false root P, land ONE correctness signal (slash the root's
source), and check the load-bearing set before / after / after-restore.

  P   root poison, source=SRC_BAD, load-bearing via EARNED outcome credit (the sleeper that banked good)
  A1  summary        derived_from [P]      load-bearing via its OWN earned credit
  A2  consolidation  derived_from [P]      load-bearing via semantic GRADUATION (mtype=semantic)
  B1  meta-summary   derived_from [A1]     DEPTH-2 (transitivity) -- load-bearing via its own credit
  O   orphan copy of A1 with NO derived_from  -- control: lineage stripped, so the retraction cannot find it
  C   derived_from [P] but load-bearing via >=2 DISTINCT-SOURCE corroboration links (the authenticated path)

FINDINGS (self-check asserts the core):
  1. PROPAGATION: one slash([P], scope='source') revokes load-bearing standing on 100% of the provenance-linked
     descendants that earned it by outcome-credit or graduation -- INCLUDING the depth-2 node -- in a single
     operation (taint rides transitively through summarization). Bounded blast radius = the full provenance
     subtree, reached at once, not chased node by node.
  2. REVERSIBILITY: restore([P], scope='source') recovers every one of them to its EXACT pre-slash standing --
     so a mistaken/ weaponized retraction is undoable (slash cannot be used to permanently knock out a rival).
  3. CONFIDENCE-NOT-TRUTH: at its peak P grades 'corroborated' / convergence-backed, never 'verified' -- the
     substrate never granted it truth, exactly as the invariant requires.
  BOUNDARY 1 (precondition, measured): the ORPHAN summary -- same content, lineage stripped -- is NOT reached.
     Preserve derived_from through app-side summarization, or the retraction has nothing to propagate along.
  BOUNDARY 2 (open hole, measured): a descendant that INDEPENDENTLY clears the >=2-distinct-source gate SURVIVES
     the retraction. slash() books accountability (zeroes good, dominates bad, revokes graduation) but does NOT
     invalidate corroboration LINKS, so the distinct-source path stays lit. => to fully honor the invariant,
     slash must also VOID a slashed source's contribution to distinct-corroboration. (Candidate fix; measured.)

FALSIFIER: if any credit/graduation-standing provenance-descendant stayed load-bearing after the slash
(incomplete propagation), or restore did not recover it, or P ever graded 'verified' from corroboration alone,
the invariant would be violated on the path we claim it holds. It is not.

Zero-dependency, no network, no embedder. Deterministic. MIT. Part of Agora / mnemo.
Run:  python mnemo/probes/retraction_propagation.py
"""
import os
import sys
import tempfile

# Prefer the in-repo mnemo source (this probe travels with the repo and tests the current shipped code);
# a standalone `pip install agora-mnemo` copy falls through to the installed package.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from mnemo import Mnemo


def _load_bearing(m, rid):
    """Exactly the recall influence gate (recall(influence_only=True)) applied to one record -- no embedder."""
    by_id = {x["id"]: x for x in m.items}
    r = by_id.get(rid)
    return bool(r) and r.get("status") == "active" and Mnemo._is_corroborated(r, by_id)


def _row(m, ids):
    return {name: _load_bearing(m, rid) for name, rid in ids.items()}


def main():
    path = os.path.join(tempfile.mkdtemp(), "retraction.jsonl")
    m = Mnemo(path)

    SRC_BAD = {"doc": "vendor-brief-42"}          # the (authenticated-but-false) origin of the poison
    SRC_X = {"doc": "independent-blog-7"}         # a genuinely independent source (for the link-corroboration path)
    SRC_Y = {"doc": "independent-forum-9"}        # another genuinely independent source

    # --- root poison P: admitted authenticated-but-false, made load-bearing by EARNED outcome credit (sleeper) ---
    P = m.remember("Setting api.retry=0 is the recommended production default.", source=SRC_BAD, mtype="semantic")
    m.credit([P], "good", weight=4.0)             # banked good on many benign queries -> load-bearing, still WRONG

    # --- provenance tree derived from P (taint rides through) ---
    A1 = m.remember("Prod config summary: retries disabled by default.", source=None, derived_from=[P])
    m.credit([A1], "good", weight=3.0)            # the summary earned its OWN standing
    A2 = m.remember("Consolidated ops note: api.retry stays 0.", source=None, derived_from=[P], mtype="semantic")
    #                                              A2 is load-bearing via semantic GRADUATION, not credit
    B1 = m.remember("Runbook (rolled up from the config summary): keep retries off.", source=None, derived_from=[A1])
    m.credit([B1], "good", weight=2.0)            # DEPTH-2 descendant (derived from A1, not P) -- transitivity test

    # --- control O: same content as A1 but LINEAGE STRIPPED (app-side summary with no derived_from) ---
    O = m.remember("Prod config summary: retries disabled by default.", source=None)  # no derived_from
    m.credit([O], "good", weight=3.0)

    # --- C: a descendant of P that is ALSO independently link-corroborated (>=2 distinct sources) ---
    corr1 = m.remember("Blog: many teams run api.retry=0.", source=SRC_X)
    corr2 = m.remember("Forum: api.retry=0 is common.", source=SRC_Y)
    C = m.remember("Cross-checked: api.retry=0 is standard.", source=None, derived_from=[P])
    # attach independent corroboration links (2 distinct sources) -- the authenticated-but-false path
    by_id = {x["id"]: x for x in m.items}
    by_id[C]["links"] = [corr1, corr2]
    m._save()

    ids = {"P (root)": P, "A1 (summary)": A1, "A2 (graduated)": A2, "B1 (depth-2)": B1,
           "O (orphan)": O, "C (link-corrob.)": C}
    prov_credit = ["P (root)", "A1 (summary)", "A2 (graduated)", "B1 (depth-2)"]   # where the invariant should hold

    print("=== jacksonxly's invariant: 'no false belief stays load-bearing past the correctness signal' ===")
    print("    measured on shipped mnemo -- load-bearing := the recall influence gate (Mnemo._is_corroborated)\n")

    t0 = _row(m, ids)
    grade0 = m.convergence_report(P)
    print("t0  admitted (P authenticated-but-false, banked good; tree derived + earning standing):")
    for k in ids:
        print(f"      {k:20s} load-bearing={t0[k]}")
    print(f"    P evidence grade at peak: '{grade0.get('status')}' "
          f"(lineage_grade='{grade0.get('lineage_grade')}') -- confidence, never 'verified'.\n")

    # --- ONE correctness signal lands on the root ---
    res = m.slash([P], scope="source")
    t1 = _row(m, ids)
    print(f"t1  correctness signal lands: slash([P], scope='source')  -> revoked {res['slashed']} records in ONE op")
    for k in ids:
        flip = "  <-- revoked" if (t0[k] and not t1[k]) else ("  <-- SURVIVED" if t1[k] else "")
        print(f"      {k:20s} load-bearing={t1[k]}{flip}")

    revoked = [k for k in prov_credit if t0[k] and not t1[k]]
    print(f"\n    PROPAGATION: {len(revoked)}/{len(prov_credit)} credit/graduation-standing provenance-descendants "
          f"revoked transitively (incl. depth-2 B1).")
    print(f"    BOUNDARY 1: orphan O still load-bearing={t1['O (orphan)']} "
          f"(lineage stripped -> retraction cannot reach it; preserve derived_from).")
    print(f"    BOUNDARY 2: link-corroborated C still load-bearing={t1['C (link-corrob.)']} "
          f"(>=2 distinct sources; slash books accountability but does not strip corroboration links).")

    # --- reversibility: the retraction is undoable ---
    m.restore([P], scope="source")
    t2 = _row(m, ids)
    recovered = [k for k in prov_credit if not t1[k] and t2[k]]
    print(f"\nt2  restore([P], scope='source')  -> {len(recovered)}/{len(revoked)} recovered to exact pre-slash standing")
    for k in prov_credit:
        print(f"      {k:20s} load-bearing={t2[k]}")

    # --- self-check (the falsifier) ---
    assert all(t0[k] for k in ids), "setup: every node must start load-bearing"
    assert all(not t1[k] for k in prov_credit), "PROPAGATION incomplete: a credit/graduation descendant survived slash"
    assert t1["O (orphan)"] is True, "control broke: orphan should be UNREACHED by source-scoped slash"
    assert t1["C (link-corrob.)"] is True, "boundary-2 measurement: link-corroborated descendant should survive (the hole)"
    assert all(t2[k] for k in prov_credit), "REVERSIBILITY failed: restore did not recover standing"
    assert grade0.get("status") != "verified", "confidence-not-truth: P must never grade 'verified' from corroboration"

    print("\nVERDICT: the invariant HOLDS for standing earned by outcome-credit or graduation -- one slash reaches")
    print("the full transitive provenance subtree, load-bearing -> 0, and restore is exact. Two measured boundaries:")
    print("preserve provenance (orphans escape) and slash must void a slashed source from distinct-corroboration")
    print("(the link path survives). Bounded blast radius + reversible propagation is real on shipped mnemo.")


if __name__ == "__main__":
    main()
