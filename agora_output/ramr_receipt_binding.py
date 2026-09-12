#!/usr/bin/env python3
"""Receipt binding — the one integrity cell that needs no assertion channel and no ranking.

WHY THIS CELL EXISTS. The other cells in this folder assume a store of asserted facts: they correct a
value, then try to undo or resurrect it. A store that only records what it OBSERVED — a read ledger, an
audit trail, a provenance log — has no `add`, no `revert` and no "current value of a fact", so those
cells are unsatisfiable rather than failed (@Stratogain, DanceNitra/ramr#1). Ranking is a separate
exclusion: where lookup is by exact key there is no top-1 for an echo to retake.

What such a store CAN answer is the question @safal207 stated as a contract on DanceNitra/ramr#2:

    receipt = bind(answer, observed_source_ids + digests)
    verify_receipt(receipt) -> VALID | STALE

with STALE meaning **the consumer must not silently treat the original answer as freshly evidenced** —
and, explicitly, `verify_receipt` must NOT decide whether the old answer is still semantically correct.
It answers the narrower question: is this answer still backed by the same evidence it was bound to?

That contract needs `observe`, `answer_with_receipt`, `verify_receipt` and nothing else. Provenance
ledgers, audit logs, content-addressed caches and assertion-based memory systems can all satisfy it
without being forced into one storage model.

THE SCENARIOS ARE THE CONTROLS. A receipt checker that always says STALE is not a checker; one that
fires on any change anywhere is not *binding* but alarming; and one that binds nothing at all
reassures. Five scenarios have a required answer, and a backend earns the row only by getting all
five right:

    S1  nothing changes                          -> VALID    (it can say VALID at all)
    S2  a source the answer was BOUND to changes -> STALE    (it detects what it exists to detect)
    S3  a source it was NOT bound to changes     -> VALID    (bound, not merely alarmed)
    S4  a bound source is rewritten to different
        bytes with the same meaning              -> STALE    (evidence-bound, not meaning-bound)
    S6  the answer cites a source that was
        never observed                           -> NOT VALID (a receipt over nothing is not a pass)

S3 and S6 are the two discriminating ones and they are mirrors. S3 catches a receipt bound to MORE
than the answer used; S6 catches one bound to LESS, down to nothing. Only the first made a scenario
fail before @Stratogain reported the second (DanceNitra/ramr#3) against the row built for his own
store — an answer citing an unobserved file produced `{"sources": {}}` and verified VALID off an
empty loop. S4 is @safal207's boundary made executable: a checker returning VALID there has started
judging semantics, which the contract forbids.

S6 is also the fail-closed rule of inspeximus 2.19.0 one level down. There, an artifact that
declares no scope is sufficient for nothing. Here, a receipt that binds nothing is sufficient for
nothing. The same statement about the same object at two granularities, and we shipped the first
while leaving the second open.

    S5  a bound source changes and then RETURNS
        to its original bytes                    -> required PER PROFILE, and that is the point

S5 is where the two contributions meet. On an append-only read ledger of 862 paths over 2,443
records, 288 paths changed content and none returned to a previous digest; asked whether the return
was even available, 194 of those 288 sit under git control, and 35 live in temp directories where it
cannot happen at all. So the zero describes a working pattern rather than a property of files.
Under `content_continuity` the return is VALID -- the bytes the answer was bound to are the bytes
there now. Under `transition_continuity` it is STALE. Same ledger, same event, opposite verdicts,
which is why `verifies` has to travel in the receipt. The stronger profile needs one extra field,
`generation`, and an append-only ledger has it for free: **a repeated old digest in the source is a
new observation of previous bytes; a revert command in a store is an operation on an assertion.**

HONEST SCOPE. Minimal fixture, real files on disk as the sources, one query. It tells you whether the
failure mode is POSSIBLE in your stack, not how often it happens. A backend reporting `unsupported` is
making a statement about its interface, not failing: an audit log with no receipt primitive cannot be
graded on one, and inventing an adapter for it would grade the invention.

Usage:  python receipt_binding.py                # auto-detect
        python receipt_binding.py ledger inspeximus
"""
import hashlib
import json
import os
import sys
import tempfile
import time

