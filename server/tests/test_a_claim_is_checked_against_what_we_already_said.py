"""The publish path reads our own history in the thread a claim is aimed at.

THE CASE THIS EXISTS FOR, recorded verbatim. On 2026-08-14 we nearly posted, to
deepseek-ai/DeepSeek-V3#1466, that "80.7/4.1 appears nowhere in the package". Our own comment
5271557433 in that same thread, two days earlier, contains

    | TAT v0.9 | 80.7% | **242** | 4.10% -> ~86 | 0.738 |
    The reconstruction checks out: 242/(242+86) = 0.7378 ...

The refutation would have been public, immediate, and written by us. `tools/send_approved.py` bound
approval to BYTES; nothing bound a claim to what we had already said about it.

The fixture is the real thread, recorded: `fixtures/deepseek_v3_1466_our_comments.json`. Not a
paraphrase of it. A synthetic fixture proves the matcher matches strings; only the real comments
prove it would have caught the claim we actually wrote.

A gate is worth what it REFUSES, so every assertion below is paired: it must fire on the draft that
was wrong, and stay silent on the one that was right. The second half is not decoration -- a matcher
that flags every comment passes the first half perfectly.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "deepseek_v3_1466_our_comments.json"
THREAD = "https://github.com/deepseek-ai/DeepSeek-V3/issues/1466"

# The claim as it would have gone out.
KILLED_CLAIM = ("The pair 80.7 / 4.1 appears nowhere in the package. There is no artifact that "
                "produces it, and the 242 figure has no runner behind it.")

# The claim we actually sent to that thread on 2026-08-14. It is IN the fixture, so it must flag
# itself -- that is the "we already said this" signal working, not a false positive.
WHAT_WE_SENT = ("The curve is over 305 contradiction pairs, not the 2400 records; AUC(connectivity) "
                "inverts to 0.2911 inside the support==1 stratum.")

# The negative control. It carries three significant numbers, none of which appear in that thread.
# A control with NO numbers would pass vacuously -- it would be satisfied by a matcher that had
# stopped working entirely, which is the shape of an absence test that nothing has to survive.
UNRELATED = ("The erasure defect reproduced 12 times over 4096 records, at 99.73% coverage and "
             "0.0841 residue.")


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    assert spec and spec.loader, f"cannot load tools/{name}.py"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


psc = _load("prior_statement_check")


@pytest.fixture(scope="module")
def ours() -> list[dict]:
    assert FIXTURE.exists(), f"{FIXTURE} is gone -- the fixture no longer exists"
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ the half that must keep firing
def test_the_claim_we_nearly_posted_is_flagged_by_our_own_comment(ours):
    """If this goes quiet, either the matcher stopped seeing it or the fixture stopped carrying it.
    Both are asserted, so a green run cannot mean 'the case never arose'."""
    assert any("80.7%" in c["body"] and "242" in c["body"] for c in ours), \
        "the fixture no longer reproduces the defect -- comment 5271557433 lost its numbers"
    r = psc.compare(KILLED_CLAIM, ours)
    hit = [o for o in r["overlaps"] if o["id"] == 5271557433]
    assert hit, f"comment 5271557433 was not flagged -- overlaps: {[o['id'] for o in r['overlaps']]}"
    assert {"80.7", "242"} <= set(hit[0]["numbers"]), \
        f"flagged, but not on the numbers that matter: {hit[0]['numbers']}"
    assert any("242/(242+86)" in ln or "80.7%" in ln for ln in hit[0]["lines"]), \
        f"the flagged comment shows no line a reader could act on: {hit[0]['lines']}"


def test_the_negative_existence_claim_is_named_as_such():
    """Two of the six claims killed on 2026-08-14 were claims of ABSENCE. That class is called out
    by name because a single overlooked artifact refutes it completely."""
    negs = psc.negative_claims(KILLED_CLAIM)
    joined = " ".join(negs).lower()
    assert "appears nowhere" in joined, f"the absence claim was not recognised: {negs}"
    assert "no runner" in joined, f"'has no runner behind it' was not recognised: {negs}"


def test_a_decimal_does_not_split_the_sentence_it_sits_in():
    """The first run against the real thread quoted the claim back as '1 appears nowhere in the
    package' -- the sentence splitter broke at the decimal point in 80.7, so the operator was shown
    a mangled version of their own draft."""
    negs = psc.negative_claims(KILLED_CLAIM)
    assert any(s.startswith("The pair 80.7 / 4.1 appears nowhere") for s in negs), \
        f"the claim came back mangled: {negs}"


# -------------------------------------------------------------------- the half that must stay quiet
def test_an_unrelated_claim_with_real_numbers_is_not_flagged(ours):
    """The other half. A matcher that flags everything passes every assertion above.

    The control carries three significant numbers on purpose: a numberless control is satisfied by a
    matcher that has stopped working, and would keep passing after the gate went blind.
    """
    r = psc.compare(UNRELATED, ours)
    assert r["numbers_checked"] == ["0.0841", "4096", "99.73"], \
        f"the control stopped carrying numbers -- it can now pass vacuously: {r['numbers_checked']}"
    assert not r["overlaps"], \
        f"a clean draft was flagged against {[o['id'] for o in r['overlaps']]}"


def test_restating_a_number_we_published_surfaces_the_comment_that_published_it(ours):
    """Not a false positive: the draft we DID send restates numbers from that thread, and the check
    points at where they came from. Asserting something about a number is exactly when our own
    earlier statement of it is worth re-reading."""
    flagged = {o["id"] for o in psc.compare(WHAT_WE_SENT, ours)["overlaps"]}
    assert 5295272576 in flagged, "our own published numbers no longer trace back to their comment"


def test_a_substring_of_a_longer_number_is_not_a_match(ours):
    """Measured on the real thread: a substring test for '4.1' fires inside '24.11%', and comment
    5249160043 was flagged for a number it does not contain. Matching is by VALUE."""
    only_41 = "The figure 4.1 is not stated anywhere."
    flagged = {o["id"] for o in psc.compare(only_41, ours)["overlaps"]}
    assert 5249160043 not in flagged, "24.11% was matched as 4.1 again"
    assert 5271557433 in flagged, "4.1 no longer matches our own 4.10% -- value equality is gone"


def test_two_digit_integers_are_below_the_floor():
    """A check that fires on '86' fires on everything and is read by nobody. If this ever fails,
    the floor was lowered -- which is a decision, not an accident."""
    assert psc.significant_numbers("we found 86 of them in 12 runs") == set()
    assert psc.significant_numbers("80.7% over 242 records, 2100 total") == {"80.7", "242", "2100"}


# ------------------------------------------------------------------------ the failure modes differ
def test_an_unreadable_thread_is_a_refusal_not_a_pass():
    """The expensive shape in this codebase: a check that never sees its target reports SAFE."""
    code, report = psc.check(KILLED_CLAIM, "not-a-url")
    assert code == 2, f"a bad thread url returned {code}, not a refusal"
    assert "COULD NOT CHECK" in report


def test_nothing_to_check_is_its_own_code_not_a_clean_pass():
    """A draft with no number and no absence claim is OUT OF SCOPE, and says so. Reporting it as 0
    would make an empty check indistinguishable from a passed one."""
    code, report = psc.check("Thank you -- that clears it up, and I will follow up next week.",
                             THREAD)
    assert code == 3, f"an out-of-scope draft returned {code}"
    assert "NOTHING TO CHECK" in report and "not a pass" in report


# ------------------------------------------------------------------------------- the wiring itself
def test_send_approved_calls_the_check_rather_than_mentioning_it():
    """`construction_audit.py` shipped saying 'wire it into the publish path, not into someone's
    memory' and then lived in memory for six days. Pin the CALL."""
    src = (ROOT / "tools" / "send_approved.py").read_text(encoding="utf-8", errors="replace")
    assert "import prior_statement_check" in src, "send_approved does not import the check"
    assert "_prior_gate(" in src, "send_approved imports the check but never calls it"
    assert "psc.check(" in src, "the gate never reaches the checker"


