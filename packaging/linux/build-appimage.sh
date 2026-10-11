#!/usr/bin/env bash
# Wraps the PyInstaller output in dist/vth into an AppImage.
set -euo pipefail

version=$(python -c 'import voice_to_hotkey; print(voice_to_hotkey.__version__)')
appdir=build/AppDir
tool=build/appimagetool

rm -rf "$appdir"
mkdir -p "$appdir/usr/bin"
cp -r dist/vth/. "$appdir/usr/bin/"
cp packaging/app.png "$appdir/voice-to-hotkey.png"
cp packaging/linux/voice-to-hotkey.desktop "$appdir/"
cat > "$appdir/AppRun" <<'RUN'
#!/bin/sh
exec "$(dirname "$(readlink -f "$0")")/usr/bin/vth" "$@"
RUN
chmod +x "$appdir/AppRun"

if [ ! -x "$tool" ]; then
    curl -fsSL -o "$tool" \
        https://github.com/AppImage/appimagetool/releases/download/1.9.0/appimagetool-x86_64.AppImage
    chmod +x "$tool"
fi
APPIMAGE_EXTRACT_AND_RUN=1 ARCH=x86_64 "$tool" "$appdir" "dist/VTH-$version-x86_64.AppImage"
