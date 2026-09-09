"""Command-line entrypoint for Dictate.

Commands:
    python -m dictate                 Run the app (tray + hotkey).
    python -m dictate --list-mics     List available microphones.
    python -m dictate --test-mic 3    Record 3 s with beeps and transcribe.
    python -m dictate --listen 3      Probe mics, then record and transcribe 3 takes.
    python -m dictate --transcribe file.wav   Transcribe a wav file.
    python -m dictate --download-model        Download the default model.
    python -m dictate --config-path          Print the config path.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _list_mics() -> int:
    """Print available input devices and return 0."""
    import sounddevice as sd

    devices = sd.query_devices()
    inputs = [d for d in devices if d["max_input_channels"] > 0]
    if not inputs:
        print("No input devices found.", file=sys.stderr)
        return 1
    print("Available input devices:")
    for index, device in enumerate(devices):
        if device["max_input_channels"] > 0:
            name = device["name"]
            channels = device["max_input_channels"]
            host = sd.query_hostapis(device["hostapi"])["name"]
            default = " (default)" if index == sd.default.device[0] else ""
            print(f"  [{index}] {name} ({channels} ch) [{host}]{default}")
    return 0


def _config_path() -> int:
    """Print the config path and return 0."""
    from .config import default_config_path

    print(default_config_path())
    return 0


def _run_app(config_path: Path | None = None) -> int:
    """Run the standalone dictation window with hotkey support."""
    import threading

    from .app import DictationApp
    from .config import load_config
    from .log import setup_logging
    from .overlay import WebViewWindow

    setup_logging("INFO")
    app = DictationApp(load_config(config_path))

    stop_event = threading.Event()
    window = WebViewWindow(app, stop_event)
    app.set_target_provider(lambda: window.last_external)
    worker = threading.Thread(target=app.run_forever, args=(stop_event,), daemon=True)
    worker.start()
    window.run()  # blocks the main thread in the webview loop
    return 0

def main(argv: list[str] | None = None) -> int:
    """Parse arguments and dispatch to the requested command."""
    parser = argparse.ArgumentParser(prog="dictate", description="Local Windows dictation app.")
    parser.add_argument(
        "--list-mics",
        action="store_true",
        help="List available input devices and exit.",
    )
    parser.add_argument(
        "--test-mic",
        metavar="SECONDS",
        type=int,
        nargs="?",
        const=3,
        help="Record N seconds with beeps and a live meter, then transcribe.",
    )
    parser.add_argument(
        "--listen",
        metavar="TAKES",
        type=int,
        nargs="?",
        const=3,
        help="Record and transcribe TAKES takes with beeps."
    )
    parser.add_argument(
        "--probe",
        action="store_true",
        help="Force a microphone probe before --listen takes.",
    )
    parser.add_argument(
        "--app",
        action="store_true",
        help="Run the dictation loop with the global hotkey (console output).",
    )
    parser.add_argument(
        "--transcribe",
        metavar="FILE",
        type=Path,
        help="Transcribe a wav file and print timing and text.",
    )
    parser.add_argument(
        "--download-model",
        action="store_true",
        help="Download the default ASR model and exit.",
    )
    parser.add_argument(
        "--config-path",
        action="store_true",
        help="Print the config file path and exit.",
    )
    parser.add_argument(
        "--config",
        metavar="PATH",
        type=Path,
        help="Use a specific config file instead of the default.",
    )

    args = parser.parse_args(argv)

    if args.config_path:
        return _config_path()
    if args.list_mics:
        return _list_mics()
    if args.test_mic is not None:
        from .cli import test_mic

        return test_mic(args.test_mic, config_path=args.config)
    if args.listen is not None:
        from .cli import listen

        return listen(args.listen, probe=args.probe or None, config_path=args.config)
    if args.app:
        from .app import DictationApp
        from .config import load_config as _load_config
        from .log import setup_logging

        setup_logging("INFO")
        return DictationApp(_load_config(args.config)).run() or 0
    if args.transcribe is not None:
        from .cli import transcribe_file

        return transcribe_file(args.transcribe, config_path=args.config)
    if args.download_model:
        from .cli import download_model

        return download_model(config_path=args.config)

    return _run_app(args.config)


if __name__ == "__main__":
    raise SystemExit(main())






