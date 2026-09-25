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
