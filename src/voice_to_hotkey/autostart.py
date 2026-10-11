"""Start on login, per OS."""

import os
import plistlib
import subprocess
import sys
from pathlib import Path

from . import APP_ID, APP_NAME

LINUX_ENTRY = Path.home() / ".config" / "autostart" / f"{APP_ID}.desktop"
MAC_AGENT = Path.home() / "Library" / "LaunchAgents" / f"{APP_ID}.plist"
WINDOWS_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def command() -> list[str]:
    """How to launch this same copy of VTH."""
    # An AppImage runs from a temporary mount, so point at the file itself.
    if os.environ.get("APPIMAGE"):
        return [os.environ["APPIMAGE"]]
    if getattr(sys, "frozen", False):
        return [sys.executable]
    return [sys.executable, "-m", "voice_to_hotkey"]


def is_enabled() -> bool:
    if sys.platform == "win32":
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, WINDOWS_RUN_KEY) as key:
                winreg.QueryValueEx(key, APP_NAME)
            return True
        except OSError:
            return False
    if sys.platform == "darwin":
        return MAC_AGENT.exists()
    return LINUX_ENTRY.exists()


def set_enabled(on: bool):
    if sys.platform == "win32":
        _set_windows(on)
    elif sys.platform == "darwin":
        _set_mac(on)
    else:
        _set_linux(on)


def _set_linux(on: bool):
    if not on:
        LINUX_ENTRY.unlink(missing_ok=True)
        return
    LINUX_ENTRY.parent.mkdir(parents=True, exist_ok=True)
    LINUX_ENTRY.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={APP_NAME}\n"
        "Comment=Presses a hotkey when you say a phrase\n"
        f"Exec={' '.join(_desktop_quote(arg) for arg in command())}\n"
        f"Icon={APP_ID}\n"
        "X-GNOME-Autostart-enabled=true\n"
    )


def _desktop_quote(arg: str) -> str:
    """Quote an argument the way .desktop Exec lines expect."""
    if not any(c in arg for c in ' \t"\'\\$`'):
        return arg
    escaped = "".join("\\" + c if c in '"`$\\' else c for c in arg)
    return f'"{escaped}"'


def _set_mac(on: bool):
    if not on:
        MAC_AGENT.unlink(missing_ok=True)
        return
    MAC_AGENT.parent.mkdir(parents=True, exist_ok=True)
    with MAC_AGENT.open("wb") as f:
        plistlib.dump({"Label": APP_ID, "ProgramArguments": command(), "RunAtLoad": True}, f)


def _set_windows(on: bool):
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, WINDOWS_RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if on:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, subprocess.list2cmdline(command()))
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
