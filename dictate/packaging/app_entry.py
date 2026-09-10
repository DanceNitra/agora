"""Entry point for the packaged app."""

from dictate.log import ensure_streams

ensure_streams()

from dictate.__main__ import main  # noqa: E402  streams first

if __name__ == "__main__":
    raise SystemExit(main())