BOUND = "runbook.md"
UNBOUND = "changelog.md"
BOUND_V1 = b"The staging database host is db-old.internal\n"
BOUND_V2 = b"The staging database host is db-new.internal\n"
BOUND_SEMANTIC_NOOP = b"The staging  database   host is db-old.internal\n"   # same meaning, new bytes
UNBOUND_V2 = b"Unrelated: bumped the linter to 4.2\n"
QUERY = "what is the staging database host?"

CHECKS = {}


def _mkroot():
    d = tempfile.mkdtemp()
    for name, body in ((BOUND, BOUND_V1), (UNBOUND, b"Unrelated: initial changelog\n")):
        with open(os.path.join(d, name), "wb") as f:
            f.write(body)
    return d


def _write(root, name, body):
    with open(os.path.join(root, name), "wb") as f:
        f.write(body)


# --------------------------------------------------------------------------------------------------
# Backend 1: a minimal append-only observation ledger -- @Stratogain's class, ~25 lines.
# It has no add(), no revert(), no ranking and no "current value of a fact". It satisfies the contract
# anyway, which is the point of the cell.
# --------------------------------------------------------------------------------------------------
class Ledger:
    """`profile` selects which predicate this store's receipts claim to support. Nothing about the
    STORAGE changes between the two -- the generation is the count of observations already recorded
    for that source, which an append-only ledger has for free."""

    def __init__(self, root, profile="content_continuity"):
        self.root, self.records, self.profile = root, [], profile

    def observe(self, source_id):
        raw = open(os.path.join(self.root, source_id), "rb").read()
        self.records.append({"source_id": source_id, "digest": hashlib.sha256(raw).hexdigest(),
                             "seq": len(self.records)})

    def _generation(self, sid):
        return sum(1 for r in self.records if r["source_id"] == sid)

    def answer_with_receipt(self, source_ids):
        """The answer is 'what these files said when last read'. The receipt binds it to exactly
        those, and -- under the stronger profile -- to how many times they had been read by then."""
        # NAME WHAT WAS NOT SEEN. The first version dropped an unobserved source silently, so an
        # answer citing a file the ledger had never read produced `{"sources": {}}` and verified
        # VALID off an empty loop -- @Stratogain, DanceNitra/ramr#3. It is `_unscoped` in the
        # mirror: that one binds MORE than the answer used and alarms, this one binds LESS, down to
        # nothing, and reassures. Both are the same sentence -- a check that never reaches its
        # target reports something reassuring -- and only the alarming one made a scenario fail.
        #
        # It is also the fail-closed rule of inspeximus 2.19.0 one level down: an artifact that
        # declares no scope is sufficient for nothing, so a receipt that binds nothing is
        # sufficient for nothing. We built that rule for the artifact and left the receipt open.
        #
        # Raising would be the other fix and discards information the consumer wants. The unbound
        # ids travel in the receipt instead.
        want = set(PROFILES[self.profile]["scope"])
        pinned, unobserved = {}, []
        for sid in source_ids:
            seen = [r for r in self.records if r["source_id"] == sid]
            if not seen:
                unobserved.append(sid)
                continue
            entry = {"digest": seen[-1]["digest"]}
            if "generation" in want:
                entry["generation"] = self._generation(sid)
            pinned[sid] = entry
        return ("what the runbook said when last read",
                {"sources": pinned, "unobserved": unobserved,
                 "commitment_scope": PROFILES[self.profile]["scope"],
                 "verifies": PROFILES[self.profile]["verifies"], "profile": self.profile})

    def verify_receipt(self, receipt):
        # A receipt that binds nothing, or that omits a source the answer cited, cannot support the
        # predicate it declares. Checked BEFORE the loop, because an empty loop returns VALID and
        # that is the whole defect.
        if receipt.get("unobserved") or not receipt.get("sources"):
            # verifying is a read, and an append-only ledger records its reads even when the
            # verdict is a refusal -- otherwise the store cannot show that a check happened.
            self.records.append({"source_id": "__verify__", "digest": "unsupported",
                                 "seq": len(self.records)})
            return "UNSUPPORTED"
        for sid, pin in receipt["sources"].items():
            raw = open(os.path.join(self.root, sid), "rb").read()
            now = hashlib.sha256(raw).hexdigest()
            # re-observe, because verifying IS a read and an append-only ledger records its reads
            self.records.append({"source_id": sid, "digest": now, "seq": len(self.records)})
            if now != pin["digest"]:
                return "STALE"
            if "generation" in pin and self._generation(sid) - 1 != pin["generation"]:
                # same bytes, but the ledger saw the source move in between: content continuity
                # holds and transition continuity does not. Same event, opposite verdicts.
                return "STALE"
        return "VALID"


