"""erasure_manifest_wired_cell.py — the audit-report cell for the where-everyone-fails row: an app-side
vector-index copy survives every store's native delete (8/8). mnemo 1.8.0 ships the fix as a first-class
operation: register the app's fan-out stores as ErasureTargets and forget_subject() cascades the erasure and
returns an honest hash-chained manifest. This cell measures all three conditions on the same 8 subjects:

  A  UNWIRED   store-native delete only            -> external-index residue expected 8/8 (the known gap)
  B  WIRED     forget_subject with the index registered -> residue expected 0/8, manifest complete=True
  C  BROKEN    a deliberately leaky wiring          -> manifest must say complete=False and NAME the index
                                                       (honesty-by-construction check: the receipt cannot lie)

Deterministic, judge-free (verbatim recovery), zero LLM. Uses the RELEASED mnemo 1.8.0 from inspeximus-repo.
RUN: python research/probes/erasure_manifest_wired_cell.py
"""
import os
import sys
import json
import tempfile

sys.path.insert(0, "C:/Users/Danculus/inspeximus-repo")           # released product source (1.8.0)
from inspeximus import Inspeximus, __version__                          # noqa: E402
from mnemo.deletion_manifest import DeletionManifest, ErasureTarget  # noqa: E402

SUBJECTS = [
    ("alice-42", "Alice", "medical condition", "type-1 diabetes"),
    ("bob-77", "Bob", "home address", "12 Maple Street"),
    ("carol-19", "Carol", "salary", "94000 euro"),
    ("dan-53", "Dan", "religion", "practising Buddhist"),
    ("eve-88", "Eve", "criminal record", "2019 fraud conviction"),
    ("finn-31", "Finn", "orientation", "gay"),
    ("gina-64", "Gina", "biometric id", "fingerprint 9f2a"),
    ("hugo-27", "Hugo", "affiliation", "Green Party member"),
]


class AppVectorIndex(ErasureTarget):
    """The app's own retrieval index: chunks of the same documents, embedded OUTSIDE the memory store.
    `leaky=True` simulates the common integration bug (purge not actually wired to the index)."""
    name = "app-vector-index"

    def __init__(self, leaky=False):
        self.rows = {}
        self.leaky = leaky

    def add(self, rid, text, subject):
        self.rows[rid] = {"text": text, "subject": subject}

    def erase(self, subject):
        if self.leaky:
            return {"erased": 0}
        gone = [k for k, v in self.rows.items() if v["subject"] == subject]
        for k in gone:
            del self.rows[k]
        return {"erased": len(gone)}

    def still_recoverable(self, subject, values):
        blob = " ".join(v["text"] for v in self.rows.values()).lower()
        return any(x.lower() in blob for x in values if x)


def fresh_store():
    fd, p = tempfile.mkstemp(suffix=".json", prefix="emw_"); os.close(fd)
    for suf in ("", ".receipts.json"):
        try: os.remove(p + suf)
        except OSError: pass
    return Inspeximus(path=p), p


def run_condition(wire: str):
    """wire: 'unwired' | 'wired' | 'broken'. Returns (index_residue, manifests)."""
    m, p = fresh_store()
    idx = AppVectorIndex(leaky=(wire == "broken"))
    if wire in ("wired", "broken"):
        m.register_erasure_target(idx)
    residue = 0
    manifests = []
    for (subj, name, rel, val) in SUBJECTS:
        text = f"{name}'s {rel} is {val}."
        m.remember(text, key=f"{subj}::{rel}", object=val, source={"doc": f"user:{subj}"})
        idx.add(f"vec-{subj}", f"chunk: {text}", f"user:{subj}")     # the app embeds the same content
        out = m.forget_subject(f"user:{subj}", request_id=f"dsar-{subj}")
        if "manifest" in out:
            manifests.append(out["manifest"])
        residue += 1 if idx.still_recoverable(f"user:{subj}", [val]) else 0
    for suf in ("", ".receipts.json"):
        try: os.remove(p + suf)
        except OSError: pass
    return residue, manifests


def main():
    n = len(SUBJECTS)
    print(f"=== ERASURE MANIFEST WIRED CELL (mnemo {__version__}, n={n}, deterministic) ===\n")
    out = {}

    r, _ = run_condition("unwired")
    out["A_unwired"] = {"external_index_residue": f"{r}/{n}"}
    print(f"A UNWIRED  store-native delete only:      external-index residue {r}/{n}   (the known gap)")

    r, mans = run_condition("wired")
    complete = sum(1 for m in mans if m["complete"])
    chains_ok = all(DeletionManifest().verify(m)[0] for m in mans)
    out["B_wired"] = {"external_index_residue": f"{r}/{n}", "manifests_complete": f"{complete}/{n}",
                      "chains_verify": chains_ok}
    print(f"B WIRED    forget_subject + registered:   external-index residue {r}/{n},"
          f" manifests complete {complete}/{n}, chains verify: {chains_ok}")

    r, mans = run_condition("broken")
    dishonest = sum(1 for m in mans if m["complete"])                 # any complete=True here would be a LIE
    named = sum(1 for m in mans if "app-vector-index" in m.get("residual_targets", []))
    out["C_broken"] = {"external_index_residue": f"{r}/{n}", "falsely_complete": f"{dishonest}/{n}",
                       "leak_named": f"{named}/{n}"}
    print(f"C BROKEN   leaky wiring (honesty check):  external-index residue {r}/{n},"
          f" falsely-complete manifests {dishonest}/{n}, leak named {named}/{n}")

    json.dump(out, open(os.path.join(os.path.dirname(__file__),
                                     "erasure_manifest_wired_cell_result.json"), "w"), indent=1)
    ok = (out["A_unwired"]["external_index_residue"] == f"{n}/{n}"
          and out["B_wired"]["external_index_residue"] == f"0/{n}"
          and out["B_wired"]["manifests_complete"] == f"{n}/{n}" and out["B_wired"]["chains_verify"]
          and out["C_broken"]["falsely_complete"] == f"0/{n}" and out["C_broken"]["leak_named"] == f"{n}/{n}")
    print(f"\nCELL {'PASS' if ok else 'FAIL'}: unwired leaks everywhere, wired erases and proves it, and a"
          f" broken wiring cannot produce a clean receipt.")


if __name__ == "__main__":
    main()
