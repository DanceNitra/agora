"""Re-derive every checkable statement in the memex#233 reply from its primary source.

THIS IS ONE CHECK INSIDE VALIDATE. It is not the gate. The gate is the skills.

WHAT THIS ONE HAS TO GET RIGHT. The draft describes somebody else's dataclass, quotes a commit, and
makes a claim about our own shipped code. All three are checkable, and the third is the one most
likely to be wrong from memory: our keyed branch is a plain equality test only when the value is
stored on BOTH records, and falls back to a text clash otherwise. An earlier draft said "an equality
test on the value field" without that condition.

CONTROLS, each able to fail:
  * HIS DATACLASS IS FETCHED, NOT RECALLED. The field list is read from his master branch, and the
    absence of a value field is asserted with a control that would catch a fetch returning nothing.
  * THE COMMIT GAP IS COMPUTED from both timestamps rather than restated.
  * OUR OWN CODE IS READ FROM THE INSTALLED SOURCE, and the fallback branch is asserted to exist, so
    a draft that promises unconditional equality fails here.
  * A CLAIM WE DECLINE TO MAKE IS ASSERTED ABSENT: the draft must not say his kernel needs a key,
    because it has one.
"""
from __future__ import annotations

import datetime as dt
import io
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.stdout.reconfigure(line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DRAFT = os.path.join(ROOT, "drafts", "memex233_sign_derivation.md")
OUT = os.path.join(HERE, "recheck_figures_memex233_sign.result.json")
CORE = os.path.join(os.path.expanduser("~"), "inspeximus-repo", "inspeximus", "core.py")
LCORE = ("https://raw.githubusercontent.com/Lantern-svg/lantern/master/"
         "lantern-babel-codex-bridge/src/lantern/core.py")


def refuse(why: str):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why}, io.open(OUT, "w", encoding="utf-8"), indent=1)
    raise SystemExit(2)


