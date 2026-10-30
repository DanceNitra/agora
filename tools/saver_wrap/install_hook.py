"""Switch the inspeximus context saver on for every Claude Code session: install_hook.py [--off].

The saver runs as a PreToolUse hook on Bash in the USER settings (C:/Users/Danculus/.claude/settings.json), so it
covers every project, in the desktop app and in VS Code alike. The project-level copy in agora is removed, because
two hooks would rewrite the same command twice. The previous settings file is kept beside it as .bak-saver-<time>.

Output under 5,000 bytes is untouched. A larger output is replaced by a digest plus the path of the full output.
Switch off per session with AGORA_SAVER_WRAP=0, or everywhere with --off.
"""
import json
import os
import shutil
import sys
import time

USER = os.path.join(os.path.expanduser("~"), ".claude", "settings.json")
PROJECT = "C:/Users/Danculus/agora/.claude/settings.json"
WRAP = os.path.join(os.path.expanduser("~"), ".claude", "saver", "saver_wrap.py").replace("\\", "/")
ENTRY = {"matcher": "Bash", "hooks": [{"type": "command", "command": 'python "%s"' % WRAP, "timeout": 10}]}


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _save(path, data):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def _without_saver(hooks):
    return [h for h in hooks if "saver_wrap" not in json.dumps(h)]


def main(argv):
    off = "--off" in argv
    d = _load(USER)
    shutil.copyfile(USER, USER + ".bak-saver-" + time.strftime("%Y%m%d-%H%M%S"))
    pre = _without_saver(d.setdefault("hooks", {}).setdefault("PreToolUse", []))
    if not off:
        pre.append(ENTRY)
    d["hooks"]["PreToolUse"] = pre
    _save(USER, d)
    if os.path.exists(PROJECT):                       # one hook only, or a command is wrapped twice
        p = _load(PROJECT)
        p.setdefault("hooks", {})["PreToolUse"] = _without_saver(p.get("hooks", {}).get("PreToolUse", []))
        _save(PROJECT, p)
    print("context saver %s for every Claude Code session. Restart a session to pick it up." %
          ("OFF" if off else "ON"))
    print("user hook: %s" % ("removed" if off else WRAP))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
