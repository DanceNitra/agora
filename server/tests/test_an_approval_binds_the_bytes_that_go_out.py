"""Approval binds the published BYTES, and a publish that did not land is not reported as one.

WHY THIS FILE EXISTS. Until 2026-08-14 an approval bound `uuid4().hex[:6]` and nothing else:

  * the owner saw `body[:180]` for outreach and press, a resolved-item COUNT for portfolio and an
    insight count for publish — then typed `approve <id>`, and up to 12,000 characters went out;
  * `execute_action` called compose() FRESH for `publish` and `portfolio` (its own comments said
    "re-compose fresh"), so the published bytes were generated AFTER the approval and could not
    have been the approved ones even in principle;
  * `set_status` never inspected the current status, so a rejected, failed or already-done action
    could be re-approved and re-executed;
  * all three publishers ran `git commit -m <msg>` with NO pathspec (committing whatever else was
    staged) and `git push origin main` from whatever branch happened to be checked out — which
    exits 0 on "Everything up-to-date", so a file that never left was recorded as published with a
    public URL.

Every test below is paired: the guard must refuse the bad case AND stay out of the way of the good
one. A publish gate that refuses everything would pass half of this file.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "server"
if str(SERVER) not in sys.path:
    sys.path.insert(0, str(SERVER))


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


hands = _load("hands_under_test", "server/agora/execution/hands.py")
pubrepo = _load("public_repo_under_test", "server/agora/execution/public_repo.py")


@pytest.fixture(autouse=True)
def isolated_actions(tmp_path, monkeypatch):
    """Never touch the live .actions.json."""
    monkeypatch.setattr(hands, "_ACTIONS", tmp_path / "actions.json")


# ------------------------------------------------------------------ the digest binds the bytes
def test_a_bound_kind_records_the_digest_of_what_will_be_sent(monkeypatch):
    monkeypatch.setattr(hands, "publishable_text", lambda k, p: "the exact draft body")
    rec = hands.propose_action("outreach", "Post something", "spec", {"corr_id": "x"})
    assert rec["content_sha"] == hands.content_sha("the exact draft body")
    assert rec["content_len"] == len("the exact draft body")


def test_an_unbound_kind_records_no_digest(monkeypatch):
    """The other half: a kind with nothing publishable must not grow a phantom digest."""
    rec = hands.propose_action("build_tool", "Build a thing", "spec", {})
    assert "content_sha" not in rec


def test_execution_refuses_when_the_content_changed_after_approval(monkeypatch):
    monkeypatch.setattr(hands, "publishable_text", lambda k, p: "APPROVED BODY")
    rec = hands.propose_action("outreach", "Post", "spec", {"corr_id": "x"})
    hands.approve_action(rec["id"])
    # ...and the draft is edited between approval and execution.
    monkeypatch.setattr(hands, "publishable_text", lambda k, p: "APPROVED BODY plus a paragraph")
    r = hands.execute_action(rec["id"])
    assert "error" in r and "content changed after approval" in r["error"], r
    assert "nothing was published" in r["error"]
    assert hands.get_action(rec["id"])["status"] == "approved", "the action was consumed anyway"


def test_execution_refuses_a_bound_kind_that_carries_no_digest(monkeypatch):
    """A proposer that forgets to bind must be indistinguishable from nothing — refused, not run.
    Otherwise the guard silently stops applying to every caller added later."""
    monkeypatch.setattr(hands, "publishable_text", lambda k, p: None)   # nothing bindable at propose
    rec = hands.propose_action("press", "Publish a piece", "spec", {"press_id": "p1"})
    assert "content_sha" not in rec
    hands.approve_action(rec["id"])
    monkeypatch.setattr(hands, "publishable_text", lambda k, p: "a body that appeared later")
    r = hands.execute_action(rec["id"])
    assert "error" in r and "no content digest" in r["error"], r


def test_unchanged_content_is_not_blocked(monkeypatch):
    """The half that keeps the gate usable: identical bytes must pass the check."""
    monkeypatch.setattr(hands, "publishable_text", lambda k, p: "STABLE BODY")
    rec = hands.propose_action("press", "Publish", "spec", {"press_id": "p1"})
    hands.approve_action(rec["id"])
    called = {}

    def publish_piece(pid):
        called["pid"] = pid
        return {"url": "https://x/y"}

    fake = type(sys)("agora.execution.press")
    fake.publish_piece = publish_piece
    monkeypatch.setitem(sys.modules, "agora.execution.press", fake)
    r = hands.execute_action(rec["id"])
    assert r.get("ok"), r
    assert called["pid"] == "p1", "the publisher was not reached on identical bytes"


# ------------------------------------------------------------ an approval is not reusable
@pytest.mark.parametrize("status", ["done", "rejected", "failed"])
def test_a_finished_action_cannot_be_re_approved(monkeypatch, status):
    monkeypatch.setattr(hands, "publishable_text", lambda k, p: "body")
    rec = hands.propose_action("portfolio", "Publish", "spec", {})
    hands.set_status(rec["id"], status)
    r = hands.approve_action(rec["id"])
    assert isinstance(r, dict) and "error" in r, f"a '{status}' action was re-approved: {r}"
    assert hands.get_action(rec["id"])["status"] == status, "the status was overwritten anyway"


def test_a_pending_action_can_still_be_approved(monkeypatch):
    monkeypatch.setattr(hands, "publishable_text", lambda k, p: "body")
    rec = hands.propose_action("portfolio", "Publish", "spec", {})
    assert hands.approve_action(rec["id"])["status"] == "approved"


# ------------------------------------------------------------------- the git publish contract
@pytest.fixture
def repo(tmp_path: Path) -> Path:
    origin, wt = tmp_path / "origin.git", tmp_path / "repo"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(origin)], capture_output=True)
    subprocess.run(["git", "clone", str(origin), str(wt)], capture_output=True)
    for k, v in (("user.email", "t@t.local"), ("user.name", "test")):
        subprocess.run(["git", "-C", str(wt), "config", k, v], capture_output=True)
    (wt / "public").mkdir()
    (wt / "public" / "track-record.md").write_text("v1\n", encoding="utf-8")
    (wt / "other.txt").write_text("unrelated\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(wt), "add", "-A"], capture_output=True)
    subprocess.run(["git", "-C", str(wt), "commit", "-m", "seed"], capture_output=True)
    subprocess.run(["git", "-C", str(wt), "push", "-u", "origin", "main"], capture_output=True)
    return wt


def _sh(repo: Path, *a: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True,
                          encoding="utf-8").stdout


def test_the_commit_carries_only_the_named_paths(repo: Path):
    """Another process leaves an unrelated file staged; the owner's approval of a track-record
    update must not carry it outward."""
    (repo / "public" / "track-record.md").write_text("v2\n", encoding="utf-8")
    (repo / "other.txt").write_text("someone else was working\n", encoding="utf-8")
    _sh(repo, "add", "other.txt")                       # staged by somebody else

    r = pubrepo.commit_and_push(repo, ["public/track-record.md"], "Track Record: update")
    assert "sha" in r, r
    files = [ln for ln in _sh(repo, "show", "--name-only", "--format=", "HEAD").splitlines() if ln]
    assert files == ["public/track-record.md"], f"the commit swept in extra files: {files}"
    assert "other.txt" in _sh(repo, "diff", "--cached", "--name-only"), \
        "the other process's staged file was consumed"


def test_publishing_from_the_wrong_branch_is_a_refusal_not_a_false_success(repo: Path):
    """The live repo sits on a feature branch. The commit would land there while the push sends
    `main`, git exits 0 on 'Everything up-to-date', and the record is marked published."""
    _sh(repo, "checkout", "-b", "integration/something")
    (repo / "public" / "track-record.md").write_text("v2\n", encoding="utf-8")
    r = pubrepo.commit_and_push(repo, ["public/track-record.md"], "Track Record: update")
    assert "error" in r and "integration/something" in r["error"], r
    assert "never left" in r["error"]
    assert _sh(repo, "rev-parse", "origin/main").strip() == _sh(repo, "rev-parse", "main").strip(), \
        "the remote moved despite the refusal"


def test_a_push_that_does_not_move_the_remote_is_an_error(repo: Path, monkeypatch):
    """'Everything up-to-date' exits 0. The remote ref is the oracle, not the exit code."""
    (repo / "public" / "track-record.md").write_text("v2\n", encoding="utf-8")
    real = pubrepo._git

    def no_op_push(r, *args):
        if args and args[0] == "push":
            return subprocess.CompletedProcess(args, 0, "Everything up-to-date\n", "")
        return real(r, *args)

    monkeypatch.setattr(pubrepo, "_git", no_op_push)
    out = pubrepo.commit_and_push(repo, ["public/track-record.md"], "Track Record: update")
    assert "error" in out and "not our commit" in out["error"], out


def test_nothing_to_commit_is_a_note_not_an_error_and_not_a_success(repo: Path):
    """The third outcome has to stay distinguishable from both of the others."""
    r = pubrepo.commit_and_push(repo, ["public/track-record.md"], "Track Record: update")
    assert r.get("note") and "sha" not in r and "error" not in r, r


def test_an_empty_path_list_is_refused(repo: Path):
    """A commit with an unspecified set is exactly the defect; asking for one must fail loudly."""
    r = pubrepo.commit_and_push(repo, [], "whatever")
    assert "error" in r and "no paths given" in r["error"]
