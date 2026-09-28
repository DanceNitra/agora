"""Seal SVGs go to the `seals` branch of DanceNitra/inspeximus, never to main (2026-09-28).

Every seal upload used to be a commit on inspeximus main. Two landed during the 3.15.2 and 3.15.3 releases,
so `tools/release.py` refused with "origin/main moved" and a release was rebased and re-run through CI. A
seal link is pinned to its commit sha, so the branch it lives on does not change the link's shape. Each
test drives the real function with a recording stand-in for the GitHub API, and carries a control.
"""
import os
import sys
import urllib.error

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
SEAL = os.path.join(os.path.dirname(HERE), "tools", "seal")
sys.path.insert(0, SEAL)
import seal_draft as sd  # noqa: E402


class Recorder:
    def __init__(self, answers):
        self.calls, self.answers = [], answers

    def __call__(self, method, path, token, data=None):
        self.calls.append((method, path, data))
        for (m, prefix), answer in self.answers.items():
            if m == method and path.startswith(prefix):
                if isinstance(answer, Exception):
                    raise answer
                return answer
        raise AssertionError("unexpected API call %s %s" % (method, path))


def test_the_branch_is_not_main():
    assert sd.SEAL_BRANCH == "seals" and sd.SEAL_BRANCH != "main"


def test_upload_commits_to_the_seal_branch_and_checks_that_branch_first(monkeypatch):
    missing = urllib.error.HTTPError("u", 404, "Not Found", None, None)
    rec = Recorder({("GET", "/repos/DanceNitra/inspeximus/contents/"): missing,
                    ("PUT", "/repos/DanceNitra/inspeximus/contents/"): {"commit": {"sha": "c" * 40}}})
    monkeypatch.setattr(sd, "api", rec)
    sha = sd.upload("docs/seal/abcdef123456-seal-dark.svg", b"<svg/>", "seal: test", "token")
    assert sha == "c" * 40
    (gm, gpath, _), (pm, ppath, body) = rec.calls
    assert gm == "GET" and gpath.endswith("?ref=seals"), gpath
    assert pm == "PUT" and body["branch"] == "seals", body
    assert "?" not in ppath                                        # the branch travels in the body, not the URL


def test_upload_refuses_a_tail_that_exists_on_the_seal_branch(monkeypatch):
    rec = Recorder({("GET", "/repos/DanceNitra/inspeximus/contents/"): {"sha": "x"}})
    monkeypatch.setattr(sd, "api", rec)
    with pytest.raises(SystemExit):                                # control: an existing file is never replaced
        sd.upload("docs/seal/abcdef123456-seal-dark.svg", b"<svg/>", "seal: test", "token")
    assert [c[0] for c in rec.calls] == ["GET"]


def test_the_newest_pair_is_read_from_the_seal_branch(monkeypatch):
    rec = Recorder({("GET", "/repos/DanceNitra/inspeximus/commits?"): []})
    monkeypatch.setattr(sd, "api", rec)
    with pytest.raises(SystemExit):
        sd.last_seal_pair("token")
    assert "sha=seals" in rec.calls[0][1], rec.calls[0][1]


def test_no_seal_tool_reads_or_writes_main():
    for name in ("seal_draft.py", "seal_strip.py"):
        src = open(os.path.join(SEAL, name), encoding="utf-8").read()
        assert "origin/main" not in src, name
        assert '"branch": "main"' not in src and "ref=main" not in src and "sha=main" not in src, name
    strip = open(os.path.join(SEAL, "seal_strip.py"), encoding="utf-8").read()
    assert '"origin/" + SEAL_BRANCH' in strip                    # control: the reader names the seal branch
