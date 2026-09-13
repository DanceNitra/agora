"""The SessionStart receipt names exactly the pointers the loader's cut rule drops, and nothing else."""
import os
import subprocess
import sys

import pytest

HOOK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hooks", "memory_index_receipt.py")


def _run(index_text: str, tmp_path):
    p = tmp_path / "MEMORY.md"
    p.write_bytes(index_text.encode("utf-8"))
    r = subprocess.run([sys.executable, "-X", "utf8", HOOK], capture_output=True, text=True,
                       encoding="utf-8", env={**os.environ, "CLAUDE_MEMORY_INDEX": str(p)}, timeout=30)
    assert r.returncode == 0, r.stderr
    return r.stdout


def _index(n_lines: int, width: int = 120):
    return "".join("- [e%d](e%d.md) - %s\n" % (i, i, "x" * width) for i in range(n_lines))


def test_an_index_inside_both_caps_prints_nothing(tmp_path):
    assert _run(_index(50), tmp_path) == ""


def test_the_line_cap_names_every_pointer_past_line_200(tmp_path):
    out = _run(_index(205, width=20), tmp_path)
    for i in range(200, 205):
        assert "e%d.md" % i in out
    assert "e199.md" not in out and "5 pointer(s)" in out


def test_the_unit_cap_names_the_tail_and_counts_utf16_not_bytes(tmp_path):
    # 190 lines of 140 units each is 26,790 units: under the line cap, over the unit cap.
    out = _run(_index(190, width=125), tmp_path)
    assert "pointer(s) are on disk but NOT" in out
    assert "e189.md" in out and "e0.md" not in out


def test_carriage_returns_count_toward_the_cap_as_the_loader_counts_them(tmp_path):
    # Build an LF index that fits with fewer than 185 units to spare, MEASURED rather than computed by
    # hand: the first version of this test priced a line at 135 units and was 5.8 off, because the
    # entry number grows the prefix. Then the same text with CRLF gains one unit per line and must cut.
    def units(t): return len(t.encode("utf-16-le")) // 2
    width = 121
    while units(_index(185, width)) > 25_000 - 1:
        width -= 1
    lf = _index(185, width)
    assert 25_000 - 185 < units(lf) <= 25_000, units(lf)
    assert _run(lf, tmp_path) == ""
    crlf = lf.replace("\n", "\r\n")
    assert units(crlf) > 25_000
    out = _run(crlf, tmp_path)
    assert "NOT in this session's context" in out, "a CR-blind count would report this index as fitting"


def test_a_dropped_pointer_that_also_appears_above_the_cut_is_not_reported(tmp_path):
    text = _index(205, width=20)
    text = text.replace("- [e204](e204.md)", "- [e204](e1.md)")   # the last line points at an entry the window has
    out = _run(text, tmp_path)
    assert "e1.md" not in out and "4 pointer(s)" in out


def test_a_missing_index_is_silent_and_exits_zero(tmp_path):
    r = subprocess.run([sys.executable, "-X", "utf8", HOOK], capture_output=True, text=True,
                       env={**os.environ, "CLAUDE_MEMORY_INDEX": str(tmp_path / "absent.md")}, timeout=30)
    assert r.returncode == 0 and r.stdout == ""


def test_the_probe_and_the_hook_agree_on_the_saved_before_state():
    """The same-day before/after we published on claude-code#70555 came from the probe; the hook must
    read the same file to the same four names or the two instruments disagree on the cut rule."""
    saved = os.path.join(os.path.expanduser("~"), ".claude", "projects", "C--Users-Danculus-agora",
                         "memory", "MEMORY.md.pre-compaction-2026-09-13")
    if not os.path.isfile(saved):
        pytest.skip("the saved pre-compaction index is not on this machine")
    r = subprocess.run([sys.executable, "-X", "utf8", HOOK], capture_output=True, text=True, encoding="utf-8",
                       env={**os.environ, "CLAUDE_MEMORY_INDEX": saved}, timeout=30)
    assert "kept 180 of 184 lines (24,892 of 25,149 units); 4 pointer(s)" in r.stdout
    assert "public-repo-anon-git-identity.md" in r.stdout
