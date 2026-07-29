> **QUEUED** — found 2026-07-29 ~05:05, gate mid-run so the repo is off limits. Small and mechanical.

# `inspeximus distill` cannot attribute what it writes

Closing an item I explicitly left open. The census probe flagged three CLI subcommands as unverified write
paths — `distill`, `browse`, `audit-build` — and refused to call them findings without reading them.

**Two were false positives.** My regex window bled into the adjacent `elif` branch, so `browse` appeared to
call `remember_decision` (that is the `decision` branch ten lines below) and `audit-build` appeared to call
`remember` (same reason). Neither writes. This is the second time that scan produced a plausible number
from the wrong node, which is why nothing it prints counts until it is read.

**One is real.** `cli.py:189` defines `distill` with a single `--file` argument, and the branch calls:

```python
res = m.distill_and_remember(text, distiller)
```

`Inspeximus.distill_and_remember(text, distiller, source, require_support)` **already takes a source** —
core is fine. The CLI simply never offers it, so a transcript distilled into memories through the CLI
produces records attributable to nothing. Exactly the shape of the `decision` gap fixed earlier tonight,
one subcommand over.

## The fix

```python
di.add_argument("--source", help="who or what the transcript came from ('crm/alice') — without it the "
                                 "distilled memories are attributable to nothing and forget-subject "
                                 "cannot reach them")
...
res = m.distill_and_remember(text, distiller, source=a.source or None)
```

Plus a test in `tests/test_cli_provenance.py` (no importorskip there — the CLI needs nothing optional),
with the control that matters: **without** `--source` the distilled records stay unreachable, because the
CLI must never invent a subject the caller did not supply.

## Note on the measurement

The probe run that established core's signature did NOT exercise the write: the fake distiller's output was
dropped (`captured: 0, dropped: 1`), so the erasure arm proved nothing. The finding rests on reading the
signature and the CLI branch, not on that run — stated here so nobody later mistakes the probe output for
evidence it is not.
