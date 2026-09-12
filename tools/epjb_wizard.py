"""Open the incomplete EPJ B submission and report WHICH wizard steps are still missing.

The Author Main Menu says Incomplete Submissions (1) and Waiting for Author's Approval (0), so the
submission exists and was never finished. This walks into it and screenshots each step, because the
list of what is missing has to come from the portal rather than from our checklist file, which was
written on 2026-09-01 and already misled one status report today.

Everything renders inside a frame; a reader that does not switch into it sees only the menu bar.
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from epjb_portal import _driver, into_content, login, shot, visible_text  # noqa: E402

from selenium.webdriver.common.by import By  # noqa: E402


CLICK_JS = """
const needle = arguments[0].toLowerCase();
const els = Array.from(document.querySelectorAll('a, input[type=button], input[type=submit], button'));
for (const e of els) {
  const t = ((e.innerText || e.value || '') + '').toLowerCase();
  if (t.includes(needle)) { e.click(); return (e.innerText || e.value || '').trim(); }
}
return null;
"""


def click_text(d, needle, tag="a"):
    """Find and click in ONE script call, so no element reference survives to go stale.

    Holding a Selenium element across a frame switch raised StaleElementReferenceException on every
    attempt: into_content() leaves and re-enters the frame, and every reference taken before that is
    dead. Doing the search and the click inside the page removes the reference entirely.
    """
    into_content(d)
    try:
        return d.execute_script(CLICK_JS, needle)
    except Exception as e:
        print("  click(%r) failed: %s" % (needle, type(e).__name__))
        return None


def main():
    d = _driver()
    if not login(d):
        print("login failed; see the screenshot")
        return
    time.sleep(2)

    got = click_text(d, "Incomplete Submissions")
    print("clicked: %r" % got)
    time.sleep(6)
    into_content(d)
    shot(d, "10_incomplete_list")

    got = click_text(d, "Action Links")
    print("clicked: %r" % got)
    time.sleep(4)
    into_content(d)
    shot(d, "11_action_menu")
    print("--- menu text ---")
    print(visible_text(d, 1200))

    got = click_text(d, "Edit Submission")
    print("clicked: %r" % got)
    time.sleep(8)
    if len(d.window_handles) > 1:
        d.switch_to.window(d.window_handles[-1])
        time.sleep(3)
    into_content(d)
    shot(d, "12_wizard")
    print("--- the wizard ---")
    print(visible_text(d, 4000))


if __name__ == "__main__":
    main()
