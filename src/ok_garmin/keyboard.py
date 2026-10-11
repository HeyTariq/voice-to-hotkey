import time

from evdev import UInput, ecodes

# Advertising the whole keyboard range makes udev tag the device as a
# keyboard. Hotkey readers like gsr-global-hotkeys skip devices that
# only report a single key.
KEYBOARD_KEYS = set(range(ecodes.KEY_ESC, ecodes.KEY_MICMUTE + 1))

# Readers that poll can miss a press with no time between down and up.
HOLD_SECONDS = 0.05


class Keyboard:
    """Virtual keyboard on /dev/uinput. Works on Wayland and X11."""

    def __init__(self, key_name: str):
        self.code = ecodes.ecodes[key_name]
        keys = sorted(KEYBOARD_KEYS | {self.code})
        # Created once at startup so the compositor has picked up the
        # device by the time the first key press is sent.
        self.device = UInput({ecodes.EV_KEY: keys}, name="ok-garmin")

    def press(self):
        self.device.write(ecodes.EV_KEY, self.code, 1)
        self.device.syn()
        time.sleep(HOLD_SECONDS)
        self.device.write(ecodes.EV_KEY, self.code, 0)
        self.device.syn()

    def close(self):
        self.device.close()
