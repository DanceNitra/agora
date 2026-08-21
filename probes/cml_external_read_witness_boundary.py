"""Does CML's merged External Read Witness layer hold at its own stated boundary?

CONTEXT. safal207/Causal-Memory-Layer#289 produced a layer we adopted into inspeximus 2.14.0. We told
that thread our translation of @Stratogain's `reads > 0 => observations > 0` was WEAKER than the
original, because ours compares two fields inside the store and so cannot see a collector dead from
day one. safal207 answered with an architecture and merged it: #290 (`ExternalReadWitness`,
`check_admissibility_preconditions`) and #291 (an adapter from the vCML eBPF monitor's JSONL).

THIS FILE IS VERSION 2, AND VERSION 1 WAS THE DEFECT IT EXISTS TO FIND. v1 reported `USABLE` over six
claims, but its VOID gate was computed from three controls that all called
`check_admissibility_preconditions` -- so four of the six claims, which were regexes over source text,
were certified by controls that could not see them. Measured afterwards: v1's test-coverage detector
found ZERO matches in one of the two test files (every witness there is built through
`external_witness_from_vcml_records`, which matched neither alternative), its recall against six
plausible ways to write the case under test was 1 in 6, its emitted-key list omitted `pid`/`ppid`/
`comm` -- the very fields two other claims argued about -- and its "no drop counter" regex missed a
real silent-loss path in the same file (`_evict_pid`, FIFO at `_MAX_PID_CACHE = 10_000`). A check that
never sees its target reports SAFE.

So v2 obeys two rules. Every claim about BEHAVIOUR is measured by calling the code or by running their
suite. Every claim about ABSENCE in source text carries a MUST-FAIL PLANT: the same detector is run
against a copy with the missing thing inserted, and the whole run is VOID unless the detector flags
its own plant. There is also a build-identity control, because nothing in v1 would have failed if a
different `cml` had been imported.

CLAIMS
  B1  an AVAILABLE witness reporting reads_count == 0 returns a full pass
  B2  mutating the guard `reads_count > 0` to `>= 0` survives all 12 of their tests
  B3  implementing the `available && reads == 0 -> applicable: False` row they sketched ALSO survives
      all 12 -- so the cell is unexercised in either direction
  B4  and that row would make a quiet scope fail closed EVEN WITH a healthy ledger, which is why we
      are not asking for it
  B5  foreign-PID reads stamped with the caller's scope: at observations == 0 a noisy false accusation,
      at observations >= 1 a SILENT false credit with no reason string
  B6  the witness dataclass carries no observation window and no loss count (runtime fields, not regex)
  B7  OUR OWN published number was wrong: "the other 19 are untested" of 24 surfaces
  T1  the monitor has no PID/comm filter                       [plant: a pid guard in BPF_TEXT]
  T2  the monitor emits no cgroup id                           [plant: bpf_get_current_cgroup_id]
  T3  the monitor wires no perf-buffer loss callback           [plant: open_perf_buffer(..., lost_cb=)]

Run: python probes/cml_external_read_witness_boundary.py
"""
from __future__ import annotations

import base64
import dataclasses
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request

CML_REF = "0a324faaa498dc79f86c933aa5a8e0f3c233bd49"       # main, 2026-08-17, #290 + #291 merged