def _ledger(profile):
    return lambda: _run(lambda root: Ledger(root, profile),
                        observe=lambda b, sid: b.observe(sid),
                        answer=lambda b, sids: b.answer_with_receipt(sids),
                        verify=lambda b, r: b.verify_receipt(r))


CHECKS["ledger"] = _ledger("content_continuity")
CHECKS["ledger+gen"] = _ledger("transition_continuity")


# --------------------------------------------------------------------------------------------------
# Backend 2: inspeximus. witness(bind_sources=True) / verify_witness() were built from @safal207's own
# OBSERVE->BIND->CAPTURE->VERIFY->USE framing, so this is a check of whether the implementation matches
# the contract its framing produced -- not an independent invention of it.
# --------------------------------------------------------------------------------------------------
def check_inspeximus():
    from inspeximus import Inspeximus

    class Adapter:
        def __init__(self, root):
            self.root, self.ids = root, {}
            self.m = Inspeximus(path=os.path.join(tempfile.mkdtemp(), "s.json"))

        def observe(self, sid):
            path = os.path.join(self.root, sid)
            body = open(path, "rb").read().decode("utf-8", "replace").strip()
            # NOTE for readers: inspeximus's own `observe()` is a DIFFERENT primitive -- a
            # read-path contradiction check -- and passing the source through `meta` leaves
            # `bind_sources` with nothing to re-read, so this cell reported "no receipt
            # primitive" for a store that has one. The source must be the top-level `source`
            # field, which is what check_sources/bind_sources actually read.
            self.ids[sid] = self.m.remember(body, key=sid, source={"doc": path})

        def answer_with_receipt(self, sids):
            # SCOPE THE RECEIPT TO THE RECORDS THE ANSWER CAME FROM. The bare
            # `witness(bind_sources=True)` pins EVERY source in the store, which answers
            # "did anything in my world move" rather than "is this answer still evidenced" --
            # and a receipt that fires on an unrelated file is not binding, it is alarming.
            # This cost this cell two wrong verdicts before it was noticed: first
            # "no receipt primitive" (source passed through meta), then a failed S3.
            want = {self.ids[sid] for sid in sids if sid in self.ids}
            hits = [h for h in (self.m.recall(QUERY, k=50) or []) if h.get("id") in want]
            missing = [sid for sid in sids if sid not in self.ids]
            if missing or not hits:
                # Never fall back to a store-wide witness -- that is the defect the scoping exists
                # to avoid -- and never mint a receipt over sources this store has no record of.
                return ("what the runbook said when last read",
                        {"unobserved": missing or list(sids), "_refuse": True})
            w = self.m.witness(records=hits, bind_sources=True)
            w["unobserved"] = []
            return "what the runbook said when last read", w

        def verify_receipt(self, w):
            if w.get("_refuse") or w.get("unobserved"):
                return "UNSUPPORTED"
            v = self.m.verify_witness(w)
            # The two answers are kept separate on purpose: digest_match is about the STORE,
            # sources_match is about the WORLD. This cell asks only the second question, so a
            # backend must not be marked STALE because its own store moved.
            sm = v.get("sources_match")
            if sm is None:
                return "UNSUPPORTED"
            return "VALID" if sm else "STALE"

    return _run(Adapter, observe=lambda b, sid: b.observe(sid),
                answer=lambda b, sids: b.answer_with_receipt(sids),
                verify=lambda b, r: b.verify_receipt(r))
