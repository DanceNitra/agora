# -*- coding: utf-8 -*-
"""deepseek_balance_notify.py - after every Codex turn, show the DeepSeek balance as a Windows toast.

Codex runs `notify` with the turn event as the last argument. The config already had a notify
command (Codex computer-use), so this script runs that command first with the same arguments and
then reads GET https://api.deepseek.com/user/balance. The toast shows the balance and what the
turn cost. Every reading is appended to ~/.codex/deepseek_balance.jsonl.

    notify = ["pythonw", "C:\\Users\\Danculus\\agora\\tools\\deepseek_balance_notify.py", "<original exe>", "turn-ended"]

The key comes from the DEEPSEEK_API_KEY user environment variable and is never printed.
"""
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

LOG = Path.home() / ".codex" / "deepseek_balance.jsonl"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def user_env(name):
    v = os.environ.get(name)
    if v:
        return v
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            return winreg.QueryValueEx(k, name)[0]
    except OSError:
        return None


def balance():
    req = urllib.request.Request("https://api.deepseek.com/user/balance",
                                 headers={"Authorization": f"Bearer {user_env('DEEPSEEK_API_KEY')}",
                                          "Accept": "application/json"})
    d = json.load(urllib.request.urlopen(req, timeout=15))
    usd = next((b for b in d.get("balance_infos", []) if b.get("currency") == "USD"), d["balance_infos"][0])
    return float(usd["total_balance"]), usd.get("currency", "USD")


def last_reading():
    try:
        return json.loads(LOG.read_text(encoding="utf-8").strip().splitlines()[-1])
    except Exception:
        return None


def toast(title, text):
    ps = ("[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime] | Out-Null;"
          "$x=[Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02);"
          f"$t=$x.GetElementsByTagName('text');$t.Item(0).InnerText='{title}';$t.Item(1).InnerText='{text}';"
          "$n=[Windows.UI.Notifications.ToastNotification]::new($x);"
          "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("
          "'{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\\WindowsPowerShell\\v1.0\\powershell.exe').Show($n)")
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], creationflags=NO_WINDOW, timeout=20)


def main():
    args = sys.argv[1:]
    # Keep the notify command that was configured before us: every arg except Codex's JSON payload.
    if args and args[0].lower().endswith(".exe") and Path(args[0]).exists():
        subprocess.Popen(args, creationflags=NO_WINDOW)
    try:
        bal, cur = balance()
    except Exception as e:
        toast("DeepSeek kredit", f"Neda sa zistit: {type(e).__name__}")
        return
    prev = last_reading()
    spent = (prev["balance"] - bal) if prev else 0.0
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "balance": bal, "currency": cur}) + "\n")
    line = f"Zostava {bal:.2f} {cur}" + (f", tah stal {spent * 100:.1f} centu" if prev and spent > 0 else "")
    toast("DeepSeek kredit", line)


if __name__ == "__main__":
    main()
