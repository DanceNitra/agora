"""Switch into the content frame ONCE, then read everything without switching again.

Every earlier failure came from re-entering the frame: `into_content` was called by the reader AND
by the clicker, and each call re-picked a frame, so the second call landed somewhere else and the
row's links vanished. One switch, one read.
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from epjb_portal import _driver, login, shot  # noqa: E402

from selenium.webdriver.common.by import By  # noqa: E402

LIST_URL = "https://www.editorialmanager.com/epjb/auth_incSubmissions.asp?currentPage=1"
DUMP = """
return Array.from(document.querySelectorAll('a'))
  .map(a => [ (a.innerText||'').trim().slice(0,40), a.getAttribute('href')||'',
              (a.getAttribute('onclick')||'').slice(0,120) ])
  .filter(x => x[0].length > 0);
"""


def main():
    d = _driver()
    if not login(d):
        return
    d.get(LIST_URL)
    time.sleep(7)

    # find the ONE frame that carries the paper's title, then stay in it
    target = None
    d.switch_to.default_content()
    frames = d.find_elements(By.CSS_SELECTOR, "iframe, frame")
    print("frames at top level: %d" % len(frames))
    for i, fr in enumerate(frames):
        d.switch_to.default_content()
        try:
            d.switch_to.frame(fr)
            t = d.execute_script("return document.body.innerText") or ""
            print("  frame %d: %d chars | has title: %s" %
                  (i, len(t), "Non-Monotonic" in t))
            if "Non-Monotonic" in t:
                target = i
        except Exception as e:
            print("  frame %d: %s" % (i, type(e).__name__))
    if target is None:
        d.switch_to.default_content()
        t = d.execute_script("return document.body.innerText") or ""
        print("top level has title: %s" % ("Non-Monotonic" in t))
    else:
        d.switch_to.default_content()
        d.switch_to.frame(frames[target])
        print("staying in frame %d" % target)

    shot(d, "40_row")
    print("--- every link here ---")
    for text, href, onclick in (d.execute_script(DUMP) or []):
        print("  %-40s href=%-40s onclick=%s" % (text, href[:40], onclick))


if __name__ == "__main__":
    main()