CHECKS["inspeximus"] = check_inspeximus


# --------------------------------------------------------------------------------------------------
# Backend 3: a store with no receipt primitive. It must report unsupported -- never VALID. A store that
# answers VALID because it has nothing to check with is the failure this cell is really about.
# --------------------------------------------------------------------------------------------------
def check_noreceipt():
    class Adapter:
        def __init__(self, root):
            self.root, self.texts = root, []

        def observe(self, sid):
            self.texts.append(open(os.path.join(self.root, sid), "rb").read())

        def answer_with_receipt(self, sids):
            return "what the runbook said when last read", None      # no receipt exists

        def verify_receipt(self, r):
            return "UNSUPPORTED"

    return _run(Adapter, observe=lambda b, sid: b.observe(sid),
                answer=lambda b, sids: b.answer_with_receipt(sids),
                verify=lambda b, r: b.verify_receipt(r))
CHECKS["noreceipt"] = check_noreceipt


# --------------------------------------------------------------------------------------------------
# ADVERSARIAL CONTROLS. A cell whose every row passes has not shown that it can fail. These three are
# wrong in three different ways, and each must be caught by a DIFFERENT scenario.
# --------------------------------------------------------------------------------------------------
def _constant(verdict):
    class Adapter:
        def __init__(self, root):
            self.root = root

        def observe(self, sid):
            pass

        def answer_with_receipt(self, sids):
            return "", {}

        def verify_receipt(self, r):
            return verdict
    return lambda: _run(Adapter, observe=lambda b, s: b.observe(s),
                        answer=lambda b, s: b.answer_with_receipt(s),
                        verify=lambda b, r: b.verify_receipt(r))


CHECKS["_always_valid"] = _constant("VALID")     # must fail S2 and S4, and only those
CHECKS["_always_stale"] = _constant("STALE")     # must fail S1 and S3, and only those


def check_underbound():
    """@Stratogain's control, and the mirror of `_unscoped`. This is the ledger EXACTLY as it was
    written before his review: it pins the sources it happens to have observed and drops the rest
    without saying so, so an answer citing an unobserved file yields an empty receipt that verifies
    VALID off a loop with nothing in it. It passes S1-S5 identically to `ledger` and fails S6 alone,
    which is what makes it a control rather than a straw backend -- the shipped row had this hole."""
    class Adapter(Ledger):
        def answer_with_receipt(self, source_ids):
            pinned = {}
            for sid in source_ids:
                seen = [r for r in self.records if r["source_id"] == sid]
                if seen:
                    pinned[sid] = {"digest": seen[-1]["digest"]}
            return "", {"sources": pinned, "commitment_scope": PROFILES[self.profile]["scope"],
                        "verifies": PROFILES[self.profile]["verifies"], "profile": self.profile}

        def verify_receipt(self, receipt):
            for sid, pin in receipt["sources"].items():
                raw = open(os.path.join(self.root, sid), "rb").read()
                if hashlib.sha256(raw).hexdigest() != pin["digest"]:
                    return "STALE"
            return "VALID"
    return _run(lambda root: Adapter(root, "content_continuity"),
                observe=lambda b, s: b.observe(s),
                answer=lambda b, s: b.answer_with_receipt(s),
                verify=lambda b, r: b.verify_receipt(r))
