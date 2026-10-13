# Voice to Hotkey (VTH)

Say a phrase, and your computer presses a hotkey.

Say "clip that" and your recording app saves a clip. Say "next slide" and your slides move on. VTH sits in the system tray, listens for the phrases you pick, and presses the key or combo you choose, like `F8` or `Alt+F10`.

Speech recognition runs entirely on your computer, using [Vosk](https://alphacephei.com/vosk/). Nothing you say is sent anywhere.

## Download

Get the latest version from the [Releases page](../../releases/latest).

| System | File |
| --- | --- |
| Windows 10 or 11 | `VTH-Setup-<version>.exe` |
| Mac with Apple silicon (M1 and later) | `VTH-<version>-macOS-AppleSilicon.dmg` |
| Mac with an Intel chip | `VTH-<version>-macOS-Intel.dmg` |
| Linux (64-bit) | `VTH-<version>-x86_64.AppImage` |

Not sure which Mac you have? Open the Apple menu and choose **About This Mac**. The **Chip** line says "Apple" or "Intel".

## Install

VTH isn't signed with a paid developer certificate yet, so Windows and macOS show a warning the first time you open it. It's safe to continue, and you only have to do this once.

### Windows

1. Run `VTH-Setup-<version>.exe`.
2. If you see **Windows protected your PC**, click **More info**, then **Run anyway**.
3. Finish the installer. VTH opens when it's done, and you can find it in the Start menu later.

### macOS

1. Open the `.dmg` and drag **Voice to Hotkey** into **Applications**.
2. Open Voice to Hotkey from Applications. macOS will say it can't verify the app. Click **Done**.
3. Open **System Settings**, go to **Privacy & Security**, scroll down, and click **Open Anyway** next to the Voice to Hotkey message. Confirm with your password.
4. When asked, allow microphone access.
5. VTH also needs **Accessibility** access to press keys. Open **System Settings**, go to **Privacy & Security**, then **Accessibility**, and turn on **Voice to Hotkey**. Then quit and reopen VTH.

After an update, macOS sometimes forgets the Accessibility permission. If keys stop working, turn it off and on again in the same place.

### Linux

1. Make the AppImage executable. In most file managers that's right-click, **Properties**, **Permissions**, then **Allow executing file as program**. In a terminal it's `chmod +x VTH-*.AppImage`.
2. Double-click it to run.

VTH presses keys through a virtual keyboard, which works on both Wayland and X11. That needs write access to `/dev/uinput`. Most desktops give this to the logged-in user already. If VTH says it can't create a virtual keyboard, run:

```sh
echo 'KERNEL=="uinput", GROUP="input", MODE="0660"' | sudo tee /etc/udev/rules.d/60-uinput.rules
sudo usermod -aG input "$USER"
```

Then log out and back in.

On GNOME, the system tray needs the [AppIndicator extension](https://extensions.gnome.org/extension/615/appindicator-support/). Ubuntu includes it already.

## First launch

The first time VTH opens, it asks for:

- **Language**: which speech model to use. VTH downloads it once (40 to 90 MB).
- **Phrase**: what to listen for. Short phrases of common words work best.
- **Hotkey**: click the box and press the key or combo your app uses.
- Whether to start listening as soon as VTH opens, and whether to open VTH when you log in.

When the model has downloaded, VTH shows a notice that it's ready.

## Using VTH

VTH lives in the system tray. The icon shows what it's doing:

- **Teal**: listening.
- **Gray with a line through it**: paused.
- **Orange flash**: it heard your phrase and pressed the hotkey.

Click the icon to pause or resume. Right-click it (or click, on macOS) for the menu:

- **Start listening** or **Pause listening**
- **Microphone**: pick which mic to use.
- **Sound**: play a sound of your choice before the hotkey is pressed, or turn it off.
- **When VTH opens**: start listening right away, or stay paused until you click.
- **Open on login**: start VTH when you log in.
- **Open config file**: change phrases, the hotkey and other settings.
- **Quit VTH**

## Settings

Everything lives in `config.toml`. Open it from the tray menu. VTH picks up changes as soon as you save the file, with no restart. If the file has a mistake, VTH tells you what's wrong and keeps using the last working settings.

| Setting | Default | What it does |
| --- | --- | --- |
| `phrases` | `["clip that"]` | Saying any of these presses the hotkey |
| `hotkey` | `"f8"` | Key or combo to press, like `"alt+f10"` or `"ctrl+shift+s"` |
| `start_listening` | `true` | Start listening when VTH opens |
| `model` | `"vosk-model-small-en-us-0.15"` | Speech model, from the [Vosk model list](https://alphacephei.com/vosk/models) |
| `microphone` | `""` (system default) | Part of the microphone's name |
| `cooldown_seconds` | `3` | Ignore the phrase this long after it triggers |
| `min_confidence` | `0.7` | How sure the recognizer must be about each word, from 0 to 1 |
| `sound` | `""` (no sound) | WAV, MP3, OGG or FLAC file to play before the hotkey. VTH waits for it to end, so keep it short |

Hotkey modifiers are `ctrl`, `shift`, `alt` and `meta` (the Windows key, or Command on a Mac). Keys can be letters, numbers, `f1` to `f24`, arrows, `space`, `enter`, `tab`, `esc`, `home`, `end`, `pageup`, `pagedown`, `insert`, `delete`, `printscreen` and common punctuation.

Where the file lives:

| System | Path |
| --- | --- |
| Windows | `%LOCALAPPDATA%\voice-to-hotkey\config.toml` |
| macOS | `~/Library/Preferences/voice-to-hotkey/config.toml` |
| Linux | `~/.config/voice-to-hotkey/config.toml` |

## Troubleshooting

**VTH never reacts to my phrase.** Every word has to be in the speech model's vocabulary. If a word isn't, VTH shows a notice naming it. Try another spelling, a different word, or add a few spellings as separate phrases. If it reacts too rarely, lower `min_confidence` a little, like `0.5`.

**VTH reacts but the app doesn't do anything.** Check the hotkey matches the app's setting exactly, including modifiers. Some games with anti-cheat ignore simulated key presses. On Windows, if the target app runs as administrator, VTH has to run as administrator too.

**The wrong microphone is used.** Pick the right one from the tray menu's **Microphone** list.

## Privacy

VTH listens to your microphone only while it's listening (teal icon), and all recognition happens on your computer. The only network access is the one-time model download from alphacephei.com.

## Build from source

You need Python 3.11 or newer.

```sh
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/vth
```

Run the tests with `.venv/bin/pytest`. To build a standalone app for your system:

```sh
.venv/bin/pyinstaller --noconfirm packaging/vth.spec
```

### Releasing

1. Update `__version__` in `src/voice_to_hotkey/__init__.py`.
2. Commit, then tag and push: `git tag v0.2.0 && git push origin v0.2.0`.
3. GitHub Actions builds every platform and opens a draft release. Check it and publish.

## License

MIT. See [LICENSE](LICENSE). Speech recognition by [Vosk](https://alphacephei.com/vosk/) (Apache 2.0).
