#!/usr/bin/env bash
# For translators: creates an .xdelta patch from YOUR build and checks it.
# Usage: ./make-patch.sh original.iso my-build.iso my-patch.xdelta
set -euo pipefail
[ $# -eq 3 ] || { echo "Usage: $0 <original.iso> <my-build.iso> <my-patch.xdelta>"; exit 1; }
XD=xdelta3; [ -x "$(dirname "$0")/xdelta3" ] && XD="$(dirname "$0")/xdelta3"
[ ! -e "$3" ] || { echo "$3 already exists. Choose another name."; exit 1; }
md5() { if command -v md5sum >/dev/null; then md5sum "$1" | cut -d' ' -f1; else md5 -q "$1"; fi; }
echo "Creating patch (1 GB source window, so it stays small)..."
"$XD" -e -9 -S djw -B 1073741824 -s "$1" "$2" "$3"
echo "Checking: applying the patch to the original again..."
"$XD" -d -f -s "$1" "$3" "$3.check.iso"
A=$(md5 "$2"); B=$(md5 "$3.check.iso"); rm -f "$3.check.iso"
[ "$A" = "$B" ] || { echo "FAILED: the patch does not reproduce your build. Do not share it."; exit 1; }
echo "OK: the patch reproduces your build exactly. Share $3 with these MD5s:"
echo "  original : $(md5 "$1")"
echo "  patched  : $A"
