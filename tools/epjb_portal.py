"""Drive the EPJ B Editorial Manager portal in a real Edge window, and LOOK at what it renders.

WHY A REAL WINDOW, AND WHY A SCREENSHOT. On 2026-09-09 and again on 2026-09-11 this project read
the portal's HTML with curl, found the string "Site under development. Do not use for live
manuscript submission.", and reported it as a blocking banner. It sits inside
`<div id='implMessage' ... style="display: none;">` and no user has ever seen it. The first time
cost an e-mail to the editorial office; the second time cost the owner's trust in a status report.

So this file has one rule: a claim about the portal comes from a rendered screenshot, never from the
page source.

WHY THE PASSWORD IS NEVER HERE. The profile directory persists, so the owner logs in ONCE, by hand,
in the window this opens. Everything afterwards runs in that session. Two steps stay his in any
case: the registration e-mail goes to his Gmail, which there is a standing rule never to read, and
the final Approve of the compiled PDF is the act that fixes the corresponding author.

    python tools/epjb_portal.py open          # open the portal, screenshot what renders
    python tools/epjb_portal.py state         # where is the submission, as the page shows it
    python tools/epjb_portal.py shot <name>   # screenshot the current page
"""
from __future__ import annotations

import os
import sys
import time

PORTAL = "https://www.editorialmanager.com/epjb/"
PROFILE = os.path.join(os.path.expanduser("~"), ".agora", "edge-epjb-profile")
SHOTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "agora_output", "edrn_submission", "portal_shots")


def _driver():
    from selenium import webdriver
    from selenium.webdriver.edge.options import Options

    os.makedirs(PROFILE, exist_ok=True)
    os.makedirs(SHOTS, exist_ok=True)
    o = Options()
    # NOT headless. The owner types the password in this window, and a headed window is also the
    # only way a screenshot shows what a person would actually see.
    o.add_argument("--user-data-dir=" + PROFILE)
    o.add_argument("--window-size=1400,1000")
    o.add_experimental_option("detach", True)      # the window outlives this process
    return webdriver.Edge(options=o)


def shot(d, name):
    path = os.path.join(SHOTS, "%s.png" % name)
    d.save_screenshot(path)
    print("  screenshot: %s" % path)
    return path


def visible_text(d, limit=2500):
    """What a PERSON sees. innerText skips display:none; innerHTML does not, and that difference is
    the whole reason this file exists."""
    return (d.execute_script("return document.body.innerText") or "")[:limit]


def into_content(d, marker=None):
    """Editorial Manager puts the page inside a frame, so the top document holds only the header.

    Measured: `document.body.innerText` at the top level returned the menu bar and nothing else,
    while the screenshot showed a full table. Every click and every read below has to happen inside
    the frame, and a script that does not switch reports an empty page and clicks nothing.

    Returns the frame it switched into, or None when the content is already at the top level.
    """
    from selenium.webdriver.common.by import By

    # BY CONTENT, NOT BY SIZE. The first version picked the frame with the most text and kept
    # landing on the Author Main Menu, which is longer than the page actually being viewed. Every
    # read then described the menu and every click missed, exactly the wrong-target defect this
    # session has hit five times elsewhere. `want` names something only the right frame carries.
    want = (marker or "").lower()
    d.switch_to.default_content()
    frames = d.find_elements(By.CSS_SELECTOR, "iframe, frame")
    if want:
        for fr in frames:
            try:
                d.switch_to.frame(fr)
                if want in visible_text(d, 100000).lower():
                    return fr
            except Exception:
                pass
            d.switch_to.default_content()
        # the marker may be at the top level
        if want in visible_text(d, 100000).lower():
            return None
    d.switch_to.default_content()
    best, best_len = None, len(visible_text(d, 100000))
    for fr in frames:
        try:
            d.switch_to.frame(fr)
            n = len(visible_text(d, 100000))
            if n > best_len:
                best, best_len = fr, n
        except Exception:
            pass
        d.switch_to.default_content()
    if best is not None:
        d.switch_to.frame(best)
    return best


