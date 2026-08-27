"""The construction audit, wired where publication actually happens.

WHY THIS FILE EXISTS. On 2026-08-08 we posted a number on openclaw/openclaw#7707 that could not have
come out any other way: the probe called `measure(..., minja_p=1.0)`, `random() < 1.0` is always true,
so the poison record never accrued `bad`, so the guard that was supposed to block it could never fire.
"Poison earns standing 100% of the time" was a DEFINITION wearing the clothes of a measurement.

Our standing gate did not catch it, and both halves of it passed correctly by their own definitions:
`validate` asks that every number be backed by an artifact re-run this cycle, `verify` asks that the
number match the artifact. Neither asks whether the artifact could have produced any other number. A
construction defect reproduces perfectly, forever, on demand — every re-run made us more confident.

`tools/construction_audit.py` closes that hole. It shipped the same day with a docstring that ended
"Wire it into the publish path, not into someone's memory." Until this file, it was in someone's
memory. That is the second half of the same lesson, and it is the half that repeats.

WHAT THIS ENFORCES, and the failure mode it is built against. The expensive shape in this codebase is
a check that never sees its target and reports SAFE. So:

  * An EMPTY target set is a REFUSAL, not a pass. A gate that audits nothing has measured nothing.
  * A declared artifact that does not RESOLVE is a REFUSAL. A publication that links a runnable model
    the reader cannot open is a broken receipt.
  * A link into ANOTHER repo is reported and skipped, never silently resolved against this one.
    Measured: `verify-agent-memory-deletion` links `DanceNitra/ramr` and a repo-blind resolver called
    its artifact missing. A path is relative to its own repo.
  * Every exception is a dated WAIVER carrying a reason, printed on every run. The alternative to a
    visible waiver is not a stricter gate, it is a gate someone comments out.

Call it from a renderer; do not call it from a habit.
"""
from __future__ import annotations

import ast
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WAIVERS = ROOT / "tools" / "construction_waivers.json"

# Repos we can resolve to a local checkout. A link to anything else is OUT OF SCOPE and is reported
# as such — never resolved against ROOT, which is how a live artifact gets reported missing.
KNOWN_REPOS = {
    "DanceNitra/agora": ROOT,
    "DanceNitra/ramr": Path("C:/Users/Danculus/ramr-pub"),
    # inspeximus is the product repo and we cite runnable artifacts out of it in outreach -- a reply
    # about a data-loss fix pointed at its regression test and this gate refused with "NO artifact
    # resolved", because it had never been told the repo exists. A checker that cannot see a repo we
    # publish from audits nothing there and says so only as an empty target set.
    "DanceNitra/inspeximus": Path("C:/Users/Danculus/inspeximus-repo"),
}
BLOB_RE = re.compile(r"github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/blob/[^/]+/([A-Za-z0-9_/.\-]+\.py)")


def _audit_module():
    spec = importlib.util.spec_from_file_location("construction_audit",
                                                  ROOT / "tools" / "construction_audit.py")
    if spec is None or spec.loader is None:
        raise SystemExit("REFUSED: cannot load tools/construction_audit.py — the gate cannot run.")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_waivers() -> dict:
    if not WAIVERS.exists():
        return {}
    return json.loads(WAIVERS.read_text(encoding="utf-8"))


def links_in_text(text: str) -> tuple[list[Path], list[str], list[str]]:
    """Split the artifacts a piece of writing points at into (local, unresolved, external).

    `local` resolve inside a repo we have; `unresolved` are OUR repo but the file is not there (a
    broken receipt); `external` belong to a repo we cannot see and are out of scope, not missing.
    """
    local: list[Path] = []
    unresolved: list[str] = []
    external: list[str] = []
    for repo, rel in dict.fromkeys(BLOB_RE.findall(text)):
        base = KNOWN_REPOS.get(repo)
        if base is None or not base.exists():
            external.append("%s/%s" % (repo, rel))
            continue
        p = base / rel
        (local if p.exists() else unresolved).append(p if p.exists() else "%s/%s" % (repo, rel))
    return local, unresolved, external


def enforce(paths, label: str, *, unresolved=(), external=(), require_nonempty: bool = True) -> None:
    """Audit every artifact backing `label`. Refuse — SystemExit(1) — on anything unwaived.

    This raises rather than returning a bool on purpose: a caller that forgets to check a return value
    is exactly the failure this file exists to remove.
    """
    ca = _audit_module()
    waivers = load_waivers()
    paths = [Path(p) for p in paths]

    print("\n=== construction gate: %s ===" % label)
    for x in external:
        print("  skip (other repo, out of scope): %s" % x)

    problems: list[str] = []
    if unresolved:
        for u in unresolved:
            problems.append("UNRESOLVED artifact: %s — the publication links a runnable model that is "
                            "not in the repo it names" % u)

    if not paths and require_nonempty and not external:
        problems.append("NO artifact resolved for %r. An empty target set is a refusal: a gate that "
                        "audits nothing cannot tell you the claim is safe." % label)

    for p in sorted(set(paths)):
        rel = p.relative_to(ROOT).as_posix() if ROOT in p.parents else p.as_posix()
        try:
            findings = ca.audit(p)
        except Exception as ex:                     # a crash is a failure to run, not a pass
            problems.append("CRASH auditing %s: %s: %s" % (rel, type(ex).__name__, ex))
            continue
        w = waivers.get(rel, {})
        waived_kinds = set(w.get("kinds", []))
        for f in findings:
            if f.kind in waived_kinds:
                print("  waived [%s] %s line %d — %s (waived %s)"
                      % (f.kind, rel, f.line, w.get("reason", "NO REASON GIVEN"), w.get("dated", "?")))
            else:
                problems.append("[%s] %s line %d\n      %s\n      why: %s"
                                % (f.kind, rel, f.line, f.detail, f.why))
        if not findings:
            print("  clean: %s" % rel)

    if problems:
        print("\nREFUSED — %d blocking problem(s):" % len(problems))
        for pr in problems:
            print("  * %s" % pr)
        print("\nA number whose result is forced by its own construction must not be published.\n"
              "Fix the probe, or add a dated waiver with a reason to tools/construction_waivers.json.")
        raise SystemExit(1)
    print("  OK — %d artifact(s) audited. Necessary, not sufficient: this cannot tell you the claim "
          "is TRUE, only that the probe could have said no." % len(set(paths)))


def main() -> int:
    """CLI: audit files directly, or every artifact a piece of writing links."""
    args = sys.argv[1:]
    if not args:
        print(__doc__.split("\n")[0])
        print("usage: publish_gate.py <file.py|draft.md> ...")
        return 2
    direct, texts = [], []
    for a in args:
        (texts if Path(a).suffix.lower() in (".md", ".txt", ".html") else direct).append(a)
    local, unres, ext = [], [], []
    for t in texts:
        l, u, e = links_in_text(Path(t).read_text(encoding="utf-8", errors="replace"))
        local += l
        unres += u
        ext += e
    enforce(direct + local, ", ".join(args), unresolved=unres, external=ext)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
