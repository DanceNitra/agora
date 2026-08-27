"""Verify erasure WITHOUT SEARCHING FOR THE VALUE. Two erasures must leave the same store.

WHY SEARCHING CANNOT WORK, established over six audit rounds and not worth a seventh. A check of the
form "the erased value must not appear in the store" is defeated by anything that transforms or
fragments it. Measured against our own suite: bz2, a one-byte XOR, utf-32 (which the search does NOT cover -- an
earlier version of this docstring listed it among the handled forms, which was false and is exactly
the kind of unchecked capability claim this file exists to argue against), and, with no encoding
trick whatsoever, the plain UTF-8 value written across two files as "is veg" and "etarian". Every
fix widened the list of recognised encodings, and the list is unbounded, so the rate of new escapes
never fell. The same limit applies to the specification's own confidentiality vector, which asserts
`forbidden_value not in evidence`.

NONE OF THIS IS NEW, AND THE FILE SHIPPED WITH NO CITATIONS AT ALL. Credit where it belongs:

  Ippolito et al., "Preventing Generation of Verbatim Memorization in Language Models Gives a False
  Sense of Privacy", INLG 2023 (2023.inlg-main.3) -- verbatim matching is not sufficient, and
  anticipating transforms is "an innumerable problem".
  Shu, Yao et al., CODASPY 2015 -- "none of the existing techniques is adequate for detecting
  transformed data leaks", in a storage setting closer to ours.
  NIST SP 800-88r1 (WITHDRAWN, superseded by r2, Sept 2025), sec. 4.7.3 -- already ranks
  compare-before-and-after above string search; r2 drops content inspection entirely.
  Garg, Goldwasser, Vasudevan, EUROCRYPT 2020 -- "perfect deletion-compliance", Def 2.2, which is
  the formal version of what this file gropes toward, and is STRICTLY STRONGER: it compares
  present-then-deleted against never-present, where this compares two different secrets and so
  cannot see residue that is identical for every secret yet still reveals that a deletion occurred.
  Naor and Teague, STOC 2001 -- history independence, the structural twin.
  Thudi et al., USENIX Security 2022 -- absence cannot be proven; only algorithmic definitions audit.

THE TEST THAT DOES WORK asks a different question. Not "is the value there?", which requires
recognising it, but "does the store's state DEPEND on it?", which does not.

Erase secret A from a fresh store. Erase secret B, of identical length, from an otherwise identical
fresh store. If the erasure was complete, the two stores are now in the same state: nothing that
remains was computed from the secret, so nothing that remains can differ. If any byte differs -- a
retained copy, a fragment, a gzip member, an XOR, a hash of the content, a length-revealing index --
the state is a function of the secret, and the secret is not gone.

THAT CLAIM WAS TOO STRONG AND AN INDEPENDENT PASS BROKE IT. Twelve ways, including two that store
the secret as UNENCODED PLAINTEXT. The method does not read the value, but the NORMALISERS do, and
three of them replace a VALUE rather than a shape: `{"trace_id": "<the secret>"}` and
`{"links": ["<the secret>"]}` are rewritten to placeholders, so the plaintext survives on disk while
both runs look identical. The `<HEX>` rule hides a reversible hexlified copy. And `errors="replace"`
collapses distinct byte sequences to the same U+FFFD, which is not a rule that can be widened -- it
is the decode step itself.

So the honest position: this trades one unbounded list for another. Searching required enumerating
ENCODINGS; this requires enumerating NORMALISERS and a SCAN SURFACE, and the surface leaks too --
writes outside the walked root, NTFS alternate data streams, file mtimes, and a locked file that
`except OSError: pass` drops from BOTH states so even its name disappears.

THE POSITIVE CONTROL BELOW DOES NOT CERTIFY THE NORMALISERS, which is what it was written to do.
`control_fires` is `ctl_a != ctl_b`, and the control states contain all ordinary residue, so any
residue makes it fire: it is vacuously true in every RESIDUE run, and it reported "caught" in all
eight false-negative runs while plaintext sat in the store.

WHAT REMAINS TRUE AND USEFUL. It catches everything the content search caught plus the three attacks
that beat it (split-across-files, bz2, XOR), it is stable across ten runs, and it needs no knowledge
of an encoding to do so. It is a better smoke test. It is not a proof of erasure, and no black-box
inspection of a store appears to be one.

WHAT IT COSTS. It cannot say WHERE the residue is, only that there is some. It needs the two runs to
be otherwise deterministic, so anything legitimately variable -- ids, timestamps, paths, nonces --
must be normalised away, and every normalisation is a place a real residue could hide. Each one is
declared below and kept as narrow as possible. A normaliser that erased the whole difference would
make this vacuous, so the run carries a positive control that must still be distinguishable.

    python erasure_indistinguishability.py --pkg <dir with prototype/>
"""
import argparse
import io
import json
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
RESULT = os.path.join(HERE, "erasure-indistinguishability.result.json")

