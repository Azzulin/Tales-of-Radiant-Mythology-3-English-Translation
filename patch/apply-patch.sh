#!/usr/bin/env bash
# Tales of the World: Radiant Mythology 3 - English patch
# Applies the .xdelta in this folder to YOUR copy of the Japanese ISO.
# Usage: ./apply-patch.sh /path/to/original.iso
# Needs xdelta3 (Debian/Ubuntu: sudo apt install xdelta3 | macOS: brew install xdelta)
set -euo pipefail
cd "$(dirname "$0")"
ORIG_MD5=5d63d1652b851e005d27fe42db7d6241

if [ $# -lt 1 ]; then echo "Usage: $0 /path/to/original.iso"; exit 1; fi
ORIG=$1
[ -f "$ORIG" ] || { echo "File not found: $ORIG"; exit 1; }

if [ -x ./xdelta3 ]; then XD=./xdelta3
elif command -v xdelta3 >/dev/null; then XD=xdelta3
else echo "xdelta3 not found. Install it (apt install xdelta3 / brew install xdelta)."; exit 1; fi

PATCH=$(ls -1 *.xdelta 2>/dev/null | head -1 || true)
[ -n "$PATCH" ] || { echo "No .xdelta file in this folder. Get it from the Releases page."; exit 1; }
OUT="${PATCH%.xdelta}.iso"
[ ! -e "$OUT" ] || { echo "$OUT already exists. Delete or rename it first."; exit 1; }

md5() { if command -v md5sum >/dev/null; then md5sum "$1" | cut -d' ' -f1; else md5 -q "$1"; fi; }

echo "Checking your ISO (MD5)..."
H=$(md5 "$ORIG" | tr 'A-F' 'a-f')
if [ "$H" != "$ORIG_MD5" ]; then
  echo "Your ISO's MD5 is $H, the patch needs $ORIG_MD5."
  echo "This is not the original Japanese dump (NPJH50353), or it was modified."
  exit 1
fi
echo "OK, original ISO recognized. Applying $PATCH ..."
if ! "$XD" -d -s "$ORIG" "$PATCH" "$OUT"; then
  rm -f "$OUT"; echo "xdelta3 reported an error."; exit 1
fi
echo "Done: $OUT"
echo "Play it on PPSSPP or a PSP/Vita with custom firmware. Do NOT use the in-game Data Install."
