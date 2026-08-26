"""RECHECK THE FIGURES in follow-up about an absent key reading as a negative answer.

Every claim here is about a THIRD PARTY's API, so every one is re-fetched live rather than quoted
from the session that produced it. The message's whole point is that a wrong endpoint gives a
confident wrong answer -- publishing it on an unverified reading of a different endpoint would be
the joke landing on us for the second time in one thread.

Run:  python probes/gate_34556_absent_vs_negative.py

THIS FILE IS NOT THE GATE. It recomputes figures against receipts, which is ONE check
inside VALIDATE. The gate is the SKILLS: verify-claims, stress-claim, humanizer, and
storm when the claim rests on literature. Owner, 2026-08-26, after I called a file like
this one "the gate" three times in a day: "ZAPIS SI TO NATVRDO A TEN TVOJ SKRIPT DAJ DO
HOVEN." tools/send_approved.py now refuses to publish without a receipt from each skill,
bound to the draft's bytes, so this file cannot stand in for them any more.
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DRAFT = os.path.join(ROOT, "agora_output", "drafts", "reply_ramr3_absent_vs_negative.md")
rows: list[tuple[bool, str, str]] = []


def ck(ok, label, detail=""):
    rows.append((bool(ok), label, detail))


def get(url, accept=None):
    req = urllib.request.Request(url, headers={"Accept": accept} if accept else {})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


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

    # ---- 1. the JSON API really has NO provenance key, for us and for others ------------------
    for pkg, ver, attested in (("inspeximus", "2.19.0", True), ("sigstore", "3.6.1", True),
                               ("pydantic", "2.11.7", True)):
        d = get(f"https://pypi.org/pypi/{pkg}/{ver}/json")
        whl = [u for u in d["urls"] if u["filename"].endswith(".whl")][0]
        ck("provenance" not in whl,
           f"JSON API carries no `provenance` key for {pkg} {ver}", str(sorted(whl)[:3]))
        if attested:
            b = get(f"https://pypi.org/integrity/{pkg}/{ver}/{whl['filename']}/provenance")
            ck(len(b.get("attestation_bundles") or []) >= 1,
               f"  yet {pkg} {ver} IS attested via /integrity -- so the key's absence is not a 'no'")

    # ---- 2. the Simple API DOES carry it, as a URL --------------------------------------------
    s = get("https://pypi.org/simple/inspeximus/",
            accept="application/vnd.pypi.simple.v1+json")
    f = [x for x in s["files"] if x["filename"] == "inspeximus-2.19.0-py3-none-any.whl"][0]
    ck("provenance" in f, "the Simple API DOES carry `provenance`")
    ck(isinstance(f.get("provenance"), str) and f["provenance"].startswith("https://pypi.org/integrity/"),
       "and it is a URL into the integrity endpoint, exactly as the draft says", str(f.get("provenance"))[:70])
    ck("vnd.pypi.simple.v1+json" in draft and "/integrity/" in draft,
       "the draft names both surfaces correctly")

    # ---- 3. our own attestation, the claim the draft ends on ----------------------------------
    b = get("https://pypi.org/integrity/inspeximus/2.19.0/"
            "inspeximus-2.19.0-py3-none-any.whl/provenance")
    pub = ((b.get("attestation_bundles") or [{}])[0].get("publisher") or {})
    ck(pub.get("repository") == "DanceNitra/inspeximus" and pub.get("workflow") == "release.yml",
       "the attestation the draft reaffirms really is there", str(pub))

    # ---- 4. the draft must NOT accuse PyPI of a defect ----------------------------------------
    for bad in ("bug in pypi", "pypi bug", "defect in pypi", "pypi is wrong", "inconsistency in pypi"):
        ck(bad not in draft.lower(), f"the draft does not accuse PyPI: '{bad}'")
    # PROPERTY, not spelling. This asked for the exact phrase "PyPI is entirely consistent" and the
    # humanizer pass cut "entirely" -- so the check failed on a draft that says the right thing.
    absolves = any(p in draft for p in ("PyPI is consistent", "PyPI is entirely consistent"))
    owns = any(p in draft for p in ("I asked an endpoint a question it never offered to answer",
                                    "the error was ours", "I nearly wrote the weaker sentence"))
    ck(absolves and owns,
       "it says plainly that PyPI is consistent and that the mistake was ours",
       f"absolves={absolves} owns={owns}")
    ck("nearly wrote the weaker sentence" in draft or "one `.get()` from being retracted" in draft,
       "the draft owns the near-miss rather than presenting it as a discovery")

    # ---- 5. the three-state claim matches what we actually ship --------------------------------
    venv = os.path.join(os.environ.get("TEMP", "/tmp"), "claude", "C--Users-Danculus-agora",
                        "e6f8e2c8-b4c1-4269-a886-f10b2cd62521", "scratchpad", "v219",
                        "Scripts", "python.exe")
    probe = ("import json,tempfile,os\nfrom inspeximus import Inspeximus\n"
             "m=Inspeximus(path=os.path.join(tempfile.mkdtemp(),'s.json'));m.remember('x',key='k')\n"
             "c=m.identifier_contract()\n"
             "print(json.dumps([Inspeximus.commitment_supports({},'headroom')['reason'],"
             "Inspeximus.commitment_supports(c,'observation_current')['reason'],"
             "Inspeximus.commitment_supports(c,'headroom')['reason']]))")
    out = subprocess.run([venv, "-c", probe], capture_output=True, text=True, encoding="utf-8")
    ck(out.returncode == 0, "the released wheel answers", (out.stderr or "")[:100])
    if out.returncode == 0:
        got = json.loads(out.stdout.strip().splitlines()[-1])
        ck(got == ["undeclared_scope", "scope_too_narrow", "covered"],
           "the three states the draft prints are the three the wheel returns", str(got))
        for st in got:
            ck(st in draft, f"  and the draft names `{st}`")

    # ---- 6. the room ----------------------------------------------------------------------------
    # VENUE. This moved out of anthropics/claude-code#34556 and into the repo, because a third party
    # there said the thread had turned into essays and he was right. So the room check is now about
    # ramr#3 -- and about having actually done what was promised in that reply rather than said it.
    st = gh("api", "repos/DanceNitra/ramr/pulls/3", "--jq", ".state")
    ck(st == "open", "ramr#3 is open", str(st))
    disc = gh("api", "repos/anthropics/claude-code/issues/comments/5373388210", "--jq", ".body") or ""
    ck("ramr#3" in disc and "keep it there" in disc,
       "we publicly said the detail moves to the repo -- this is that promise being kept")
    ck(len(open(DRAFT, encoding="utf-8").read()) < 2000,
       "and it is short, which was the other half of his complaint",
       f"{len(open(DRAFT, encoding='utf-8').read())} chars")

    for ok, l, d in rows:
        print(f"  {'PASS' if ok else 'FAIL'}  {l}" + (f"   [{d}]" if d else ""))
    p = sum(1 for ok, _, _ in rows if ok)
    print(f"\n{p}/{len(rows)} checks pass")
    return 0 if p == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
