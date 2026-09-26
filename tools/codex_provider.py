# -*- coding: utf-8 -*-
"""codex_provider.py - switch Codex (CREW OS) between Ollama, DeepSeek and Gemini without losing sessions.

Sessions live in ~/.codex/sessions/*.jsonl whatever the provider, so switching and then `codex resume`
keeps the history. Codex 0.154 accepts only the Responses API (wire_api = "chat" is no longer supported).
If a provider answers the Responses API directly (see agora_output/api_key_check_<p>.json, written by
tools/set_api_key.ps1), Codex talks to it directly. Otherwise a local LiteLLM proxy on 127.0.0.1:4000
translates Responses -> Chat Completions. Keys stay in Windows user environment variables; this script
never reads or prints them except to pass them to the proxy process environment.

    python tools/codex_provider.py status
    python tools/codex_provider.py use deepseek [--model deepseek-chat]
    python tools/codex_provider.py use gemini   [--model gemini-2.5-flash]
    python tools/codex_provider.py use ollama          # back to the original config
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

CODEX = Path.home() / ".codex"
CONFIG = CODEX / "config.toml"
STATE = CODEX / "agora_provider_state.json"
AGORA = Path(__file__).resolve().parent.parent
CHECK = AGORA / "agora_output"
LITELLM = Path.home() / ".venvs" / "litellm" / "Scripts" / "litellm.exe"
PROXY_PORT = 4000
PROVIDERS = {
    "deepseek": {"env": "DEEPSEEK_API_KEY", "base": "https://api.deepseek.com/v1", "litellm_prefix": "deepseek/"},
    "gemini": {"env": "GEMINI_API_KEY", "base": "https://generativelanguage.googleapis.com/v1beta/openai",
               "litellm_prefix": "gemini/"},
}


def user_env(name):
    """Read a Windows USER env var (set by set_api_key.ps1) even if this shell started before it was set."""
    v = os.environ.get(name)
    if v:
        return v
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            return winreg.QueryValueEx(k, name)[0]
    except OSError:
        return None


def read_top(text, key):
    m = re.search(rf'^{key}\s*=\s*"([^"]*)"', text.split("\n[", 1)[0], re.M)
    return m.group(1) if m else None


def set_top(text, key, value):
    head, sep, rest = text.partition("\n[")
    line = f'{key} = "{value}"'
    if re.search(rf"^{key}\s*=", head, re.M):
        head = re.sub(rf"^{key}\s*=.*$", line, head, flags=re.M)
    else:
        head = line + "\n" + head
    return head + sep + rest


def ensure_table(text, name, body):
    block = f"\n[model_providers.{name}]\n" + "".join(f"{k} = {json.dumps(v)}\n" for k, v in body.items())
    pat = rf"\n\[model_providers\.{re.escape(name)}\]\n(?:[^\[\n].*\n?)*"
    if re.search(pat, text):
        return re.sub(pat, block, text)
    return text.rstrip("\n") + "\n" + block


def check(p):
    f = CHECK / f"api_key_check_{p}.json"
    return json.loads(f.read_text(encoding="utf-8-sig")) if f.exists() else {}


def proxy_up():
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{PROXY_PORT}/health/liveliness", timeout=3)
        return True
    except Exception:
        return False


def start_proxy(p, model):
    """LiteLLM proxy: Codex speaks Responses to it, it speaks Chat Completions to the provider."""
    if not LITELLM.exists():
        sys.exit(f"LiteLLM is not installed at {LITELLM}.")
    cfg = CODEX / f"litellm_{p}.yaml"
    cfg.write_text(
        "model_list:\n"
        f"  - model_name: {model}\n"
        "    litellm_params:\n"
        f"      model: {PROVIDERS[p]['litellm_prefix']}{model}\n"
        f"      api_key: os.environ/{PROVIDERS[p]['env']}\n", encoding="utf-8")
    env = dict(os.environ)
    key = user_env(PROVIDERS[p]["env"])
    if not key:
        sys.exit(f"{PROVIDERS[p]['env']} is not set. Run: powershell -File tools\\set_api_key.ps1 {p}")
    env[PROVIDERS[p]["env"]] = key
    log = open(CODEX / "litellm_proxy.log", "a", encoding="utf-8")
    proc = subprocess.Popen([str(LITELLM), "--config", str(cfg), "--port", str(PROXY_PORT), "--host", "127.0.0.1"],
                            env=env, stdout=log, stderr=subprocess.STDOUT,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    for _ in range(60):
        if proxy_up():
            (CODEX / "litellm_proxy.pid").write_text(str(proc.pid))
            return proc.pid
        time.sleep(1)
    sys.exit("LiteLLM proxy did not come up; see ~/.codex/litellm_proxy.log")


def stop_proxy():
    pidf = CODEX / "litellm_proxy.pid"
    if pidf.exists():
        subprocess.run(["taskkill", "/PID", pidf.read_text().strip(), "/T", "/F"], capture_output=True)
        pidf.unlink()


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("status")
    u = sp.add_parser("use")
    u.add_argument("provider", choices=["ollama", "deepseek", "gemini"])
    u.add_argument("--model")
    a = ap.parse_args()
    text = CONFIG.read_text(encoding="utf-8")

    if a.cmd == "status":
        print(json.dumps({"model_provider": read_top(text, "model_provider"), "model": read_top(text, "model"),
                          "proxy_up": proxy_up(), "saved_original": json.loads(STATE.read_text()) if STATE.exists() else None},
                         indent=1))
        return

    if not STATE.exists():  # remember the original Ollama setup once
        STATE.write_text(json.dumps({"model_provider": read_top(text, "model_provider"), "model": read_top(text, "model")}))
    shutil.copy(CONFIG, CONFIG.with_name(f"config.toml.bak-{time.strftime('%Y%m%d-%H%M%S')}"))

    if a.provider == "ollama":
        orig = json.loads(STATE.read_text())
        text = set_top(set_top(text, "model_provider", orig["model_provider"]), "model", orig["model"])
        if orig.get("ollama_table_original"):  # old threads pin their provider id; that table was pointed at DeepSeek
            text = re.sub(r"\n\[model_providers\.ollama-launch-codex-app\]\n(?:[^\[\n].*\n?)*",
                          lambda _: "\n" + orig["ollama_table_original"] + "\n", text)
        stop_proxy()
        CONFIG.write_text(text, encoding="utf-8")
        print(f"Codex -> {orig['model_provider']} / {orig['model']}. Restart Codex, then `codex resume`.")
        return

    info = check(a.provider)
    model = a.model or (info.get("models") or [None])[0]
    if not model:
        sys.exit(f"No model known for {a.provider}. Run: powershell -File tools\\set_api_key.ps1 {a.provider}")
    direct = info.get("responses_http") == 200
    if direct:
        name = f"agora_{a.provider}"
        text = ensure_table(text, name, {"name": a.provider, "base_url": PROVIDERS[a.provider]["base"],
                                         "env_key": PROVIDERS[a.provider]["env"], "wire_api": "responses"})
        stop_proxy()
    else:
        name = "agora_proxy"
        stop_proxy()
        pid = start_proxy(a.provider, model)
        text = ensure_table(text, name, {"name": f"LiteLLM -> {a.provider}", "base_url": f"http://127.0.0.1:{PROXY_PORT}/v1",
                                         "wire_api": "responses"})
        print(f"LiteLLM proxy running, PID {pid}")
    text = set_top(set_top(text, "model_provider", name), "model", model)
    CONFIG.write_text(text, encoding="utf-8")
    print(f"Codex -> {a.provider} ({'direct' if direct else 'via LiteLLM proxy'}), model {model}. "
          f"Restart Codex, then `codex resume` to continue the same thread.")


if __name__ == "__main__":
    main()
