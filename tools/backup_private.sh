#!/usr/bin/env bash
# Encrypted backup of everything that exists ONLY on this machine.
#
# What it covers: the gitignored strategy directory, the SSH keys, both .env
# files, and the crew-os workflow plans. What it does NOT cover: anything
# already on GitHub, and the two signing keys, which live on paper.
#
# The passphrase lives in ~/.agora_backup_pass, outside every repository. The
# script creates it on the first run. Print that file and store it with the
# key sheet: an encrypted archive without its passphrase is a deleted archive.
#
# Usage: bash tools/backup_private.sh [target_dir]
set -euo pipefail

HOME_DIR="/c/Users/Danculus"
PASS_FILE="$HOME_DIR/.agora_backup_pass"
# openssl here is a native Windows build, so it needs a Windows path for -pass.
winpath() { cygpath -w "$1" 2>/dev/null || echo "$1"; }
OUT_DIR="${1:-$HOME_DIR/backups}"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="$OUT_DIR/agora-private-$STAMP.tar.gz.enc"

if [ ! -f "$PASS_FILE" ]; then
  openssl rand -base64 32 > "$PASS_FILE"
  chmod 600 "$PASS_FILE"
  echo "NEW PASSPHRASE written to $PASS_FILE. Print it and store it on paper."
fi

mkdir -p "$OUT_DIR"

SOURCES=(
  "agora/agora_output/strategy"
  "agora/agora_output/channels"
  "agora/tools/brief_panel"
  "agora/server/.env"
  "agora/agora-game-server/.env"
  ".ssh"
  "crew-os/07 Workflow"
  ".claude/projects/C--Users-Danculus-agora/memory"
)

PRESENT=()
for s in "${SOURCES[@]}"; do
  if [ -e "$HOME_DIR/$s" ]; then PRESENT+=("$s"); else echo "MISSING, skipped: $s"; fi
done

tar -C "$HOME_DIR" -czf - "${PRESENT[@]}" |
  openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -salt -pass "file:$(winpath "$PASS_FILE")" -out "$OUT"

SIZE=$(du -h "$OUT" | cut -f1)
SHA=$(sha256sum "$OUT" | cut -d' ' -f1)
echo "$STAMP  $SHA  $SIZE  $(basename "$OUT")" >> "$OUT_DIR/MANIFEST.txt"

# Prove the archive decrypts and lists, so the backup is verified, not assumed.
COUNT=$(openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -pass "file:$(winpath "$PASS_FILE")" -in "$OUT" | tar -tzf - | wc -l)

echo "OK  $OUT"
echo "    size $SIZE  sha256 $SHA"
echo "    verified: decrypts and lists $COUNT entries"
echo "    Copy this file off the machine. One copy on one disk is not a backup."