# A commit ref pins a NAME; a sha256 pins the BYTES. Asserted rather than merely recorded, so that the
# only environment knob this probe reads -- a GitHub token, which affects rate limiting and nothing
# else -- provably cannot change any number below. The construction gate refused the first version for
# exactly that undisclosed degree of freedom, and a waiver would have been the lazy answer.
EXPECTED_SHA256 = {
    "cml/external_read_witness.py":
        "1688dc353ecef924a78aaa217571f9be73066017fa0709a79309afa8851076c1",
    "cml/admissibility_preconditions.py":
        "492045443656dc8f79492e2508639717333ad88ff3cd55aaccd73a8ef1893bc4",
    "cml/integrations/vcml_ebpf_external_witness.py":
        "1e5df5847b752cbccd618f6e41a2fad227753e43090cd95e4b9ad241150d487d",
    "tests/test_external_read_witness.py":
        "cad9a75b50d7b5c56fad0baaae857e5cf74c6c27782152f3ff7599e2947a9012",
    "tests/test_vcml_ebpf_external_witness.py":
        "d46817baff160dda1e4733e2caffb8998bfe9abc07a8282a99dbe4b3433abd47",
    "vcml/linux-ebpf/file_monitor.py":
        "e9533149f3d817cc6a71f712108f926034f46f7ad05d785fb5f330854176207a",
}
INSPEXIMUS_SHIPPED = "2.14.0"                              # the version whose number we published
MODULES = {
    "cml/external_read_witness.py": "external_read_witness.py",
    "cml/admissibility_preconditions.py": "admissibility_preconditions.py",
    "cml/integrations/vcml_ebpf_external_witness.py": "integrations/vcml_ebpf_external_witness.py",
}
TESTS = ["tests/test_external_read_witness.py", "tests/test_vcml_ebpf_external_witness.py"]
MONITOR = "vcml/linux-ebpf/file_monitor.py"

# ── PR #293 arrived while this probe was being written, and closed three of the four things it was
# built to find. So the probe now measures BOTH refs: the merged count-based layer, and the per-read
# reconciliation that supersedes it for the per-read case. Note that
# `cml/admissibility_preconditions.py` has the SAME digest under both refs -- #293 does not touch it,
# which is why the count-path finding survives #293 rather than being stale.
CML_REF_293 = "7a9893235d770ce67cd7042e703a3136ad70f000"      # head of PR #293, monitor v0.7
MODULES_293 = dict(MODULES, **{
    "cml/integrations/vcml_read_id_coverage.py": "integrations/vcml_read_id_coverage.py"})
TESTS_293 = TESTS + ["tests/test_vcml_read_id_coverage.py"]
EXPECTED_SHA256_293 = {
    "cml/external_read_witness.py":
        "1688dc353ecef924a78aaa217571f9be73066017fa0709a79309afa8851076c1",
    "cml/admissibility_preconditions.py":
        "492045443656dc8f79492e2508639717333ad88ff3cd55aaccd73a8ef1893bc4",
    "cml/integrations/vcml_ebpf_external_witness.py":
        "1e5df5847b752cbccd618f6e41a2fad227753e43090cd95e4b9ad241150d487d",
    "cml/integrations/vcml_read_id_coverage.py":
        "b7692991976aae8bf6963583bb42b576b171f0a9613b575ef651af077e7172f4",
    "vcml/linux-ebpf/file_monitor.py":
        "53d5eee4efcdd1cdddb27f3955b28949aeb7b367c027edb0af3f0e533622e894",
    "tests/test_external_read_witness.py":
        "cad9a75b50d7b5c56fad0baaae857e5cf74c6c27782152f3ff7599e2947a9012",
    "tests/test_vcml_ebpf_external_witness.py":
        "d46817baff160dda1e4733e2caffb8998bfe9abc07a8282a99dbe4b3433abd47",
    "tests/test_vcml_read_id_coverage.py":
        "62bfa1513876ed00ac9c47cf704d256849e271b069b9bd7039fcbbefd1f3cdf8",
}
API = "https://api.github.com/repos/safal207/Causal-Memory-Layer/contents/%s?ref=" + CML_REF

_T0 = time.monotonic()


def _log(msg: str) -> None:
    print("[%6.1fs] %s" % (time.monotonic() - _T0, msg), flush=True)


