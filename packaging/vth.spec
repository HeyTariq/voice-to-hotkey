# Build with: pyinstaller --noconfirm packaging/vth.spec
import os
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

from voice_to_hotkey import APP_ID, APP_NAME, __version__

exe_name = "vth" if sys.platform.startswith("linux") else "VTH"
icon = os.path.join(SPECPATH, "app.png")

a = Analysis(
    [os.path.join(SPECPATH, "launcher.py")],
    binaries=collect_dynamic_libs("vosk"),
    datas=collect_data_files("voice_to_hotkey"),
    hiddenimports=[
        "PySide6.QtSvg",
        "pynput.keyboard._win32",
        "pynput.keyboard._darwin",
        "pynput.mouse._win32",
        "pynput.mouse._darwin",
    ],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=exe_name,
    console=False,
    icon=icon,
)
coll = COLLECT(exe, a.binaries, a.datas, name=exe_name)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name=f"{APP_NAME}.app",
        icon=icon,
        bundle_identifier=f"io.github.{APP_ID}",
        version=__version__,
        info_plist={
            "CFBundleDisplayName": APP_NAME,
            "CFBundleShortVersionString": __version__,
            # Tray only, no Dock icon.
            "LSUIElement": True,
            "NSMicrophoneUsageDescription":
                "Voice to Hotkey listens for your phrase. Audio never leaves this Mac.",
        },
    )
