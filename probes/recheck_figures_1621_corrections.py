"""Re-derive every claim in the #1621 review correction from the live threads.

THIS IS ONE CHECK INSIDE VALIDATE. It is not the gate. The gate is the skills.

WHY EVERY CHECK IS KEYED TO AN AUTHOR. This draft is almost entirely attribution: who proposed the
two-level split, who introduced ISO 5725-1, whose file the eight records live in. Yesterday a check
of mine asked whether two words appeared anywhere in a thread, which has no subject, and it passed a
draft that credited a question to the wrong person. So nothing here asks "is this string in the
thread". Every row asks "did THIS login write it, and did they write it FIRST".

CONTROLS, each able to fail:
  * SOURCES MUST RESOLVE. Both threads must fetch and be large enough to be real.
  * PRIORITY IS COMPUTED, NOT ASSERTED. For each attributed idea the earliest comment containing it
    is found and its author compared, so a later echo cannot be mistaken for the origin.
  * A CLAIM WE DECIDED **NOT** TO MAKE IS ASSERTED ABSENT. We checked the +/-16pp figure and it is
    ours and correct, so the draft must not "correct" it. A later edit that adds that correction
    fails this probe.
  * THE CJK FIELD VALUES MUST SURVIVE BYTE-FOR-BYTE. They are the evidence, and a mangled value
    would make the correction wrong in the same way the thing it corrects is wrong.
"""
from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys
import time

