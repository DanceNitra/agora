"""tools/outbound.py: the lint that stands between a draft and the gate.

Positive controls are the two texts actually sent on 2026-09-24 (they must pass), negative controls
are the defects the lint exists for (each must fail on its own check).
"""
import hashlib
import io
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import outbound  # noqa: E402

SENT = {
    "github": ("agora_output/drafts/agmi_pr_defended_controls_2026-09-24.md", 42),
    "edrn": ("agora_output/drafts/edrn_guanghao_orbit_paper_2026-09-24.md", 22),
}


@pytest.fixture
def slot(tmp_path, monkeypatch):
    monkeypatch.setattr(outbound, "BASE", str(tmp_path))

    def make(sign, body):
        d = tmp_path / "t"
        d.mkdir(exist_ok=True)
        (d / "meta.json").write_text(json.dumps({"slug": "t", "thread": "o/r#1", "sign": sign}))
        (d / "draft.md").write_bytes(body.encode("utf-8"))
        return {n: ok for ok, n, _ in outbound.lint("t")}
    return make


def _head(path, n):
    with io.open(os.path.join(ROOT, path), encoding="utf-8") as fh:
        return "".join(fh.readlines()[:n])


@pytest.mark.parametrize("sign", sorted(SENT))
def test_the_texts_actually_sent_pass(slot, sign):
    path, n = SENT[sign]
    if not os.path.exists(os.path.join(ROOT, path)):
        pytest.skip("sent draft not on disk")
    res = slot(sign, _head(path, n))
    hard = {k: v for k, v in res.items() if not k.startswith("WARN ")}
    assert all(hard.values()), hard


def test_em_dash_fails(slot):
    assert not slot("edrn", "A — B.\n\nRastislav Drahoš, Agora Research OS\n")["no em or en dash"]


def test_non_ascii_fails_on_github(slot):
    res = slot("github", "Café.\n\n" + outbound.SIGNATURES["github"] + "\n")
    assert not res["pure ASCII (gh mangles non-ASCII)"]


def test_ai_disclosure_fails_on_edrn(slot):
    res = slot("edrn", "x.\n\n" + outbound.SIGNATURES["github"] + "\n" + outbound.SIGNATURES["edrn"] + "\n")
    assert not res["no AI disclosure in the EDRN thread"]


def test_wrong_signature_fails(slot):
    assert not slot("github", "x.\n\n" + outbound.SIGNATURES["edrn"] + "\n")["ends with the github signature"]


def test_seal_in_draft_fails(slot):
    res = slot("github", '<img alt="Inspeximus seal">\n\n' + outbound.SIGNATURES["github"] + "\n")
    assert not res["draft.md carries no seal (seal adds it)"]


R91188 = os.path.join(ROOT, "agora_output", "outbound", "r91188")


@pytest.fixture
def sent_copy(tmp_path, monkeypatch):
    """r91188 as it was sent on 2026-09-25, copied so a mutation never touches the real folder.

    It was gated under the three skill receipts, which 0ecce9b3 replaced with one author receipt,
    so the copy gets that receipt recorded on its unchanged draft, as `outbound.py gate` does now.
    """
    if not os.path.exists(os.path.join(R91188, "draft.sealed.md")):
        pytest.skip("r91188 not on disk")
    import shutil
    import author_receipt
    shutil.copytree(R91188, tmp_path / "r91188")
    monkeypatch.setattr(outbound, "BASE", str(tmp_path))
    author_receipt.record(str(tmp_path / "r91188" / "draft.md"))
    return tmp_path / "r91188"


def _fails(res):
    return [n for st, n, _ in res if st == "FAIL"]


def test_dryrun_passes_the_text_actually_sent(sent_copy):
    assert _fails(outbound.dryrun_checks("r91188", offline=True)) == []


def test_dryrun_fails_on_one_changed_character(sent_copy):
    p = sent_copy / "draft.md"
    t = p.read_bytes()
    i = t.index(b"fired 8 times") + 6
    p.write_bytes(t[:i] + b"9" + t[i + 1:])
    assert _fails(outbound.dryrun_checks("r91188", offline=True)) == [
        "author receipt binds the draft"]


def test_dryrun_fails_on_a_wrong_sha(sent_copy):
    res = outbound.dryrun_checks("r91188", sha="0" * 64, offline=True)
    assert _fails(res) == ["sha matches the approved hash"]


ME = "DanceNitra"