def gh(path: str, jq: str) -> str:
    r = subprocess.run(["gh", "api", path, "--paginate", "--jq", jq],
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        refuse("could not read %s: %s" % (path, (r.stderr or "")[:200]))
    return r.stdout


def fetch(url: str) -> str:
    try:
        with urllib.request.urlopen(urllib.request.Request(
                url, headers={"User-Agent": "agora-probe"}), timeout=90) as r:
            return r.read().decode("utf-8", "replace")
    except Exception as e:
        refuse("could not fetch %s: %r" % (url, e))


def main() -> int:
    for p, what in ((DRAFT, "draft"), (CORE, "our own core.py")):
        if not os.path.isfile(p):
            refuse("%s missing: %s" % (what, p))
    draft = io.open(DRAFT, encoding="utf-8").read()
    flat = " ".join(draft.split())
    ours = io.open(CORE, encoding="utf-8").read()
    his = fetch(LCORE)
    if len(his) < 5000:
        refuse("his core.py came back too small to be the real file (%d bytes)" % len(his))

    checks = []

    def chk(claim, phrase, ok, source):
        present = " ".join(phrase.split()) in flat if phrase else True
        checks.append({"claim": claim, "phrase_in_draft": present, "verified": bool(ok),
                       "source": source})
        print("  %-5s %-54s %s" % ("OK" if (present and ok) else "FAIL", claim, source))

    # --- his dataclass, fetched from master ---
    m = re.search(r"@dataclass\s*\nclass Evidence\b(.*?)(?=\n@dataclass|\nclass )", his, re.S)
    if not m:
        refuse("the Evidence dataclass was not found in his master core.py")
    fields = re.findall(r"^\s{4}([a-z_]+)\s*:", m.group(1), re.M)
    chk("his Evidence fields are the ones the draft lists",
        "`concept, observation_id, weight, sign, step, owner_instance, id`",
        fields == ["concept", "observation_id", "weight", "sign", "step", "owner_instance", "id"],
        "fetched from master: %s" % ", ".join(fields))
    chk("it carries no value field, so the suggestion is not already shipped",
        "What it has no field for is the value",
        not any(f in fields for f in ("value", "object", "object_value", "val")),
        "no value-shaped field among %d fields" % len(fields))
    chk("CONTROL: the field scan really found fields", "", len(fields) >= 5,
        "%d fields parsed, so an empty parse cannot pass the check above" % len(fields))
    chk("concept is already the key, so we do not ask him to add one",
        "`concept` is already the key",
        "concept" in fields and "add a key" not in draft.lower(),
        "concept is present and the draft asks only for a value")

    # --- the commit, computed rather than restated ---
    f = "%Y-%m-%dT%H:%M:%SZ"
    meta = json.loads(gh("repos/Lantern-svg/lantern/commits/bf4b32d7",
                         "{d: .commit.author.date, f: [.files[].filename]}"))
    times = json.loads(gh("repos/JasperHG90/memex/issues/233/comments",
                          '[.[] | select(.user.login=="Lantern-svg") | .created_at]'))
    gap = (dt.datetime.strptime(meta["d"], f) - dt.datetime.strptime(sorted(times)[-1], f)).total_seconds()
    chk("the gap really is eight seconds", "eight seconds after your comment", gap == 8,
        "comment %s, commit %s, gap %.0fs" % (sorted(times)[-1], meta["d"], gap))
    chk("the file path is the one named", "`lantern-babel-codex-bridge/ARCHITECTURE.md`",
        meta["f"] == ["lantern-babel-codex-bridge/ARCHITECTURE.md"],
        "the commit touched %s" % ", ".join(meta["f"]))
    arch = fetch("https://raw.githubusercontent.com/Lantern-svg/lantern/master/"
                 "lantern-babel-codex-bridge/ARCHITECTURE.md")
    chk("the old shape is still readable in the committed file",
        "keeps the wrong version readable in the note above the corrected block",
        "belief_a" in arch and "Corrected 2026-09-01" in arch,
        "the live file carries both the correction note and the old field names")

    # --- our own code, read from the installed source ---
    # Slice the METHOD, not a guessed number of characters. A fixed window silently excluded
    # the embedding call and the probe crashed instead of reporting, which is a refusal
    # wearing the clothes of a bug.
    i = ours.index("def check_conflict(")
    nxt = ours.find(chr(10) + "    def ", i + 10)
    body = ours[i:nxt if nxt > 0 else i + 12000]
    for needle in ('hits.append((r, "keyed_value_change"))', "self._qvec(text)"):
        if needle not in body:
            refuse("check_conflict no longer contains %r, so the draft describes code that "
                   "has changed under it" % needle)
    keyed = body.index('hits.append((r, "keyed_value_change"))')
    embed = body.index("self._qvec(text)")
    chk("the conflict kind is spelled the way the draft spells it",
        "conflict kind `keyed_value_change`", '"keyed_value_change"' in body,
        "the literal appears in check_conflict")
    chk("the keyed branch runs before any embedding",
        "the keyed branch runs before any embedding", keyed < embed,
        "keyed append at +%d, first _qvec at +%d" % (keyed, embed))
    chk("equality only when the value is on both records",
        "when the value is stored on both records it is a plain equality test",
        'if object is not None and r.get("object") is not None:' in body
        and 'conflict = (r["object"] != object)' in body,
        "the guard and the equality are both present")
    chk("and it falls back to a deterministic clash, not a judge",
        "when either side lacks it, it falls back to a deterministic text clash rather than to a judge",
        'conflict = inc(text, r["text"])' in body
        and "inc = incompatible or (lambda a, b: _value_clash(a, b) or _negation_clash(a, b))" in body,
        "the fallback calls the deterministic default")
    chk("the callback name is right", "`incompatible(a, b)` callback",
        "incompatible=None" in body, "check_conflict takes incompatible=None")
    chk("CONTROL: a wrong kind string is absent from our code", "",
        '"keyed_object_change"' not in ours and '"value_changed"' not in ours,
        "near-miss kind names do not appear, so the match is selective")

    # --- claims the draft must NOT make ---
    for claim, needle in (("no claim that our design is better", "better than"),
                          ("no claim he should build it", "you should"),
                          ("no novelty claim", "novel")):
        chk(claim, "", needle not in draft.lower(), "absent from the draft")
    chk("the textbook framing is stated", "It is the ordinary database move, not a new idea", True,
        "the draft credits the mechanism rather than claiming it")
    chk("the limit is stated with the suggestion", "This narrows the gap; it does not close it",
        True, "stated inline")
    chk("AI assistance is disclosed", "*Written with AI assistance.*", True, "owner rule, permanent")
    chk("pure ASCII apart from nothing, and no dash gh can mangle", "",
        chr(8212) not in draft and chr(8211) not in draft, "no em dash or en dash")

    bad = [c for c in checks if not (c["phrase_in_draft"] and c["verified"])]
    json.dump({"probe": os.path.basename(__file__),
               "when_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "draft": "drafts/memex233_sign_derivation.md",
               "draft_bytes": len(draft.encode("utf-8")),
               "his_evidence_fields": fields, "commit_gap_seconds": gap,
               "checks": len(checks), "failed": len(bad), "rows": checks,
               "controls": {"his_dataclass_fetched_not_recalled": True,
                            "commit_gap_computed": True,
                            "our_fallback_branch_asserted": True}},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("\n%d checks, %d failed." % (len(checks), len(bad)))
    for c in bad:
        print("  FAILED: %s | phrase: %s | verified: %s"
              % (c["claim"], c["phrase_in_draft"], c["verified"]))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
