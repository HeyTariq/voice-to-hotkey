#!/usr/bin/env bash
# Packs dist/Voice to Hotkey.app into a drag-to-Applications disk image.
# Usage: build-dmg.sh AppleSilicon|Intel
set -euo pipefail

version=$(python -c 'import voice_to_hotkey; print(voice_to_hotkey.__version__)')
staging=build/dmg

rm -rf "$staging"
mkdir -p "$staging"
cp -R "dist/Voice to Hotkey.app" "$staging/"
ln -s /Applications "$staging/Applications"
hdiutil create -volname "Voice to Hotkey" -srcfolder "$staging" -ov -format UDZO \
    "dist/VTH-$version-macOS-$1.dmg"
