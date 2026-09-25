"""The pure parts of tools/seal/seal_draft.py, each with a control that must fail.

Fixtures are the real ones from 2026-09-24: the agmi PR receipt (log entry 6, whose statement the log
holds by sha256), and the footer of tech4biz-yasha/agmi#4 as it was sent.
"""
import hashlib
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools", "seal"))
import seal_draft as sd  # noqa: E402

# ---------------------------------------------------------------- statement

AGMI_INPUTS = [
    "7d40a7f5f3117bc6e2a130e55030b88cdc8a90ef73bb1ae8796db976e91f6ba5",
    "941c20b9b20b2b8e67a2275800cb90e79dae247691b6b79b5f5af0e2bed638e8",
    "941c20b9b20b2b8e67a2275800cb90e79dae247691b6b79b5f5af0e2bed638e8",
    "c7ae009ba04dfa20ecea8e3937beaf1d6be97f3c337544f2c2ba95b3ad13302d",
    "13dc38ce64811aaf39016f75a7eec57eda866827676995903d03e92c85d8ef6c",
    "240b4ad1aabae5ba4d57390793d247312c6d56ec95135fe114a071fd0ac3527f",
    "eb6838bd668c2dd312917d08693397d445d2f3dd082d07236023a0116cb63c93",
    "1d4a6d900eb1806303350153702808e4db552adedae7867c2e8b63dd63821579",
    "ad57ecb39753a9c3c5e2f1437ec88de860ff4531edf4885de28b29b05356ec19",
    "26180214eb8b9da9c6d7a2f09e07e865fa8e3440e60e07c76d80139fa622a3af"
]
AGMI_CLAIMS = ['all_vulnerable', 'args_default_off', 'base', 'bleed_safe', 'ci_fork', 'ci_main', 'default_identical', 'five_tests', 'key_row', 'keyring_before_sign', 'label_row']
AGMI_BROKEN = ['ci_fork', 'default_identical', 'default_identical', 'label_row', 'key_row', 'ci_fork', 'ci_main', 'base', 'args_default_off', 'five_tests', 'keyring_before_sign']
# sha256 of 7d40a7f5f3117bc6.log-statement.json, as recorded in log entry 6's payload.
AGMI_STATEMENT_SHA = "c73c4e8200c56dc9eb260c7f785a0ba52b8aff47b613f826e4b7b4c8258c5e66"


def agmi_receipt():
    return {
        "draft_sha256": "7d40a7f5f3117bc6e2a130e55030b88cdc8a90ef73bb1ae8796db976e91f6ba5",
        "script_sha256": "14cd91391d1bb59f9dcc18dab4d67bdcaec042c946927ea6f02df574078c3e46",
        "stdout_sha256": "112ab15f5c722c74fc3782a6e874fba24869a115d11388fa2d59c0949ab39914",
        "recorded_utc": "2026-09-24T21:22:08Z",
        "skill": "verify",
        "inputs": [{"sha256": s} for s in AGMI_INPUTS],
        "claims": {k: {"verdict": "PASS", "text": "t"} for k in AGMI_CLAIMS},
        "mutations": [{"claims_broken": [b]} for b in AGMI_BROKEN],
    }


def test_statement_is_byte_identical_to_the_logged_one():
    assert hashlib.sha256(sd.build_statement(agmi_receipt())).hexdigest() == AGMI_STATEMENT_SHA


def test_statement_control_a_mutation_that_broke_nothing_changes_the_bytes():
    rec = agmi_receipt()
    rec["mutations"][3]["claims_broken"] = []
    assert hashlib.sha256(sd.build_statement(rec)).hexdigest() != AGMI_STATEMENT_SHA


def test_statement_control_input_order_matters():
    rec = agmi_receipt()
    rec["inputs"] = rec["inputs"][::-1]
    assert hashlib.sha256(sd.build_statement(rec)).hexdigest() != AGMI_STATEMENT_SHA


# ---------------------------------------------------------------- SVG band

ROOT_A = "f733c852045f925d30caf104da2a0879b5f6ec0c3f258a0c1bd9d453f82f7ac8"   # log entry 6
ROOT_B = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"

SVG = ('<svg viewBox="0 0 10 10"><circle r="1" fill="#000000"/>'
       '<text x="1" y="2" fill="#000000" font-size="118">d453 f82f 7ac8</text></svg>')


def test_band_replacement_changes_only_the_band():
    new = sd.replace_band(SVG, ROOT_B)
    assert ">4567 89ab cdef<" in new                # the LAST twelve, in fours
    assert ">0123 4567 89ab<" not in new            # not the head
    assert sd.band_problems(SVG, new, ROOT_B) == []
    assert new.replace(sd.grouped(ROOT_B), "d453 f82f 7ac8") == SVG


def test_band_control_wrong_tail_is_caught():
    wrong = sd.replace_band(SVG, ROOT_B[::-1])      # a different root
    assert sd.band_problems(SVG, wrong, ROOT_B)
    head = SVG.replace("d453 f82f 7ac8", " ".join([ROOT_B[:4], ROOT_B[4:8], ROOT_B[8:12]]))
    assert sd.band_problems(SVG, head, ROOT_B)      # the root's HEAD in the band


def test_band_control_other_change_is_caught():
    new = sd.replace_band(SVG, ROOT_B).replace('fill="#000000"/>', 'fill="#111111"/>')
    assert sd.band_problems(SVG, new, ROOT_B) == ["something other than the band text changed"]


