"""Open the incomplete submission's Edit Submission wizard and list every step it shows.

The frame is chosen BY CONTENT here. Choosing it by size kept landing on the Author Main Menu,
which is longer than the page being viewed, so every read described the menu and every click
missed.
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from epjb_portal import _driver, into_content, login, shot, visible_text  # noqa: E402

LIST_URL = "https://www.editorialmanager.com/epjb/auth_incSubmissions.asp?currentPage=1"

LINKS_JS = """
return Array.from(document.querySelectorAll('a'))
  .map(a => [ (a.innerText||'').trim(), a.getAttribute('href')||'', a.getAttribute('onclick')||'' ])
  .filter(x => x[0].length > 0);
"""


def main():
    d = _driver()
    if not login(d):
        print("login failed")
        return
    d.get(LIST_URL)
    time.sleep(6)
    into_content(d, "Incomplete Submissions")
    shot(d, "30_list")
    print("--- the row's links, from the frame that actually holds the table ---")
    for text, href, onclick in (d.execute_script(LINKS_JS) or []):
        print("  %-26s href=%-46s onclick=%s" % (text[:26], href[:46], onclick[:70]))


if __name__ == "__main__":
    main()