#: Two secrets of IDENTICAL length. Equal length matters: a store that leaks only the LENGTH of what
#: it erased would otherwise be indistinguishable here for the wrong reason, and we would be
#: measuring our own fixture rather than the store.
SECRET_A = "the patient is HIV positive"
SECRET_B = "the patient is left-handed!"   # 27, matching A; it was 26 and unchecked
COLLATERAL = "prefers appointments in the morning"

#: A DERIVED record holding both. Its absence is why this file first reported our own store clean:
#: `forget()` removes the record it is given, not a summariser's verbatim copy of the same text, so a
#: two-record fixture is precisely the shape that passes. Measured: without it the secret is gone
#: from disk, with it the secret is still there. The fixture that flatters is not the fixture to use.
INCLUDE_DERIVED = True


def _normalise(blob, root):
    """Remove differences that CANNOT carry the secret, and nothing else.

    Each rule is a hole by construction, so each is stated:

      paths      the temp root differs per run by construction
      ids        content-addressed or random record ids differ per run; a store deriving an id FROM
                 the secret would be hidden by this, which is why the positive control below plants
                 the secret verbatim and must still be caught
      timestamps wall-clock differs per run
      digests    hex runs of 16+ chars: a chain hash over a differing record legitimately differs.
                 THIS IS THE WIDEST RULE AND THE MOST DANGEROUS: a store could hide a secret in a
                 hex field. It is kept because a hash-chained tombstone is exactly what a compliant
                 store writes, and without it every honest store fails.
    """
    text = blob.decode("utf-8", errors="replace")
    text = text.replace(root.replace("\\", "/"), "<ROOT>").replace(root, "<ROOT>")
    text = re.sub(r"\b[0-9a-f]{16,}\b", "<HEX>", text)
    text = re.sub(r"\d{4}-\d{2}-\d{2}T[\d:.]+Z?", "<TS>", text)
    text = re.sub(r"\b\d{10}\.\d+\b", "<EPOCH>", text)
    # Any *_id key, not only "id". `memory_id` in the tombstone differed between runs and read as
    # residue until it was checked: the same text stored twice yields DIFFERENT ids, so inspeximus
    # ids are random rather than content-addressed and the difference carries nothing. Had they been
    # content-addressed the tombstone would have carried a VERIFIER for the erased text -- a guesser
    # could confirm a guess by recomputing the id -- and normalising it away would have hidden that.
    # Which is exactly why the positive control below is not optional.
    text = re.sub(r'"[a-z_]*id"\s*:\s*"[^"]+"', '"<IDKEY>": "<ID>"', text)
    # mkdtemp names created by the store INSIDE our root
    text = re.sub(r"tmp[a-z0-9_]{6,}", "<TMPDIR>", text)
    text = re.sub(r'"(derived_from|links|supersedes|revert_of)"\s*:\s*\[[^\]]*\]',
                  r'"\1": [<IDS>]', text)
    return text