def _creds():
    """Read the account out of the gitignored .env.epjb. The values never reach stdout."""
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env.epjb")
    out = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def login(d):
    """Author Login, from the stored account. Prints whether it worked, never what it used."""
    from selenium.webdriver.common.by import By

    c = _creds()
    d.get(PORTAL)
    time.sleep(3)
    try:
        d.find_element(By.ID, "username").send_keys(c["EPJB_USERNAME"])
        d.find_element(By.ID, "passwordTextbox").send_keys(c["EPJB_PASSWORD"])
        d.find_element(By.ID, "authorLoginButton").click()
    except Exception:
        # the field ids differ between EM skins; fall back to the visible labels
        boxes = d.find_elements(By.CSS_SELECTOR, "input[type=text], input[type=password]")
        if len(boxes) >= 2:
            boxes[0].send_keys(c["EPJB_USERNAME"])
            boxes[1].send_keys(c["EPJB_PASSWORD"])
        for b in d.find_elements(By.CSS_SELECTOR, "input[type=submit], button"):
            if "author" in (b.get_attribute("value") or b.text or "").lower():
                b.click()
                break
    time.sleep(5)
    txt = visible_text(d, 400)
    print("after login, the page shows: %s" % txt[:200].replace("\n", " | "))
    return "logout" in txt.lower() or "main menu" in txt.lower()


def state(d):
    """Go to Incomplete Submissions and report what RENDERS there."""
    from selenium.webdriver.common.by import By

    into_content(d)
    for label in ("Incomplete Submissions", "Submissions Sent Back to Author",
                  "Incomplete Submissions Being Revised"):
        links = [a for a in d.find_elements(By.TAG_NAME, "a")
                 if label.lower() in (a.text or "").lower()]
        if links:
            print("  clicking: %s" % links[0].text.strip())
            links[0].click()
            time.sleep(5)
            into_content(d)
            break
    shot(d, "02_incomplete_%s" % time.strftime("%H%M%S"))
    print("--- what the page shows ---")
    print(visible_text(d, 3000))


def edit(d):
    """Open Action Links -> Edit Submission and report every step the portal lists."""
    from selenium.webdriver.common.by import By

    into_content(d)
    for a in d.find_elements(By.TAG_NAME, "a"):
        if "action links" in (a.text or "").lower():
            a.click()
            time.sleep(3)
            into_content(d)
            break
    shot(d, "03_action_links_%s" % time.strftime("%H%M%S"))
    for a in d.find_elements(By.TAG_NAME, "a"):
        if "edit submission" in (a.text or "").lower():
            print("  clicking: %s" % a.text.strip())
            a.click()
            time.sleep(6)
            break
    # EM opens the submission wizard in a new window more often than not
    if len(d.window_handles) > 1:
        d.switch_to.window(d.window_handles[-1])
        time.sleep(3)
    into_content(d)
    shot(d, "04_edit_submission_%s" % time.strftime("%H%M%S"))
    print("--- the wizard, as it renders ---")
    print(visible_text(d, 4000))


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "open"
    d = _driver()
    try:
        if cmd in ("state", "edit"):
            ok = login(d)
            shot(d, "01b_after_login_%s" % time.strftime("%H%M%S"))
            if not ok:
                print("login did not land on the author menu; the screenshot shows where it stopped.")
                return
            state(d)
            if cmd == "edit":
                edit(d)
            return
        d.get(PORTAL)
        time.sleep(4)
        print("title : %s" % d.title)
        print("url   : %s" % d.current_url)
        shot(d, "01_landing_%s" % time.strftime("%H%M%S"))
        text = visible_text(d)
        print("--- what the page actually shows (innerText, first 1200 chars) ---")
        print(text[:1200])
        hidden = "under development" in (d.page_source or "").lower()
        shown = "under development" in text.lower()
        print()
        print("'under development' in the SOURCE : %s" % hidden)
        print("'under development' VISIBLE to a user: %s" % shown)
        if hidden and not shown:
            print("  -> exactly the trap that cost two reports. The source is not the page.")
        if cmd == "open":
            print()
            print("The window stays open. Log in there by hand, then say so and I will read the")
            print("submission state from the rendered page.")
    finally:
        pass    # detach=True: the window is left open on purpose


if __name__ == "__main__":
    main()
