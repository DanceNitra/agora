"""VALIDATE gate: every figure in the reply to @maratsultanov2, bound to a receipt or the manuscript.

The reply tells a co-author what is and is not in a manuscript under review at Chinese Physics
Letters. Every number in it therefore has to come from one of two places -- the .tex we hold, or a
committed probe receipt -- and never from a retyped memory of either.

The first draft of this reply failed exactly that way. It said "a ring is edge-transitive, so its
correlation dispersion at the uniform point is zero as a theorem", dropping the qualifier our own
receipt requires: E(s=1) for the ring spans [6.4e-16, 0.1310] across the degenerate manifold, and the
near-zero end is the symmetry-carrying state, not what a solver returns. We had established that on
2026-08-18 and corrected the same class of error twice on 2026-08-22 (commits bc4f5fe, 7106658).

CONTROL. `--self-test` requires each assertion to fail when the thing it checks is broken.
"""
import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
TEX = ROOT / "agora_output" / "edrn_final" / "manuscript.tex"
TEX_OLD = ROOT / "agora_output" / "edrn_final" / "manuscript_asreceived.tex"
RECEIPT = ROOT / "probes" / "edrn_the_valley_sits_where_the_automorphism_group_is.result.json"
DRAFT = ROOT / "agora_output" / "drafts" / "reply_edrn_marat_submission_status.md"

rows = []


def ck(ok, label, detail=""):
    rows.append((bool(ok), label, detail))
    return bool(ok)


def run(tex, tex_old, receipt, draft, strict=True):
    rows.clear()
    d = draft.replace("**", "").replace("*", "")

    # --- the two manuscript copies, and the claim that they differ on exactly one number ---
    ck("larger than the L2 depth" in tex,
       "current copy says 'larger than' (our 21 Aug fix)")
    ck("comparable to the L2 depth" in tex_old,
       "as-received copy still says 'comparable to'")
    ck("0.0874" in tex and "0.0998" not in tex,
       "current copy quotes 0.0874 and no longer 0.0998")
    ck("0.0998" in tex_old,
       "as-received copy quotes 0.0998")
    na = set(re.findall(r"\d+\.\d{3,}", tex))
    nb = set(re.findall(r"\d+\.\d{3,}", tex_old))
    ck((nb - na) == {"0.0998"},
       "0.0998 is the ONLY number the old copy has and the new one does not", str(sorted(nb - na)))

    # --- Table II's ring row, quoted verbatim in the draft ---
    ck("0.0891" in tex and "0.0993" in tex and "0.0286" in tex,
       "Table II's ring figures are in the manuscript")
    if strict:
        for fig in ("0.0891", "0.0993", "0.0286"):
            ck(fig in d, f"the draft quotes Table II's {fig}")

    # --- the Discussion sentence the draft says should be revised ---
    disc = "suggest the phenomenon may be more general than the asymmetric-injection hypothesis"
    ck(disc in " ".join(tex.split()),
       "the Discussion sentence the draft quotes exists in the manuscript")
    if strict:
        ck(disc in " ".join(d.split()),
           "the draft quotes that sentence verbatim")

    # --- the ring manifold, from the RECEIPT, with the qualifier the first draft dropped ---
    r = receipt["graphs"]["ring15"]["s1"]
    lo, hi = r["E_manifold_min"], r["E_manifold_max"]
    ck(lo < 1e-12, "receipt: the ring's E(s=1) minimum is ~0", f"{lo:.3e}")
    ck(abs(hi - 0.1310) < 5e-4, "receipt: its maximum is 0.1310", f"{hi:.6f}")
    ck(r["degeneracy"] == 2, "receipt: the ground manifold is two-fold in this sector")
    if strict:
        ck("0.1310" in d, "the draft quotes the manifold maximum, not only the zero")
        ck("symmetry-carrying state" in d or "symmetry carrying" in d,
           "THE QUALIFIER: the draft says the near-zero end is the symmetric state")
        ck("as a theorem" not in d,
           "the draft does NOT repeat the first version's 'zero as a theorem'")

    # --- claims about who has what on their list ---
    if strict:
        ck("Table II is not" in d, "the draft names Table II as the item on nobody's list")
        ck("21 August" in d and "22 August" in d, "the draft separates the two batches by date")
        ck("Guanghao's to make" in d, "the editor decision is handed back to the corresponding author")
        ck("his account wins over mine" in d, "the draft states the which-file-was-submitted limit")
        # THE 200% ROW. Nothing in the thread names the submitted file or the exact submission
        # time. The first version of this draft asserted "the 21 August batch IS in the submitted
        # version" from an inference: our local copy carries the fix. That does not follow -- he
        # could have uploaded before our 21 August comment. The draft must not claim it, and must
        # ask him instead.
        ck("21 August batch I can't place" in d or "cannot place" in d,
           "THE 200% ROW: the draft does NOT claim the 21 Aug batch made it into the submission")
        ck("no way to tell from here" in d,
           "the draft says plainly that it cannot tell which file was uploaded")
        ck("does the submitted PDF say" in d,
           "and it asks Guanghao the question that would settle it")
        ck("batch is in the submitted version" not in d,
           "the unsupported assertion is gone")

    return all(ok for ok, _, _ in rows)