def _run_erasure(binding_cls, secret, plant=False):
    """Build a store holding `secret` + collateral, erase the secret, return the normalised state."""
    root = tempfile.mkdtemp(prefix="indist-")
    prior = tempfile.tempdir
    tempfile.tempdir = root
    try:
        binding = binding_cls()
        adapter, handle = binding.build([
            {"id": "secret", "text": secret, "root": "fact:secret"},
            {"id": "keep", "text": COLLATERAL, "root": "fact:keep"},
        ])
        if INCLUDE_DERIVED:
            handle.remember("%s; %s" % (secret, COLLATERAL), derived=True,
                            derived_from=[r["id"] for r in handle.items][:2])
        target = next(r["id"] for r in handle.items if r.get("key") == "secret")
        if plant:
            # POSITIVE CONTROL: a store that keeps the secret somewhere the normaliser does not
            # touch. If this is NOT caught, the normalisers have erased the signal and every clean
            # verdict above is meaningless.
            io.open(os.path.join(root, "kept.bin"), "wb").write(secret.encode("utf-8"))
        adapter.retire(target)
    finally:
        tempfile.tempdir = prior

    chunks = []
    for base, _dirs, names in os.walk(root):
        for n in sorted(names):
            fp = os.path.join(base, n)
            try:
                # The file NAME is normalised too. A store creating its own mkdtemp inside our root
                # gives each run a different directory name, which is not residue. A store that
                # named a file after the secret WOULD be, and the same rule would hide it -- which
                # is what the positive control exists to keep honest.
                rel = re.sub(r"tmp[a-z0-9_]{6,}", "<TMPDIR>",
                             os.path.relpath(fp, root).replace("\\", "/"))
                chunks.append("%s\n%s" % (rel, _normalise(io.open(fp, "rb").read(), root)))
            except OSError:
                pass
    return "\n=====\n".join(chunks)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkg", required=True)
    ap.add_argument("--binding", default=None)
    ap.add_argument("--inspeximus", default=r"C:/Users/Danculus/inspeximus-repo")
    a = ap.parse_args(argv)
    sys.path.insert(0, a.pkg)
    sys.path.insert(0, a.inspeximus)
    sys.path.insert(0, HERE)

    if a.binding:
        import importlib
        mod, cls = a.binding.split(":")
        binding_cls = getattr(importlib.import_module(mod), cls)
    else:
        from run_adapter_conformance import InspeximusBinding as binding_cls

    print("Erasure indistinguishability -- binding: %s\n" % binding_cls.__name__)

    state_a = _run_erasure(binding_cls, SECRET_A)
    state_b = _run_erasure(binding_cls, SECRET_B)
    indistinguishable = state_a == state_b

    # THE POSITIVE CONTROL. Planting the secret verbatim must make the two runs differ. If it does
    # not, the normalisers have flattened the very signal this test reads, and a clean verdict means
    # nothing. This runs every time, not as an option.
    ctl_a = _run_erasure(binding_cls, SECRET_A, plant=True)
    ctl_b = _run_erasure(binding_cls, SECRET_B, plant=True)
    control_fires = ctl_a != ctl_b

    diff = []
    if not indistinguishable:
        la, lb = state_a.split("\n"), state_b.split("\n")
        for i, (x, y) in enumerate(zip(la, lb)):
            if x != y:
                diff.append({"line": i, "erasing_A": x[:160], "erasing_B": y[:160]})
            if len(diff) >= 8:
                break
        if len(la) != len(lb):
            diff.append({"line": "count", "erasing_A": len(la), "erasing_B": len(lb)})

    print("  states after erasing two different secrets : %s"
          % ("IDENTICAL" if indistinguishable else "DIFFER"))
    print("  positive control (secret planted verbatim) : %s"
          % ("caught" if control_fires else "NOT CAUGHT"))
    if diff:
        print("\n  residue -- the state depends on what was erased:")
        for d in diff[:6]:
            print("    line %s" % d["line"])
            print("      A: %s" % d["erasing_A"])
            print("      B: %s" % d["erasing_B"])

    out = {"indistinguishable": indistinguishable, "control_fires": control_fires,
           "binding": binding_cls.__name__, "residue_sample": diff}
    io.open(RESULT, "w", encoding="utf-8", newline="\n").write(json.dumps(out, indent=2) + "\n")
    print("\nwrote %s" % os.path.basename(RESULT))

    if not control_fires:
        print("\nVERDICT: UNUSABLE. The normalisers flatten a verbatim planted secret, so a clean "
              "result here would mean nothing.")
        return 2
    if not indistinguishable:
        print("\nVERDICT: RESIDUE. What remains after erasure is a function of what was erased.")
        return 1
    print("\nVERDICT: INDISTINGUISHABLE UNDER THESE NORMALISERS. That is not a proof of erasure.")
    print("  An independent pass defeated this twelve ways, two of them storing the secret as")
    print("  unencoded PLAINTEXT in a field a normaliser rewrites. Treat a clean result as a smoke")
    print("  test that the store is not lazily broken, which is what it caught in our own adapter.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
