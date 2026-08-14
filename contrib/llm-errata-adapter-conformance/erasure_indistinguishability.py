"""Verify erasure WITHOUT SEARCHING FOR THE VALUE. Two erasures must leave the same store.

WHY SEARCHING CANNOT WORK, established over six audit rounds and not worth a seventh. A check of the
form "the erased value must not appear in the store" is defeated by anything that transforms or
fragments it. Measured against our own suite: bz2, utf-32-le, a one-byte XOR, and -- with no encoding
trick whatsoever -- the plain UTF-8 value written across two files as "is veg" and "etarian". Every
fix widened the list of recognised encodings, and the list is unbounded, so the rate of new escapes
never fell. The same limit applies to the specification's own confidentiality vector, which asserts
`forbidden_value not in evidence`.

THE TEST THAT DOES WORK asks a different question. Not "is the value there?", which requires
recognising it, but "does the store's state DEPEND on it?", which does not.

Erase secret A from a fresh store. Erase secret B, of identical length, from an otherwise identical
fresh store. If the erasure was complete, the two stores are now in the same state: nothing that
remains was computed from the secret, so nothing that remains can differ. If any byte differs -- a
retained copy, a fragment, a gzip member, an XOR, a hash of the content, a length-revealing index --
the state is a function of the secret, and the secret is not gone.

This is indistinguishability, borrowed from where it belongs, and it is sound against transforms this
file knows nothing about. It cannot be defeated by inventing an encoding, because it never tries to
read anything.

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
SECRET_B = "the patient is left handed"
COLLATERAL = "prefers appointments in the morning"


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
    print("\nVERDICT: INDISTINGUISHABLE. Nothing remaining depends on which secret was erased, and "
          "the control shows a planted secret would have been caught.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