CHECKS["_underbound"] = check_underbound       # must fail S6 and ONLY S6


def check_unscoped():
    """The trap, checked in rather than remembered: a receipt bound to EVERY source in the store
    instead of the ones the answer came from. It looks right on S1, S2 and S4 and is wrong about what
    it measures -- "did anything in my world move" is not "is this answer still evidenced". Both of the
    inspeximus adapter's first two attempts landed here, so it stays as a permanent control."""
    class Adapter:
        def __init__(self, root):
            self.root, self.pinned = root, {}

        def observe(self, sid):
            raw = open(os.path.join(self.root, sid), "rb").read()
            self.pinned[sid] = hashlib.sha256(raw).hexdigest()

        def answer_with_receipt(self, sids):
            return "", {"sources": dict(self.pinned)}          # every source, not just `sids`

        def verify_receipt(self, r):
            for sid, dig in r["sources"].items():
                if hashlib.sha256(open(os.path.join(self.root, sid), "rb").read()).hexdigest() != dig:
                    return "STALE"
            return "VALID"
    return _run(Adapter, observe=lambda b, s: b.observe(s),
                answer=lambda b, s: b.answer_with_receipt(s),
                verify=lambda b, r: b.verify_receipt(r))
CHECKS["_unscoped"] = check_unscoped              # must fail S3 and ONLY S3


def _run(make, observe, answer, verify):
    """One backend through all five scenarios. Each scenario gets a FRESH root and a fresh backend, so
    no scenario can inherit another's state -- a shared root is how S3 quietly becomes S2."""
    out = {}
    for name, mutate in (
        ("S1_no_change", lambda root: None),
        ("S2_bound_changed", lambda root: _write(root, BOUND, BOUND_V2)),
        ("S3_unbound_changed", lambda root: _write(root, UNBOUND, UNBOUND_V2)),
        ("S4_semantic_noop", lambda root: _write(root, BOUND, BOUND_SEMANTIC_NOOP)),
        # S5 hands the backend to the mutation, because a read ledger only knows what it READ.
        # The first version wrote B then A with nobody looking in between, and every backend
        # correctly said VALID -- there was no transition to detect, only a file that ends where it
        # started. That is the fixture failing to instantiate its own case, not the store missing
        # it. A tool reads the file while it is B, which is exactly the world @Stratogain measured:
        # 226 of 634 paths changed BECAUSE the same path is re-read over months.
        ("S5_returned_to_original", lambda root, b: (_write(root, BOUND, BOUND_V2),
                                                     observe(b, BOUND),
                                                     _write(root, BOUND, BOUND_V1))),
        # S6 is @Stratogain's, and it is the mirror of S3. S3 catches a receipt bound to MORE than
        # the answer used, which alarms. S6 catches one bound to LESS -- down to nothing -- which
        # reassures, and nothing in S1-S5 could reach it because every scenario observed every
        # source before answering. On his store this is the ordinary case rather than the edge:
        # the witness sits on 33.4% of tool calls, so an answer routinely cites files it never saw.
        ("S6_cites_an_unobserved_source", lambda root: None),
    ):
        root = _mkroot()
        b = make(root)
        observe(b, BOUND)
        observe(b, UNBOUND)
        if name == "S6_cites_an_unobserved_source":
            _write(root, "never_read.md", b"A file the witness never saw\n")
            _, receipt = answer(b, [BOUND, "never_read.md"])
        else:
            _, receipt = answer(b, [BOUND])    # bound to the runbook ONLY
        try:
            mutate(root, b)
        except TypeError:
            mutate(root)
        out[name] = verify(b, receipt)
    return out


