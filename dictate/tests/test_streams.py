"""A windowed executable has no console, and the code must survive that.

The packaged setup wizard failed on its download page with "NoneType object has no
attribute 'write'". Nothing in the test suite could have caught it, because a test run
always has a stdout. These tests take it away.
"""

from __future__ import annotations

import inspect
import sys

from dictate import cli
from dictate.log import ensure_streams, setup_logging


def test_ensure_streams_replaces_missing_stdout_and_stderr(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)
    ensure_streams()
    assert sys.stdout is not None and sys.stderr is not None
    print("this raised before the fix")
    print("so did this", file=sys.stderr)


def test_setup_logging_survives_a_console_less_process(monkeypatch, tmp_path):
    # StreamHandler binds sys.stderr when it is built, so a None stderr breaks logging
    # itself, not only print.
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)
    import logging

    logger = logging.getLogger("dictate")
    monkeypatch.setattr(logger, "handlers", [])
    setup_logging("INFO", log_dir=tmp_path)
    logger.info("a line that must not raise")


def test_the_self_test_helper_prints_nothing():
    """`run_selftest` is what the wizard calls, so a print in it is a crash there.

    A control for this test: the same check against `selftest`, which is the command-line
    wrapper and does print. If both came back clean the check would not be measuring
    anything.
    """
    quiet = inspect.getsource(cli.run_selftest)
    loud = inspect.getsource(cli.selftest)
    assert "print(" not in quiet, "run_selftest prints; the wizard has no stdout"
    assert "print(" in loud, "the control failed: selftest is supposed to print"


def test_the_help_page_names_the_key_the_app_listens_on(tmp_path, monkeypatch):
    """The instructions must come from the config, not from a sentence someone typed.

    This page said Ctrl+Shift+R for a build that listened on right Ctrl. The check is
    written against a NON-default key, so a hardcoded default would still fail it.
    """
    import json

    from dictate import setup_wizard
    from dictate.config import DictateConfig, save_config

    config_path = tmp_path / "config.json"
    save_config(DictateConfig(hotkey="scroll lock"), config_path)

    shown = []
    monkeypatch.setattr(setup_wizard.SetupWizard, "_line",
                        lambda self, text, colour=None, size=10: shown.append(text))
    monkeypatch.setattr(setup_wizard.SetupWizard, "_title",
                        lambda self, text, subtitle="": None)

    wizard = setup_wizard.SetupWizard.__new__(setup_wizard.SetupWizard)
    wizard.config_path = config_path
    wizard.next_button = type("Button", (), {"config": lambda self, **kw: None})()
    setup_wizard.SetupWizard._page_help(wizard)

    joined = " ".join(shown)
    assert "Scroll Lock" in joined, "the page does not name the configured key: %s" % joined
    assert "Ctrl+Shift+R" not in joined
    assert json.loads(config_path.read_text(encoding="utf-8"))["hotkey"] == "scroll lock"


def test_the_system_page_shows_every_failed_check(monkeypatch):
    """A failing check must reach the screen and must block Next.

    Written against a fabricated failure rather than this machine, which passes
    everything: a page that only ever renders green has not been tested.
    """
    from dictate import setup_wizard

    monkeypatch.setattr(setup_wizard, "_wizard_checks", None, raising=False)
    monkeypatch.setattr("dictate.preflight.run_all", lambda: [
        ("Graphics card", True, "NVIDIA Test Card"),
        ("Driver", False, "driver 442.19 is older than 527.41"),
        ("WebView2 runtime", False, "The WebView2 runtime is missing"),
        ("Disk space", True, "40.0 GB free"),
    ])

    shown, buttons = [], []
    monkeypatch.setattr(setup_wizard.SetupWizard, "_line",
                        lambda self, text, colour=None, size=10: shown.append(text))
    monkeypatch.setattr(setup_wizard.SetupWizard, "_title",
                        lambda self, text, subtitle="": None)

    wizard = setup_wizard.SetupWizard.__new__(setup_wizard.SetupWizard)
    wizard.next_button = type("Button", (), {
        "config": lambda self, **kw: buttons.append(kw)})()
    wizard.status = type("Label", (), {"config": lambda self, **kw: None})()
    setup_wizard.SetupWizard._page_system(wizard)

    joined = " ".join(shown)
    assert "442.19" in joined and "WebView2 runtime is missing" in joined
    assert wizard.gpu_ok is False
    assert {"state": "disabled"} in buttons, "a failed check must block Next"
