"""tools/outbound.py: the lint that stands between a draft and the gate.

Positive controls are the two texts actually sent on 2026-09-24 (they must pass), negative controls
are the defects the lint exists for (each must fail on its own check).
"""
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


@pytest.fixture
def sealed(tmp_path, monkeypatch):
    """A sealed draft that passes check and gate, and a writer for its pregate record."""
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
    (d / "draft.sealed.md").write_bytes(body.encode("utf-8"))

    def record(**fields):
        (tmp_path / "pregate" / "outbound_t.json").write_text(json.dumps(dict(tool="pregate", **fields)))
        return outbound._stage("t")[0]
    return record, tmp_path


def test_status_sealed_without_a_record_waits_for_the_owner(sealed):
    record, _ = sealed
    assert outbound._stage("t")[0] == "5 owner"
    assert record(blocked=0) == "5 owner"


def test_status_sent_with_a_real_comment_id(sealed):
    record, _ = sealed
    assert record(sent="5601087957") == "6 sent 5601087957"


def test_status_a_fake_sent_value_does_not_count(sealed):
    record, _ = sealed
    assert record(sent="yes") == "5 owner"
    assert record(sent="12") == "5 owner"


def test_status_killed_naming_an_existing_dead_path(sealed):
    record, tmp = sealed
    dead = tmp / "outbound" / "t" / "draft.DEAD.md"
    dead.write_text("x")
    why = "The target repository is archived, so this cannot be posted. Dead copy: %s" % dead.as_posix()
    assert record(killed=why) == "x killed"


def test_status_killed_without_a_real_dead_path_does_not_count(sealed):
    record, tmp = sealed
    assert record(killed="repo archived") == "5 owner"
    missing = (tmp / "nowhere" / "draft.DEAD.md").as_posix()
    assert record(killed="The target repository is archived. Dead copy: %s" % missing) == "5 owner"
    alive = tmp / "outbound" / "t" / "draft.md"
    assert record(killed="The target repository is archived. Dead copy: %s" % alive.as_posix()) == "5 owner"