# TWO PROFILES, and S5 is the whole reason they have to be declared rather than inferred.
# @Stratogain's framing on anthropics/claude-code#34556: making S5 required would silently change
# the predicate from CONTENT continuity to TRANSITION continuity, and those need different fields.
# The two are indistinguishable from outside while returning opposite verdicts on the same event,
# which is precisely why `verifies` has to be in the artifact.
#
# And his observation that makes the stronger profile cheap: an append-only ledger ALREADY has the
# generation, because append order IS the generation. It is one more field in the receipt, not a
# different storage model. Measured below rather than granted -- the `ledger` adapter derives its
# generation from the record index it already keeps.
# `verifies` IS A LIST HERE TOO. @Stratogain caught the asymmetry on anthropics/claude-code#34556:
# inspeximus's `identifier_contract()` declares `verifies` as a list while this receipt declared it
# as a string (the profile name), so a consumer holding both had to branch on TYPE to read one field
# name. Defensible as stated -- a receipt is minted under one profile, an artifact can serve several
# -- but the branch costs the consumer and a one-element list costs nothing. The profile name moved
# to its own field rather than being smuggled through `verifies`, which was the deeper version of
# the same complaint: one field carrying two kinds of thing.
PROFILES = {
    "content_continuity":    {"scope": ["source_id", "digest"],
                              "verifies": ["answer_still_evidenced"],
                              "means": "the answer is still backed by the same bytes",
                              "S5": "VALID"},
    "transition_continuity": {"scope": ["source_id", "digest", "generation"],
                              "verifies": ["answer_still_evidenced", "source_never_moved"],
                              "means": "and the source has not moved since the answer was bound",
                              "S5": "STALE"},
}

REQUIRED = {"S1_no_change": "VALID", "S2_bound_changed": "STALE",
            "S3_unbound_changed": "VALID", "S4_semantic_noop": "STALE"}