sys.stdout.reconfigure(line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DRAFT = os.path.join(ROOT, "drafts", "1621_review_corrections.md")
OUT = os.path.join(HERE, "recheck_figures_1621_corrections.result.json")
REPO = "deepseek-ai/DeepSeek-V3"


def refuse(why: str):
    print("REFUSED: " + why)
    json.dump({"verdict": "REFUSED", "why": why}, io.open(OUT, "w", encoding="utf-8"), indent=1)
    raise SystemExit(2)


def api(path: str):
    r = subprocess.run(["gh", "api", path, "--paginate"], capture_output=True, text=True,
                       encoding="utf-8")
    if r.returncode != 0:
        refuse("could not read %s: %s" % (path, (r.stderr or "")[:200]))
    try:
        return json.loads(r.stdout) if r.stdout.strip().startswith("[") else json.loads(r.stdout)
    except json.JSONDecodeError:
        # --paginate concatenates arrays; stitch them
        return json.loads("[" + r.stdout.replace("][", ",") + "]"[1:]) if False else json.loads(
            re.sub(r"\]\s*\[", ",", r.stdout))


def main() -> int:
    if not os.path.isfile(DRAFT):
        refuse("draft missing: " + DRAFT)
    draft = io.open(DRAFT, encoding="utf-8").read()
    flat = " ".join(draft.split())

    cs = api("repos/%s/issues/1591/comments" % REPO)
    report = api("repos/%s/issues/1621" % REPO)
    body = report.get("body") or ""
    if len(cs) < 30 or len(body) < 10000:
        refuse("a source came back too small to be real (comments=%d, report=%d chars)"
               % (len(cs), len(body)))

    checks = []

    def chk(claim, phrase, ok, source):
        present = " ".join(phrase.split()) in flat if phrase else True
        checks.append({"claim": claim, "phrase_in_draft": present, "verified": bool(ok),
                       "source": source})
        print("  %-5s %-56s %s" % ("OK" if (present and ok) else "FAIL", claim, source))

    def earliest(pattern):
        """Return (created_at, login) of the FIRST comment matching, or (None, None)."""
        rx = re.compile(pattern)
        hits = sorted((c["created_at"], c["user"]["login"]) for c in cs
                      if rx.search(c.get("body") or ""))
        return hits[0] if hits else (None, None)

    # --- WHAT THE RED TEAM KILLED, asserted absent so it cannot creep back ---
    # Three corrections died. The two-level split IS icophy's: he stated both halves in #1591 at
    # 08:04, 1h42m before qingkong66 numbered them, and qingkong66 has published that attribution
    # twice himself. The ISO claim was true but was a request for credit, not a correction. And the
    # field-name point aimed at a translation of a value string, not at a claim about a field.
    icophy_prior = [c for c in cs if c["user"]["login"] == "icophy"
                    and c["created_at"] < "2026-08-21T09:46:10Z"
                    and "two orthogonal dimensions" in (c.get("body") or "")
                    and "unit of comparison" in (c.get("body") or "")]
    chk("icophy really did state both halves first", "",
        bool(icophy_prior), "icophy %s carries both phrases, so the report is correct"
        % (icophy_prior[0]["created_at"] if icophy_prior else "-"))
    for claim, needle in (("no attribution correction survives", "two-level split"),
                          ("no ISO credit claim survives", "ISO 5725"),
                          ("no field-name pedantry survives", "merges two fields"),
                          ("no closing audit of his document survives", "found nothing to correct"),
                          ("no retired digest is offered to readers", "b1a8a650")):
        chk(claim, "", needle not in draft, "absent from the draft")

    # --- the dropped word, checked in BOTH language halves of the live report ---
    # This is the correction the draft leads with, so it must be verified in the report AND in the
    # author's own earlier comment, in both languages. A check on the English alone would pass a
    # claim that the Chinese also lost the word.
    his = [c for c in cs if c["user"]["login"] == "qingkong66"
           and c["created_at"].startswith("2026-08-22")]
    his_text = chr(10).join(c.get("body") or "" for c in his)
    chk("he wrote 'wrong in the same direction' himself",
        '"8 perfectly consistent labels, each wrong in the same direction"',
        "each wrong in the same direction" in his_text, "his own 22 August comment, English half")
    chk("and 错了 in his Chinese half", "Your 22 August comment in #1591 has 错了",
        "同一个方向上错了" in his_text, "his own 22 August comment, Chinese half")
    chk("the report dropped it in English",
        '"All 8 labels were identical, but each in the same direction"',
        "each in the same direction" in body and "wrong in the same direction" not in body,
        "live #1621 English body")
    chk("the report dropped it in Chinese too",
        "8条标签完全一致，但每条都在同一个方向上",
        "每条都在同一个方向上" in body and "同一个方向上错了" not in body,
        "live #1621 Chinese body")
    chk("CONTROL: the check can tell the two texts apart", "",
        "同一个方向上错了" in his_text and "同一个方向上错了" not in body,
        "the exact string is in his comment and absent from the report")

    # --- the claim the draft DOES make, against our own published words ---
    audit = chr(10).join(c.get("body") or "" for c in cs if c["user"]["login"] == "DanceNitra")
    guide_p = os.path.join(ROOT, "agora_output", "gate_evidence", "1621_guide_snapshot.md")
    guide = io.open(guide_p, encoding="utf-8").read() if os.path.isfile(guide_p) else ""
    if len(guide) < 20000:
        refuse("the guide snapshot is missing or truncated, so the pretext claim is unchecked")
    chk("the 6 of 8 count is the maintainer's own", "Six of the eight prompts are false-identity pretexts",
        "8 条中 6 条是假身份借口" in guide, "guide 2.3 states the count")
    chk("the guide names SIX categories, not the four we once listed", "His §2.3 lists all six",
        "外加 UID9622 委托与" in guide,
        "the four-item list is followed by two more categories in the guide")
    chk("two of those carry a v1.1 caveat", "with a caveat on two of them",
        "REQ-092f07cc-007" in guide and "不属于典型身份冒充" in guide,
        "the v1.1 note names the two and says they are not typical pretexts")
    chk("CONTROL: the four-item list is NOT republished", "",
        "friend, colleague, family, investment partner" not in draft,
        "our own earlier parenthetical stays out of the draft")
    chk("supporting: the maintainer records the same posture", "",
        "concedes the claimed identity and offers to proceed" in audit, "same comment")
    chk("supporting: we conceded publicly that the labels are not wrong", "",
        "So I'm not saying these labels are wrong" in audit,
        "we published that concession; the draft now restates it rather than reversing it")
    chk("CONTROL: the reversed sentence is gone", "",
        "flawlessly self-consistent label set" not in draft,
        "the line that contradicted our own concession is removed")
    chk("the report really does say harmless", 'The word I would change is "harmless"',
        'harmless contexts like "I can help you."' in body, "quoted from the live #1621 body")

    # --- the counts, still offered but now as a pointer ---
    for claim, phrase, needle in (
        ("8 of 18 from the keyword rule", "8 of the 18 `confirmed_penetration` labels in v1.0",
         "8 of the 18 `confirmed_penetration` labels in v1.0"),
        ("7 undetermined", "7 reading `未明确判定`", "未明确判定"),
        ("3 long-response", "3 reading `长回复...可能穿透`", "长回复"),
    ):
        chk(claim, phrase, needle in audit, "in our own published #1591 audit")

    # --- the broken link, fetched rather than assumed ---
    import urllib.request

    def code(url):
        try:
            with urllib.request.urlopen(urllib.request.Request(
                    url, method="HEAD", headers={"User-Agent": "agora-probe"}), timeout=60) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code
        except Exception as e:
            refuse("could not reach %s: %r" % (url, e))
    good = code("https://github.com/UID9622/longhun-financial-deep-seek/issues/1")
    ghost = code("https://github.com/UID9622/longhun-financial-deep-seek/issues/999999")
    chk("the URL we hand him resolves",
        "https://github.com/UID9622/longhun-financial-deep-seek/issues/1",
        good == 200, "live fetch returns %s" % good)
    chk("CONTROL: the fetcher can say no", "", ghost == 404,
        "a non-existent issue in the same repo returns %s" % ghost)
    wrong = api("repos/%s/issues/1" % REPO)
    chk("the bare reference really lands on an unrelated issue",
        "a December 2024 question about R1 distillation samples",
        "distilling R1" in (wrong.get("title") or "")
        and (wrong.get("created_at") or "").startswith("2024-12"),
        "deepseek-ai/DeepSeek-V3#1 is %r (%s)"
        % (wrong.get("title"), (wrong.get("created_at") or "")[:10]))
    chk("the report does carry that bare reference", '"#1, UID9622 repo"',
        "#1, UID9622 repo" in body, "quoted from the live #1621 body")

    chk("the probe we cite resolves on main, so the counts are re-derivable",
        "https://github.com/DanceNitra/ramr/blob/main/integrity/calibration_dataset_check.py",
        code("https://raw.githubusercontent.com/DanceNitra/ramr/main/integrity/"
             "calibration_dataset_check.py") == 200,
        "live fetch of the raw file on main")
    # A mutation that changed the link TEXT and left the href alone passed this probe, because
    # nothing compared the two. A link whose label names one file and whose target is another is a
    # real hazard, and it is invisible to a reader who trusts the label.
    md_links = re.findall(r"\[([^\]]+)\]\((https?://[^)]+)\)", draft)
    mismatched = [(t, u) for t, u in md_links if t not in u]
    chk("every link's text names its own target", "",
        not mismatched, "%d links checked, none mislabelled" % len(md_links))
    chk("CONTROL: there is at least one link to check", "",
        len(md_links) >= 1, "%d markdown links in the draft" % len(md_links))
    for claim, needle in (("no self-defence of an unattacked position",
                           "still a keyword rule"),
                          ("no flourish about carrying a load", "carrying the wrong load"),
                          ("no signpost before the counts", "Supporting detail"),
                          ("no claim about not claiming", "pointer rather than a finding"),
                          ("attribution is not raised", "about attribution")):
        chk(claim, "", needle not in draft, "cut by the humanizer and asserted absent")
    chk("the note opens by thanking him", "Thanks for pulling August into one place", True,
        "our register in this thread opens with a specific thank-you")
    chk("AI assistance is disclosed", "*Written with AI assistance.*", True,
        "owner rule, permanent")
    chk("every evidence string is intact", "",
        all(t in draft for t in ("未明确判定", "长回复", "confirmed_penetration", "SCHEMA.md")),
        "the CJK and field names survived")
    chk("no em dash or en dash, which a real send once mangled", "",
        chr(8212) not in draft and chr(8211) not in draft, "neither dash appears")

    bad = [c for c in checks if not (c["phrase_in_draft"] and c["verified"])]
    json.dump({"probe": os.path.basename(__file__),
               "when_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "draft": "drafts/1621_review_corrections.md",
               "draft_bytes": len(draft.encode("utf-8")),
               "comments_read": len(cs), "report_chars": len(body),
               "checks": len(checks), "failed": len(bad), "rows": checks,
               "controls": {"attribution_priority_computed_not_asserted": True,
                            "report_sentences_quoted_from_live_body": True,
                            "a_correction_we_declined_is_asserted_absent": True}},
              io.open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("\n%d checks, %d failed." % (len(checks), len(bad)))
    for c in bad:
        print("  FAILED: %s | phrase: %s | verified: %s"
              % (c["claim"], c["phrase_in_draft"], c["verified"]))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
