import sys
import time

from . import keys

# Readers that poll can miss a press with no time between down and up.
HOLD_SECONDS = 0.05


class KeyboardError(Exception):
    pass


class EvdevKeyboard:
    """Virtual keyboard on /dev/uinput. Works on Wayland and X11."""

    def __init__(self):
        from evdev import UInput, ecodes

        self.ecodes = ecodes
        # Advertising the whole keyboard range makes udev tag the device as
        # a keyboard. Hotkey readers like gsr-global-hotkeys skip devices
        # that only report a single key.
        all_keys = list(range(ecodes.KEY_ESC, ecodes.KEY_MICMUTE + 1))
        try:
            # Created once at startup so the compositor has picked up the
            # device by the time the first key press is sent.
            self.device = UInput({ecodes.EV_KEY: all_keys}, name="voice-to-hotkey")
        except PermissionError:
            raise KeyboardError(
                "VTH can't create a virtual keyboard because it has no write "
                "access to /dev/uinput.\n\nTo fix it, create "
                "/etc/udev/rules.d/60-uinput.rules containing\n\n"
                'KERNEL=="uinput", GROUP="input", MODE="0660"\n\n'
                "then add yourself to the input group and log out and back in."
            ) from None
        except OSError as e:
            raise KeyboardError(f"VTH can't create a virtual keyboard: {e}") from None

    def press(self, combo: list[str]):
        codes = [self.ecodes.ecodes[keys.to_evdev(name)] for name in combo]
        for code in codes:
            self.device.write(self.ecodes.EV_KEY, code, 1)
        self.device.syn()
        time.sleep(HOLD_SECONDS)
        for code in reversed(codes):
            self.device.write(self.ecodes.EV_KEY, code, 0)
        self.device.syn()

    def permission_problem(self) -> str | None:
        return None

    def close(self):
        self.device.close()


class PynputKeyboard:
    """Sends key events through the OS input API on Windows and macOS."""

    SPECIAL = {
        "meta": "cmd", "printscreen": "print_screen", "scrolllock": "scroll_lock",
        "capslock": "caps_lock", "pageup": "page_up", "pagedown": "page_down",
    }

    def __init__(self):
        from pynput.keyboard import Controller, Key, KeyCode

        self.controller = Controller()
        self.Key = Key
        self.KeyCode = KeyCode

    def to_key(self, name: str):
        if name in keys.SYMBOL_KEYS:
            return self.KeyCode.from_char(keys.SYMBOL_KEYS[name])
        if len(name) == 1:
            return self.KeyCode.from_char(name)
        key = getattr(self.Key, self.SPECIAL.get(name, name), None)
        if key is None:
            raise KeyboardError(f"{keys.label([name])} isn't available on this system.")
        return key

    def press(self, combo: list[str]):
        resolved = [self.to_key(name) for name in combo]
        for key in resolved:
            self.controller.press(key)
        time.sleep(HOLD_SECONDS)
        for key in reversed(resolved):
            self.controller.release(key)

    def permission_problem(self) -> str | None:
        """macOS drops key events from apps without Accessibility access."""
        if sys.platform != "darwin":
            return None
        import ctypes

        services = ctypes.cdll.LoadLibrary(
            "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices")
        services.AXIsProcessTrusted.restype = ctypes.c_bool
        if services.AXIsProcessTrusted():
            return None
        return ("VTH needs Accessibility access to press keys.\n\n"
                "Open System Settings, go to Privacy & Security, then Accessibility, "
                "and turn on Voice to Hotkey. Then quit and reopen VTH.")

    def close(self):
        pass


def create():
    if sys.platform.startswith("linux"):
        return EvdevKeyboard()
    return PynputKeyboard()