def fetch(path: str) -> str:
    """Fetch UNAUTHENTICATED, deliberately.

    The first version read `GITHUB_TOKEN`/`GH_TOKEN` if present, and the construction gate refused it:
    an environment knob the published run never varied is an undisclosed degree of freedom. A waiver
    would have been the lazy answer, because there is a real fix -- six unauthenticated requests fit
    inside GitHub's anonymous rate limit, so the knob can simply go. That also makes this receipt
    runnable by a reader who has no credentials, which is the point of publishing it.
    """
    req = urllib.request.Request(API % path, headers={"Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return base64.b64decode(json.load(r)["content"]).decode("utf-8")


# ── the three text detectors, each paired with the plant that must trip it ──────────────────────────
DETECTORS = {
    "T1_no_pid_or_comm_filter": {
        "asserts": "the monitor emits every process's events; nothing filters by pid or comm",
        # A filter can live in the BPF C string, so the detector must read that too.
        "detect": lambda s: bool(re.search(
            r"(?:data\.pid|event\.pid|pid)\s*(?:!=|==)\s*(?:target|filter|self_|\d)"
            r"|target_pid|filter_pid|FILTER_PID|bpf_get_current_comm\(\)\s*!=", s)),
        "plant": lambda s: s.replace("BPF_TEXT = r\"\"\"",
                                     "BPF_TEXT = r\"\"\"\n// planted\n#define FILTER_PID 4242\n", 1),
    },
    "T2_no_cgroup_id_emitted": {
        "asserts": "no cgroup id is captured, so events cannot be bound to a container scope",
        "detect": lambda s: bool(re.search(r"cgroup_id|bpf_get_current_cgroup_id|cgroup\"", s)),
        "plant": lambda s: s.replace("data.pid = pid_tgid >> 32;",
                                     "data.pid = pid_tgid >> 32;\n"
                                     "    data.cgroup_id = bpf_get_current_cgroup_id();", 1),
    },
    "T3_no_perf_loss_callback": {
        "asserts": "open_perf_buffer is called without lost_cb, so dropped samples are silent",
        "detect": lambda s: bool(re.search(r"lost_cb\s*=|def\s+on_lost|lost_callback", s)),
        "plant": lambda s: s.replace('b["read_events"].open_perf_buffer(on_read)',
                                     'b["read_events"].open_perf_buffer(on_read, lost_cb=on_lost)', 1),
    },
}


def main() -> int:
    work = tempfile.mkdtemp(prefix="cml_witness_v2_")
    pkg = os.path.join(work, "cml")
    os.makedirs(os.path.join(pkg, "integrations"), exist_ok=True)
    open(os.path.join(pkg, "__init__.py"), "w").close()
    open(os.path.join(pkg, "integrations", "__init__.py"), "w").close()

    src: dict[str, str] = {}
    digests: dict[str, str] = {}
    for i, p in enumerate(list(MODULES) + TESTS + [MONITOR], 1):
        _log("fetching %d/%d %s" % (i, len(MODULES) + len(TESTS) + 1, p))
        src[p] = fetch(p)
        digests[p] = hashlib.sha256(src[p].encode("utf-8")).hexdigest()
        want = EXPECTED_SHA256.get(p)
        if want and digests[p] != want:
            raise SystemExit(
                "REFUSED: %s does not match its pinned sha256.\n  expected %s\n  got      %s\n"
                "The bytes under this ref changed, so every number below would describe a different\n"
                "artifact than the one the claims were written against." % (p, want, digests[p]))
    for remote, local in MODULES.items():
        with open(os.path.join(pkg, local), "w", encoding="utf-8") as fh:
            fh.write(src[remote])
    for t in TESTS:
        with open(os.path.join(work, os.path.basename(t)), "w", encoding="utf-8") as fh:
            fh.write(src[t])

    sys.path.insert(0, work)
    import cml.admissibility_preconditions as AP
    from cml.admissibility_preconditions import check_admissibility_preconditions as chk
    from cml.external_read_witness import ExternalReadWitness as W
    from cml.integrations.vcml_ebpf_external_witness import (
        external_witness_from_vcml_records as from_records,
    )

    out: dict = {"cml_ref": CML_REF, "sha256": digests, "controls": {}, "claims": {}}

    # ── CONTROL 0: am I even measuring the code I fetched? Nothing in v1 would have caught this.
    imported_from = os.path.abspath(AP.__file__)
    out["controls"]["C0_build_identity"] = {
        "imported_from": imported_from,
        "expected_under": os.path.abspath(work),
        "ok": imported_from.startswith(os.path.abspath(work)),
    }

    def pytest_all() -> tuple:
        """-> (exit_code, passed, failed, errors). COUNTS, never the summary string.

        The first version of this returned the summary line verbatim and compared it for equality.
        That line ends in an elapsed time ("12 passed in 0.03s"), so two identical outcomes never
        compared equal and a surviving mutant was reported as killed -- the run went VOID on its own
        control, correctly, and that is how this was found.
        """
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                           capture_output=True, text=True, cwd=work, timeout=600)
        blob = r.stdout
        def n(word: str) -> int:
            m = re.search(r"(\d+)\s+%s" % word, blob)
            return int(m.group(1)) if m else 0
        return r.returncode, n("passed"), n("failed"), n("error")

    _log("controls P1/P2 + baseline suite")
    p1 = chk(witness=W(source_id="s", scope_id="sess", reads_count=3), ledger_scope_id="sess",
             ledger_observations=0)
    p2 = chk(witness=W(source_id="s", scope_id="sess", reads_count=0, available=False),
             ledger_scope_id="sess", ledger_observations=0)
    out["controls"]["P1_dead_collector_is_caught"] = {
        "reasons": list(p1.reasons),
        "ok": p1.applicable and not p1.holds and "observation_channel_missing" in p1.reasons}
    out["controls"]["P2_unavailable_witness_is_inapplicable"] = {
        "reasons": list(p2.reasons), "ok": (p2.applicable is False)}
    baseline = pytest_all()
    out["controls"]["P4_their_suite_is_green_before_we_touch_it"] = {
        "exit_passed_failed_errors": baseline,
        "ok": baseline[0] == 0 and baseline[1] == 12 and baseline[2] == 0 and baseline[3] == 0}

    # ── B1
    _log("B1 available witness, zero reads")
    rows = []
    for obs in (0, 5):
        r = chk(witness=W(source_id="s", scope_id="sess", reads_count=0), ledger_scope_id="sess",
                ledger_observations=obs)
        rows.append({"ledger_observations": obs, "applicable": r.applicable, "holds": r.holds,
                     "allows_applicability": r.allows_applicability, "reasons": list(r.reasons)})
    out["claims"]["B1_zero_reads_returns_a_pass"] = {
        "sketched_in_289": "external witness available, reads == 0 -> applicable: false",
        "measured": rows,
        "holds": all(x["allows_applicability"] is True for x in rows)}

    # ── B2 / B3 / B4: mutate, run THEIR suite, restore.
    apath = os.path.join(pkg, "admissibility_preconditions.py")
    pristine = open(apath, encoding="utf-8").read()
    MUTANTS = {
        "B2_guard_relaxed_to_ge_survives_their_suite": (
            "if witness.reads_count > 0 and ledger_observations == 0:",
            "if witness.reads_count >= 0 and ledger_observations == 0:"),
        "B3_implementing_the_sketched_row_survives_their_suite": (
            "    reasons: list[str] = []",
            '    if witness.reads_count == 0:\n'
            '        return AdmissibilityPreconditionResult(\n'
            '            applicable=False, holds=False, reasons=("not_exercised",))\n\n'
            "    reasons: list[str] = []"),
    }
    for name, (anchor, repl) in MUTANTS.items():
        _log("%s" % name.split("_")[0])
        found = pristine.count(anchor) == 1
        if found:
            with open(apath, "w", encoding="utf-8") as fh:
                fh.write(pristine.replace(anchor, repl, 1))
            res = pytest_all()
            with open(apath, "w", encoding="utf-8") as fh:
                fh.write(pristine)
        else:
            res = None
        out["claims"][name] = {
            "anchor_unique": found,
            "baseline_exit_passed_failed_errors": baseline,
            "with_mutant_exit_passed_failed_errors": res,
            "holds": bool(found and res == baseline and baseline[0] == 0),
            "read_this_as": "the case is unexercised -- a test gap, not a code defect"}
    restored = pytest_all()
    out["controls"]["P5_suite_green_again_after_restore"] = {
        "exit_passed_failed_errors": restored, "ok": restored == baseline}

    _log("B4 consequence of that row on a QUIET scope")
    with open(apath, "w", encoding="utf-8") as fh:
        fh.write(pristine.replace(*MUTANTS["B3_implementing_the_sketched_row_survives_their_suite"]))
    import importlib
    importlib.reload(AP)
    b4 = []
    for obs in (0, 5):
        r = AP.check_admissibility_preconditions(
            witness=W(source_id="s", scope_id="sess", reads_count=0),
            ledger_scope_id="sess", ledger_observations=obs)
        b4.append({"ledger_observations": obs, "applicable": r.applicable, "holds": r.holds,
                   "allows_applicability": r.allows_applicability})
    with open(apath, "w", encoding="utf-8") as fh:
        fh.write(pristine)
    importlib.reload(AP)
    out["claims"]["B4_that_row_fails_a_quiet_scope_even_with_a_healthy_ledger"] = {
        "measured": b4,
        "holds": all(x["allows_applicability"] is False for x in b4),
        "read_this_as": "why we are NOT asking for that row: near-zero precision on idle windows"}

    # ── B5: both directions of the unfiltered-capture hazard.
    _log("B5 foreign-PID reads, both ledger states")
    w = from_records([{"action": "open", "actor": {"pid": 111}},
                      {"action": "read", "actor": {"pid": 999}, "object": {"fd": 3}},
                      {"action": "read", "actor": {"pid": 999}, "object": {"fd": 4}}],
                     scope_id="sess")
    b5 = []
    for obs in (0, 1):
        r = chk(witness=w, ledger_scope_id="sess", ledger_observations=obs)
        b5.append({"ledger_observations": obs, "allows": r.allows_applicability,
                   "reasons": list(r.reasons)})
    out["claims"]["B5_unfiltered_capture_gives_a_silent_false_credit"] = {
        "reads_counted": w.reads_count, "all_reads_belong_to_pid": 999,
        "scope_stamped": w.scope_id, "measured": b5,
        "adapter_contract": 'docstring: read events "for the supplied scope" -- so this is a CALLER '
                            'obligation, not an adapter defect',
        # The claim is the SILENT one: a live collector plus foreign reads passes with no reasons.
        "holds": (w.reads_count == 2
                  and b5[1]["allows"] is True and b5[1]["reasons"] == []
                  and b5[0]["allows"] is False)}

    # ── B6: runtime fields.
    _log("B6 witness fields at runtime")
    fields = [f.name for f in dataclasses.fields(W)]
    out["claims"]["B6_contract_has_no_window_and_no_loss_count"] = {
        "fields": fields,
        "holds": not any(re.search(r"window|since|until|delta|interval|loss|lost|drop", f)
                         for f in fields)}

    # ── B7: our own number.
    _log("B7 re-measuring OUR OWN '19 untested' against shipped inspeximus %s" % INSPEXIMUS_SHIPPED)
    code = ("import json,os,tempfile,hashlib;from inspeximus import Inspeximus;"
            "d=tempfile.mkdtemp();p=os.path.join(d,'s.json');"
            "s=os.path.join(d,'doc.txt');open(s,'wb').write(b'x');"
            "m=Inspeximus(path=p,embed=False,receipts=True);"
            "m.remember('a',key='a',object='a',source={'doc':s,"
            "'observed_sha256':hashlib.sha256(b'x').hexdigest()});"
            "m.remember('b',key='b',object='b');m.flush();r=m.audit_the_audits();"
            "print(json.dumps({'probes':len(r['probes']),"
            "'surfaces':sorted({x['surface'] for x in r['probes']}),"
            "'available':r['surfaces_available']}))")
    b7: dict = {"published": "Five probes against 24 surfaces; the other 19 are untested"}
    try:
        raw = subprocess.run(["uvx", "--from", "inspeximus==" + INSPEXIMUS_SHIPPED, "python", "-c",
                              code], capture_output=True, text=True, timeout=300)
        got = json.loads(raw.stdout.strip().splitlines()[-1])
        b7.update(got, untested_measured=got["available"] - len(got["surfaces"]),
                  untested_published=19,
                  holds=(got["available"] - len(got["surfaces"])) != 19)
    except Exception as ex:                                        # noqa: BLE001
        b7.update(error="%s: %s" % (type(ex).__name__, ex), holds=None)
    out["claims"]["B7_our_own_untested_count_was_wrong"] = b7

    # ── T1/T2/T3: absence in source, each with its own must-fail plant.
    mon = src[MONITOR]
    # Keys are emitted in nested dict literals, several per line -- v1's line-anchored regex missed
    # pid/ppid/comm, which are exactly the fields T1 and T2 are about.
    emit = mon[mon.index("record = {"):] if "record = {" in mon else mon
    keys = sorted(set(re.findall(r'"(\w+)"\s*:', emit)))
    for name, d in DETECTORS.items():
        _log("%s + its must-fail plant" % name.split("_")[0])
        fires_clean = d["detect"](mon)
        planted = d["plant"](mon)
        row = {
            "asserts": d["asserts"],
            "detector_fires_on_the_real_source": fires_clean,
            "plant_changed_the_source": planted != mon,
            "detector_fires_on_the_plant": d["detect"](planted),
            # The CLAIM holds only if the thing is absent AND the detector can see it when present.
            "holds": (not fires_clean) and planted != mon and d["detect"](planted),
        }
        out["claims"][name] = row
    out["claims"]["T4_emitted_record_keys"] = {
        "keys": keys,
        "note": "v1 published this list without pid/ppid/comm because its regex was line-anchored",
        "silent_loss_path_v1_missed": "_evict_pid: FIFO eviction at _MAX_PID_CACHE = 10_000 drops the "
                                      "open-path context for the oldest pid, unreported",
        "holds": None}

    # ══ PR #293: the per-read reconciliation, and the disagreement between the two layers. ══
    _log("D-series: fetching the #293 head and re-measuring both layers")
    w293 = tempfile.mkdtemp(prefix="cml_293_")
    p293 = os.path.join(w293, "cml")
    os.makedirs(os.path.join(p293, "integrations"), exist_ok=True)
    os.makedirs(os.path.join(w293, "vcml", "linux-ebpf"), exist_ok=True)
    open(os.path.join(p293, "__init__.py"), "w").close()
    open(os.path.join(p293, "integrations", "__init__.py"), "w").close()
    api293 = API.replace(CML_REF, CML_REF_293)
    d293: dict = {}

    def fetch293(path: str) -> str:
        req = urllib.request.Request(api293 % path,
                                     headers={"Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return base64.b64decode(json.load(r)["content"]).decode("utf-8")

    for p in list(MODULES_293) + TESTS_293 + [MONITOR]:
        text = fetch293(p)
        got = hashlib.sha256(text.encode("utf-8")).hexdigest()
        want = EXPECTED_SHA256_293.get(p)
        if want and got != want:
            raise SystemExit("REFUSED: %s at %s does not match its pinned sha256 (%s != %s)"
                             % (p, CML_REF_293[:7], got, want))
        d293[p] = got
        if p in MODULES_293:
            dest = os.path.join(p293, MODULES_293[p])
        elif p == MONITOR:
            dest = os.path.join(w293, MONITOR)          # the contract test reads this RELATIVE path
        else:
            dest = os.path.join(w293, os.path.basename(p))
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(text)
    out["sha256_pr293"] = d293
    out["cml_ref_pr293"] = CML_REF_293
    out["admissibility_unchanged_by_293"] = (
        digests["cml/admissibility_preconditions.py"]
        == d293["cml/admissibility_preconditions.py"])

    def pytest293() -> tuple:
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                           capture_output=True, text=True, cwd=w293, timeout=600)
        def n(word: str) -> int:
            m = re.search(r"(\d+)\s+%s" % word, r.stdout)
            return int(m.group(1)) if m else 0
        return r.returncode, n("passed"), n("failed"), n("error")

    base293 = pytest293()
    # A green baseline is load-bearing: the contract test reads vcml/linux-ebpf/file_monitor.py by
    # RELATIVE path, so a tree without it reports a failure that belongs to the harness. That happened
    # here first, and it is why this control exists rather than a bare assertion.
    out["controls"]["P6_the_293_suite_is_green_with_the_monitor_present"] = {
        "exit_passed_failed_errors": base293,
        "ok": base293[0] == 0 and base293[1] == 22 and base293[2] == 0}

    import importlib
    sys.path.insert(0, w293)
    for mod in ("cml", "cml.integrations", "cml.external_read_witness",
                "cml.admissibility_preconditions", "cml.integrations.vcml_read_id_coverage"):
        sys.modules.pop(mod, None)
    from cml.admissibility_preconditions import (                       # noqa: E402
        check_admissibility_preconditions as count_based)
    from cml.external_read_witness import ExternalReadWitness as W293   # noqa: E402
    from cml.integrations.vcml_read_id_coverage import (                # noqa: E402
        reconcile_successful_read_id_coverage as per_read)

    def ex(rid: str, ret: int = 8) -> dict:
        return {"action": "read_exit", "object": {"return_value": ret}, "read_id": rid}

    # D1: THE disagreement. Same question, two layers, opposite answers.
    _log("D1 the two layers on 'the channel was not exercised'")
    cb = count_based(witness=W293(source_id="s", scope_id="sess", reads_count=0),
                     ledger_scope_id="sess", ledger_observations=0)
    pr = per_read([], [], scope_id="sess", external_available=True)
    out["claims"]["D1_the_two_layers_disagree_on_not_exercised"] = {
        "count_based": {"applicable": cb.applicable, "holds": cb.holds,
                        "allows": cb.allows_applicability, "reasons": list(cb.reasons)},
        "per_read": {"applicable": pr.applicable, "holds": pr.holds, "reasons": list(pr.reasons)},
        "holds": (cb.allows_applicability is True and pr.applicable is False
                  and "coverage_not_exercised" in pr.reasons)}

    # D2: their own argument for #293, confirmed independently rather than assumed.
    _log("D2 confirming THEIR point: count equality cannot see [r1,r1] vs [r1,r2]")
    dup = per_read([ex("r1"), ex("r2")], [{"read_id": "r1"}, {"read_id": "r1"}], scope_id="sess")
    cnt = count_based(witness=W293(source_id="s", scope_id="sess", reads_count=2),
                      ledger_scope_id="sess", ledger_observations=2)
    out["claims"]["D2_per_read_catches_what_count_equality_cannot"] = {
        "per_read": {"holds": dup.holds, "missing": list(dup.missing_read_ids),
                     "duplicate_ledger": list(dup.duplicate_ledger_read_ids)},
        "count_path_same_shape": {"applicable": cnt.applicable, "holds": cnt.holds},
        "holds": (dup.holds is False and "r2" in dup.missing_read_ids
                  and cnt.applicable is True and cnt.holds is True)}

    # D3: the hazard the count path had, now fails closed under subset-by-identity.
    _log("D3 a read id the ledger never observed")
    foreign = per_read([ex("foreign-999")], [{"read_id": "r1"}], scope_id="sess")
    out["claims"]["D3_an_unobserved_read_id_now_fails_closed"] = {
        "holds": foreign.holds is False and "foreign-999" in foreign.missing_read_ids,
        "missing": list(foreign.missing_read_ids),
        "unexpected": list(foreign.unexpected_ledger_read_ids)}

    # D4: completion semantics, both directions -- ret<0 excluded, ret==0 (EOF) required.
    _log("D4 failed read excluded, EOF required")
    failed = per_read([ex("r-failed", -5)], [], scope_id="sess")
    eof = per_read([ex("r-eof", 0)], [], scope_id="sess")
    out["claims"]["D4_ret_lt_0_excluded_and_EOF_required"] = {
        "failed_read": {"applicable": failed.applicable, "reasons": list(failed.reasons)},
        "eof_read": {"applicable": eof.applicable, "holds": eof.holds,
                     "missing": list(eof.missing_read_ids)},
        "holds": (failed.applicable is False and eof.applicable is True
                  and eof.holds is False and "r-eof" in eof.missing_read_ids)}

    # D5: M1 still survives, now against the LARGER suite on the #293 head.
    _log("D5 mutant '>' -> '>=' against the 22-test suite")
    a293 = os.path.join(p293, "admissibility_preconditions.py")
    clean293 = open(a293, encoding="utf-8").read()
    anchor = "if witness.reads_count > 0 and ledger_observations == 0:"
    found = clean293.count(anchor) == 1
    if found:
        with open(a293, "w", encoding="utf-8") as fh:
            fh.write(clean293.replace(anchor, anchor.replace("> 0", ">= 0"), 1))
        mut293 = pytest293()
        with open(a293, "w", encoding="utf-8") as fh:
            fh.write(clean293)
    else:
        mut293 = None
    out["claims"]["D5_the_count_guard_mutant_survives_the_293_suite"] = {
        "anchor_unique": found, "baseline": base293, "with_mutant": mut293,
        "holds": bool(found and mut293 == base293 and base293[2] == 0)}
    out["controls"]["P7_293_suite_green_after_restore"] = {
        "exit_passed_failed_errors": pytest293(), "ok": pytest293() == base293}

    # ── VOID unless every control passed AND every text detector tripped its own plant.
    controls_ok = all(v["ok"] for v in out["controls"].values())
    plants_ok = all(out["claims"][n]["detector_fires_on_the_plant"] for n in DETECTORS)
    out["controls_all_passed"] = controls_ok
    out["every_text_detector_tripped_its_plant"] = plants_ok
    out["verdict"] = ("USABLE" if (controls_ok and plants_ok) else
                      "VOID -- a control failed or a text detector could not see its own plant, so "
                      "no claim here is evidence of anything")

    dst = os.path.splitext(os.path.abspath(__file__))[0] + ".result.json"
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)

    print("\n" + "=" * 78)
    print("CONTROLS:")
    for k, v in out["controls"].items():
        print("  %-46s %s" % (k, "ok" if v["ok"] else "FAILED"))
    print("TEXT DETECTORS -- each must flag its own plant:")
    for n in DETECTORS:
        r = out["claims"][n]
        print("  %-46s clean=%-5s plant=%-5s %s"
              % (n, r["detector_fires_on_the_real_source"], r["detector_fires_on_the_plant"],
                 "ok" if r["detector_fires_on_the_plant"] else "BLIND"))
    print("CLAIMS (holds=True means CONFIRMED):")
    for k, v in out["claims"].items():
        if v.get("holds") is not None:
            print("  %-46s holds=%s" % (k, v["holds"]))
    print("VERDICT:", out["verdict"])
    print("receipt ->", dst)
    return 0 if (controls_ok and plants_ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
