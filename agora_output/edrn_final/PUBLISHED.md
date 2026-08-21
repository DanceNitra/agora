# Published

**Non-Monotonic Correlation Fluctuations in Heisenberg Models on Small Quantum Graphs**
Guanghao Li · Rastislav Drahoš · Marat Sultanov

- **DOI** — [10.5281/zenodo.22047304](https://doi.org/10.5281/zenodo.22047304)  *(this exact version)*
- **Concept DOI** — 10.5281/zenodo.22047303  *(always the newest version)*
- Record — https://zenodo.org/record/22047304
- Published 2026-08-21, preprint, CC-BY-4.0, PDF + `manuscript.tex`

Source of record is `luoxuejian000/edrn-dmrg-verification`, file
`8月20日沉默失谐最新修改稿`, after PR #6 and PR #7. The deposited PDF was built from
that file re-fetched from `main`, not from a local copy, and the published PDF was
re-downloaded unauthenticated afterwards and compared byte-for-byte against the build.

## Reproducing the checks

    python probes/edrn_manuscript_lint.py                  # source: 47/47, incl. controls
    python probes/edrn_corrected_gap_curve.py              # the corrected Fig. 3 data
    python probes/edrn_every_sector_not_just_three.py      # all 8 magnetisation sectors
    python probes/edrn_the_recovery_percentages_we_published.py   # the truncation control

The lint reads `manuscript_asreceived.tex` as its control fixture: several of its checks
assert that the defect it is looking for *was* present in the file as received, so that a
pass means "the fix works" rather than "the case never arises". Do not delete that file.

Marat's ORCID is still missing from the record. It can be added to a published Zenodo
deposit without minting a new version.