def test_the_gate_refuses_an_overlap_and_proceeds_on_a_clean_draft(tmp_path, monkeypatch):
    """End to end through send_approved's own gate, with the checker stubbed to each verdict."""
    sa = _load("send_approved")
    draft = tmp_path / "d.md"
    draft.write_text(KILLED_CLAIM, encoding="utf-8")
    cmd = ["gh", "issue", "comment", THREAD, "--body-file", str(draft)]

    monkeypatch.setattr(sa.psc, "check", lambda *_a, **_k: (1, "overlap report"))
    assert sa._prior_gate(str(draft), cmd, None, ack=False) == 1, "an overlap did not refuse"
    assert sa._prior_gate(str(draft), cmd, None, ack=True) is None, "--ack-prior did not release it"

    monkeypatch.setattr(sa.psc, "check", lambda *_a, **_k: (2, "unreadable"))
    assert sa._prior_gate(str(draft), cmd, None, ack=False) == 2, "unreadable thread did not refuse"

    monkeypatch.setattr(sa.psc, "check", lambda *_a, **_k: (0, "clean"))
    assert sa._prior_gate(str(draft), cmd, None, ack=False) is None, "a clean draft was blocked"


# --------------------------------------------------- the gate has to SEE the thread it is aimed at
# Measured on the day this gate was written, by an adversarial review of it: of the three normal
# ways to post a comment, the first version recognised ONE. It printed "NOT RUN" and let the publish
# through on the other two -- a check that never sees its target reporting SAFE, in the file whose
# docstring names that exact failure.
@pytest.mark.parametrize("cmd,expected", [
    (["gh", "issue", "comment", THREAD, "--body-file", "d.md"], THREAD),
    (["gh", "issue", "comment", "1466", "--repo", "deepseek-ai/DeepSeek-V3", "-F", "body=@d.md"],
     THREAD),
    (["gh", "pr", "comment", "1466", "-R", "deepseek-ai/DeepSeek-V3", "--body-file", "d.md"],
     THREAD),
    (["gh", "api", "repos/deepseek-ai/DeepSeek-V3/issues/1466/comments", "-f", "body=@d.md"],
     THREAD),
    (["gh", "release", "create", "v1.0"], None),
])
def test_every_normal_way_of_posting_is_recognised(cmd, expected):
    sa = _load("send_approved")
    assert sa._thread_in(cmd) == expected, f"not seen in: {' '.join(cmd)}"