def test_band_refuses_art_with_two_bands():
    with pytest.raises(ValueError):
        sd.replace_band(SVG.replace("</svg>", '<text x="0">aaaa bbbb cccc</text></svg>'), ROOT_B)


def test_band_on_the_real_pair_reproduces_the_committed_seal():
    """b085 a4c5 6253 -> d453 f82f 7ac8 must give the committed d453 files byte for byte."""
    seal = os.path.join(sd.INSPEXIMUS_REPO, "docs", "seal")
    for th in ("light", "dark"):
        old_p = os.path.join(seal, "b085a4c56253-seal-%s.svg" % th)
        new_p = os.path.join(seal, "d453f82f7ac8-seal-%s.svg" % th)
        if not (os.path.isfile(old_p) and os.path.isfile(new_p)):
            pytest.skip("inspeximus-repo docs/seal not on this machine")
        old = open(old_p, encoding="utf-8", newline="").read()
        want = open(new_p, encoding="utf-8", newline="").read()
        assert sd.replace_band(old, ROOT_A) == want
        assert sd.replace_band(old, ROOT_B) != want


# ---------------------------------------------------------------- footer

SENT = '<a href="https://raw.githubusercontent.com/DanceNitra/inspeximus/d80f2d16e54365ba0ec17ead059e84bf63fb3329/docs/seal/d453f82f7ac8-seal-light.svg#gh-light-mode-only"><img align="left" src="https://raw.githubusercontent.com/DanceNitra/inspeximus/d80f2d16e54365ba0ec17ead059e84bf63fb3329/docs/seal/d453f82f7ac8-seal-light.svg" width="41" height="47" alt="Inspeximus seal"></a><a href="https://raw.githubusercontent.com/DanceNitra/inspeximus/d80f2d16e54365ba0ec17ead059e84bf63fb3329/docs/seal/d453f82f7ac8-seal-dark.svg#gh-dark-mode-only"><img align="left" src="https://raw.githubusercontent.com/DanceNitra/inspeximus/d80f2d16e54365ba0ec17ead059e84bf63fb3329/docs/seal/d453f82f7ac8-seal-dark.svg" width="41" height="47" alt="Inspeximus seal"></a><small><b>Inspeximus</b> &middot; figures above recomputed from the files; 11 of 11 planted errors caught.</small><br><small>Root <code>&hellip; d453 f82f 7ac8</code> &middot; sealed 2026-09-24 &middot; certifies time and integrity, not correctness.</small>'
COMMIT = "a" * 40


def test_footer_substitutes_exactly_four_things():
    new = sd.substitute_footer(SENT, COMMIT, ROOT_B, 7, "2026-09-25")
    assert sd.footer_problems(SENT, new, COMMIT, ROOT_B, 7, "2026-09-25") == []
    assert "7 of 7 planted errors caught" in new and "11 of 11" not in new
    assert "Root <code>&hellip; 4567 89ab cdef</code>" in new
    assert sd.grouped(ROOT_B) in new and "d453 f82f 7ac8" not in new and "d453f82f7ac8" not in new
    assert new.count(COMMIT) == 4 and "d80f2d16" not in new
    assert "sealed 2026-09-25" in new
    assert sd.SEAL_MARK in new and sd.ROOT_MARK in new


def test_footer_control_wrong_count_is_caught():
    new = sd.substitute_footer(SENT, COMMIT, ROOT_B, 7, "2026-09-25")
    assert sd.footer_problems(SENT, new, COMMIT, ROOT_B, 8, "2026-09-25")
    assert sd.footer_problems(SENT, new.replace("7 of 7", "7 of 8"), COMMIT, ROOT_B, 7, "2026-09-25")


def test_footer_control_wrong_tail_is_caught():
    new = sd.substitute_footer(SENT, COMMIT, ROOT_B, 7, "2026-09-25")
    assert sd.footer_problems(SENT, new, COMMIT, ROOT_A, 7, "2026-09-25")
    stale = sd.substitute_footer(SENT, COMMIT, ROOT_A, 7, "2026-09-25")   # the old tail left in
    assert sd.footer_problems(SENT, stale, COMMIT, ROOT_B, 7, "2026-09-25")


def test_footer_control_redescribed_text_is_caught():
    new = sd.substitute_footer(SENT, COMMIT, ROOT_B, 7, "2026-09-25")
    reworded = new.replace("recomputed from the files", "checked against the sources")
    assert sd.footer_problems(SENT, reworded, COMMIT, ROOT_B, 7, "2026-09-25")


def test_footer_of_takes_the_block_after_the_signature():
    body = "Hello.\r\n\r\nRastislav.\r\n\r\n" + SENT + "\r\n"
    assert sd.footer_of(body) == SENT


def test_sealed_body_keeps_the_draft_bytes_and_line_endings():
    draft = b"Line one.\r\n\r\nRastislav.\r\n"
    out = sd.seal_body(draft, SENT)
    assert out.startswith(draft + b"\r\n") and out.endswith(b"</small>\r\n")


# ---------------------------------------------------------------- render check

def test_vanished_tag_is_caught_and_escaped_or_kept_tags_are_not():
    src = "a <sz sz> b `<sz>` <small>x</small>"
    html = "<p>a  b <code>&lt;sz&gt;</code> <small>x</small></p>"
    assert sd.vanished_tags(src, html) == [("sz", 2, 1)]
    assert sd.vanished_tags(src, html.replace("a  b", "a &lt;sz sz&gt; b")) == []