@pytest.fixture
def sealed(tmp_path, monkeypatch):
    """A sealed draft that passes check and gate, a fake live thread, and a pregate record writer.

    The thread is a dict the test fills: "comments" for o/r#1, "issues" for issues our account
    opened in o/r. No test here reaches the network: subprocess.run raises if anything calls it.
    """
    import author_receipt
    monkeypatch.setattr(outbound, "BASE", str(tmp_path / "outbound"))
    monkeypatch.setattr(outbound, "PREGATE", str(tmp_path / "pregate"))
    d = tmp_path / "outbound" / "t"
    d.mkdir(parents=True)
    (tmp_path / "pregate").mkdir()
    (d / "meta.json").write_text(json.dumps({"slug": "t", "thread": "o/r#1", "sign": "github"}))
    body = ("We ran the walk over our own transcripts and found the reminder fired eight times in "
            "total, with no edit to the index inside any window.\n\n" + outbound.SIGNATURES["github"] + "\n")
    (d / "draft.md").write_bytes(body.encode("utf-8"))
    author_receipt.record(str(d / "draft.md"))
    sealed_bytes = (body + "\n<img alt=\"Inspeximus seal\" src=\"x\">\n").encode("utf-8")
    (d / "draft.sealed.md").write_bytes(sealed_bytes)

    live = {"comments": [], "issues": [], "fail": None, "reads": []}

    def fake_list(path):
        live["reads"].append(path)
        if live["fail"]:
            raise outbound.LiveReadFailed(live["fail"])
        if path == "repos/o/r/issues/1/comments":
            return list(live["comments"])
        if path == "repos/o/r/issues?creator=%s&state=all" % ME:
            return list(live["issues"])
        raise AssertionError("unexpected read %s" % path)

    def no_network(*a, **kw):
        raise AssertionError("a test reached subprocess.run: %r" % (a[:1],))
    monkeypatch.setattr(outbound, "_gh_list", fake_list)
    monkeypatch.setattr(outbound, "_our_login", lambda: ME)
    monkeypatch.setattr(outbound.subprocess, "run", no_network)

    def record(**fields):
        (tmp_path / "pregate" / "outbound_t.json").write_text(json.dumps(dict(tool="pregate", **fields)))
        return outbound._stage("t")[0]
    return {"record": record, "tmp": tmp_path, "dir": d, "live": live, "sealed": sealed_bytes,
            "draft": body}


def _c(cid, body, login=ME, url=None):
    return (cid, url or "https://github.com/o/r/issues/1#issuecomment-%s" % cid, login, body)


def test_status_sealed_without_a_record_waits_for_the_owner(sealed):
    assert outbound._stage("t")[0] == "5 owner"
    assert sealed["record"](blocked=0) == "5 owner"


def test_status_sent_when_the_live_thread_holds_the_sealed_bytes(sealed):
    sealed["live"]["comments"] = [_c(5850000001, "an earlier reply"),
                                  _c(5860335219, sealed["sealed"].decode("utf-8"))]
    stage, nxt = outbound._stage("t")
    assert stage == "6 sent 5860335219"
    assert "issuecomment-5860335219" in nxt
    rec = json.loads((sealed["dir"] / "sent.json").read_text())
    assert rec["id"] == 5860335219
    assert rec["draft_sealed_sha256"] == hashlib.sha256(sealed["sealed"]).hexdigest()


def test_status_control_a_draft_but_no_matching_comment_is_not_sent(sealed):
    """The control: a draft exists everywhere we keep drafts, and the thread holds near misses."""
    s = sealed["sealed"].decode("utf-8")
    drafts = sealed["tmp"] / "drafts"
    drafts.mkdir()
    (drafts / "t.md").write_bytes(sealed["sealed"])
    sealed["live"]["comments"] = [
        _c(5860000001, sealed["draft"]),                  # the unsealed draft.md, posted
        _c(5860000002, s.rstrip("\n")),                   # the sealed text minus its last newline
        _c(5860000003, s.replace("eight", "nine")),       # one word changed
        _c(5860000004, s, login="someone-else"),          # our exact bytes, another account
    ]
    assert outbound._stage("t")[0] == "5 owner"
    assert not (sealed["dir"] / "sent.json").exists()


def test_status_a_text_that_opened_a_new_issue_is_sent(sealed):
    """lantern-outcome-questions: meta names a closed PR, the text became the body of issue #2."""
    sealed["live"]["issues"] = [_c(5601087957, sealed["sealed"].decode("utf-8"),
                                   url="https://github.com/o/r/issues/2")]
    stage, nxt = outbound._stage("t")
    assert stage == "6 sent 5601087957"
    assert nxt.endswith("https://github.com/o/r/issues/2")


