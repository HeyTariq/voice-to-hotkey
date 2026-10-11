from evdev import UInput, ecodes


class Keyboard:
    """Virtual keyboard on /dev/uinput. Works on Wayland and X11."""

    def __init__(self, key_name: str):
        self.code = ecodes.ecodes[key_name]
        # Created once at startup so the compositor has picked up the
        # device by the time the first key press is sent.
        self.device = UInput({ecodes.EV_KEY: [self.code]}, name="ok-garmin")

    def press(self):
        self.device.write(ecodes.EV_KEY, self.code, 1)
        self.device.syn()
        self.device.write(ecodes.EV_KEY, self.code, 0)
        self.device.syn()

    def close(self):
        self.device.close()
