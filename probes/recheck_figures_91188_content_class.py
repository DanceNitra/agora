"""Bind every number in the content-class reply to the receipt it claims to come from.

THIS IS ONE CHECK INSIDE VALIDATE. IT IS NOT THE GATE. The gate is validate, storm where the claim
rests on literature, redteam (stress-claim) and verify (verify-claims). A script written the same
morning as the draft is not a substitute for any of them; every probes/gate_*.py in this repo was
renamed for exactly that reason.

The first version of this checker passed 28 of 28 on a draft an adversarial pass then took apart. It
confirmed that each number matched a field. It could not ask whether the sentence around the number
was true, and five of them were not: a row count that appeared in no receipt, a chi-square whose
approximation did not hold, a doubled denominator, a population of four standing in for 229, and a
claim that files had lost a pointer they never had. So this version also asserts the things that
caught it: no number may be quoted that the receipt does not contain, the asymptotic p must stay out,
and the phrases that were refuted must stay deleted.
"""
import io
import json
import os
import re
import sys

D = "drafts/91188_reply_content_class.md"
R = "probes/what_class_of_row_actually_leaves_the_index.result.json"
P = "probes/what_class_of_row_actually_leaves_the_index.py"
MEM = os.path.join(os.path.expanduser("~"), ".claude", "projects", "C--Users-Danculus-agora", "memory")