def test_status_a_record_alone_never_makes_a_text_sent(sealed):
    """The pregate `sent` field and our own sent.json are files, not the thread."""
    (sealed["dir"] / "sent.json").write_text(json.dumps({"id": 5860335219}))
    assert outbound._stage("t")[0] == "5 owner"
    assert sealed["record"](sent="5860335219") == "! unconfirmed"


def test_status_a_fake_sent_value_does_not_count(sealed):
    assert sealed["record"](sent="yes") == "5 owner"
    assert sealed["record"](sent="12") == "5 owner"


def test_status_an_unreadable_thread_is_neither_sent_nor_waiting(sealed):
    sealed["live"]["fail"] = "gh api exited 1: HTTP 502"
    stage, nxt = outbound._stage("t")
    assert stage == "? gh failed"
    assert nxt.startswith("do not post")
    assert sealed["record"](sent="5860335219") == "? gh failed"


def test_status_the_live_thread_outranks_a_kill_record(sealed):
    dead = sealed["dir"] / "draft.DEAD.md"
    dead.write_text("x")
    why = "The target repository is archived, so this cannot be posted. Dead copy: %s" % dead.as_posix()
    sealed["live"]["comments"] = [_c(5860335219, sealed["sealed"].decode("utf-8"))]
    assert sealed["record"](killed=why) == "6 sent 5860335219"


def test_status_killed_naming_an_existing_dead_path(sealed):
    dead = sealed["dir"] / "draft.DEAD.md"
    dead.write_text("x")
    why = "The target repository is archived, so this cannot be posted. Dead copy: %s" % dead.as_posix()
    assert sealed["record"](killed=why) == "x killed"


def test_status_killed_without_a_real_dead_path_does_not_count(sealed):
    record, tmp = sealed["record"], sealed["tmp"]
    assert record(killed="repo archived") == "5 owner"
    missing = (tmp / "nowhere" / "draft.DEAD.md").as_posix()
    assert record(killed="The target repository is archived. Dead copy: %s" % missing) == "5 owner"
    alive = tmp / "outbound" / "t" / "draft.md"
    assert record(killed="The target repository is archived. Dead copy: %s" % alive.as_posix()) == "5 owner"


def test_status_without_a_sealed_draft_reads_nothing(sealed):
    (sealed["dir"] / "draft.sealed.md").unlink()
    assert outbound._stage("t")[0] == "4 seal"
    assert sealed["live"]["reads"] == []


def test_status_reads_each_thread_once_per_run(sealed):
    cache = {}
    outbound._stage("t", cache)
    outbound._stage("t", cache)
    assert sealed["live"]["reads"] == ["repos/o/r/issues/1/comments",
                                       "repos/o/r/issues?creator=%s&state=all" % ME]


WRITE_FLAGS = {"-f", "-F", "--field", "--raw-field", "--input", "-X", "--method=POST",
               "-H", "--header", "POST", "PATCH", "PUT", "DELETE"}


def test_every_gh_call_status_makes_is_a_get(monkeypatch):
    """The two functions that reach gh, with subprocess.run captured: GET only, no write flag."""
    import subprocess
    calls = []

    def capture(cmd, **kw):
        calls.append(cmd)
        out = b"DanceNitra\n" if cmd[-1] == ".login" else b'[1, "u", "DanceNitra", "b"]\n'
        return subprocess.CompletedProcess(cmd, 0, out, b"")
    monkeypatch.setattr(outbound.subprocess, "run", capture)
    monkeypatch.setattr(outbound, "_LOGIN", [])
    assert outbound._our_login() == "DanceNitra"
    assert outbound._gh_list("repos/o/r/issues/1/comments") == [(1, "u", "DanceNitra", "b")]
    assert len(calls) == 2
    for cmd in calls:
        assert cmd[:4] == ["gh", "api", "--method", "GET"], cmd
        assert not WRITE_FLAGS & set(cmd), cmd


def test_a_failed_gh_read_raises_instead_of_reading_as_empty(monkeypatch):
    import subprocess
    monkeypatch.setattr(outbound.subprocess, "run",
                        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 1, b"", b"HTTP 404"))
    with pytest.raises(outbound.LiveReadFailed):
        outbound._gh_list("repos/o/r/issues/1/comments")
