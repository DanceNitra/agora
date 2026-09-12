"""Navigate to the incomplete submission by URL, because clicking the menu link does nothing.

A scripted `.click()` on the Author Main Menu anchors leaves the page on the menu: Editorial Manager
drives them through a postback that a synthetic click does not trigger. Reading the anchor's href
and navigating to it does work, and it is also the honest thing to report: the automation follows
the link the page itself carries.
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from epjb_portal import _driver, into_content, login, shot, visible_text  # noqa: E402

HREFS_JS = """
return Array.from(document.querySelectorAll('a'))
  .map(a => [ (a.innerText||'').trim(), a.getAttribute('href')||'', a.getAttribute('onclick')||'' ])
  .filter(x => x[0].length > 0);
"""


def links(d):
    into_content(d)
    try:
        return d.execute_script(HREFS_JS) or []
    except Exception:
        return []


def main():
    d = _driver()
    if not login(d):
        print("login failed")
        return
    time.sleep(2)
    rows = links(d)
    print("--- the menu's own links ---")
    for text, href, onclick in rows:
        if any(k in text.lower() for k in ("incomplete", "approval", "processed", "submit new")):
            print("  %-48s href=%s onclick=%s" % (text[:48], href[:90], onclick[:70]))

    target = None
    for text, href, _o in rows:
        if "incomplete submissions" in text.lower() and "revised" not in text.lower():
            target = href
            break
    if not target:
        print("no href found for Incomplete Submissions")
        return
    url = target if target.startswith("http") else \
        d.current_url.rsplit("/", 1)[0] + "/" + target.lstrip("/")
    print("navigating to: %s" % url[:120])
    d.get(url)
    time.sleep(6)
    into_content(d)
    shot(d, "20_incomplete_by_url")
    print("--- page ---")
    print(visible_text(d, 1200))

    # Action Links is a menu the row carries. Take its href the same way.
    rows = links(d)
    print()
    print("--- every link on the row ---")
    for text, href, onclick in rows:
        if text and ("action" in text.lower() or "edit" in text.lower()
                     or "submission" in text.lower()):
            print("  %-30s href=%s onclick=%s" % (text[:30], href[:80], onclick[:80]))
    tgt = None
    for text, href, _o in rows:
        if "edit submission" in text.lower():
            tgt = href
            break
    if tgt is None:
        for text, href, _o in rows:
            if "action links" in text.lower():
                print()
                print("Action Links carries href=%r; opening it." % href[:120])
                if href and not href.lower().startswith("javascript"):
                    d.get(href if href.startswith("http")
                          else d.current_url.rsplit("/", 1)[0] + "/" + href.lstrip("/"))
                    time.sleep(5)
                    into_content(d)
                    shot(d, "21_action_links")
                    print(visible_text(d, 1500))
                break
        return
    url = tgt if tgt.startswith("http") else d.current_url.rsplit("/", 1)[0] + "/" + tgt.lstrip("/")
    print("opening Edit Submission: %s" % url[:120])
    d.get(url)
    time.sleep(8)
    into_content(d)
    shot(d, "22_edit_submission")
    print("--- the wizard ---")
    print(visible_text(d, 3500))


if __name__ == "__main__":
    main()
