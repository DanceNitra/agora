"""Configuration model, load/save, defaults, and version migration.

Settings live in ``%LOCALAPPDATA%/Dictate/config.json``. The model is
versioned so future releases can migrate old files without breaking.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

CONFIG_VERSION = 1
APP_DIR_NAME = "Dictate"
CONFIG_FILE_NAME = "config.json"


class LLMCleanupConfig(BaseModel):
    """Optional LLM cleanup settings. Disabled by default."""

    enabled: bool = False
    base_url: str = "http://127.0.0.1:8080/v1"
    model: str = ""
    api_key: str = ""
    system_prompt: str = (
        "Clean up the following dictation transcript. Keep the meaning, "
        "fix obvious transcription errors, and return only the corrected text."
    )


class DictateConfig(BaseModel):
    """Validated configuration for the dictation app."""

    version: int = CONFIG_VERSION
    hotkey: str = "ctrl+alt+space"
    hotkey_mode: Literal["hold", "toggle"] = "hold"
    engine: Literal["parakeet", "whisper"] = "whisper"
    language: str = "sk"
    provider: Literal["cpu", "cuda"] = "cpu"
    num_threads: int = Field(default=0, ge=0)
    microphone: str | int | None = None
    insert_mode: Literal["clipboard", "sendinput"] = "clipboard"
    paste_shortcut: str = "ctrl+v"
    clipboard_restore_delay_ms: int = Field(default=300, ge=0)
    prefix_space: Literal["auto", "always", "never"] = "auto"
    refocus_original_window: bool = True
    vad_enabled: bool = True
    preroll_ms: int = Field(default=250, ge=0)
    max_record_seconds: int = Field(default=120, ge=1)
    feedback_sound: bool = True
    replacements_file: str = "slovnik.json"
    app_overrides: dict[str, dict[str, Any]] = Field(default_factory=dict)
    llm_cleanup: LLMCleanupConfig = Field(default_factory=LLMCleanupConfig)
    whisper_model: str = "large-v3-turbo"
    whisper_device: str = "cuda"
    typing_delay_ms: int = Field(default=2, ge=0)
    log_level: str = "INFO"

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        """Normalize language to a lowercase two-letter code."""
        value = value.strip().lower()
        if value not in {"sk", "cs", "en"}:
            raise ValueError(f"Unsupported language: {value!r}. Use sk, cs, or en.")
        return value

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        """Validate the log level name."""
        value = value.upper()
        if value not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError(f"Invalid log level: {value!r}")
        return value


def app_data_dir() -> Path:
    """Return the per-user data directory for Dictate."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / APP_DIR_NAME
    return Path.home() / f".{APP_DIR_NAME.lower()}"


def default_config_path() -> Path:
    """Return the default config file path."""
    return app_data_dir() / CONFIG_FILE_NAME


def _migrate(raw: dict[str, Any]) -> dict[str, Any]:
    """Migrate an older config dict to the current version."""
    version = int(raw.get("version", 1))
    if version > CONFIG_VERSION:
        raise ValueError(
            f"Config version {version} is newer than supported version {CONFIG_VERSION}."
        )
    # Future migrations go here, keyed by version.
    raw["version"] = CONFIG_VERSION
    return raw


def load_config(path: Path | None = None) -> DictateConfig:
    """Load config from ``path``, or the default location if ``path`` is None.

    Missing files produce the default config. Invalid JSON or validation
    errors raise so the user can fix the file instead of silently losing
    settings.
    """
    config_path = path or default_config_path()
    if not config_path.exists():
        return DictateConfig()
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    migrated = _migrate(raw)
    return DictateConfig.model_validate(migrated)


def save_config(config: DictateConfig, path: Path | None = None) -> Path:
    """Save ``config`` to ``path``, or the default location if ``path`` is None.

    Returns the path that was written.
    """
    config_path = path or default_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(config.model_dump(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return config_path

