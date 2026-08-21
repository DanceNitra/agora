"""Gate the reply to @safal207 and @Stratogain on anthropics/claude-code#34556.

The reply says a released version does something. So it is checked against the version INSTALLED
FROM PyPI in a clean environment, never against the working tree -- the tree is what I edited, and
"it works here" is the claim a reader cannot reproduce.

The attestation line is checked too, and against the right endpoint. The PyPI JSON API's
`provenance` field reads `None` for 2.17.0, 2.18.0 and 2.19.0 alike, all three published the same
way, so that field is the wrong instrument. `/integrity/.../provenance` returns the bundle.
Reporting "no attestation" from the first would have understated a true claim, which is the same
class of error as overstating one.

Run:  python probes/gate_34556_commitment_scope.py
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DRAFT = os.path.join(ROOT, "agora_output", "drafts", "reply_34556_commitment_scope.md")
VENV = os.path.join(os.environ.get("TEMP", "/tmp"), "claude", "C--Users-Danculus-agora",
                    "e6f8e2c8-b4c1-4269-a886-f10b2cd62521", "scratchpad", "v219",
                    "Scripts", "python.exe")
rows: list[tuple[bool, str, str]] = []


def ck(ok, label, detail=""):
    rows.append((bool(ok), label, detail))


def gh(*a):
    r = subprocess.run(["gh", *a], capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return r.stdout.strip() if r.returncode == 0 else None


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    draft = " ".join(open(DRAFT, encoding="utf-8").read().split())

    # ---- 1. every behavioural claim, against the wheel a reader would install ------------------
    ck(os.path.exists(VENV), "the clean-install venv exists", VENV)
    probe = (
        "import json,tempfile,os,inspeximus\n"
        "from inspeximus import Inspeximus\n"
        "m=Inspeximus(path=os.path.join(tempfile.mkdtemp(),'s.json'))\n"
        "m.remember('x',key='runbook.md')\n"
        "c=m.identifier_contract(); w0=m.witness(); w1=m.witness(bind_sources=True)\n"
        "print(json.dumps({'v':inspeximus.__version__,'ic':c['commitment_scope'],"
        "'ic_v':c['verifies'],'ic_n':c['does_not_verify'],'w0':w0['commitment_scope'],"
        "'w1':w1['commitment_scope'],"
        "'narrow':Inspeximus.commitment_supports(c,'observation_current'),"
        "'undecl':Inspeximus.commitment_supports({'population_commitment':'x'},'headroom')['reason'],"
        "'limits':' '.join(c['limits'])}))")
    out = subprocess.run([VENV, "-c", probe], capture_output=True, text=True, encoding="utf-8")
    ck(out.returncode == 0, "the installed wheel runs the probe", (out.stderr or "")[:120])
    if out.returncode != 0:
        for ok, l, d in rows:
            print(f"  {'PASS' if ok else 'FAIL'}  {l}   [{d}]")
        return 1
    r = json.loads(out.stdout.strip().splitlines()[-1])

    ck(r["v"] == "2.19.0", "the installed version is the one the reply names", r["v"])
    ck(r["ic"] == ["key"] and '["key"]' in draft.replace("'", '"'),
       "identifier_contract scope matches the reply", str(r["ic"]))
    ck(r["w0"] == ["store"], "bare witness scope matches the reply", str(r["w0"]))
    ck(r["w1"] == ["store", "source_digest"], "bound witness scope matches the reply", str(r["w1"]))
    ck(set(r["w1"]) > set(r["w0"]) and "grows" in draft,
       "the reply's word 'grows' is true of the shipped artifacts")
    ck(r["narrow"]["sufficient"] is False and r["narrow"]["reason"] == "scope_too_narrow"
       and "scope_too_narrow" in draft, "the quoted refusal reproduces", str(r["narrow"]["missing"]))
    ck(r["narrow"]["missing"] == ["source_digest"] and "source_digest" in draft,
       "the missing field the reply prints is the one returned")
    ck(r["undecl"] == "undeclared_scope" and "undeclared_scope" in draft,
       "fail-closed on an undeclared scope reproduces")

    # ---- 2. the quotation from OUR OWN limits, which is the reply's opening move ---------------
    quote = "would hold a commitment over the wrong set, and it would verify clean every time"
    ck(quote in r["limits"], "the limits sentence the reply quotes is in the SHIPPED wheel")
    ck(quote.replace(", and it", ", **and it").replace("every time", "every time**") in draft
       or quote in draft, "and the reply quotes it verbatim")

    # ---- 3. the attestation line, against the endpoint that actually answers -------------------
    url = ("https://pypi.org/integrity/inspeximus/2.19.0/"
           "inspeximus-2.19.0-py3-none-any.whl/provenance")
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            prov = json.load(resp)
        b = prov.get("attestation_bundles") or []
        pub = (b[0].get("publisher") if b else {}) or {}
        ck(len(b) >= 1 and pub.get("repository") == "DanceNitra/inspeximus"
           and pub.get("workflow") == "release.yml",
           "the trusted-publisher attestation the reply claims really exists", str(pub))
    except Exception as e:
        ck(False, "fetched the attestation", f"{type(e).__name__}: {e}"[:90])
    ck("trusted-publisher attestation" in draft, "the reply makes that claim (so it must be true)")

    # ---- 4. the cross-repo claim ----------------------------------------------------------------
    pr = gh("api", "repos/DanceNitra/ramr/pulls/3", "--jq", ".state")
    ck(pr == "open", "ramr#3 is open, as the reply says", str(pr))
    files = gh("api", "repos/DanceNitra/ramr/pulls/3/files", "--jq", ".[].filename") or ""
    ck("integrity/receipt_binding.py" in files, "and it contains the cell the reply points at")
    ck("S3" in draft and "_unscoped" in draft, "the reply names the scenario and the control")

    # ---- 5. the room ----------------------------------------------------------------------------
    # PAGINATE. Without --paginate this returned 4288554057, the last id on the FIRST page of 101
    # comments, and the freshness check compared against a comment from months ago. The gate would
    # have reported "nothing newer" while today's message sat unread on the last page.
    ids = (gh("api", "--paginate", "repos/anthropics/claude-code/issues/34556/comments",
              "--jq", ".[] | .id") or "").split()
    ck(len(ids) > 60, "read the WHOLE thread, not page one", f"{len(ids)} comments")
    # BOUND TO CONTENT, NOT TO AN ID. A hardcoded id has to be edited every time someone posts,
    # and editing a gate to make it pass is how it stops being one. This asserts that the DRAFT
    # engages with the distinctive terms of whatever the newest comment actually says -- so a new
    # comment on a NEW topic fails it, while the same conversation continuing does not.
    newest = gh("api", f"repos/anthropics/claude-code/issues/comments/{ids[-1]}",
                "--jq", ".body") or ""
    terms = [t for t in ("transition continuity", "generation", "commitment_scope", "verifies",
                         "evidentiary sufficiency", "ramr#3", "S5")
             if t.lower() in newest.lower()]
    ck(len(terms) >= 3, "the newest comment is on the topic this reply answers",
       f"id {ids[-1]}: {terms}")
    hit = [t for t in terms if t.lower() in draft.lower()]
    ck(len(hit) >= 3, "and the reply engages its distinctive terms", f"{hit}")

    # THE ISSUE IS CLOSED, and that is not automatically a stop. It was closed as `completed` on
    # 2026-08-17; it is NOT locked; and both correspondents have posted into it since -- Stratogain
    # on 20 August, @safal207 today. Our own two replies of 19 August also landed after closure.
    # So the condition is not "open" but "still a live venue": unlocked, and someone other than us
    # has spoken there after it closed. A closed-and-quiet thread would fail this.
    meta = gh("api", "repos/anthropics/claude-code/issues/34556",
              "--jq", "[.state, (.locked|tostring), .closed_at] | join(\" \")") or ""
    state, locked, closed_at = (meta.split() + ["", "", ""])[:3]
    ck(locked == "false", "the thread is not locked", f"state={state} locked={locked}")
    others_after = gh("api", "--paginate",
                      "repos/anthropics/claude-code/issues/34556/comments",
                      "--jq", "[.[] | select(.user.login != \"DanceNitra\") "
                              "| select(.created_at > \"%s\") | .user.login] | unique | join(\",\")"
                              % closed_at) or ""
    ck(len(others_after.split(",")) >= 2 and others_after.strip(),
       "others are still conversing there AFTER it closed -- so it is a live venue",
       f"closed {closed_at}; since then: {others_after}")
    ck("closed" in draft.lower(),
       "the reply itself acknowledges the thread is closed rather than pretending otherwise")

    for ok, l, d in rows:
        print(f"  {'PASS' if ok else 'FAIL'}  {l}" + (f"   [{d}]" if d else ""))
    p = sum(1 for ok, _, _ in rows if ok)
    print(f"\n{p}/{len(rows)} checks pass")
    return 0 if p == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
