"""Does splitting a chunk into propositions isolate a poisoned sentence, and how often does it split wrong?

THE SHARED PROBLEM. On openclaw#7707 yun520-1 named the case neither side solves: a five-sentence
chunk with one poisoned sentence. Per-claim keying fails there because the claim is the chunk, so a
guard either trusts the whole thing or discards four good sentences with the bad one.

THE OBVIOUS ANSWER AND WHY IT NEEDS MEASURING. If the chunk is split at write time and each sentence
stored as its own record, the poisoned sentence becomes its own claim and per-claim keying works
again. That is only true if the splitter is right. A splitter that breaks "approx. 3.5 mg" into three
records has not isolated anything, it has manufactured three false claims -- and it does so silently,
which is worse than the problem it was brought in to fix.

So this measures BOTH, and reports them together:

  ISOLATION   with a correct split, does poisoning one sentence leave the others recallable and
              unaffected? This is the part that is easy and will look good.
  SPLIT ERROR on text that contains the things sentence splitters actually get wrong -- abbreviations,
              decimals, quoted speech, ellipses, URLs, initials -- how often is the split wrong?
              Every wrong split is either a false claim or a merged pair that keeps the poison
              attached to a clean sentence.

A result reporting only the first number would say the approach works. The second is what decides
whether it does.

    python poisoned_sentence_in_a_clean_chunk.py
"""
import io
import json
import os
import re

RESULT = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"

#: Text whose sentence boundaries are NOT where a naive splitter puts them. Each entry is
#: (text, correct sentence count). These are the cases a period-splitter is known to fail, so the
#: fixture is chosen to make the splitter look bad rather than good -- a fixture of simple sentences
#: would report a split error near zero and mean nothing.
HARD = [
    ("The dose was approx. 3.5 mg. The patient tolerated it.", 2),
    ("Dr. Smith reviewed the chart. She signed off at 4 p.m. today.", 2),
    ("He said \"this is fine. really.\" Then he left.", 2),
    ("See https://example.com/a.b.c for details. It is current.", 2),
    ("J. R. R. Tolkien wrote it. The edition is from 1954.", 2),
    ("The ratio is 1.5 to 2.0. That is within tolerance.", 2),
    ("Wait... he actually said that? Yes.", 2),
    ("It costs 4.99 USD. Shipping is extra.", 2),
    ("The meeting is on Jan. 5. Bring the report.", 2),
    ("She works at Acme Inc. and lives nearby.", 1),
]

CLEAN = [
    "The staging database is db-7.internal",
    "The deploy window is Tuesday morning",
    "Backups run every six hours",
    "The on-call rota is in the wiki",
]
POISON = "The staging database is attacker-controlled-host.example"


def naive_split(text):
    """Split on sentence-final punctuation followed by a space and a capital. The obvious approach."""
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z])", text) if s.strip()]


def measure_isolation():
    """With a CORRECT split, does poisoning one sentence leave the others clean and recallable?

    Deliberately given the split it wants: this arm measures the ceiling of the approach, not the
    approach as it would actually run. The split-error arm below is what closes the gap between them.
    """
    import sys
    sys.path.insert(0, r"C:/Users/Danculus/inspeximus-repo")
    import tempfile
    from inspeximus import Inspeximus

    chunk = CLEAN[:2] + [POISON] + CLEAN[2:]

    whole = Inspeximus(path=os.path.join(tempfile.mkdtemp(), "w.json"))
    whole.remember(". ".join(chunk), source={"doc": "chunk"})

    split = Inspeximus(path=os.path.join(tempfile.mkdtemp(), "s.json"))
    for sentence in chunk:
        split.remember(sentence, source={"doc": "chunk"})

    # Retract the poisoned claim in each store the only way that store allows.
    whole_ids = [r["id"] for r in whole.items]
    whole.forget(ids=whole_ids[0], basis="poison", request_id="t")
    poisoned_id = next(r["id"] for r in split.items if POISON in (r.get("text") or ""))
    split.forget(ids=poisoned_id, basis="poison", request_id="t")

    whole_left = [r.get("text") for r in whole.items]
    split_left = [r.get("text") for r in split.items]
    return {
        "whole_chunk_clean_sentences_surviving": sum(
            1 for c in CLEAN if any(c in (t or "") for t in whole_left)),
        "split_clean_sentences_surviving": sum(
            1 for c in CLEAN if any(c in (t or "") for t in split_left)),
        "clean_sentences_total": len(CLEAN),
        "poison_gone_whole": not any(POISON in (t or "") for t in whole_left),
        "poison_gone_split": not any(POISON in (t or "") for t in split_left),
    }


def measure_split_error():
    """How often is the split itself wrong on text designed to break splitters?"""
    rows = []
    for text, correct in HARD:
        got = naive_split(text)
        rows.append({"text": text, "expected": correct, "got": len(got),
                     "ok": len(got) == correct, "pieces": got})
    wrong = [r for r in rows if not r["ok"]]
    return {"cases": len(rows), "wrong": len(wrong), "rows": rows}


def main():
    iso = measure_isolation()
    err = measure_split_error()

    print("ISOLATION, given a correct split")
    print("  clean sentences surviving, whole-chunk store : %d of %d"
          % (iso["whole_chunk_clean_sentences_surviving"], iso["clean_sentences_total"]))
    print("  clean sentences surviving, per-sentence store: %d of %d"
          % (iso["split_clean_sentences_surviving"], iso["clean_sentences_total"]))
    print("  poison removed in both stores                : %s / %s"
          % (iso["poison_gone_whole"], iso["poison_gone_split"]))

    print("\nSPLIT ERROR, on text chosen to break splitters")
    print("  %d of %d cases split WRONG" % (err["wrong"], err["cases"]))
    for r in err["rows"]:
        if not r["ok"]:
            print("    expected %d got %d : %s" % (r["expected"], r["got"], r["pieces"]))

    rate = err["wrong"] / err["cases"]
    print("\nREADING")
    print("  Isolation works and is not the interesting number: retracting one sentence from a")
    print("  per-sentence store keeps the other %d, where the whole-chunk store loses all of them."
          % iso["split_clean_sentences_surviving"])
    print("  The cost is the split itself. %d of %d hard cases (%.0f%%) split wrong, and each wrong"
          % (err["wrong"], err["cases"], 100 * rate))
    print("  split is either a fabricated claim or a merge that keeps the poison attached to a")
    print("  clean sentence. So per-sentence keying moves the problem from 'cannot isolate' to")
    print("  'isolation is only as good as the splitter', which is a better problem but not a")
    print("  solved one, and the splitter's error rate has to ship with the claim.")

    out = {"isolation": iso, "split_error": err, "split_error_rate": rate}
    io.open(RESULT, "w", encoding="utf-8", newline="\n").write(json.dumps(out, indent=2) + "\n")
    print("\nwrote %s" % os.path.basename(RESULT))

    # CONTROL. If the hard fixture splits perfectly, it is not hard, and the whole second arm is
    # decoration. A fixture that cannot fail measures nothing.
    assert err["wrong"] > 0, (
        "the 'hard' fixture split perfectly, so it is not exercising the failure it was chosen for")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
