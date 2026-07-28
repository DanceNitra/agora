# Write paths that still cannot attribute what they write

**Measured 2026-07-28, read from the code rather than inferred.** Queued behind the 1.87.0 release, which
carries a data-loss fix and per `RELEASING.md` ships immediately rather than waiting for ordinary gaps.

## Closed this cycle

| surface | `source` | `derived_from` |
|---|---|---|
| `Inspeximus.remember` | ✔ | ✔ |
| `Inspeximus.remember_decision` | ✔ | ✔ |
| MCP `remember` | ✔ | ✔ |
| MCP `remember_decision` | ✔ | ✔ |
| CLI `remember` | ✔ `--source` | ✔ `--derived-from` |

## Still open

| surface | state | why it matters |
|---|---|---|
| **CLI `decision`** | `--because`, `--topic` only; calls `remember_decision(...)` with no provenance | The core method now accepts it and the MCP tool passes it — the CLI is the one surface left that cannot. A decision is usually *about* someone, which is exactly what an erasure request must reach. |
| `Inspeximus.route` / MCP `route` | no provenance parameter in core | ~8 internal `self.remember(...)` call sites; threading a caller's source through all of them is a larger change than a delegation. |
| `Inspeximus.observe` / MCP `observe` | no provenance parameter in core | Observations are evidence about a subject; same argument as decisions. |
| `resolve_reopened` | no provenance parameter | Lower volume, but it writes. |
| CLI `distill`, `browse`, `audit-build` | write via other paths | Unverified per-path; the regex scan that suggested them produced false positives (a 900-char window bled into the neighbouring branch), so each needs reading before it is claimed. |

## The method note that matters

The first scan of the CLI reported nine write-capable subcommands with provenance missing. It was wrong:
the window overlapped adjacent `elif` branches, so `recall` appeared to call `revert`. Only `decision` was
confirmed, by reading the argparse definition (`cli.py:151`) and the branch (`cli.py:487`) directly.

A scan that finds a plausible number by looking at the wrong node is the failure this whole audit exists
to catch. Nothing above is listed as confirmed unless it was read.

## The guard that keeps this list honest

`tests/test_write_paths_provenance_census.py` in the inspeximus repo pins `route`, `observe` and
`resolve_reopened` as still-open and FAILS if one of them silently gains a `source` — so the list cannot
rot into a lie. The CLI has no equivalent census yet; it should get one with the `--source` fix.
