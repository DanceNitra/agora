"""
bseries_matrix_probe.py — mnemo's corroboration/withhold trace for the cross-framework B-series
(B-001 preference application, B-002 same-origin sybil, B-003 belief update / independent 2nd source).

Runs the actual mnemo mechanics (not a model of them) so a claim about mnemo's behavior can be checked
against code BEFORE it goes into a joint matrix/paper. The honest result:
  B-001 (preference): a keyed latest-wins supersession -> ALLOW (preferences need no corroboration bar).
  B-002 (same-origin sybil re-asserts the override): withheld ONLY under strict (verified-key) corroboration,
        where the same origin collapses to one key. In the DEFAULT string-corroboration mode, a sybil that
        uses two distinct source *labels* clears the >=2 gate and mnemo wrongly resumes — two labels from the
        same origin are not two independent votes, and a naive count can't tell them apart.
  B-003 (genuinely independent second source): resumes/ALLOW in both modes (2 distinct sources).

Run: python bseries_matrix_probe.py   (imports the shipped mnemo; no keys)
"""
import os, sys, tempfile
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from mnemo.mnemo import Mnemo


def _store(strict=False):
    fd, p = tempfile.mkstemp(suffix=".json"); os.close(fd); os.remove(p)
    try:
        s = Mnemo(path=p)
    except TypeError:
        s = Mnemo()
    s.strict_corroboration = strict
    return s


def _corrob(s, rec):
    return s._corroborated(rec, {r["id"]: r for r in s.items})


def _dsrc(s, rec):
    return Mnemo._distinct_sources(rec.get("links"), {r["id"]: r for r in s.items})


def main():
    # B-001 preference application
    s = _store()
    p1 = s.remember("pref: theme=dark", mtype="episodic", key="ui::theme", source={"doc": "user"})
    p2 = s.remember("pref: theme=light", mtype="episodic", key="ui::theme", source={"doc": "user"})
    old = next(r for r in s.items if r["id"] == p1)
    print(f"B-001 preference | keyed latest-wins -> ALLOW; prior status={old.get('status')}")

    # B-002 same-origin sybil, three modes
    def b002(mode):
        s = _store(strict=(mode == "strict"))
        claim = s.remember("belief: capital=Aville", mtype="episodic", source={"doc": "canon"})
        c = next(r for r in s.items if r["id"] == claim)
        w1 = s.remember("override: capital=Bville", mtype="episodic", source={"doc": "attacker"})
        c["links"] = [w1]
        s1 = not _corrob(s, c)
        src2 = {"doc": "attacker"} if mode == "same-string" else {"doc": "attacker-sockpuppet"}
        w2 = s.remember("override: capital=Bville", mtype="episodic", source=src2)
        c["links"] = [w1, w2]
        return s1, (not _corrob(s, c)), _dsrc(s, c)
    for mode in ("same-string", "distinct-strings (default)", "strict (verified-key)"):
        m = "same-string" if mode == "same-string" else ("strict" if "strict" in mode else "distinct")
        s1, withheld, ds = b002(m)
        print(f"B-002 [{mode:26}] step1_withhold={s1} step2_distinct_sources={ds} "
              f"withheld={withheld}  {'OK (withheld)' if withheld else 'FOOLED (resumed)'}")

    # B-003 independent second source
    s = _store()
    claim = s.remember("belief: capital=Aville", mtype="episodic", source={"doc": "canon"})
    c = next(r for r in s.items if r["id"] == claim)
    w1 = s.remember("update: capital=Cville", mtype="episodic", source={"doc": "registry"})
    c["links"] = [w1]; s1 = not _corrob(s, c)
    w2 = s.remember("update: capital=Cville", mtype="episodic", source={"doc": "independent-survey"})
    c["links"] = [w1, w2]
    print(f"B-003 independent 2nd source | step1_withhold={s1} step2_distinct_sources={_dsrc(s, c)} "
          f"-> {'RESUME/ALLOW' if _corrob(s, c) else 'still withheld'}")
    print("\nmnemo's B-002 withhold is CONDITIONAL on strict/attested corroboration; the default string count is "
          "fooled by a distinct-label same-origin sybil. B-003 resumes on a genuinely independent source.")


if __name__ == "__main__":
    main()