def test_a_post_command_with_no_determinable_thread_refuses(tmp_path):
    """Fail CLOSED on a publish path: 'I cannot tell where this goes' must not read as 'clean'."""
    sa = _load("send_approved")
    draft = tmp_path / "d.md"
    draft.write_text(KILLED_CLAIM, encoding="utf-8")
    cmd = ["gh", "issue", "comment", "--body-file", str(draft)]     # no repo, no number, no url
    assert psc.thread_from_command(cmd) == (None, True), "not recognised as a github post"
    assert sa._prior_gate(str(draft), cmd, None, ack=False) == 2, "an unaimed post did not refuse"


def test_a_declared_thread_cannot_aim_the_check_away_from_the_command(tmp_path):
    """`--thread` is an assertion to cross-check, never an override. Preferring it let a caller
    point the check at a quiet thread while the command posted to a loud one."""
    sa = _load("send_approved")
    draft = tmp_path / "d.md"
    draft.write_text(KILLED_CLAIM, encoding="utf-8")
    cmd = ["gh", "issue", "comment", "1466", "--repo", "deepseek-ai/DeepSeek-V3"]
    quiet = "https://github.com/DanceNitra/agora/issues/1"
    assert sa._prior_gate(str(draft), cmd, quiet, ack=False) == 2, "a mismatched --thread was allowed"


def test_a_non_posting_command_is_reported_not_refused(tmp_path):
    """The other half: a command that does not post must not be blocked, or the gate is useless."""
    sa = _load("send_approved")
    draft = tmp_path / "d.md"
    draft.write_text(KILLED_CLAIM, encoding="utf-8")
    assert sa._prior_gate(str(draft), ["echo", "hello"], None, ack=False) is None


