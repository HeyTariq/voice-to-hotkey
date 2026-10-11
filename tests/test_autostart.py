from voice_to_hotkey.autostart import _desktop_quote


def test_desktop_quote():
    assert _desktop_quote("/usr/bin/vth") == "/usr/bin/vth"
    assert _desktop_quote("/home/a b/VTH.AppImage") == '"/home/a b/VTH.AppImage"'
    assert _desktop_quote('a"$b') == '"a\\"\\$b"'