# S6 has no single right answer, only a wrong one: a silent pass. STALE or UNSUPPORTED both say
# "do not treat this as freshly evidenced", which is the whole contract.
NOT_ALLOWED = {"S6_cites_an_unobserved_source": "VALID"}


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    names = [a for a in argv[1:] if a in CHECKS] or list(CHECKS)
    rows = {}
    for n in names:
        try:
            rows[n] = CHECKS[n]()
        except ImportError:
            rows[n] = {"skipped": "not installed"}
        except Exception as e:
            rows[n] = {"error": f"{type(e).__name__}: {e}"[:200]}

    hdr = ["S1_no_change", "S2_bound_changed", "S3_unbound_changed", "S4_semantic_noop",
           "S5_returned_to_original", "S6_cites_an_unobserved_source"]
    regressed = []
    print(f"{'backend':12} " + " ".join(f"{h.split('_',1)[0]:>6}" for h in hdr) + "   honours the contract?")
    for n, r in rows.items():
        if "skipped" in r or "error" in r:
            print(f"{n:12} {r.get('skipped') or r.get('error')}")
            continue
        ok = (all(r.get(k) == v for k, v in REQUIRED.items())
              and all(r.get(k) != v for k, v in NOT_ALLOWED.items()))
        unsup = all(v == "UNSUPPORTED" for v in r.values())
        verdict = ("no receipt primitive (correctly declined)" if unsup
                   else ("yes" if ok else "NO -- " + ", ".join(
                       [f"{k.split('_',1)[0]} said {r.get(k)}, wants {v}"
                        for k, v in REQUIRED.items() if r.get(k) != v]
                       + [f"{k.split('_',1)[0]} said {v}, which is a silent pass"
                          for k, v in NOT_ALLOWED.items() if r.get(k) == v])))
        # ASSERT the honest rows, do not merely print them. A live mutation that reverted the S6
        # fix left every control green and the run exiting 0, because only the underscore backends
        # were ever checked -- the regression showed up as the word "NO" in a table nobody diffs.
        if not n.startswith("_") and not unsup and not ok:
            regressed.append(f"{n}: {verdict}")
        print(f"{n:12} " + " ".join(f"{str(r.get(h))[:6]:>6}" for h in hdr) + f"   {verdict}")

    # The controls are ASSERTED, not merely displayed. A cell that prints a failing control and exits 0
    # has reported nothing. Each adversarial backend must be caught by its OWN scenario -- if two of
    # them fail on the same one, the other scenarios are not doing any work.
    # What each mutant ACTUALLY breaks, not what would be tidy. Adding S6 made two of them fail a
    # second scenario, and both are true: `_always_valid` says VALID to everything by construction,
    # and `_unscoped` carries the under-binding hole as well because it never names an unobserved
    # source either. The property that matters survives -- `_underbound` fails S6 and NOTHING else,
    # which is what separates it from `_unscoped`, exactly as S3 separates `_unscoped` from the
    # honest ledger.
    ctl = {"_always_valid": {"S2_bound_changed", "S4_semantic_noop",
                             "S6_cites_an_unobserved_source"},
           "_always_stale": {"S1_no_change", "S3_unbound_changed"},
           "_unscoped": {"S3_unbound_changed", "S6_cites_an_unobserved_source"},
           "_underbound": {"S6_cites_an_unobserved_source"}}
    bad = []
    for name, expect_fail in ctl.items():
        r = rows.get(name)
        if not isinstance(r, dict) or "error" in r or "skipped" in r:
            bad.append(f"{name}: did not run")
            continue
        got = ({k for k, v in REQUIRED.items() if r.get(k) != v}
               | {k for k, v in NOT_ALLOWED.items() if r.get(k) == v})
        if got != expect_fail:
            bad.append(f"{name} fails {sorted(got) or ['nothing']}, must fail exactly {sorted(expect_fail)}")
    # S5 IS NOW REQUIRED -- per profile. It stopped being an open question the moment the predicate
    # was declared: under content continuity the return IS valid, under transition continuity it is
    # not, and the same store gives both. If the two ever agree, the `generation` field has stopped
    # doing anything and the declaration has become decoration.
    # SOURCE IDENTITY, because source_id IS the identity in this contract and a fold on it merges
    # two files into one receipt entry. @Stratogain: his path fold is toLowerCase(), correct on
    # Windows and wrong on Linux the moment the same ledger runs there. SloNN reported the Unicode
    # half at basicmachines-co/basic-memory#1275 -- NFC and NFD forms of one visible filename
    # minting two entities, or one where there should be two. Tested on the NFC/NFD pair because
    # both forms can coexist on disk, where two case variants cannot on Windows.
    import unicodedata
    idroot = _mkroot()
    nfc = unicodedata.normalize("NFC", "café.md")
    nfd = unicodedata.normalize("NFD", "café.md")
    ident, demo = [], False
    if nfc != nfd:
        _write(idroot, nfc, b"one\n")
        _write(idroot, nfd, b"two\n")
        lg2 = Ledger(idroot)
        try:
            lg2.observe(nfc)
            lg2.observe(nfd)
            _, rc = lg2.answer_with_receipt([nfc, nfd])
            # (1) a DEFECT if it fires: this cell must never fold a source id.
            if len(rc["sources"]) != 2:
                ident.append(f"two distinct source ids collapsed to {len(rc['sources'])}")
            # (2) a DEMONSTRATION, not a defect: an adapter that normalises WOULD merge these two,
            # so the trap is real for every adapter rather than hypothetical. Reported separately,
            # because printing it as a failure makes a true statement look like our bug.
            demo = len({unicodedata.normalize("NFC", k) for k in rc["sources"]}) == 1
        except OSError:
            demo = False
            ident.append("SKIPPED: this filesystem will not hold both forms")
    print("\nidentity: "
          + ("the cell keeps two distinct source ids distinct" if not ident
             else "BROKEN -- " + "; ".join(ident))
          + ("   (an NFC-normalising adapter would merge exactly these two: "
             "basicmachines-co/basic-memory#1275, reported by SloNN)" if demo else ""))

    # TYPE CONSISTENCY, checked rather than agreed. The asymmetry @Stratogain found existed because
    # two artifacts used one field name for two shapes and nothing objected. "Pick one and write it
    # down" only survives if something fails when it drifts back.
    shape = []
    for name, prof in PROFILES.items():
        for field in ("scope", "verifies"):
            if not isinstance(prof.get(field), list) or not prof[field]:
                shape.append(f"PROFILES[{name}][{field}] is {type(prof.get(field)).__name__}, "
                             f"must be a non-empty list")
    probe_root = _mkroot()
    lg = Ledger(probe_root, "content_continuity")
    lg.observe(BOUND)
    _, rcpt = lg.answer_with_receipt([BOUND])
    for field in ("commitment_scope", "verifies"):
        if not isinstance(rcpt.get(field), list):
            shape.append(f"a minted receipt's `{field}` is {type(rcpt.get(field)).__name__}, "
                         f"must be a list -- a consumer should never branch on type to read a field")
    if not isinstance(rcpt.get("profile"), str):
        shape.append("the profile name must travel in its own field, not inside `verifies`")
    print("\nshape: " + ("`commitment_scope` and `verifies` are lists on every artifact, and the "
                          "profile name has its own field" if not shape
                          else "BROKEN -- " + "; ".join(shape)))

    bad_profiles = list(shape)
    a, b_ = rows.get("ledger"), rows.get("ledger+gen")
    if isinstance(a, dict) and isinstance(b_, dict) and "error" not in a and "error" not in b_:
        for name, r in (("content_continuity", a), ("transition_continuity", b_)):
            want = PROFILES[name]["S5"]
            if r.get("S5_returned_to_original") != want:
                bad_profiles.append(f"{name} S5 = {r.get('S5_returned_to_original')}, wants {want}")
        if a.get("S5_returned_to_original") == b_.get("S5_returned_to_original"):
            bad_profiles.append("the two profiles AGREE on S5 -- `generation` is doing nothing")
        for k in ("S1_no_change", "S2_bound_changed", "S3_unbound_changed", "S4_semantic_noop"):
            if a.get(k) != b_.get(k):
                bad_profiles.append(f"the profiles differ on {k}; they must differ ONLY on S5")
    else:
        bad_profiles.append("one of the two profiles did not run")
    print("\nprofiles: " + ("the same store returns opposite S5 verdicts under the two declared "
                            "predicates and agrees everywhere else -- which is why `verifies` has "
                            "to be in the receipt" if not bad_profiles
                            else "BROKEN -- " + "; ".join(bad_profiles)))

    print("\nbackends: " + ("every non-adversarial backend honours the contract"
                            if not regressed else "REGRESSED -- " + "; ".join(regressed)))

    print("\ncontrols: " + ("all three adversarial backends fail exactly the scenario they should"
                            if not bad else "BROKEN -- " + "; ".join(bad)))

    print("\nS1-S4 are required of every backend. S5 is required PER PROFILE, and it is the reason")
    print("the profiles exist: the same ledger returns VALID under content continuity and STALE")
    print("under transition continuity for the same event. Making S5 universally required would")
    print("silently change which predicate the cell tests -- and the field it needs is `generation`,")
    print("which an append-only ledger already has, because append order IS the generation. One")
    print("extra field in the receipt, not a different storage model.")
    print("A repeated old digest is a new observation of previous bytes; a revert command in a store")
    print("is an operation on an assertion. The cell now tells them apart instead of declining to.")

    out = {"fixture": "receipt_binding", "bound_source": BOUND, "unbound_source": UNBOUND,
           "query": QUERY, "required": REQUIRED,
           "iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "rows": rows}
    d = os.path.join(os.path.dirname(__file__) or ".", "results")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "receipt_binding.json")
    json.dump(out, open(p, "w", encoding="utf-8"), indent=2)
    print(f"\nreceipt -> {p}")
    return 0 if not (bad or bad_profiles or regressed or ident) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