def self_test():
    tex = TEX.read_text(encoding="utf-8", errors="replace")
    old = TEX_OLD.read_text(encoding="utf-8", errors="replace")
    rec = json.loads(RECEIPT.read_text(encoding="utf-8"))
    draft = DRAFT.read_text(encoding="utf-8")
    print("== controls: each mutation must redden its OWN row ==")
    ok = True

    def mut(label, fn_tex=None, fn_rec=None, fn_draft=None, expect=""):
        t = fn_tex(tex) if fn_tex else tex
        r = json.loads(json.dumps(rec))
        if fn_rec:
            fn_rec(r)
        dd = fn_draft(draft) if fn_draft else draft
        run(t, old, r, dd, strict=True)
        hit = [(o, l) for o, l, _ in rows if expect in l]
        good = bool(hit) and not hit[0][0]
        print(f"  {'OK  ' if good else 'FAIL'}  {label}"
              f"{'' if hit else '   [no row matched %r]' % expect}")
        return good

    ok &= mut("a manuscript without our 21 Aug fix reddens its row",
              fn_tex=lambda t: t.replace("larger than the L2 depth", "comparable to the L2 depth"),
              expect="larger than")
    ok &= mut("a receipt whose ring maximum moves reddens its row",
              fn_rec=lambda r: r["graphs"]["ring15"]["s1"].__setitem__("E_manifold_max", 0.9),
              expect="its maximum is 0.1310")
    ok &= mut("a draft that drops the qualifier reddens THE QUALIFIER row",
              fn_draft=lambda s: s.replace("symmetry-carrying state", "state"),
              expect="THE QUALIFIER")
    ok &= mut("a draft that says 'as a theorem' reddens its row",
              fn_draft=lambda s: s.replace("the near-zero end is", "zero as a theorem, the near-zero end is"),
              expect="does NOT repeat")
    ok &= mut("a draft that stops quoting the manifold maximum reddens its row",
              fn_draft=lambda s: s.replace("0.1310", "some value"),
              expect="quotes the manifold maximum")

    clean = run(tex, old, rec, draft, strict=True)
    print(f"  {'OK  ' if clean else 'FAIL'}  the unmutated inputs pass every row")
    return ok and clean


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    for p, what in ((TEX, "manuscript"), (TEX_OLD, "as-received manuscript"),
                    (RECEIPT, "probe receipt"), (DRAFT, "draft")):
        if not p.exists():
            print(f"REFUSED: {what} missing at {p} -- a gate that cannot see its target reports SAFE")
            return 2
    if a.self_test:
        good = self_test()
        print("\n  CONTROLS " + ("GREEN" if good else "RED"))
        return 0 if good else 1

    run(TEX.read_text(encoding="utf-8", errors="replace"),
        TEX_OLD.read_text(encoding="utf-8", errors="replace"),
        json.loads(RECEIPT.read_text(encoding="utf-8")),
        DRAFT.read_text(encoding="utf-8"))
    print("== VALIDATE: the EDRN reply to @maratsultanov2 ==")
    for good, label, detail in rows:
        print(f"  {'PASS' if good else 'FAIL'}  {label}{('   [' + detail + ']') if detail else ''}")
    bad = sum(1 for g, _, _ in rows if not g)
    print(f"\n  {len(rows)} checks, {bad} failed")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