# ------------------------------------------------- the digest has to bind the BYTES THAT ARE SENT
# An adversarial review of this file on 2026-08-14 found that nothing tied the hashed file to the
# publish command: `post draft.md --sha <correct digest> -- gh issue comment N -R o/r --body "..."`
# printed "approved digest matches; publishing" and sent text nobody had hashed. It also observed,
# correctly, that this test module had no test touching --sha, digest, a.rest or subprocess at all.
def _draft(tmp_path, text=KILLED_CLAIM):
    p = tmp_path / "draft.md"
    p.write_text(text, encoding="utf-8")
    return p


def test_an_inline_body_is_refused_because_a_digest_cannot_bind_it(tmp_path):
    sa = _load("send_approved")
    d = _draft(tmp_path)
    r = sa.bind_payload(str(d), ["gh", "issue", "comment", THREAD, "--body", "something else"])
    assert isinstance(r, str) and "inline body" in r, f"an inline body was allowed: {r}"
    r = sa.bind_payload(str(d), ["gh", "issue", "comment", THREAD, "-b", "something else"])
    assert isinstance(r, str), "the -b short form was allowed"
    r = sa.bind_payload(str(d), ["gh", "api", "repos/o/r/issues/1/comments", "-f", "body=other"])
    assert isinstance(r, str), "an inline gh api body was allowed"


def test_a_body_file_that_is_not_the_approved_file_is_refused(tmp_path):
    sa = _load("send_approved")
    d, other = _draft(tmp_path), tmp_path / "other.md"
    other.write_text("a different draft entirely", encoding="utf-8")
    r = sa.bind_payload(str(d), ["gh", "issue", "comment", THREAD, "--body-file", str(other)])
    assert isinstance(r, str) and "approved digest is of" in r, f"a foreign file was sent: {r}"


def test_a_non_gh_transport_is_refused(tmp_path):
    """`_is_github_post` returns False for a non-gh executable, so the prior-statement gate reports
    NOT RUN and proceeds. The payload binding has to refuse it, or that is a hole straight through."""
    sa = _load("send_approved")
    d = _draft(tmp_path)
    r = sa.bind_payload(str(d), ["curl", "-X", "POST", "https://api.github.com/x", "-d", "@" + str(d)])
    assert isinstance(r, str) and "only a `gh` command" in r, f"a non-gh transport was allowed: {r}"


@pytest.mark.parametrize("cmd,idx,token", [
    (["gh", "issue", "comment", THREAD, "--body-file", "{d}"], 5, "-"),
    (["gh", "pr", "comment", THREAD, "-F", "{d}"], 5, "-"),
    (["gh", "api", "repos/o/r/issues/1/comments", "--input", "{d}"], 4, "-"),
    (["gh", "api", "repos/o/r/issues/1/comments", "-F", "body=@{d}"], 4, "body=@-"),
])
def test_the_approved_file_is_rewritten_to_stdin_and_the_bytes_come_from_memory(
        tmp_path, cmd, idx, token):
    """Flag shapes taken from `gh help issue comment` / `gh api --help`, not from memory. Note the
    collision this pins: -F is --body-file for issue/pr comment and --field for gh api."""
    sa = _load("send_approved")
    d = _draft(tmp_path)
    out, body = sa.bind_payload(str(d), [c.replace("{d}", str(d)) for c in cmd])
    assert out[idx] == token, f"the body was not redirected to stdin: {out}"
    assert str(d) not in " ".join(out), f"the file path survived into the command: {out}"
    assert body == d.read_bytes(), "the bytes sent are not the bytes on disk at digest time"


def test_a_command_with_no_body_file_is_refused(tmp_path):
    sa = _load("send_approved")
    r = sa.bind_payload(str(_draft(tmp_path)), ["gh", "issue", "comment", THREAD])
    assert isinstance(r, str) and "no body file" in r


def test_a_read_only_gh_api_call_is_not_treated_as_a_post():
    """`gh api` defaults to GET; only a method or a field makes it a write."""
    assert psc.thread_from_command(
        ["gh", "api", "repos/o/r/issues/5/comments"])[1] is False
    assert psc.thread_from_command(
        ["gh", "api", "-X", "POST", "repos/o/r/issues/5/comments"])[1] is True