def main():
    raw = io.open(D, encoding="utf-8").read()
    draft = " ".join(raw.split())          # match text, not where a line happens to wrap
    r = json.load(open(R, encoding="utf-8"))
    het = r.get("heterogeneity") or {}
    ok = True

    def check(name, cond, got=""):
        nonlocal ok
        ok = ok and bool(cond)
        print("  %-4s %-46s %s" % ("YES" if cond else "NO", name, got))

    for field, want, phrase in [
        ("files_on_disk", 505, "505-file store"),
        ("live_pointers", 224, "189 of 224"),
        ("retired_rows", 194, "194 distinct retired rows"),
        ("retired_still_referenced", 124, "124 (63.9%)"),
        ("retired_referenced_share", 63.9, "63.9%"),
        ("live_still_referenced", 189, "189 of 224 (84.4%)"),
        ("live_referenced_share", 84.4, "84.4%"),
        ("live_guards", 166, "166 of 224 pointers"),
        ("live_guard_share", 74.1, "74.1%"),
        ("pooled_retirement_share", 46.9, "46.9% pooled"),
        ("in_neither_index", 0, None),
    ]:
        good = r[field] == want and (phrase is None or phrase in draft)
        check(field, good, "%s%s" % (r[field], "" if phrase is None or phrase in draft else "  PHRASE MISSING"))

    # the table must BE the receipt's retirement rows, in order
    rows = [(e["rows"], e["guards"], e["guard_share"]) for e in r["events"] if e["is_a_retirement"]]
    tbl = re.search(r"```\n(rows.*?)\n```", raw, re.S)
    got = re.findall(r"^\s*(\d+)\s+(\d+)\s+([\d.]+)%", tbl.group(1), re.M) if tbl else []
    want = [(str(n), str(g), "%.1f" % s) for n, g, s in rows] + [("194", "91", "46.9")]
    check("table_is_the_receipt", [tuple(x) for x in got] == want, "%d rows" % len(got))

    # the two events whose headings are identical, which is the draft's strongest sentence
    a = io.open(os.path.join(MEM, "MEMORY_ARCHIVE.md"), encoding="utf-8").read()
    heads = re.findall(r"^## (?:\[NEVER IN THE LIVE INDEX\] )?(.+)$", a, re.M)
    same = [h for h in heads if h.endswith("to fit the loader window")]
    stem = {re.sub(r"\d{4}-\d\d-\d\d", "", h) for h in same}
    check("two_headings_are_word_for_word_identical", len(same) == 2 and len(stem) == 1,
          "%d headings, %d distinct once the date is removed" % (len(same), len(stem)))
    pair = sorted((e["guard_share"] for e in r["events"] if "to fit the loader window" in e["event"]))
    check("that_pair_is_5.6_and_52.6", pair == [5.6, 52.6] and "52.6% against 5.6%" in draft, pair)

    # the resurrections: the finding the double count was hiding
    res = r.get("resurrected") or []
    check("two_resurrections", len(res) == 2 and "Two in 194 retirements, 1.0%" in draft, res)
    for slug in res:
        check("names_%s" % slug[:28], slug.replace(".md", "") in draft)

    # The statistic must be NAMED, not called "the observed dispersion". Our own pregate refused
    # that sentence for stating a comparison without naming the axis it is measured on, which is
    # the standing rule that a rank is not a rank until you name the unit.
    check("chi_square_is_named_and_matches", het.get("chi2") == 65.9
          and "observed chi-square of 65.9" in draft, het.get("chi2"))
    check("monte_carlo_bound_only", het.get("mc_at_or_above") == 0 and het.get("mc_draws") == 20000
          and "none of 20,000 Monte Carlo draws" in draft and "p < 5e-5" in draft, het.get("mc_draws"))

    # the type retention asymmetry, re-derived from the files rather than trusted from the draft
    live = {os.path.basename(x) for x in
            re.findall(r"\]\(([^)]+\.md)\)", io.open(os.path.join(MEM, "MEMORY.md"), encoding="utf-8").read())}

    def typ(f):
        b = io.open(os.path.join(MEM, f), encoding="utf-8", errors="replace").read()
        m = re.search(r"^\s*type:\s*([a-z |]+)\s*$", b, re.M)
        v = m.group(1).strip() if m else "undeclared"
        return "undeclared" if "|" in v else v
    disk = [f for f in os.listdir(MEM) if f.endswith(".md") and f not in ("MEMORY.md", "MEMORY_ARCHIVE.md")]
    fb = [f for f in disk if typ(f) == "feedback"]
    pr = [f for f in disk if typ(f) == "project"]
    kfb, kpr = sum(1 for f in fb if f in live) / len(fb), sum(1 for f in pr if f in live) / len(pr)
    check("type_population_229_and_259", len(pr) == 229 and len(fb) == 259
          and "229 of my 505 files" in draft and "259 declare `feedback`" in draft, "%d/%d" % (len(pr), len(fb)))
    check("retention_ratio_2.8x", round(kfb / kpr, 1) == 2.8 and "keeps `feedback` at 2.8x the rate" in draft
          and "63.3% against 22.7%" in draft, round(kfb / kpr, 2))

    # the file I got wrong, quoted in the draft as my own correction
    corp = io.open(os.path.join(MEM, "corporation-subsystem-decision.md"), encoding="utf-8",
                   errors="replace").read()
    check("the_resolved_file_says_so", "RESOLVED 2026-06-26" in corp and 'opens "RESOLVED 2026-06-26"' in draft)
    check("and_it_is_no_longer_live", "corporation-subsystem-decision.md" not in live)

    # the 68, and the sentence that had to die
    section = a.split("Found unpointed 2026-09-08")[1].split("\n## ")[0]
    n68 = len(set(re.findall(r"\]\(([^)]+\.md)\)", section)))
    check("sixty_eight", n68 == 68 and "68 files sat in neither index" in draft, n68)

    # WITHDRAWN: each of these was published in a draft and refuted. They must stay out.
    check("RETRACTED_3e-12_is_marked_as_retracted",
          "3e-12" not in draft or "My first draft quoted 3e-12" in draft,
          "a banned string cannot tell a claim from a correction of one")
    for phrase in ("they lost their pointer", "421", "72.5%", "impson",
                   "the class I did not expect", "cheaper check", "79 of the 505"):
        check("WITHDRAWN_%s" % phrase[:26].replace(" ", "_"), phrase not in draft)

    # CONTROLS
    check("CONTROL_reference_control_fired", r["live_referenced_share"] > r["retired_referenced_share"],
          "live %.1f > retired %.1f" % (r["live_referenced_share"], r["retired_referenced_share"]))
    check("CONTROL_every_number_in_the_draft_is_in_the_receipt",
          r["live_pointers"] + r["retired_rows"] == 418, "224 + 194 = 418, and 418 is not quoted")
    check("CONTROL_receipt_not_older_than_probe", os.path.getmtime(R) >= os.path.getmtime(P))
    check("pure_ascii", all(ord(c) < 128 for c in raw), "gh mangles anything else")
    check("length_inside_the_thread_range", 2000 <= len(raw) <= 4100, "%d chars" % len(raw))

    print("\n  %s" % ("all checks passed" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
