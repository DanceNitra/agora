# Candidate adapter-conformance cases for LLM Errata

**Status: CANDIDATE. Proposed to [thomaswillner/llm-errata](https://github.com/thomaswillner/llm-errata), not accepted.**
Being proposed, or merged, does not make any output here G2 or G4 evidence.

**Authored by an interested party.** inspeximus wrote these cases and is itself a G4 adapter candidate.
A separate producer must validate both implementations *and* this fixture. Nothing here is independent
evidence about inspeximus.

Target: commit `ac4468faf73c2cc7949dd29b2a2a151f5bd23116`, canonical surface digest
`7e0d6c88c1ca3a87743ac70ba2a3dfea0b350d112d2d3c59a3c6cbb537568f12`.

## Why these exist

Measured under `sys.settrace` against the published vectors at that commit
(`probes/errata_conformance_ac4468f.py` in this repository): **28 of 28 cases pass, and 1 of 28 reaches
a store adapter at all.** The published vectors grade the wire schema, the feed authenticator, the
receipt signer and the semantic aggregator, and they grade them hard. They were never intended to grade
adapter behaviour: `spec/README.md` is titled *The LLM Errata wire schema*.

So a clean-room adapter author can score 28/28 and have measured almost nothing about the thing they
wrote. These cases are the missing half.

## What is in here

| File | What it is |
|---|---|
| `adapter-conformance.json` | Five adapter behaviour cases and three validator anti-vacuity cases. |
| `run_adapter_conformance.py` | The runner. Enforces three rules on the fixture itself, below. |
| `adapter-conformance.result.json` | Raw output of the last run. |

The five adapter cases: an undeclared derivative must not reach `verified`; complete lineage must reach
`verified`; a repair must not assert the same proposition twice; erasure evidence must be content-free
*and* non-trivial; collateral must survive a supersession.

The second case is there because of the first. An adapter hard-wired to answer `unknown` passes every
honesty case ever written while being useless, so a suite without the positive twin rewards permanent
pessimism exactly as much as honesty.

## Three rules the runner enforces on its own fixture

Each comes from a defect we shipped or nearly shipped while building this.

1. **No expectation without a citation.** A case missing a `normative` block is refused, not scored. Our
   first conformance harness derived expected verdicts by splitting case names on a hyphen, so
   `provider-error` expected `"provider"`. It produced five false failures against the specification's
   own fixtures and was one step from reporting them upstream.
2. **No case without a positive control.** Each case declares the adapter methods it must reach, and the
   run traces whether it reached them. A case that never touches the surface it claims to test passes
   for the wrong reason.
3. **No fixture that has never failed.** Each case names a flattering implementation; the runner installs
   it and the case must fail. Two mutations in this suite silently no-opped when first written, and rule
   3 is the only reason that was caught rather than shipped.

Every mutation goes through the protocol surface or the binding, never through private attributes. The
first version reached for `adapter._store`, which does not exist, and an `except` swallowed the error:
a mutation aimed at a private name no-ops for every implementation except the one it was written
against, which would hand a third party a suite whose controls quietly stop working on their store.

## Running it against your own store

Implement one class:

```python
class YourBinding:
    name = "your-store"

    def build(self, records):
        """records -> (your StoreAdapter, a handle you understand)"""

    def active_texts(self, handle):
        """-> list[str] of the propositions currently asserted"""
```

Then:

```bash
python run_adapter_conformance.py --pkg <dir containing prototype/> --binding your.module:YourBinding
```

Nothing above `InspeximusBinding` in the runner names inspeximus. **If a case can only be satisfied by
reading that class, the case is coupled to our implementation and should be refused.**

## Last run

`3/4` adapter cases for the inspeximus binding.

`collateral-must-survive-a-supersession` FAILS, and the cause is neither adapter. `RebuildStrategy`
introduces the replacement only through `rebuild()` of a mixed descendant, so a superseded root with no
mixed descendant is retired while the correction is never asserted anywhere. Measured four ways in
`probes/rebuildstrategy_loses_the_replacement_without_a_descendant.py`: both inspeximus and the
reference `MarkdownAdapter` fail without a descendant, and both succeed with one. The receipt stays
honest in every failing arm (`aggregate=failed`), so this is a repair that cannot succeed for that store
shape, not one that claims falsely to have succeeded.

`repair-must-not-duplicate-a-preserved-proposition` moved to `awaiting_specification` and is not scored.
`StoreAdapter.rebuild` names parameters; the specification does not yet define provider-neutral
proposition identity, multiplicity or cardinality, and the maintainer asked that a candidate fixture not
manufacture that rule by quotation. Our own citation check reached the same verdict independently and
refused to score it. The blind spot is real and stays recorded as a specification request.

## Six gaps the maintainer found in the first version, all fixed

Every one was a false pass or an unbound source, and all six are closed here.

1. A mutated run that raised any exception counted as "mutation caught". A crash is not the declared
   counter-result; a raise now fails the case unless the case names the exception it expects.
2. `sys.settrace` recorded function names globally, so a control asking for `coverage` or `retire` was
   satisfied by any function of that name anywhere. Calls are now bound to the target instance.
3. The target commit and digest lived in prose. The runner now asserts the bound adapter matches the
   fixture's target and digests the tree it scores; `--pkg-digest` makes that binding enforceable.
4. A citation counted as valid when the quote was merely non-empty. Quotes are now checked against the
   named file in the pinned tree. That check immediately caught three of our own citations: a missing
   file, a markdown-formatting mismatch, and one attributed to the wrong source entirely.
5. `must_produce` was declarative. Each mutation's declared counter-result is now evaluated, so a
   mutation that breaks a case for an unrelated reason no longer earns credit.
6. Expectations were partial, so `collateral-must-survive-a-supersession` reported PASS while its own
   baseline carried `aggregate=failed` and `triad.positive=fail`. An outcome a case does not mention
   must still conform. Fixing this is what surfaced the `RebuildStrategy` finding above.

The three validator anti-vacuity cases remain declarative here and are not scored. They belong in an
executable validator contract, which is where the maintainer has moved them.
