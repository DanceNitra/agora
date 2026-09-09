# Dictate

Local Windows dictation app for Slovak, Czech, and English. Runs in the
system tray, records while a global hotkey is held, and transcribes offline
with NVIDIA Parakeet TDT 0.6B v3 via sherpa-onnx.

## Status

Phase 1: project skeleton, config model, logging, and `--list-mics`.

## Development

```powershell
cd dictate
uv sync --extra dev
uv run pytest
uv run python -m dictate --list-mics
```

## Commands

```powershell
uv run python -m dictate                 # run the app (tray + hotkey)
uv run python -m dictate --list-mics     # list input devices
uv run python -m dictate --test-mic 3    # record 3 s and transcribe
uv run python -m dictate --transcribe file.wav
uv run python -m dictate --download-model
uv run python -m dictate --config-path
```

## Config

Settings live in `%LOCALAPPDATA%/Dictate/config.json`. See
`config.example.json` for the full schema.
